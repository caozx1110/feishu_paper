"""Actionable configuration validation for CLI and tests."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping

from omegaconf import DictConfig, OmegaConf

from ..terminal import print, success
from .runtime import FeishuEnvPolicy


@dataclass(frozen=True)
class ConfigIssue:
    """A user-facing config validation issue."""

    level: str
    path: str
    message: str
    hint: str = ""


def validate_config(cfg: Mapping[str, Any] | DictConfig) -> list[ConfigIssue]:
    """Validate the runtime config shape and common first-run mistakes."""
    data = _to_plain_mapping(cfg)
    issues: list[ConfigIssue] = []

    search_cfg = _mapping(data.get("search"))
    if not search_cfg:
        issues.append(ConfigIssue("error", "search", "缺少 search 配置段", "添加 search.field / days / max_results"))
    else:
        if not search_cfg.get("field"):
            issues.append(ConfigIssue("error", "search.field", "搜索领域为空", "设置为 robotics、ai、cv、nlp 或 arXiv 分类"))
        _check_positive_int(issues, search_cfg, "search.days", "days")
        _check_positive_int(issues, search_cfg, "search.max_results", "max_results")
        _check_score(issues, search_cfg, "search.min_score", "min_score")
        _check_date_range(issues, _mapping(search_cfg.get("date_range")))
        _check_batch_config(issues, _mapping(search_cfg.get("batch_processing")))

    interest_keywords = data.get("interest_keywords", [])
    if not isinstance(interest_keywords, list) or not interest_keywords:
        issues.append(ConfigIssue("warning", "interest_keywords", "兴趣关键词为空", "至少配置一个关键词，或显式使用 '*'"))
    elif "*" in interest_keywords:
        issues.append(ConfigIssue("warning", "interest_keywords", "当前会匹配所有论文", "生产同步前建议换成具体关键词"))

    required_cfg = _mapping(data.get("required_keywords"))
    if required_cfg.get("enabled", False):
        keywords = required_cfg.get("keywords", [])
        if not isinstance(keywords, list) or not keywords:
            issues.append(
                ConfigIssue(
                    "error",
                    "required_keywords.keywords",
                    "已启用必须关键词过滤，但关键词列表为空",
                    "添加关键词或关闭 required_keywords.enabled",
                )
            )
        _check_score(issues, required_cfg, "required_keywords.similarity_threshold", "similarity_threshold")

    feishu_cfg = _mapping(data.get("feishu"))
    chat_cfg = _mapping(feishu_cfg.get("chat_notification"))
    feishu_enabled = bool(feishu_cfg.get("enabled", False))
    chat_enabled = bool(chat_cfg.get("enabled", False))

    if feishu_enabled:
        _check_score(issues, feishu_cfg, "feishu.sync_threshold", "sync_threshold")
        _check_positive_int(issues, feishu_cfg, "feishu.batch_size", "batch_size")
        issues.extend(_validate_feishu_credentials(data))
    elif chat_enabled:
        issues.append(
            ConfigIssue(
                "warning",
                "feishu.chat_notification.enabled",
                "群通知已开启，但 feishu.enabled=false",
                "开启飞书同步或关闭群通知",
            )
        )
    if chat_enabled:
        target_chat_ids = chat_cfg.get("target_chat_ids", [])
        if target_chat_ids and not isinstance(target_chat_ids, list):
            issues.append(ConfigIssue("error", "feishu.chat_notification.target_chat_ids", "必须是群聊ID列表"))
        if not target_chat_ids and not chat_cfg.get("send_to_all_chats", False):
            issues.append(
                ConfigIssue(
                    "warning",
                    "feishu.chat_notification.target_chat_ids",
                    "未指定目标群聊，且 send_to_all_chats=false",
                    "填写目标 chat_id，或显式设置 send_to_all_chats=true",
                )
            )

    return issues


def has_errors(issues: list[ConfigIssue]) -> bool:
    return any(issue.level == "error" for issue in issues)


def print_validation_report(name: str, issues: list[ConfigIssue]) -> None:
    if not issues:
        success(f"{name}: 配置校验通过")
        return

    print(f"⚠️ {name}: 发现 {len(issues)} 个配置问题")
    for issue in issues:
        marker = "❌" if issue.level == "error" else "⚠️"
        detail = f"{marker} {issue.path}: {issue.message}"
        if issue.hint:
            detail += f"；建议：{issue.hint}"
        print(detail)


def _validate_feishu_credentials(data: Mapping[str, Any]) -> list[ConfigIssue]:
    issues: list[ConfigIssue] = []
    policy = FeishuEnvPolicy.from_config(data)
    feishu_cfg = _mapping(data.get("feishu"))
    api_cfg = _mapping(feishu_cfg.get("api"))
    bitable_cfg = _mapping(feishu_cfg.get("bitable"))

    configured_values = {
        "FEISHU_APP_ID": api_cfg.get("app_id", ""),
        "FEISHU_APP_SECRET": api_cfg.get("app_secret", ""),
        "FEISHU_BITABLE_APP_TOKEN": bitable_cfg.get("app_token", ""),
        "FEISHU_USER_ACCESS_TOKEN": api_cfg.get("user_access_token", ""),
        "FEISHU_TENANT_ACCESS_TOKEN": api_cfg.get("tenant_access_token", ""),
    }

    for name in policy.required:
        if not _has_real_value(name, policy, configured_values):
            issues.append(ConfigIssue("error", f"env.{name}", "飞书同步需要该环境变量", "写入 .env 后重新运行 health"))

    if not any(_has_real_value(name, policy, configured_values) for name in policy.token_any_of):
        issues.append(
            ConfigIssue(
                "error",
                "env.FEISHU_*_ACCESS_TOKEN",
                "飞书同步需要 user 或 tenant access token",
                "运行 autopaper get-token 或填写 FEISHU_USER_ACCESS_TOKEN",
            )
        )

    return issues


def _to_plain_mapping(cfg: Mapping[str, Any] | DictConfig) -> Mapping[str, Any]:
    if isinstance(cfg, DictConfig):
        return OmegaConf.to_container(cfg, resolve=True) or {}
    return cfg or {}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _check_positive_int(issues: list[ConfigIssue], section: Mapping[str, Any], path: str, key: str) -> None:
    value = section.get(key)
    if value is None:
        return
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        issues.append(ConfigIssue("error", path, "必须是正整数"))
        return
    if parsed <= 0:
        issues.append(ConfigIssue("error", path, "必须大于 0"))


def _check_score(issues: list[ConfigIssue], section: Mapping[str, Any], path: str, key: str) -> None:
    value = section.get(key)
    if value is None:
        return
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        issues.append(ConfigIssue("error", path, "必须是 0 到 1 之间的数字"))
        return
    if parsed < 0 or parsed > 1:
        issues.append(ConfigIssue("error", path, "必须在 0 到 1 之间"))


def _check_date_range(issues: list[ConfigIssue], date_range_cfg: Mapping[str, Any]) -> None:
    if not date_range_cfg.get("enabled", False):
        return

    start_date = str(date_range_cfg.get("start_date", "") or "")
    end_date = str(date_range_cfg.get("end_date", "") or "")
    start_dt = _parse_date(start_date)
    end_dt = _parse_date(end_date) if end_date else None

    if not start_dt:
        issues.append(ConfigIssue("error", "search.date_range.start_date", "启用日期范围时必须填写 YYYY-MM-DD"))
    if end_date and not end_dt:
        issues.append(ConfigIssue("error", "search.date_range.end_date", "日期格式必须是 YYYY-MM-DD"))
    if start_dt and end_dt and end_dt < start_dt:
        issues.append(ConfigIssue("error", "search.date_range", "end_date 不能早于 start_date"))


def _check_batch_config(issues: list[ConfigIssue], batch_cfg: Mapping[str, Any]) -> None:
    if not batch_cfg:
        return
    _check_positive_int(issues, batch_cfg, "search.batch_processing.max_days_per_batch", "max_days_per_batch")
    interval = batch_cfg.get("min_batch_interval")
    if interval is not None:
        try:
            parsed = float(interval)
        except (TypeError, ValueError):
            issues.append(ConfigIssue("error", "search.batch_processing.min_batch_interval", "必须是非负数字"))
            return
        if parsed < 0:
            issues.append(ConfigIssue("error", "search.batch_processing.min_batch_interval", "不能小于 0"))


def _parse_date(value: str) -> datetime | None:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        return None


def _has_real_value(name: str, policy: FeishuEnvPolicy, configured_values: Mapping[str, Any]) -> bool:
    value = str(os.getenv(name) or configured_values.get(name) or "")
    return bool(value) and not any(marker in value for marker in policy.placeholder_markers)
