#!/usr/bin/env bash
#
# Install, remove, and inspect the AutoPaper daily cron job.

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${AUTOPAPER_PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
DAILY_SYNC_SCRIPT="${AUTOPAPER_DAILY_SYNC_SCRIPT:-$SCRIPT_DIR/daily_arxiv_sync.sh}"
CRON_SCHEDULE="${AUTOPAPER_CRON_SCHEDULE:-0 10 * * *}"
CRON_MARKER="autopaper daily_arxiv_sync"
CRON_LINE="$CRON_SCHEDULE AUTOPAPER_PROJECT_DIR=\"$PROJECT_DIR\" \"$DAILY_SYNC_SCRIPT\" # $CRON_MARKER"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
print_success() { echo -e "${GREEN}✅ $1${NC}"; }
print_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
print_error() { echo -e "${RED}❌ $1${NC}"; }

show_help() {
    echo "AutoPaper 定时任务管理脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 install      安装每日同步任务"
    echo "  $0 uninstall    卸载同步任务"
    echo "  $0 status       查看同步任务状态"
    echo "  $0 test         手动执行一次同步脚本"
    echo "  $0 logs         查看最近日志"
    echo ""
    echo "环境变量:"
    echo "  AUTOPAPER_CRON_SCHEDULE='0 10 * * *'"
    echo "  AUTOPAPER_PROJECT_DIR='$PROJECT_DIR'"
    echo "  AUTOPAPER_CONDA_ENV='autopaper'"
    echo "  AUTOPAPER_SYNC_FLAGS='--limit 10 --no-notify'"
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

install_cron() {
    print_info "开始安装 AutoPaper 定时任务..."

    if ! command -v crontab >/dev/null 2>&1; then
        print_error "未找到 crontab，请先安装 cron 或使用系统调度器手动运行 $DAILY_SYNC_SCRIPT"
        exit 1
    fi

    if [ ! -f "$DAILY_SYNC_SCRIPT" ]; then
        print_error "执行脚本不存在: $DAILY_SYNC_SCRIPT"
        exit 1
    fi

    if [ ! -x "$DAILY_SYNC_SCRIPT" ]; then
        chmod +x "$DAILY_SYNC_SCRIPT"
    fi

    crontab -l > "/tmp/autopaper_crontab_backup_$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
    (crontab -l 2>/dev/null | grep -v "$CRON_MARKER"; echo "$CRON_LINE") | crontab -

    if [ $? -eq 0 ]; then
        print_success "定时任务安装成功"
        print_info "任务: $CRON_LINE"
        print_info "日志目录: $PROJECT_DIR/logs"
    else
        print_error "定时任务安装失败"
        exit 1
    fi
}

uninstall_cron() {
    print_info "开始卸载 AutoPaper 定时任务..."
    if ! command -v crontab >/dev/null 2>&1; then
        print_error "未找到 crontab"
        exit 1
    fi
    if ! crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
        print_warning "未找到 AutoPaper 同步定时任务"
        exit 0
    fi

    crontab -l > "/tmp/autopaper_crontab_backup_$(date +%Y%m%d_%H%M%S)" 2>/dev/null || true
    crontab -l 2>/dev/null | grep -v "$CRON_MARKER" | crontab -
    print_success "定时任务卸载成功"
}

show_status() {
    print_info "AutoPaper 定时任务状态"
    if ! command -v crontab >/dev/null 2>&1; then
        print_warning "未找到 crontab"
        check_timezone
        return
    fi
    if crontab -l 2>/dev/null | grep -q "$CRON_MARKER"; then
        print_success "定时任务已安装"
        crontab -l 2>/dev/null | grep "$CRON_MARKER"
    else
        print_warning "定时任务未安装"
    fi
    echo ""
    check_timezone
}

test_script() {
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
    install) install_cron ;;
    uninstall) uninstall_cron ;;
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
