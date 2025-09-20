"""
飞书聊天通知器

负责群聊消息的发送和通知功能。
"""

import json
import time
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass
from .config import FeishuConfig, FeishuAPIError
from .connector import FeishuConnector

logger = logging.getLogger(__name__)


@dataclass
class ChatNotificationConfig:
    """群聊通知配置类"""

    enabled: bool = True
    notify_on_update: bool = True
    notify_on_new_papers: bool = True
    min_papers_threshold: int = 1  # 最少论文数量才发送通知
    max_recommended_papers: int = 1  # 每个领域推荐的论文数量
    message_template: str = "default"  # 消息模板类型


class ChatNotifier:
    """飞书群聊通知器"""

    def __init__(self, config: FeishuConfig, chat_config: ChatNotificationConfig = None):
        """
        初始化飞书群聊通知器

        Args:
            config: 飞书配置对象
            chat_config: 聊天通知配置
        """
        self.config = config
        self.chat_config = chat_config or ChatNotificationConfig()
        self.connector = FeishuConnector(config)

        logger.info(f"🤖 飞书群聊通知器已初始化，token类型: {config.token_type}")

    def get_bot_chats(self) -> List[Dict[str, Any]]:
        """获取机器人所在的所有群聊"""
        try:
            endpoint = "im/v1/chats"
            params = {"page_size": 100, "membership": "member"}  # 机器人作为成员的群聊

            result = self.connector.make_request("GET", endpoint, params=params)
            chats = result.get("items", [])

            logger.info(f"🔍 发现 {len(chats)} 个机器人参与的群聊")
            for chat in chats:
                chat_id = chat.get("chat_id", "")
                chat_name = chat.get("name", "未命名群聊")
                chat_type = chat.get("chat_type", "unknown")
                logger.debug(f"   - {chat_name} ({chat_type}): {chat_id}")

            return chats

        except FeishuAPIError as e:
            logger.error(f"❌ 获取群聊列表失败: {e}")
            return []

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

            payload = {
                "receive_id": chat_id,
                "msg_type": message_content.get("msg_type", "text"),
                "content": json.dumps(message_content.get("content", {}), ensure_ascii=False),
            }

            result = self.connector.make_request("POST", endpoint, json=payload, params=params)

            if result:
                logger.debug(f"✅ 消息发送成功到群聊: {chat_id}")
                return True
            else:
                logger.error(f"❌ 消息发送失败到群聊: {chat_id}")
                return False

        except FeishuAPIError as e:
            logger.error(f"❌ 发送消息到群聊 {chat_id} 失败: {e}")
            return False

    def create_paper_update_message(
        self,
        update_stats: Dict[str, Any],
        recommended_papers: Dict[str, List[Dict]],
        table_links: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """创建论文更新通知消息

        Args:
            update_stats: 更新统计信息 {领域名: {新增数量, 总数量, 表格名}}
            recommended_papers: 推荐论文 {领域名: [论文列表]}
            table_links: 多维表格链接 {领域名: 表格链接}

        Returns:
            消息内容字典
        """
        # 构建富文本消息
        elements = []

        # 标题
        elements.append({"tag": "div", "text": {"tag": "lark_md", "content": "📚 **ArXiv论文更新通知**"}})

        # 时间信息
        current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
        elements.append({"tag": "div", "text": {"tag": "plain_text", "content": f"🕒 更新时间: {current_time}"}})

        # 统计信息概览
        total_new = sum(stats.get("new_count", 0) for stats in update_stats.values())
        total_papers = sum(stats.get("total_count", 0) for stats in update_stats.values())

        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": (
                        f"📊 **本次更新概览**\n新增论文: {total_new} 篇\n"
                        f"数据库总计: {total_papers} 篇\n覆盖领域: {len(update_stats)} 个"
                    ),
                },
            }
        )

        # 分隔线
        elements.append({"tag": "hr"})

        # 各领域详细信息
        for field_name, stats in update_stats.items():
            new_count = stats.get("new_count", 0)
            total_count = stats.get("total_count", 0)

            if new_count > 0:
                # 构建领域信息，包含表格链接
                field_content = f"🎯 **{field_name}**\n📈 新增: {new_count} 篇 | 📚 总计: {total_count} 篇"

                # 添加表格链接（如果提供）
                if table_links and field_name in table_links:
                    table_link = table_links[field_name]
                    field_content += f"\n📊 [查看完整表格]({table_link})"

                elements.append({"tag": "div", "text": {"tag": "lark_md", "content": field_content}})

                # 推荐论文
                if field_name in recommended_papers and recommended_papers[field_name]:
                    paper = recommended_papers[field_name][0]  # 取第一篇推荐论文

                    title = paper.get("title", "未知标题")[:100]  # 限制标题长度
                    authors = paper.get("authors_str", "")[:80]  # 限制作者长度
                    score = paper.get("relevance_score", paper.get("final_score", 0))
                    arxiv_id = paper.get("arxiv_id", "")
                    paper_url = paper.get("paper_url", "")

                    recommendation_text = f"🏆 **推荐论文** (评分: {score:.2f})\n"
                    recommendation_text += f"📄 [{title}]({paper_url})\n"
                    recommendation_text += f"👥 {authors}\n"
                    recommendation_text += f"🔗 ArXiv ID: {arxiv_id}"

                    elements.append({"tag": "div", "text": {"tag": "lark_md", "content": recommendation_text}})

                # 领域间分隔
                elements.append({"tag": "div", "text": {"tag": "plain_text", "content": ""}})

        # 底部信息
        elements.append({"tag": "hr"})
        elements.append({"tag": "div", "text": {"tag": "plain_text", "content": "🤖 ArXiv论文采集机器人自动推送"}})

        return {"msg_type": "interactive", "content": {"elements": elements}}

    def create_simple_text_message(
        self,
        update_stats: Dict[str, Any],
        recommended_papers: Dict[str, List[Dict]],
        table_links: Dict[str, str] = None,
    ) -> Dict[str, Any]:
        """创建简单文本消息（备用方案）"""
        lines = []
        lines.append("📚 ArXiv论文更新通知")
        lines.append("")

        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        lines.append(f"🕒 更新时间: {current_time}")
        lines.append("")

        # 统计概览
        total_new = sum(stats.get("new_count", 0) for stats in update_stats.values())
        total_papers = sum(stats.get("total_count", 0) for stats in update_stats.values())

        lines.append(f"📊 本次更新: 新增 {total_new} 篇，总计 {total_papers} 篇")
        lines.append(f"🎯 涉及领域: {len(update_stats)} 个")
        lines.append("")

        # 各领域信息
        for field_name, stats in update_stats.items():
            new_count = stats.get("new_count", 0)
            total_count = stats.get("total_count", 0)

            if new_count > 0:
                lines.append(f"【{field_name}】")
                lines.append(f"  📈 新增: {new_count} 篇 | 📚 总计: {total_count} 篇")

                # 添加表格链接（如果提供）
                if table_links and field_name in table_links:
                    table_link = table_links[field_name]
                    lines.append(f"  📊 表格链接: {table_link}")

                # 推荐论文
                if field_name in recommended_papers and recommended_papers[field_name]:
                    paper = recommended_papers[field_name][0]
                    title = paper.get("title", "未知标题")[:80]
                    score = paper.get("relevance_score", paper.get("final_score", 0))
                    arxiv_id = paper.get("arxiv_id", "")

                    lines.append(f"  🏆 推荐: {title}")
                    lines.append(f"     评分: {score:.2f} | ID: {arxiv_id}")

                lines.append("")

        lines.append("🤖 ArXiv论文采集机器人")

        return {"msg_type": "text", "content": {"text": "\n".join(lines)}}

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
            logger.info("ℹ️ 群聊通知功能已禁用")
            return False

        # 检查是否有足够的更新需要通知
        total_new = sum(stats.get("new_count", 0) for stats in update_stats.values())
        if total_new < self.chat_config.min_papers_threshold:
            logger.info(f"ℹ️ 新增论文数量({total_new})低于通知阈值({self.chat_config.min_papers_threshold})，跳过通知")
            return False

        logger.info("📢 开始发送论文更新通知...")
        logger.info(f"   📊 统计信息: {total_new} 篇新论文，{len(update_stats)} 个领域")

        # 生成推荐论文
        recommended_papers = self._select_recommended_papers(papers_by_field)

        # 获取群聊列表
        chats = self.get_bot_chats()
        if not chats:
            logger.error("❌ 没有找到可发送的群聊")
            return False

        # 创建消息内容
        try:
            message_content = self.create_paper_update_message(update_stats, recommended_papers, table_links)
        except Exception as e:
            logger.warning(f"⚠️ 创建富文本消息失败，使用简单文本: {e}")
            message_content = self.create_simple_text_message(update_stats, recommended_papers, table_links)

        # 发送到所有群聊
        success_count = 0
        total_chats = 0

        for chat in chats:
            chat_id = chat.get("chat_id")
            chat_name = chat.get("name", "未命名群聊")

            if not chat_id:
                continue

            total_chats += 1
            logger.info(f"📤 发送通知到: {chat_name}")

            if self.send_message_to_chat(chat_id, message_content):
                success_count += 1

            # 避免发送过快
            time.sleep(0.5)

        logger.info(f"📊 通知发送完成: {success_count}/{total_chats} 个群聊发送成功")
        return success_count > 0

    def _select_recommended_papers(self, papers_by_field: Dict[str, List[Dict]]) -> Dict[str, List[Dict]]:
        """为每个领域选择推荐论文"""
        recommended = {}

        for field_name, papers in papers_by_field.items():
            if not papers:
                continue

            # 按相关性评分排序
            sorted_papers = sorted(
                papers, key=lambda p: p.get("relevance_score", p.get("final_score", 0)), reverse=True
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
                logger.warning("⚠️ 未配置多维表格app_token，无法生成表格链接")
                return None

            # 如果没有提供table_id，尝试通过table_name查找
            if not table_id and table_name:
                from .bitable import BitableManager

                bitable_manager = BitableManager(self.config)
                table_id = bitable_manager.find_table_by_name(table_name)

                if not table_id:
                    logger.warning(f"⚠️ 未找到表格: {table_name}")
                    return None

            if not table_id:
                logger.warning("⚠️ 无法确定表格ID，无法生成链接")
                return None

            # 生成飞书多维表格访问链接
            table_link = f"https://feishu.cn/base/{app_token}?table={table_id}&view=vew"
            return table_link

        except Exception as e:
            logger.warning(f"⚠️ 生成表格链接失败: {e}")
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

        logger.info("🧪 开始测试群聊通知功能...")
        return self.notify_paper_updates(test_stats, test_papers, test_table_links)


def create_chat_notifier_from_config(cfg) -> ChatNotifier:
    """从配置创建群聊通知器"""
    from .config import FeishuConfig

    # 创建基础配置
    feishu_config = FeishuConfig.from_hydra_config(cfg)

    # 创建聊天配置
    feishu_cfg = cfg.get("feishu", {})
    chat_cfg = feishu_cfg.get("chat_notification", {})

    chat_config = ChatNotificationConfig(
        enabled=chat_cfg.get("enabled", True),
        notify_on_update=chat_cfg.get("notify_on_update", True),
        notify_on_new_papers=chat_cfg.get("notify_on_new_papers", True),
        min_papers_threshold=chat_cfg.get("min_papers_threshold", 1),
        max_recommended_papers=chat_cfg.get("max_recommended_papers", 1),
        message_template=chat_cfg.get("message_template", "default"),
    )

    return ChatNotifier(feishu_config, chat_config)
