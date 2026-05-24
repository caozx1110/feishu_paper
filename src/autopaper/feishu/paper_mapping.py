"""Mapping parsed arXiv papers to Feishu Bitable field payloads."""

from __future__ import annotations

from typing import Any, Dict, List

from .dates import to_feishu_timestamp_millis


class FeishuPaperMappingMixin:
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
                timestamp = to_feishu_timestamp_millis(value)
                if timestamp is not None:
                    formatted_data[key] = timestamp
                else:
                    formatted_data[key] = value

            elif key in ["PDF链接", "论文链接"] and value:
                # 超链接字段需要特殊格式
                formatted_data[key] = {"link": value, "text": value.split("/")[-1] if "/" in value else value}

            else:
                # 其他字段直接使用
                formatted_data[key] = value

        return formatted_data

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
