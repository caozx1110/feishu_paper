"""arXiv search execution, date windows, retries, and batching."""

from __future__ import annotations

import time
from datetime import datetime, timedelta
from typing import Any, Dict, List

import arxiv


class ArxivSearchMixin:
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

            search_page_sizes = [page_size for page_size in self.config.page_sizes if page_size <= max_results]
            if not search_page_sizes:
                search_page_sizes = [max(1, max_results)]

            for page_size in search_page_sizes:
                try:
                    # 重新配置客户端的page_size
                    self.client = self._create_client(page_size=page_size, delay_seconds=self.config.retry_delay_seconds)

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
                            if empty_page_count >= self.config.max_empty_pages:
                                print(f"⚠️  遇到{self.config.max_empty_pages}个连续空页面，尝试更小的page_size...")
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
