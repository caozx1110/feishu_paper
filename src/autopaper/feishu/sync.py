"""Feishu Bitable paper sync service."""

from __future__ import annotations

import os
from typing import Any

from dotenv import load_dotenv

from ..terminal import debug, error, info, key_values, print, success, table, warning
from .bitable import FeishuBitableConnector
from .config import FeishuBitableConfig
from .dates import to_feishu_timestamp_millis
from .sync_result import FeishuSyncResult


def sync_papers_to_feishu(papers, cfg, matched_keywords_map=None, score_map=None) -> FeishuSyncResult:
    """Sync ranked papers to a Feishu Bitable table.

    Returns a structured result so callers can distinguish a clean no-op from
    partial write failures.
    """
    load_dotenv()

    feishu_cfg = cfg.get("feishu", {})
    if not feishu_cfg.get("enabled", False):
        info("飞书同步已禁用")
        return FeishuSyncResult.skipped("feishu.disabled", disabled=True)

    try:
        connector_config = FeishuBitableConfig.from_hydra_config(cfg)
        if not connector_config.app_token:
            return FeishuSyncResult.failed("缺少 feishu.bitable.app_token / FEISHU_BITABLE_APP_TOKEN")
    except Exception as exc:
        error(f"飞书配置不完整: {exc}")
        return FeishuSyncResult.failed(str(exc))

    table_display_name, research_area, field_name = _resolve_table_context(cfg)
    result = FeishuSyncResult(
        success=False,
        table_name=table_display_name,
        research_area=research_area,
    )

    try:
        print("\n🔗 开始飞书同步...")
        connector = FeishuBitableConnector(connector_config)

        debug(f"📊 为研究领域 '{research_area}' 处理专用数据表...")
        target_table_id = connector.find_table_by_name(table_display_name)

        if not target_table_id:
            print(f"🆕 创建新数据表: {table_display_name}")
            table_result = connector.create_domain_papers_table(table_display_name, research_area)
            target_table_id = table_result.get("table_id") if table_result else ""
            if not target_table_id:
                return FeishuSyncResult.failed(
                    "数据表创建失败",
                    table_name=table_display_name,
                    research_area=research_area,
                )
            debug(f"✅ 数据表创建成功，ID: {target_table_id}")
        else:
            debug(f"✅ 找到现有数据表: {table_display_name} (ID: {target_table_id})")

        result.table_id = target_table_id

        debug("🔍 检查现有记录，避免重复...")
        existing_records = connector.get_all_records(target_table_id)
        existing_arxiv_ids = _extract_existing_arxiv_ids(existing_records)
        result.total_existing = len(existing_arxiv_ids)
        debug(f"📋 发现 {len(existing_arxiv_ids)} 条现有记录")

        sync_threshold = float(feishu_cfg.get("sync_threshold", 0.0))
        new_papers_data, skipped_existing, skipped_threshold = _prepare_papers_for_sync(
            papers,
            research_area=research_area,
            existing_arxiv_ids=existing_arxiv_ids,
            sync_threshold=sync_threshold,
            matched_keywords_map=matched_keywords_map,
            score_map=score_map,
        )
        result.skipped_existing = skipped_existing
        result.skipped_threshold = skipped_threshold
        result.would_sync_count = len(new_papers_data)

        if skipped_existing:
            debug(f"📋 跳过已存在论文: {skipped_existing} 篇")
        if not new_papers_data:
            if skipped_threshold:
                info(f"没有符合同步条件的论文（阈值: {sync_threshold}）")
                result.reason = "below_threshold"
            else:
                info("没有新的论文需要同步")
                result.reason = "no_new_papers"
            result.success = True
            return result

        batch_size = max(1, int(feishu_cfg.get("batch_size", 20)))
        print(f"📊 准备同步 {len(new_papers_data)} 篇新论文到 '{table_display_name}'...")
        _write_batches(connector, target_table_id, new_papers_data, batch_size, result)

        _manage_views_if_enabled(connector, target_table_id, feishu_cfg, result)

        if result.failed_count:
            warning(f"飞书同步部分完成，失败 {result.failed_count} 篇")
        else:
            success("飞书同步完成")
        table(
            "飞书同步摘要",
            ["表格名称", "研究领域", "新增论文", "失败论文", "总记录数"],
            [
                (
                    table_display_name,
                    research_area,
                    result.synced_count,
                    result.failed_count,
                    len(existing_arxiv_ids) + result.synced_count,
                )
            ],
        )

        if result.synced_count > 0:
            _notify_if_enabled(
                papers,
                cfg,
                feishu_cfg,
                field_name,
                table_display_name,
                target_table_id,
                existing_arxiv_ids,
                sync_threshold,
                result,
            )

        result.success = result.failed_count == 0
        if result.failed_count:
            result.reason = "partial_write_failure"
        return result

    except Exception as exc:
        error(f"飞书同步失败: {exc}")
        return FeishuSyncResult.failed(
            str(exc),
            table_id=result.table_id,
            table_name=table_display_name,
            research_area=research_area,
            synced_count=result.synced_count,
            failed_count=result.failed_count,
            would_sync_count=result.would_sync_count,
            skipped_existing=result.skipped_existing,
            skipped_threshold=result.skipped_threshold,
            total_existing=result.total_existing,
        )


