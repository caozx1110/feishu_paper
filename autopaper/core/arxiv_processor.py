#!/usr/bin/env python3
"""
ArXiv API 核心模块
统一管理ArXiv数据交互和论文智能排序功能
使用官方arxiv库进行请求，支持PDF下载
"""

import arxiv
import re
import json
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from collections import defaultdict
import math
import requests
from pathlib import Path
import hashlib

# 优先使用 rapidfuzz，如果不可用则回退到 difflib
try:
    from rapidfuzz import fuzz, process

    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    import difflib

    RAPIDFUZZ_AVAILABLE = False
    print("⚠️  rapidfuzz 不可用，使用 difflib 作为备用方案")


class ArxivAPI:
    """ArXiv API 交互类 - 使用官方arxiv库"""

    def __init__(self, timeout: int = 30, download_dir: str = "downloads"):
        """初始化ArXiv API客户端"""
        self.timeout = timeout
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)

        # 配置arxiv客户端（使用正确的方式）
        self.client = arxiv.Client(page_size=100, delay_seconds=3.0, num_retries=3)

    def search_papers(
        self,
        query: str = None,
        categories: List[str] = None,
        max_results: int = 100,
        sort_by: arxiv.SortCriterion = arxiv.SortCriterion.SubmittedDate,
        sort_order: arxiv.SortOrder = arxiv.SortOrder.Descending,
        date_from: datetime = None,
        date_to: datetime = None,
    ) -> List[Dict[str, Any]]:
        """
        搜索ArXiv论文

        Args:
            query: 搜索查询字符串
            categories: 分类列表，如 ['cs.AI', 'cs.RO']
            max_results: 最大结果数
            sort_by: 排序字段
            sort_order: 排序顺序
            date_from: 开始日期
            date_to: 结束日期

        Returns:
            论文信息列表
        """
        try:
            # 构建搜索查询
            search_query = self._build_search_query(query, categories, date_from, date_to)

            print(f"🔍 搜索查询: {search_query}")

            # 创建搜索对象
            search = arxiv.Search(query=search_query, max_results=max_results, sort_by=sort_by, sort_order=sort_order)

            papers = []
            for result in self.client.results(search):
                paper_info = self._parse_arxiv_result(result)
                if paper_info:
                    papers.append(paper_info)

            print(f"✅ 成功获取 {len(papers)} 篇论文")
            return papers

        except Exception as e:
            print(f"❌ 搜索论文时出错: {e}")
            return []

    def get_recent_papers(
        self, days: int = 7, max_results: int = 300, categories: List[str] = None, field_type: str = "all"
    ) -> List[Dict[str, Any]]:
        """
        获取最近N天的论文

        Args:
            days: 天数范围
            max_results: 最大结果数
            categories: 分类列表
            field_type: 领域类型 (all, ai, robotics, cv, nlp)

        Returns:
            论文信息列表
        """
        # 根据field_type设置默认分类
        if categories is None:
            categories = self._get_field_categories(field_type)

        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        return self.search_papers(
            categories=categories, max_results=max_results, date_from=start_date, date_to=end_date
        )

    def download_pdf(
        self, paper: Dict[str, Any], force_download: bool = False, create_metadata: bool = True
    ) -> Tuple[bool, str]:
        """
        下载论文PDF

        Args:
            paper: 论文信息字典
            force_download: 是否强制重新下载
            create_metadata: 是否创建元数据文件

        Returns:
            tuple: (是否成功, 文件路径或错误信息)
        """
        try:
            arxiv_id = paper.get("arxiv_id", "")
            if not arxiv_id:
                return False, "论文ID无效"

            # 生成文件名
            safe_title = self._sanitize_filename(paper.get("title", ""))[:100]
            pdf_filename = f"{arxiv_id}_{safe_title}.pdf"
            pdf_path = self.download_dir / pdf_filename

            # 检查是否已存在
            if pdf_path.exists() and not force_download:
                return True, str(pdf_path)

            print(f"📥 下载论文: {paper.get('title', '')[:50]}...")

            # 获取arxiv结果对象
            search = arxiv.Search(id_list=[arxiv_id])
            result = next(self.client.results(search), None)

            if not result:
                return False, "无法找到论文"

            # 下载PDF
            result.download_pdf(dirpath=str(self.download_dir), filename=pdf_filename)

            # 创建元数据文件
            if create_metadata:
                self._create_paper_metadata(paper, pdf_path.with_suffix(".md"))

            print(f"✅ 下载完成: {pdf_filename}")
            return True, str(pdf_path)

        except Exception as e:
            error_msg = f"下载失败: {e}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def batch_download_pdfs(
        self, papers: List[Dict[str, Any]], max_downloads: int = 10, create_index: bool = True
    ) -> Dict[str, Any]:
        """
        批量下载PDF

        Args:
            papers: 论文列表
            max_downloads: 最大下载数量
            create_index: 是否创建索引文件

        Returns:
            下载统计信息
        """
        stats = {"total": len(papers), "downloaded": 0, "skipped": 0, "failed": 0, "failed_papers": []}

        download_count = 0
        downloaded_papers = []

        for paper in papers:
            if download_count >= max_downloads:
                break

            success, result = self.download_pdf(paper)
            if success:
                stats["downloaded"] += 1
                downloaded_papers.append({**paper, "pdf_path": result})
            else:
                if "已存在" in result:
                    stats["skipped"] += 1
                else:
                    stats["failed"] += 1
                    stats["failed_papers"].append({"title": paper.get("title", ""), "error": result})

            download_count += 1

        # 创建下载索引
        if create_index and downloaded_papers:
            self._create_download_index(downloaded_papers)

        return stats

    def _build_search_query(
        self, query: str = None, categories: List[str] = None, date_from: datetime = None, date_to: datetime = None
    ) -> str:
        """构建搜索查询字符串"""
        query_parts = []

        # 添加自定义查询
        if query:
            query_parts.append(f"({query})")

        # 添加分类查询
        if categories:
            category_query = " OR ".join([f"cat:{cat}" for cat in categories])
            query_parts.append(f"({category_query})")

        # 添加日期范围查询
        if date_from or date_to:
            date_parts = []

            if date_from:
                # 将datetime转换为YYYYMMDD格式
                date_from_str = date_from.strftime("%Y%m%d")
                date_parts.append(f"submittedDate:[{date_from_str}0000")

            if date_to:
                # 将datetime转换为YYYYMMDD格式
                date_to_str = date_to.strftime("%Y%m%d")
                if not date_from:
                    date_parts.append(f"submittedDate:[19910801 TO {date_to_str}2359]")
                else:
                    # 闭合之前的范围
                    date_parts[0] = f"submittedDate:[{date_from_str}0000 TO {date_to_str}2359]"
            elif date_from:
                # 只有开始日期，到当前日期
                current_date = datetime.now().strftime("%Y%m%d")
                date_parts[0] = f"submittedDate:[{date_from_str}0000 TO {current_date}2359]"

            if date_parts:
                query_parts.extend(date_parts)

        # 合并查询部分
        search_query = " AND ".join(query_parts) if query_parts else "all:*"

        return search_query

    def _parse_arxiv_result(self, result: arxiv.Result) -> Optional[Dict[str, Any]]:
        """解析arxiv.Result对象为论文信息字典"""
        try:
            return {
                "title": result.title.strip(),
                "authors": [author.name for author in result.authors],
                "authors_str": ", ".join([author.name for author in result.authors]),
                "summary": result.summary.strip(),
                "published_date": result.published,
                "updated_date": result.updated if result.updated else result.published,
                "paper_url": result.entry_id,
                "pdf_url": result.pdf_url,
                "categories": [cat for cat in result.categories],
                "categories_str": ", ".join(result.categories),
                "arxiv_id": result.entry_id.split("/")[-1],
                "primary_category": result.primary_category,
                "comment": result.comment if result.comment else "",
                "journal_ref": result.journal_ref if result.journal_ref else "",
                "doi": result.doi if result.doi else "",
            }
        except Exception as e:
            print(f"解析论文信息时出错: {e}")
            return None

    def _get_field_categories(self, field_type) -> List[str]:
        """
        根据领域类型获取分类列表，支持交集/并集操作

        支持的格式：
        - 单个字符串: "ai", "robotics"
        - 并集操作: "ai+robotics" 或 ["ai", "robotics"]
        - 交集操作: "ai&robotics" (目前ArXiv API不直接支持，返回并集)
        - 直接分类: "cs.AI" 或 ["cs.AI", "cs.LG"]
        """
        # 基础领域映射
        field_mappings = {
            "ai": ["cs.AI", "cs.LG", "stat.ML"],
            "robotics": ["cs.RO"],
            "cv": ["cs.CV", "eess.IV"],
            "nlp": ["cs.CL"],
            "physics": ["physics.comp-ph", "cond-mat", "quant-ph"],
            "math": ["math.OC", "math.ST", "math.NA"],
            "stat": ["stat.ML", "stat.ME", "stat.AP"],
            "eess": ["eess.IV", "eess.SP", "eess.AS"],
            "q-bio": ["q-bio.QM", "q-bio.GN", "q-bio.MN"],
            "all": ["cs.AI", "cs.LG", "cs.RO", "cs.CV", "cs.CL", "cs.CR", "cs.DC", "cs.DS", "cs.HC", "cs.IR"],
        }

        # 如果是列表，处理列表中的每个元素
        if isinstance(field_type, list):
            all_categories = []
            for field in field_type:
                all_categories.extend(self._parse_single_field(field, field_mappings))
            return list(set(all_categories))  # 去重

        # 如果是字符串，检查是否包含运算符
        if isinstance(field_type, str):
            return self._parse_field_string(field_type, field_mappings)

        # 默认返回all
        return field_mappings["all"]

    def _parse_field_string(self, field_str: str, field_mappings: dict) -> List[str]:
        """解析字段字符串，支持运算符"""
        field_str = field_str.strip()

        # 检查并集运算符 (+, |, or)
        if "+" in field_str or "|" in field_str or " or " in field_str.lower():
            # 分割并处理各个部分
            separators = ["+", "|", " or ", " OR "]
            parts = [field_str]

            for sep in separators:
                new_parts = []
                for part in parts:
                    new_parts.extend(part.split(sep))
                parts = new_parts

            all_categories = []
            for part in parts:
                part = part.strip()
                if part:
                    all_categories.extend(self._parse_single_field(part, field_mappings))

            return list(set(all_categories))  # 去重

        # 检查交集运算符 (&, and) - 注意：ArXiv API不直接支持交集
        elif "&" in field_str or " and " in field_str.lower():
            print("⚠️  注意：ArXiv API不直接支持分类交集查询，将转换为并集查询")
            # 将交集转换为并集处理
            separators = ["&", " and ", " AND "]
            parts = [field_str]

            for sep in separators:
                new_parts = []
                for part in parts:
                    new_parts.extend(part.split(sep))
                parts = new_parts

            all_categories = []
            for part in parts:
                part = part.strip()
                if part:
                    all_categories.extend(self._parse_single_field(part, field_mappings))

            return list(set(all_categories))

        # 单个字段
        else:
            return self._parse_single_field(field_str, field_mappings)

    def _parse_single_field(self, field: str, field_mappings: dict) -> List[str]:
        """解析单个字段"""
        field = field.strip()

        # 直接是ArXiv分类
        if field.startswith(("cs.", "stat.", "math.", "physics.", "eess.", "q-bio.", "quant-ph", "cond-mat")):
            return [field]

        # 查找预定义映射
        if field.lower() in field_mappings:
            return field_mappings[field.lower()]

        # 如果不在映射中，假设是自定义分类
        print(f"⚠️  未识别的领域类型: {field}，将尝试作为ArXiv分类使用")
        return [field]

    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除不合法字符"""
        # 移除或替换不合法字符
        invalid_chars = r'[<>:"/\\|?*]'
        sanitized = re.sub(invalid_chars, "_", filename)
        # 移除多余空格和标点
        sanitized = re.sub(r"\s+", "_", sanitized)
        sanitized = re.sub(r"[^\w\-_.]", "", sanitized)
        return sanitized.strip("_")

    def _create_paper_metadata(self, paper: Dict[str, Any], md_path: Path) -> None:
        """创建论文元数据Markdown文件"""
        try:
            content = f"""# {paper.get('title', 'Unknown Title')}

