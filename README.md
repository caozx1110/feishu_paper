# 飞书论文同步系统

> 基于Hydra配置管理的arXiv论文采集与飞书同步工具，支持多维表格集成、定时批量同步和Docker部署

## 🚀 主要功能

### 1. 飞书多维表格集成
- 🔗 **自动同步**: 将arXiv论文自动同步到飞书多维表格
- 📊 **结构化存储**: 论文信息按字段分类存储，便于管理和搜索
- 🔄 **双模式支持**: 同时支持Wiki文档和Bitable多维表格模式
- 🛠️ **自动初始化**: 一键创建所需的表格结构

### 2. 定时批量同步
- ⏰ **定时执行**: 支持定时自动同步所有研究领域
- 🔄 **批量处理**: 一次性处理多个sync配置文件
- 📊 **统一通知**: 汇总所有更新信息发送到群聊
- 🐳 **Docker支持**: 完整的容器化部署方案

### 3. 安全的配置管理
- ⚡ **Hydra集成**: 基于Hydra的现代化配置管理
- 🔐 **环境变量**: 敏感信息通过环境变量安全管理
- 📝 **配置模板**: 提供完整的配置示例和文档
- 🎯 **零硬编码**: 所有配置项都可通过环境变量覆盖

### 4. 智能论文处理
- 🤖 **官方API**: 使用官方 `arxiv` 库和 `lark-oapi` SDK
- 🔍 **灵活搜索**: 支持关键词、分类、时间范围等多维度搜索
- 📄 **完整信息**: 提取标题、作者、摘要、链接等完整论文信息
- 🏷️ **智能分类**: 支持研究领域分类和标签管理

### 5. 现代化工具集成
- 📊 **多维表格**: 利用飞书强大的表格功能进行数据管理
- 🔄 **批量操作**: 支持批量添加、更新论文记录
- 📱 **移动友好**: 通过飞书移动端随时查看和管理论文
- 🎨 **美观界面**: 飞书原生界面，无需额外UI开发

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

主要依赖：
- `arxiv`: 官方arXiv API库
- `hydra-core`: 配置管理框架
- `lark-oapi`: 飞书开放平台SDK
- `python-dotenv`: 环境变量管理

## 🎯 快速开始

### 方法一：使用统一管理工具（推荐）

```bash
# 1. 环境设置
python tools/manager.py setup

# 2. 配置向导（首次使用）
python tools/setup_wizard.py

# 3. 健康检查
python tools/manager.py health

# 4. 开始同步
python tools/manager.py sync
```

### 方法二：Docker 部署（生产环境推荐）

```bash
# 1. 设置环境变量
python tools/manager.py setup

# 2. 启动 Docker 服务
python tools/manager.py docker up

# 3. 查看运行状态
python tools/manager.py docker ps

# 4. 查看日志
python tools/manager.py docker logs
```

### 方法三：手动配置

如果需要手动配置，请参考 [tools/README.md](tools/README.md) 获取详细的工具使用说明。

## 📚 文档指南

- **新用户**: [tools/README.md](tools/README.md) - 工具使用完整指南
- **定时同步**: [SCHEDULED_SYNC_README.md](SCHEDULED_SYNC_README.md) - 定时同步详细说明
- **Docker 部署**: [docker/README.md](docker/README.md) - 容器化部署指南

## 🚀 传统使用方法

### 1. 设置环境变量

复制环境变量模板：
```bash
cp .env.template .env
```

编辑 `.env` 文件，填入你的飞书配置信息：

