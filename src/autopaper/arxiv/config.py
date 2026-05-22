"""Runtime configuration for the arXiv client."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Tuple

from ..configuration.runtime import ArxivRuntimeSettings
from .categories import default_field_categories

@dataclass(frozen=True)
class ArxivClientConfig:
    """Runtime knobs for the arXiv client.

    Normal package execution passes this from ``default.yaml``. The defaults
    below keep the public Python API usable when the class is constructed
    directly in notebooks or third-party code.
    """

    request_timeout: Any = (5.0, 30.0)
    initial_page_size: int = 500
    page_sizes: Tuple[int, ...] = (500, 250, 100, 50, 10)
    initial_delay_seconds: float = 1.0
    retry_delay_seconds: float = 3.0
    num_retries: int = 3
    max_empty_pages: int = 3
    field_categories: Dict[str, List[str]] = field(
        default_factory=default_field_categories
    )

    @classmethod
    def from_runtime_settings(cls, settings: ArxivRuntimeSettings) -> "ArxivClientConfig":
        return cls(
            request_timeout=settings.request_timeout,
            initial_page_size=settings.initial_page_size,
            page_sizes=tuple(settings.page_sizes),
            initial_delay_seconds=settings.initial_delay_seconds,
            retry_delay_seconds=settings.retry_delay_seconds,
            num_retries=settings.num_retries,
            max_empty_pages=settings.max_empty_pages,
            field_categories=dict(settings.field_categories) or cls().field_categories,
        )

    @classmethod
    def from_mapping(cls, config: Mapping[str, Any]) -> "ArxivClientConfig":
        settings = ArxivRuntimeSettings.from_config({"arxiv": config})
        return cls.from_runtime_settings(settings)
