#!/usr/bin/env python3
"""
飞书群聊通知模块
支持在飞书群聊中发送论文更新通知
"""

import json
import time
import os
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import requests
from dataclasses import dataclass
from .feishu_bitable_connector import FeishuBitableConfig, FeishuBitableAPIError


@dataclass
class ChatNotificationConfig:
    """群聊通知配置类"""

    enabled: bool = True
    notify_on_update: bool = True
    notify_on_new_papers: bool = True
    min_papers_threshold: int = 1  # 最少论文数量才发送通知
    max_recommended_papers: int = 1  # 每个领域推荐的论文数量
    message_template: str = "default"  # 消息模板类型


class FeishuChatNotifier:
    """飞书群聊通知器"""

    def __init__(self, config: FeishuBitableConfig, chat_config: ChatNotificationConfig = None):
        """初始化飞书群聊通知器"""
        self.config = config
        self.chat_config = chat_config or ChatNotificationConfig()
        self.session = requests.Session()
        self.session.headers.update(
            {'Content-Type': 'application/json; charset=utf-8', 'Authorization': f'Bearer {config.access_token}'}
        )

        print(f"🤖 飞书群聊通知器已初始化，token类型: {config.token_type}")

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
                    print("🔄 检测到token过期，尝试刷新...")
                    if self._refresh_token_if_needed():
                        print("✅ token刷新成功，重试请求...")
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
                from .feishu_bitable_connector import FeishuBitableConnector

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

            print(f"🔍 发现 {len(chats)} 个机器人参与的群聊")
            for chat in chats:
                chat_id = chat.get('chat_id', '')
                chat_name = chat.get('name', '未命名群聊')
                chat_type = chat.get('chat_type', 'unknown')
                print(f"   - {chat_name} ({chat_type}): {chat_id}")

            return chats

        except Exception as e:
            print(f"❌ 获取群聊列表失败: {e}")
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

            result = self._make_request('POST', endpoint, json=payload, params=params)

            if result:
                print(f"✅ 消息发送成功到群聊: {chat_id}")
                return True
            else:
                print(f"❌ 消息发送失败到群聊: {chat_id}")
                return False

        except Exception as e:
            print(f"❌ 发送消息到群聊 {chat_id} 失败: {e}")
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
        total_new = sum(stats.get('new_count', 0) for stats in update_stats.values())
        total_papers = sum(stats.get('total_count', 0) for stats in update_stats.values())

        elements.append(
            {
                "tag": "div",
                "text": {
                    "tag": "lark_md",
                    "content": f"📊 **本次更新概览**\n新增论文: {total_new} 篇\n数据库总计: {total_papers} 篇\n覆盖领域: {len(update_stats)} 个",
                },
            }
        )

        # 分隔线
        elements.append({"tag": "hr"})

        # 各领域详细信息
        for field_name, stats in update_stats.items():
            new_count = stats.get('new_count', 0)
            total_count = stats.get('total_count', 0)
            table_name = stats.get('table_name', field_name)

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

                    title = paper.get('title', '未知标题')[:100]  # 限制标题长度
                    authors = paper.get('authors_str', '')[:80]  # 限制作者长度
                    score = paper.get('relevance_score', paper.get('final_score', 0))
                    arxiv_id = paper.get('arxiv_id', '')
                    paper_url = paper.get('paper_url', '')

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
        total_new = sum(stats.get('new_count', 0) for stats in update_stats.values())
        total_papers = sum(stats.get('total_count', 0) for stats in update_stats.values())

        lines.append(f"📊 本次更新: 新增 {total_new} 篇，总计 {total_papers} 篇")
        lines.append(f"🎯 涉及领域: {len(update_stats)} 个")
        lines.append("")

        # 各领域信息
        for field_name, stats in update_stats.items():
            new_count = stats.get('new_count', 0)
            total_count = stats.get('total_count', 0)

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
                    title = paper.get('title', '未知标题')[:80]
                    score = paper.get('relevance_score', paper.get('final_score', 0))
                    arxiv_id = paper.get('arxiv_id', '')

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
            print("ℹ️ 群聊通知功能已禁用")
            return False

        # 检查是否有足够的更新需要通知
        total_new = sum(stats.get('new_count', 0) for stats in update_stats.values())
        if total_new < self.chat_config.min_papers_threshold:
            print(f"ℹ️ 新增论文数量({total_new})低于通知阈值({self.chat_config.min_papers_threshold})，跳过通知")
            return False

        print(f"📢 开始发送论文更新通知...")
        print(f"   📊 统计信息: {total_new} 篇新论文，{len(update_stats)} 个领域")

        # 生成推荐论文
        recommended_papers = self._select_recommended_papers(papers_by_field)

        # 获取群聊列表
        chats = self.get_bot_chats()
        if not chats:
            print("❌ 没有找到可发送的群聊")
            return False

        # 创建消息内容
        try:
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
            print(f"📤 发送通知到: {chat_name}")

            if self.send_message_to_chat(chat_id, message_content):
                success_count += 1

            # 避免发送过快
            time.sleep(0.5)

        print(f"📊 通知发送完成: {success_count}/{total_chats} 个群聊发送成功")
        return success_count > 0

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
                from .feishu_bitable_connector import FeishuBitableConnector

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


def create_chat_notifier_from_config(cfg) -> FeishuChatNotifier:
    """从配置创建群聊通知器"""
    from .feishu_bitable_connector import FeishuBitableConfig

    # 创建基础配置
    feishu_config = FeishuBitableConfig.from_hydra_config(cfg)

    # 创建聊天配置
    feishu_cfg = cfg.get('feishu', {})
    chat_cfg = feishu_cfg.get('chat_notification', {})

    chat_config = ChatNotificationConfig(
        enabled=chat_cfg.get('enabled', True),
        notify_on_update=chat_cfg.get('notify_on_update', True),
        notify_on_new_papers=chat_cfg.get('notify_on_new_papers', True),
        min_papers_threshold=chat_cfg.get('min_papers_threshold', 1),
        max_recommended_papers=chat_cfg.get('max_recommended_papers', 1),
        message_template=chat_cfg.get('message_template', 'default'),
    )

    return FeishuChatNotifier(feishu_config, chat_config)


if __name__ == "__main__":
    print("飞书群聊通知模块测试")

    # 测试配置
    from dotenv import load_dotenv

    load_dotenv()

    try:
        from .feishu_bitable_connector import FeishuBitableConfig

        config = FeishuBitableConfig(
            app_id=os.getenv('FEISHU_APP_ID', ''),
            app_secret=os.getenv('FEISHU_APP_SECRET', ''),
            tenant_access_token=os.getenv('FEISHU_TENANT_ACCESS_TOKEN'),
            user_access_token=os.getenv('FEISHU_USER_ACCESS_TOKEN'),
        )

        notifier = FeishuChatNotifier(config)
        notifier.test_notification()

    except Exception as e:
        print(f"❌ 测试失败: {e}")
