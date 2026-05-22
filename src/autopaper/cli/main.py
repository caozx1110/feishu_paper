"""Command line entry point for AutoPaper."""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import shutil
import sys
from importlib import resources
from pathlib import Path
from typing import Iterable, Optional

import requests
from dotenv import load_dotenv

from .. import __version__
from ..configuration import (
    DEFAULT_CONFIG_DIR,
    RuntimeSettings,
    configure_network,
    find_sync_configs,
    has_errors,
    healthcheck_url,
    load_config,
    load_default_config,
    normalize_config,
    print_validation_report,
    validate_config,
)
from ..configuration.loader import resolve_config_dir
from ..sync import process_all_configs, process_single_config
from ..terminal import bullet_list, debug, error, info, key_values, panel, print, set_output_mode, success, table


def build_parser() -> argparse.ArgumentParser:
    common_parent = argparse.ArgumentParser(add_help=False)
    common_parent.add_argument("--env-file", default=argparse.SUPPRESS, help="load environment variables from this file")
    common_parent.add_argument("--verbose", action="store_true", default=argparse.SUPPRESS, help="show diagnostic output")
    common_parent.add_argument("--quiet", action="store_true", default=argparse.SUPPRESS, help="print only essential output")

    parser = argparse.ArgumentParser(
        prog="autopaper",
        description="Collect, rank, and sync arXiv papers to Feishu Bitable.",
    )
    parser.add_argument("--version", action="version", version=f"autopaper {__version__}")
    parser.add_argument("--env-file", default=None, help="load environment variables from this file")
    parser.add_argument("--verbose", action="store_true", default=False, help="show diagnostic output")
    parser.add_argument("--quiet", action="store_true", default=False, help="print only essential output")

    subparsers = parser.add_subparsers(dest="command")

    sync_parser = subparsers.add_parser("sync", parents=[common_parent], help="run one config or all sync configs")
    sync_parser.add_argument("-c", "--config", default="all", help="config name or YAML path")
    sync_parser.add_argument("--config-dir", help="directory containing YAML configs")
    sync_parser.add_argument("--dry-run", action="store_true", help="search and rank without writing to Feishu")
    sync_parser.add_argument("--no-feishu", action="store_true", help="skip Feishu writes for this run")
    sync_parser.add_argument("--no-notify", action="store_true", help="skip Feishu chat notifications for this run")
    sync_parser.add_argument("--limit", type=int, help="limit fetched and ranked papers")
    sync_parser.add_argument("--since-days", type=int, help="override search.days and disable date_range")

    list_parser = subparsers.add_parser("list-configs", parents=[common_parent], help="list available sync configs")
    list_parser.add_argument("--config-dir", help="directory containing YAML configs")

    init_parser = subparsers.add_parser("init", parents=[common_parent], help="copy configs and scheduler scripts into a project")
    init_parser.add_argument("--target", default=".", help="target project directory")
    init_parser.add_argument("--force", action="store_true", help="overwrite generated files")
    init_parser.add_argument("--with-scripts", action="store_true", help="also copy cron helper scripts")

    health_parser = subparsers.add_parser("health", parents=[common_parent], help="check imports, config, Feishu env, and arXiv")
    health_parser.add_argument("-c", "--config", default="default", help="config name or YAML path")
    health_parser.add_argument("--config-dir", help="directory containing YAML configs")
    health_parser.add_argument("--skip-network", action="store_true", help="skip the arXiv network probe")
    health_parser.add_argument("--timeout", type=float, help="override healthcheck timeout in seconds")

    smoke_parser = subparsers.add_parser("smoke-search", parents=[common_parent], help="perform a small live arXiv search")
    smoke_parser.add_argument("--config-dir", help="directory containing YAML configs")
    smoke_parser.add_argument("--max-results", type=int, help="override smoke max_results")
    smoke_parser.add_argument("--mode", choices=["id", "query"], default="id", help="stable id lookup or query search")
    smoke_parser.add_argument("--paper-id", help="arXiv id used by stable id smoke mode")

    validate_parser = subparsers.add_parser(
        "validate-config", parents=[common_parent], help="validate one config or all sync configs"
    )
    validate_parser.add_argument("-c", "--config", default="default", help="config name, YAML path, or all")
    validate_parser.add_argument("--config-dir", help="directory containing YAML configs")

    feishu_parser = subparsers.add_parser("feishu", parents=[common_parent], help="diagnose Feishu setup")
    feishu_subparsers = feishu_parser.add_subparsers(dest="feishu_command")
    for name, help_text in [
        ("check", "validate Feishu env and list table count"),
        ("list-tables", "list Feishu Bitable tables"),
        ("test-notify", "check or send a Feishu chat test notification"),
    ]:
        subparser = feishu_subparsers.add_parser(name, parents=[common_parent], help=help_text)
        subparser.add_argument("-c", "--config", default="default", help="config name or YAML path")
        subparser.add_argument("--config-dir", help="directory containing YAML configs")
        if name == "test-notify":
            subparser.add_argument("--send", action="store_true", help="send a real test notification")
            subparser.add_argument("--all-chats", action="store_true", help="with --send, send to every bot chat")

    subparsers.add_parser("get-token", parents=[common_parent], help="fetch a Feishu tenant_access_token")
    return parser


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    config_count = _copy_tree(_package_path("config"), target / "conf", args.force)
    env_path = target / ".env.template"
    if args.force or not env_path.exists():
        shutil.copy2(_package_path("templates", "env.template"), env_path)
        env_status = "created"
    else:
        env_status = "exists"

    script_count = 0
    if args.with_scripts:
        script_count = _copy_tree(_package_path("scripts"), target / "scripts", args.force)
        for script in (target / "scripts").glob("*.sh"):
            script.chmod(script.stat().st_mode | 0o111)

    panel("Initialized AutoPaper Project", str(target), style="green")
    key_values(
        "Generated Files",
        {
            "configs": f"{config_count} files -> {target / 'conf'}",
            "env template": f"{env_status} -> {env_path}",
            "scripts": f"{script_count} files -> {target / 'scripts'}" if args.with_scripts else "not copied",
        },
    )
    bullet_list(
        "Next Steps",
        [
            "cp .env.template .env && edit .env",
            "autopaper health --config-dir ./conf --skip-network",
            "autopaper smoke-search --config-dir ./conf --max-results 1",
            "autopaper sync --config sync_7_vln --config-dir ./conf --dry-run --limit 2",
        ],
        style="green",
    )
    return 0


