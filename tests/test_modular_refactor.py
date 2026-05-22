from __future__ import annotations

import importlib
from datetime import datetime

import pytest

from autopaper import ArxivAPI, FeishuBitableConfig, FeishuBitableConnector, PaperDisplayer, PaperRanker
from autopaper.feishu.tokens import get_tenant_access_token, update_env_file


def test_new_module_paths_are_public_and_old_paths_are_removed():
    assert importlib.import_module("autopaper.arxiv").ArxivAPI is ArxivAPI
    assert importlib.import_module("autopaper.ranking").PaperRanker is PaperRanker
    assert importlib.import_module("autopaper.feishu").FeishuBitableConnector is FeishuBitableConnector
    assert importlib.import_module("autopaper.display").PaperDisplayer is PaperDisplayer

    for removed in [
        "autopaper.arxiv_core",
        "autopaper.arxiv_hydra",
        "autopaper.feishu_bitable_connector",
        "autopaper.feishu_chat_notification",
        "autopaper.get_token",
        "autopaper.paper_display",
        "autopaper.sync_to_feishu",
    ]:
        with pytest.raises(ModuleNotFoundError):
            importlib.import_module(removed)


def test_required_keywords_keep_and_or_semantics():
    ranker = PaperRanker()
    paper = {
        "title": "Zero-shot vision-language navigation with semantic memory",
        "summary": "A robot uses map-free graph reasoning for VLN.",
        "authors_str": "AutoPaper Test",
        "categories": ["cs.RO"],
    }

    passed, matched = ranker.check_required_keywords(
        paper,
        {
            "enabled": True,
            "fuzzy_match": True,
            "similarity_threshold": 0.8,
            "keywords": ["robot OR embodied agent", "vision-language navigation OR VLN"],
        },
    )

    assert passed
    assert "robot" in matched
    assert any(keyword in matched for keyword in ["vision-language navigation", "VLN"])


def test_ranking_wildcard_regex_and_basic_scoring_are_preserved():
    ranker = PaperRanker()
    paper = {
        "title": "Robot navigation with graph memory",
        "summary": "A transformer policy improves embodied navigation.",
        "authors_str": "AutoPaper Test",
        "categories": ["cs.RO"],
        "published_date": datetime.now(),
    }

    score, excluded, matched, excludes = ranker.calculate_relevance_score(
        paper,
        interest_keywords=["regex:graph\\s+memory", "robot"],
        exclude_keywords=["medical"],
    )

    assert score > 0
    assert not excluded
    assert "regex:graph\\s+memory" in matched
    assert excludes == []
    assert ranker.calculate_relevance_score(paper, interest_keywords=["*"])[0] == 1.0


def test_feishu_config_and_payload_mapping_are_preserved():
    config = FeishuBitableConfig(
        app_id="cli_a_test",
        app_secret="secret",
        tenant_access_token="t-" + "1" * 32,
        app_token="app_token",
    )
    connector = FeishuBitableConnector(config)

    payload = connector.format_paper_data(
        {
            "ArXiv ID": "2601.00001",
            "发布日期": "2026-01-01",
            "论文链接": "https://arxiv.org/abs/2601.00001",
            "PDF链接": "https://arxiv.org/pdf/2601.00001",
        }
    )

    assert payload["发布日期"] == 1767196800000
    assert payload["论文链接"]["link"].endswith("2601.00001")
    assert payload["PDF链接"]["text"] == "2601.00001"
    assert connector.prepare_multi_select_field_data("cs.RO, cs.AI, cs.RO") == ["cs.RO", "cs.AI"]


def test_token_helpers_are_usable_from_new_feishu_module(monkeypatch, tmp_path):
    class FakeResponse:
        def json(self):
            return {"code": 0, "tenant_access_token": "tenant-token", "expire": 7200}

    def fake_post(url, json, headers, timeout):
        assert "tenant_access_token" in url
        assert json == {"app_id": "app-id", "app_secret": "app-secret"}
        return FakeResponse()

    monkeypatch.setattr("autopaper.feishu.tokens.requests.post", fake_post)
    result = get_tenant_access_token("app-id", "app-secret")

    assert result["success"] is True
    assert result["tenant_access_token"] == "tenant-token"

    env_file = tmp_path / ".env"
    env_file.write_text("FEISHU_APP_ID=app-id\nFEISHU_TENANT_ACCESS_TOKEN=old\n", encoding="utf-8")
    assert update_env_file("new-token", str(env_file))
    assert "FEISHU_TENANT_ACCESS_TOKEN=new-token" in env_file.read_text(encoding="utf-8")


def test_display_report_still_writes_markdown(tmp_path):
    displayer = PaperDisplayer(output_dir=str(tmp_path))
    displayer.save_papers_report_markdown(
        [
            {
                "title": "Robot Navigation",
                "authors_str": "AutoPaper Test",
                "summary": "A navigation paper.",
                "arxiv_id": "2601.00001",
                "paper_url": "https://arxiv.org/abs/2601.00001",
                "pdf_url": "https://arxiv.org/pdf/2601.00001",
                "relevance_score": 0.9,
            }
        ],
        field_name="robotics",
        days=1,
        include_scores=True,
        output_dir=str(tmp_path),
    )

    report_path = next(tmp_path.glob("*.md"))
    assert report_path.exists()
    assert "Robot Navigation" in report_path.read_text(encoding="utf-8")
