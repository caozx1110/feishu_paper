# Architecture

AutoPaper 的主路径由四层组成：

1. `configuration`

负责读取 `default.yaml` 和用户配置，提供类型化运行时设置。网络代理、healthcheck URL、arXiv 客户端参数、Feishu 环境变量策略都从这里取得。

2. `core`

负责论文搜索与排序。`create_arxiv_api(cfg)` 从配置创建 `ArxivAPI`，`SearchService` 只关心搜索配置，不依赖 CLI 或飞书。

3. `sync`

负责单配置和批量同步：加载配置、执行搜索、排序、同步飞书、发送汇总通知。

4. `cli`

只做参数解析和命令分发。所有默认行为都来自配置文件。

兼容层：

- `autopaper.arxiv_core` 保留公共类 `ArxivAPI` 和 `PaperRanker`。
- `autopaper.arxiv_hydra` 保留旧 Hydra 入口。

## Configuration First

可变化的行为应放在 YAML 中：

- API 超时和重试：`arxiv.request_timeout`、`arxiv.page_sizes`。
- arXiv 分类映射：`arxiv.field_categories`。
- smoke test：`arxiv.smoke_test`。
- 代理：`runtime.network.proxy`。
- Feishu 环境变量要求：`runtime.env.feishu`。

新增功能时，优先扩展默认配置，再在代码中读取配置。
