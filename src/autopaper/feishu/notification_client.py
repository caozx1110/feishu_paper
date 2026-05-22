"""Low-level Feishu chat API operations."""

from __future__ import annotations

import json
import time
from typing import Any, Dict, List

import requests

from ..terminal import debug, debug_table, print, success
from .errors import FeishuBitableAPIError


class FeishuChatClientMixin:
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """发送API请求"""
        url = f"{self.config.base_url}/{endpoint}"

        for attempt in range(self.config.max_retries):
            try:
                response = self.session.request(method, url, timeout=self.config.timeout, **kwargs)

                result = response.json()

                if result.get('code') == 0:
                    return result.get('data', {})
                elif result.get('code') == 99991663:  # token过期
                    debug("🔄 检测到token过期，尝试刷新...")
                    if self._refresh_token_if_needed():
                        debug("✅ token刷新成功，重试请求...")
                        continue
                    else:
                        raise FeishuBitableAPIError(
                            f"Token已过期且刷新失败: {result.get('msg', 'Unknown error')}", result.get('code'), result
                        )
                else:
                    raise FeishuBitableAPIError(
                        f"API请求失败: {result.get('msg', 'Unknown error')}", result.get('code'), result
                    )

            except requests.exceptions.RequestException as e:
                if attempt == self.config.max_retries - 1:
                    raise FeishuBitableAPIError(f"网络请求失败: {str(e)}")
                time.sleep(self.config.retry_delay)

    def _refresh_token_if_needed(self) -> bool:
        """刷新token（如果需要）"""
        if self.config.token_type == "tenant" and self.config.app_id and self.config.app_secret:
            try:
                from .bitable import FeishuBitableConnector

                connector = FeishuBitableConnector(self.config)
                new_token = connector.get_tenant_access_token()
                self.config.tenant_access_token = new_token

                # 更新session header
                self.session.headers.update({'Authorization': f'Bearer {new_token}'})
                return True
            except Exception as e:
                print(f"⚠️ token刷新失败: {e}")
                return False
        return False

    def get_bot_chats(self) -> List[Dict[str, Any]]:
        """获取机器人所在的所有群聊"""
        try:
            # 获取机器人参与的群聊列表
            endpoint = "im/v1/chats"
            params = {"page_size": 100, "membership": "member"}  # 机器人作为成员的群聊

            result = self._make_request('GET', endpoint, params=params)
            chats = result.get('items', [])

            debug(f"🔍 发现 {len(chats)} 个机器人参与的群聊")
            if chats:
                debug_table(
                    "机器人群聊",
                    ["群聊名", "类型", "Chat ID"],
                    [
                        (
                            chat.get('name', '未命名群聊'),
                            chat.get('chat_type', 'unknown'),
                            chat.get('chat_id', ''),
                        )
                        for chat in chats
                    ],
                )

            return chats

        except Exception as e:
            print(f"❌ 获取群聊列表失败: {e}")
            return []

    def build_message_payload(self, chat_id: str, message_content: Dict[str, Any]) -> Dict[str, Any]:
        """Build the Feishu ``im/v1/messages`` payload without sending it."""
        msg_type = message_content.get("msg_type", "text")
        content = message_content.get("content", {})
        if not isinstance(content, dict):
            raise ValueError("message content must be a dict")
        if msg_type == "interactive":
            self._validate_interactive_card(content)
        elif msg_type == "text" and not isinstance(content.get("text", ""), str):
            raise ValueError("text message content.text must be a string")

        return {
            "receive_id": chat_id,
            "msg_type": msg_type,
            "content": json.dumps(content, ensure_ascii=False),
        }

    @staticmethod
    def _validate_interactive_card(content: Dict[str, Any]) -> None:
        if not isinstance(content, dict):
            raise ValueError("interactive content must be a dict")
        if not isinstance(content.get("elements"), list) or not content["elements"]:
            raise ValueError("interactive card requires non-empty elements")
        header = content.get("header")
        if not isinstance(header, dict) or "title" not in header:
            raise ValueError("interactive card requires header.title")

    def send_message_to_chat(self, chat_id: str, message_content: Dict[str, Any]) -> bool:
        """向指定群聊发送消息

        Args:
            chat_id: 群聊ID
            message_content: 消息内容，包含msg_type和content

        Returns:
            是否发送成功
        """
        try:
            endpoint = "im/v1/messages"
            params = {"receive_id_type": "chat_id"}

            payload = self.build_message_payload(chat_id, message_content)

            result = self._make_request('POST', endpoint, json=payload, params=params)

            if result:
                success(f"消息发送成功到群聊: {chat_id}")
                return True
            else:
                print(f"❌ 消息发送失败到群聊: {chat_id}")
                return False

        except Exception as e:
            print(f"❌ 发送消息到群聊 {chat_id} 失败: {e}")
            return False
