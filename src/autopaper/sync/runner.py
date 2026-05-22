"""Batch sync orchestration for AutoPaper."""

from __future__ import annotations

import os
import traceback
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, Union

from omegaconf import DictConfig

from ..configuration.keywords import load_keywords_from_config
from ..configuration.loader import find_sync_configs, load_config, normalize_config
from ..core import PaperRanker, SearchService, create_arxiv_api
from ..terminal import debug, print, section, table

try:
    from ..feishu import FeishuSyncResult, create_chat_notifier_from_config, sync_papers_to_feishu

    FEISHU_AVAILABLE = True
except ImportError:
    FEISHU_AVAILABLE = False


@dataclass
class SyncOptions:
    """User-facing safety switches for sync commands."""

    dry_run: bool = False
    no_feishu: bool = False
    no_notify: bool = False
    limit: Optional[int] = None
    since_days: Optional[int] = None
    verbose: bool = False


@dataclass
class SyncRunner:
    """Run one or many sync configs using the package service layer."""

    config_dir: Optional[Union[str, Path]] = None
    options: SyncOptions = field(default_factory=SyncOptions)

    def process_single_config(self, config_name: str) -> dict[str, Any]:
        try:
            section(f"开始处理配置: {config_name}")

            final_cfg = normalize_config(load_config(config_name, self.config_dir))
            self._apply_runtime_overrides(final_cfg)
            papers = SearchService(create_arxiv_api(final_cfg)).fetch(final_cfg)

            if not papers:
                return self._result(
                    final_cfg,
                    config_name,
                    success=True,
                    total_papers=0,
                    ranked_papers=[],
                    dry_run=self.options.dry_run,
                )

            ranked_papers, sync_result, would_sync_count = self._rank_and_sync(papers, final_cfg)
            if ranked_papers is not None:
                sync_success = True if sync_result is None else sync_result.success
                sync_errors = [] if sync_result is None else sync_result.errors
                return self._result(
                    final_cfg,
                    config_name,
                    success=sync_success,
                    error="; ".join(sync_errors) if sync_errors and not sync_success else "",
                    sync_errors=sync_errors,
                    new_papers=0 if sync_result is None else max(sync_result.synced_count, 0),
                    would_sync=would_sync_count,
                    total_papers=len(ranked_papers),
                    ranked_papers=ranked_papers[:1],
                    dry_run=self.options.dry_run,
                    sync_result=sync_result,
                )

            return self._result(
                final_cfg,
                config_name,
                success=True,
                total_papers=len(papers),
                ranked_papers=[],
                dry_run=self.options.dry_run,
            )

        except Exception as exc:
            print(f"❌ 配置 {config_name} 处理失败: {exc}")
            if self.options.verbose:
                traceback.print_exc()
            return {
                "config_name": config_name,
                "success": False,
                "error": str(exc),
                "new_papers": 0,
                "would_sync": 0,
                "total_papers": 0,
                "research_area": config_name.replace("sync_", ""),
                "table_name": f'{config_name.replace("sync_", "")}论文表',
                "ranked_papers": [],
                "dry_run": self.options.dry_run,
            }

    def process_all_configs(self) -> bool:
        try:
            section("ArXiv 论文批量同步模式")

            sync_configs = find_sync_configs(self.config_dir, verbose=False)
            if not sync_configs:
                print("❌ 没有找到同步配置文件")
                return False

            print(f"\n🎯 处理 {len(sync_configs)} 个同步配置")

            all_results = []
            total_new_papers = 0
            total_would_sync = 0
            successful_configs = 0

            for config_name in sync_configs:
                result = self.process_single_config(config_name)
                all_results.append(result)

                if result["success"]:
                    successful_configs += 1
                    total_new_papers += result["new_papers"]
                    total_would_sync += result.get("would_sync", 0)
                    if self.options.dry_run:
                        print(f"✅ {config_name}: dry-run 预计可同步 {result.get('would_sync', 0)} 篇论文")
                    else:
                        print(f"✅ {config_name}: 新增 {result['new_papers']} 篇论文")
                else:
                    print(f"❌ {config_name}: 失败 - {result.get('error', '未知错误')}")

            print("\n📊 批量处理完成!")
            if self.options.dry_run:
                metric_name = "dry-run 预计可同步论文"
                metric_value = total_would_sync
            else:
                metric_name = "总新增论文"
                metric_value = total_new_papers
            table(
                "批量同步摘要",
                ["成功配置", "失败配置", metric_name],
                [(successful_configs, len(sync_configs) - successful_configs, f"{metric_value} 篇")],
            )

            if self.options.dry_run or self.options.no_feishu or self.options.no_notify:
                debug("\nℹ️ 已跳过批量汇总通知")
                return True
            if total_new_papers > 0:
                print("\n📢 发送汇总通知...")
                return send_batch_summary_notification(all_results, self.config_dir)

            debug("\nℹ️ 没有新论文，跳过通知发送")
            return True

        except Exception as exc:
            print(f"❌ 批量处理失败: {exc}")
            if self.options.verbose:
                traceback.print_exc()
            return False

    def _rank_and_sync(
        self, papers: list[dict[str, Any]], final_cfg: DictConfig
    ) -> tuple[Optional[list], Optional["FeishuSyncResult"], int]:
        interest_keywords, exclude_keywords, raw_interest_keywords, required_keywords_config = load_keywords_from_config(
            final_cfg
        )
        if not interest_keywords and not exclude_keywords:
            return None, None, 0

        search_cfg = final_cfg.get("search", {})
        intelligent_cfg = final_cfg.get("intelligent_matching", {})
        use_intelligent = intelligent_cfg.get("enabled", False)
        score_weights = dict(intelligent_cfg.get("score_weights", {})) if use_intelligent else None

        ranked_papers, _, _ = PaperRanker().filter_and_rank_papers(
            papers,
            interest_keywords,
            exclude_keywords,
            search_cfg.get("min_score", 0.1),
            use_advanced_scoring=use_intelligent,
            score_weights=score_weights,
            raw_interest_keywords=raw_interest_keywords,
            required_keywords_config=required_keywords_config,
        )
        if self.options.limit:
            ranked_papers = ranked_papers[: self.options.limit]

        would_sync_count = self._count_sync_candidates(ranked_papers, final_cfg)

        if not ranked_papers:
            return ranked_papers, None, would_sync_count

        if self.options.dry_run:
            print(f"🧪 dry-run: 已完成搜索和排序，预计 {would_sync_count} 篇论文满足飞书同步阈值，未写入飞书")
            self._print_preview(ranked_papers)
            return ranked_papers, None, would_sync_count

        if self.options.no_feishu:
            print("ℹ️ 已按 --no-feishu 跳过飞书写入")
            return ranked_papers, None, would_sync_count

        if not FEISHU_AVAILABLE:
            print("⚠️ 飞书模块不可用，跳过飞书写入")
            return ranked_papers, None, would_sync_count

        if not final_cfg.get("feishu", {}).get("enabled", False):
            print("ℹ️ 配置中 feishu.enabled=false，跳过飞书写入")
            return ranked_papers, None, would_sync_count

        os.environ["BATCH_MODE"] = "1"
        try:
            sync_result = sync_papers_to_feishu(ranked_papers, final_cfg)
        except Exception as sync_error:
            print(f"⚠️ 同步过程出错: {sync_error}")
            if self.options.verbose:
                traceback.print_exc()
            sync_result = FeishuSyncResult.failed(str(sync_error)) if FEISHU_AVAILABLE else None
        finally:
            os.environ.pop("BATCH_MODE", None)

        return ranked_papers, sync_result, would_sync_count

    def _apply_runtime_overrides(self, final_cfg: DictConfig) -> None:
        if self.options.limit is not None and self.options.limit <= 0:
            raise ValueError("--limit 必须大于 0")
        if self.options.since_days is not None and self.options.since_days <= 0:
            raise ValueError("--since-days 必须大于 0")

        if "search" not in final_cfg:
            final_cfg["search"] = {}

        if self.options.limit is not None:
            final_cfg.search.max_results = self.options.limit
            final_cfg.search.max_display = self.options.limit

        if self.options.since_days is not None:
            final_cfg.search.days = self.options.since_days
            final_cfg.search.date_range = {"enabled": False}

        if self.options.no_notify and "feishu" in final_cfg:
            if "chat_notification" not in final_cfg.feishu:
                final_cfg.feishu.chat_notification = {}
            final_cfg.feishu.chat_notification.enabled = False

    @staticmethod
    def _count_sync_candidates(ranked_papers: list[dict[str, Any]], final_cfg: DictConfig) -> int:
        feishu_cfg = final_cfg.get("feishu", {})
        threshold = feishu_cfg.get("sync_threshold", 0.0)
        count = 0
        for paper in ranked_papers:
            score = paper.get("final_score", paper.get("relevance_score", paper.get("score", 0)))
            if score >= threshold:
                count += 1
        return count

    @staticmethod
    def _print_preview(ranked_papers: list[dict[str, Any]], preview_count: int = 3) -> None:
        table(
            "论文预览",
            ["#", "评分", "ArXiv ID", "标题"],
            [
                (
                    index,
                    f"{paper.get('final_score', paper.get('relevance_score', paper.get('score', 0))):.2f}",
                    paper.get('arxiv_id', '-'),
                    paper.get('title', ''),
                )
                for index, paper in enumerate(ranked_papers[:preview_count], start=1)
            ],
            show_lines=True,
        )

    @staticmethod
    def _result(
        final_cfg: DictConfig,
        config_name: str,
        *,
        success: bool,
        new_papers: int = 0,
        would_sync: int = 0,
        total_papers: int = 0,
        ranked_papers: list | None = None,
        dry_run: bool = False,
        error: str = "",
        sync_errors: list[str] | None = None,
        sync_result: Any = None,
    ) -> dict[str, Any]:
        research_area = final_cfg.get("user_profile", {}).get("research_area", config_name.replace("sync_", ""))
        table_name = final_cfg.get("user_profile", {}).get("name", "").replace("研究员", "").strip() + "论文表"
        return {
            "config_name": config_name,
            "success": success,
            "new_papers": new_papers,
            "would_sync": would_sync,
            "total_papers": total_papers,
            "research_area": research_area,
            "table_name": table_name,
            "ranked_papers": ranked_papers or [],
            "dry_run": dry_run,
            "error": error,
            "sync_errors": sync_errors or [],
            "sync_result": sync_result,
            "database_total": _database_total_count(sync_result, fallback=0),
        }


