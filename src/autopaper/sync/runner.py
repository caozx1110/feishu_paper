"""Batch sync orchestration for AutoPaper."""

from __future__ import annotations

import os
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional, Union

from omegaconf import DictConfig

from ..configuration.keywords import load_keywords_from_config
from ..configuration.loader import find_sync_configs, load_config, normalize_config
from ..core import PaperRanker, SearchService, create_arxiv_api

try:
    from ..feishu_chat_notification import create_chat_notifier_from_config
    from ..sync_to_feishu import sync_papers_to_feishu

    FEISHU_AVAILABLE = True
except ImportError:
    FEISHU_AVAILABLE = False


@dataclass
class SyncRunner:
    """Run one or many sync configs using the package service layer."""

    config_dir: Optional[Union[str, Path]] = None

    def process_single_config(self, config_name: str) -> dict[str, Any]:
        try:
            print(f"\n🚀 开始处理配置: {config_name}")
            print("=" * 60)

            final_cfg = normalize_config(load_config(config_name, self.config_dir))
            papers = SearchService(create_arxiv_api(final_cfg)).fetch(final_cfg)

            if not papers:
                return self._result(final_cfg, config_name, success=True, total_papers=0, ranked_papers=[])

            ranked_papers, synced_count = self._rank_and_sync(papers, final_cfg)
            if ranked_papers is not None:
                return self._result(
                    final_cfg,
                    config_name,
                    success=True,
                    new_papers=max(synced_count, 0),
                    total_papers=len(ranked_papers),
                    ranked_papers=ranked_papers[:1],
                )

            return self._result(final_cfg, config_name, success=True, total_papers=len(papers), ranked_papers=[])

        except Exception as exc:
            print(f"❌ 配置 {config_name} 处理失败: {exc}")
            traceback.print_exc()
            return {
                "config_name": config_name,
                "success": False,
                "error": str(exc),
                "new_papers": 0,
                "total_papers": 0,
                "research_area": config_name.replace("sync_", ""),
                "table_name": f'{config_name.replace("sync_", "")}论文表',
                "ranked_papers": [],
            }

    def process_all_configs(self) -> bool:
        try:
            print("🚀 ArXiv论文批量同步模式")
            print("=" * 70)

            sync_configs = find_sync_configs(self.config_dir)
            if not sync_configs:
                print("❌ 没有找到同步配置文件")
                return False

            print(f"\n🎯 开始处理 {len(sync_configs)} 个配置...")

            all_results = []
            total_new_papers = 0
            successful_configs = 0

            for config_name in sync_configs:
                result = self.process_single_config(config_name)
                all_results.append(result)

                if result["success"]:
                    successful_configs += 1
                    total_new_papers += result["new_papers"]
                    print(f"✅ {config_name}: 新增 {result['new_papers']} 篇论文")
                else:
                    print(f"❌ {config_name}: 失败 - {result.get('error', '未知错误')}")

            print(f"\n📊 批量处理完成!")
            print(f"✅ 成功: {successful_configs} 个")
            print(f"❌ 失败: {len(sync_configs) - successful_configs} 个")
            print(f"📚 总新增论文: {total_new_papers} 篇")

            if total_new_papers > 0:
                print("\n📢 发送汇总通知...")
                return send_batch_summary_notification(all_results, self.config_dir)

            print("\nℹ️ 没有新论文，跳过通知发送")
            return True

        except Exception as exc:
            print(f"❌ 批量处理失败: {exc}")
            traceback.print_exc()
            return False

    def _rank_and_sync(self, papers: list[dict[str, Any]], final_cfg: DictConfig) -> tuple[Optional[list], int]:
        interest_keywords, exclude_keywords, raw_interest_keywords, required_keywords_config = load_keywords_from_config(
            final_cfg
        )
        if not interest_keywords and not exclude_keywords:
            return None, 0

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

        synced_count = 0
        if ranked_papers and FEISHU_AVAILABLE and final_cfg.get("feishu", {}).get("enabled", True):
            os.environ["BATCH_MODE"] = "1"
            try:
                sync_result = sync_papers_to_feishu(ranked_papers, final_cfg)
                if isinstance(sync_result, int):
                    synced_count = sync_result
                elif sync_result is True:
                    synced_count = 0
            except Exception as sync_error:
                print(f"⚠️ 同步过程出错: {sync_error}")
                synced_count = 0
            finally:
                os.environ.pop("BATCH_MODE", None)

        return ranked_papers, synced_count

    @staticmethod
    def _result(
        final_cfg: DictConfig,
        config_name: str,
        *,
        success: bool,
        new_papers: int = 0,
        total_papers: int = 0,
        ranked_papers: list | None = None,
    ) -> dict[str, Any]:
        research_area = final_cfg.get("user_profile", {}).get("research_area", config_name.replace("sync_", ""))
        table_name = final_cfg.get("user_profile", {}).get("name", "").replace("研究员", "").strip() + "论文表"
        return {
            "config_name": config_name,
            "success": success,
            "new_papers": new_papers,
            "total_papers": total_papers,
            "research_area": research_area,
            "table_name": table_name,
            "ranked_papers": ranked_papers or [],
        }


def process_single_config(config_name: str, config_dir: Optional[Union[str, Path]] = None) -> dict[str, Any]:
    return SyncRunner(config_dir=config_dir).process_single_config(config_name)


def process_all_configs(config_dir: Optional[Union[str, Path]] = None) -> bool:
    return SyncRunner(config_dir=config_dir).process_all_configs()


def send_batch_summary_notification(
    results: list[dict[str, Any]], config_dir: Optional[Union[str, Path]] = None
) -> bool:
    try:
        if not FEISHU_AVAILABLE:
            print("⚠️ 飞书模块不可用，跳过通知")
            return False

        default_cfg = normalize_config(load_config("default", config_dir))
        notifier = create_chat_notifier_from_config(default_cfg)

        update_stats = {}
        papers_by_field = {}
        table_links = {}

        for result in results:
            if result["success"] and result["new_papers"] > 0:
                field_name = result["table_name"].replace("论文表", "").strip() or result["research_area"]
                update_stats[field_name] = {
                    "new_count": result["new_papers"],
                    "total_count": result["total_papers"],
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
