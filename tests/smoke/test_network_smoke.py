from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest
from dotenv import load_dotenv

from autopaper.arxiv_core import ArxivAPI
from autopaper.configuration import configure_network, load_config, normalize_config
from autopaper.configuration.runtime import ArxivRuntimeSettings

MASTER_ARXIV_CORE = Path("/home/ubuntu/ws/feishu_paper/arxiv_core.py")


pytestmark = pytest.mark.network


def _load_master_arxiv_core():
    spec = importlib.util.spec_from_file_location("autopaper_master_arxiv_core_live", MASTER_ARXIV_CORE)
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
    settings = ArxivRuntimeSettings.from_config(cfg)

    query = smoke_cfg.get("query", "robot")
    categories = list(smoke_cfg.get("categories", ["cs.RO"]))

    package_api = ArxivAPI(download_dir=str(tmp_path / "package"), client_config=settings)
    package_papers = package_api.search_papers(query=query, categories=categories, max_results=1)

    master = _load_master_arxiv_core()
    master_api = master.ArxivAPI(download_dir=str(tmp_path / "master"))
    master_papers = master_api.search_papers(query=query, categories=categories, max_results=1)

    assert package_papers, "package search returned no arXiv papers"
    assert master_papers, "master search returned no arXiv papers"
    assert package_papers[0]["arxiv_id"] == master_papers[0]["arxiv_id"]
    assert package_papers[0]["title"] == master_papers[0]["title"]
