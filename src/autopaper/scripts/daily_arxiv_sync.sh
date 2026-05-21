#!/usr/bin/env bash
#
# Daily AutoPaper sync helper.
#
# This script is intended to be copied into a project directory with:
#   autopaper init --with-scripts
#
# Environment overrides:
#   AUTOPAPER_PROJECT_DIR=/path/to/project
#   AUTOPAPER_CONFIG_DIR=/path/to/project/conf
#   SYNC_TIMEOUT_SECONDS=7200
#   ARXIV_REQUEST_TIMEOUT=5,30

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${AUTOPAPER_PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
CONFIG_DIR="${AUTOPAPER_CONFIG_DIR:-$PROJECT_DIR/conf}"
LOG_DIR="${AUTOPAPER_LOG_DIR:-$PROJECT_DIR/logs}"
LOG_FILE="$LOG_DIR/daily_sync_$(date +%Y%m%d).log"

mkdir -p "$LOG_DIR"

LOCK_FILE="$LOG_DIR/daily_sync.lock"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    {
        echo "==========================================="
        echo "⚠️  $(date '+%Y-%m-%d %H:%M:%S %Z') - 已有同步任务在运行，本次跳过"
        echo "==========================================="
    } >> "$LOG_FILE"
    exit 0
fi

SYNC_TIMEOUT_SECONDS="${SYNC_TIMEOUT_SECONDS:-7200}"

{
    echo "==========================================="
    echo "🕒 $(date '+%Y-%m-%d %H:%M:%S %Z') - 开始每日 AutoPaper 同步"
    echo "📂 项目目录: $PROJECT_DIR"
    echo "📄 配置目录: $CONFIG_DIR"
    echo "⏱️  总超时: ${SYNC_TIMEOUT_SECONDS} 秒"
    echo "==========================================="
} >> "$LOG_FILE"

cd "$PROJECT_DIR" || {
    echo "❌ 无法切换到项目目录: $PROJECT_DIR" >> "$LOG_FILE"
    exit 1
}

if [ -f "/opt/miniconda3/etc/profile.d/conda.sh" ]; then
    echo "🐍 初始化conda环境..." >> "$LOG_FILE"
    source /opt/miniconda3/etc/profile.d/conda.sh
    conda activate base
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    echo "🐍 初始化conda环境..." >> "$LOG_FILE"
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
    conda activate base
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    echo "🐍 初始化conda环境..." >> "$LOG_FILE"
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
    conda activate base
fi

if [ -f "venv/bin/activate" ]; then
    echo "🐍 激活Python虚拟环境..." >> "$LOG_FILE"
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo "🐍 激活Python虚拟环境..." >> "$LOG_FILE"
    source .venv/bin/activate
fi

if ! command -v python3 >/dev/null 2>&1; then
    echo "❌ Python3 未找到" >> "$LOG_FILE"
    exit 1
fi

if ! python3 -m autopaper --version >> "$LOG_FILE" 2>&1; then
    echo "❌ autopaper 包不可用，请先运行: pip install -e /path/to/autopaper" >> "$LOG_FILE"
    exit 1
fi

echo "🌐 检查AutoPaper运行环境..." >> "$LOG_FILE"
HEALTH_CMD=(python3 -m autopaper health)
if [ -f "$CONFIG_DIR/default.yaml" ]; then
    HEALTH_CMD+=(--config-dir "$CONFIG_DIR")
fi
if ! "${HEALTH_CMD[@]}" >> "$LOG_FILE" 2>&1; then
    echo "❌ AutoPaper健康检查失败，跳过本次同步" >> "$LOG_FILE"
    exit 1
fi

SYNC_CMD=(python3 -m autopaper sync --config all)
if [ -f "$CONFIG_DIR/all.yaml" ]; then
    SYNC_CMD+=(--config-dir "$CONFIG_DIR")
fi

echo "🚀 开始执行论文采集..." >> "$LOG_FILE"
echo "📝 命令: ${SYNC_CMD[*]}" >> "$LOG_FILE"

timeout --kill-after=60s "$SYNC_TIMEOUT_SECONDS" "${SYNC_CMD[@]}" >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

{
    echo "==========================================="
    if [ $EXIT_CODE -eq 0 ]; then
        echo "✅ $(date '+%Y-%m-%d %H:%M:%S %Z') - 定时同步成功完成"
    elif [ $EXIT_CODE -eq 124 ]; then
        echo "⏱️  $(date '+%Y-%m-%d %H:%M:%S %Z') - 定时同步超时，阈值: ${SYNC_TIMEOUT_SECONDS} 秒"
    else
        echo "❌ $(date '+%Y-%m-%d %H:%M:%S %Z') - 定时同步失败，退出码: $EXIT_CODE"
    fi
    echo "==========================================="
    echo ""
} >> "$LOG_FILE"

find "$LOG_DIR" -name "daily_sync_*.log" -type f -mtime +30 -delete 2>/dev/null

exit $EXIT_CODE
