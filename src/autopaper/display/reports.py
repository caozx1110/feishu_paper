"""Report file writers for paper collections."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from ..terminal import print


class ReportWriterMixin:
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
                f.write("arXiv 论文收集报告\n")
                f.write(f"生成时间: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
                f.write(f"配置文件: {config_name}\n")
                f.write(f"研究领域: {research_area}\n")
                f.write(f"查询字段: {field_name}\n")
                f.write(f"时间范围: 最近 {days} 天\n")
                f.write(f"总论文数: {len(papers)}\n")
                if include_scores:
                    f.write("智能排序: 已启用\n")
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
                f.write("# ArXiv 论文采集报告\n\n")
                f.write(f"- **生成时间**: {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}\n")
                f.write(f"- **配置文件**: {config_name}\n")
                if research_area and research_area != config_name:
                    f.write(f"- **研究领域**: {research_area}\n")
                f.write(f"- **搜索领域**: {field_name}\n")
                f.write(f"- **时间范围**: 最近{days}天\n")
                f.write(f"- **论文数量**: {len(papers)}篇\n")
                f.write("\n---\n\n")

                # 统计信息
                if include_scores:
                    scores = [p.get('final_score', p.get('relevance_score', 0)) for p in papers]
                    if scores:
                        f.write("## 📊 统计信息\n\n")
                        f.write(f"- **最高评分**: {max(scores):.2f}\n")
                        f.write(f"- **最低评分**: {min(scores):.2f}\n")
                        f.write(f"- **平均评分**: {sum(scores)/len(scores):.2f}\n\n")

                # 论文列表
                f.write("## 📚 论文列表\n\n")

                for i, paper in enumerate(papers, 1):
                    # 标题和基本信息
                    title = paper.get('title', 'Unknown Title')
                    authors = paper.get('authors_str', 'Unknown Authors')
                    arxiv_id = paper.get('arxiv_id', 'N/A')
                    categories = paper.get('categories_str', 'N/A')
                    published = paper.get('published_date', 'N/A')

                    f.write(f"### {i}. {title}\n\n")

                    # 基本信息表格
                    f.write("| 项目 | 信息 |\n")
                    f.write("|------|------|\n")
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

                    f.write("\n")

                    # 摘要
                    summary = paper.get('summary', 'No summary available')
                    f.write(f"**摘要**: {summary}\n\n")

                    # 评分详情（如果启用了高级评分）
                    if include_scores and 'score_breakdown' in paper:
                        breakdown = paper['score_breakdown']
                        f.write("**评分详情**:\n")
                        f.write(f"- 基础匹配: {breakdown.get('base_score', 0):.2f}\n")
                        f.write(f"- 语义增强: {breakdown.get('semantic_boost', 0):.2f}\n")
                        f.write(f"- 作者分析: {breakdown.get('author_boost', 0):.2f}\n")
                        f.write(f"- 新颖性: {breakdown.get('novelty_boost', 0):.2f}\n")
                        f.write(f"- 引用潜力: {breakdown.get('citation_potential', 0):.2f}\n\n")

                    f.write("---\n\n")

                # 页脚
                f.write("\n*报告由 ArXiv 论文采集工具生成*\n")

            print(f"💾 Markdown报告已保存到: {filepath}")

        except Exception as e:
            print(f"❌ 保存Markdown报告失败: {e}")
