from datetime import datetime

import yaml

import autopaper
from autopaper.arxiv import ArxivAPI
from autopaper.configuration import DEFAULT_CONFIG_DIR, find_sync_configs, load_config, normalize_config
from autopaper.cli import build_parser, main


def test_public_imports():
    assert autopaper.__version__
    assert autopaper.ArxivAPI is ArxivAPI


def test_packaged_sync_configs_are_discoverable():
    configs = find_sync_configs()
    assert len(configs) >= 7
    assert "sync_7_vln" in configs


def test_packaged_yaml_files_parse():
    for config_path in DEFAULT_CONFIG_DIR.glob("*.yaml"):
        with config_path.open("r", encoding="utf-8") as f:
            assert yaml.safe_load(f) is not None


def test_extended_config_normalizes_to_runtime_schema():
    cfg = normalize_config(load_config("sync_7_vln"))
    assert cfg.search.days == 3
    assert cfg.feishu.sync_threshold == 0.5
    assert cfg.user_profile.research_area == "vision_language_navigation"


def test_arxiv_query_includes_category_and_date_range(tmp_path):
    api = ArxivAPI(timeout=1, download_dir=str(tmp_path))
    query = api._build_search_query(
        query="robot",
        categories=["cs.RO"],
        date_from=datetime(2026, 1, 1),
        date_to=datetime(2026, 1, 2),
    )

    assert "(robot)" in query
    assert "(cat:cs.RO)" in query
    assert "submittedDate:[202601010000 TO 202601022359]" in query


def test_cli_parser_has_core_commands():
    parser = build_parser()
    help_text = parser.format_help()
    assert "sync" in help_text
    assert "health" in help_text
    assert "init" in help_text
    assert "smoke-search" in help_text


def test_cli_init_copies_configs(tmp_path):
    exit_code = main(["init", "--target", str(tmp_path), "--with-scripts"])

    assert exit_code == 0
    assert (tmp_path / "conf" / "default.yaml").exists()
    assert (tmp_path / "conf" / "sync_7_vln.yaml").exists()
    assert (tmp_path / ".env.template").exists()
    assert (tmp_path / "scripts" / "daily_arxiv_sync.sh").exists()
