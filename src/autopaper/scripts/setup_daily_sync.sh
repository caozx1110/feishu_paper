#!/usr/bin/env bash
#
# Manage the AutoPaper daily cron job.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${AUTOPAPER_PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
DAILY_SYNC_SCRIPT="${AUTOPAPER_DAILY_SYNC_SCRIPT:-$SCRIPT_DIR/daily_arxiv_sync.sh}"
CRON_SCHEDULE="${AUTOPAPER_CRON_SCHEDULE:-0 10 * * *}"
CRON_MARKER="autopaper daily_arxiv_sync"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

escape_cron_value() {
    printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

cron_env_pair() {
    local name="$1"
    local value="$2"
    printf '%s="%s"' "$name" "$(escape_cron_value "$value")"
}

build_cron_env() {
    local entries=()
    entries+=("$(cron_env_pair AUTOPAPER_PROJECT_DIR "$PROJECT_DIR")")

    if [ -n "${AUTOPAPER_CONFIG_DIR:-}" ]; then
        entries+=("$(cron_env_pair AUTOPAPER_CONFIG_DIR "$AUTOPAPER_CONFIG_DIR")")
    fi
    if [ -n "${AUTOPAPER_LOG_DIR:-}" ]; then
        entries+=("$(cron_env_pair AUTOPAPER_LOG_DIR "$AUTOPAPER_LOG_DIR")")
    fi
    if [ -n "${AUTOPAPER_SYNC_FLAGS:-}" ]; then
        entries+=("$(cron_env_pair AUTOPAPER_SYNC_FLAGS "$AUTOPAPER_SYNC_FLAGS")")
    fi
    if [ -n "${AUTOPAPER_CONDA_ENV:-}" ]; then
        entries+=("$(cron_env_pair AUTOPAPER_CONDA_ENV "$AUTOPAPER_CONDA_ENV")")
    fi
    if [ -n "${AUTOPAPER_BIN:-}" ]; then
        entries+=("$(cron_env_pair AUTOPAPER_BIN "$AUTOPAPER_BIN")")
    fi
    if [ -n "${SYNC_TIMEOUT_SECONDS:-}" ]; then
        entries+=("$(cron_env_pair SYNC_TIMEOUT_SECONDS "$SYNC_TIMEOUT_SECONDS")")
    fi
    if [ -n "${ARXIV_REQUEST_TIMEOUT:-}" ]; then
        entries+=("$(cron_env_pair ARXIV_REQUEST_TIMEOUT "$ARXIV_REQUEST_TIMEOUT")")
    fi

    local IFS=' '
    echo "${entries[*]}"
}

cron_line() {
    echo "$CRON_SCHEDULE $(build_cron_env) \"$(escape_cron_value "$DAILY_SYNC_SCRIPT")\" # $CRON_MARKER"
}

show_help() {
    echo "AutoPaper 定时任务管理脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 add       新增定时同步任务；已存在时不会覆盖"
    echo "  $0 delete    删除当前 AutoPaper 定时同步任务"
    echo "  $0 update    更新已存在任务的时间、脚本路径和环境变量"
    echo "  $0 status    查看当前任务状态"
    echo "  $0 test      手动执行一次同步脚本"
    echo "  $0 logs      查看最近日志"
    echo ""
    echo "常用环境变量:"
    echo "  AUTOPAPER_CRON_SCHEDULE='0 10 * * *'"
    echo "  AUTOPAPER_PROJECT_DIR='$PROJECT_DIR'"
    echo "  AUTOPAPER_DAILY_SYNC_SCRIPT='$DAILY_SYNC_SCRIPT'"
    echo "  AUTOPAPER_BIN='/path/to/autopaper'"
    echo "  AUTOPAPER_SYNC_FLAGS='--limit 10 --no-notify'"
    echo "  AUTOPAPER_CONDA_ENV='autopaper'"
    echo "  SYNC_TIMEOUT_SECONDS=7200"
    echo ""
    echo "当前将写入的 cron:"
    echo "  $(cron_line)"
}

ensure_crontab() {
    if ! command -v crontab >/dev/null 2>&1; then
        print_error "未找到 crontab，请先安装 cron，或使用系统调度器手动运行 $DAILY_SYNC_SCRIPT"
        exit 1
    fi
}

ensure_sync_script() {
    if [ ! -f "$DAILY_SYNC_SCRIPT" ]; then
        print_error "执行脚本不存在: $DAILY_SYNC_SCRIPT"
        exit 1
    fi

    if [ ! -x "$DAILY_SYNC_SCRIPT" ]; then
        chmod +x "$DAILY_SYNC_SCRIPT"
    fi
}

backup_crontab() {
    crontab -l > "/tmp/autopaper_crontab_backup_$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
}

current_crontab() {
    crontab -l 2>/dev/null || true
}

job_exists() {
    current_crontab | grep -q "$CRON_MARKER"
}

write_crontab_without_job() {
    current_crontab | grep -v "$CRON_MARKER" | crontab -
}

add_cron() {
    print_info "新增 AutoPaper 定时任务..."
    ensure_crontab
    ensure_sync_script

    if job_exists; then
        print_warning "定时任务已存在；如需修改请运行: $0 update"
        show_status
        exit 1
    fi

    backup_crontab
    local new_cron_line
    new_cron_line="$(cron_line)"
    if ! (current_crontab; echo "$new_cron_line") | crontab -; then
        print_error "定时任务新增失败"
        exit 1
    fi
    print_success "定时任务新增成功"
    print_info "任务: $new_cron_line"
    print_info "日志目录: $PROJECT_DIR/logs"
}

delete_cron() {
    print_info "删除 AutoPaper 定时任务..."
    ensure_crontab

    if ! job_exists; then
        print_warning "未找到 AutoPaper 定时任务"
        exit 0
    fi

    backup_crontab
    if ! write_crontab_without_job; then
        print_error "定时任务删除失败"
        exit 1
    fi
    print_success "定时任务删除成功"
}

update_cron() {
    print_info "更新 AutoPaper 定时任务..."
    ensure_crontab
    ensure_sync_script

    if ! job_exists; then
        print_error "未找到可更新的 AutoPaper 定时任务；请先运行: $0 add"
        exit 1
    fi

    backup_crontab
    local new_cron_line
    new_cron_line="$(cron_line)"
    if ! (current_crontab | grep -v "$CRON_MARKER"; echo "$new_cron_line") | crontab -; then
        print_error "定时任务更新失败"
        exit 1
    fi
    print_success "定时任务更新成功"
    print_info "任务: $new_cron_line"
}

check_timezone() {
    print_info "检查系统时区..."
    CURRENT_TZ=$(timedatectl show --property=Timezone --value 2>/dev/null || date +%Z)
    echo "当前时区: $CURRENT_TZ"
    if [[ "$CURRENT_TZ" != "Asia/Shanghai" && "$CURRENT_TZ" != "CST" ]]; then
        print_warning "当前时区不是中国标准时间；如需每天北京时间执行，请设置 Asia/Shanghai"
    else
        print_success "时区设置正确"
    fi
}

show_status() {
    print_info "AutoPaper 定时任务状态"
    if ! command -v crontab >/dev/null 2>&1; then
        print_warning "未找到 crontab"
        check_timezone
        return
    fi

    if job_exists; then
        print_success "定时任务已安装"
        current_crontab | grep "$CRON_MARKER"
    else
        print_warning "定时任务未安装"
    fi

    echo ""
    print_info "当前配置生成的任务:"
    cron_line
    echo ""
    check_timezone
}

test_script() {
    ensure_sync_script
    print_info "手动执行同步脚本..."
    "$DAILY_SYNC_SCRIPT"
}

show_logs() {
    LOG_DIR="$PROJECT_DIR/logs"
    if [ ! -d "$LOG_DIR" ]; then
        print_warning "日志目录不存在: $LOG_DIR"
        exit 1
    fi

    LATEST_LOG=$(ls -t "$LOG_DIR"/daily_sync_*.log 2>/dev/null | head -1)
    if [ -z "$LATEST_LOG" ]; then
        print_warning "未找到日志文件"
        exit 1
    fi

    print_info "最近日志: $LATEST_LOG"
    tail -80 "$LATEST_LOG"
}

case "${1:-help}" in
    add) add_cron ;;
    delete) delete_cron ;;
    update) update_cron ;;
    status) show_status ;;
    test) test_script ;;
    logs) show_logs ;;
    help|--help|-h) show_help ;;
    *)
        print_error "未知命令: $1"
        show_help
        exit 1
        ;;
esac
