"""Query and category normalization for arXiv searches."""

from __future__ import annotations

from datetime import datetime
from typing import List


class ArxivQueryMixin:
    def _build_search_query(
        self, query: str = None, categories: List[str] = None, date_from: datetime = None, date_to: datetime = None
    ) -> str:
        """构建搜索查询字符串"""
        query_parts = []

        # 添加自定义查询
        if query:
            query_parts.append(f"({query})")

        # 添加分类查询
        if categories:
            category_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query_parts.append(f"({category_query})")

        # 添加日期范围查询
        if date_from or date_to:
            date_parts = []

            if date_from:
                # 将datetime转换为YYYYMMDD格式
                date_from_str = date_from.strftime("%Y%m%d")
                date_parts.append(f"submittedDate:[{date_from_str}0000")

            if date_to:
                # 将datetime转换为YYYYMMDD格式
                date_to_str = date_to.strftime("%Y%m%d")
                if not date_from:
                    date_parts.append(f"submittedDate:[19910801 TO {date_to_str}2359]")
                else:
                    # 闭合之前的范围
                    date_parts[0] = f"submittedDate:[{date_from_str}0000 TO {date_to_str}2359]"
            elif date_from:
                # 只有开始日期，到当前日期
                current_date = datetime.now().strftime("%Y%m%d")
                date_parts[0] = f"submittedDate:[{date_from_str}0000 TO {current_date}2359]"

            if date_parts:
                query_parts.extend(date_parts)

        # 合并查询部分
        search_query = " AND ".join(query_parts) if query_parts else "all:*"

        return search_query

    def _get_field_categories(self, field_type) -> List[str]:
        """
        根据领域类型获取分类列表，支持交集/并集操作

        支持的格式：
        - 单个字符串: "ai", "robotics"
        - 并集操作: "ai+robotics" 或 ["ai", "robotics"]
        - 交集操作: "ai&robotics" (目前ArXiv API不直接支持，返回并集)
        - 直接分类: "cs.AI" 或 ["cs.AI", "cs.LG"]
        """
        field_mappings = self.field_mappings

        # 如果是列表，处理列表中的每个元素
        if isinstance(field_type, list):
            all_categories = []
            for field in field_type:
                all_categories.extend(self._parse_single_field(field, field_mappings))
            return list(set(all_categories))  # 去重

        # 如果是字符串，检查是否包含运算符
        if isinstance(field_type, str):
            return self._parse_field_string(field_type, field_mappings)

        # 默认返回all
        return field_mappings.get("all", [])

    def _parse_field_string(self, field_str: str, field_mappings: dict) -> List[str]:
        """解析字段字符串，支持运算符"""
        field_str = field_str.strip()

        # 检查并集运算符 (+, |, or)
        if "+" in field_str or "|" in field_str or " or " in field_str.lower():
            # 分割并处理各个部分
            separators = ["+", "|", " or ", " OR "]
            parts = [field_str]

            for sep in separators:
                new_parts = []
                for part in parts:
                    new_parts.extend(part.split(sep))
                parts = new_parts

            all_categories = []
            for part in parts:
                part = part.strip()
                if part:
                    all_categories.extend(self._parse_single_field(part, field_mappings))

            return list(set(all_categories))  # 去重

        # 检查交集运算符 (&, and) - 注意：ArXiv API不直接支持交集
        elif "&" in field_str or " and " in field_str.lower():
            print("⚠️  注意：ArXiv API不直接支持分类交集查询，将转换为并集查询")
            # 将交集转换为并集处理
            separators = ["&", " and ", " AND "]
            parts = [field_str]

            for sep in separators:
                new_parts = []
                for part in parts:
                    new_parts.extend(part.split(sep))
                parts = new_parts

            all_categories = []
            for part in parts:
                part = part.strip()
                if part:
                    all_categories.extend(self._parse_single_field(part, field_mappings))

            return list(set(all_categories))

        # 单个字段
        else:
            return self._parse_single_field(field_str, field_mappings)

    def _parse_single_field(self, field: str, field_mappings: dict) -> List[str]:
        """解析单个字段"""
        field = field.strip()

        # 直接是ArXiv分类
        if field.startswith(("cs.", "stat.", "math.", "physics.", "eess.", "q-bio.", "quant-ph", "cond-mat")):
            return [field]

        # 查找预定义映射
        if field.lower() in field_mappings:
            return field_mappings[field.lower()]

        # 如果不在映射中，假设是自定义分类
        print(f"⚠️  未识别的领域类型: {field}，将尝试作为ArXiv分类使用")
        return [field]
