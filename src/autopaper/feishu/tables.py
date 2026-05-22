"""Feishu Bitable table discovery and setup operations."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..terminal import print


class FeishuTableMixin:
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

    def find_table_by_name(self, table_name: str) -> Optional[str]:
        """根据表格名称查找表格ID"""
        tables = self.list_tables()
        for table in tables:
            if table.get('name') == table_name:
                return table.get('table_id')
        return None

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
