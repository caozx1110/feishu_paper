#!/usr/bin/env python3
"""
论文显示和输出模块
处理论文信息的格式化显示和文件保存
"""

from datetime import datetime
from typing import List, Dict, Any
import os
from pathlib import Path


class PaperDisplayer:
    """论文显示类"""

    def __init__(self, output_dir: str = "outputs"):
        """初始化显示器"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def display_hot_categories(self, papers: List[Dict[str, Any]]):
        """显示热门分类统计"""
        if not papers:
            return

        category_count = {}
        for paper in papers:
            for category in paper.get('categories', []):
                category_count[category] = category_count.get(category, 0) + 1

        print(f"\n🔥 热门领域 Top 10:")
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

        print(f"\n📊 智能排序统计:")
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
            print(f"\n🚫 被排除的论文 (前5篇):")
            for i, paper in enumerate(excluded_papers[:5], 1):
                exclude_reason = paper.get('exclude_reason', [])
                if isinstance(exclude_reason, list):
                    exclude_reason = ', '.join(exclude_reason)
                print(f"  {i}. {paper['title'][:60]}...")
                if exclude_reason == "未包含必须关键词":
                    print(f"     排除原因: {exclude_reason}")
                else:
                    print(f"     排除原因: 匹配了排除词条 [{exclude_reason}]")

    def save_papers_report(
        self,
        papers: List[Dict[str, Any]],
        field_name: str = "",
        days: int = 1,
        include_scores: bool = False,
        config_name: str = "",
        research_area: str = "",
    ):
        """保存论文报告到文件"""
        if not papers:
            return

        date_str = datetime.now().strftime('%Y%m%d')

        # 使用与markdown相同的命名逻辑
        def clean_name_component(name: str) -> str:
            if not name:
                return ""
            return (
                name.replace("/", "_")
                .replace("\\", "_")
                .replace(":", "_")
                .replace("*", "_")
                .replace("?", "_")
                .replace("\"", "_")
                .replace("<", "_")
                .replace(">", "_")
                .replace("|", "_")
                .replace("+", "_")
                .replace("&", "_")
                .replace(" ", "_")
                .strip("_")
            )

        # 构建文件名组件
        clean_config = clean_name_component(config_name)
        clean_research_area = clean_name_component(research_area)
        clean_field = clean_name_component(field_name)

        # 构建文件名：arxiv_配置名_研究领域_字段_天数days_时间戳.txt
        name_parts = ["arxiv"]

        if clean_config and clean_config != "unknown":
            name_parts.append(clean_config)

        if clean_research_area and clean_research_area != clean_config:
            name_parts.append(clean_research_area)

        if clean_field:
            name_parts.append(clean_field)

        name_parts.extend([f"{days}days", date_str])

        filename = f"{self.output_dir}/{'_'.join(name_parts)}.txt"

        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"arXiv 论文收集报告\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
                f.write(f"配置文件: {config_name}\n")
                f.write(f"研究领域: {research_area}\n")
                f.write(f"查询字段: {field_name}\n")
                f.write(f"时间范围: 最近 {days} 天\n")
                f.write(f"总论文数: {len(papers)}\n")
                if include_scores:
                    f.write(f"智能排序: 已启用\n")
                f.write("=" * 80 + "\n\n")

                for i, paper in enumerate(papers, 1):
                    f.write(f"{i}. {paper['title']}\n")

                    if include_scores and 'relevance_score' in paper:
                        f.write(f"   相关性评分: {paper['relevance_score']:.2f}\n")
                        if paper.get('matched_interests'):
                            f.write(f"   匹配关键词: {', '.join(paper['matched_interests'])}\n")

                    f.write(f"   作者: {paper['authors_str']}\n")
                    f.write(f"   分类: {paper['categories_str']}\n")
                    f.write(f"   发布: {paper['published_date'].strftime('%Y-%m-%d %H:%M')}\n")
                    f.write(f"   链接: {paper['paper_url']}\n")
                    f.write(f"   PDF: {paper['pdf_url']}\n")
                    f.write(f"   摘要: {paper['summary']}\n")
                    f.write("-" * 80 + "\n\n")

            print(f"💾 报告已保存到: {filename}")
            return filename

        except Exception as e:
            print(f"❌ 保存文件失败: {e}")
            return None

    def save_papers_report_markdown(
        self,
        papers: List[Dict[str, Any]],
        field_name: str,
        days: int,
        include_scores: bool = True,
        config_name: str = "",
        research_area: str = "",
        output_dir: str = "outputs",
    ):
        """保存论文报告为Markdown格式"""
        if not papers:
            return

        # 创建输出目录
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)

        # 生成统一的文件名格式: arxiv_{config_name}_{research_area}_{field}_{days}days_{timestamp}.md
        timestamp = datetime.now().strftime("%Y%m%d")

        # 清理各个组件中的特殊字符
        def clean_name_component(name: str) -> str:
            if not name:
                return ""
            return (
                name.replace("/", "_")
                .replace("\\", "_")
                .replace(":", "_")
                .replace("*", "_")
                .replace("?", "_")
                .replace("\"", "_")
                .replace("<", "_")
                .replace(">", "_")
                .replace("|", "_")
                .replace("+", "_")
                .replace("&", "_")
                .replace(" ", "_")
                .strip("_")
            )

        # 构建文件名组件
        clean_config = clean_name_component(config_name)
        clean_research_area = clean_name_component(research_area)
        clean_field = clean_name_component(field_name)

        # 构建文件名：arxiv_配置名_研究领域_字段_天数days_时间戳.md
        name_parts = ["arxiv"]

        if clean_config and clean_config != "unknown":
            name_parts.append(clean_config)

        if clean_research_area and clean_research_area != clean_config:
            name_parts.append(clean_research_area)

        if clean_field:
            name_parts.append(clean_field)

        name_parts.extend([f"{days}days", timestamp])

        filename = "_".join(name_parts) + ".md"
        filepath = output_path / filename

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                # 写入标题和基本信息
                f.write(f"# ArXiv 论文采集报告\n\n")
                f.write(f"- **生成时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
                f.write(f"- **配置文件**: {config_name}\n")
                if research_area and research_area != config_name:
                    f.write(f"- **研究领域**: {research_area}\n")
                f.write(f"- **搜索领域**: {field_name}\n")
                f.write(f"- **时间范围**: 最近{days}天\n")
                f.write(f"- **论文数量**: {len(papers)}篇\n")
                f.write(f"\n---\n\n")

                # 统计信息
                if include_scores:
                    scores = [p.get('final_score', p.get('relevance_score', 0)) for p in papers]
                    if scores:
                        f.write(f"## 📊 统计信息\n\n")
                        f.write(f"- **最高评分**: {max(scores):.2f}\n")
                        f.write(f"- **最低评分**: {min(scores):.2f}\n")
                        f.write(f"- **平均评分**: {sum(scores)/len(scores):.2f}\n\n")

                # 论文列表
                f.write(f"## 📚 论文列表\n\n")

                for i, paper in enumerate(papers, 1):
                    # 标题和基本信息
                    title = paper.get('title', 'Unknown Title')
                    authors = paper.get('authors_str', 'Unknown Authors')
                    arxiv_id = paper.get('arxiv_id', 'N/A')
                    categories = paper.get('categories_str', 'N/A')
                    published = paper.get('published_date', 'N/A')

                    f.write(f"### {i}. {title}\n\n")

                    # 基本信息表格
                    f.write(f"| 项目 | 信息 |\n")
                    f.write(f"|------|------|\n")
                    f.write(f"| **ArXiv ID** | {arxiv_id} |\n")
                    f.write(f"| **作者** | {authors} |\n")
                    f.write(f"| **分类** | {categories} |\n")
                    f.write(f"| **发布日期** | {published} |\n")

                    # 评分信息
                    if include_scores:
                        score = paper.get('final_score', paper.get('relevance_score', 0))
                        f.write(f"| **相关性评分** | {score:.2f} |\n")

                        if 'matched_interests' in paper:
                            matched = ', '.join(paper['matched_interests'])
                            f.write(f"| **匹配关键词** | {matched} |\n")

                    # 链接
                    paper_url = paper.get('paper_url', '')
                    pdf_url = paper.get('pdf_url', '')
                    if paper_url:
                        f.write(f"| **论文链接** | [{arxiv_id}]({paper_url}) |\n")
                    if pdf_url:
                        f.write(f"| **PDF下载** | [PDF]({pdf_url}) |\n")

                    f.write(f"\n")

                    # 摘要
                    summary = paper.get('summary', 'No summary available')
                    f.write(f"**摘要**: {summary}\n\n")

                    # 评分详情（如果启用了高级评分）
                    if include_scores and 'score_breakdown' in paper:
                        breakdown = paper['score_breakdown']
                        f.write(f"**评分详情**:\n")
                        f.write(f"- 基础匹配: {breakdown.get('base_score', 0):.2f}\n")
                        f.write(f"- 语义增强: {breakdown.get('semantic_boost', 0):.2f}\n")
                        f.write(f"- 作者分析: {breakdown.get('author_boost', 0):.2f}\n")
                        f.write(f"- 新颖性: {breakdown.get('novelty_boost', 0):.2f}\n")
                        f.write(f"- 引用潜力: {breakdown.get('citation_potential', 0):.2f}\n\n")

                    f.write(f"---\n\n")

                # 页脚
                f.write(f"\n*报告由 ArXiv 论文采集工具生成*\n")

            print(f"💾 Markdown报告已保存到: {filepath}")

        except Exception as e:
            print(f"❌ 保存Markdown报告失败: {e}")

    def display_advanced_ranking_stats(self, papers: List[Dict[str, Any]], score_stats: Dict[str, Any]):
        """显示高级排序统计信息"""
        if not papers or not score_stats.get('use_advanced_scoring'):
            return

        print(f"\n🧠 高级智能排序统计:")
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
            print(f"\n📊 评分维度分析:")

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
        print(f"    📊 评分详情:")
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
