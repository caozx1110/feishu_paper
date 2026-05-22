"""Keyword config utilities."""

from __future__ import annotations

from typing import Any

from omegaconf import DictConfig


def load_keywords_from_config(cfg: DictConfig) -> tuple[list[str], list[str], list[str], Any]:
    """Load interest, exclude, raw interest, and required keyword sections."""
    if hasattr(cfg, "keywords"):
        raw_interest_keywords = cfg.keywords.get("interest_keywords", [])
        raw_exclude_keywords = cfg.keywords.get("exclude_keywords", [])
    else:
        raw_interest_keywords = cfg.get("interest_keywords", [])
        raw_exclude_keywords = cfg.get("exclude_keywords", [])

    raw_interest_keywords = _as_list(raw_interest_keywords)
    raw_exclude_keywords = _as_list(raw_exclude_keywords)

    interest_keywords = filter_keywords(raw_interest_keywords)
    exclude_keywords = filter_keywords(raw_exclude_keywords)
    required_keywords_config = cfg.get("required_keywords", {})

    return interest_keywords, exclude_keywords, raw_interest_keywords, required_keywords_config


def filter_keywords(keywords: list[str]) -> list[str]:
    """Drop empty/comment rows and de-duplicate keyword lists while preserving order."""
    filtered = []
    seen = set()
    for keyword in keywords or []:
        if not keyword or not str(keyword).strip():
            continue
        keyword = str(keyword).strip()
        if keyword.startswith("#"):
            continue
        key = keyword.casefold()
        if key in seen:
            continue
        seen.add(key)
        filtered.append(keyword)
    return filtered


def _as_list(value: Any) -> list[str]:
    if not value:
        return []
    if hasattr(value, "_content"):
        return list(value)
    if isinstance(value, list):
        return value
    return list(value)
