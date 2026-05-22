"""Public Feishu chat notification facade."""

from __future__ import annotations

import requests

from ..terminal import debug
from .config import FeishuBitableConfig
from .notification_client import FeishuChatClientMixin
from .notification_config import ChatNotificationConfig
from .notification_messages import FeishuMessageBuilderMixin
from .notification_service import FeishuNotificationServiceMixin


class FeishuChatNotifier(FeishuChatClientMixin, FeishuMessageBuilderMixin, FeishuNotificationServiceMixin):
    """飞书群聊通知器"""

    def __init__(self, config: FeishuBitableConfig, chat_config: ChatNotificationConfig = None):
        """初始化飞书群聊通知器"""
        self.config = config
        self.chat_config = chat_config or ChatNotificationConfig()
        self.session = requests.Session()
        self.session.headers.update(
            {'Content-Type': 'application/json; charset=utf-8', 'Authorization': f'Bearer {config.access_token}'}
        )

        debug(f"🤖 飞书群聊通知器已初始化，token类型: {config.token_type}")


def create_chat_notifier_from_config(cfg) -> FeishuChatNotifier:
    """从配置创建群聊通知器"""
    from .config import FeishuBitableConfig

    # 创建基础配置
    feishu_config = FeishuBitableConfig.from_hydra_config(cfg)

    # 创建聊天配置
    feishu_cfg = cfg.get('feishu', {})
    chat_cfg = feishu_cfg.get('chat_notification', {})

    chat_config = ChatNotificationConfig(
        enabled=chat_cfg.get('enabled', False),
        notify_on_update=chat_cfg.get('notify_on_update', True),
        notify_on_new_papers=chat_cfg.get('notify_on_new_papers', True),
        min_papers_threshold=chat_cfg.get('min_papers_threshold', 1),
        max_recommended_papers=chat_cfg.get('max_recommended_papers', 1),
        message_template=chat_cfg.get('message_template', 'default'),
        target_chat_ids=tuple(chat_cfg.get('target_chat_ids', []) or ()),
        send_to_all_chats=chat_cfg.get('send_to_all_chats', False),
        send_delay_seconds=chat_cfg.get('send_delay_seconds', 0.5),
        include_table_links=chat_cfg.get('include_table_links', True),
        max_title_chars=chat_cfg.get('max_title_chars', 100),
        max_authors_chars=chat_cfg.get('max_authors_chars', 80),
    )

    return FeishuChatNotifier(feishu_config, chat_config)
