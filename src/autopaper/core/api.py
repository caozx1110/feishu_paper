"""Factories for core API clients."""

from __future__ import annotations

from typing import Any

from omegaconf import DictConfig

from ..arxiv_core import ArxivAPI, ArxivClientConfig
from ..configuration.runtime import ArxivRuntimeSettings


def create_arxiv_api(cfg: DictConfig, **overrides: Any) -> ArxivAPI:
    """Create an ArxivAPI from canonical runtime configuration."""
    download_dir = overrides.pop("download_dir", cfg.get("download", {}).get("download_dir", "downloads"))
    settings = ArxivRuntimeSettings.from_config(cfg)
    client_config = ArxivClientConfig.from_runtime_settings(settings)
    return ArxivAPI(download_dir=download_dir, client_config=client_config, **overrides)