```bash
# 飞书应用配置（从飞书开放平台获取）
FEISHU_APP_ID=cli_xxxxxxxxxx
FEISHU_APP_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
FEISHU_USER_ACCESS_TOKEN=u-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx

# 多维表格配置
FEISHU_BITABLE_APP_TOKEN=bascnxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 2. 初始化飞书表格

运行初始化脚本自动创建所需的多维表格：

```bash
python setup_feishu.py
```

这会自动创建：
- 📋 **论文主表**: 存储论文基本信息（标题、作者、摘要等）
- 🔗 **领域关系表**: 管理论文分类和研究领域关系

脚本会输出表格ID，请将它们添加到 `.env` 文件中。

### 3. 运行同步程序

```bash
python arxiv_hydra.py search.field=robotics
```

## 🎯 使用示例

### 基础搜索与同步
```bash
python arxiv_hydra.py keywords=cs_ro_wildcard search.field=robotics
```

### 指定研究领域
```bash
python arxiv_hydra.py search.field=machine_learning
```

### 自定义关键词
```bash
python arxiv_hydra.py keywords=custom_keywords
```

### 启用调试模式
```bash
python arxiv_hydra.py --debug search.field=robotics
```

## ⚙️ 配置管理

### 环境变量配置

所有敏感信息都通过环境变量安全管理：

| 变量名 | 说明 | 必需 | 示例 |
|--------|------|------|------|
| `FEISHU_APP_ID` | 飞书应用ID | ✅ | `cli_xxxxxxxxxx` |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | ✅ | `xxxxxxxxxxxxxxxx` |
| `FEISHU_USER_ACCESS_TOKEN` | 用户访问令牌 | 🔀 | `u-xxxxxxxxxxxxxxx` |
| `FEISHU_TENANT_ACCESS_TOKEN` | 应用访问令牌 | 🔀 | `t-xxxxxxxxxxxxxxx` |
| `FEISHU_BITABLE_APP_TOKEN` | 多维表格app token | ✅ | `bascnxxxxxxxxxxxxxxx` |
| `FEISHU_PAPERS_TABLE_ID` | 论文主表ID | ✅ | `tblxxxxxxxxxxxxxxx` |
| `FEISHU_RELATIONS_TABLE_ID` | 关系表ID | ✅ | `tblxxxxxxxxxxxxxxx` |

**注意**: `FEISHU_USER_ACCESS_TOKEN` 和 `FEISHU_TENANT_ACCESS_TOKEN` 二选一即可。

### Hydra配置

主配置文件位于 `conf/default.yaml`，支持环境变量替换：

```yaml
feishu:
  api:
    app_id: ${oc.env:FEISHU_APP_ID,""}
    app_secret: ${oc.env:FEISHU_APP_SECRET,""}
    # 访问令牌配置（二选一）
    user_access_token: ${oc.env:FEISHU_USER_ACCESS_TOKEN,""}
    tenant_access_token: ${oc.env:FEISHU_TENANT_ACCESS_TOKEN,""}
  
  bitable:
    app_token: ${oc.env:FEISHU_BITABLE_APP_TOKEN,""}
    papers_table_id: ${oc.env:FEISHU_PAPERS_TABLE_ID,""}
    relations_table_id: ${oc.env:FEISHU_RELATIONS_TABLE_ID,""}
  
  wiki:
    space_token: ${oc.env:FEISHU_WIKI_SPACE_TOKEN,""}
    papers_node_token: ${oc.env:FEISHU_PAPERS_NODE_TOKEN,""}
    relations_node_token: ${oc.env:FEISHU_RELATIONS_NODE_TOKEN,""}
```

### 搜索配置

```yaml
search:
  max_results: 50
  sort_by: "submittedDate"
  sort_order: "descending"
  categories:
    - "cs.RO"    # 机器人学
    - "cs.AI"    # 人工智能
    - "cs.LG"    # 机器学习
    - "cs.CV"    # 计算机视觉
