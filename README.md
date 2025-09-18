# ArXiv 论文采集工具

> 基于官方arxiv库的智能论文采集工具，支持通配符匹配、正则表达式搜索和PDF自动下载

## 🚀 新功能特性

### 1. 官方ArXiv库支持
- 使用官方 `arxiv` 库进行API请求
- 更稳定的请求处理和错误重试
- 支持直接在搜索时添加时间、领域条件

### 2. 通配符和正则表达式匹配
- **通配符**: 使用 `*` 匹配所有文章
- **正则表达式**: 使用 `regex:pattern` 进行精确模式匹配
- **智能过滤**: 结合排除关键词精确控制结果

### 3. PDF自动下载功能
- 增量式下载：避免重复下载已存在文件
- 自动生成元数据：每个PDF配备详细的Markdown元数据
- 批量下载控制：可配置最大下载数量
- 自动创建索引：生成 `README.md` 索引文件

### 4. Markdown格式输出
- 支持Markdown格式的论文报告
- 表格化显示论文信息
- 包含评分详情和链接

## � 安装依赖

```bash
pip install arxiv hydra-core omegaconf pyyaml
```

## 🎯 使用示例

### 基础使用 - 查看所有cs.RO论文
```bash
python arxiv_hydra.py keywords=cs_ro_wildcard search.field=robotics
```

### 启用PDF下载
```bash
python arxiv_hydra.py keywords=cs_ro_wildcard search.field=robotics download.enabled=true download.max_downloads=5
```

### 使用正则表达式匹配
```bash
python arxiv_hydra.py keywords=regex_test search.field=robotics
```

### 输出Markdown格式报告
```bash
python arxiv_hydra.py keywords=default output.format=markdown
```

## ⚙️ 配置选项

### PDF下载配置
```yaml
download:
  enabled: false          # 是否启用PDF下载
  max_downloads: 10       # 最大下载数量
  download_dir: "downloads" # 下载目录
  create_metadata: true   # 是否创建元数据文件
  create_index: true      # 是否创建索引文件
  force_download: false   # 是否强制重新下载
```

### 输出配置
```yaml
output:
  save: true
  format: "markdown"      # 输出格式: markdown, txt
  include_scores: true
```

## 📁 文件结构

```
├── conf/                    # 配置文件目录
│   ├── config.yaml         # 主配置文件
│   └── keywords/           # 关键词配置
│       ├── cs_ro_wildcard.yaml  # 通配符配置示例
│       └── regex_test.yaml      # 正则表达式配置示例
├── downloads/              # PDF下载目录
│   ├── README.md          # 下载索引文件
│   ├── *.pdf              # 下载的PDF文件
│   └── *.md               # 论文元数据文件
├── outputs/                # 输出报告目录
└── arxiv_hydra.py         # 主程序
```

## 🔧 配置示例

### 通配符配置 (cs_ro_wildcard.yaml)
```yaml
interest_keywords:
  - "*"  # 匹配所有文章
exclude_keywords:
  - "pure mathematics"
  - "theoretical physics"
description: "cs.RO 领域全覆盖配置"
```

### 正则表达式配置 (regex_test.yaml)
```yaml
interest_keywords:
  - "regex:robot.*learning"           # 机器人学习
  - "regex:(SLAM|localization)"       # SLAM或定位
  - "regex:(autonomous|mobile).*robot" # 自主或移动机器人
exclude_keywords:
  - "survey"
  - "review"
description: "正则表达式匹配测试"
```

## � 输出格式

### Markdown报告包含
- � 基本统计信息
- 📚 论文列表（表格格式）
- 🔗 直接链接到ArXiv和PDF
- 📊 评分详情（如果启用）
- 📄 完整摘要

### PDF下载功能
- 自动下载匹配的论文PDF
- 生成对应的Markdown元数据文件
- 创建包含所有下载论文的索引文件
- 支持断点续传（跳过已存在文件）

## ⚡ 性能优化

1. **通配符使用时**：建议关闭智能匹配 `intelligent_matching.enabled=false`
2. **大量下载时**：合理设置 `download.max_downloads` 避免请求过频
3. **网络限制**：arxiv库自动处理请求间隔和重试

## 🎉 最新更新

- ✅ 替换为官方arxiv库
- ✅ 增加PDF自动下载功能
- ✅ 支持Markdown格式输出
- ✅ 通配符和正则表达式匹配
- ✅ 自动生成论文索引和元数据

现在可以更高效地收集和管理ArXiv论文！🚀
