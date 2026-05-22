"""High-level paper update notification workflow."""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

from ..terminal import debug, key_values, print, success


class FeishuNotificationServiceMixin:
    def notify_paper_updates(
        self, update_stats: Dict[str, Any], papers_by_field: Dict[str, List[Dict]], table_links: Dict[str, str] = None
    ) -> bool:
        """发送论文更新通知到所有群聊

        Args:
            update_stats: 更新统计信息
            papers_by_field: 按领域分组的论文数据
            table_links: 多维表格链接映射 {领域名: 表格链接}

        Returns:
            是否成功发送到至少一个群聊
        """
        if not self.chat_config.enabled:
            debug("ℹ️ 群聊通知功能已禁用")
            return False

        # 检查是否有足够的更新需要通知
        total_new = sum(stats.get('new_count', 0) for stats in update_stats.values())
        if total_new < self.chat_config.min_papers_threshold:
            debug(f"ℹ️ 新增论文数量({total_new})低于通知阈值({self.chat_config.min_papers_threshold})，跳过通知")
            return False

        print("📢 开始发送论文更新通知...")
        key_values("通知统计", {"新增论文": f"{total_new} 篇", "领域数": len(update_stats)})

        # 生成推荐论文
        recommended_papers = self._select_recommended_papers(papers_by_field)

        # 获取群聊列表
        chats = self.get_bot_chats()
        if not chats:
            print("❌ 没有找到可发送的群聊")
            return False
        chats = self._filter_target_chats(chats)
        if not chats:
            print("⚠️ 未匹配到通知目标群聊，请检查 feishu.chat_notification.target_chat_ids")
            return False

        # 创建消息内容
        try:
            if self.chat_config.message_template in {"text", "simple"}:
                message_content = self.create_simple_text_message(update_stats, recommended_papers, table_links)
            else:
                message_content = self.create_paper_update_message(update_stats, recommended_papers, table_links)
        except Exception as e:
            print(f"⚠️ 创建富文本消息失败，使用简单文本: {e}")
            message_content = self.create_simple_text_message(update_stats, recommended_papers, table_links)

        # 发送到所有群聊
        success_count = 0
        total_chats = 0

        for chat in chats:
            chat_id = chat.get('chat_id')
            chat_name = chat.get('name', '未命名群聊')

            if not chat_id:
                continue

            total_chats += 1
            debug(f"📤 发送通知到: {chat_name}")

            if self.send_message_to_chat(chat_id, message_content):
                success_count += 1

            # 避免发送过快
            if self.chat_config.send_delay_seconds > 0:
                time.sleep(self.chat_config.send_delay_seconds)

        success(f"通知发送完成: {success_count}/{total_chats} 个群聊发送成功")
        return success_count > 0

    def _filter_target_chats(self, chats: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        target_chat_ids = set(self.chat_config.target_chat_ids or ())
        if target_chat_ids:
            return [chat for chat in chats if chat.get('chat_id') in target_chat_ids]
        if self.chat_config.send_to_all_chats:
            return chats
        return []

    def _select_recommended_papers(self, papers_by_field: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """为每个领域选择推荐论文"""
        recommended = {}

        for field_name, papers in papers_by_field.items():
            if not papers:
                continue

            # 按相关性评分排序
            sorted_papers = sorted(
                papers, key=lambda p: p.get('relevance_score', p.get('final_score', 0)), reverse=True
            )

            # 选择顶部论文
            top_papers = sorted_papers[: self.chat_config.max_recommended_papers]
            recommended[field_name] = top_papers

        return recommended

    def generate_table_link(self, table_name: str = None, table_id: str = None) -> Optional[str]:
        """生成多维表格访问链接

        Args:
            table_name: 表格名称（用于查找table_id）
            table_id: 表格ID（直接使用）

        Returns:
            表格访问链接，失败时返回None
        """
        try:
            app_token = self.config.app_token
            if not app_token:
                print("⚠️ 未配置多维表格app_token，无法生成表格链接")
                return None

            # 如果没有提供table_id，尝试通过table_name查找
            if not table_id and table_name:
                from .bitable import FeishuBitableConnector

                connector = FeishuBitableConnector(self.config)
                table_id = connector.find_table_by_name(table_name)

                if not table_id:
                    print(f"⚠️ 未找到表格: {table_name}")
                    return None

            if not table_id:
                print("⚠️ 无法确定表格ID，无法生成链接")
                return None

            # 生成飞书多维表格访问链接
            table_link = f"https://feishu.cn/base/{app_token}?table={table_id}&view=vew"
            return table_link

        except Exception as e:
            print(f"⚠️ 生成表格链接失败: {e}")
            return None

    def test_notification(self, test_stats: Dict[str, Any] = None) -> bool:
        """测试通知功能

        Args:
            test_stats: 测试用的统计数据

        Returns:
            是否测试成功
        """
        if test_stats is None:
            test_stats = {
                "移动操作": {"new_count": 3, "total_count": 15, "table_name": "移动操作论文表"},
                "计算机视觉": {"new_count": 2, "total_count": 28, "table_name": "计算机视觉论文表"},
            }

        test_papers = {
            "移动操作": [
                {
                    "title": "Advanced Mobile Manipulation with Deep Reinforcement Learning",
                    "authors_str": "Zhang, J., Wang, L., Chen, M.",
                    "relevance_score": 95.6,
                    "arxiv_id": "2409.12345",
                    "paper_url": "http://arxiv.org/abs/2409.12345",
                }
            ],
            "计算机视觉": [
                {
                    "title": "Real-time Object Detection for Autonomous Navigation",
                    "authors_str": "Li, X., Brown, A., Smith, K.",
                    "relevance_score": 87.3,
                    "arxiv_id": "2409.67890",
                    "paper_url": "http://arxiv.org/abs/2409.67890",
                }
            ],
        }

        # 生成测试表格链接
        test_table_links = {}
        if self.config.app_token:
            test_table_links = {
                "移动操作": f"https://feishu.cn/base/{self.config.app_token}?table=test_table_1",
                "计算机视觉": f"https://feishu.cn/base/{self.config.app_token}?table=test_table_2",
            }

        print("🧪 开始测试群聊通知功能...")
        return self.notify_paper_updates(test_stats, test_papers, test_table_links)
