# AutoPaper

AutoPaper 是一个自动采集 arXiv 论文、按关键词筛选排序、同步到飞书多维表格并发送飞书群通知的工具。适合每天按多个研究方向追踪新论文，并把结果沉淀到团队共享表格中。

## 功能

| 能力             | 说明                                                                                                  |
| ---------------- | ----------------------------------------------------------------------------------------------------- |
| arXiv 论文采集   | 按领域、分类、最近天数或日期范围检索论文，支持批量分页和网络重试。                                    |
| 关键词筛选       | 支持兴趣关键词、排除关键词、必须关键词、`AND` / `OR`、通配符、正则和模糊匹配。                    |
| 论文排序         | 根据命中关键词、评分阈值和可选高级评分策略筛选推荐论文。                                              |
| 飞书多维表格同步 | 自动查找或创建研究方向表格，写入论文标题、作者、摘要、分类、评分、关键词、链接和日期。                |
| 去重与增量同步   | 按 ArXiv ID 检查已有记录，只同步新增论文，避免重复写入。                                              |
| 飞书群通知       | 完整同步后发送汇总消息，包含新增数量、相关表格总计、推荐论文和表格链接。                              |
| 多方向批量同步   | `sync_*.yaml` 每个文件对应一个研究方向，`all.yaml` 统一批量执行并汇总通知。                       |
| 定时任务         | 初始化项目时复制 cron 脚本，可每天自动同步并在有新增论文时通知。                                      |
| 命令行体验       | 提供 `init`、`health`、`feishu check`、`feishu test-notify`、`sync`、`get-token` 等命令。 |

## 安装

推荐使用 `uv`：

```bash
uv sync --group dev
uv run autopaper --help
```

安装为可直接调用的命令：

```bash
uv tool install -e .
autopaper --help
```

也可以使用 pip：

```bash
python -m pip install -e .
autopaper --help
```

## Quick Start

下面是一套从零开始的完整流程：初始化项目、配置飞书、同步全部方向，并在有新增论文时发送飞书群通知。

### 1. 初始化项目

```bash
mkdir my-autopaper
cd my-autopaper
autopaper init --with-scripts
cp .env.template .env
```

生成后的主要文件：

| 路径                            | 用途                                       |
| ------------------------------- | ------------------------------------------ |
| `.env`                        | 飞书应用密钥、访问 token、多维表格 token。 |
| `conf/default.yaml`           | 通用默认配置。                             |
| `conf/all.yaml`               | 批量同步和飞书汇总通知配置。               |
| `conf/sync_*.yaml`            | 每个研究方向的搜索、关键词和同步配置。     |
| `scripts/setup_daily_sync.sh` | 定时任务安装和管理脚本。                   |
| `scripts/daily_arxiv_sync.sh` | 每日同步执行脚本。                         |

如果没有全局安装 `autopaper` 命令，可以在源码仓库中使用：

```bash
uv run autopaper init --target my-autopaper --with-scripts
```

### 2. 配置飞书环境变量

编辑 `.env`：

```bash
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_BITABLE_APP_TOKEN=xxx
FEISHU_TENANT_ACCESS_TOKEN=t-xxx
```

如果还没有 `FEISHU_TENANT_ACCESS_TOKEN`，可以用应用 ID 和密钥获取并保存：

```bash
autopaper get-token --env-file .env --save
```

### 3. 配置飞书群通知

编辑 `conf/all.yaml`，开启批量汇总通知：

```yaml
feishu:
  enabled: true
  sync_threshold: 0.3
  batch_size: 50
  chat_notification:
    enabled: true
    min_papers_threshold: 1
    max_recommended_papers: 1
    message_template: "default"
    include_table_links: true
    send_to_all_chats: false
    target_chat_ids:
      - "oc_xxx_your_chat_id"
```

推荐在生产环境填写 `target_chat_ids`。如果机器人只加入一个测试群，可以临时使用：

```yaml
send_to_all_chats: true
target_chat_ids: []
```

通知发送条件：

