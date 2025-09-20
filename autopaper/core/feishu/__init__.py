"""
飞书功能模块

包含飞书API的所有功能实现，包括：
- 配置管理
- 多维表格操作
- 消息通知
- 数据同步
"""

from .config import FeishuConfig, FeishuAPIError, FieldType, FIELD_TYPE_NAMES
from .connector import FeishuConnector
from .bitable import BitableManager
from .notification import ChatNotifier
from .sync import SyncManager

__all__ = [
    "FeishuConfig",
    "FeishuAPIError",
    "FieldType",
    "FIELD_TYPE_NAMES",
    "FeishuConnector",
    "BitableManager",
    "ChatNotifier",
    "SyncManager",
]
