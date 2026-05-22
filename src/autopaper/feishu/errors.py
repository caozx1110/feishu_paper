"""Feishu API exceptions."""

from __future__ import annotations

class FeishuBitableAPIError(Exception):
    """飞书多维表格API异常类"""

    def __init__(self, message: str, code: int = None, response: dict = None):
        self.message = message
        self.code = code
        self.response = response
        super().__init__(self.message)