def cmd_list_configs(args: argparse.Namespace) -> int:
    configs = find_sync_configs(args.config_dir, verbose=False)
    bullet_list("Available Sync Configs", configs)
    return 0 if configs else 1


def cmd_sync(args: argparse.Namespace) -> int:
    try:
        cfg = _load_named_config(args.config, args.config_dir)
    except FileNotFoundError:
        cfg = _load_runtime_config(args.config_dir)
    configure_network(cfg)
    common_kwargs = {
        "dry_run": args.dry_run,
        "no_feishu": args.no_feishu,
        "no_notify": args.no_notify,
        "limit": args.limit,
        "since_days": args.since_days,
        "verbose": args.verbose,
    }

    if args.config == "all":
        if args.quiet:
            with contextlib.redirect_stdout(io.StringIO()):
                ok = process_all_configs(args.config_dir, **common_kwargs)
            print("✅ sync all completed" if ok else "❌ sync all failed")
            return 0 if ok else 1
        return 0 if process_all_configs(args.config_dir, **common_kwargs) else 1

    if args.quiet:
        with contextlib.redirect_stdout(io.StringIO()):
            result = process_single_config(args.config, args.config_dir, **common_kwargs)
    else:
        result = process_single_config(args.config, args.config_dir, **common_kwargs)
    if result.get("success"):
        if result.get("dry_run"):
            success(f"{args.config} dry-run 完成，预计可同步 {result.get('would_sync', 0)} 篇论文")
            return 0
        success(f"{args.config} 同步完成，新增 {result.get('new_papers', 0)} 篇论文")
        return 0

    error(f"{args.config} 同步失败: {result.get('error', '未知错误')}")
    return 1


