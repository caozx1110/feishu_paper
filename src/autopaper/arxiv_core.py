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
import time
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

    def __init__(self, timeout: Any = (5, 30), download_dir: str = "downloads"):
        """初始化ArXiv API客户端"""
        self.timeout = self._resolve_timeout(timeout)
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(exist_ok=True)

        # 配置arxiv客户端（使用正确的方式）
        # 初始设置较小的page_size以避免空页面问题
        self.initial_page_size = 500
        self.client = self._create_client(page_size=self.initial_page_size, delay_seconds=1.0)

    @staticmethod
    def _resolve_timeout(default_timeout: Any) -> Any:
        """读取ArXiv请求超时配置，避免网络异常时被系统TCP超时拖住。"""
        raw_timeout = os.getenv("ARXIV_REQUEST_TIMEOUT")
        if not raw_timeout:
            return default_timeout

        try:
            timeout_parts = [part.strip() for part in raw_timeout.split(",")]
            if len(timeout_parts) == 1:
                timeout = float(timeout_parts[0])
            elif len(timeout_parts) == 2:
                timeout = (float(timeout_parts[0]), float(timeout_parts[1]))
            else:
                raise ValueError
        except ValueError:
            print(f"⚠️  ARXIV_REQUEST_TIMEOUT={raw_timeout!r} 无效，使用默认 {default_timeout} 秒")
            return default_timeout

        if isinstance(timeout, tuple):
            invalid_timeout = timeout[0] <= 0 or timeout[1] <= 0
        else:
            invalid_timeout = timeout <= 0

        if invalid_timeout:
            print(f"⚠️  ARXIV_REQUEST_TIMEOUT={raw_timeout!r} 必须大于0，使用默认 {default_timeout} 秒")
            return default_timeout

        return timeout

    def _create_client(self, page_size: int, delay_seconds: float) -> arxiv.Client:
        client = arxiv.Client(page_size=page_size, delay_seconds=delay_seconds, num_retries=3)
        original_get = client._session.get
        request_timeout = self.timeout

        def get_with_timeout(url, **kwargs):
            kwargs.setdefault("timeout", request_timeout)
            return original_get(url, **kwargs)

        client._session.get = get_with_timeout
        return client

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
        搜索ArXiv论文，支持动态调整page_size以解决空页面问题

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
            empty_page_count = 0
            max_empty_pages = 3  # 最大允许的连续空页面数
            page_sizes_to_try = [500, 250, 100, 50, 10]  # 依次尝试的page_size

            for page_size in page_sizes_to_try:
                try:
                    # 重新配置客户端的page_size
                    self.client = self._create_client(page_size=page_size, delay_seconds=3.0)

                    print(f"📄 使用page_size={page_size}进行搜索...")

                    # 重新创建搜索对象
                    search = arxiv.Search(
                        query=search_query, max_results=max_results, sort_by=sort_by, sort_order=sort_order
                    )

                    papers = []
                    empty_page_count = 0
                    results_count = 0

                    for result in self.client.results(search):
                        paper_info = self._parse_arxiv_result(result)
                        if paper_info:
                            papers.append(paper_info)
                            results_count += 1
                            empty_page_count = 0  # 重置空页面计数

                        # 检查是否遇到连续空页面
                        if results_count == 0 and len(papers) == 0:
                            empty_page_count += 1
                            if empty_page_count >= max_empty_pages:
                                print(f"⚠️  遇到{max_empty_pages}个连续空页面，尝试更小的page_size...")
                                break

                    # 如果成功获取到论文，跳出循环
                    if papers:
                        print(f"✅ 成功获取 {len(papers)} 篇论文 (page_size={page_size})")
                        return papers

                except Exception as e:
                    print(f"❌ page_size={page_size}搜索失败: {e}")
                    continue

            # 如果所有page_size都失败了，返回空列表
            if not papers:
                print("⚠️  尝试所有page_size都未能获取论文，可能该日期范围内无相关论文")

            return papers

        except Exception as e:
            print(f"❌ 搜索论文时出错: {e}")
            return []

    def get_recent_papers(
        self,
        days: int = 7,
        max_results: int = 300,
        categories: List[str] = None,
        field_type: str = "all",
        batch_config: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        获取最近N天的论文，支持分批处理
        现在直接调用日期范围搜索接口以提高稳定性

        Args:
            days: 天数范围
            max_results: 最大结果数
            categories: 分类列表
            field_type: 领域类型 (all, ai, robotics, cv, nlp)
            batch_config: 分批处理配置

        Returns:
            论文信息列表
        """
        # 计算日期范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # 转换为日期字符串格式
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = end_date.strftime("%Y-%m-%d")

        print(f"📅 获取最近 {days} 天的论文 ({start_date_str} 到 {end_date_str})")

        # 直接调用日期范围搜索方法，复用其稳定的分批处理逻辑
        return self.get_papers_by_date_range(
            start_date=start_date_str,
            end_date=end_date_str,
            max_results=max_results,
            categories=categories,
            field_type=field_type,
            batch_config=batch_config,
        )

    def get_papers_by_date_range(
        self,
        start_date: str,
        end_date: str = None,
        max_results: int = 300,
        categories: List[str] = None,
        field_type: str = "all",
        batch_config: Dict[str, Any] = None,
    ) -> List[Dict[str, Any]]:
        """
        根据日期范围获取论文，支持分批处理

        Args:
            start_date: 开始日期，格式: "YYYY-MM-DD"
            end_date: 结束日期，格式: "YYYY-MM-DD"，为空时使用当前日期
            max_results: 最大结果数
            categories: 分类列表
            field_type: 领域类型
            batch_config: 分批处理配置

        Returns:
            论文信息列表
        """

        # 解析日期
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()
        except ValueError as e:
            print(f"❌ 日期格式错误: {e}")
            return []

        # 根据field_type设置默认分类
        if categories is None:
            categories = self._get_field_categories(field_type)
        # 如果field_type本身就是一个列表并且categories为None，直接使用field_type
        elif field_type and isinstance(field_type, list) and all(isinstance(item, str) for item in field_type):
            # 检查是否都是有效的ArXiv分类格式
            valid_prefixes = ("cs.", "stat.", "math.", "physics.", "eess.", "q-bio.", "quant-ph", "cond-mat")
            if all(item.startswith(valid_prefixes) for item in field_type):
                categories = field_type
                print(f"📋 使用直接指定的分类列表: {categories}")
            else:
                categories = self._get_field_categories(field_type)

        # 检查是否需要分批处理
        total_days = (end_dt - start_dt).days + 1

        # 默认分批处理配置
        default_batch_config = {
            "enabled": True,
            "max_days_per_batch": 7,
            "min_batch_interval": 1.0,
            "auto_split": True,
            "batch_overlap_days": 0,
        }

        if batch_config:
            default_batch_config.update(batch_config)

        batch_config = default_batch_config

        print(f"📅 日期范围: {start_date} 到 {end_date or '当前日期'} (共 {total_days} 天)")

        # 如果不启用分批处理或日期范围较小，直接搜索
        if not batch_config.get("enabled", True) or total_days <= batch_config.get("max_days_per_batch", 7):
            print("🔍 单次搜索...")
            return self.search_papers(
                categories=categories, max_results=max_results, date_from=start_dt, date_to=end_dt
            )

        # 分批处理
        return self._batch_search_papers(
            start_dt=start_dt, end_dt=end_dt, categories=categories, max_results=max_results, batch_config=batch_config
        )

    def _batch_search_papers(
        self,
        start_dt: datetime,
        end_dt: datetime,
        categories: List[str],
        max_results: int,
        batch_config: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        分批搜索论文

        Args:
            start_dt: 开始日期
            end_dt: 结束日期
            categories: 分类列表
            max_results: 最大结果数
            batch_config: 分批处理配置

        Returns:
            论文信息列表
        """

        max_days_per_batch = batch_config.get("max_days_per_batch", 7)
        min_batch_interval = batch_config.get("min_batch_interval", 1.0)
        batch_overlap_days = batch_config.get("batch_overlap_days", 0)

        all_papers = []
        seen_papers = set()  # 用于去重
        batch_num = 1

        current_start = start_dt

        print(f"🔄 启动分批处理，每批最多 {max_days_per_batch} 天，间隔 {min_batch_interval} 秒")

        while current_start <= end_dt:
            # 计算当前批次的结束日期
            current_end = min(current_start + timedelta(days=max_days_per_batch - 1), end_dt)

            print(f"📦 批次 {batch_num}: {current_start.strftime('%Y-%m-%d')} 到 {current_end.strftime('%Y-%m-%d')}")

            try:
                # 搜索当前批次
                batch_papers = self.search_papers(
                    categories=categories, max_results=max_results, date_from=current_start, date_to=current_end
                )

                # 去重并添加到总列表
                new_papers_count = 0
                for paper in batch_papers:
                    paper_id = paper.get("arxiv_id", "")
                    if paper_id and paper_id not in seen_papers:
                        seen_papers.add(paper_id)
                        all_papers.append(paper)
                        new_papers_count += 1

                print(f"✅ 批次 {batch_num} 完成: 获取 {len(batch_papers)} 篇论文，新增 {new_papers_count} 篇")

            except Exception as e:
                print(f"❌ 批次 {batch_num} 搜索失败: {e}")

            # 准备下一批次
            batch_num += 1

            # 计算下一批次的开始日期（考虑重叠）
            next_start = current_start + timedelta(days=max_days_per_batch - batch_overlap_days)
            current_start = next_start

            # 如果还有更多批次，则等待
            if current_start <= end_dt and min_batch_interval > 0:
                print(f"⏳ 等待 {min_batch_interval} 秒...")
                time.sleep(min_batch_interval)

        print(f"🎉 分批处理完成: 总共获取 {len(all_papers)} 篇去重后的论文")
        return all_papers

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


class PaperRanker:
    """论文智能排序和过滤类"""

    def __init__(self):
        """初始化排序器"""
        # 关键词权重分层
        self.keyword_weights = {
            "core": 2.5,  # 核心关键词权重（🎯标记的关键词）
            "extended": 1.5,  # 扩展关键词权重（🔧标记的关键词）
            "related": 1.0,  # 相关关键词权重
            "default": 1.0,  # 默认权重
        }

        # 匹配缓存
        self._match_cache = {}
        self._max_cache_size = 1000

        # 同义词词典 - 可以扩展
        self.synonyms = {
            "robot": ["robotics", "robotic", "autonomous agent", "android", "humanoid"],
            "ai": ["artificial intelligence", "machine intelligence", "intelligent system"],
            "ml": ["machine learning", "statistical learning", "automated learning"],
            "dl": ["deep learning", "neural network", "neural net", "deep neural network"],
            "cv": ["computer vision", "visual perception", "image analysis", "visual recognition"],
            "nlp": ["natural language processing", "language processing", "text processing"],
            "llm": ["large language model", "language model", "generative model"],
            "vla": ["vision language action", "vision-language-action", "multimodal action"],
            "slam": ["simultaneous localization and mapping", "localization and mapping"],
            "rl": ["reinforcement learning", "reward learning", "policy learning"],
            "transformer": ["attention mechanism", "self-attention", "multi-head attention"],
        }

        # 常见缩写扩展
        self.abbreviations = {
            "ai": "artificial intelligence",
            "ml": "machine learning",
            "dl": "deep learning",
            "cv": "computer vision",
            "nlp": "natural language processing",
            "llm": "large language model",
            "vla": "vision language action",
            "slam": "simultaneous localization and mapping",
            "rl": "reinforcement learning",
            "gnn": "graph neural network",
            "cnn": "convolutional neural network",
            "rnn": "recurrent neural network",
            "lstm": "long short term memory",
            "bert": "bidirectional encoder representations from transformers",
            "gpt": "generative pre-trained transformer",
        }

        # 技术领域关键词权重
        self.domain_weights = {
            "cs.AI": 1.5,
            "cs.LG": 1.4,
            "cs.RO": 1.3,
            "cs.CV": 1.2,
            "cs.CL": 1.2,
        }

    def check_required_keywords(
        self, paper: Dict[str, Any], required_keywords_config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        检查论文是否包含必须的关键词（支持AND和OR逻辑组合）

        支持的格式:
        - "robot" - 单个关键词
        - "A OR B" - A或B任选其一
        - ["mobile", "A OR B"] - 必须包含mobile且必须包含(A或B)

        Args:
            paper: 论文信息字典
            required_keywords_config: 必须包含关键词配置

        Returns:
            tuple: (是否通过检查, 实际匹配到的关键词列表)
        """
        if not required_keywords_config.get("enabled", False):
            return True, []

        required_keywords = required_keywords_config.get("keywords", [])
        if not required_keywords:
            return True, []

        # 提取论文文本信息
        title = paper.get("title", "").lower()
        summary = paper.get("summary", "").lower()
        categories = paper.get("categories", [])
        categories_str = " ".join(categories).lower()
        authors = paper.get("authors_str", "").lower()

        # 组合所有文本用于搜索
        full_text = f"{title} {summary} {categories_str} {authors}"

        fuzzy_match = required_keywords_config.get("fuzzy_match", True)
        similarity_threshold = required_keywords_config.get("similarity_threshold", 0.8)

        all_matched_keywords = []

        # 检查所有关键词项是否都匹配（AND逻辑：全部必须匹配）
        for keyword_item in required_keywords:
            matched_keywords = self._check_keyword_item_detailed(
                keyword_item, full_text, fuzzy_match, similarity_threshold
            )
            if matched_keywords:
                # 添加实际匹配到的关键词
                all_matched_keywords.extend(matched_keywords)
            else:
                # 如果有任何一个关键词项不匹配，则直接返回False
                return False, []

        # 所有关键词项都匹配才通过检查
        return True, all_matched_keywords

    def _check_keyword_item_detailed(
        self, keyword_item: str, full_text: str, fuzzy_match: bool, similarity_threshold: float
    ) -> List[str]:
        """
        检查单个关键词项并返回具体匹配的关键词

        Args:
            keyword_item: 关键词项，可能是单个关键词或包含OR的组合
            full_text: 论文全文
            fuzzy_match: 是否启用模糊匹配
            similarity_threshold: 模糊匹配阈值

        Returns:
            List[str]: 匹配到的具体关键词列表
        """
        # 检查是否包含OR逻辑
        if " or " in keyword_item.lower() or " OR " in keyword_item:
            return self._check_or_keyword_detailed(keyword_item, full_text, fuzzy_match, similarity_threshold)
        else:
            # 单个关键词
            if self._check_single_keyword(keyword_item, full_text, fuzzy_match, similarity_threshold):
                return [keyword_item]
            else:
                return []

    def _check_or_keyword_detailed(
        self, or_keyword: str, full_text: str, fuzzy_match: bool, similarity_threshold: float
    ) -> List[str]:
        """
        检查OR逻辑关键词并返回所有匹配的关键词

        Args:
            or_keyword: 包含OR的关键词字符串，如 "A OR B OR C"
            full_text: 论文全文
            fuzzy_match: 是否启用模糊匹配
            similarity_threshold: 模糊匹配阈值

        Returns:
            List[str]: 匹配到的具体关键词列表
        """
        # 分割OR关键词
        or_parts = []
        if " OR " in or_keyword:
            or_parts = [part.strip() for part in or_keyword.split(" OR ")]
        elif " or " in or_keyword:
            or_parts = [part.strip() for part in or_keyword.split(" or ")]

        if len(or_parts) < 2:
            return []

        matched_keywords = []
        # 检查所有部分，收集所有匹配的关键词
        for part in or_parts:
            if self._check_single_keyword(part, full_text, fuzzy_match, similarity_threshold):
                matched_keywords.append(part)

        return matched_keywords

    def _check_single_keyword(
        self, keyword: str, full_text: str, fuzzy_match: bool, similarity_threshold: float
    ) -> bool:
        """
        检查单个关键词是否匹配

        Args:
            keyword: 关键词
            full_text: 论文全文
            fuzzy_match: 是否启用模糊匹配
            similarity_threshold: 模糊匹配阈值

        Returns:
            bool: 是否匹配
        """
        keyword_lower = keyword.lower()

        # 精确匹配
        if keyword_lower in full_text:
            return True

        # 模糊匹配（如果启用）
        if fuzzy_match:
            # 检查关键词变体
            keyword_variants = self._generate_keyword_variants(keyword)

            for variant in keyword_variants:
                if variant.lower() in full_text:
                    return True

            # 使用字符串相似度匹配
            if self._fuzzy_match_required_keyword(keyword_lower, full_text, similarity_threshold):
                return True

        return False

    def _generate_keyword_variants(self, keyword: str) -> List[str]:
        """
        生成关键词变体

        Args:
            keyword: 原始关键词

        Returns:
            关键词变体列表
        """
        variants = [keyword]
        keyword_lower = keyword.lower()

        # 从同义词词典获取变体
        for syn_key, syn_list in self.synonyms.items():
            if syn_key in keyword_lower or keyword_lower in syn_key:
                variants.extend(syn_list)

        # 生成常见变体
        # 复数形式
        if not keyword.endswith("s"):
            variants.append(keyword + "s")
        if keyword.endswith("y"):
            variants.append(keyword[:-1] + "ies")

        # 形容词形式
        if keyword.endswith("e"):
            variants.append(keyword[:-1] + "ic")
        else:
            variants.append(keyword + "ic")

        # 连字符和空格变体
        if " " in keyword:
            variants.append(keyword.replace(" ", "-"))
            variants.append(keyword.replace(" ", "_"))
            variants.append(keyword.replace(" ", ""))
        if "-" in keyword:
            variants.append(keyword.replace("-", " "))
            variants.append(keyword.replace("-", "_"))
            variants.append(keyword.replace("-", ""))

        # 去除重复并返回
        return list(set(variants))

    def _fuzzy_match_required_keyword(self, keyword: str, text: str, threshold: float) -> bool:
        """
        对必须关键词进行模糊匹配

        Args:
            keyword: 关键词
            text: 待匹配文本
            threshold: 相似度阈值

        Returns:
            是否匹配
        """
        try:
            from difflib import SequenceMatcher

            # 分词处理
            words = text.split()

            # 检查与单个词的相似度
            for word in words:
                if len(word) >= 3:  # 只检查长度大于等于3的词
                    similarity = SequenceMatcher(None, keyword, word).ratio()
                    if similarity >= threshold:
                        return True

            # 检查与词组的相似度
            keyword_words = keyword.split()
            if len(keyword_words) > 1:
                for i in range(len(words) - len(keyword_words) + 1):
                    phrase = " ".join(words[i : i + len(keyword_words)])
                    similarity = SequenceMatcher(None, keyword, phrase).ratio()
                    if similarity >= threshold:
                        return True

            return False

        except ImportError:
            # 如果没有difflib，使用简单的包含检查
            return keyword in text

    def calculate_relevance_score(
        self,
        paper: Dict[str, Any],
        interest_keywords: List[str] = None,
        exclude_keywords: List[str] = None,
        raw_interest_keywords: List[str] = None,
    ) -> Tuple[float, bool, List[str], List[str]]:
        """
        计算论文与关注词条的相关性评分 (增强版)

        支持通配符匹配：
        - "*" 或 ["*"] 匹配所有文章
        - 以 "regex:" 开头的关键词会被当作正则表达式处理
        - 支持分层权重系统：🎯核心概念、🔧扩展概念

        Args:
            paper: 论文信息字典
            interest_keywords: 关注词条列表（已过滤的），越前面权重越高
            exclude_keywords: 排除词条列表
            raw_interest_keywords: 原始关键词列表（包含注释行，用于权重分析）

        Returns:
            tuple: (relevance_score, is_excluded, matched_interests, matched_excludes)
        """
        if not interest_keywords:
            return 0.0, False, [], []

        # 解析分层权重（如果提供了原始关键词列表）
        keyword_categories = {}
        if raw_interest_keywords:
            keyword_categories = self._parse_keyword_weights(raw_interest_keywords)

        # 检查通配符匹配（匹配所有文章）
        if self._is_wildcard_match(interest_keywords):
            return 1.0, False, ["*"], []

        # 提取论文文本信息
        title = paper.get("title", "").lower()
        summary = paper.get("summary", "").lower()
        categories = paper.get("categories", [])
        categories_str = " ".join(categories).lower()
        authors = paper.get("authors_str", "").lower()
        paper_date = paper.get("published_date", datetime.now())

        # 组合所有文本用于搜索
        full_text = f"{title} {summary} {categories_str} {authors}"

        # 扩展关键词
        expanded_interests = self._expand_keywords(interest_keywords)
        expanded_excludes = self._expand_keywords(exclude_keywords) if exclude_keywords else []

        # 检查排除词条 (使用扩展后的词条)
        excluded = False
        matched_excludes = []
        if expanded_excludes:
            for exclude_term in expanded_excludes:
                if exclude_term.lower() in full_text:
                    excluded = True
                    matched_excludes.append(exclude_term)

                # 模糊匹配检查
                fuzzy_score = self._fuzzy_match_score(exclude_term, full_text, threshold=0.9)
                if fuzzy_score > 0:
                    excluded = True
                    matched_excludes.append(f"{exclude_term}(模糊匹配)")

        # 如果被排除，直接返回
        if excluded:
            return -999.0, True, [], matched_excludes

        # 计算关注词条匹配得分 (增强版)
        relevance_score = 0.0
        matched_interests = []

        # 时间衰减权重
        time_weight = self._calculate_time_decay(paper_date)

        # 领域相关性权重
        domain_weight = self._calculate_domain_relevance(categories)

        # 共现检测
        cooccurrence_bonus = self._detect_cooccurrence(expanded_interests, full_text)

        for i, keyword in enumerate(interest_keywords):
            keyword_lower = keyword.lower()

            # 基础权重：越靠前的词条权重越高
            base_weight = len(interest_keywords) - i

            # 增强的关键词匹配（支持正则表达式）
            enhanced_matched, enhanced_score = self._enhance_keyword_matching(keyword, full_text)

            if enhanced_matched:
                matched_interests.append(keyword)

                # 获取分层权重
                tier_weight = self._get_keyword_weight(keyword, keyword_categories)

                final_score = (
                    enhanced_score * base_weight * tier_weight * time_weight * domain_weight * cooccurrence_bonus
                )
                relevance_score += final_score
                continue  # 如果增强匹配成功，跳过后续处理

            # 检查原关键词和扩展关键词
            all_variants = [keyword_lower] + [syn.lower() for syn in self.synonyms.get(keyword_lower, [])]

            keyword_score = 0.0
            keyword_matched = False

            for variant in all_variants:
                # 精确匹配
                position_weights = self._calculate_position_weight(variant, title, summary)
                exact_score = sum(position_weights.values())

                if exact_score > 0:
                    keyword_matched = True
                    keyword_score += exact_score

                # 模糊匹配
                fuzzy_title_score = self._fuzzy_match_score(variant, title, threshold=0.8)
                fuzzy_summary_score = self._fuzzy_match_score(variant, summary, threshold=0.8)

                if fuzzy_title_score > 0:
                    keyword_matched = True
                    keyword_score += fuzzy_title_score * 2.0  # 标题模糊匹配权重

                if fuzzy_summary_score > 0:
                    keyword_matched = True
                    keyword_score += fuzzy_summary_score * 1.0  # 摘要模糊匹配权重

                # 分类匹配
                category_matches = len(re.findall(r"\b" + re.escape(variant) + r"\b", categories_str))
                if category_matches > 0:
                    keyword_matched = True
                    keyword_score += category_matches * 1.5

            if keyword_matched:
                matched_interests.append(keyword)

                # 获取分层权重
                tier_weight = self._get_keyword_weight(keyword, keyword_categories)

                # 综合计算最终分数（添加分层权重）
                final_score = (
                    keyword_score * base_weight * tier_weight * time_weight * domain_weight * cooccurrence_bonus
                )
                relevance_score += final_score

        return relevance_score, excluded, matched_interests, matched_excludes

    def filter_and_rank_papers(
        self,
        papers: List[Dict[str, Any]],
        interest_keywords: List[str] = None,
        exclude_keywords: List[str] = None,
        min_score: float = 0.1,
        use_advanced_scoring: bool = False,
        score_weights: Dict[str, float] = None,
        raw_interest_keywords: List[str] = None,
        required_keywords_config: Dict[str, Any] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        根据关注词条过滤和排序论文 (支持高级评分和必须关键词)

        Args:
            papers: 论文列表
            interest_keywords: 关注词条列表 (按重要性排序)
            exclude_keywords: 排除词条列表
            min_score: 最小相关性分数阈值
            use_advanced_scoring: 是否使用高级智能评分
            score_weights: 评分权重配置
            required_keywords_config: 必须包含关键词配置

        Returns:
            tuple: (ranked_papers, excluded_papers, score_stats)
        """
        if not papers:
            return [], [], {}

        # 默认评分权重
        if score_weights is None:
            score_weights = {"base": 1.0, "semantic": 0.3, "author": 0.2, "novelty": 0.4, "citation": 0.3}

        # 计算每篇论文的相关性分数
        scored_papers = []
        excluded_papers = []

        for paper in papers:
            # 首先检查必须包含关键词
            if required_keywords_config:
                required_passed, required_matches = self.check_required_keywords(paper, required_keywords_config)
                if not required_passed:
                    paper["exclude_reason"] = "未包含必须关键词"
                    excluded_papers.append(paper)
                    continue
                else:
                    paper["required_keyword_matches"] = required_matches

            # 如果没有关注词条，只进行排除过滤
            if not interest_keywords:
                if exclude_keywords:
                    _, is_excluded, _, _ = self.calculate_relevance_score(
                        paper, [], exclude_keywords, raw_interest_keywords
                    )
                    if is_excluded:
                        excluded_papers.append(paper)
                    else:
                        scored_papers.append(paper)
                else:
                    scored_papers.append(paper)
                continue

            if use_advanced_scoring:
                # 使用高级评分
                total_score, is_excluded, matched_interests, matched_excludes, score_breakdown = (
                    self.calculate_advanced_relevance_score(
                        paper, interest_keywords, exclude_keywords, True, True, raw_interest_keywords
                    )
                )

                # 应用权重
                final_score = (
                    score_breakdown.get("base_score", 0) * score_weights["base"]
                    + score_breakdown.get("semantic_boost", 0) * score_weights["semantic"]
                    + score_breakdown.get("author_boost", 0) * score_weights["author"]
                    + score_breakdown.get("novelty_boost", 0) * score_weights["novelty"]
                    + score_breakdown.get("citation_potential", 0) * score_weights["citation"]
                )

                paper["score_breakdown"] = score_breakdown
                paper["final_score"] = final_score

            else:
                # 使用基础评分
                final_score, is_excluded, matched_interests, matched_excludes = self.calculate_relevance_score(
                    paper, interest_keywords, exclude_keywords, raw_interest_keywords
                )

            if is_excluded:
                paper["exclude_reason"] = matched_excludes
                excluded_papers.append(paper)
            else:
                paper["relevance_score"] = final_score
                paper["matched_interests"] = matched_interests
                paper["interest_match_count"] = len(matched_interests)

                if final_score >= min_score:
                    scored_papers.append(paper)

        # 按相关性分数降序排序
        sort_key = "final_score" if use_advanced_scoring else "relevance_score"
        ranked_papers = sorted(scored_papers, key=lambda x: x.get(sort_key, 0), reverse=True)

        # 统计信息
        scores = [p.get(sort_key, 0) for p in ranked_papers]
        required_filtered = len([p for p in excluded_papers if p.get("exclude_reason") == "未包含必须关键词"])

        score_stats = {
            "total_papers": len(papers),
            "ranked_papers": len(ranked_papers),
            "excluded_papers": len(excluded_papers),
            "required_filtered": required_filtered,
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "use_advanced_scoring": use_advanced_scoring,
        }

        return ranked_papers, excluded_papers, score_stats

    def get_field_papers(self, papers: List[Dict[str, Any]], field_type: str) -> List[Dict[str, Any]]:
        """根据领域类型过滤论文"""
        field_keywords = {
            "ai": {
                "keywords": [
                    "artificial intelligence",
                    "AI",
                    "machine intelligence",
                    "deep learning",
                    "neural network",
                ],
                "categories": ["cs.AI", "cs.LG", "stat.ML"],
            },
            "robotics": {
                "keywords": [
                    "robot",
                    "robotics",
                    "robotic",
                    "autonomous",
                    "navigation",
                    "manipulation",
                    "SLAM",
                    "motion planning",
                    "path planning",
                    "humanoid",
                    "quadruped",
                    "mobile robot",
                ],
                "categories": ["cs.RO"],
            },
            "cv": {
                "keywords": [
                    "computer vision",
                    "image processing",
                    "visual",
                    "object detection",
                    "image recognition",
                    "video analysis",
                ],
                "categories": ["cs.CV", "eess.IV"],
            },
            "nlp": {
                "keywords": [
                    "natural language",
                    "NLP",
                    "language model",
                    "text processing",
                    "machine translation",
                    "sentiment analysis",
                ],
                "categories": ["cs.CL"],
            },
        }

        if field_type not in field_keywords:
            return papers

        field_config = field_keywords[field_type]
        filtered_papers = []

        for paper in papers:
            # 检查分类匹配
            if any(cat in paper.get("categories", []) for cat in field_config["categories"]):
                filtered_papers.append(paper)
                continue

            # 检查关键词匹配
            title_lower = paper["title"].lower()
            summary_lower = paper["summary"].lower()

            for keyword in field_config["keywords"]:
                if keyword.lower() in title_lower or keyword.lower() in summary_lower:
                    filtered_papers.append(paper)
                    break

        return filtered_papers

    def _expand_keywords(self, keywords: List[str]) -> List[str]:
        """扩展关键词列表，包含同义词和缩写"""
        expanded = set(keywords)

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # 添加缩写扩展
            if keyword_lower in self.abbreviations:
                expanded.add(self.abbreviations[keyword_lower])

            # 添加同义词
            if keyword_lower in self.synonyms:
                expanded.update(self.synonyms[keyword_lower])

            # 反向查找 - 如果输入的是全称，也要包含缩写
            for abbr, full_term in self.abbreviations.items():
                if keyword_lower == full_term:
                    expanded.add(abbr)

        return list(expanded)

    def _fuzzy_match_score(self, keyword: str, text: str, threshold: float = 0.8) -> float:
        """计算模糊匹配分数 - 优化版本，使用 rapidfuzz"""
        if RAPIDFUZZ_AVAILABLE:
            return self._rapidfuzz_match_score(keyword, text, threshold)
        else:
            return self._fallback_fuzzy_match(keyword, text, threshold)

    def _rapidfuzz_match_score(self, keyword: str, text: str, threshold: float = 0.8) -> float:
        """使用 rapidfuzz 进行快速模糊匹配"""
        keyword_lower = keyword.lower()

        # 快速检查精确匹配
        if keyword_lower in text.lower():
            return 1.0

        # 分词并限制检查范围以提高效率
        words = re.findall(r"\b\w+\b", text.lower())
        if not words:
            return 0.0

        # 限制检查的词数以提高效率（rapidfuzz 很快，可以检查更多词）
        check_words = words[:100] if len(words) > 100 else words

        # 使用 rapidfuzz 进行快速模糊匹配
        best_match = process.extractOne(keyword_lower, check_words, scorer=fuzz.ratio, score_cutoff=threshold * 100)

        return best_match[1] / 100.0 if best_match else 0.0

    def _fallback_fuzzy_match(self, keyword: str, text: str, threshold: float = 0.8) -> float:
        """备用模糊匹配方法（rapidfuzz 不可用时使用 difflib）"""
        if not RAPIDFUZZ_AVAILABLE:
            import difflib

        keyword_lower = keyword.lower()

        # 快速检查精确匹配
        if keyword_lower in text.lower():
            return 1.0

        words = re.findall(r"\b\w+\b", text.lower())
        if not words:
            return 0.0

        max_similarity = 0.0
        # 限制检查的词数以提高效率（difflib 较慢，减少检查词数）
        check_words = words[:30] if len(words) > 30 else words

        for word in check_words:
            # 跳过过短的词
            if len(word) < 3:
                continue

            if RAPIDFUZZ_AVAILABLE:
                # 如果 rapidfuzz 可用，使用它
                similarity = fuzz.ratio(keyword_lower, word) / 100.0
            else:
                # 否则使用 difflib
                similarity = difflib.SequenceMatcher(None, keyword_lower, word).ratio()

            if similarity >= threshold:
                max_similarity = max(max_similarity, similarity)
                # 如果找到非常好的匹配，提前终止
                if similarity > 0.95:
                    break

        return max_similarity

    def _calculate_time_decay(self, paper_date: datetime, decay_days: int = 30) -> float:
        """计算时间衰减权重 - 较新的论文权重更高"""
        # 处理时区问题
        if paper_date.tzinfo is not None:
            paper_date = paper_date.replace(tzinfo=None)

        days_ago = (datetime.now() - paper_date).days
        if days_ago <= 0:
            return 1.0
        elif days_ago <= decay_days:
            # 线性衰减
            return 1.0 - (days_ago / decay_days) * 0.3  # 最多衰减30%
        else:
            return 0.7  # 最小权重

    def _calculate_domain_relevance(self, categories: List[str]) -> float:
        """根据论文分类计算领域相关性权重"""
        max_weight = 1.0
        for category in categories:
            if category in self.domain_weights:
                max_weight = max(max_weight, self.domain_weights[category])
        return max_weight

    def _detect_cooccurrence(self, keywords: List[str], text: str) -> float:
        """检测关键词共现，提升相关性"""
        text_lower = text.lower()
        found_keywords = []

        for keyword in keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)

        # 共现奖励 - 同时出现多个关键词时给予额外分数
        cooccurrence_count = len(found_keywords)
        if cooccurrence_count >= 2:
            # 共现奖励系数
            return 1.0 + (cooccurrence_count - 1) * 0.2
        return 1.0

    def _calculate_position_weight(self, keyword: str, title: str, summary: str) -> Dict[str, float]:
        """计算关键词在不同位置的权重"""
        weights = {"title": 0.0, "summary_start": 0.0, "summary_mid": 0.0}

        keyword_lower = keyword.lower()
        title_lower = title.lower()
        summary_lower = summary.lower()

        # 标题中的权重
        if keyword_lower in title_lower:
            title_words = title_lower.split()
            keyword_position = -1
            for i, word in enumerate(title_words):
                if keyword_lower in word:
                    keyword_position = i
                    break

            if keyword_position != -1:
                # 标题开头的词权重更高
                position_factor = max(0.5, 1.0 - (keyword_position / len(title_words)) * 0.5)
                weights["title"] = 3.0 * position_factor

        # 摘要中的权重 - 区分前半部分和后半部分
        if keyword_lower in summary_lower:
            summary_length = len(summary_lower)
            keyword_pos = summary_lower.find(keyword_lower)

            if keyword_pos < summary_length * 0.3:  # 前30%
                weights["summary_start"] = 2.5
            else:  # 其他位置
                weights["summary_mid"] = 1.5

        return weights

    def calculate_advanced_relevance_score(
        self,
        paper: Dict[str, Any],
        interest_keywords: List[str] = None,
        exclude_keywords: List[str] = None,
        use_semantic_boost: bool = True,
        use_author_analysis: bool = True,
        raw_interest_keywords: List[str] = None,
    ) -> Tuple[float, bool, List[str], List[str], Dict[str, Any]]:
        """
        高级相关性评分计算 (包含更多智能特性)

        Args:
            paper: 论文信息字典
            interest_keywords: 关注词条列表
            exclude_keywords: 排除词条列表
            use_semantic_boost: 是否使用语义增强
            use_author_analysis: 是否分析作者信息

        Returns:
            tuple: (relevance_score, is_excluded, matched_interests, matched_excludes, score_breakdown)
        """
        # 基础评分
        base_score, excluded, matched_interests, matched_excludes = self.calculate_relevance_score(
            paper, interest_keywords, exclude_keywords, raw_interest_keywords
        )

        if excluded:
            return base_score, excluded, matched_interests, matched_excludes, {}

        score_breakdown = {
            "base_score": base_score,
            "semantic_boost": 0.0,
            "author_boost": 0.0,
            "novelty_boost": 0.0,
            "citation_potential": 0.0,
        }

        total_score = base_score

        # 语义增强分析
        if use_semantic_boost and interest_keywords:
            semantic_boost = self._calculate_semantic_boost(paper, interest_keywords)
            score_breakdown["semantic_boost"] = semantic_boost
            total_score += semantic_boost

        # 作者分析增强
        if use_author_analysis:
            author_boost = self._calculate_author_relevance(paper, interest_keywords)
            score_breakdown["author_boost"] = author_boost
            total_score += author_boost

        # 新颖性分析
        novelty_boost = self._calculate_novelty_score(paper)
        score_breakdown["novelty_boost"] = novelty_boost
        total_score += novelty_boost

        # 引用潜力预测
        citation_potential = self._predict_citation_potential(paper)
        score_breakdown["citation_potential"] = citation_potential
        total_score += citation_potential

        return total_score, excluded, matched_interests, matched_excludes, score_breakdown

    def _calculate_semantic_boost(self, paper: Dict[str, Any], keywords: List[str]) -> float:
        """计算语义相关性增强分数"""
        title = paper.get("title", "").lower()
        summary = paper.get("summary", "").lower()

        # 技术术语共现分析
        tech_terms = [
            "neural",
            "learning",
            "model",
            "algorithm",
            "method",
            "approach",
            "framework",
            "system",
            "network",
            "optimization",
            "training",
            "inference",
            "prediction",
            "classification",
            "regression",
        ]

        tech_term_count = sum(1 for term in tech_terms if term in title + " " + summary)

        # 基于技术密度的语义增强
        semantic_boost = min(tech_term_count * 0.1, 1.0)

        # 关键词语境分析
        context_boost = 0.0
        for keyword in keywords:
            keyword_lower = keyword.lower()

            # 寻找关键词附近的相关术语
            for text in [title, summary]:
                sentences = re.split(r"[.!?]", text)
                for sentence in sentences:
                    if keyword_lower in sentence:
                        # 分析句子中的其他技术术语
                        sentence_tech_terms = sum(1 for term in tech_terms if term in sentence)
                        context_boost += sentence_tech_terms * 0.05

        return semantic_boost + min(context_boost, 0.5)

    def _calculate_author_relevance(self, paper: Dict[str, Any], keywords: List[str]) -> float:
        """基于作者信息计算相关性增强"""
        authors = paper.get("authors", [])
        if not authors:
            return 0.0

        # 作者数量对研究质量的影响 (适中的作者数量通常较好)
        author_count = len(authors)
        if 2 <= author_count <= 6:
            author_count_boost = 0.2
        elif author_count == 1:
            author_count_boost = 0.1  # 单作者可能是理论性强的工作
        else:
            author_count_boost = 0.0  # 作者过多可能质量参差不齐

        # 分析作者姓名中的机构信息 (通过邮箱域名等)
        institution_boost = 0.0
        # 这里可以扩展为从作者附加信息中提取机构相关性

        return author_count_boost + institution_boost

    def _calculate_novelty_score(self, paper: Dict[str, Any]) -> float:
        """计算论文新颖性分数"""
        title = paper.get("title", "").lower()
        summary = paper.get("summary", "").lower()

        # 新颖性指示词
        novelty_indicators = [
            "novel",
            "new",
            "first",
            "introduce",
            "propose",
            "present",
            "innovative",
            "breakthrough",
            "pioneer",
            "original",
            "unprecedented",
            "state-of-the-art",
            "sota",
            "outperform",
            "improve",
            "enhance",
            "advance",
            "superior",
            "better than",
        ]

        novelty_count = 0
        for indicator in novelty_indicators:
            novelty_count += len(re.findall(r"\b" + re.escape(indicator) + r"\b", title + " " + summary))

        # 标题中的新颖性词汇权重更高
        title_novelty = sum(1 for indicator in novelty_indicators if indicator in title)

        novelty_score = min((novelty_count * 0.1) + (title_novelty * 0.2), 1.0)
        return novelty_score

    def _predict_citation_potential(self, paper: Dict[str, Any]) -> float:
        """预测论文的引用潜力"""
        title = paper.get("title", "").lower()
        summary = paper.get("summary", "").lower()
        categories = paper.get("categories", [])

        # 高引用潜力指标
        high_impact_terms = [
            "benchmark",
            "dataset",
            "survey",
            "review",
            "framework",
            "open source",
            "code available",
            "reproducible",
            "evaluation",
            "comparison",
            "analysis",
            "comprehensive",
            "extensive",
        ]

        impact_count = sum(1 for term in high_impact_terms if term in title + " " + summary)

        # 热门领域加权
        hot_categories = ["cs.AI", "cs.LG", "cs.CV", "cs.CL", "cs.RO"]
        category_boost = 0.2 if any(cat in hot_categories for cat in categories) else 0.0

        # 论文长度预测 (更长的摘要通常表示更全面的工作)
        length_boost = min(len(summary) / 1000, 0.3)  # 摘要长度归一化

        citation_potential = min((impact_count * 0.15) + category_boost + length_boost, 1.0)
        return citation_potential

    def _is_wildcard_match(self, keywords: List[str]) -> bool:
        """
        检查是否为通配符匹配（匹配所有文章）
        """
        if not keywords:
            return False

        # 检查是否包含通配符
        wildcard_patterns = ["*", "all", ".*", "全部", "所有"]
        for keyword in keywords:
            if keyword.lower().strip() in wildcard_patterns:
                return True

        # 如果只有一个关键词且为空或只有空白字符
        if len(keywords) == 1 and not keywords[0].strip():
            return True

        return False

    def _is_regex_keyword(self, keyword: str) -> bool:
        """
        检查关键词是否为正则表达式模式
        """
        return keyword.startswith("regex:") or keyword.startswith("re:")

    def _process_regex_keyword(self, keyword: str, text: str) -> bool:
        """
        处理正则表达式关键词匹配
        """
        try:
            if keyword.startswith("regex:"):
                pattern = keyword[6:].strip()  # 移除 "regex:" 前缀
            elif keyword.startswith("re:"):
                pattern = keyword[3:].strip()  # 移除 "re:" 前缀
            else:
                return False

            # 编译并匹配正则表达式
            regex = re.compile(pattern, re.IGNORECASE)
            return bool(regex.search(text))
        except re.error:
            # 如果正则表达式无效，回退到普通字符串匹配
            return keyword.lower() in text.lower()

    def _enhance_keyword_matching(self, keyword: str, text: str) -> Tuple[bool, float]:
        """
        增强的关键词匹配，支持正则表达式和通配符

        Returns:
            tuple: (是否匹配, 匹配分数)
        """
        # 正则表达式匹配
        if self._is_regex_keyword(keyword):
            matched = self._process_regex_keyword(keyword, text)
            return matched, 1.0 if matched else 0.0

        # 普通字符串匹配
        if keyword.lower() in text.lower():
            return True, 1.0

        # 模糊匹配
        fuzzy_score = self._fuzzy_match_score(keyword, text, threshold=0.8)
        if fuzzy_score > 0:
            return True, fuzzy_score

        return False, 0.0

    def _parse_keyword_weights(self, raw_keywords: List[str]) -> Dict[str, str]:
        """
        解析原始关键词列表，确定每个关键词的权重类别

        Args:
            raw_keywords: 包含注释行的原始关键词列表

        Returns:
            字典，键为关键词，值为权重类别 ('core', 'extended', 'default')
        """
        keyword_categories = {}
        current_category = "default"

        for keyword in raw_keywords:
            keyword = keyword.strip()

            # 跳过空行
            if not keyword:
                continue

            # 检查注释行，确定当前分类
            if keyword.startswith("#"):
                if "🎯" in keyword or "核心概念" in keyword or "高权重" in keyword:
                    current_category = "core"
                elif "🔧" in keyword or "扩展概念" in keyword or "中权重" in keyword:
                    current_category = "extended"
                elif "📝" in keyword or "相关概念" in keyword or "标准权重" in keyword:
                    current_category = "related"
                # 注释行本身不作为关键词
                continue

            # 为非注释的关键词分配类别
            keyword_categories[keyword] = current_category

        return keyword_categories

    def _get_keyword_weight(self, keyword: str, keyword_categories: Dict[str, str]) -> float:
        """
        获取关键词的权重倍数

        Args:
            keyword: 关键词
            keyword_categories: 关键词分类字典

        Returns:
            权重倍数
        """
        category = keyword_categories.get(keyword, "default")
        return self.keyword_weights.get(category, self.keyword_weights["default"])