| 条件                          | 说明                                                       |
| ----------------------------- | ---------------------------------------------------------- |
| 使用 `sync --config all`    | 批量同步完成后才发送汇总通知。                             |
| 本次有新增论文                | 没有新增记录时不会通知。                                   |
| 达到 `min_papers_threshold` | 新增数量小于阈值时不会通知。                               |
| 未使用跳过参数                | 不要加 `--dry-run`、`--no-feishu` 或 `--no-notify`。 |

### 4. 检查配置和飞书连通性

```bash
autopaper --env-file .env validate-config --config all --config-dir ./conf
autopaper --env-file .env health --config all --config-dir ./conf --skip-network
autopaper --env-file .env feishu check --config sync_1_llm_robotics --config-dir ./conf
```

### 5. 先小范围试运行

先确认搜索、排序和飞书写入链路。`--limit 2` 会限制本次处理数量，`--no-notify` 避免测试时发送正式汇总通知：

```bash
autopaper --env-file .env sync --config sync_1_llm_robotics --config-dir ./conf --limit 2 --no-notify
```

再检查批量同步流程，但不写入飞书：

```bash
autopaper --env-file .env sync --config all --config-dir ./conf --dry-run --limit 2
```

### 6. 完整同步并发送飞书通知

确认配置无误后，执行完整同步：

```bash
autopaper --env-file .env sync --config all --config-dir ./conf
```

这个命令会：

| 步骤                      | 行为                                           |
| ------------------------- | ---------------------------------------------- |
| 读取 `conf/sync_*.yaml` | 按每个研究方向分别搜索 arXiv。                 |
| 关键词筛选和排序          | 只保留满足规则和评分阈值的论文。               |
| 写入飞书多维表格          | 新论文写入对应研究方向表格。                   |
| 发送飞书汇总通知          | 有新增论文且达到阈值时，向配置的群聊发送消息。 |

### 7. 开启每日自动同步

```bash
chmod +x scripts/*.sh
scripts/setup_daily_sync.sh install
scripts/setup_daily_sync.sh status
```

默认每天按 `AUTOPAPER_CRON_SCHEDULE` 执行，默认值为 `0 10 * * *`。可通过环境变量调整：

```bash
AUTOPAPER_CRON_SCHEDULE="0 9 * * *" scripts/setup_daily_sync.sh install
```

定时任务默认执行：

```bash
autopaper sync --config all
```

因此，只要 `conf/all.yaml` 中开启 `feishu.chat_notification.enabled: true`，每天有新增论文时就会自动发送飞书通知。日志在：

```text
logs/daily_sync_YYYYMMDD.log
```

## 常用命令

| 命令                                                                                      | 用途                           |
| ----------------------------------------------------------------------------------------- | ------------------------------ |
| `autopaper list-configs --config-dir ./conf`                                            | 查看所有同步配置。             |
| `autopaper validate-config --config all --config-dir ./conf`                            | 校验全部配置。                 |
| `autopaper health --config all --config-dir ./conf --skip-network`                      | 检查包、配置和飞书环境变量。   |
| `autopaper feishu check --config sync_1_llm_robotics --config-dir ./conf`               | 检查飞书多维表格访问权限。     |
| `autopaper feishu test-notify --config all --config-dir ./conf --send`                  | 发送飞书测试通知。             |
| `autopaper sync --config sync_1_llm_robotics --config-dir ./conf --limit 2 --no-notify` | 小范围同步单个方向。           |
| `autopaper sync --config all --config-dir ./conf`                                       | 完整批量同步并按条件发送通知。 |

## 配置入口

| 配置                           | 说明                                                     |
| ------------------------------ | -------------------------------------------------------- |
| `search.*`                   | 搜索领域、最近天数、最大结果数、日期范围、批处理窗口。   |
| `interest_keywords`          | 感兴趣关键词，影响评分和排序。                           |
| `exclude_keywords`           | 排除关键词，命中后过滤论文。                             |
| `required_keywords.*`        | 必须命中的关键词规则，支持 `AND` / `OR` 和模糊匹配。 |
| `feishu.sync_threshold`      | 飞书同步最低评分阈值。                                   |
| `feishu.chat_notification.*` | 群通知开关、目标群、推荐论文数量、消息模板。             |
| `user_profile.*`             | 研究方向名称、描述和飞书表格命名。                       |

## Python API

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
