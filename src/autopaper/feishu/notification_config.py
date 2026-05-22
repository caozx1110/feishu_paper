"""Configuration for Feishu chat notifications."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass
class ChatNotificationConfig:
    """群聊通知配置类"""

    enabled: bool = False
    notify_on_update: bool = True
    notify_on_new_papers: bool = True
    min_papers_threshold: int = 1  # 最少论文数量才发送通知
    max_recommended_papers: int = 1  # 每个领域推荐的论文数量
    message_template: str = "default"  # 消息模板类型
    target_chat_ids: Tuple[str, ...] = ()  # 为空时按 send_to_all_chats 决定目标
    send_to_all_chats: bool = False
    send_delay_seconds: float = 0.5
    include_table_links: bool = True
    max_title_chars: int = 100
    max_authors_chars: int = 80
