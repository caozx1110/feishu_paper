"""arXiv result parsing helpers."""

from __future__ import annotations

from typing import Any, Dict, Optional

import arxiv


class ArxivParsingMixin:
    def _parse_arxiv_result(self, result: arxiv.Result) -> Optional[Dict[str, Any]]:
        """解析arxiv.Result对象为论文信息字典"""
        try:
            return {
                "title": result.title.strip(),
                "authors": [author.name for author in result.authors],
                "authors_str": ", ".join([author.name for author in result.authors]),
                "summary": result.summary.strip(),
                "published_date": result.published,
                "updated_date": result.updated if result.updated else result.published,
                "paper_url": result.entry_id,
                "pdf_url": result.pdf_url,
                "categories": [cat for cat in result.categories],
                "categories_str": ", ".join(result.categories),
                "arxiv_id": result.entry_id.split("/")[-1],
                "primary_category": result.primary_category,
                "comment": result.comment if result.comment else "",
                "journal_ref": result.journal_ref if result.journal_ref else "",
                "doi": result.doi if result.doi else "",
            }
        except Exception as e:
            print(f"解析论文信息时出错: {e}")
            return None