def cmd_health(args: argparse.Namespace) -> int:
    cfg = _load_named_config(args.config, args.config_dir)
    configure_network(cfg)
    settings = RuntimeSettings.from_config(cfg)

    passed = 0
    total = 0

    import_passed, import_total = _check_imports(["arxiv", "hydra", "omegaconf", "yaml", "requests"])
    passed += import_passed
    total += import_total

    total += 1
    config_dir = resolve_config_dir(args.config_dir) if args.config_dir else DEFAULT_CONFIG_DIR
    configs = find_sync_configs(config_dir, verbose=False)
    if configs:
        success(f"configs: found {len(configs)} sync configs in {config_dir}")
        passed += 1
    else:
        error(f"configs: no sync configs found in {config_dir}")

    if not _feishu_enabled(cfg):
        info("Feishu sync disabled by config; skipping Feishu env check")
    else:
        total += 1
        missing = [name for name in settings.feishu_env.required if not _has_real_value(name, settings)]
        has_token = any(_has_real_value(name, settings) for name in settings.feishu_env.token_any_of)
        if not missing and has_token:
            success("Feishu environment variables look complete")
            passed += 1
        else:
            details = missing[:]
            if not has_token:
                details.append(" or ".join(settings.feishu_env.token_any_of))
            print(f"⚠️ Feishu environment variables incomplete: {', '.join(details)}")

    if not args.skip_network:
        total += 1
        timeout = args.timeout if args.timeout is not None else settings.healthcheck.timeout_seconds
        try:
            response = requests.get(healthcheck_url(cfg), timeout=timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            error(f"arXiv connectivity: {exc}")
        else:
            success(f"arXiv connectivity: HTTP {response.status_code}")
            passed += 1

    key_values("Health Check", {"passed": passed, "total": total, "status": "ok" if passed == total else "failed"})
    return 0 if passed == total else 1


def cmd_smoke_search(args: argparse.Namespace) -> int:
    from ..core import SearchService, create_arxiv_api

    cfg = _load_runtime_config(args.config_dir)
    configure_network(cfg)
    smoke_cfg = cfg.get("arxiv", {}).get("smoke_test", {})
    max_results = args.max_results or smoke_cfg.get("max_results", 2)

    if args.mode == "id":
        import arxiv

        paper_id = args.paper_id or smoke_cfg.get("paper_id", "1706.03762")
        api = create_arxiv_api(cfg)
        api.client = api._create_client(page_size=1, delay_seconds=0)
        result = next(api.client.results(arxiv.Search(id_list=[paper_id], max_results=1)), None)
        if result is None:
            error(f"smoke search returned no paper for id {paper_id}")
            return 1
        paper = api._parse_arxiv_result(result)
        table("arXiv Smoke Result", ["ArXiv ID", "Title"], [(paper.get('arxiv_id'), paper.get('title'))])
        return 0

    search_cfg = cfg.get("search", {})
    search_cfg["field"] = smoke_cfg.get("field", search_cfg.get("field", "robotics"))
    search_cfg["days"] = smoke_cfg.get("days", 7)
    search_cfg["max_results"] = max_results
    search_cfg["date_range"] = {"enabled": False}
    search_cfg["batch_processing"] = {"enabled": False}
    cfg["search"] = search_cfg

    papers = SearchService(create_arxiv_api(cfg)).fetch(cfg)
    if not papers:
        error("smoke search returned no papers")
        return 1

    table(
        "arXiv Smoke Results",
        ["ArXiv ID", "Title"],
        [(paper.get('arxiv_id'), paper.get('title')) for paper in papers[:max_results]],
        show_lines=True,
    )
    return 0


def cmd_validate_config(args: argparse.Namespace) -> int:
    results = _validate_named_configs(args.config, args.config_dir)
    return 1 if any(has_errors(issues) for _, issues in results) else 0


def cmd_feishu(args: argparse.Namespace) -> int:
    if args.feishu_command is None:
        info("Use one of: check, list-tables, test-notify")
        return 1

    cfg = _load_named_config(args.config, args.config_dir)
    configure_network(cfg)
    if "feishu" not in cfg:
        cfg["feishu"] = {}
    cfg.feishu.enabled = True
    feishu_issues = [issue for issue in validate_config(cfg) if issue.path.startswith("env.")]
    if feishu_issues:
        print_validation_report(args.config, feishu_issues)
        return 1

    from ..feishu import FeishuBitableConfig, FeishuBitableConnector, create_chat_notifier_from_config

    if args.feishu_command == "check":
        connector = FeishuBitableConnector(FeishuBitableConfig.from_hydra_config(cfg))
        tables = connector.list_tables()
        key_values("Feishu Bitable", {"connection": "ok", "tables": len(tables)}, style="green")
        return 0

    if args.feishu_command == "list-tables":
        connector = FeishuBitableConnector(FeishuBitableConfig.from_hydra_config(cfg))
        table(
            "Feishu Tables",
            ["Table ID", "Name"],
            [(item.get('table_id', '-'), item.get('name', '-')) for item in connector.list_tables()],
        )
        return 0

    if args.feishu_command == "test-notify":
        if args.send:
            if "feishu" not in cfg:
                cfg["feishu"] = {}
            if "chat_notification" not in cfg.feishu:
                cfg.feishu.chat_notification = {}
            cfg.feishu.chat_notification.enabled = True
            if args.all_chats:
                cfg.feishu.chat_notification.send_to_all_chats = True
        notifier = create_chat_notifier_from_config(cfg)
        if not args.send:
            chats = notifier.get_bot_chats()
            message_content = notifier.create_paper_update_message(
                {"通知自检": {"new_count": 1, "total_count": 1, "table_name": "AutoPaper"}},
                {
                    "通知自检": [
                        {
                            "title": "AutoPaper Feishu notification payload check",
                            "authors_str": "AutoPaper",
                            "relevance_score": 1.0,
                            "arxiv_id": "test",
                            "paper_url": "https://arxiv.org/",
                        }
                    ]
                },
                {},
            )
            payload = notifier.build_message_payload("chat_id_for_preview", message_content)
            key_values(
                "Feishu Notify Check",
                {"chats": len(chats), "msg_type": payload["msg_type"], "payload": "valid"},
                style="green" if chats else "yellow",
            )
            success("notification check completed; add --send to send a real test message")
            return 0 if chats else 1
        return 0 if notifier.test_notification() else 1

    return 1


def cmd_get_token(_: argparse.Namespace) -> int:
    from ..feishu.tokens import main as get_token_main

    get_token_main()
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    set_output_mode(verbose=getattr(args, "verbose", False), quiet=getattr(args, "quiet", False))
    env_status = _load_env(args.env_file)
    if env_status is False:
        return 1
    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "sync": cmd_sync,
        "list-configs": cmd_list_configs,
        "init": cmd_init,
        "health": cmd_health,
        "smoke-search": cmd_smoke_search,
        "validate-config": cmd_validate_config,
        "feishu": cmd_feishu,
        "get-token": cmd_get_token,
    }
    return commands[args.command](args)


