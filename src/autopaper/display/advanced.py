"""Advanced ranking display helpers."""

from __future__ import annotations

from typing import Any, Dict, List

from ..terminal import info, key_values, section, table
from .console import _paper_details


class AdvancedDisplayMixin:
    def display_advanced_ranking_stats(self, papers: List[Dict[str, Any]], score_stats: Dict[str, Any]):
        """显示高级排序统计信息"""
        if not papers or not score_stats.get('use_advanced_scoring'):
            return

        stats = {
            "总论文数": score_stats['total_papers'],
            "相关论文数": score_stats['ranked_papers'],
            "排除论文数": score_stats['excluded_papers'],
        }

        if score_stats['ranked_papers'] > 0:
            stats["最高评分"] = f"{score_stats['max_score']:.2f}"
            stats["最低评分"] = f"{score_stats['min_score']:.2f}"
            stats["平均评分"] = f"{score_stats['avg_score']:.2f}"

        key_values("高级智能排序统计", stats)

        # 分析评分分布
        papers_with_breakdown = [p for p in papers if 'score_breakdown' in p]
        if papers_with_breakdown:
            base_scores = [p['score_breakdown'].get('base_score', 0) for p in papers_with_breakdown]
            semantic_scores = [p['score_breakdown'].get('semantic_boost', 0) for p in papers_with_breakdown]
            novelty_scores = [p['score_breakdown'].get('novelty_boost', 0) for p in papers_with_breakdown]
            citation_scores = [p['score_breakdown'].get('citation_potential', 0) for p in papers_with_breakdown]
            table(
                "评分维度分析",
                ["维度", "平均分"],
                [
                    ("基础匹配", sum(base_scores) / len(base_scores) if base_scores else 0),
                    ("语义增强", sum(semantic_scores) / len(semantic_scores) if semantic_scores else 0),
                    ("新颖性", sum(novelty_scores) / len(novelty_scores) if novelty_scores else 0),
                    ("引用潜力", sum(citation_scores) / len(citation_scores) if citation_scores else 0),
                ],
            )

    def display_paper_score_breakdown(self, paper: Dict[str, Any]):
        """显示单篇论文的详细评分分解"""
        if 'score_breakdown' not in paper:
            return

        breakdown = paper['score_breakdown']
        key_values(
            "评分详情",
            {
                "基础匹配": f"{breakdown.get('base_score', 0):.2f}",
                "语义增强": f"{breakdown.get('semantic_boost', 0):.2f}",
                "作者分析": f"{breakdown.get('author_boost', 0):.2f}",
                "新颖性": f"{breakdown.get('novelty_boost', 0):.2f}",
                "引用潜力": f"{breakdown.get('citation_potential', 0):.2f}",
                "综合评分": f"{paper.get('final_score', paper.get('relevance_score', 0)):.2f}",
            },
        )

    def display_advanced_ranked_papers(
        self, papers: List[Dict[str, Any]], max_display: int = 10, show_breakdown: bool = False
    ):
        """显示高级排序后的论文（包含评分分解）"""
        if not papers:
            info("没有找到相关论文")
            return

        use_advanced = any('score_breakdown' in paper for paper in papers)
        score_key = 'final_score' if use_advanced else 'relevance_score'

        section(f"{'高级' if use_advanced else '标准'}智能排序论文", f"显示前 {min(max_display, len(papers))} 篇")

        for i, paper in enumerate(papers[:max_display], 1):
            score = paper.get(score_key, 0)
            matched_interests = paper.get('matched_interests', [])

            details = {("综合评分" if use_advanced else "相关性评分"): f"{score:.2f}"}
            if matched_interests:
                details["匹配关键词"] = ", ".join(matched_interests)

            # 显示评分分解
            if show_breakdown and use_advanced:
                self.display_paper_score_breakdown(paper)

            details.update(_paper_details(paper))
            key_values(f"{i}. {paper.get('title', '')}", details)
