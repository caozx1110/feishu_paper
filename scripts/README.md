# 📁 Scripts 目录说明

这个目录包含了所有用于定时同步的脚本和工具。

## 📋 脚本列表

### 🐍 Python 脚本

| 脚本名称 | 功能 | 推荐用途 |
|---------|------|----------|
| `scheduled_sync.py` | 完整功能定时同步脚本 | 本地开发和测试 |
| `simple_sync.py` | 简化版同步脚本 | 生产环境和容器 |
| `health_check.py` | 系统健康检查 | Docker 健康检查 |
| `setup_windows_task.py` | Windows 定时任务设置 | Windows 用户 |

### 🖥️ 系统脚本

| 脚本名称 | 功能 | 推荐用途 |
|---------|------|----------|
| `simple_sync.sh` | Bash 版简化同步脚本 | Linux/macOS 环境 |
| `start_sync.bat` | Windows 批处理启动脚本 | Windows 用户 |

## 🚀 使用方法

### 1. scheduled_sync.py - 完整功能脚本

**特性：**
- ✅ 配置文件备份和恢复
- ✅ 临时修改同步天数
- ✅ 详细日志记录
- ✅ 支持模拟运行

**基本用法：**
```bash
# 使用默认配置（1天周期）
python scripts/scheduled_sync.py

# 自定义周期
python scripts/scheduled_sync.py --days 7

# 模拟运行（不实际执行）
python scripts/scheduled_sync.py --dry-run

# 显示配置信息
python scripts/scheduled_sync.py --config

# 调试模式
python scripts/scheduled_sync.py --log-level DEBUG
```

**高级选项：**
```bash
# 禁用配置备份
python scripts/scheduled_sync.py --no-backup

# 组合使用
python scripts/scheduled_sync.py --days 3 --dry-run --log-level DEBUG
```

### 2. simple_sync.py - 简化版脚本

**特性：**
- ✅ 直接调用主程序
- ✅ 轻量级，启动快
- ✅ 适合容器环境

**使用方法：**
```bash
# 直接执行
python scripts/simple_sync.py

# 设置环境变量
export SYNC_INTERVAL=86400
export LOG_LEVEL=INFO
python scripts/simple_sync.py
```

### 3. health_check.py - 健康检查

**功能：**
- ✅ 检查 Python 环境
- ✅ 验证配置文件
- ✅ 检查环境变量
- ✅ 验证 Cron 服务

**使用方法：**
```bash
# 执行健康检查
python scripts/health_check.py

# 用于 Docker 健康检查
HEALTHCHECK CMD python scripts/health_check.py
```

### 4. setup_windows_task.py - Windows 定时任务

**功能：**
- ✅ 自动创建 Windows 定时任务
- ✅ 交互式配置
- ✅ 生成 XML 配置文件

**使用方法：**
```bash
# 运行设置向导
python scripts/setup_windows_task.py

# 按提示输入：
# - 任务名称（默认：ArXivPaperSync）
# - 执行时间（默认：02:00）
```

### 5. start_sync.bat - Windows 批处理

**功能：**
- ✅ Windows 双击启动
- ✅ 自动检查环境
- ✅ 简单易用

**使用方法：**
```cmd
# 双击运行
start_sync.bat

# 或命令行运行
cd scripts
start_sync.bat
```

### 6. simple_sync.sh - Bash 脚本

**功能：**
- ✅ Linux/macOS 支持
- ✅ 环境变量配置
- ✅ 适合 cron 任务

**使用方法：**
```bash
# 直接执行
bash scripts/simple_sync.sh

# 添加到 cron
crontab -e
# 添加: 0 2 * * * cd /path/to/project && bash scripts/simple_sync.sh
```

## ⚙️ 环境变量配置

所有脚本都支持以下环境变量：

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `SYNC_DAYS` | 默认同步天数 | `1` |
| `SYNC_INTERVAL` | 同步间隔（秒） | `86400` |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `BACKUP_CONFIGS` | 是否备份配置 | `true` |

## 🐳 Docker 集成

在 Docker 环境中，推荐使用 `simple_sync.py`：

```dockerfile
# Dockerfile 中
COPY scripts/ /app/scripts/
RUN chmod +x /app/scripts/*.py

# 健康检查
HEALTHCHECK CMD python scripts/health_check.py

# 定时任务
RUN echo "0 2 * * * cd /app && python scripts/simple_sync.py" | crontab -
```

## 📊 日志管理

### 日志文件位置

| 脚本 | 日志文件 |
|------|----------|
| `scheduled_sync.py` | `logs/scheduled_sync.log` |
| `simple_sync.py` | 控制台输出 |
| Cron 任务 | `logs/cron.log` |

### 查看日志

```bash
# 实时查看定时脚本日志
tail -f logs/scheduled_sync.log

# 查看 cron 日志
tail -f logs/cron.log

# 查看所有日志
ls -la logs/
```

## 🔧 故障排除

### 常见问题

1. **Permission denied (权限错误)**
   ```bash
   chmod +x scripts/*.py scripts/*.sh
   ```

2. **找不到 Python**
   ```bash
   which python
   # 或者
   which python3
   ```

3. **配置文件不存在**
   ```bash
   cp .env.template .env
   # 编辑 .env 文件
   ```

4. **定时任务不执行**
   ```bash
   # 检查 cron 服务
   systemctl status cron  # Linux
   # 或查看 Windows 任务计划程序
   ```

### 调试模式

```bash
# 使用调试模式运行
python scripts/scheduled_sync.py --log-level DEBUG --dry-run

# 检查配置
python scripts/scheduled_sync.py --config

# 健康检查
python scripts/health_check.py
```

## 📋 最佳实践

### 1. 选择合适的脚本

- **开发测试**: 使用 `scheduled_sync.py` + `--dry-run`
- **生产环境**: 使用 `simple_sync.py`
- **Docker 部署**: 使用 `simple_sync.py` + 健康检查
- **Windows 用户**: 使用 `setup_windows_task.py` 设置定时任务

### 2. 定时任务建议

- **日常同步**: 每天凌晨 2:00
- **频繁更新**: 每 6 小时一次
- **周报模式**: 每周一凌晨执行

### 3. 监控和维护

- 定期检查日志文件
- 监控磁盘空间使用
- 备份重要配置文件
- 定期更新依赖包

## 🔗 相关链接

- [主项目 README](../README.md)
- [定时同步详细指南](../SCHEDULED_SYNC_README.md)
- [Docker 部署指南](../docker/README.md)
- [配置文件说明](../conf/README.md)
