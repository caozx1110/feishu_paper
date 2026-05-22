# Configuration Guide

用户配置目录默认是 `./conf`。可以通过 `autopaper init` 生成：

```bash
autopaper init --target . --with-scripts
```

## default.yaml

`default.yaml` 保存一般不需要频繁修改的默认值：

- `runtime.network`: 代理和 no_proxy。
- `runtime.healthcheck`: health 命令使用的 arXiv URL。
- `runtime.env.feishu`: 必要环境变量名称。
- `arxiv`: API 客户端参数和分类映射。
- `feishu`: API、Bitable、视图、群聊通知。默认关闭写入和通知，生产配置需要显式开启。

## sync_*.yaml

每个 `sync_*.yaml` 是一个研究方向。批量模式会自动发现这些文件。

常用字段：

```yaml
user_profile:
  name: "VLN研究员"
  research_area: "vision_language_navigation"

search:
  field: "robotics"
  days: 3
  max_results: 300
  min_score: 0.5

required_keywords:
  enabled: true
  fuzzy_match: true
  keywords:
    - "vision language navigation OR VLN"

feishu:
  enabled: true
  sync_threshold: 0.5
  chat_notification:
    enabled: false
    target_chat_ids: []
    send_to_all_chats: false
```

## Smoke Test 配置

```yaml
arxiv:
  smoke_test:
    query: "robot"
    paper_id: "1706.03762"
    categories: ["cs.RO"]
    max_results: 2
    days: 7
```

命令：

```bash
autopaper smoke-search --config-dir ./conf --max-results 1
autopaper smoke-search --config-dir ./conf --mode query --max-results 1
```

默认 smoke 使用固定 `paper_id`，更适合检查网络和解析链路；`--mode query` 用于验证当前领域搜索配置。

## 安全运行

```bash
autopaper validate-config --config all --config-dir ./conf
autopaper sync --config sync_7_vln --config-dir ./conf --dry-run --limit 2
autopaper feishu check --config sync_7_vln --config-dir ./conf
```

真实写入前优先使用 `--dry-run`、`--limit`、`--since-days` 缩小范围。群通知可以用 `--no-notify` 临时关闭。开启群通知时，建议先填写 `target_chat_ids`，再用 `autopaper feishu test-notify` 预览 payload；只有明确设置 `send_to_all_chats: true` 或使用 `test-notify --send --all-chats` 时才群发到机器人所在所有群。
