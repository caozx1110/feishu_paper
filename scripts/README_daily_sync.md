# ArXiv论文定时采集系统

## 概述

这个系统提供了自动化的ArXiv论文采集功能，可以设置为每天上午10点（中国时间）自动运行，采集最新的研究论文并同步到飞书多维表格。

## 文件结构

```
scripts/
├── daily_arxiv_sync.sh        # 主要的执行脚本
├── setup_daily_sync.sh        # 定时任务管理脚本
├── crontab_daily_sync         # Crontab配置模板
└── README_daily_sync.md       # 本文档
```

## 快速开始

### 1. 安装定时任务

```bash
# 进入项目目录
cd /home/ubuntu/ws/feishu_paper

# 运行安装脚本
./scripts/setup_daily_sync.sh install
```

### 2. 查看状态

```bash
./scripts/setup_daily_sync.sh status
```

### 3. 测试执行

```bash
./scripts/setup_daily_sync.sh test
```

### 4. 查看日志

```bash
./scripts/setup_daily_sync.sh logs
```

### 5. 卸载定时任务

```bash
./scripts/setup_daily_sync.sh uninstall
```

## 详细说明

### 主要功能

- **自动论文采集**: 每天上午10:00自动运行 `python arxiv_hydra.py --config-name=all`
- **日志记录**: 详细记录每次执行的结果和错误信息
- **环境检查**: 自动检查Python环境和必要文件
- **错误处理**: 完善的错误处理和退出状态码
- **日志轮转**: 自动清理30天前的旧日志文件

### 脚本详解

#### 1. daily_arxiv_sync.sh

主要的执行脚本，负责：
- 设置正确的工作目录
- 激活Python虚拟环境（如果存在）
- 检查必要的文件和环境
- 执行论文采集命令
- 记录详细的执行日志
- 清理旧日志文件

#### 2. setup_daily_sync.sh

定时任务管理脚本，提供：
- `install`: 安装定时任务到系统crontab
- `uninstall`: 从系统crontab移除定时任务
- `status`: 查看当前定时任务状态和最近日志
- `test`: 测试执行脚本是否正常工作
- `logs`: 交互式查看历史日志文件

#### 3. crontab_daily_sync

Crontab配置模板，定义：
- 每天10:00执行的基本任务
- 可选的周度任务和健康检查任务
- 时区设置说明

## 时区配置

系统默认配置为中国标准时间(CST)，如果您的服务器时区不正确，请执行：

```bash
# 查看当前时区
timedatectl status

# 设置为中国标准时间
sudo timedatectl set-timezone Asia/Shanghai
```

## 日志系统

### 日志位置
- 日志目录: `logs/`
- 日志文件格式: `daily_sync_YYYYMMDD.log`
- 自动清理: 保留最近30天的日志

### 日志内容
- 执行开始和结束时间
- Python环境信息
- 命令执行过程
- 错误信息和退出状态码
- 论文采集结果统计

### 查看日志示例

```bash
# 查看最新日志
tail -f logs/daily_sync_$(date +%Y%m%d).log

# 查看所有日志文件
ls -la logs/

# 使用管理脚本交互式查看
./scripts/setup_daily_sync.sh logs
```

## 故障排除

### 常见问题

1. **权限错误**
   ```bash
   chmod +x scripts/daily_arxiv_sync.sh
   chmod +x scripts/setup_daily_sync.sh
   ```

2. **Python环境问题**
   - 确保Python3已安装
   - 确保必要的依赖包已安装
   - 检查虚拟环境路径

3. **配置文件缺失**
   - 确保 `conf/all.yaml` 存在
   - 确保飞书配置正确

4. **网络连接问题**
   - 检查ArXiv API访问
   - 检查飞书API连接

### 手动执行

如果定时任务出现问题，可以手动执行：

```bash
# 直接运行同步脚本
./scripts/daily_arxiv_sync.sh

# 或者直接运行论文采集命令
python arxiv_hydra.py --config-name=all
```

### 检查Crontab

```bash
# 查看当前用户的crontab
crontab -l

# 查看系统crontab
sudo cat /etc/crontab

# 查看cron服务状态
sudo systemctl status cron
```

## 高级配置

### 自定义执行时间

编辑 `scripts/crontab_daily_sync` 文件：

```bash
# 每天上午8:30执行
30 8 * * * /home/ubuntu/ws/feishu_paper/scripts/daily_arxiv_sync.sh

# 每天上午10:00和下午2:00执行
0 10,14 * * * /home/ubuntu/ws/feishu_paper/scripts/daily_arxiv_sync.sh

# 仅工作日执行
0 10 * * 1-5 /home/ubuntu/ws/feishu_paper/scripts/daily_arxiv_sync.sh
```

### 环境变量配置

在 `daily_arxiv_sync.sh` 中添加环境变量：

```bash
# 设置Python路径
export PYTHONPATH=/path/to/your/python

# 设置代理（如果需要）
export http_proxy=http://proxy.example.com:8080
export https_proxy=http://proxy.example.com:8080
```

### 通知集成

可以在脚本中添加通知功能：

```bash
# 邮件通知
echo "论文采集完成" | mail -s "ArXiv Daily Sync" user@example.com

# 企业微信通知
curl -X POST "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=YOUR_KEY" \
     -d '{"msgtype": "text", "text": {"content": "论文采集完成"}}'
```

## 监控和维护

### 性能监控

```bash
# 查看最近的执行时间
grep "开始每日定时同步\|定时同步成功完成" logs/daily_sync_*.log | tail -10

# 统计成功/失败次数
grep -c "定时同步成功完成" logs/daily_sync_*.log
grep -c "定时同步失败" logs/daily_sync_*.log
```

### 定期维护

建议定期执行以下维护任务：

1. 清理旧日志文件（自动执行）
2. 检查磁盘空间使用
3. 更新配置文件和关键词
4. 检查飞书API限制和配额

## 安全注意事项

1. **文件权限**: 确保脚本文件权限适当，避免未授权访问
2. **API密钥**: 保护飞书API密钥，不要提交到版本控制
3. **日志敏感信息**: 检查日志中是否包含敏感信息
4. **系统资源**: 监控系统资源使用，避免影响其他服务

## 支持和反馈

如果遇到问题或有改进建议，请：

1. 查看日志文件了解详细错误信息
2. 检查系统环境和配置
3. 参考故障排除部分
4. 提交问题报告时包含相关日志信息
