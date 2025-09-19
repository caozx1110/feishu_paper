#!/bin/bash
#
# 简化版定时同步脚本
#
# 直接运行 python arxiv_hydra.py --config-name=all
# 适用于 Docker 容器和 cron 定时任务
#
# 使用方法:
#     bash scripts/simple_sync.sh
#     
# 环境变量:
#     SYNC_INTERVAL: 同步间隔（秒），默认86400（1天）
#     LOG_LEVEL: 日志级别，默认INFO
#

# 设置工作目录
cd "$(dirname "$0")/.." || exit 1

# 设置默认值
SYNC_INTERVAL=${SYNC_INTERVAL:-86400}  # 默认1天
LOG_LEVEL=${LOG_LEVEL:-INFO}

# 记录开始时间
echo "🕒 $(date '+%Y-%m-%d %H:%M:%S') - 开始定时同步..."
echo "📅 同步间隔: ${SYNC_INTERVAL} 秒"

# 执行同步
python arxiv_hydra.py --config-name=all

# 记录结果
if [ $? -eq 0 ]; then
    echo "✅ $(date '+%Y-%m-%d %H:%M:%S') - 同步完成"
else
    echo "❌ $(date '+%Y-%m-%d %H:%M:%S') - 同步失败"
fi
