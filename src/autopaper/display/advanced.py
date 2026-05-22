"""Advanced ranking display helpers."""

from __future__ import annotations

from typing import Any, Dict, List


class AdvancedDisplayMixin:
    def display_advanced_ranking_stats(self, papers: List[Dict[str, Any]], score_stats: Dict[str, Any]):
        """显示高级排序统计信息"""
        if not papers or not score_stats.get('use_advanced_scoring'):
            return

        print("\n🧠 高级智能排序统计:")
        print("-" * 60)
        print(f"📄 总论文数: {score_stats['total_papers']}")
        print(f"🎯 相关论文数: {score_stats['ranked_papers']}")
        print(f"🚫 排除论文数: {score_stats['excluded_papers']}")

        if score_stats['ranked_papers'] > 0:
            print(f"📈 最高评分: {score_stats['max_score']:.2f}")
            print(f"📉 最低评分: {score_stats['min_score']:.2f}")
            print(f"📊 平均评分: {score_stats['avg_score']:.2f}")

        # 分析评分分布
        papers_with_breakdown = [p for p in papers if 'score_breakdown' in p]
        if papers_with_breakdown:
            print("\n📊 评分维度分析:")

            base_scores = [p['score_breakdown'].get('base_score', 0) for p in papers_with_breakdown]
            semantic_scores = [p['score_breakdown'].get('semantic_boost', 0) for p in papers_with_breakdown]
            novelty_scores = [p['score_breakdown'].get('novelty_boost', 0) for p in papers_with_breakdown]
            citation_scores = [p['score_breakdown'].get('citation_potential', 0) for p in papers_with_breakdown]

            if base_scores:
                print(f"   🎯 基础匹配平均分: {sum(base_scores)/len(base_scores):.2f}")
            if semantic_scores:
                print(f"   🧠 语义增强平均分: {sum(semantic_scores)/len(semantic_scores):.2f}")
            if novelty_scores:
                print(f"   ✨ 新颖性平均分: {sum(novelty_scores)/len(novelty_scores):.2f}")
            if citation_scores:
                print(f"   📈 引用潜力平均分: {sum(citation_scores)/len(citation_scores):.2f}")

    def display_paper_score_breakdown(self, paper: Dict[str, Any]):
        """显示单篇论文的详细评分分解"""
        if 'score_breakdown' not in paper:
            return

        breakdown = paper['score_breakdown']
        print("    📊 评分详情:")
        print(f"       基础匹配: {breakdown.get('base_score', 0):.2f}")
        print(f"       语义增强: {breakdown.get('semantic_boost', 0):.2f}")
        print(f"       作者分析: {breakdown.get('author_boost', 0):.2f}")
        print(f"       新颖性: {breakdown.get('novelty_boost', 0):.2f}")
        print(f"       引用潜力: {breakdown.get('citation_potential', 0):.2f}")
        print(f"       综合评分: {paper.get('final_score', paper.get('relevance_score', 0)):.2f}")

    def display_advanced_ranked_papers(
        self, papers: List[Dict[str, Any]], max_display: int = 10, show_breakdown: bool = False
    ):
        """显示高级排序后的论文（包含评分分解）"""
        if not papers:
            print("📝 没有找到相关论文")
            return

        use_advanced = any('score_breakdown' in paper for paper in papers)
        score_key = 'final_score' if use_advanced else 'relevance_score'

        print(f"\n📋 {'高级' if use_advanced else '标准'}智能排序论文 (显示前{min(max_display, len(papers))}篇):")
        print("=" * 100)

        for i, paper in enumerate(papers[:max_display], 1):
            score = paper.get(score_key, 0)
            matched_interests = paper.get('matched_interests', [])

            print(f"\n{i:2d}. {paper['title']}")
            print(f"    🎯 {'综合评分' if use_advanced else '相关性评分'}: {score:.2f}")

            if matched_interests:
                print(f"    🔍 匹配关键词: {', '.join(matched_interests)}")

            # 显示评分分解
            if show_breakdown and use_advanced:
                self.display_paper_score_breakdown(paper)

            print(f"    👥 作者: {paper['authors_str']}")
            print(f"    🏷️  分类: {paper['categories_str']}")
            print(f"    📅 发布: {paper['published_date'].strftime('%Y-%m-%d %H:%M')}")
            print(f"    🔗 论文: {paper['paper_url']}")
            print(f"    📄 PDF: {paper['pdf_url']}")

            # 显示摘要（限制长度）
            summary = paper['summary']
            if len(summary) > 200:
                summary = summary[:200] + '...'
            print(f"    📝 摘要: {summary}")
            print("    " + "-" * 96)
