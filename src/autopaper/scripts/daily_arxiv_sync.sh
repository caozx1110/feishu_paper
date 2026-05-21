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
#   SYNC_PROXY_URL=http://127.0.0.1:7890

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
export ARXIV_REQUEST_TIMEOUT="${ARXIV_REQUEST_TIMEOUT:-5,30}"
ARXIV_HEALTHCHECK_URL="${ARXIV_HEALTHCHECK_URL:-https://export.arxiv.org/api/query?search_query=all:robot&start=0&max_results=1}"
ARXIV_HEALTHCHECK_MAX_TIME="${ARXIV_HEALTHCHECK_MAX_TIME:-20}"
SYNC_USE_PROXY="${SYNC_USE_PROXY:-auto}"
SYNC_PROXY_URL="${SYNC_PROXY_URL:-}"

if [ -z "${http_proxy:-}" ] && [ -z "${https_proxy:-}" ] && [ -z "${HTTP_PROXY:-}" ] && [ -z "${HTTPS_PROXY:-}" ]; then
    if [ -n "$SYNC_PROXY_URL" ]; then
        export http_proxy="$SYNC_PROXY_URL"
        export https_proxy="$SYNC_PROXY_URL"
    elif [ "$SYNC_USE_PROXY" = "auto" ] && (echo > /dev/tcp/127.0.0.1/7890) >/dev/null 2>&1; then
        export http_proxy="http://127.0.0.1:7890"
        export https_proxy="http://127.0.0.1:7890"
    fi
fi

if [ -n "${https_proxy:-}" ]; then
    export HTTPS_PROXY="$https_proxy"
fi
if [ -n "${http_proxy:-}" ]; then
    export HTTP_PROXY="$http_proxy"
fi
export no_proxy="${no_proxy:-localhost,127.0.0.1,::1}"

{
    echo "==========================================="
    echo "🕒 $(date '+%Y-%m-%d %H:%M:%S %Z') - 开始每日 AutoPaper 同步"
    echo "📂 项目目录: $PROJECT_DIR"
    echo "📄 配置目录: $CONFIG_DIR"
    echo "⏱️  总超时: ${SYNC_TIMEOUT_SECONDS} 秒"
    echo "🌐 ArXiv请求超时: ${ARXIV_REQUEST_TIMEOUT} 秒"
    echo "🧭 HTTPS代理: ${https_proxy:-未设置}"
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

if command -v curl >/dev/null 2>&1; then
    echo "🌐 检查ArXiv API连通性..." >> "$LOG_FILE"
    if ! curl -fsS --connect-timeout 5 --max-time "$ARXIV_HEALTHCHECK_MAX_TIME" "$ARXIV_HEALTHCHECK_URL" >/dev/null 2>&1; then
        echo "❌ ArXiv API连接失败，跳过本次同步: $ARXIV_HEALTHCHECK_URL" >> "$LOG_FILE"
        exit 1
    fi
    echo "✅ ArXiv API连通性正常" >> "$LOG_FILE"
else
    echo "⚠️  未找到curl，跳过ArXiv API连通性预检" >> "$LOG_FILE"
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
