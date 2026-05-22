"""Feishu Bitable record reads and writes."""

from __future__ import annotations

import os
from typing import Any, Dict, List


class FeishuRecordMixin:
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

        result = self._make_request('POST', endpoint, json=payload)
        items = result.get('items', [])
        return len(items) > 0
