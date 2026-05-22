"""Message payload builders for Feishu chat notifications."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List


class FeishuMessageBuilderMixin:
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
        # 构建飞书消息卡片。interactive 消息的 content 必须是完整 card，
        # 不能只包含 elements，否则部分租户会拒收或渲染为空。
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
                    "content": f"📊 **本次更新概览**\n新增论文: {total_new} 篇\n相关表格总计: {total_papers} 篇\n覆盖领域: {len(update_stats)} 个",
                },
            }
        )

        # 分隔线
        elements.append({"tag": "hr"})

        # 各领域详细信息
        for field_name, stats in update_stats.items():
            new_count = stats.get('new_count', 0)
            total_count = stats.get('total_count', 0)
            if new_count > 0:
                # 构建领域信息，包含表格链接
                field_content = f"🎯 **{field_name}**\n📈 新增: {new_count} 篇 | 📚 总计: {total_count} 篇"

                # 添加表格链接（如果提供）
                include_links = getattr(self.chat_config, "include_table_links", True)
                if include_links and table_links and field_name in table_links:
                    table_link = table_links[field_name]
                    field_content += f"\n📊 [查看完整表格]({table_link})"

                elements.append({"tag": "div", "text": {"tag": "lark_md", "content": field_content}})

                # 推荐论文
                if field_name in recommended_papers and recommended_papers[field_name]:
                    paper = recommended_papers[field_name][0]  # 取第一篇推荐论文

                    title = self._truncate_message_text(
                        paper.get('title', '未知标题'), getattr(self.chat_config, "max_title_chars", 100)
                    )
                    authors = self._truncate_message_text(
                        paper.get('authors_str', ''), getattr(self.chat_config, "max_authors_chars", 80)
                    )
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

        return {
            "msg_type": "interactive",
            "content": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "template": "blue",
                    "title": {"tag": "plain_text", "content": "ArXiv 论文更新"},
                },
                "elements": elements,
            },
        }

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

        lines.append(f"📊 本次更新: 新增 {total_new} 篇，相关表格总计 {total_papers} 篇")
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
                include_links = getattr(self.chat_config, "include_table_links", True)
                if include_links and table_links and field_name in table_links:
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

    @staticmethod
    def _truncate_message_text(value: Any, max_chars: int) -> str:
        text = str(value or "")
        if max_chars <= 0 or len(text) <= max_chars:
            return text
        return text[: max_chars - 1].rstrip() + "…"
