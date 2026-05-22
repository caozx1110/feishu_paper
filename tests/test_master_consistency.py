from __future__ import annotations

import importlib.util
from datetime import datetime
from pathlib import Path

from autopaper.arxiv import ArxivAPI
from autopaper.configuration import load_config, normalize_config
from autopaper.configuration.runtime import ArxivRuntimeSettings

MASTER_ARXIV_CORE = Path("/home/ubuntu/ws/feishu_paper/arxiv_core.py")


def _load_master_arxiv_core():
    spec = importlib.util.spec_from_file_location("autopaper_master_arxiv_core", MASTER_ARXIV_CORE)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_query_builder_matches_master(tmp_path):
    master = _load_master_arxiv_core()
    package_api = ArxivAPI(download_dir=str(tmp_path / "package"))
    master_api = master.ArxivAPI(download_dir=str(tmp_path / "master"))

    kwargs = {
        "query": "robot",
        "categories": ["cs.RO"],
        "date_from": datetime(2026, 1, 1),
        "date_to": datetime(2026, 1, 2),
    }

    assert package_api._build_search_query(**kwargs) == master_api._build_search_query(**kwargs)


def test_default_field_categories_match_master(tmp_path):
    master = _load_master_arxiv_core()
    cfg = normalize_config(load_config("default"))
    settings = ArxivRuntimeSettings.from_config(cfg)
    package_api = ArxivAPI(download_dir=str(tmp_path / "package"))
    configured_api = ArxivAPI(download_dir=str(tmp_path / "configured"), client_config=settings)
    master_api = master.ArxivAPI(download_dir=str(tmp_path / "master"))

    fields = ["ai", "robotics", "cv", "nlp", "all", "ai+robotics", "cs.RO"]
    for field in fields:
        assert package_api._get_field_categories(field) == master_api._get_field_categories(field)
        assert sorted(configured_api._get_field_categories(field)) == sorted(master_api._get_field_categories(field))
