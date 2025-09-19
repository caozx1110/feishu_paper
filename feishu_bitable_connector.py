#!/usr/bin/env python3
"""
飞书多维表格API连接器
支持创建数据表、管理字段、插入和更新数据等操作
"""

import json
import time
import os
from datetime import datetime
import requests
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class FeishuBitableConfig:
    """飞书多维表格配置类"""

    app_id: str
    app_secret: str
    user_access_token: Optional[str] = None  # 用户访问令牌
    tenant_access_token: Optional[str] = None  # 应用访问令牌
    app_token: str = ""  # 多维表格的app_token
    base_url: str = "https://open.feishu.cn/open-apis"
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

    def __post_init__(self):
        """验证配置"""
        if not self.user_access_token and not self.tenant_access_token:
            raise ValueError("必须提供 user_access_token 或 tenant_access_token 之一")

        # 优先使用有效的token，而不是优先使用user_access_token
        # 如果user_access_token是占位符，则清空它
        if self.user_access_token and ('xxxx' in self.user_access_token or len(self.user_access_token) < 20):
            self.user_access_token = None

        # 如果tenant_access_token是占位符，则清空它
        if self.tenant_access_token and ('xxxx' in self.tenant_access_token or len(self.tenant_access_token) < 20):
            self.tenant_access_token = None

        # 重新检查是否有有效token
        if not self.user_access_token and not self.tenant_access_token:
            raise ValueError("未提供有效的访问令牌，请检查环境变量配置")

    @property
    def access_token(self) -> str:
        """获取当前使用的访问令牌"""
        return self.user_access_token or self.tenant_access_token

    @property
    def token_type(self) -> str:
        """获取令牌类型"""
        if self.user_access_token:
            return "user"
        elif self.tenant_access_token:
            return "tenant"
        else:
            return "unknown"

    @classmethod
    def from_hydra_config(cls, cfg) -> 'FeishuBitableConfig':
        """从Hydra配置创建飞书多维表格配置"""
        feishu_cfg = cfg.get('feishu', {})
        api_cfg = feishu_cfg.get('api', {})
        bitable_cfg = feishu_cfg.get('bitable', {})

        return cls(
            app_id=api_cfg.get('app_id', ''),
            app_secret=api_cfg.get('app_secret', ''),
            user_access_token=api_cfg.get('user_access_token') or None,
            tenant_access_token=api_cfg.get('tenant_access_token') or None,
            app_token=bitable_cfg.get('app_token', ''),
            base_url=api_cfg.get('base_url', 'https://open.feishu.cn/open-apis'),
            timeout=api_cfg.get('timeout', 30),
            max_retries=api_cfg.get('max_retries', 3),
            retry_delay=api_cfg.get('retry_delay', 1.0),
        )


class FeishuBitableAPIError(Exception):
    """飞书多维表格API异常类"""

    def __init__(self, message: str, code: int = None, response: dict = None):
        self.message = message
        self.code = code
        self.response = response
        super().__init__(self.message)


