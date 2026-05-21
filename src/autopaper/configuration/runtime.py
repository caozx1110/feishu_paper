"""Typed accessors for runtime configuration sections."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from omegaconf import DictConfig, OmegaConf


def _section(cfg: Mapping[str, Any] | DictConfig, key: str) -> Mapping[str, Any]:
    value = cfg.get(key, {}) if cfg else {}
    if isinstance(value, DictConfig):
        return OmegaConf.to_container(value, resolve=True) or {}
    return value or {}


@dataclass(frozen=True)
class ArxivRuntimeSettings:
    """ArXiv API client behavior controlled by configuration."""

    request_timeout: float | tuple[float, float] = (5.0, 30.0)
    initial_page_size: int = 500
    page_sizes: tuple[int, ...] = (500, 250, 100, 50, 10)
    initial_delay_seconds: float = 1.0
    retry_delay_seconds: float = 3.0
    num_retries: int = 3
    max_empty_pages: int = 3
    field_categories: dict[str, list[str]] = field(default_factory=dict)

    @classmethod
    def from_config(cls, cfg: Mapping[str, Any] | DictConfig) -> "ArxivRuntimeSettings":
        arxiv_cfg = _section(cfg, "arxiv")
        timeout = _parse_timeout(arxiv_cfg.get("request_timeout", (5, 30)))
        env_timeout = os.getenv("ARXIV_REQUEST_TIMEOUT")
        if env_timeout:
            timeout = _parse_timeout(env_timeout, fallback=timeout)

        field_categories = arxiv_cfg.get("field_categories", {}) or {}
        field_categories = {str(key): list(value) for key, value in field_categories.items()}

        page_sizes = arxiv_cfg.get("page_sizes", (500, 250, 100, 50, 10))
        return cls(
            request_timeout=timeout,
            initial_page_size=int(arxiv_cfg.get("initial_page_size", 500)),
            page_sizes=tuple(int(size) for size in page_sizes),
            initial_delay_seconds=float(arxiv_cfg.get("initial_delay_seconds", 1.0)),
            retry_delay_seconds=float(arxiv_cfg.get("retry_delay_seconds", 3.0)),
            num_retries=int(arxiv_cfg.get("num_retries", 3)),
            max_empty_pages=int(arxiv_cfg.get("max_empty_pages", 3)),
            field_categories=field_categories,
        )


@dataclass(frozen=True)
class NetworkSettings:
    """Network proxy behavior controlled by configuration."""

    proxy_mode: str = "auto"
    proxy_url: str = ""
    proxy_auto_host: str = "127.0.0.1"
    proxy_auto_port: int = 7890
    proxy_probe_timeout_seconds: float = 0.2
    no_proxy: str = "localhost,127.0.0.1,::1"

    @classmethod
    def from_config(cls, cfg: Mapping[str, Any] | DictConfig) -> "NetworkSettings":
        runtime_cfg = _section(cfg, "runtime")
        network_cfg = runtime_cfg.get("network", {}) or {}
        proxy_cfg = network_cfg.get("proxy", {}) or {}
        return cls(
            proxy_mode=str(proxy_cfg.get("mode", "auto")),
            proxy_url=str(proxy_cfg.get("url", "")),
            proxy_auto_host=str(proxy_cfg.get("auto_host", "127.0.0.1")),
            proxy_auto_port=int(proxy_cfg.get("auto_port", 7890)),
            proxy_probe_timeout_seconds=float(proxy_cfg.get("probe_timeout_seconds", 0.2)),
            no_proxy=str(network_cfg.get("no_proxy", "localhost,127.0.0.1,::1")),
        )


@dataclass(frozen=True)
class HealthcheckSettings:
    """Health-check endpoints and timeouts."""

    arxiv_url: str = "https://export.arxiv.org/api/query?search_query=all:robot&start=0&max_results=1"
    timeout_seconds: float = 20.0

    @classmethod
    def from_config(cls, cfg: Mapping[str, Any] | DictConfig) -> "HealthcheckSettings":
        runtime_cfg = _section(cfg, "runtime")
        health_cfg = runtime_cfg.get("healthcheck", {}) or {}
        return cls(
            arxiv_url=str(
                health_cfg.get(
                    "arxiv_url",
                    "https://export.arxiv.org/api/query?search_query=all:robot&start=0&max_results=1",
                )
            ),
            timeout_seconds=float(health_cfg.get("timeout_seconds", 20.0)),
        )


@dataclass(frozen=True)
class FeishuEnvPolicy:
    """Feishu environment variable names required by health checks."""

    required: tuple[str, ...] = ("FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_BITABLE_APP_TOKEN")
    token_any_of: tuple[str, ...] = ("FEISHU_USER_ACCESS_TOKEN", "FEISHU_TENANT_ACCESS_TOKEN")
    placeholder_markers: tuple[str, ...] = ("xxxx", "xxxxxxxx")

    @classmethod
    def from_config(cls, cfg: Mapping[str, Any] | DictConfig) -> "FeishuEnvPolicy":
        runtime_cfg = _section(cfg, "runtime")
        env_cfg = runtime_cfg.get("env", {}) or {}
        feishu_cfg = env_cfg.get("feishu", {}) or {}
        return cls(
            required=tuple(feishu_cfg.get("required", cls.required)),
            token_any_of=tuple(feishu_cfg.get("token_any_of", cls.token_any_of)),
            placeholder_markers=tuple(feishu_cfg.get("placeholder_markers", cls.placeholder_markers)),
        )


@dataclass(frozen=True)
class RuntimeSettings:
    arxiv: ArxivRuntimeSettings
    network: NetworkSettings
    healthcheck: HealthcheckSettings
    feishu_env: FeishuEnvPolicy

    @classmethod
    def from_config(cls, cfg: Mapping[str, Any] | DictConfig) -> "RuntimeSettings":
        return cls(
            arxiv=ArxivRuntimeSettings.from_config(cfg),
            network=NetworkSettings.from_config(cfg),
            healthcheck=HealthcheckSettings.from_config(cfg),
            feishu_env=FeishuEnvPolicy.from_config(cfg),
        )


def _parse_timeout(value: Any, fallback: Any = (5.0, 30.0)) -> float | tuple[float, float]:
    if isinstance(value, Sequence) and not isinstance(value, str):
        parts = list(value)
    else:
        parts = [part.strip() for part in str(value).split(",")]

    try:
        if len(parts) == 1:
            timeout: float | tuple[float, float] = float(parts[0])
        elif len(parts) == 2:
            timeout = (float(parts[0]), float(parts[1]))
        else:
            return fallback
    except (TypeError, ValueError):
        return fallback

    if isinstance(timeout, tuple):
        return timeout if timeout[0] > 0 and timeout[1] > 0 else fallback
    return timeout if timeout > 0 else fallback