def _resolve_table_context(cfg) -> tuple[str, str, str]:
    feishu_cfg = cfg.get("feishu", {})
    user_profile = cfg.get("user_profile", {})
    research_area = feishu_cfg.get("field_id") or user_profile.get("research_area", "general")
    default_field_name = str(user_profile.get("name", "研究员")).replace("研究员", "").strip()
    field_name = feishu_cfg.get("field_name") or default_field_name or str(research_area)
    table_display_name = field_name if str(field_name).endswith("论文表") else f"{field_name}论文表"
    return table_display_name, str(research_area), str(field_name)


def _extract_existing_arxiv_ids(records: list[dict[str, Any]]) -> set[str]:
    existing_arxiv_ids = set()
    for record in records:
        fields = record.get("fields", {})
        arxiv_id_field = fields.get("ArXiv ID", "")
        if isinstance(arxiv_id_field, dict):
            arxiv_id = arxiv_id_field.get("text", "")
        else:
            arxiv_id = str(arxiv_id_field) if arxiv_id_field else ""
        if arxiv_id:
            existing_arxiv_ids.add(arxiv_id)
    return existing_arxiv_ids


def _prepare_papers_for_sync(
    papers,
    *,
    research_area: str,
    existing_arxiv_ids: set[str],
    sync_threshold: float,
    matched_keywords_map=None,
    score_map=None,
) -> tuple[list[dict[str, Any]], int, int]:
    papers_to_sync: list[dict[str, Any]] = []
    skipped_existing = 0
    skipped_threshold = 0

    for paper in papers:
        arxiv_id = _paper_value(paper, "arxiv_id", _paper_value(paper, "id", ""))
        if arxiv_id in existing_arxiv_ids:
            skipped_existing += 1
            continue

        relevance_score = _paper_score(paper)
        if score_map and arxiv_id in score_map:
            relevance_score = score_map[arxiv_id]

        if relevance_score < sync_threshold:
            skipped_threshold += 1
            continue

        papers_to_sync.append(
            _build_record_fields(
                paper,
                arxiv_id=arxiv_id,
                research_area=research_area,
                relevance_score=relevance_score,
                matched_keywords=_matched_keywords(paper, arxiv_id, matched_keywords_map),
            )
        )

    return papers_to_sync, skipped_existing, skipped_threshold


def _build_record_fields(
    paper,
    *,
    arxiv_id: str,
    research_area: str,
    relevance_score: float,
    matched_keywords: list[str],
) -> dict[str, Any]:
    title = _paper_value(paper, "title", "")
    summary = _paper_value(paper, "summary", "")
    paper_url = _paper_value(paper, "paper_url", _paper_value(paper, "entry_id", ""))
    pdf_url = _paper_value(paper, "pdf_url", "")
    published_date = _paper_value(paper, "published_date", None)
    updated_date = _paper_value(paper, "updated_date", None)

    return {
        "ArXiv ID": {"text": arxiv_id, "link": paper_url} if paper_url else arxiv_id,
        "标题": title,
        "作者": _string_list(_paper_value(paper, "authors", []), limit=10),
        "摘要": summary[:1000] if summary else "",
        "分类": _string_list(_paper_value(paper, "categories", []), limit=5),
        "匹配关键词": _string_list(matched_keywords, limit=10),
        "相关性评分": round(float(relevance_score), 2),
        "研究领域": _string_list(research_area, limit=3),
        "PDF链接": {"text": "PDF", "link": pdf_url} if pdf_url else None,
        "必须关键词匹配": _string_list(_paper_value(paper, "required_keyword_matches", []), limit=5),
        "发布日期": _timestamp_millis(published_date),
        "更新日期": _timestamp_millis(updated_date),
    }


def _write_batches(
    connector: FeishuBitableConnector,
    table_id: str,
    papers_to_sync: list[dict[str, Any]],
    batch_size: int,
    result: FeishuSyncResult,
) -> None:
    for start in range(0, len(papers_to_sync), batch_size):
        batch = papers_to_sync[start : start + batch_size]
        batch_number = start // batch_size + 1
        try:
            response = connector.batch_insert_records(table_id, batch)
        except Exception as exc:
            message = f"第 {batch_number} 批同步失败: {exc}"
            error(message)
            result.errors.append(message)
            result.failed_count += len(batch)
            continue

        records = response.get("records", []) if response else []
        inserted = len(records)
        result.synced_count += inserted
        if inserted != len(batch):
            failed = len(batch) - inserted
            message = f"第 {batch_number} 批部分成功: {inserted}/{len(batch)}"
            warning(message)
            result.errors.append(message)
            result.failed_count += failed
        else:
            debug(f"✅ 第 {batch_number} 批同步成功: {inserted} 篇")


