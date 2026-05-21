"""Command line interface for AutoPaper."""

from __future__ import annotations

import argparse
import os
import shutil
import socket
import sys
from importlib import resources
from pathlib import Path
from typing import Iterable, Optional

import requests
from dotenv import load_dotenv

from . import __version__
from .arxiv_hydra import DEFAULT_CONFIG_DIR, find_sync_configs, process_all_configs, process_single_config


ENV_TEMPLATE = """# AutoPaper environment template
# Copy this file to .env and fill in values from the Feishu developer console.

FEISHU_APP_ID=cli_xxxxxxxxxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_BITABLE_APP_TOKEN=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Choose at least one access token. tenant_access_token is recommended for automation.
FEISHU_USER_ACCESS_TOKEN=u-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_TENANT_ACCESS_TOKEN=t-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# Optional table IDs if you want to target existing tables.
# FEISHU_PAPERS_TABLE_ID=tblxxxxxxxxxxxxxxxxx
# FEISHU_RELATIONS_TABLE_ID=tblxxxxxxxxxxxxxxxxx

# Network and scheduler tuning.
ARXIV_REQUEST_TIMEOUT=5,30
SYNC_TIMEOUT_SECONDS=7200
# SYNC_PROXY_URL=http://127.0.0.1:7890
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autopaper",
        description="Collect, rank, and sync arXiv papers to Feishu Bitable.",
    )
    parser.add_argument("--version", action="version", version=f"autopaper {__version__}")

    subparsers = parser.add_subparsers(dest="command")

    sync_parser = subparsers.add_parser("sync", help="run one config or all packaged sync configs")
    sync_parser.add_argument("-c", "--config", default="all", help="config name or YAML path, default: all")
    sync_parser.add_argument("--config-dir", help="directory containing YAML configs")

    list_parser = subparsers.add_parser("list-configs", help="list available sync configs")
    list_parser.add_argument("--config-dir", help="directory containing YAML configs")

    init_parser = subparsers.add_parser("init", help="copy example configs and scheduler scripts into a project")
    init_parser.add_argument("--target", default=".", help="target project directory, default: current directory")
    init_parser.add_argument("--force", action="store_true", help="overwrite existing generated files")
    init_parser.add_argument("--with-scripts", action="store_true", help="also copy cron helper scripts")

    health_parser = subparsers.add_parser("health", help="check local setup and arXiv connectivity")
    health_parser.add_argument("--config-dir", help="directory containing YAML configs")
    health_parser.add_argument("--skip-network", action="store_true", help="skip the arXiv network probe")
    health_parser.add_argument("--timeout", type=float, default=20.0, help="network probe timeout in seconds")

    subparsers.add_parser("get-token", help="fetch a Feishu tenant_access_token")

    return parser


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


def configure_network_from_env() -> None:
    """Mirror the scheduler's proxy behavior for direct CLI runs."""
    load_dotenv()
    if any(os.getenv(name) for name in ("http_proxy", "https_proxy", "HTTP_PROXY", "HTTPS_PROXY")):
        return

    proxy_url = os.getenv("SYNC_PROXY_URL", "")
    use_proxy = os.getenv("SYNC_USE_PROXY", "auto")
    if not proxy_url and use_proxy == "auto" and _port_open("127.0.0.1", 7890):
        proxy_url = "http://127.0.0.1:7890"

    if proxy_url:
        os.environ["http_proxy"] = proxy_url
        os.environ["https_proxy"] = proxy_url
        os.environ["HTTP_PROXY"] = proxy_url
        os.environ["HTTPS_PROXY"] = proxy_url

    os.environ.setdefault("no_proxy", "localhost,127.0.0.1,::1")


def _port_open(host: str, port: int, timeout: float = 0.2) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def cmd_init(args: argparse.Namespace) -> int:
    target = Path(args.target).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)

    config_count = _copy_tree(_package_path("config"), target / "conf", args.force)

    env_path = target / ".env.template"
    if args.force or not env_path.exists():
        env_path.write_text(ENV_TEMPLATE, encoding="utf-8")
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
    configure_network_from_env()

    if args.config == "all":
        return 0 if process_all_configs(args.config_dir) else 1

    result = process_single_config(args.config, args.config_dir)
    if result.get("success"):
        print(f"\n✅ {args.config} 同步完成，新增 {result.get('new_papers', 0)} 篇论文")
        return 0

    print(f"\n❌ {args.config} 同步失败: {result.get('error', '未知错误')}")
    return 1


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


def _has_real_value(name: str) -> bool:
    value = os.getenv(name, "")
    return bool(value) and "xxxx" not in value


def cmd_health(args: argparse.Namespace) -> int:
    configure_network_from_env()
    passed = 0
    total = 0

    import_passed, import_total = _check_imports(["arxiv", "hydra", "omegaconf", "yaml", "requests"])
    passed += import_passed
    total += import_total

    total += 1
    config_dir = Path(args.config_dir).expanduser().resolve() if args.config_dir else DEFAULT_CONFIG_DIR
    configs = find_sync_configs(config_dir)
    if configs:
        print(f"✅ configs: found {len(configs)} sync configs in {config_dir}")
        passed += 1
    else:
        print(f"❌ configs: no sync configs found in {config_dir}")

    total += 1
    required_env = ["FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_BITABLE_APP_TOKEN"]
    missing = [name for name in required_env if not _has_real_value(name)]
    has_token = _has_real_value("FEISHU_USER_ACCESS_TOKEN") or _has_real_value("FEISHU_TENANT_ACCESS_TOKEN")
    if not missing and has_token:
        print("✅ Feishu environment variables look complete")
        passed += 1
    else:
        details = missing[:]
        if not has_token:
            details.append("FEISHU_USER_ACCESS_TOKEN or FEISHU_TENANT_ACCESS_TOKEN")
        print(f"⚠️ Feishu environment variables incomplete: {', '.join(details)}")

    if not args.skip_network:
        total += 1
        url = "https://export.arxiv.org/api/query?search_query=all:robot&start=0&max_results=1"
        try:
            response = requests.get(url, timeout=args.timeout)
            response.raise_for_status()
        except requests.RequestException as exc:
            print(f"❌ arXiv connectivity: {exc}")
        else:
            print(f"✅ arXiv connectivity: HTTP {response.status_code}")
            passed += 1

    print(f"\nHealth check: {passed}/{total} checks passed")
    return 0 if passed == total else 1


def cmd_get_token(_: argparse.Namespace) -> int:
    from .get_token import main as get_token_main

    get_token_main()
    return 0


def main(argv: Optional[list[str]] = None) -> int:
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
        "get-token": cmd_get_token,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
