from __future__ import annotations

from datetime import datetime

import pytest
from omegaconf import OmegaConf

from autopaper.feishu.records import FeishuRecordMixin
from autopaper.feishu.sync import sync_papers_to_feishu
from autopaper.feishu.sync_result import FeishuSyncResult
from autopaper.sync.runner import SyncRunner, send_batch_summary_notification


def _cfg():
    return OmegaConf.create(
        {
            "interest_keywords": ["robot"],
            "exclude_keywords": [],
            "required_keywords": {"enabled": False, "keywords": []},
            "search": {"min_score": 0.1},
            "intelligent_matching": {"enabled": False},
            "user_profile": {"name": "测试研究员", "research_area": "robotics"},
            "feishu": {
                "enabled": True,
                "sync_threshold": 0.5,
                "batch_size": 2,
                "api": {
                    "app_id": "cli_a_test",
                    "app_secret": "secret",
                    "tenant_access_token": "t-" + "1" * 32,
                    "base_url": "https://feishu.example/open-apis",
                    "timeout": 7,
                    "max_retries": 1,
                    "retry_delay": 0.0,
                },
                "bitable": {"app_token": "app-token"},
                "views": {"enabled": False},
                "chat_notification": {"enabled": False},
            },
        }
    )


def _paper(**overrides):
    paper = {
        "arxiv_id": "2601.00001",
        "title": "Robot navigation with graph memory",
        "summary": "A robot navigation paper.",
        "authors": ["AutoPaper Test"],
        "categories": ["cs.RO"],
        "paper_url": "https://arxiv.org/abs/2601.00001",
        "pdf_url": "https://arxiv.org/pdf/2601.00001",
        "published_date": datetime(2026, 1, 1),
        "updated_date": datetime(2026, 1, 2),
        "final_score": 0.91,
        "matched_interests": ["robot"],
    }
    paper.update(overrides)
    return paper


def test_feishu_sync_uses_hydra_config_and_returns_structured_result(monkeypatch):
    created_configs = []

    class FakeConnector:
        def __init__(self, config):
            created_configs.append(config)

        def find_table_by_name(self, table_name):
            assert table_name == "测试论文表"
            return "tbl"

        def get_all_records(self, table_id):
            assert table_id == "tbl"
            return []

        def batch_insert_records(self, table_id, batch):
            assert table_id == "tbl"
            assert batch[0]["ArXiv ID"]["text"] == "2601.00001"
            return {"records": [{"record_id": "rec"} for _ in batch]}

    monkeypatch.setattr("autopaper.feishu.sync.FeishuBitableConnector", FakeConnector)

    result = sync_papers_to_feishu([_paper()], _cfg())

    assert isinstance(result, FeishuSyncResult)
    assert result.success is True
    assert result.synced_count == 1
    assert result.table_id == "tbl"
    assert created_configs[0].base_url == "https://feishu.example/open-apis"
    assert created_configs[0].timeout == 7
    assert created_configs[0].app_token == "app-token"


def test_feishu_sync_reports_batch_write_failures(monkeypatch):
    class FailingConnector:
        def __init__(self, config):
            self.config = config

        def find_table_by_name(self, table_name):
            return "tbl"

        def get_all_records(self, table_id):
            return []

        def batch_insert_records(self, table_id, batch):
            raise RuntimeError("boom")

    monkeypatch.setattr("autopaper.feishu.sync.FeishuBitableConnector", FailingConnector)

    result = sync_papers_to_feishu([_paper()], _cfg())

    assert result.success is False
    assert result.synced_count == 0
    assert result.failed_count == 1
    assert "boom" in result.errors[0]


def test_sync_runner_marks_structured_sync_failure_as_failure(monkeypatch):
    cfg = _cfg()
    ranked = [_paper()]
    failure = FeishuSyncResult.failed("write failed", would_sync_count=1, failed_count=1)

    class FakeSearchService:
        def __init__(self, api):
            self.api = api

        def fetch(self, final_cfg):
            return ranked

    monkeypatch.setattr("autopaper.sync.runner.load_config", lambda *args, **kwargs: cfg)
    monkeypatch.setattr("autopaper.sync.runner.normalize_config", lambda config: config)
    monkeypatch.setattr("autopaper.sync.runner.create_arxiv_api", lambda final_cfg: object())
    monkeypatch.setattr("autopaper.sync.runner.SearchService", FakeSearchService)
    monkeypatch.setattr(SyncRunner, "_rank_and_sync", lambda self, papers, final_cfg: (ranked, failure, 1))

    result = SyncRunner().process_single_config("sync_test")

    assert result["success"] is False
    assert result["new_papers"] == 0
    assert result["sync_errors"] == ["write failed"]
    assert result["error"] == "write failed"


def test_batch_summary_notification_uses_feishu_database_total(monkeypatch):
    captured = {}

    class FakeNotifier:
        def generate_table_link(self, table_name):
            return f"https://feishu.example/{table_name}"

        def notify_paper_updates(self, update_stats, papers_by_field, table_links):
            captured["update_stats"] = update_stats
            captured["papers_by_field"] = papers_by_field
            captured["table_links"] = table_links
            return True

    sync_result = FeishuSyncResult(
        success=True,
        synced_count=2,
        total_existing=41,
        table_name="测试论文表",
        research_area="robotics",
    )

    monkeypatch.setattr("autopaper.sync.runner.load_config", lambda *args, **kwargs: OmegaConf.create({}))
    monkeypatch.setattr("autopaper.sync.runner.normalize_config", lambda cfg: cfg)
    monkeypatch.setattr("autopaper.sync.runner.create_chat_notifier_from_config", lambda cfg: FakeNotifier())

    ok = send_batch_summary_notification(
        [
            {
                "config_name": "sync_test",
                "success": True,
                "new_papers": 2,
                "total_papers": 500,
                "research_area": "robotics",
                "table_name": "测试论文表",
                "ranked_papers": [_paper()],
                "sync_result": sync_result,
            }
        ]
    )

    assert ok is True
    assert captured["update_stats"]["测试"]["new_count"] == 2
    assert captured["update_stats"]["测试"]["total_count"] == 43
    assert captured["table_links"]["测试"].endswith("测试论文表")


def test_check_record_exists_does_not_mask_lookup_errors():
    class BrokenRecordClient(FeishuRecordMixin):
        config = type("Config", (), {"app_token": "app-token"})()

        def _make_request(self, method, endpoint, **kwargs):
            raise RuntimeError("lookup failed")

    with pytest.raises(RuntimeError, match="lookup failed"):
        BrokenRecordClient().check_record_exists("tbl", "2601.00001")
