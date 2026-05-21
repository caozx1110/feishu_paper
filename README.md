# AutoPaper

AutoPaper collects recent arXiv papers, ranks them with configurable keyword rules, and syncs selected papers into Feishu Bitable. This branch packages the original script-based repository as a reusable Python package while keeping the master branch sync behavior and YAML configs.

## Features

- arXiv search by recent days or explicit date range.
- Field/category presets for AI, robotics, CV, NLP, physics, math, statistics, EESS, and biology.
- Keyword ranking with exclude terms, required terms, fuzzy matching, and optional advanced scoring.
- Feishu Bitable sync with per-domain tables, duplicate detection, view management, and optional chat notifications.
- Batch sync across all `sync_*.yaml` configs.
- CLI commands for initialization, health checks, config listing, token fetching, and sync.

## Installation

For local development:

```bash
git checkout dev/pkg
python -m pip install -e ".[dev]"
```

For runtime-only use from a checked out source tree:

```bash
python -m pip install -e .
```

## Quick Start

Create a project directory with editable configs:

```bash
mkdir my-autopaper
cd my-autopaper
autopaper init --with-scripts
cp .env.template .env
```

Edit `.env` with Feishu credentials, then run:

```bash
autopaper health --config-dir ./conf
autopaper list-configs --config-dir ./conf
autopaper sync --config all --config-dir ./conf
```

Run one config:

```bash
autopaper sync --config sync_7_vln --config-dir ./conf
```

The packaged default configs can also be used directly:

```bash
autopaper sync --config all
```

## Configuration

`autopaper init` copies the packaged YAML files into `./conf`. Files named `sync_*.yaml` participate in batch sync.

Common settings:

- `search.days`: recent-day search window when `date_range.enabled` is false.
- `search.date_range`: explicit `YYYY-MM-DD` range search for backfills.
- `search.batch_processing`: split large ranges to avoid arXiv API failures.
- `interest_keywords`: positive ranking keywords.
- `exclude_keywords`: negative filters.
- `required_keywords`: hard requirement filters with optional fuzzy matching.
- `feishu.sync_threshold`: minimum score required before a paper is synced.

Sensitive values are read from environment variables through `.env`.

Required Feishu variables:

```bash
FEISHU_APP_ID=...
FEISHU_APP_SECRET=...
FEISHU_BITABLE_APP_TOKEN=...
FEISHU_TENANT_ACCESS_TOKEN=...
```

`FEISHU_USER_ACCESS_TOKEN` can be used instead of `FEISHU_TENANT_ACCESS_TOKEN`, but tenant tokens are usually better for automation.

## Scheduling

After `autopaper init --with-scripts`, install the daily cron job:

```bash
chmod +x scripts/*.sh
scripts/setup_daily_sync.sh install
scripts/setup_daily_sync.sh status
```

The default schedule is daily at 10:00 in the system timezone. Override it before installing:

```bash
AUTOPAPER_CRON_SCHEDULE="0 10 * * *" scripts/setup_daily_sync.sh install
```

The daily script supports network tuning:

```bash
ARXIV_REQUEST_TIMEOUT=5,30
SYNC_TIMEOUT_SECONDS=7200
SYNC_PROXY_URL=http://127.0.0.1:7890
```

Logs are written to `logs/daily_sync_YYYYMMDD.log`.

## Python API

```python
from autopaper import ArxivAPI, PaperRanker

api = ArxivAPI()
papers = api.get_recent_papers(days=3, field_type="robotics", max_results=100)

ranker = PaperRanker()
ranked, excluded, stats = ranker.filter_and_rank_papers(
    papers,
    interest_keywords=["vision-language navigation", "robotics"],
    exclude_keywords=["medical"],
    min_score=0.2,
)
```

## Compatibility

The original Hydra entry point is still available for advanced overrides:

```bash
python -m autopaper.arxiv_hydra --config-name=default search.field=robotics
python -m autopaper.arxiv_hydra --config-name=all
```

For normal package use, prefer the `autopaper` CLI because it supports external config directories without relying on the repository root.

## Development

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m build
```

Basic non-network tests cover package imports, bundled configs, CLI parsing, initialization, and arXiv query construction.

## Troubleshooting

- Run `autopaper health --config-dir ./conf` first; it checks imports, configs, Feishu env variables, and arXiv connectivity.
- If arXiv connectivity is slow, set `ARXIV_REQUEST_TIMEOUT=5,30` or configure `HTTP_PROXY` / `HTTPS_PROXY`.
- If Feishu sync fails, verify the app token, app credentials, and access token in `.env`.
- For automated jobs, prefer `FEISHU_TENANT_ACCESS_TOKEN`; refresh it with `autopaper get-token`.
