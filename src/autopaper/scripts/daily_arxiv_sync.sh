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
#   AUTOPAPER_ENV_FILE=/path/to/project/.env
#   AUTOPAPER_UV_BIN=/path/to/uv
#   AUTOPAPER_UV_PROJECT_DIR=/path/to/autopaper/source-or-project
#   AUTOPAPER_CLI=autopaper
#   AUTOPAPER_SYNC_FLAGS="--limit 10 --no-notify"
#   AUTOPAPER_CONDA_ENV=autopaper
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
LOCK_DIR="$LOG_DIR/daily_sync.lock.d"
if command -v flock >/dev/null 2>&1; then
    exec 9>"$LOCK_FILE"
    if ! flock -n 9; then
        {
            echo "==========================================="
            echo "⚠️  $(date '+%Y-%m-%d %H:%M:%S %Z') - 已有同步任务在运行，本次跳过"
            echo "==========================================="
        } >> "$LOG_FILE"
        exit 0
    fi
else
    if ! mkdir "$LOCK_DIR" 2>/dev/null; then
        {
            echo "==========================================="
            echo "⚠️  $(date '+%Y-%m-%d %H:%M:%S %Z') - 已有同步任务在运行，本次跳过"
            echo "==========================================="
        } >> "$LOG_FILE"
        exit 0
    fi
    trap 'rmdir "$LOCK_DIR" 2>/dev/null || true' EXIT
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

if [ -n "${AUTOPAPER_CONDA_ENV:-}" ]; then
    if [ -f "/opt/miniconda3/etc/profile.d/conda.sh" ]; then
        echo "🐍 激活conda环境: $AUTOPAPER_CONDA_ENV" >> "$LOG_FILE"
        source /opt/miniconda3/etc/profile.d/conda.sh
        conda activate "$AUTOPAPER_CONDA_ENV"
    elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
        echo "🐍 激活conda环境: $AUTOPAPER_CONDA_ENV" >> "$LOG_FILE"
        source "$HOME/miniconda3/etc/profile.d/conda.sh"
        conda activate "$AUTOPAPER_CONDA_ENV"
    elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
        echo "🐍 激活conda环境: $AUTOPAPER_CONDA_ENV" >> "$LOG_FILE"
        source "$HOME/anaconda3/etc/profile.d/conda.sh"
        conda activate "$AUTOPAPER_CONDA_ENV"
    else
        echo "⚠️ 已设置 AUTOPAPER_CONDA_ENV，但未找到 conda 初始化脚本" >> "$LOG_FILE"
    fi
fi

resolve_uv_bin() {
    if [ -n "${AUTOPAPER_UV_BIN:-}" ]; then
        if [ -x "$AUTOPAPER_UV_BIN" ] || command -v "$AUTOPAPER_UV_BIN" >/dev/null 2>&1; then
            printf '%s\n' "$AUTOPAPER_UV_BIN"
            return 0
        fi
        return 1
    fi

    if command -v uv >/dev/null 2>&1; then
        command -v uv
        return 0
    fi

    if [ -x "$HOME/.local/bin/uv" ]; then
        printf '%s\n' "$HOME/.local/bin/uv"
        return 0
    fi

    return 1
}

discover_uv_project_dir() {
    if [ -n "${AUTOPAPER_UV_PROJECT_DIR:-}" ]; then
        printf '%s\n' "$AUTOPAPER_UV_PROJECT_DIR"
        return 0
    fi

    local candidate
    for candidate in "$PROJECT_DIR" "$PROJECT_DIR/.." "$SCRIPT_DIR/../../.."; do
        if [ -f "$candidate/pyproject.toml" ]; then
            (cd "$candidate" >/dev/null 2>&1 && pwd)
            return 0
        fi
    done

    return 1
}

if ! UV_BIN="$(resolve_uv_bin)"; then
    echo "❌ uv 命令不可用，请先安装 uv，或设置 AUTOPAPER_UV_BIN=/path/to/uv" >> "$LOG_FILE"
    exit 1
fi

AUTOPAPER_CLI="${AUTOPAPER_CLI:-autopaper}"
ENV_FILE="${AUTOPAPER_ENV_FILE:-$PROJECT_DIR/.env}"
AUTOPAPER_CMD=("$UV_BIN")
if UV_PROJECT_DIR="$(discover_uv_project_dir)"; then
    AUTOPAPER_CMD+=(--directory "$UV_PROJECT_DIR")
    echo "🐍 使用 uv 项目目录: $UV_PROJECT_DIR" >> "$LOG_FILE"
else
    echo "🐍 未发现 pyproject.toml，将直接使用 uv run" >> "$LOG_FILE"
fi
AUTOPAPER_CMD+=(run "$AUTOPAPER_CLI")
if [ -f "$ENV_FILE" ] || [ -n "${AUTOPAPER_ENV_FILE:-}" ]; then
    AUTOPAPER_CMD+=(--env-file "$ENV_FILE")
fi

if ! "${AUTOPAPER_CMD[@]}" --version >> "$LOG_FILE" 2>&1; then
    echo "❌ AutoPaper CLI 不可用: ${AUTOPAPER_CMD[*]}" >> "$LOG_FILE"
    exit 1
fi

echo "🌐 检查AutoPaper运行环境..." >> "$LOG_FILE"
HEALTH_CMD=("${AUTOPAPER_CMD[@]}" health --config all)
if [ -f "$CONFIG_DIR/default.yaml" ]; then
    HEALTH_CMD+=(--config-dir "$CONFIG_DIR")
fi
if ! "${HEALTH_CMD[@]}" >> "$LOG_FILE" 2>&1; then
    echo "❌ AutoPaper健康检查失败，跳过本次同步" >> "$LOG_FILE"
    exit 1
fi

SYNC_CMD=("${AUTOPAPER_CMD[@]}" sync --config all)
if [ -f "$CONFIG_DIR/all.yaml" ]; then
    SYNC_CMD+=(--config-dir "$CONFIG_DIR")
fi
if [ -n "${AUTOPAPER_SYNC_FLAGS:-}" ]; then
    # shellcheck disable=SC2206
    EXTRA_SYNC_FLAGS=($AUTOPAPER_SYNC_FLAGS)
    SYNC_CMD+=("${EXTRA_SYNC_FLAGS[@]}")
fi

echo "🚀 开始执行论文采集..." >> "$LOG_FILE"
echo "📝 命令: ${SYNC_CMD[*]}" >> "$LOG_FILE"

if command -v timeout >/dev/null 2>&1; then
    timeout --kill-after=60s "$SYNC_TIMEOUT_SECONDS" "${SYNC_CMD[@]}" >> "$LOG_FILE" 2>&1
else
    echo "⚠️ 未找到 timeout 命令，将不启用总超时控制" >> "$LOG_FILE"
    "${SYNC_CMD[@]}" >> "$LOG_FILE" 2>&1
fi
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
