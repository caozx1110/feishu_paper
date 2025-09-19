# ArXiv 论文同步系统 Docker 使用指南

## 🚀 快速开始

### 1. 准备环境变量

```bash
# 复制环境变量模板
cp .env.template .env

# 编辑环境变量文件，填写飞书配置
nano .env
```

### 2. 使用 Docker Compose（推荐）

```bash
# 构建并启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 3. 使用 Docker 命令

```bash
# 构建镜像
docker build -t arxiv-paper-sync .

# 运行容器
docker run -d \
  --name arxiv-sync \
  --env-file .env \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/backup:/app/backup \
  -v $(pwd)/downloads:/app/downloads \
  arxiv-paper-sync

# 查看日志
docker logs -f arxiv-sync
```

## 📋 环境变量配置

### 必填配置

| 变量名 | 说明 | 示例 |
|--------|------|------|
| `FEISHU_APP_ID` | 飞书应用ID | `cli_xxxxxxxxx` |
| `FEISHU_APP_SECRET` | 飞书应用密钥 | `xxxxxxxxxxxxxxx` |
| `FEISHU_BITABLE_APP_TOKEN` | 飞书多维表格令牌 | `xxxxxxxxxxxxxxx` |

### 可选配置

| 变量名 | 说明 | 默认值 |
|--------|------|--------|
| `SYNC_INTERVAL` | 同步间隔（秒） | `86400` (1天) |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `TZ` | 时区 | `Asia/Shanghai` |
| `IMMEDIATE_RUN` | 启动时立即同步 | `true` |

## ⏰ 定时任务配置

### 默认调度

- 每天凌晨 2:00 执行同步

### 自定义调度

编辑 `docker/crontab` 文件：

```bash
# 每6小时执行一次
0 */6 * * * cd /app && python arxiv_hydra.py --config-name=all >> logs/cron.log 2>&1

# 每周一凌晨1点执行
0 1 * * 1 cd /app && python arxiv_hydra.py --config-name=all >> logs/cron.log 2>&1
```

## 🔍 监控和调试

### 查看日志

```bash
# 实时查看容器日志
docker logs -f arxiv-sync

# 查看同步日志文件
tail -f logs/scheduled_sync.log

# 查看 cron 日志
tail -f logs/cron.log
```

### 手动执行同步

```bash
# 进入容器
docker exec -it arxiv-sync bash

# 手动执行同步
python arxiv_hydra.py --config-name=all

# 使用定时脚本
python scripts/scheduled_sync.py --dry-run
```

### 健康检查

```bash
# 查看容器健康状态
docker ps

# 检查容器详细状态
docker inspect arxiv-sync
```

## 📁 数据持久化

### 目录映射

| 容器内路径 | 宿主机路径 | 说明 |
|-----------|-----------|------|
| `/app/logs` | `./logs` | 日志文件 |
| `/app/backup` | `./backup` | 配置备份 |
| `/app/downloads` | `./downloads` | PDF下载 |

### 备份数据

```bash
# 备份重要数据
tar -czf arxiv-sync-backup-$(date +%Y%m%d).tar.gz logs backup

# 恢复数据
tar -xzf arxiv-sync-backup-20231201.tar.gz
```

## 🔧 故障排除

### 常见问题

1. **容器启动失败**
   ```bash
   # 检查环境变量
   docker-compose config
   
   # 查看详细错误
   docker-compose logs
   ```

2. **同步失败**
   ```bash
   # 检查飞书配置
   docker exec arxiv-sync python -c "from sync_to_feishu import *; print('配置检查')"
   
   # 手动测试同步
   docker exec arxiv-sync python arxiv_hydra.py --config-name=sync_1_llm_robotics
   ```

3. **定时任务不执行**
   ```bash
   # 检查 cron 服务状态
   docker exec arxiv-sync service cron status
   
   # 查看 cron 日志
   docker exec arxiv-sync tail -f /var/log/cron.log
   ```

### 调试模式

```bash
# 使用调试模式启动
docker run -it --rm \
  --env-file .env \
  -e LOG_LEVEL=DEBUG \
  -e IMMEDIATE_RUN=true \
  -v $(pwd)/logs:/app/logs \
  arxiv-paper-sync
```

## 📈 性能优化

### 资源限制

```yaml
# docker-compose.yml 中添加
services:
  arxiv-sync:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
        reservations:
          memory: 512M
          cpus: '0.25'
```

### 网络优化

```yaml
# 使用自定义网络
networks:
  arxiv-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

## 🔄 更新和维护

### 更新镜像

```bash
# 拉取最新代码
git pull

# 重新构建镜像
docker-compose build --no-cache

# 重启服务
docker-compose up -d
```

### 清理资源

```bash
# 清理未使用的镜像
docker image prune

# 清理所有未使用的资源
docker system prune -a
```