def _load_runtime_config(config_dir: Optional[str]):
    return load_default_config(config_dir)


def _load_named_config(config_name: str, config_dir: Optional[str]):
    if config_name == "default":
        return load_default_config(config_dir)
    return normalize_config(load_config(config_name, config_dir))


def _validate_named_configs(config_name: str, config_dir: Optional[str]) -> list[tuple[str, list]]:
    if config_name == "all":
        names = find_sync_configs(config_dir, verbose=False)
    else:
        names = [config_name]

    results = []
    for name in names:
        cfg = _load_named_config(name, config_dir)
        issues = validate_config(cfg)
        print_validation_report(name, issues)
        results.append((name, issues))
    return results


def _load_env(env_file: Optional[str]) -> bool:
    requested_env_file = env_file or os.getenv("AUTOPAPER_ENV_FILE")
    if requested_env_file:
        path = Path(requested_env_file).expanduser()
        if not path.exists():
            error(f"env file not found: {path}")
            return False
        load_dotenv(path, override=True)
        return True
    load_dotenv()
    return True


def _feishu_enabled(cfg) -> bool:
    return bool(cfg.get("feishu", {}).get("enabled", False))


def _copy_tree(src: Path, dst: Path, force: bool) -> int:
    copied = 0
    dst.mkdir(parents=True, exist_ok=True)
    for source_path in sorted(src.iterdir()):
        if not source_path.is_file():
            continue
        target_path = dst / source_path.name
        if target_path.exists() and not force:
            continue
        shutil.copy2(source_path, target_path)
        copied += 1
    return copied


def _package_path(*parts: str) -> Path:
    return Path(str(resources.files("autopaper").joinpath(*parts)))


def _check_imports(modules: Iterable[str]) -> tuple[int, int]:
    passed = 0
    total = 0
    failed = []
    for module in modules:
        total += 1
        try:
            __import__(module)
        except ImportError as exc:
            failed.append((module, exc))
            print(f"❌ import {module}: {exc}")
        else:
            debug(f"✅ import {module}")
            passed += 1
    if not failed:
        success(f"imports: {passed}/{total} modules available")
    return passed, total


def _has_real_value(name: str, settings: RuntimeSettings) -> bool:
    value = requests.utils.unquote(str(os.getenv(name, "")))
    return bool(value) and not any(marker in value for marker in settings.feishu_env.placeholder_markers)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
