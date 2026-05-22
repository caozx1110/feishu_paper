# Development

## uv workflow

```bash
uv sync --group dev
uv run autopaper --help
uv run autopaper validate-config
uv run pytest
```

联网 smoke test：

```bash
AUTOPAPER_RUN_NETWORK_TESTS=1 \
AUTOPAPER_ENV_FILE=/path/to/project/.env \
uv run pytest tests/smoke/test_network_smoke.py -q
```

构建：

```bash
uv run python -m build
```

## pip workflow

```bash
python -m pip install -e ".[dev]"
python -m pytest
python -m build
```

## Master Consistency

`tests/test_master_consistency.py` 会从 git 中动态加载 `master:arxiv_core.py`，比较：

- 查询字符串构造。
- 默认领域到 arXiv 分类映射。

`tests/smoke/test_network_smoke.py` 会在显式开启时执行真实 arXiv 固定 ID 搜索，并比较 package 与 master 返回的论文 ID 和标题。
