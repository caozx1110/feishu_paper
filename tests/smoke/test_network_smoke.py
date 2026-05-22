from __future__ import annotations

import importlib.util
import os
import subprocess
from pathlib import Path

import arxiv
import pytest
from dotenv import load_dotenv

from autopaper.arxiv import ArxivAPI
from autopaper.configuration import configure_network, load_config, normalize_config
from autopaper.configuration.runtime import ArxivRuntimeSettings

REPO_ROOT = Path(__file__).resolve().parents[2]
MASTER_REF = "master"


pytestmark = pytest.mark.network


def _load_master_arxiv_core(tmp_path: Path):
    try:
        source = subprocess.check_output(
            ["git", "show", f"{MASTER_REF}:arxiv_core.py"],
            cwd=REPO_ROOT,
            text=True,
        )
    except subprocess.CalledProcessError as exc:
        pytest.skip(f"cannot load {MASTER_REF}:arxiv_core.py: {exc}")

    master_path = tmp_path / "master_arxiv_core_live.py"
    master_path.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("autopaper_master_arxiv_core_live", master_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_live_arxiv_search_returns_results_and_matches_master(tmp_path):
    if os.getenv("AUTOPAPER_RUN_NETWORK_TESTS") != "1":
        pytest.skip("set AUTOPAPER_RUN_NETWORK_TESTS=1 to run live arXiv smoke tests")

    env_file = os.getenv("AUTOPAPER_ENV_FILE", "/home/ubuntu/ws/feishu_paper/.env")
    if Path(env_file).exists():
        load_dotenv(env_file, override=True)

    cfg = normalize_config(load_config("default"))
    configure_network(cfg)
    smoke_cfg = cfg.get("arxiv", {}).get("smoke_test", {})
    os.environ.setdefault("ARXIV_REQUEST_TIMEOUT", str(smoke_cfg.get("request_timeout", "5,20")))
    settings = ArxivRuntimeSettings.from_config(cfg)

    paper_id = smoke_cfg.get("paper_id", "1706.03762")

    package_api = ArxivAPI(download_dir=str(tmp_path / "package"), client_config=settings)
    package_api.client = package_api._create_client(page_size=1, delay_seconds=0)
    package_result = next(package_api.client.results(arxiv.Search(id_list=[paper_id], max_results=1)))
    package_paper = package_api._parse_arxiv_result(package_result)

    master = _load_master_arxiv_core(tmp_path)
    master_api = master.ArxivAPI(download_dir=str(tmp_path / "master"))
    master_api.client = master_api._create_client(page_size=1, delay_seconds=0)
    master_result = next(master_api.client.results(arxiv.Search(id_list=[paper_id], max_results=1)))
    master_paper = master_api._parse_arxiv_result(master_result)

    assert package_paper, "package search returned no arXiv paper"
    assert master_paper, "master search returned no arXiv paper"
    assert package_paper["arxiv_id"] == master_paper["arxiv_id"]
    assert package_paper["title"] == master_paper["title"]