## 基本信息
- **ArXiv ID**: {paper.get('arxiv_id', 'N/A')}
- **发布日期**: {paper.get('published_date', 'N/A')}
- **主分类**: {paper.get('primary_category', 'N/A')}
- **所有分类**: {paper.get('categories_str', 'N/A')}

## 作者
{paper.get('authors_str', 'Unknown Authors')}

## 摘要
{paper.get('summary', 'No summary available')}

## 链接
- **论文页面**: {paper.get('paper_url', 'N/A')}
- **PDF下载**: {paper.get('pdf_url', 'N/A')}

## 其他信息
- **期刊引用**: {paper.get('journal_ref', 'N/A')}
- **DOI**: {paper.get('doi', 'N/A')}
- **备注**: {paper.get('comment', 'N/A')}

---
*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""

            with open(md_path, "w", encoding="utf-8") as f:
                f.write(content)

        except Exception as e:
            print(f"创建元数据文件失败: {e}")

    def _create_download_index(self, papers: List[Dict[str, Any]]) -> None:
        """创建下载索引文件"""
        try:
            index_path = self.download_dir / "README.md"

            content = f"""# ArXiv 论文下载索引

> 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
> 总计论文数: {len(papers)}

## 论文列表

"""

            for i, paper in enumerate(papers, 1):
                arxiv_id = paper.get("arxiv_id", "N/A")
                title = paper.get("title", "Unknown Title")
                authors = paper.get("authors_str", "Unknown Authors")
                categories = paper.get("categories_str", "N/A")
                published = paper.get("published_date", "N/A")

                content += f"""### {i}. {title}

- **ArXiv ID**: {arxiv_id}
- **作者**: {authors}
- **分类**: {categories}
- **发布**: {published}
- **链接**: [{arxiv_id}]({paper.get('paper_url', '#')}) | [PDF]({paper.get('pdf_url', '#')})

---

"""

            with open(index_path, "w", encoding="utf-8") as f:
                f.write(content)

            print(f"📝 创建下载索引: {index_path}")

        except Exception as e:
            print(f"创建索引文件失败: {e}")
