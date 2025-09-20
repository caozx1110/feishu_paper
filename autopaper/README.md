# AutoPaper

自动化论文管理和同步工具 - 从 arXiv 获取论文并同步到飞书表格

## 简介

AutoPaper 是一个 Python 包，用于自动化管理学术论文的获取、处理和同步。它可以从 arXiv 搜索和获取论文信息，格式化显示，并将结果同步到飞书多维表格中。

## 功能特性

- 🔍 **智能搜索**: 支持多字段搜索（标题、摘要、作者）
- 📊 **飞书集成**: 自动同步到飞书多维表格
- 🎨 **格式化输出**: 支持多种输出格式（表格、JSON、Markdown）
- 📱 **消息通知**: 支持飞书群聊通知
- ⚙️ **灵活配置**: 支持多种配置文件格式
- 🔄 **增量同步**: 支持增量更新，避免重复数据
- 📝 **丰富日志**: 详细的日志记录和错误追踪

## 安装

### 使用 pip 安装

```bash
pip install autopaper
```

### 从源码安装

```bash
git clone https://github.com/yourusername/autopaper.git
cd autopaper
pip install -e .
```

## 快速开始

### 1. 配置

创建配置文件 `config.yaml`:

```yaml
feishu:
  app_id: "your_app_id"
  app_secret: "your_app_secret"
  table_id: "your_table_id"
  chat_id: "your_chat_id"

arxiv:
  max_results: 50
  categories:
    - "cs.AI"
    - "cs.LG"
    - "cs.RO"
```

### 2. 使用命令行

```bash
# 搜索论文
autopaper search --query "machine learning" --max-results 20

# 同步到飞书
autopaper sync --config config.yaml

# 查看帮助
autopaper --help
```

### 3. 使用 Python API

```python
from autopaper import ArxivProcessor, FeishuConnector, PaperFormatter

# 初始化组件
arxiv = ArxivProcessor(max_results=50)
feishu = FeishuConnector(app_id="your_id", app_secret="your_secret")
formatter = PaperFormatter()

# 搜索论文
papers = arxiv.search_papers(
    query="machine learning",
    categories=["cs.AI", "cs.LG"]
)

# 格式化并同步
for paper in papers:
    formatted = formatter.format_for_feishu(paper)
    feishu.add_record("table_id", formatted)
```

## 配置说明

### ArXiv 配置

```yaml
arxiv:
  max_results: 100        # 最大搜索结果数
  timeout: 30            # 请求超时时间（秒）
  categories:            # 论文类别
    - "cs.AI"
    - "cs.LG"
    - "cs.RO"
```

### 飞书配置

```yaml
feishu:
  app_id: "cli_xxxxxxxx"           # 飞书应用 ID
  app_secret: "your_secret"        # 飞书应用密钥
  table_id: "tblxxxxxxxx"          # 多维表格 ID
  chat_id: "oc_xxxxxxxx"           # 群聊 ID（可选）
```

### 输出配置

```yaml
output:
  format: "table"                  # 输出格式: table, json, markdown
  max_title_length: 100           # 标题最大长度
  max_summary_length: 200         # 摘要最大长度
  max_authors: 3                  # 显示作者数量
```

## 命令行工具

### 搜索论文

```bash
autopaper search [OPTIONS]

选项:
  --query TEXT              搜索关键词
  --categories TEXT         论文类别 (可多次使用)
  --max-results INTEGER     最大结果数
  --date-from DATE         开始日期 (YYYY-MM-DD)
  --date-to DATE           结束日期 (YYYY-MM-DD)
  --output FORMAT          输出格式 (table/json/markdown)
```

### 同步到飞书

```bash
autopaper sync [OPTIONS]

选项:
  --config PATH            配置文件路径
  --query TEXT             搜索关键词
  --dry-run               仅预览，不实际同步
  --notify                发送通知到群聊
```

### 配置管理

```bash
autopaper config [OPTIONS]

选项:
  --init                  创建示例配置文件
  --validate              验证配置文件
  --show                  显示当前配置
```

## API 文档

### ArxivProcessor

处理 arXiv 论文搜索和获取。

```python
processor = ArxivProcessor(max_results=100)
papers = processor.search_papers(
    query="deep learning",
    categories=["cs.AI"],
    date_from=date(2023, 1, 1)
)
```

### FeishuConnector

处理与飞书 API 的交互。

```python
connector = FeishuConnector(app_id="xxx", app_secret="xxx")
connector.add_records(table_id="xxx", records=[...])
connector.send_message(chat_id="xxx", message="论文同步完成")
```

### PaperFormatter

格式化论文信息。

```python
formatter = PaperFormatter(template_style="detailed")
formatted_text = formatter.format_paper_list(papers)
feishu_record = formatter.format_for_feishu(paper)
```

## 开发指南

### 环境设置

```bash
git clone https://github.com/yourusername/autopaper.git
cd autopaper
pip install -e ".[dev]"
pre-commit install
```

### 运行测试

```bash
pytest
pytest --cov=autopaper
```

### 代码格式化

```bash
black autopaper/
flake8 autopaper/
mypy autopaper/
```

## 贡献

欢迎贡献代码！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建 Pull Request

## 许可证

本项目使用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 更新日志

### v0.1.0 (2024-01-01)

- 初始版本发布
- 支持 arXiv 论文搜索
- 支持飞书表格同步
- 提供命令行工具

## 支持

- 📖 [文档](https://autopaper.readthedocs.io)
- 🐛 [问题报告](https://github.com/yourusername/autopaper/issues)
- 💬 [讨论](https://github.com/yourusername/autopaper/discussions)

## 致谢

感谢以下开源项目：

- [arXiv API](https://arxiv.org/help/api)
- [飞书开放平台](https://open.feishu.cn/)
- [Requests](https://requests.readthedocs.io/)
- [Click](https://click.palletsprojects.com/)
- [Rich](https://rich.readthedocs.io/)