def process_single_config(
    config_name: str,
    config_dir: Optional[Union[str, Path]] = None,
    *,
    dry_run: bool = False,
    no_feishu: bool = False,
    no_notify: bool = False,
    limit: Optional[int] = None,
    since_days: Optional[int] = None,
    verbose: bool = False,
) -> dict[str, Any]:
    options = SyncOptions(
        dry_run=dry_run,
        no_feishu=no_feishu,
        no_notify=no_notify,
        limit=limit,
        since_days=since_days,
        verbose=verbose,
    )
    return SyncRunner(config_dir=config_dir, options=options).process_single_config(config_name)


def process_all_configs(
    config_dir: Optional[Union[str, Path]] = None,
    *,
    dry_run: bool = False,
    no_feishu: bool = False,
    no_notify: bool = False,
    limit: Optional[int] = None,
    since_days: Optional[int] = None,
    verbose: bool = False,
) -> bool:
    options = SyncOptions(
        dry_run=dry_run,
        no_feishu=no_feishu,
        no_notify=no_notify,
        limit=limit,
        since_days=since_days,
        verbose=verbose,
    )
    return SyncRunner(config_dir=config_dir, options=options).process_all_configs()


def send_batch_summary_notification(
    results: list[dict[str, Any]], config_dir: Optional[Union[str, Path]] = None
) -> bool:
    try:
        if not FEISHU_AVAILABLE:
            print("⚠️ 飞书模块不可用，跳过通知")
            return False

        try:
            notification_cfg = normalize_config(load_config("all", config_dir))
        except FileNotFoundError:
            notification_cfg = normalize_config(load_config("default", config_dir))
        notifier = create_chat_notifier_from_config(notification_cfg)

        update_stats = {}
        papers_by_field = {}
        table_links = {}

        for result in results:
            if result["success"] and result["new_papers"] > 0:
                field_name = result["table_name"].replace("论文表", "").strip() or result["research_area"]
                database_total = _database_total_count(
                    result.get("sync_result"),
                    fallback=result.get("database_total", 0),
                )
                update_stats[field_name] = {
                    "new_count": result["new_papers"],
                    "total_count": database_total,
                    "table_name": result["table_name"],
                }

                papers_by_field[field_name] = result["ranked_papers"] or [
                    {
                        "title": f"{field_name}领域最新研究进展",
                        "authors_str": "批量同步发现",
                        "relevance_score": 0.95,
                        "arxiv_id": f'batch-{result["config_name"]}',
                        "paper_url": "https://arxiv.org/",
                        "summary": f'通过批量同步在{field_name}领域发现了{result["new_papers"]}篇新论文。',
                    }
                ]

                table_link = notifier.generate_table_link(table_name=result["table_name"])
                if table_link:
                    table_links[field_name] = table_link

        if not update_stats:
            print("ℹ️ 没有需要通知的更新")
            return True

        success = notifier.notify_paper_updates(
            update_stats=update_stats,
            papers_by_field=papers_by_field,
            table_links=table_links,
        )
        print("✅ 汇总通知发送成功" if success else "❌ 汇总通知发送失败")
        return success

    except Exception as exc:
        print(f"❌ 发送汇总通知失败: {exc}")
        traceback.print_exc()
        return False


def _database_total_count(sync_result: Any, *, fallback: int = 0) -> int:
    if sync_result is None:
        return fallback
    total_existing = int(getattr(sync_result, "total_existing", 0) or 0)
    synced_count = int(getattr(sync_result, "synced_count", 0) or 0)
    return total_existing + synced_count
