# AutoPaper

AutoPaper 是一个可复用的 arXiv 文献采集、关键词排序、飞书多维表格同步工具。本分支将原来偏脚本式的仓库整理为标准 Python package，并保留 master 分支已有的搜索、排序、飞书同步、批量配置和定时任务能力。

## 适合谁

- 希望每天按多个研究方向自动同步 arXiv 论文的团队。
- 希望复用 `ArxivAPI` / `PaperRanker` 做二次开发的用户。
- 希望用 YAML 管理搜索范围、关键词、Feishu、代理、超时和 smoke test 的用户。

## 包结构

```text
src/autopaper/
  arxiv/           # arXiv 客户端、查询构造、结果解析、PDF 下载
  ranking/         # 关键词匹配、基础评分、高级评分、排序门面
  feishu/          # 多维表格、字段/记录/视图、群通知、token、同步写入
  display/         # 控制台展示和 markdown/txt 报告
  configuration/   # 配置加载、默认配置、网络代理、运行时设置
  core/            # ArXiv API 工厂、搜索服务、排序接口
  sync/            # 单配置/批量同步 orchestration
  cli/             # autopaper 命令行入口
  config/          # 随包分发的默认 YAML 配置和 sync 模板
  scripts/         # 可复制到用户项目的 cron 辅助脚本
```

旧的脚本式模块路径已经迁移，不再支持 `autopaper.arxiv_core`、`autopaper.sync_to_feishu` 等导入。用户代码应使用顶层 API 或新的子包路径。

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

- `search.*`: 搜索领域、最近天数、最大结果数、展示数量、最低评分、日期范围、分批窗口。
- `interest_keywords` / `exclude_keywords`: 关注与排除关键词，支持注释分层、通配符和正则。
- `required_keywords.*`: 必须关键词过滤，支持 `AND` 列表、单项内 `OR`、模糊匹配和阈值。
- `intelligent_matching.*`: 高级评分开关、基础/语义/作者/新颖性/引用潜力权重、模糊阈值、时间衰减。
- `download.*`: PDF 下载、最大下载数、目录、metadata/index、强制下载。
- `display.*` / `output.*`: 排名、评分、分解、统计、报告保存、格式和关键词输出。
- `arxiv.*`: API 超时、page size 退避、重试、空页上限、分类映射、联网 smoke test 参数。
- `runtime.network.*`: 代理模式、代理地址、自动探测、healthcheck、no_proxy。
- `runtime.env.feishu.*`: health/sync 检查需要的飞书环境变量和占位符规则。
- `feishu.*`: 同步开关、领域名、阈值、批大小、低分保留、已有记录更新、同步间隔。
- `feishu.api.*` / `wiki.*` / `bitable.*` / `views.*` / `chat_notification.*`: 飞书 API、Wiki、多维表格、视图和群通知。
- `user_profile.*`: 用户显示名、描述、研究领域标识。

默认值在 `src/autopaper/config/default.yaml`。用户项目通过 `autopaper init` 复制到 `./conf/default.yaml` 后可以覆盖。
旧配置中的 `search_config`、`display_config`、`output_config`、`download_config`、`intelligent_matching_config` 会自动归一化到新 schema。

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

## 飞书写入 smoke test

写入测试会真实访问飞书，请使用极小搜索范围，避免批量污染表格。推荐先加载主仓库的 `.env`：

```bash
set -a
source /home/ubuntu/ws/feishu_paper/.env
set +a

uv run autopaper health --config-dir src/autopaper/config
uv run autopaper sync --config sync_7_vln --config-dir src/autopaper/config
```

如果只是验证链路，先把目标配置中的 `search.days` 和 `search.max_results` 临时缩小到 1-2，并确认 `feishu.sync_threshold` 不会同步大量历史论文。

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

## 功能保留矩阵

重构后按功能组做验收，确保没有从 master 分支丢能力：

| 功能组 | 覆盖方式 |
| --- | --- |
| arXiv 查询、分类映射、日期范围 | `tests/test_master_consistency.py` 与 master `arxiv_core.py` 对比 |
| 真实 arXiv 联网搜索 | `tests/smoke/test_network_smoke.py`，需 `AUTOPAPER_RUN_NETWORK_TESTS=1` |
| 关键词过滤、`AND`/`OR`、通配符、正则、基础评分 | `tests/test_modular_refactor.py` |
| 飞书配置、payload 映射、多选字段 | `tests/test_modular_refactor.py` |
| 飞书 token helper | `tests/test_modular_refactor.py` 和 `autopaper get-token` |
| 单配置/批量同步编排 | `autopaper sync --config ...` 和 `autopaper sync --config all` |
| 群通知和表格链接 | 小范围飞书写入 smoke test |
| 控制台展示和报告输出 | `tests/test_modular_refactor.py` |
| CLI、init、health、配置发现 | `tests/test_package.py` |

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

新的直接子包路径：

```python
from autopaper.arxiv import ArxivAPI
from autopaper.ranking import PaperRanker
from autopaper.feishu import FeishuBitableConnector, sync_papers_to_feishu
from autopaper.display import PaperDisplayer
```

顶层导入仍然可用：

```python
from autopaper import ArxivAPI, PaperRanker, FeishuBitableConnector, sync_papers_to_feishu
```

## 迁移说明

- `autopaper.arxiv_core.ArxivAPI` -> `autopaper.arxiv.ArxivAPI` 或 `autopaper.ArxivAPI`
- `autopaper.arxiv_core.PaperRanker` -> `autopaper.ranking.PaperRanker` 或 `autopaper.PaperRanker`
- `autopaper.feishu_bitable_connector.*` -> `autopaper.feishu.*`
- `autopaper.feishu_chat_notification.*` -> `autopaper.feishu.notifications.*`
- `autopaper.sync_to_feishu.sync_papers_to_feishu` -> `autopaper.feishu.sync_papers_to_feishu`
- `autopaper.paper_display.PaperDisplayer` -> `autopaper.display.PaperDisplayer`
- `autopaper.get_token` -> `autopaper.feishu.tokens` 或 `autopaper get-token`
- Hydra 用户可改用 `python -m autopaper.hydra_app`，新项目优先使用 `autopaper` CLI。

## 排障

- arXiv 连接超时：检查 `runtime.network.proxy` 或设置 `SYNC_PROXY_URL`。
- arXiv 429：缩小 `search.days`、降低 `search.max_results`，或启用更小的分批窗口。
- 飞书 token 过期：运行 `autopaper get-token` 或更新 `.env`。
- 定时任务无日志：检查 `scripts/setup_daily_sync.sh status` 和 `logs/daily_sync_YYYYMMDD.log`。
