#!/bin/bash
#
# 定时任务安装和管理脚本
# 用于安装、卸载和管理ArXiv论文采集的定时任务
#

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
CRONTAB_FILE="$SCRIPT_DIR/crontab_daily_sync"
DAILY_SYNC_SCRIPT="$SCRIPT_DIR/daily_arxiv_sync.sh"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 显示帮助信息
show_help() {
    echo "ArXiv论文采集定时任务管理脚本"
    echo ""
    echo "使用方法:"
    echo "  $0 [选项]"
    echo ""
    echo "选项:"
    echo "  install     安装定时任务"
    echo "  uninstall   卸载定时任务"
    echo "  status      查看定时任务状态"
    echo "  test        测试执行脚本"
    echo "  logs        查看最近的日志"
    echo "  help        显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 install      # 安装每日10点的定时任务"
    echo "  $0 status       # 查看当前定时任务状态"
    echo "  $0 test         # 测试脚本是否正常工作"
}

# 检查系统时区
check_timezone() {
    print_info "检查系统时区..."
    CURRENT_TZ=$(timedatectl show --property=Timezone --value 2>/dev/null || date +%Z)
    echo "当前时区: $CURRENT_TZ"
    
    if [[ "$CURRENT_TZ" != "Asia/Shanghai" && "$CURRENT_TZ" != "CST" ]]; then
        print_warning "当前时区不是中国标准时间"
        print_info "建议设置时区为中国标准时间："
        echo "  sudo timedatectl set-timezone Asia/Shanghai"
        echo ""
    else
        print_success "时区设置正确"
    fi
}

# 安装定时任务
install_cron() {
    print_info "开始安装ArXiv论文采集定时任务..."
    
    # 检查必要文件
    if [ ! -f "$DAILY_SYNC_SCRIPT" ]; then
        print_error "执行脚本不存在: $DAILY_SYNC_SCRIPT"
        exit 1
    fi
    
    if [ ! -f "$CRONTAB_FILE" ]; then
        print_error "Crontab配置文件不存在: $CRONTAB_FILE"
        exit 1
    fi
    
    # 检查脚本权限
    if [ ! -x "$DAILY_SYNC_SCRIPT" ]; then
        print_info "添加执行权限..."
        chmod +x "$DAILY_SYNC_SCRIPT"
    fi
    
    # 备份现有crontab
    print_info "备份现有crontab..."
    crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null || true
    
    # 检查是否已存在相同任务
    if crontab -l 2>/dev/null | grep -q "daily_arxiv_sync.sh"; then
        print_warning "检测到已存在的ArXiv同步任务"
        read -p "是否要替换现有任务? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            print_info "取消安装"
            exit 0
        fi
        
        # 移除现有任务
        print_info "移除现有任务..."
        crontab -l 2>/dev/null | grep -v "daily_arxiv_sync.sh" | crontab -
    fi
    
    # 添加新任务
    print_info "添加定时任务..."
    (crontab -l 2>/dev/null; cat "$CRONTAB_FILE") | crontab -
    
    if [ $? -eq 0 ]; then
        print_success "定时任务安装成功！"
        print_info "任务将在每天上午10:00（中国时间）执行"
        print_info "日志文件位置: $PROJECT_DIR/logs/daily_sync_YYYYMMDD.log"
    else
        print_error "定时任务安装失败"
        exit 1
    fi
}

# 卸载定时任务
uninstall_cron() {
    print_info "开始卸载ArXiv论文采集定时任务..."
    
    if ! crontab -l 2>/dev/null | grep -q "daily_arxiv_sync.sh"; then
        print_warning "未找到ArXiv同步定时任务"
        exit 0
    fi
    
    # 备份现有crontab
    print_info "备份现有crontab..."
    crontab -l > /tmp/crontab_backup_$(date +%Y%m%d_%H%M%S) 2>/dev/null
    
    # 移除任务
    print_info "移除定时任务..."
    crontab -l 2>/dev/null | grep -v "daily_arxiv_sync.sh" | crontab -
    
    if [ $? -eq 0 ]; then
        print_success "定时任务卸载成功！"
    else
        print_error "定时任务卸载失败"
        exit 1
    fi
}

# 查看状态
show_status() {
    print_info "ArXiv论文采集定时任务状态"
    echo ""
    
    # 检查crontab
    if crontab -l 2>/dev/null | grep -q "daily_arxiv_sync.sh"; then
        print_success "定时任务已安装"
        echo "任务配置:"
        crontab -l 2>/dev/null | grep "daily_arxiv_sync.sh"
    else
        print_warning "定时任务未安装"
    fi
    
    echo ""
    check_timezone
    
    # 检查最近的日志
    LOG_DIR="$PROJECT_DIR/logs"
    if [ -d "$LOG_DIR" ]; then
        LATEST_LOG=$(ls -t "$LOG_DIR"/daily_sync_*.log 2>/dev/null | head -1)
        if [ -n "$LATEST_LOG" ]; then
            echo ""
            print_info "最近的日志文件: $LATEST_LOG"
            echo "最后10行:"
            tail -10 "$LATEST_LOG"
        fi
    fi
}

# 测试脚本
test_script() {
    print_info "测试ArXiv论文采集脚本..."
    
    if [ ! -f "$DAILY_SYNC_SCRIPT" ]; then
        print_error "执行脚本不存在: $DAILY_SYNC_SCRIPT"
        exit 1
    fi
    
    if [ ! -x "$DAILY_SYNC_SCRIPT" ]; then
        print_error "执行脚本没有执行权限"
        exit 1
    fi
    
    print_info "执行测试运行..."
    "$DAILY_SYNC_SCRIPT"
    
    if [ $? -eq 0 ]; then
        print_success "脚本测试成功！"
    else
        print_error "脚本测试失败"
        exit 1
    fi
}

# 查看日志
show_logs() {
    LOG_DIR="$PROJECT_DIR/logs"
    
    if [ ! -d "$LOG_DIR" ]; then
        print_warning "日志目录不存在: $LOG_DIR"
        exit 1
    fi
    
    LOG_FILES=($(ls -t "$LOG_DIR"/daily_sync_*.log 2>/dev/null))
    
    if [ ${#LOG_FILES[@]} -eq 0 ]; then
        print_warning "未找到日志文件"
        exit 1
    fi
    
    print_info "找到 ${#LOG_FILES[@]} 个日志文件"
    
    for i in "${!LOG_FILES[@]}"; do
        echo "$((i+1)). $(basename "${LOG_FILES[$i]}")"
    done
    
    echo ""
    read -p "请选择要查看的日志文件编号 (1-${#LOG_FILES[@]}，默认为1): " choice
    
    choice=${choice:-1}
    
    if [[ "$choice" =~ ^[0-9]+$ ]] && [ "$choice" -ge 1 ] && [ "$choice" -le ${#LOG_FILES[@]} ]; then
        selected_log="${LOG_FILES[$((choice-1))]}"
        print_info "显示日志文件: $(basename "$selected_log")"
        echo ""
        cat "$selected_log"
    else
        print_error "无效的选择"
        exit 1
    fi
}

# 主函数
main() {
    case "${1:-help}" in
        install)
            install_cron
            ;;
        uninstall)
            uninstall_cron
            ;;
        status)
            show_status
            ;;
        test)
            test_script
            ;;
        logs)
            show_logs
            ;;
        help|--help|-h)
            show_help
            ;;
        *)
            print_error "未知选项: $1"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"
