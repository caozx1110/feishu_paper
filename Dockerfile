# ArXiv 论文同步系统 Docker 镜像
FROM python:3.9-slim

LABEL maintainer="ArXiv Paper Sync System"
LABEL description="Automated ArXiv paper synchronization with Feishu integration"
LABEL version="1.0"

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV SYNC_INTERVAL=86400
ENV LOG_LEVEL=INFO
ENV TZ=Asia/Shanghai

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    git \
    cron \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

# 设置时区
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 复制 requirements 文件并安装 Python 依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 确保脚本有执行权限
RUN chmod +x scripts/*.sh scripts/*.py

# 创建必要的目录
RUN mkdir -p logs backup downloads

# 复制 cron 任务文件
COPY docker/crontab /etc/cron.d/arxiv-sync
RUN chmod 0644 /etc/cron.d/arxiv-sync
RUN crontab /etc/cron.d/arxiv-sync

# 创建启动脚本
RUN echo '#!/bin/bash\n\
    # 启动 cron 服务\n\
    service cron start\n\
    \n\
    # 输出当前 cron 任务\n\
    echo "📋 当前定时任务:"\n\
    crontab -l\n\
    \n\
    # 如果有 IMMEDIATE_RUN 环境变量，立即执行一次同步\n\
    if [ "$IMMEDIATE_RUN" = "true" ]; then\n\
    echo "🚀 立即执行一次同步..."\n\
    python arxiv_hydra.py --config-name=all\n\
    fi\n\
    \n\
    # 保持容器运行\n\
    echo "⏰ 定时同步系统已启动，按 Ctrl+C 停止"\n\
    echo "📅 同步间隔: ${SYNC_INTERVAL} 秒"\n\
    echo "📋 查看日志: docker logs <container_name>"\n\
    \n\
    # 持续输出日志\n\
    tail -f logs/scheduled_sync.log 2>/dev/null &\n\
    \n\
    # 等待信号\n\
    while true; do\n\
    sleep 30\n\
    done\n\
    ' > /app/docker-entrypoint.sh

RUN chmod +x /app/docker-entrypoint.sh

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python scripts/health_check.py || exit 1

# 暴露端口（健康检查不需要端口）
# EXPOSE 8080

# 设置启动命令
ENTRYPOINT ["/app/docker-entrypoint.sh"]
