"""Configuration for Feishu chat notifications."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ChatNotificationConfig:
    """群聊通知配置类"""

    enabled: bool = True
    notify_on_update: bool = True
    notify_on_new_papers: bool = True
    min_papers_threshold: int = 1  # 最少论文数量才发送通知
    max_recommended_papers: int = 1  # 每个领域推荐的论文数量
    message_template: str = "default"  # 消息模板类型
