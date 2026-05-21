"""Network configuration helpers."""

from __future__ import annotations

import os
import socket
from typing import Mapping

from omegaconf import DictConfig

from .runtime import HealthcheckSettings, NetworkSettings


def configure_network(cfg: Mapping | DictConfig) -> None:
    """Configure proxy environment variables from runtime config when unset."""
    settings = NetworkSettings.from_config(cfg)
    if any(os.getenv(name) for name in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY")):
        os.environ.setdefault("no_proxy", settings.no_proxy)
        return

    proxy_url = settings.proxy_url
    if not proxy_url and settings.proxy_mode == "auto":
        if _port_open(settings.proxy_auto_host, settings.proxy_auto_port, settings.proxy_probe_timeout_seconds):
            proxy_url = f"http://{settings.proxy_auto_host}:{settings.proxy_auto_port}"

    if proxy_url:
        os.environ["http_proxy"] = proxy_url
        os.environ["https_proxy"] = proxy_url
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url

    os.environ.setdefault("no_proxy", settings.no_proxy)


def healthcheck_url(cfg: Mapping | DictConfig) -> str:
    return HealthcheckSettings.from_config(cfg).arxiv_url


def _port_open(host: str, port: int, timeout: float) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False
