"""Command line entry point for AutoPaper."""

from __future__ import annotations

import argparse
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
    healthcheck_url,
    load_default_config,
)
from ..configuration.loader import resolve_config_dir
from ..sync import process_all_configs, process_single_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autopaper",
        description="Collect, rank, and sync arXiv papers to Feishu Bitable.",
    )
    parser.add_argument("--version", action="version", version=f"autopaper {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    sync_parser = subparsers.add_parser("sync", help="run one config or all sync configs")
    sync_parser.add_argument("-c", "--config", default="all", help="config name or YAML path")
    sync_parser.add_argument("--config-dir", help="directory containing YAML configs")

    list_parser = subparsers.add_parser("list-configs", help="list available sync configs")
    list_parser.add_argument("--config-dir", help="directory containing YAML configs")

    init_parser = subparsers.add_parser("init", help="copy configs and scheduler scripts into a project")
    init_parser.add_argument("--target", default=".", help="target project directory")
    init_parser.add_argument("--force", action="store_true", help="overwrite generated files")
    init_parser.add_argument("--with-scripts", action="store_true", help="also copy cron helper scripts")

    health_parser = subparsers.add_parser("health", help="check imports, config, Feishu env, and arXiv")
    health_parser.add_argument("--config-dir", help="directory containing YAML configs")
    health_parser.add_argument("--skip-network", action="store_true", help="skip the arXiv network probe")
    health_parser.add_argument("--timeout", type=float, help="override healthcheck timeout in seconds")

    smoke_parser = subparsers.add_parser("smoke-search", help="perform a small live arXiv search")
    smoke_parser.add_argument("--config-dir", help="directory containing YAML configs")
    smoke_parser.add_argument("--max-results", type=int, help="override smoke max_results")

    subparsers.add_parser("get-token", help="fetch a Feishu tenant_access_token")
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

    print(f"Initialized AutoPaper project at {target}")
    print(f"- configs: {config_count} files copied to {target / 'conf'}")
    print(f"- env template: {env_status} at {env_path}")
    if args.with_scripts:
        print(f"- scripts: {script_count} files copied to {target / 'scripts'}")
    return 0


def cmd_list_configs(args: argparse.Namespace) -> int:
    configs = find_sync_configs(args.config_dir)
    for config in configs:
        print(config)
    return 0 if configs else 1


def cmd_sync(args: argparse.Namespace) -> int:
    cfg = _load_runtime_config(args.config_dir)
    configure_network(cfg)

    if args.config == "all":
        return 0 if process_all_configs(args.config_dir) else 1

    result = process_single_config(args.config, args.config_dir)
    if result.get("success"):
        print(f"\n✅ {args.config} 同步完成，新增 {result.get('new_papers', 0)} 篇论文")
        return 0

    print(f"\n❌ {args.config} 同步失败: {result.get('error', '未知错误')}")
    return 1


def cmd_health(args: argparse.Namespace) -> int:
    cfg = _load_runtime_config(args.config_dir)
    configure_network(cfg)
    settings = RuntimeSettings.from_config(cfg)

    passed = 0
    total = 0

    import_passed, import_total = _check_imports(["arxiv", "hydra", "omegaconf", "yaml", "requests"])
    passed += import_passed
    total += import_total

    total += 1
    config_dir = resolve_config_dir(args.config_dir) if args.config_dir else DEFAULT_CONFIG_DIR
    configs = find_sync_configs(config_dir)
    if configs:
        print(f"✅ configs: found {len(configs)} sync configs in {config_dir}")
        passed += 1
    else:
        print(f"❌ configs: no sync configs found in {config_dir}")

    total += 1
    missing = [name for name in settings.feishu_env.required if not _has_real_value(name, settings)]
    has_token = any(_has_real_value(name, settings) for name in settings.feishu_env.token_any_of)
    if not missing and has_token:
        print("✅ Feishu environment variables look complete")
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
            print(f"❌ arXiv connectivity: {exc}")
        else:
            print(f"✅ arXiv connectivity: HTTP {response.status_code}")
            passed += 1

    print(f"\nHealth check: {passed}/{total} checks passed")
    return 0 if passed == total else 1


def cmd_smoke_search(args: argparse.Namespace) -> int:
    from ..core import SearchService, create_arxiv_api

    cfg = _load_runtime_config(args.config_dir)
    configure_network(cfg)
    smoke_cfg = cfg.get("arxiv", {}).get("smoke_test", {})

    search_cfg = cfg.get("search", {})
    search_cfg["field"] = smoke_cfg.get("field", search_cfg.get("field", "robotics"))
    search_cfg["days"] = smoke_cfg.get("days", 7)
    search_cfg["max_results"] = args.max_results or smoke_cfg.get("max_results", 2)
    search_cfg["date_range"] = {"enabled": False}
    search_cfg["batch_processing"] = {"enabled": False}
    cfg["search"] = search_cfg

    papers = SearchService(create_arxiv_api(cfg)).fetch(cfg)
    if not papers:
        print("❌ smoke search returned no papers")
        return 1

    for paper in papers[: search_cfg["max_results"]]:
        print(f"{paper.get('arxiv_id')}\t{paper.get('title')}")
    return 0


def cmd_get_token(_: argparse.Namespace) -> int:
    from ..get_token import main as get_token_main

    get_token_main()
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0

    commands = {
        "sync": cmd_sync,
        "list-configs": cmd_list_configs,
        "init": cmd_init,
        "health": cmd_health,
        "smoke-search": cmd_smoke_search,
        "get-token": cmd_get_token,
    }
    return commands[args.command](args)


def _load_runtime_config(config_dir: Optional[str]):
    return load_default_config(config_dir)


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
    for module in modules:
        total += 1
        try:
            __import__(module)
        except ImportError as exc:
            print(f"❌ import {module}: {exc}")
        else:
            print(f"✅ import {module}")
            passed += 1
    return passed, total


def _has_real_value(name: str, settings: RuntimeSettings) -> bool:
    value = requests.utils.unquote(str(os.getenv(name, "")))
    return bool(value) and not any(marker in value for marker in settings.feishu_env.placeholder_markers)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