def _manage_views_if_enabled(
    connector: FeishuBitableConnector,
    table_id: str,
    feishu_cfg,
    result: FeishuSyncResult,
) -> None:
    view_config = feishu_cfg.get("views", {})
    if not view_config.get("enabled", False):
        return

    debug("🎯 管理表格视图...")
    view_configs = view_config.get("create_views", [])
    if not view_configs:
        return

    try:
        view_result = connector.manage_table_views(table_id, view_configs, view_config.get("auto_cleanup", True))
    except Exception as exc:
        message = f"视图管理失败: {exc}"
        warning(message)
        result.errors.append(message)
        return

    key_values(
        "视图管理结果",
        {
            "创建": f"{view_result['created']} 个",
            "已存在": f"{view_result['existing']} 个",
            "删除": f"{view_result['deleted']} 个",
        },
    )
    for view_error in view_result.get("errors", []):
        result.errors.append(str(view_error))
        warning(str(view_error))


def _notify_if_enabled(
    papers,
    cfg,
    feishu_cfg,
    field_name: str,
    table_display_name: str,
    table_id: str,
    existing_arxiv_ids: set[str],
    sync_threshold: float,
    result: FeishuSyncResult,
) -> None:
    batch_mode = os.getenv("BATCH_MODE", "0") == "1"
    if batch_mode:
        debug("ℹ️ 批量模式运行，跳过个别群聊通知")
        return

    chat_config = feishu_cfg.get("chat_notification", {})
    if not chat_config.get("enabled", False):
        return

    print("📢 准备发送群聊通知...")
    try:
        from .notifications import create_chat_notifier_from_config

        notifier = create_chat_notifier_from_config(cfg)
        update_stats = {
            field_name: {
                "new_count": result.synced_count,
                "total_count": result.total_existing + result.synced_count,
                "table_name": table_display_name,
            }
        }
        papers_for_notification = _notification_papers(
            papers,
            existing_arxiv_ids,
            sync_threshold,
            limit=result.synced_count,
        )
        table_links = {}
        table_link = notifier.generate_table_link(table_name=table_display_name, table_id=table_id)
        if table_link:
            table_links[field_name] = table_link
            debug(f"📊 生成表格链接: {table_link}")
        else:
            warning("无法生成表格链接")

        result.notification_sent = notifier.notify_paper_updates(
            update_stats,
            {field_name: papers_for_notification},
            table_links,
        )
        if result.notification_sent:
            success("群聊通知发送成功")
        else:
            warning("群聊通知发送失败或跳过")
    except Exception as exc:
        message = f"群聊通知功能异常: {exc}"
        warning(message)
        result.notification_sent = False
        result.errors.append(message)


def _notification_papers(
    papers,
    existing_arxiv_ids: set[str],
    sync_threshold: float,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    notification_papers = []
    for paper in papers:
        arxiv_id = _paper_value(paper, "arxiv_id", _paper_value(paper, "id", ""))
        if arxiv_id in existing_arxiv_ids or _paper_score(paper) < sync_threshold:
            continue
        if isinstance(paper, dict):
            payload = paper.copy()
            summary = payload.get("summary", "")
            if summary:
                payload["summary"] = summary[:200] + "..." if len(summary) > 200 else summary
        else:
            summary = _paper_value(paper, "summary", "")
            payload = {
                "title": _paper_value(paper, "title", ""),
                "arxiv_id": arxiv_id,
                "authors_str": ", ".join(_string_list(_paper_value(paper, "authors", []))),
                "paper_url": _paper_value(paper, "paper_url", _paper_value(paper, "entry_id", "")),
                "relevance_score": _paper_score(paper),
                "summary": summary[:200] + "..." if summary else "",
            }
        notification_papers.append(payload)
        if len(notification_papers) >= limit:
            break
    return notification_papers


def _matched_keywords(paper, arxiv_id: str, matched_keywords_map=None) -> list[str]:
    matched_keywords = _paper_value(
        paper,
        "matched_interests",
        _paper_value(paper, "matched_keywords", []),
    )
    if matched_keywords_map and arxiv_id in matched_keywords_map:
        matched_keywords = matched_keywords_map[arxiv_id]
    return _string_list(matched_keywords)


def _paper_score(paper) -> float:
    return float(
        _paper_value(
            paper,
            "final_score",
            _paper_value(
                paper,
                "relevance_score",
                _paper_value(paper, "score", 0),
            ),
        )
        or 0
    )


def _paper_value(paper, name: str, default=None):
    if isinstance(paper, dict):
        return paper.get(name, default)
    return getattr(paper, name, default)


def _string_list(value, *, limit: int | None = None) -> list[str]:
    if value is None:
        values: list[Any] = []
    elif isinstance(value, list | tuple | set):
        values = list(value)
    else:
        values = str(value).split(",")
    cleaned = [str(item).strip() for item in values if item is not None and str(item).strip()]
    return cleaned[:limit] if limit else cleaned


def _timestamp_millis(value) -> int | None:
    return to_feishu_timestamp_millis(value)
