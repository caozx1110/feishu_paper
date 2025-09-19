# Tools 工具目录

这个目录包含了 ArXiv 论文同步系统的所有管理工具和实用脚本。

## 📁 目录结构

```
tools/
├── manager.py              # 🎯 统一管理工具（推荐使用）
├── simple_sync.py          # 简单同步脚本（Python）
├── sync_unix.sh           # Unix/Linux 同步脚本
├── sync_windows.bat       # Windows 同步脚本
├── setup_feishu.py        # 飞书环境设置
├── setup_wizard.py        # 交互式设置向导
└── setup_windows_task.py  # Windows 任务计划设置
```

## 🚀 主要工具

### 1. manager.py（推荐）
**统一管理工具**，整合了所有功能：

```bash
# 基本同步
python tools/manager.py sync

# 模拟运行
python tools/manager.py sync --dry-run

# 定时同步（7天周期）
python tools/manager.py schedule --days 7

# 健康检查
python tools/manager.py health

# 环境设置
python tools/manager.py setup

# Docker 管理
python tools/manager.py docker up
python tools/manager.py docker down
python tools/manager.py docker logs

# 数据备份
python tools/manager.py backup

# 环境清理
python tools/manager.py clean
python tools/manager.py clean --deep
```

### 2. 平台特定同步脚本

#### Windows
```batch
# 使用批处理脚本
tools\sync_windows.bat

# 或使用 Python
python tools/simple_sync.py
```

#### Linux/macOS
```bash
# 使用 shell 脚本
./tools/sync_unix.sh

# 或使用 Python
python tools/simple_sync.py
```

### 3. 环境设置工具

#### 自动设置
```bash
# 交互式向导（推荐新用户）
python tools/setup_wizard.py

# 飞书专用设置
python tools/setup_feishu.py
```

#### Windows 任务计划
```bash
# 设置自动定时任务
python tools/setup_windows_task.py
```

## 📋 使用场景

### 🎯 新用户入门
1. **环境设置**: `python tools/manager.py setup`
2. **配置向导**: `python tools/setup_wizard.py`
3. **健康检查**: `python tools/manager.py health`
4. **首次同步**: `python tools/manager.py sync --dry-run`

### 🔄 日常使用
- **手动同步**: `python tools/manager.py sync`
- **检查状态**: `python tools/manager.py health`
- **查看日志**: `python tools/manager.py docker logs`

### ⚙️ 高级用户
- **定时同步**: `python tools/manager.py schedule --days 3`
- **数据管理**: `python tools/manager.py backup`
- **环境维护**: `python tools/manager.py clean`

### 🐳 Docker 部署
```bash
# 启动服务
python tools/manager.py docker up

# 查看状态
python tools/manager.py docker ps

# 查看日志
python tools/manager.py docker logs

# 停止服务
python tools/manager.py docker down
```

## 🛠️ 工具特性

### manager.py 优势
- ✅ **统一入口**: 一个工具管理所有功能
- ✅ **智能检查**: 自动环境检查和错误诊断
- ✅ **日志记录**: 完整的操作日志和错误追踪
- ✅ **跨平台**: 支持 Windows、Linux、macOS
- ✅ **容错处理**: 优雅的错误处理和恢复机制

### 平台特定脚本
- 🎯 **针对性强**: 为特定平台优化
- 🚀 **启动快速**: 无需复杂依赖
- 🔧 **易于定制**: 简单的脚本结构

## 📝 最佳实践

### 1. 优先使用 manager.py
```bash
# ✅ 推荐：使用统一管理工具
python tools/manager.py sync

# ❌ 不推荐：直接调用底层脚本
python arxiv_hydra.py --config-name=all
```

### 2. 环境检查
```bash
# 定期健康检查
python tools/manager.py health

# 出现问题时重新设置
python tools/manager.py setup
```

### 3. 数据安全
```bash
# 重要操作前备份
python tools/manager.py backup

# 定期清理
python tools/manager.py clean
```

## 🔧 故障排除

### 常见问题

1. **依赖缺失**
   ```bash
   python tools/manager.py health
   ```

2. **配置错误**
   ```bash
   python tools/setup_wizard.py
   ```

3. **权限问题**
   ```bash
   # Windows: 以管理员身份运行
   python tools/setup_windows_task.py
   ```

4. **Docker 问题**
   ```bash
   python tools/manager.py docker ps
   python tools/manager.py docker logs
   ```

### 获取帮助
```bash
# 查看帮助
python tools/manager.py --help
python tools/manager.py sync --help
python tools/manager.py docker --help
```

## 📞 支持

如需技术支持，请：
1. 首先运行健康检查：`python tools/manager.py health`
2. 查看日志文件：`logs/manager.log`
3. 提供详细的错误信息和系统环境

---

💡 **提示**: 对于新用户，建议从 `python tools/manager.py setup` 开始，然后使用 `python tools/setup_wizard.py` 进行详细配置。
