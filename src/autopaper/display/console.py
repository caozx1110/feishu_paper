"""Console rendering for paper lists and ranking summaries."""

from __future__ import annotations

from typing import Any, Dict, List


class ConsoleDisplayMixin:
    def display_hot_categories(self, papers: List[Dict[str, Any]]):
        """显示热门分类统计"""
        if not papers:
            return

        category_count = {}
        for paper in papers:
            for category in paper.get('categories', []):
                category_count[category] = category_count.get(category, 0) + 1

        print("\n🔥 热门领域 Top 10:")
        print("-" * 40)

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

        for i, (category, count) in enumerate(sorted_categories, 1):
            cat_name = category_names.get(category, category)
            print(f"{i:2d}. {category:15s} ({cat_name:12s}) - {count:3d} 篇")

    def display_ranked_papers(self, papers: List[Dict[str, Any]], max_display: int = 10, show_scores: bool = True):
        """显示排序后的论文，包含相关性信息"""
        if not papers:
            print("📝 没有找到相关论文")
            return

        print(f"\n📋 智能排序论文 (显示前{min(max_display, len(papers))}篇):")
        print("=" * 90)

        for i, paper in enumerate(papers[:max_display], 1):
            score = paper.get('relevance_score', 0)
            matched_interests = paper.get('matched_interests', [])

            print(f"\n{i:2d}. {paper['title']}")
            if show_scores:
                print(f"    🎯 相关性评分: {score:.2f}")
                if matched_interests:
                    print(f"    🔍 匹配关键词: {', '.join(matched_interests)}")

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
            print("    " + "-" * 86)

    def display_papers_detailed(self, papers: List[Dict[str, Any]], max_display: int = 10):
        """详细显示论文信息"""
        if not papers:
            print("📝 没有找到相关论文")
            return

        print(f"\n📋 论文详情 (显示前{min(max_display, len(papers))}篇):")
        print("=" * 80)

        for i, paper in enumerate(papers[:max_display], 1):
            print(f"\n{i:2d}. {paper['title']}")
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
            print("    " + "-" * 76)

    def display_ranking_stats(self, score_stats: Dict[str, Any], excluded_papers: List[Dict[str, Any]]):
        """显示排序统计信息"""
        if not score_stats:
            return

        print("\n📊 智能排序统计:")
        print("-" * 50)
        print(f"📄 总论文数: {score_stats['total_papers']}")
        print(f"🎯 相关论文数: {score_stats['ranked_papers']}")
        print(f"🚫 排除论文数: {score_stats['excluded_papers']}")

        # 显示必须关键词过滤统计
        required_filtered = score_stats.get('required_filtered', 0)
        if required_filtered > 0:
            print(f"✅ 必须关键词过滤: {required_filtered}")

        if score_stats['ranked_papers'] > 0:
            print(f"📈 最高评分: {score_stats['max_score']:.2f}")
            print(f"📉 最低评分: {score_stats['min_score']:.2f}")
            print(f"📊 平均评分: {score_stats['avg_score']:.2f}")

        # 显示排除的论文信息
        if excluded_papers:
            print("\n🚫 被排除的论文 (前5篇):")
            for i, paper in enumerate(excluded_papers[:5], 1):
                exclude_reason = paper.get('exclude_reason', [])
                if isinstance(exclude_reason, list):
                    exclude_reason = ', '.join(exclude_reason)
                print(f"  {i}. {paper['title'][:60]}...")
                if exclude_reason == "未包含必须关键词":
                    print(f"     排除原因: {exclude_reason}")
                else:
                    print(f"     排除原因: 匹配了排除词条 [{exclude_reason}]")
