# AutoPaper

AutoPaper 是一个可复用的 arXiv 文献采集、关键词排序、飞书多维表格同步工具。本分支将原来偏脚本式的仓库整理为标准 Python package，并保留 master 分支已有的搜索、排序、飞书同步、批量配置和定时任务能力。

## 适合谁

- 希望每天按多个研究方向自动同步 arXiv 论文的团队。
- 希望复用 `ArxivAPI` / `PaperRanker` 做二次开发的用户。
- 希望用 YAML 管理搜索范围、关键词、Feishu、代理、超时和 smoke test 的用户。

## 包结构

```text
src/autopaper/
  configuration/   # 配置加载、默认配置、网络代理、运行时设置
  core/            # ArXiv API 工厂、搜索服务、排序接口
  sync/            # 单配置/批量同步 orchestration
  cli/             # autopaper 命令行入口
  config/          # 随包分发的默认 YAML 配置和 sync 模板
  scripts/         # 可复制到用户项目的 cron 辅助脚本
```

旧的 `python -m autopaper.arxiv_hydra` 仍保留为兼容入口；新项目优先使用 `autopaper` CLI。

## 安装

推荐使用 `uv`：

```bash
git checkout refactor/industrial-package
uv sync --group dev
uv run autopaper --help
```

也可以使用 pip：

```bash
python -m pip install -e ".[dev]"
autopaper --help
```

## 新项目完整使用步骤

1. 初始化工作目录：

```bash
mkdir my-autopaper
cd my-autopaper
uv run --project /home/ubuntu/ws/feishu_paper_pkg autopaper init --with-scripts
cp .env.template .env
```

2. 编辑 `.env`，至少填写：

```bash
FEISHU_APP_ID=...
FEISHU_APP_SECRET=...
FEISHU_BITABLE_APP_TOKEN=...
FEISHU_TENANT_ACCESS_TOKEN=...
```

`FEISHU_USER_ACCESS_TOKEN` 也可以使用，但自动化任务推荐 `FEISHU_TENANT_ACCESS_TOKEN`。

3. 检查环境：

```bash
uv run --project /home/ubuntu/ws/feishu_paper_pkg autopaper health --config-dir ./conf
```

4. 查看可用同步配置：

```bash
uv run --project /home/ubuntu/ws/feishu_paper_pkg autopaper list-configs --config-dir ./conf
```

5. 手动同步全部配置：

```bash
uv run --project /home/ubuntu/ws/feishu_paper_pkg autopaper sync --config all --config-dir ./conf
```

6. 手动同步单个方向：

```bash
uv run --project /home/ubuntu/ws/feishu_paper_pkg autopaper sync --config sync_7_vln --config-dir ./conf
```

7. 安装每日定时任务：

```bash
chmod +x scripts/*.sh
scripts/setup_daily_sync.sh install
scripts/setup_daily_sync.sh status
```

## 配置原则

AutoPaper 的可变行为都应从 YAML 配置或环境变量进入，不在业务入口写死：

- `search`: 搜索领域、时间范围、最大结果数、分批处理。
- `interest_keywords` / `exclude_keywords` / `required_keywords`: 排序和过滤规则。
- `arxiv`: API 超时、page size 退避、分类映射、联网 smoke test 参数。
- `runtime.network`: 代理、healthcheck、no_proxy。
- `runtime.env.feishu`: health 检查需要的环境变量名称。
- `feishu`: 多维表格、视图、群聊通知和同步阈值。

默认值在 `src/autopaper/config/default.yaml`。用户项目通过 `autopaper init` 复制到 `./conf/default.yaml` 后可以覆盖。

## 联网 smoke test

命令行快速测试：

```bash
uv run autopaper smoke-search --max-results 1
```

pytest 联网测试默认跳过，需要显式开启：

```bash
AUTOPAPER_RUN_NETWORK_TESTS=1 \
AUTOPAPER_ENV_FILE=/home/ubuntu/ws/feishu_paper/.env \
uv run pytest tests/smoke/test_network_smoke.py -q
```

该测试会同时调用 package 版本和 master 分支的 `arxiv_core.py`，并比较返回的第一篇论文 ID 与标题，确保核心搜索结果一致。

## 开发验证

```bash
uv sync --group dev
uv run pytest
AUTOPAPER_RUN_NETWORK_TESTS=1 AUTOPAPER_ENV_FILE=/home/ubuntu/ws/feishu_paper/.env uv run pytest tests/smoke/test_network_smoke.py -q
uv run python -m build
```

pip 等价命令：

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m build
```

## Python API

```python
from autopaper.configuration import load_config, normalize_config
from autopaper.core import SearchService, create_arxiv_api

cfg = normalize_config(load_config("sync_7_vln"))
papers = SearchService(create_arxiv_api(cfg)).fetch(cfg)
```

```python
from autopaper import ArxivAPI, PaperRanker

api = ArxivAPI()
papers = api.search_papers(query="robot", categories=["cs.RO"], max_results=3)
ranker = PaperRanker()
ranked, excluded, stats = ranker.filter_and_rank_papers(
    papers,
    interest_keywords=["navigation", "robot"],
    exclude_keywords=["medical"],
    min_score=0.1,
)
```

## 排障

- arXiv 连接超时：检查 `runtime.network.proxy` 或设置 `SYNC_PROXY_URL`。
- arXiv 429：缩小 `search.days`、降低 `search.max_results`，或启用更小的分批窗口。
- 飞书 token 过期：运行 `autopaper get-token` 或更新 `.env`。
- 定时任务无日志：检查 `scripts/setup_daily_sync.sh status` 和 `logs/daily_sync_YYYYMMDD.log`。
