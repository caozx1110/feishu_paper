"""Search orchestration independent from CLI and Feishu sync."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from omegaconf import DictConfig

from ..arxiv import ArxivAPI


@dataclass
class SearchService:
    """Fetch papers using the canonical search config schema."""

    arxiv_api: ArxivAPI

    def fetch(self, cfg: DictConfig) -> list[dict[str, Any]]:
        search_cfg = cfg.get("search", {})
        date_range_cfg = search_cfg.get("date_range", {})
        batch_processing_cfg = search_cfg.get("batch_processing", {})

        if date_range_cfg.get("enabled", False):
            start_date = date_range_cfg.get("start_date", "")
            end_date = date_range_cfg.get("end_date", "")
            if not start_date:
                raise ValueError("日期范围搜索需要指定 start_date")

            print(f"📅 使用日期范围搜索: {start_date} 到 {end_date or '当前日期'}")
            return self.arxiv_api.get_papers_by_date_range(
                start_date=start_date,
                end_date=end_date,
                max_results=search_cfg.get("max_results", 300),
                field_type=search_cfg.get("field", "all"),
                batch_config=batch_processing_cfg,
            )

        return self.arxiv_api.get_recent_papers(
            days=search_cfg.get("days", 7),
            max_results=search_cfg.get("max_results", 300),
            field_type=search_cfg.get("field", "all"),
            batch_config=batch_processing_cfg,
        )
