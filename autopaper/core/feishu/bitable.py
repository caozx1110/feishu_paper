"""
飞书多维表格管理器

负责多维表格的创建、管理、数据操作等功能。
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from .config import FeishuConfig, FeishuAPIError, FieldType
from .connector import FeishuConnector

logger = logging.getLogger(__name__)


class BitableManager:
    """多维表格管理器"""

    def __init__(self, config: FeishuConfig):
        """
        初始化多维表格管理器

        Args:
            config: 飞书配置对象
        """
        self.config = config
        self.connector = FeishuConnector(config)

        if not config.app_token:
            logger.warning("⚠️ 未配置app_token，部分功能可能无法使用")

    def create_table(self, table_name: str, fields: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """在多维表格中创建新的数据表

        Args:
            table_name: 表格名称
            fields: 字段定义列表，如果为None则创建默认字段

        Returns:
            创建的表格信息
        """
        if not self.config.app_token:
            raise FeishuAPIError("创建表格需要配置app_token")

        if fields is None:
            fields = self._get_default_fields()

        payload = {"table": {"name": table_name, "default_view_name": "表格视图", "fields": fields}}

        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables"
        result = self.connector.make_request("POST", endpoint, json=payload)

        logger.info(f"✅ 成功创建表格: {table_name}")
        return result

    def _get_default_fields(self) -> List[Dict[str, Any]]:
        """获取默认字段定义"""
        return [
            {"field_name": "标题", "type": FieldType.TEXT},
            {"field_name": "创建时间", "type": FieldType.CREATED_TIME},
        ]

    def create_papers_table(self, table_name: str = "论文信息表") -> Dict[str, Any]:
        """创建论文信息表"""
        fields = [
            {"field_name": "ArXiv ID", "type": FieldType.TEXT},
            {"field_name": "标题", "type": FieldType.TEXT},
            {"field_name": "作者", "type": FieldType.MULTI_SELECT},
            {"field_name": "摘要", "type": FieldType.TEXT},
            {"field_name": "分类", "type": FieldType.MULTI_SELECT},
            {
                "field_name": "发布日期",
                "type": FieldType.DATE,
                "property": {"date_formatter": "yyyy/MM/dd", "auto_fill": False},
            },
            {
                "field_name": "更新日期",
                "type": FieldType.DATE,
                "property": {"date_formatter": "yyyy/MM/dd", "auto_fill": False},
            },
            {"field_name": "PDF链接", "type": FieldType.URL},
            {"field_name": "论文链接", "type": FieldType.URL},
            {"field_name": "同步时间", "type": FieldType.CREATED_TIME},
        ]

        return self.create_table(table_name, fields)

    def create_domain_papers_table(self, table_name: str, research_area: str) -> Dict[str, Any]:
        """为特定研究领域创建论文表格"""
        fields = [
            {"field_name": "ArXiv ID", "type": FieldType.URL},
            {"field_name": "标题", "type": FieldType.TEXT},
            {"field_name": "作者", "type": FieldType.MULTI_SELECT},
            {"field_name": "摘要", "type": FieldType.TEXT},
            {"field_name": "分类", "type": FieldType.MULTI_SELECT},
            {"field_name": "匹配关键词", "type": FieldType.MULTI_SELECT},
            {"field_name": "相关性评分", "type": FieldType.NUMBER, "property": {"formatter": "0.00"}},
            {"field_name": "研究领域", "type": FieldType.MULTI_SELECT},
            {"field_name": "PDF链接", "type": FieldType.URL},
            {"field_name": "必须关键词匹配", "type": FieldType.MULTI_SELECT},
            {
                "field_name": "发布日期",
                "type": FieldType.DATE,
                "property": {"date_formatter": "yyyy/MM/dd", "auto_fill": False},
            },
            {
                "field_name": "更新日期",
                "type": FieldType.DATE,
                "property": {"date_formatter": "yyyy/MM/dd", "auto_fill": False},
            },
            {"field_name": "同步时间", "type": FieldType.CREATED_TIME},
        ]

        return self.create_table(table_name, fields)

    def list_tables(self) -> List[Dict[str, Any]]:
        """获取多维表格中的所有数据表"""
        if not self.config.app_token:
            raise FeishuAPIError("获取表格列表需要配置app_token")

        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables"
        result = self.connector.make_request("GET", endpoint)

        return result.get("items", [])

    def get_table_info(self, table_id: str) -> Dict[str, Any]:
        """获取指定数据表的详细信息"""
        if not self.config.app_token:
            raise FeishuAPIError("获取表格信息需要配置app_token")

        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}"
        result = self.connector.make_request("GET", endpoint)

        return result

    def find_table_by_name(self, table_name: str) -> Optional[str]:
        """根据表格名称查找表格ID"""
        try:
            tables = self.list_tables()
            for table in tables:
                if table.get("name") == table_name:
                    return table.get("table_id")
            return None
        except FeishuAPIError:
            return None

    def get_all_records(self, table_id: str, page_size: int = 500) -> List[Dict[str, Any]]:
        """获取数据表中的所有记录"""
        if not self.config.app_token:
            raise FeishuAPIError("获取记录需要配置app_token")

        all_records = []
        page_token = None

        while True:
            params = {"page_size": page_size}
            if page_token:
                params["page_token"] = page_token

            endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/records"
            result = self.connector.make_request("GET", endpoint, params=params)

            records = result.get("items", [])
            all_records.extend(records)

            page_token = result.get("page_token")
            if not page_token or not result.get("has_more", False):
                break

        return all_records

    def insert_record(self, table_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """向数据表插入新记录

        Args:
            table_id: 表格ID
            fields: 字段数据字典

        Returns:
            插入的记录信息
        """
        if not self.config.app_token:
            raise FeishuAPIError("插入记录需要配置app_token")

        payload = {"fields": fields}

        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/records"
        result = self.connector.make_request("POST", endpoint, json=payload)

        return result

    def batch_insert_records(self, table_id: str, records_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """批量插入记录到指定表格

        Args:
            table_id: 表格ID
            records_data: 记录列表，每个记录是字段数据字典

        Returns:
            批量插入结果
        """
        if not self.config.app_token:
            raise FeishuAPIError("批量插入记录需要配置app_token")

        records = []
        for data in records_data:
            records.append({"fields": data})

        payload = {"records": records}
        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/records/batch_create"

        return self.connector.make_request("POST", endpoint, json=payload)

    def update_record(self, table_id: str, record_id: str, fields: Dict[str, Any]) -> Dict[str, Any]:
        """更新表格记录

        Args:
            table_id: 表格ID
            record_id: 记录ID
            fields: 要更新的字段数据

        Returns:
            更新后的记录信息
        """
        if not self.config.app_token:
            raise FeishuAPIError("更新记录需要配置app_token")

        payload = {"fields": fields}

        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/records/{record_id}"
        result = self.connector.make_request("PUT", endpoint, json=payload)

        return result

    def check_record_exists(self, table_id: str, arxiv_id: str) -> bool:
        """检查记录是否已存在（基于ArXiv ID）

        Args:
            table_id: 表格ID
            arxiv_id: ArXiv ID

        Returns:
            记录是否存在
        """
        try:
            records = self.get_all_records(table_id)

            for record in records:
                fields = record.get("fields", {})
                arxiv_id_field = fields.get("ArXiv ID", "")

                # 处理ArXiv ID字段，可能是字符串或超链接格式
                if isinstance(arxiv_id_field, dict):
                    existing_id = arxiv_id_field.get("text", "")
                else:
                    existing_id = str(arxiv_id_field) if arxiv_id_field else ""

                if existing_id == arxiv_id:
                    return True

            return False
        except FeishuAPIError:
            return False

    def add_field_to_table(
        self, table_id: str, field_name: str, field_type: int, property_config: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """向数据表添加新字段

        Args:
            table_id: 表格ID
            field_name: 字段名称
            field_type: 字段类型
            property_config: 字段属性配置

        Returns:
            添加的字段信息
        """
        if not self.config.app_token:
            raise FeishuAPIError("添加字段需要配置app_token")

        if property_config is None:
            property_config = {}

        payload = {"field_name": field_name, "type": field_type, "property": property_config}

        endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/fields"
        result = self.connector.make_request("POST", endpoint, json=payload)

        return result

    def format_paper_data(self, paper_data: Dict[str, Any]) -> Dict[str, Any]:
        """格式化论文数据以符合飞书API要求

        Args:
            paper_data: 原始论文数据

        Returns:
            格式化后的数据
        """
        formatted_data = {}

        for key, value in paper_data.items():
            if value is None:
                continue

            # 根据字段类型进行格式化
            if key in ["作者", "分类", "匹配关键词", "研究领域", "必须关键词匹配"]:
                # 多选字段
                if isinstance(value, list):
                    formatted_data[key] = value[:20]  # 限制选项数量
                elif isinstance(value, str):
                    formatted_data[key] = [item.strip() for item in value.split(",") if item.strip()][:20]
                else:
                    formatted_data[key] = [str(value)]
            elif key in ["PDF链接", "ArXiv ID"]:
                # 超链接字段
                if isinstance(value, dict):
                    formatted_data[key] = value
                else:
                    formatted_data[key] = {"text": str(value), "link": str(value)}
            elif key in ["发布日期", "更新日期"]:
                # 日期字段（时间戳格式）
                if isinstance(value, datetime):
                    formatted_data[key] = int(value.timestamp() * 1000)
                elif isinstance(value, (int, float)):
                    formatted_data[key] = int(value * 1000) if value < 1e10 else int(value)
                else:
                    # 跳过无效日期
                    continue
            elif key == "相关性评分":
                # 数字字段
                try:
                    formatted_data[key] = float(value) if value else 0.0
                except (ValueError, TypeError):
                    formatted_data[key] = 0.0
            else:
                # 文本字段
                formatted_data[key] = str(value) if value else ""

        return formatted_data

    def get_record_count(self, table_id: str) -> int:
        """获取表格记录数量

        Args:
            table_id: 表格ID

        Returns:
            记录数量
        """
        if not self.config.app_token:
            raise FeishuAPIError("获取记录数需要配置app_token")

        try:
            endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/records"
            response = self.connector.make_request("GET", endpoint, params={"page_size": 1})
            return response.get("total", 0)
        except Exception as e:
            logger.error(f"获取表格记录数失败: {e}")
            return 0

    def get_table_fields(self, table_id: str) -> List[Dict[str, Any]]:
        """获取表格字段信息

        Args:
            table_id: 表格ID

        Returns:
            字段列表
        """
        if not self.config.app_token:
            raise FeishuAPIError("获取表格字段需要配置app_token")

        try:
            endpoint = f"bitable/v1/apps/{self.config.app_token}/tables/{table_id}/fields"
            response = self.connector.make_request("GET", endpoint)
            return response.get("items", [])
        except Exception as e:
            logger.error(f"获取表格字段失败: {e}")
            return []

    def test_connection(self) -> bool:
        """测试连接是否正常

        Returns:
            连接是否成功
        """
        if not self.config.app_token:
            logger.warning("未配置app_token，无法测试连接")
            return False

        try:
            endpoint = f"bitable/v1/apps/{self.config.app_token}/tables"
            response = self.connector.make_request("GET", endpoint, params={"page_size": 1})
            return "items" in response
        except Exception as e:
            logger.error(f"连接测试失败: {e}")
            return False
