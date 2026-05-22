# AutoPaper

AutoPaper 是一个可复用的 arXiv 文献采集、关键词排序、飞书多维表格同步工具。本分支将原来偏脚本式的仓库整理为标准 Python package，并保留 master 分支已有的搜索、排序、飞书同步、批量配置和定时任务能力。

## 适合谁

- 希望每天按多个研究方向自动同步 arXiv 论文的团队。
- 希望复用 `ArxivAPI` / `PaperRanker` 做二次开发的用户。
- 希望用 YAML 管理搜索范围、关键词、Feishu、代理、超时和 smoke test 的用户。
- 希望命令行输出带表格、面板、状态色和清晰下一步提示的用户。

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

如果要在任意目录使用 CLI，可以先安装为可编辑命令：

```bash
uv tool install -e .
autopaper --help
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
autopaper init --with-scripts
cp .env.template .env
```

如果尚未安装 `autopaper` 命令，也可以用 `uv run --project /path/to/autopaper autopaper ...` 调用本地源码。

2. 编辑 `.env`，至少填写：

```bash
FEISHU_APP_ID=...
FEISHU_APP_SECRET=...
FEISHU_BITABLE_APP_TOKEN=...
FEISHU_TENANT_ACCESS_TOKEN=...
```

`FEISHU_USER_ACCESS_TOKEN` 也可以使用，但自动化任务推荐 `FEISHU_TENANT_ACCESS_TOKEN`。

3. 检查配置和基础环境。默认配置不会写入飞书，也不会发送群通知：

```bash
autopaper validate-config --config all --config-dir ./conf
autopaper health --config-dir ./conf --skip-network
```

4. 查看可用同步配置，并做一次稳定的 arXiv 联网 smoke test：

```bash
autopaper list-configs --config-dir ./conf
autopaper smoke-search --config-dir ./conf --max-results 1
```

5. 先 dry-run 单个方向。该命令会真实搜索和排序，但不会写入飞书：

```bash
autopaper sync --config sync_7_vln --config-dir ./conf --dry-run --limit 2
```

6. 验证飞书权限。`test-notify` 默认只检查机器人所在群；添加 `--send` 才会发送真实测试消息：

```bash
autopaper feishu check --config sync_7_vln --config-dir ./conf
autopaper feishu test-notify --config sync_7_vln --config-dir ./conf
```

7. 确认范围安全后再真实同步：

```bash
autopaper sync --config sync_7_vln --config-dir ./conf --limit 2 --no-notify
autopaper sync --config all --config-dir ./conf --dry-run --limit 2
```

8. 安装每日定时任务：

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

## CLI 常用安全开关

- `--dry-run`: 执行搜索和排序，展示预计同步数量，不写飞书。
- `--limit N`: 限制本次搜索/排序数量，适合 smoke test。
- `--since-days N`: 临时覆盖 `search.days`，并关闭 date range。
- `--no-feishu`: 本次运行跳过飞书写入。
- `--no-notify`: 本次运行跳过群通知。
- `--env-file PATH`: 显式加载 `.env` 文件。
- `--verbose`: 显示诊断细节，例如 arXiv query、分页退避、飞书视图 payload；默认只显示关键进度。
- `--quiet`: 只显示成功、警告和错误等必要输出。

## 飞书群通知

群聊通知默认关闭。开启前建议先只做检查，不发送真实消息：

```bash
uv run autopaper --env-file .env feishu test-notify --config sync_7_vln --config-dir ./conf
```

如需限制目标群，在配置中填写 `feishu.chat_notification.target_chat_ids`；留空时只有显式设置 `send_to_all_chats: true` 或运行 `test-notify --send --all-chats` 才会发给机器人所在的全部群。`message_template: "default"` 会发送飞书消息卡片，`"text"` 使用纯文本备用格式。

## 联网 smoke test

命令行快速测试默认使用固定 arXiv ID，避免宽泛搜索受当天结果和限流影响：

```bash
uv run autopaper smoke-search --max-results 1
```

如需验证配置里的领域搜索，可以显式使用 query 模式：

```bash
uv run autopaper smoke-search --mode query --max-results 1
```

pytest 联网测试默认跳过，需要显式开启：

```bash
AUTOPAPER_RUN_NETWORK_TESTS=1 \
AUTOPAPER_ENV_FILE=/home/ubuntu/ws/feishu_paper/.env \
uv run pytest tests/smoke/test_network_smoke.py -q
```

该测试会从 git 的 `master:arxiv_core.py` 加载基线，并比较固定论文 ID 的解析结果，确保 package 与 master 的核心搜索结果一致。

## 飞书写入 smoke test

写入测试会真实访问飞书，请使用极小搜索范围，避免批量污染表格。推荐显式指定 `.env`：

```bash
uv run autopaper --env-file /home/ubuntu/ws/feishu_paper/.env health --config sync_7_vln --config-dir src/autopaper/config
uv run autopaper --env-file /home/ubuntu/ws/feishu_paper/.env feishu check --config sync_7_vln --config-dir src/autopaper/config
uv run autopaper --env-file /home/ubuntu/ws/feishu_paper/.env sync --config sync_7_vln --config-dir src/autopaper/config --limit 2 --no-notify
```

如果只是验证链路，优先用 `--dry-run --limit 2 --since-days 1`，确认 `feishu.sync_threshold` 不会同步大量历史论文后再移除 `--dry-run`。

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
| arXiv 查询、分类映射、日期范围 | `tests/test_master_consistency.py` 与 git `master:arxiv_core.py` 对比 |
| 真实 arXiv 联网搜索 | `tests/smoke/test_network_smoke.py`，需 `AUTOPAPER_RUN_NETWORK_TESTS=1` |
| 关键词过滤、`AND`/`OR`、通配符、正则、基础评分 | `tests/test_modular_refactor.py` |
| 飞书配置、payload 映射、多选字段 | `tests/test_modular_refactor.py` |
| 飞书 token helper | `tests/test_modular_refactor.py` 和 `autopaper get-token` |
| 单配置/批量同步编排 | `autopaper sync --config ...` 和 `autopaper sync --config all` |
| 群通知和表格链接 | 小范围飞书写入 smoke test |
| 控制台展示和报告输出 | `tests/test_modular_refactor.py` |
| CLI、init、health、配置发现、安全默认值 | `tests/test_package.py` |

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
- 不确定会写入多少：先运行 `autopaper sync --dry-run --limit 2`。
- 飞书权限不确定：先运行 `autopaper feishu check` 和 `autopaper feishu list-tables`。
- 飞书 token 过期：运行 `autopaper get-token` 或更新 `.env`。
- 定时任务无日志：检查 `scripts/setup_daily_sync.sh status` 和 `logs/daily_sync_YYYYMMDD.log`。