```

## 📁 项目结构

```
feishu_paper/
├── conf/                           # Hydra配置文件目录
│   ├── default.yaml               # 主配置文件
│   └── keywords/                  # 关键词配置
│       ├── cs_ro_wildcard.yaml   # 机器人学关键词
│       └── machine_learning.yaml  # 机器学习关键词
├── feishu_bitable_connector.py    # 多维表格API连接器
├── feishu_wiki_connector.py       # Wiki API连接器  
├── setup_feishu.py               # 初始化脚本
├── get_token.py                  # 访问令牌获取工具
├── arxiv_hydra.py                # 主程序
├── requirements.txt              # Python依赖
├── .env.example                  # 环境变量模板
└── README.md                     # 本文件
```

## 🔧 飞书配置获取

### 1. 创建飞书应用

1. 访问 [飞书开放平台](https://open.feishu.cn/)
2. 创建新应用，获取 `APP_ID` 和 `APP_SECRET`
3. 配置应用权限：
   - `bitable:app` (多维表格应用权限)
   - `wiki:readonly` (知识库读取权限，可选)

### 2. 获取访问令牌

飞书API支持两种访问令牌，**任选其一**即可：

#### 方式一：应用访问令牌 (推荐)

应用访问令牌适用于自动化操作，无需用户登录：

```bash
# 使用工具脚本自动获取
python get_token.py
```

该脚本会：
- 使用你的应用凭证自动获取`tenant_access_token`
- 询问是否保存到`.env`文件
- 显示token有效期信息

#### 方式二：用户访问令牌

用户访问令牌需要用户授权，适用于用户相关操作：
- 通过OAuth2.0流程获取用户授权
- 在飞书开发者后台获取临时测试token

#### 令牌对比

| 类型 | 前缀 | 获取方式 | 适用场景 | 推荐度 |
|------|------|----------|----------|--------|
| `tenant_access_token` | `t-` | 应用凭证自动获取 | 自动化、定时任务 | ⭐⭐⭐ |
| `user_access_token` | `u-` | 用户授权获取 | 用户操作、个人数据 | ⭐⭐ |

### 3. 创建多维表格

1. 在飞书中创建新的多维表格
2. 从URL中获取 `app_token`：
   ```
   https://xxx.feishu.cn/base/[app_token]
   ```
3. 运行 `setup_feishu.py` 自动创建表格结构

## 🚀 API功能详解

### 多维表格 (Bitable) API

使用 `FeishuBitableConnector` 类进行多维表格操作：

```python
from feishu_bitable_connector import FeishuBitableConnector

# 初始化连接器
connector = FeishuBitableConnector()

# 创建论文表
result = connector.create_papers_table()
if result['success']:
    print(f"表格创建成功，Table ID: {result['table_id']}")

# 添加论文记录
paper_data = {
    "title": "Attention Is All You Need",
    "authors": "Vaswani et al.",
    "abstract": "The dominant sequence transduction models...",
    "arxiv_id": "1706.03762",
    "pdf_url": "https://arxiv.org/pdf/1706.03762.pdf",
    "primary_category": "cs.CL",
    "published": "2017-06-12T00:00:00Z"
}
connector.add_paper_record(paper_data)

# 批量添加多篇论文
papers_list = [paper_data1, paper_data2, ...]
connector.batch_add_papers(papers_list)
```

### 支持的字段类型

| 字段类型 | 类型ID | 说明 | 示例 |
|----------|--------|------|------|
| 单行文本 | 1 | 标题、作者等 | "论文标题" |
| 数字 | 2 | 评分、引用数 | 95 |
| 日期 | 5 | 发布时间 | "2023-01-15" |
| 超链接 | 15 | arXiv、PDF链接 | "https://arxiv.org/abs/2301.12345" |
| 多行文本 | 17 | 摘要、备注 | "详细的论文摘要..." |

### 表格结构设计

#### 论文主表字段
- **标题** (单行文本): 论文完整标题
- **作者** (单行文本): 论文作者列表
- **arXiv ID** (单行文本): 唯一标识符
- **分类** (单行文本): 主要研究分类
- **发布时间** (日期): 论文发布日期
- **arXiv链接** (超链接): 论文页面链接
- **PDF链接** (超链接): PDF下载链接
- **摘要** (多行文本): 论文摘要内容

#### 领域关系表字段
- **论文ID** (单行文本): 关联论文主表
- **研究领域** (单行文本): 具体研究方向
- **权重** (数字): 相关性权重
- **备注** (多行文本): 额外说明

## 🔍 故障排除

### 常见问题及解决方案

#### 1. 认证相关问题

**问题**: `401 Unauthorized` 或认证失败
```
解决方案:
- 检查 FEISHU_USER_ACCESS_TOKEN 是否正确
- 确认token未过期（用户访问令牌有效期通常较短）
- 验证应用权限是否包含 bitable:app
```

**问题**: `403 Forbidden` 权限不足
```
解决方案:
- 确认用户对目标多维表格有编辑权限
- 检查应用是否被用户授权
- 验证 app_token 是否正确
```

#### 2. 表格操作问题

**问题**: 表格创建失败
```
解决方案:
- 检查 FEISHU_BITABLE_APP_TOKEN 是否正确
- 确认用户有创建表格的权限
- 验证字段类型定义是否正确
```

**问题**: 字段类型错误
```
解决方案:
- 参考支持的字段类型表格
- 检查字段定义中的 type 值
- 确认字段属性设置正确
```

#### 3. 环境配置问题

**问题**: 环境变量未加载
```bash
# 检查 .env 文件是否存在
ls -la .env

