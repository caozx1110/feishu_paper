"""Feishu Bitable field helpers."""

from __future__ import annotations

from typing import Any, Dict


class FeishuFieldMixin:
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
