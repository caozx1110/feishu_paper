"""Public arXiv API facade."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

import arxiv

from ..configuration.runtime import ArxivRuntimeSettings
from .config import ArxivClientConfig
from .download import ArxivDownloadMixin
from .parsing import ArxivParsingMixin
from .query import ArxivQueryMixin
from .search import ArxivSearchMixin


class ArxivAPI(ArxivSearchMixin, ArxivDownloadMixin, ArxivQueryMixin, ArxivParsingMixin):
    """ArXiv API 交互类 - 使用官方arxiv库"""

    def __init__(
        self,
        timeout: Any = None,
        download_dir: str = "downloads",
        client_config: ArxivClientConfig | ArxivRuntimeSettings | Mapping[str, Any] | None = None,
    ):
        """初始化ArXiv API客户端"""
        self.config = self._coerce_client_config(client_config)
        timeout = timeout if timeout is not None else self.config.request_timeout
        self.timeout = self._resolve_timeout(timeout)
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)

        self.initial_page_size = self.config.initial_page_size
        self.field_mappings = self.config.field_categories
        self.client = self._create_client(
            page_size=self.initial_page_size,
            delay_seconds=self.config.initial_delay_seconds,
        )

    @staticmethod
    def _coerce_client_config(
        client_config: ArxivClientConfig | ArxivRuntimeSettings | Mapping[str, Any] | None,
    ) -> ArxivClientConfig:
        if client_config is None:
            return ArxivClientConfig()
        if isinstance(client_config, ArxivClientConfig):
            return client_config
        if isinstance(client_config, ArxivRuntimeSettings):
            return ArxivClientConfig.from_runtime_settings(client_config)
        return ArxivClientConfig.from_mapping(client_config)

    @staticmethod
    def _resolve_timeout(default_timeout: Any) -> Any:
        """读取ArXiv请求超时配置，避免网络异常时被系统TCP超时拖住。"""
        raw_timeout = os.getenv("ARXIV_REQUEST_TIMEOUT")
        if not raw_timeout:
            return default_timeout

        try:
            timeout_parts = [part.strip() for part in raw_timeout.split(",")]
            if len(timeout_parts) == 1:
                timeout = float(timeout_parts[0])
            elif len(timeout_parts) == 2:
                timeout = (float(timeout_parts[0]), float(timeout_parts[1]))
            else:
                raise ValueError
        except ValueError:
            print(f"⚠️  ARXIV_REQUEST_TIMEOUT={raw_timeout!r} 无效，使用默认 {default_timeout} 秒")
            return default_timeout

        if isinstance(timeout, tuple):
            invalid_timeout = timeout[0] <= 0 or timeout[1] <= 0
        else:
            invalid_timeout = timeout <= 0

        if invalid_timeout:
            print(f"⚠️  ARXIV_REQUEST_TIMEOUT={raw_timeout!r} 必须大于0，使用默认 {default_timeout} 秒")
            return default_timeout

        return timeout

    def _create_client(self, page_size: int, delay_seconds: float) -> arxiv.Client:
        client = arxiv.Client(page_size=page_size, delay_seconds=delay_seconds, num_retries=self.config.num_retries)
        original_get = client._session.get
        request_timeout = self.timeout

        def get_with_timeout(url, **kwargs):
            kwargs.setdefault("timeout", request_timeout)
            return original_get(url, **kwargs)

        client._session.get = get_with_timeout
        return client