class FeishuBitableConnector:
    """飞书多维表格连接器"""

    def __init__(self, config: FeishuBitableConfig = None):
        """初始化飞书多维表格连接器"""
        if config is None:
            # 如果没有提供配置，尝试从环境变量创建
            config = self._create_config_from_env()

        self.config = config
        self.session = requests.Session()
        self.session.headers.update(
            {'Content-Type': 'application/json; charset=utf-8', 'Authorization': f'Bearer {config.access_token}'}
        )

        # 打印使用的令牌类型（调试信息）
        print(f"🔑 使用 {config.token_type}_access_token 进行API认证")

    def _create_config_from_env(self) -> FeishuBitableConfig:
        """从环境变量创建配置"""
        import os
        from dotenv import load_dotenv

        load_dotenv()

        return FeishuBitableConfig(
            app_id=os.getenv('FEISHU_APP_ID', ''),
            app_secret=os.getenv('FEISHU_APP_SECRET', ''),
            user_access_token=os.getenv('FEISHU_USER_ACCESS_TOKEN'),
            tenant_access_token=os.getenv('FEISHU_TENANT_ACCESS_TOKEN'),
            app_token=os.getenv('FEISHU_BITABLE_APP_TOKEN', ''),
        )

    def get_tenant_access_token(self) -> str:
        """获取应用访问令牌 (tenant_access_token)

        Returns:
            应用访问令牌字符串
        """
        if not self.config.app_id or not self.config.app_secret:
            raise FeishuBitableAPIError("获取tenant_access_token需要app_id和app_secret")

        payload = {"app_id": self.config.app_id, "app_secret": self.config.app_secret}

        endpoint = "auth/v3/tenant_access_token/internal"

        # 临时创建一个不带认证的session来获取token
        temp_session = requests.Session()
        temp_session.headers.update({'Content-Type': 'application/json; charset=utf-8'})

        try:
            url = f"{self.config.base_url}/{endpoint}"
            response = temp_session.post(url, json=payload, timeout=self.config.timeout)
            result = response.json()

            if result.get('code') == 0:
                tenant_access_token = result.get('tenant_access_token')
                expires_in = result.get('expire')

                print(f"✅ 成功获取tenant_access_token，有效期: {expires_in}秒")
                return tenant_access_token
            else:
                raise FeishuBitableAPIError(
                    f"获取tenant_access_token失败: {result.get('msg', 'Unknown error')}", result.get('code'), result
                )

        except requests.exceptions.RequestException as e:
            raise FeishuBitableAPIError(f"获取tenant_access_token网络请求失败: {str(e)}")

    def refresh_token_if_needed(self) -> bool:
        """如果使用tenant_access_token且需要刷新，则自动刷新

        Returns:
            是否成功刷新了token
        """
        if self.config.token_type == "tenant" and self.config.app_id and self.config.app_secret:
            try:
                new_token = self.get_tenant_access_token()
                self.config.tenant_access_token = new_token

                # 更新session header
                self.session.headers.update({'Authorization': f'Bearer {new_token}'})

                return True
            except Exception as e:
                print(f"⚠️ token刷新失败: {e}")
                return False
        return False

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送API请求"""
        url = f"{self.config.base_url}/{endpoint}"

        for attempt in range(self.config.max_retries):
            try:
                response = self.session.request(method, url, timeout=self.config.timeout, **kwargs)

                result = response.json()

                if result.get('code') == 0:
                    return result.get('data', {})
                elif result.get('code') == 99991663:  # token过期
                    print("🔄 检测到token过期，尝试刷新...")
                    if self.refresh_token_if_needed():
                        print("✅ token刷新成功，重试请求...")
                        continue  # 重试请求
                    else:
                        raise FeishuBitableAPIError(
                            f"Token已过期且刷新失败: {result.get('msg', 'Unknown error')}", result.get('code'), result
                        )
                else:
                    raise FeishuBitableAPIError(
                        f"API请求失败: {result.get('msg', 'Unknown error')}", result.get('code'), result
                    )

            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise FeishuBitableAPIError(f"网络请求失败: {str(e)}")
                time.sleep(self.config.retry_delay)

    def create_table(self, table_name: str, fields: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """在多维表格中创建新的数据表

        Args:
            table_name: 表格名称
            fields: 字段定义列表，如果为None则创建默认字段

        Returns:
            创建的表格信息
        """
        if fields is None:
            # 默认字段配置
            fields = [{"field_name": "标题", "type": 1, "property": {}}]  # 多行文本

        payload = {"table": {"name": table_name, "default_view_name": "表格视图", "fields": fields}}

        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables"
        result = self._make_request('POST', endpoint, json=payload)

        return result

    def create_papers_table(self) -> Dict[str, Any]:
        """创建论文信息表（简化版）"""
        fields = [
            {"field_name": "ArXiv ID", "type": 1},  # 单行文本
            {"field_name": "标题", "type": 1},  # 单行文本
            {"field_name": "作者", "type": 1},  # 单行文本
            {"field_name": "摘要", "type": 1},  # 单行文本（暂时改为单行）
            {"field_name": "分类", "type": 1},  # 单行文本
            {
                "field_name": "发布日期",
                "type": 5,  # 日期
                "property": {"date_formatter": "yyyy/MM/dd", "auto_fill": False},
            },
            {
                "field_name": "更新日期",
                "type": 5,  # 日期
                "property": {"date_formatter": "yyyy/MM/dd", "auto_fill": False},
            },
            {"field_name": "PDF链接", "type": 15},  # 超链接
            {"field_name": "论文链接", "type": 15},  # 超链接
            {"field_name": "同步时间", "type": 1001},  # 创建时间
        ]

        return self.create_table("论文信息表", fields)

    def create_relations_table(self) -> Dict[str, Any]:
        """创建论文-领域关系表"""
        fields = [
            {"field_name": "论文ID", "type": 1},  # 单行文本
            {"field_name": "领域ID", "type": 1},  # 单行文本
            {"field_name": "领域名称", "type": 1},  # 单行文本
            {"field_name": "相关性评分", "type": 2, "property": {"formatter": "0.00"}},  # 数字
            {"field_name": "匹配关键词", "type": 1},  # 单行文本
            {"field_name": "同步时间", "type": 1001},  # 创建时间
        ]

        return self.create_table("论文领域关系表", fields)

    def create_domain_papers_table(self, table_name: str, research_area: str) -> Dict[str, Any]:
        """为特定研究领域创建论文表格"""
        fields = [
            {"field_name": "ArXiv ID", "type": 15},  # 超链接
            {"field_name": "标题", "type": 1},  # 单行文本
            {"field_name": "作者", "type": 4},  # 多选项
            {"field_name": "摘要", "type": 1},  # 单行文本
            {"field_name": "分类", "type": 4},  # 多选项
            {"field_name": "匹配关键词", "type": 4},  # 多选项
            {"field_name": "相关性评分", "type": 2, "property": {"formatter": "0.00"}},  # 数字
            {"field_name": "研究领域", "type": 4},  # 多选项
            {"field_name": "PDF链接", "type": 15},  # 超链接
            {"field_name": "必须关键词匹配", "type": 4},  # 多选项
            {
                "field_name": "发布日期",
                "type": 5,  # 日期
                "property": {"date_formatter": "yyyy/MM/dd", "auto_fill": False},
            },
            {
                "field_name": "更新日期",
                "type": 5,  # 日期
                "property": {"date_formatter": "yyyy/MM/dd", "auto_fill": False},
            },
            {"field_name": "同步时间", "type": 1001},  # 创建时间
        ]

        return self.create_table(table_name, fields)

    def list_tables(self) -> List[Dict[str, Any]]:
        """获取多维表格中的所有数据表"""
        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables"
        result = self._make_request('GET', endpoint)

        return result.get('items', [])

    def get_table_info(self, table_id: str) -> Dict[str, Any]:
        """获取指定数据表的详细信息"""
        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}"
        result = self._make_request('GET', endpoint)

        return result

    def get_all_records(self, table_id: str, page_size: int = 500) -> List[Dict[str, Any]]:
        """获取数据表中的所有记录"""
        all_records = []
        page_token = None

        while True:
            endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/records"
            params = {"page_size": page_size}

            if page_token:
                params["page_token"] = page_token

            result = self._make_request('GET', endpoint, params=params)

            if not result:
                break

            records = result.get('items', [])
            all_records.extend(records)

            page_token = result.get('page_token')
            if not page_token:
                break

        return all_records

    def add_field_to_table(
        self, table_id: str, field_name: str, field_type: int, property_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """向数据表添加新字段

        Args:
            table_id: 表格ID
            field_name: 字段名称
            field_type: 字段类型（1=多行文本, 2=数字, 5=日期, 15=超链接等）
            property_config: 字段属性配置

        Returns:
            添加的字段信息
        """
        if property_config is None:
            property_config = {}

        payload = {"field_name": field_name, "type": field_type, "property": property_config}

        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/fields"
        result = self._make_request('POST', endpoint, json=payload)

        return result

    def insert_record(self, table_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """向数据表插入新记录

        Args:
            table_id: 表格ID
            fields: 字段数据字典

        Returns:
            插入的记录信息
        """
        payload = {"fields": fields}

        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/records"
        result = self._make_request('POST', endpoint, json=payload)

        return result

    def batch_insert_records(self, table_id: str, records_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量插入记录到指定表格

        Args:
            table_id: 表格ID
            records_data: 记录列表，每个记录是字段数据字典

        Returns:
            批量插入结果
        """
        records = []
        for data in records_data:
            records.append({"fields": data})

        payload = {"records": records}
        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/records/batch_create"

        return self._make_request('POST', endpoint, json=payload)

    def format_paper_data(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化论文数据以符合飞书API要求

        Args:
            paper_data: 原始论文数据

        Returns:
            格式化后的数据
        """
        formatted_data = {}

        for key, value in paper_data.items():
            if key in ["发布日期", "更新日期"] and value:
                # 日期字段需要时间戳（毫秒）
                if isinstance(value, str):
                    try:
                        from datetime import datetime

                        dt = datetime.strptime(value, "%Y-%m-%d")
                        formatted_data[key] = int(dt.timestamp() * 1000)
                    except:
                        formatted_data[key] = value
                else:
                    formatted_data[key] = value

            elif key in ["PDF链接", "论文链接"] and value:
                # 超链接字段需要特殊格式
                formatted_data[key] = {"link": value, "text": value.split("/")[-1] if "/" in value else value}

            else:
                # 其他字段直接使用
                formatted_data[key] = value

        return formatted_data

    def insert_paper_record(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """插入论文记录（自动格式化数据）

        Args:
            paper_data: 论文数据

        Returns:
            插入结果
        """
        papers_table_id = os.getenv('FEISHU_PAPERS_TABLE_ID')
        if not papers_table_id:
            raise ValueError("未设置FEISHU_PAPERS_TABLE_ID环境变量")

        formatted_data = self.format_paper_data(paper_data)
        return self.insert_record(papers_table_id, formatted_data)

    def batch_insert_paper_records(self, papers_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量插入论文记录（自动格式化数据）

        Args:
            papers_list: 论文数据列表

        Returns:
            批量插入结果
        """
        papers_table_id = os.getenv('FEISHU_PAPERS_TABLE_ID')
        if not papers_table_id:
            raise ValueError("未设置FEISHU_PAPERS_TABLE_ID环境变量")

        formatted_papers = [self.format_paper_data(paper) for paper in papers_list]
        return self.batch_insert_records(papers_table_id, formatted_papers)

    def find_table_by_name(self, table_name: str) -> Optional[str]:
        """根据表格名称查找表格ID"""
        tables = self.list_tables()
        for table in tables:
            if table.get('name') == table_name:
                return table.get('table_id')
        return None

    def check_record_exists(self, table_id: str, arxiv_id: str) -> bool:
        """检查指定ArXiv ID的记录是否已存在"""
        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/records/search"

        # 构建查询条件
        payload = {
            "filter": {
                "conjunction": "and",
                "conditions": [{"field_name": "ArXiv ID", "operator": "is", "value": [arxiv_id]}],
            }
        }

        try:
            result = self._make_request('POST', endpoint, json=payload)
            items = result.get('items', [])
            return len(items) > 0
        except Exception:
            # 如果搜索失败，返回False，允许插入
            return False

    def setup_paper_sync_tables(self):
        """设置论文同步所需的数据表

        Returns:
            包含表格ID的字典
        """
        results = {}

        try:
            # 创建论文信息表
            print("📊 创建论文信息表...")
            papers_table = self.create_papers_table()
            papers_table_id = papers_table.get('table_id')
            results['papers_table_id'] = papers_table_id
            print(f"✅ 论文信息表创建成功: {papers_table_id}")

            # 创建关系表
            print("🔗 创建论文领域关系表...")
            relations_table = self.create_relations_table()
            relations_table_id = relations_table.get('table_id')
            results['relations_table_id'] = relations_table_id
            print(f"✅ 论文领域关系表创建成功: {relations_table_id}")

            return results

        except Exception as e:
            print(f"❌ 设置数据表失败: {e}")
            raise

    def format_multi_select_options(self, values: List[str], max_options: int = 20) -> List[str]:
        """格式化多选项字段的值

        Args:
            values: 选项值列表
            max_options: 最大选项数量限制

        Returns:
            格式化后的选项列表
        """
        if not values:
            return []

        # 清理和去重
        clean_values = []
        for value in values:
            if value and isinstance(value, str):
                cleaned = value.strip()
                if cleaned and cleaned not in clean_values:
                    clean_values.append(cleaned)

        # 限制选项数量
        return clean_values[:max_options]

    def prepare_multi_select_field_data(self, field_value: Any, field_type: str = "string") -> List[str]:
        """准备多选项字段数据

        Args:
            field_value: 字段值（可能是字符串、列表等）
            field_type: 字段类型

        Returns:
            格式化后的选项列表
        """
        if not field_value:
            return []

        if isinstance(field_value, str):
            # 字符串格式，按逗号分割
            values = [val.strip() for val in field_value.split(',') if val.strip()]
        elif isinstance(field_value, list):
            # 列表格式
            values = [str(val).strip() for val in field_value if val]
        else:
            # 其他格式，转换为字符串
            values = [str(field_value).strip()] if field_value else []

        return self.format_multi_select_options(values)

    def list_views(self, table_id: str) -> List[Dict[str, Any]]:
        """获取数据表中的所有视图"""
        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/views"
        result = self._make_request('GET', endpoint)
        return result.get('items', [])

    def create_view(self, table_id: str, view_config: Dict[str, Any]) -> Dict[str, Any]:
        """创建新视图并配置筛选排序条件

        Args:
            table_id: 表格ID
            view_config: 视图配置

        Returns:
            创建的视图信息
        """
        view_name = view_config.get('name', '新视图')

        # 第一步：创建基础视图
        payload = {"view_name": view_name, "view_type": "grid"}

        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/views"
        result = self._make_request('POST', endpoint, json=payload)

        if not result or not result.get('view', {}).get('view_id'):
            raise Exception(f"创建视图失败: {result}")

        view_id = result['view']['view_id']
        print(f"   ✅ 基础视图已创建: {view_name}")

        # 第二步：通过更新视图API配置筛选和排序
        success = self._configure_view_properties(table_id, view_id, view_config)
        if success:
            print(f"   ✅ 视图配置已应用")
        else:
            print(f"   ⚠️ 视图配置应用失败，但视图已创建")

        return result

    def _configure_view_properties(self, table_id: str, view_id: str, view_config: Dict[str, Any]) -> bool:
        """配置视图的排序和分组属性（不包括筛选，因为API限制）"""
        try:
            # 获取字段映射
            field_mapping = self._get_field_mapping(table_id)

            # 构建视图属性
            property_payload = {}

            # 处理排序条件（已验证可用）
            sorts = view_config.get('sorts', [])
            if sorts:
                sort_info = self._build_sort_info(sorts, field_mapping)
                if sort_info:
                    property_payload["sort_info"] = sort_info

            # 处理分组条件（已验证可用）
            group_by = view_config.get('group_by')
            if group_by:
                group_info = self._build_group_info(group_by, field_mapping)
                if group_info:
                    property_payload["group_info"] = group_info

            # 如果有属性需要设置，则更新视图
            if property_payload:
                update_payload = {"property": property_payload}
                endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/views/{view_id}"
                self._make_request('PATCH', endpoint, json=update_payload)
                return True

            return True

        except Exception as e:
            print(f"   ❌ 配置视图属性失败: {e}")
            return False

    def _build_view_property(self, table_id: str, view_config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """构建视图属性配置"""
        property_config = {}

        # 获取字段映射
        field_mapping = self._get_field_mapping(table_id)

        # 构建筛选条件
        filters = view_config.get('filters', [])
        if filters:
            conditions = []
            for filter_item in filters:
                condition = self._build_filter_condition_v2(filter_item, field_mapping)
                if condition:
                    conditions.append(condition)

            if conditions:
                property_config["filter_info"] = {"conjunction": "and", "conditions": conditions}

        # 构建排序条件
        sorts = view_config.get('sorts', [])
        if sorts:
            sort_infos = []
            for sort_item in sorts:
                field_name = sort_item.get('field')
                field_id = field_mapping.get(field_name, field_name)
                sort_info = {"field_id": field_id, "desc": sort_item.get('direction', 'desc') == 'desc'}
                sort_infos.append(sort_info)

            property_config["sort_info"] = sort_infos

        # 构建分组条件
        group_by = view_config.get('group_by')
        if group_by:
            field_id = field_mapping.get(group_by, group_by)
            property_config["group_info"] = [{"field_id": field_id, "desc": False}]

        return property_config if property_config else None

    def _build_filter_condition_v2(
        self, filter_item: Dict[str, Any], field_mapping: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """构建视图筛选条件（V2版本用于视图属性）"""
        field = filter_item.get('field')
        operator = filter_item.get('operator')
        value = filter_item.get('value')

        if not field or not operator:
            return None

        # 获取字段ID
        field_id = field_mapping.get(field, field)

        # 操作符映射（视图属性可能使用不同的操作符）
        operator_map = {
            'gte': 'isGreaterThanOrEqualTo',
            'lte': 'isLessThanOrEqualTo',
            'gt': 'isGreaterThan',
            'lt': 'isLessThan',
            'eq': 'is',
            'contains': 'contains',
            'not_contains': 'doesNotContain',
        }

        # 特殊处理日期相关操作符
        if operator == 'gte_days_ago':
            from datetime import datetime, timedelta

            days_ago = datetime.now() - timedelta(days=int(value))
            value = int(days_ago.timestamp() * 1000)
            operator = 'gte'

        feishu_operator = operator_map.get(operator, 'is')

        return {
            "field_id": field_id,
            "operator": feishu_operator,
            "value": [str(value)] if not isinstance(value, list) else [str(v) for v in value],
        }

    def delete_view(self, table_id: str, view_id: str) -> bool:
        """删除视图

        Args:
            table_id: 表格ID
            view_id: 视图ID

        Returns:
            是否删除成功
        """
        try:
            endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/views/{view_id}"
            self._make_request('DELETE', endpoint)
            return True
        except Exception as e:
            print(f"⚠️ 删除视图失败: {e}")
            return False

    def _build_filter_condition(
        self, filter_item: Dict[str, Any], field_mapping: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """构建筛选条件"""
        field = filter_item.get('field')
        operator = filter_item.get('operator')
        value = filter_item.get('value')

        if not field or not operator:
            return None

        # 获取字段ID
        field_id = field_mapping.get(field, field)

        # 操作符映射
        operator_map = {
            'gte': 'isGreaterThanOrEqualTo',
            'lte': 'isLessThanOrEqualTo',
            'gt': 'isGreaterThan',
            'lt': 'isLessThan',
            'eq': 'is',
            'contains': 'contains',
            'not_contains': 'doesNotContain',
        }

        # 特殊处理日期相关操作符
        if operator == 'gte_days_ago':
            # 计算N天前的时间戳
            from datetime import datetime, timedelta

            days_ago = datetime.now() - timedelta(days=int(value))
            value = int(days_ago.timestamp() * 1000)
            operator = 'gte'

        feishu_operator = operator_map.get(operator, 'is')

        return {
            "field_name": field_id,
            "operator": feishu_operator,
            "value": [str(value)] if not isinstance(value, list) else [str(v) for v in value],
        }

    def manage_table_views(
        self, table_id: str, view_configs: List[Dict[str, Any]], auto_cleanup: bool = True
    ) -> Dict[str, Any]:
        """管理表格视图

        Args:
            table_id: 表格ID
            view_configs: 视图配置列表
            auto_cleanup: 是否自动清理多余视图

        Returns:
            管理结果统计
        """
        result = {'created': 0, 'deleted': 0, 'existing': 0, 'errors': []}

        try:
            # 获取现有视图
            existing_views = self.list_views(table_id)
            existing_view_names = {view.get('view_name'): view.get('view_id') for view in existing_views}

            # 需要创建的视图名称
            target_view_names = {config.get('name') for config in view_configs}

            # 创建缺失的视图
            for view_config in view_configs:
                view_name = view_config.get('name')
                if view_name not in existing_view_names:
                    try:
                        print(f"🆕 创建视图: {view_name}")
                        self.create_view(table_id, view_config)
                        result['created'] += 1
                    except Exception as e:
                        error_msg = f"创建视图 '{view_name}' 失败: {e}"
                        print(f"❌ {error_msg}")
                        result['errors'].append(error_msg)
                else:
                    result['existing'] += 1

            # 删除多余的视图（如果启用自动清理）
            if auto_cleanup:
                for view_name, view_id in existing_view_names.items():
                    # 跳过默认视图
                    if view_name in ['表格视图', 'Grid View', '默认视图']:
                        continue

                    if view_name not in target_view_names:
                        try:
                            print(f"🗑️ 删除多余视图: {view_name}")
                            if self.delete_view(table_id, view_id):
                                result['deleted'] += 1
                        except Exception as e:
                            error_msg = f"删除视图 '{view_name}' 失败: {e}"
                            print(f"❌ {error_msg}")
                            result['errors'].append(error_msg)

            return result

        except Exception as e:
            error_msg = f"视图管理失败: {e}"
            print(f"❌ {error_msg}")
            result['errors'].append(error_msg)
            return result

    def _get_field_mapping(self, table_id: str) -> Dict[str, str]:
        """获取表格字段名称到ID的映射

        Args:
            table_id: 表格ID

        Returns:
            字段名称到字段ID的映射字典
        """
        try:
            endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/fields"
            fields_result = self._make_request('GET', endpoint)

            field_mapping = {}
            fields = fields_result.get('items', [])

            for field in fields:
                field_id = field.get('field_id')
                field_name = field.get('field_name')
                if field_id and field_name:
                    field_mapping[field_name] = field_id

            return field_mapping

        except Exception as e:
            print(f"⚠️ 获取字段映射失败: {e}")
            return {}

    def _build_filter_info(self, filters: List[Dict], field_mapping: Dict[str, str]) -> Optional[Dict]:
        """构建筛选信息"""
        conditions = []

        for filter_item in filters:
            field_name = filter_item.get('field')
            operator = filter_item.get('operator')
            value = filter_item.get('value')

            if not field_name or not operator:
                continue

            # 获取字段ID
            field_id = field_mapping.get(field_name)
            if not field_id:
                print(f"     ⚠️ 字段 '{field_name}' 未找到")
                continue

            # 转换操作符
            feishu_operator = self._convert_operator(operator)

            # 处理特殊操作符
            if operator == 'gte_days_ago':
                from datetime import datetime, timedelta

                days_ago = datetime.now() - timedelta(days=int(value))
                value = int(days_ago.timestamp() * 1000)
                feishu_operator = 'isGreaterThanOrEqualTo'

            # 构建条件
            condition = {
                "field_id": field_id,
                "operator": feishu_operator,
                "value": [str(value)] if not isinstance(value, list) else [str(v) for v in value],
            }
            conditions.append(condition)

        if conditions:
            return {"conjunction": "and", "conditions": conditions}

        return None

    def _build_sort_info(self, sorts: List[Dict], field_mapping: Dict[str, str]) -> Optional[List[Dict]]:
        """构建排序信息"""
        sort_specs = []

        for sort_item in sorts:
            field_name = sort_item.get('field')
            direction = sort_item.get('direction', 'desc')

            if not field_name:
                continue

            field_id = field_mapping.get(field_name)
            if not field_id:
                print(f"     ⚠️ 排序字段 '{field_name}' 未找到")
                continue

            sort_spec = {"field_id": field_id, "desc": direction == 'desc'}
            sort_specs.append(sort_spec)

        return sort_specs if sort_specs else None

    def _build_group_info(self, group_by: str, field_mapping: Dict[str, str]) -> Optional[List[Dict]]:
        """构建分组信息"""
        field_id = field_mapping.get(group_by)
        if not field_id:
            print(f"     ⚠️ 分组字段 '{group_by}' 未找到")
            return None

        return [{"field_id": field_id, "desc": False}]

    def _convert_operator(self, operator: str) -> str:
        """转换操作符为飞书API格式"""
        operator_map = {
            'gte': 'isGreaterThanOrEqualTo',
            'lte': 'isLessThanOrEqualTo',
            'gt': 'isGreaterThan',
            'lt': 'isLessThan',
            'eq': 'is',
            'contains': 'contains',
            'not_contains': 'doesNotContain',
            'is_empty': 'isEmpty',
            'is_not_empty': 'isNotEmpty',
        }
        return operator_map.get(operator, 'is')

    # ...existing code...


def test_bitable_connection(config: FeishuBitableConfig) -> bool:
    """测试多维表格连接"""
    try:
        connector = FeishuBitableConnector(config)
        tables = connector.list_tables()
        print(f"✅ 多维表格连接测试成功")
        print(f"   当前表格数量: {len(tables)}")
        for table in tables:
            print(f"   - {table.get('name', 'Unknown')} ({table.get('table_id', 'Unknown')})")
        return True

    except Exception as e:
        print(f"❌ 多维表格连接测试失败: {e}")
        return False


if __name__ == "__main__":
    print("飞书多维表格连接器模块")

    # 字段类型参考
    field_types = {
        1: "单行文本",
        2: "数字",
        3: "单选",
        4: "多选",
        5: "日期",
        7: "复选框",
        11: "人员",
        13: "电话号码",
        15: "超链接",
        17: "附件",
        18: "单向关联",
        20: "公式",
        21: "双向关联",
        22: "地理位置",
        23: "群组",
        1001: "创建时间",
        1002: "最后更新时间",
        1003: "创建人",
        1004: "修改人",
        1005: "自动编号",
    }

    print("\n📋 支持的字段类型:")
    for type_id, type_name in field_types.items():
        print(f"   {type_id}: {type_name}")
