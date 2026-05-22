"""Console rendering for paper lists and ranking summaries."""

from __future__ import annotations

from typing import Any, Dict, List

from ..terminal import info, key_values, section, table


class ConsoleDisplayMixin:
    def display_hot_categories(self, papers: List[Dict[str, Any]]):
        """显示热门分类统计"""
        if not papers:
            return

        category_count = {}
        for paper in papers:
            for category in paper.get('categories', []):
                category_count[category] = category_count.get(category, 0) + 1

        sorted_categories = sorted(category_count.items(), key=lambda x: x[1], reverse=True)[:10]

        category_names = {
            'cs.AI': '人工智能',
            'cs.LG': '机器学习',
            'cs.CV': '计算机视觉',
            'cs.RO': '机器人学',
            'cs.CL': '计算语言学',
            'cs.CR': '密码学与安全',
            'cs.NE': '神经与进化计算',
            'cs.DB': '数据库',
            'cs.HC': '人机交互',
            'cs.IR': '信息检索',
            'stat.ML': '机器学习(统计)',
            'eess.IV': '图像和视频处理',
        }

        table(
            "热门领域 Top 10",
            ["#", "分类", "名称", "论文数"],
            [
                (index, category, category_names.get(category, category), count)
                for index, (category, count) in enumerate(sorted_categories, 1)
            ],
        )

    def display_ranked_papers(self, papers: List[Dict[str, Any]], max_display: int = 10, show_scores: bool = True):
        """显示排序后的论文，包含相关性信息"""
        if not papers:
            info("没有找到相关论文")
            return

        section("智能排序论文", f"显示前 {min(max_display, len(papers))} 篇")

        for i, paper in enumerate(papers[:max_display], 1):
            score = paper.get('relevance_score', 0)
            matched_interests = paper.get('matched_interests', [])
            details = {}
            if show_scores:
                details["相关性评分"] = f"{score:.2f}"
                if matched_interests:
                    details["匹配关键词"] = ", ".join(matched_interests)
            details.update(_paper_details(paper))
            key_values(f"{i}. {paper.get('title', '')}", details)

    def display_papers_detailed(self, papers: List[Dict[str, Any]], max_display: int = 10):
        """详细显示论文信息"""
        if not papers:
            info("没有找到相关论文")
            return

        section("论文详情", f"显示前 {min(max_display, len(papers))} 篇")

        for i, paper in enumerate(papers[:max_display], 1):
            key_values(f"{i}. {paper.get('title', '')}", _paper_details(paper))

    def display_ranking_stats(self, score_stats: Dict[str, Any], excluded_papers: List[Dict[str, Any]]):
        """显示排序统计信息"""
        if not score_stats:
            return

        stats = {
            "总论文数": score_stats['total_papers'],
            "相关论文数": score_stats['ranked_papers'],
            "排除论文数": score_stats['excluded_papers'],
        }

        # 显示必须关键词过滤统计
        required_filtered = score_stats.get('required_filtered', 0)
        if required_filtered > 0:
            stats["必须关键词过滤"] = required_filtered

        if score_stats['ranked_papers'] > 0:
            stats["最高评分"] = f"{score_stats['max_score']:.2f}"
            stats["最低评分"] = f"{score_stats['min_score']:.2f}"
            stats["平均评分"] = f"{score_stats['avg_score']:.2f}"

        key_values("智能排序统计", stats)

        # 显示排除的论文信息
        if excluded_papers:
            table(
                "被排除的论文（前5篇）",
                ["#", "标题", "排除原因"],
                [
                    (
                        index,
                        paper.get('title', '')[:80],
                        _exclude_reason_text(paper.get('exclude_reason', [])),
                    )
                    for index, paper in enumerate(excluded_papers[:5], 1)
                ],
                show_lines=True,
            )


def _paper_details(paper: Dict[str, Any]) -> dict[str, Any]:
    published = paper.get('published_date')
    published_text = published.strftime('%Y-%m-%d %H:%M') if published else "-"
    summary = paper.get('summary', '')
    if len(summary) > 240:
        summary = summary[:240] + '...'
    return {
        "作者": paper.get('authors_str', ''),
        "分类": paper.get('categories_str', ''),
        "发布": published_text,
        "论文": paper.get('paper_url', ''),
        "PDF": paper.get('pdf_url', ''),
        "摘要": summary,
    }


def _exclude_reason_text(exclude_reason: Any) -> str:
    if isinstance(exclude_reason, list):
        exclude_reason = ', '.join(exclude_reason)
    if exclude_reason == "未包含必须关键词":
        return exclude_reason
    return f"匹配了排除词条 [{exclude_reason}]"