# 手动设置环境变量（临时方案）
$env:FEISHU_APP_ID="你的APP_ID"
$env:FEISHU_APP_SECRET="你的APP_SECRET"
```

**问题**: 依赖包安装失败
```bash
# 升级pip
python -m pip install --upgrade pip

# 重新安装依赖
pip install -r requirements.txt --force-reinstall
```

### 调试模式

启用详细日志输出：
```bash
# 设置调试环境变量
$env:FEISHU_DEBUG="true"

# 运行程序查看详细日志
python arxiv_hydra.py --debug
```

### API请求限制

飞书API有请求频率限制，建议：
- 批量操作时使用 `batch_add_papers()` 方法
- 避免短时间内大量单个请求
- 在请求失败时实现适当的重试机制

### 获取帮助

1. **查看初始化脚本帮助**:
   ```bash
   python setup_feishu.py --help
   ```

2. **检查配置是否正确**:
   ```bash
   python -c "
   from dotenv import load_dotenv
   import os
   load_dotenv()
   print('APP_ID:', os.getenv('FEISHU_APP_ID', 'Not set'))
   print('TOKEN:', 'Set' if os.getenv('FEISHU_USER_ACCESS_TOKEN') else 'Not set')
   "
   ```

3. **测试API连接**:
   ```bash
   python -c "
   from feishu_bitable_connector import FeishuBitableConnector
   connector = FeishuBitableConnector()
   print('连接器初始化成功')
   "
   ```

## 🎉 更新历史

### 更新历史

### v2.1.0 (当前版本)
- ✅ **双令牌支持**: 同时支持user_access_token和tenant_access_token
- ✅ **自动化工具**: 新增get_token.py自动获取应用访问令牌
- ✅ **智能认证**: 自动选择最佳令牌类型，支持token自动刷新
- ✅ **配置优化**: 简化环境变量配置，提供更好的错误提示

### v2.0.0
- ✅ **重大重构**: 全面迁移到飞书多维表格集成
- ✅ **安全增强**: 采用环境变量管理敏感配置
- ✅ **现代化配置**: 基于Hydra的配置管理系统
- ✅ **API升级**: 使用官方lark-oapi SDK
- ✅ **自动化工具**: 提供一键初始化脚本
- ✅ **完整文档**: 详细的使用指南和故障排除

### v1.x (传统版本)
- ❌ **已废弃**: JSON配置文件管理
- ❌ **已移除**: 本地PDF下载功能
- ❌ **已替换**: 手动配置流程

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个项目！

### 开发环境设置
```bash
# 克隆项目
git clone [repository-url]
cd feishu_paper

# 安装开发依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt  # 如果存在

# 设置pre-commit hooks
pre-commit install
```

### 提交规范
- 使用清晰的commit message
- 确保代码通过所有测试
- 更新相关文档

### 报告问题
创建Issue时请包含：
- 错误详细描述
- 重现步骤
- 环境信息（Python版本、依赖版本等）
- 相关日志输出

## 📄 许可证

MIT License - 详见 LICENSE 文件

---

🚀 **现在就开始使用飞书论文同步系统，让论文管理变得更加高效！**
