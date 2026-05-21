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
- `feishu`: API、Bitable、视图、群聊通知。

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
```

## Smoke Test 配置

```yaml
arxiv:
  smoke_test:
    query: "robot"
    categories: ["cs.RO"]
    max_results: 2
    days: 7
```

命令：

```bash
autopaper smoke-search --config-dir ./conf --max-results 1
```
