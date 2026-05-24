#!/usr/bin/env bash
#
# Interactive AutoPaper project setup.
#
# Run from an initialized project directory:
#   scripts/configure_project.sh
#
# Environment overrides:
#   AUTOPAPER_PROJECT_DIR=/path/to/project
#   AUTOPAPER_CONFIG_DIR=/path/to/project/conf
#   AUTOPAPER_ENV_FILE=/path/to/project/.env
#   AUTOPAPER_UV_BIN=/path/to/uv
#   AUTOPAPER_UV_PROJECT_DIR=/path/to/autopaper/source-or-project
#   AUTOPAPER_CLI=autopaper

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${AUTOPAPER_PROJECT_DIR:-$(cd "$SCRIPT_DIR/.." && pwd)}"
CONFIG_DIR="${AUTOPAPER_CONFIG_DIR:-$PROJECT_DIR/conf}"
ENV_FILE="${AUTOPAPER_ENV_FILE:-$PROJECT_DIR/.env}"
ENV_TEMPLATE="$PROJECT_DIR/.env.template"
ALL_CONFIG="$CONFIG_DIR/all.yaml"
SETUP_SCRIPT="$SCRIPT_DIR/setup_daily_sync.sh"
AUTOPAPER_CLI="${AUTOPAPER_CLI:-autopaper}"

if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    RED=$'\033[0;31m'
    GREEN=$'\033[0;32m'
    YELLOW=$'\033[1;33m'
    BLUE=$'\033[0;34m'
    CYAN=$'\033[0;36m'
    BOLD=$'\033[1m'
    DIM=$'\033[2m'
    NC=$'\033[0m'
else
    RED=''
    GREEN=''
    YELLOW=''
    BLUE=''
    CYAN=''
    BOLD=''
    DIM=''
    NC=''
fi

terminal_width() {
    local width
    width="$(tput cols 2>/dev/null || true)"
    if [[ "$width" =~ ^[0-9]+$ ]] && [ "$width" -ge 60 ]; then
        printf '%s\n' "$width"
    else
        printf '88\n'
    fi
}

rule() {
    local width line
    width="$(terminal_width)"
    printf -v line '%*s' "$width" ''
    printf '%s%s%s\n' "$DIM" "${line// /─}" "$NC"
}

print_banner() {
    echo ""
    rule
    printf "%sAutoPaper 交互式配置向导%s\n" "$BOLD" "$NC"
    printf "%s一次完成 .env、飞书通知、健康检查和每日定时任务。%s\n" "$DIM" "$NC"
    rule
}

print_section() {
    local number="$1"
    local title="$2"
    local subtitle="${3:-}"
    echo ""
    rule
    printf "%s[%s/4] %s%s\n" "$BOLD" "$number" "$title" "$NC"
    if [ -n "$subtitle" ]; then
        printf "%s%s%s\n" "$DIM" "$subtitle" "$NC"
    fi
}

print_info() { printf "%s•%s %s\n" "$BLUE" "$NC" "$1"; }
print_success() { printf "%s✓%s %s\n" "$GREEN" "$NC" "$1"; }
print_warning() { printf "%s!%s %s\n" "$YELLOW" "$NC" "$1"; }
print_error() { printf "%sx%s %s\n" "$RED" "$NC" "$1"; }
print_hint() { printf "%s  %s%s\n" "$DIM" "$1" "$NC"; }
print_help_text() {
    local label="$1"
    local text="$2"
    if [ -n "$text" ]; then
        print_hint "$label：$text"
    fi
}

print_kv() {
    local key="$1"
    local value="$2"
    printf "  %-14s %s\n" "$key" "$value"
}

print_command() {
    printf "  %s%s%s\n" "$CYAN" "$1" "$NC"
}

finish_prompt_line() {
    if [ ! -t 0 ]; then
        echo ""
    fi
}

show_help() {
    echo "AutoPaper 交互式配置向导"
    echo ""
    echo "使用方法:"
    print_command "$0"
    echo ""
    echo "可选环境变量:"
    print_kv "项目目录" "AUTOPAPER_PROJECT_DIR='$PROJECT_DIR'"
    print_kv "配置目录" "AUTOPAPER_CONFIG_DIR='$CONFIG_DIR'"
    print_kv ".env" "AUTOPAPER_ENV_FILE='$ENV_FILE'"
    print_kv "uv 路径" "AUTOPAPER_UV_BIN='/path/to/uv'"
    print_kv "uv 项目" "AUTOPAPER_UV_PROJECT_DIR='/path/to/autopaper/source-or-project'"
    print_kv "CLI" "AUTOPAPER_CLI='autopaper'"
}

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

UV_BIN="$(resolve_uv_bin || true)"
UV_PROJECT_DIR="$(discover_uv_project_dir || true)"

run_python() {
    if [ -n "$UV_BIN" ] && [ -n "$UV_PROJECT_DIR" ]; then
        "$UV_BIN" --directory "$UV_PROJECT_DIR" run python "$@"
    else
        python3 "$@"
    fi
}

run_autopaper() {
    local cmd=()
    if [ -n "$UV_BIN" ]; then
        cmd+=("$UV_BIN")
        if [ -n "$UV_PROJECT_DIR" ]; then
            cmd+=(--directory "$UV_PROJECT_DIR")
        fi
        cmd+=(run "$AUTOPAPER_CLI")
    else
        cmd+=("$AUTOPAPER_CLI")
    fi

    if [ -f "$ENV_FILE" ]; then
        cmd+=(--env-file "$ENV_FILE")
    fi

    "${cmd[@]}" "$@"
}

require_project() {
    if [ ! -d "$CONFIG_DIR" ]; then
        print_error "配置目录不存在: $CONFIG_DIR"
        echo "请先运行: autopaper init --with-scripts"
        exit 1
    fi

    if [ ! -f "$ALL_CONFIG" ]; then
        print_error "批量配置不存在: $ALL_CONFIG"
        exit 1
    fi
}

ensure_env_file() {
    if [ -f "$ENV_FILE" ]; then
        return
    fi

    if [ -f "$ENV_TEMPLATE" ]; then
        cp "$ENV_TEMPLATE" "$ENV_FILE"
        print_success "已从 .env.template 创建 .env"
    else
        touch "$ENV_FILE"
        print_success "已创建空 .env"
    fi
}

read_env_value() {
    local key="$1"
    local value
    if [ ! -f "$ENV_FILE" ]; then
        return 0
    fi
    value="$(awk -F= -v key="$key" '
        $0 ~ "^[[:space:]]*" key "=" {
            sub(/^[^=]*=/, "")
            value=$0
        }
        END { if (value != "") print value }
    ' "$ENV_FILE")"

    if [[ "$value" =~ ^cli_x+$ || "$value" =~ ^x+$ || "$value" =~ ^u-x+$ || "$value" =~ ^t-x+$ ]]; then
        return 0
    fi

    printf '%s\n' "$value"
}

mask_value() {
    local value="$1"
    local length=${#value}
    if [ "$length" -le 8 ]; then
        printf '********'
    else
        printf '%s****%s' "${value:0:4}" "${value: -4}"
    fi
}

prompt_value() {
    local result_var="$1"
    local label="$2"
    local current="$3"
    local required="$4"
    local secret="$5"
    local meaning="${6:-}"
    local source="${7:-}"
    local input value display

    while true; do
        echo ""
        if [ "$required" = "yes" ]; then
            printf "%s%s%s %s*%s\n" "$BOLD" "$label" "$NC" "$RED" "$NC"
        else
            printf "%s%s%s\n" "$BOLD" "$label" "$NC"
        fi
        print_help_text "含义" "$meaning"
        print_help_text "获取/建议" "$source"
        if [ -n "$current" ]; then
            if [ "$secret" = "yes" ]; then
                display="$(mask_value "$current")"
            else
                display="$current"
            fi
            print_hint "当前值: $display"
            print_hint "回车保留当前值；输入 - 清空。"
        elif [ "$required" = "yes" ]; then
            print_hint "必填。"
        else
            print_hint "可选；留空跳过。"
        fi
        printf "%s›%s " "$CYAN" "$NC"
        if [ "$secret" = "yes" ]; then
            read -r -s input
            echo ""
        else
            read -r input
            finish_prompt_line
        fi

        if [ -z "$input" ]; then
            value="$current"
        elif [ "$input" = "-" ]; then
            value=""
        else
            value="$input"
        fi

        if [ "$required" = "yes" ] && [ -z "$value" ]; then
            print_warning "该项不能为空"
            continue
        fi

        printf -v "$result_var" '%s' "$value"
        return
    done
}

prompt_yes_no() {
    local result_var="$1"
    local question="$2"
    local default="$3"
    local meaning="${4:-}"
    local suggestion="${5:-}"
    local suffix answer value

    if [ "$default" = "yes" ]; then
        suffix="Y/n"
    else
        suffix="y/N"
    fi

    while true; do
        echo ""
        printf "%s%s%s %s[%s]%s\n" "$BOLD" "$question" "$NC" "$DIM" "$suffix" "$NC"
        print_help_text "含义" "$meaning"
        print_help_text "建议" "$suggestion"
        printf "%s›%s " "$CYAN" "$NC"
        read -r answer
        finish_prompt_line
        answer="${answer,,}"
        if [ -z "$answer" ]; then
            value="$default"
            break
        fi
        case "$answer" in
            y|yes) value="yes"; break ;;
            n|no) value="no"; break ;;
            *) print_warning "请输入 y 或 n" ;;
        esac
    done

    printf -v "$result_var" '%s' "$value"
}

prompt_number() {
    local result_var="$1"
    local question="$2"
    local default="$3"
    local meaning="${4:-}"
    local suggestion="${5:-}"
    local answer

    while true; do
        echo ""
        printf "%s%s%s %s[%s]%s\n" "$BOLD" "$question" "$NC" "$DIM" "$default" "$NC"
        print_help_text "含义" "$meaning"
        print_help_text "建议" "$suggestion"
        printf "%s›%s " "$CYAN" "$NC"
        read -r answer
        finish_prompt_line
        answer="${answer:-$default}"
        if [[ "$answer" =~ ^[0-9]+$ ]]; then
            printf -v "$result_var" '%s' "$answer"
            return
        fi
        print_warning "请输入非负整数"
    done
}

upsert_env_value() {
    local key="$1"
    local value="$2"
    ENV_FILE="$ENV_FILE" KEY="$key" VALUE="$value" run_python <<'PY'
import os
import re
from pathlib import Path

path = Path(os.environ["ENV_FILE"])
key = os.environ["KEY"]
value = os.environ["VALUE"]
pattern = re.compile(rf"^\s*{re.escape(key)}=")

lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
updated = False
new_lines = []
for line in lines:
    if pattern.match(line):
        if not updated:
            new_lines.append(f"{key}={value}")
            updated = True
        continue
    new_lines.append(line)

if not updated:
    if new_lines and new_lines[-1] != "":
        new_lines.append("")
    new_lines.append(f"{key}={value}")

path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
PY
}

configure_env() {
    print_section "1" "飞书环境配置" "准备飞书开放平台应用、目标多维表格，以及自动化访问 token。"
    print_info "App ID / App Secret 来自飞书开放平台应用凭证。"
    print_info "多维表格 app_token 来自目标表格 URL 或开放平台资源。"
    print_info "tenant_access_token 可手动填写；留空时可让脚本尝试获取并保存。"

    local app_id app_secret bitable_token tenant_token user_token papers_table relations_table timeout sync_timeout

    prompt_value app_id \
        "飞书 App ID，形如 cli_xxx" \
        "$(read_env_value FEISHU_APP_ID)" \
        yes \
        no \
        "飞书开放平台应用的唯一标识，AutoPaper 用它确认调用哪个应用的权限。" \
        "飞书开放平台 -> 应用详情 -> 凭证与基础信息。"
    prompt_value app_secret \
        "飞书 App Secret" \
        "$(read_env_value FEISHU_APP_SECRET)" \
        yes \
        yes \
        "应用密钥，用来和 App ID 一起换取访问令牌；这是敏感信息。" \
        "飞书开放平台 -> 应用详情 -> 凭证与基础信息。"
    prompt_value bitable_token \
        "飞书多维表格 app_token" \
        "$(read_env_value FEISHU_BITABLE_APP_TOKEN)" \
        yes \
        no \
        "目标多维表格文档的标识，决定论文写入哪个多维表格。" \
        "打开多维表格 URL，从链接中获取 base/app token；或在开放平台资源信息中查看。"
    prompt_value tenant_token \
        "Tenant Access Token，推荐自动化使用，形如 t-xxx" \
        "$(read_env_value FEISHU_TENANT_ACCESS_TOKEN)" \
        no \
        yes \
        "应用级访问令牌，定时任务和服务器后台同步优先使用它。" \
        "可手动填写，也可以留空后让脚本用 App ID / App Secret 自动获取。"
    prompt_value user_token \
        "User Access Token，可选；一般定时同步不需要" \
        "$(read_env_value FEISHU_USER_ACCESS_TOKEN)" \
        no \
        yes \
        "用户身份访问令牌，只在某些需要用户权限的飞书接口里使用。" \
        "常规自动同步可留空。"
    prompt_value papers_table \
        "已有论文主表 table_id，可选；留空则按配置查找或创建" \
        "$(read_env_value FEISHU_PAPERS_TABLE_ID)" \
        no \
        no \
        "指定已有论文表的表 ID；填写后会直接写入该表。" \
        "如果希望 AutoPaper 自动查找或创建表格，请留空。"
    prompt_value relations_table \
        "已有领域关系表 table_id，可选；留空则按配置查找或创建" \
        "$(read_env_value FEISHU_RELATIONS_TABLE_ID)" \
        no \
        no \
        "指定已有领域关系表的表 ID，用于维护论文与研究方向关系。" \
        "大多数场景可以留空。"
    prompt_value timeout \
        "arXiv 请求超时，格式如 5,30" \
        "$(read_env_value ARXIV_REQUEST_TIMEOUT)" \
        no \
        no \
        "arXiv 网络请求超时设置，通常是连接超时和读取超时。" \
        "网络稳定时保留 5,30；网络较慢可调大，例如 10,60。"
    timeout="${timeout:-5,30}"
    local current_sync_timeout
    current_sync_timeout="$(read_env_value SYNC_TIMEOUT_SECONDS || true)"
    prompt_number sync_timeout \
        "单次定时同步总超时秒数" \
        "${current_sync_timeout:-7200}" \
        "cron 每次运行允许占用的最长时间，超过后会终止，避免任务堆积。" \
        "保留 7200 即 2 小时；配置很多或网络慢时可适当调大。"

    upsert_env_value FEISHU_APP_ID "$app_id"
    upsert_env_value FEISHU_APP_SECRET "$app_secret"
    upsert_env_value FEISHU_BITABLE_APP_TOKEN "$bitable_token"
    upsert_env_value FEISHU_TENANT_ACCESS_TOKEN "$tenant_token"
    upsert_env_value FEISHU_USER_ACCESS_TOKEN "$user_token"
    upsert_env_value FEISHU_PAPERS_TABLE_ID "$papers_table"
    upsert_env_value FEISHU_RELATIONS_TABLE_ID "$relations_table"
    upsert_env_value ARXIV_REQUEST_TIMEOUT "$timeout"
    upsert_env_value SYNC_TIMEOUT_SECONDS "$sync_timeout"

    print_success ".env 已更新"
    print_hint "$ENV_FILE"

    if [ -z "$tenant_token" ]; then
        local fetch_token
        prompt_yes_no fetch_token \
            "是否现在用 App ID / App Secret 获取并保存 tenant_access_token？" \
            yes \
            "脚本会调用飞书接口生成应用级访问令牌，并写回 .env。" \
            "第一次配置推荐选择 yes。"
        if [ "$fetch_token" = "yes" ]; then
            if run_autopaper get-token --save; then
                print_success "tenant_access_token 已保存"
            else
                print_warning "获取 token 失败；可稍后运行: autopaper --env-file .env get-token --save"
            fi
        fi
    fi
}

configure_all_yaml() {
    print_section "2" "飞书同步和群通知" "更新 conf/all.yaml，控制完整批量同步后的飞书写入和群消息。"
    print_info "生产环境建议填写明确的 target_chat_ids。"
    print_info "如果暂时不知道群聊 ID，可以先选择发送到机器人所在所有群。"

    local enable_feishu enable_notify send_all chat_ids threshold recommended include_links
    prompt_yes_no enable_feishu \
        "是否启用飞书多维表格写入？" \
        yes \
        "开启后，同步结果会写入飞书多维表格；关闭后只做搜索、筛选和本地输出。" \
        "正式使用推荐开启；调试搜索规则时可以关闭或使用 --dry-run。"
    prompt_yes_no enable_notify \
        "是否启用飞书群通知？" \
        yes \
        "开启后，完整批量同步结束会按新增论文数量发送群汇总。" \
        "需要机器人已加入目标群，且不要在同步命令里加 --no-notify。"
    prompt_number threshold \
        "至少新增多少篇论文才发送通知？" \
        1 \
        "本次同步新增论文数低于该值时，不打扰群聊。" \
        "希望每天有新增就通知可填 1；想减少打扰可填 2 或更高。"
    prompt_number recommended \
        "每个方向在通知中展示几篇推荐论文？" \
        1 \
        "群消息里每个研究方向最多展示的高分论文数量。" \
        "1 最简洁；团队需要浏览更多候选时可填 2 或 3。"
    prompt_yes_no include_links \
        "通知中是否包含表格链接？" \
        yes \
        "开启后群消息会附带飞书多维表格入口，方便点进完整列表。" \
        "推荐开启。"

    if [ "$enable_notify" = "yes" ]; then
        prompt_yes_no send_all \
            "是否发送到机器人所在所有群？" \
            no \
            "开启后会向机器人可见的所有群发送通知；关闭后只发给 target_chat_ids。" \
            "生产环境推荐选择 no，并填写明确的群聊 ID。"
        if [ "$send_all" = "yes" ]; then
            chat_ids=""
        else
            echo ""
            printf "%s目标群聊 chat_id%s\n" "$BOLD" "$NC"
            print_help_text "含义" "飞书群聊的唯一 ID，AutoPaper 会只向这些群发送通知。"
            print_help_text "建议" "多个 ID 用英文逗号分隔；生产环境建议明确填写，避免误发。"
            print_hint "多个 ID 用英文逗号分隔，形如 oc_xxx。"
            print_hint "也可以稍后用 AutoPaper 通知检查命令确认群聊。"
            printf "%s›%s " "$CYAN" "$NC"
            read -r chat_ids
            finish_prompt_line
        fi
    else
        send_all="no"
        chat_ids=""
    fi

    ALL_CONFIG="$ALL_CONFIG" \
    ENABLE_FEISHU="$enable_feishu" \
    ENABLE_NOTIFY="$enable_notify" \
    SEND_ALL="$send_all" \
    CHAT_IDS="$chat_ids" \
    MIN_THRESHOLD="$threshold" \
    MAX_RECOMMENDED="$recommended" \
    INCLUDE_LINKS="$include_links" \
    run_python <<'PY'
import os
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("缺少 PyYAML，无法更新 YAML；请使用 uv 环境运行或安装 PyYAML。", file=sys.stderr)
    raise


def as_bool(value: str) -> bool:
    return value.lower() in {"1", "true", "yes", "y"}


path = Path(os.environ["ALL_CONFIG"])
data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}

feishu = data.setdefault("feishu", {})
feishu["enabled"] = as_bool(os.environ["ENABLE_FEISHU"])
chat = feishu.setdefault("chat_notification", {})
chat["enabled"] = as_bool(os.environ["ENABLE_NOTIFY"])
chat["min_papers_threshold"] = int(os.environ["MIN_THRESHOLD"])
chat["max_recommended_papers"] = int(os.environ["MAX_RECOMMENDED"])
chat["message_template"] = chat.get("message_template") or "default"
chat["include_table_links"] = as_bool(os.environ["INCLUDE_LINKS"])
chat["send_to_all_chats"] = as_bool(os.environ["SEND_ALL"])

ids = [item.strip() for item in os.environ["CHAT_IDS"].replace("\n", ",").split(",") if item.strip()]
chat["target_chat_ids"] = [] if chat["send_to_all_chats"] else ids

path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
PY

    print_success "群通知配置已更新"
    print_hint "$ALL_CONFIG"
}

run_checks() {
    print_section "3" "配置检查" "校验配置文件、飞书环境变量，并可选择检查通知目标。"

    print_info "校验同步配置..."
    if ! run_autopaper validate-config --config all --config-dir "$CONFIG_DIR"; then
        print_warning "配置校验未完全通过，请根据上方提示修正。"
    fi

    print_info "运行健康检查..."
    if ! run_autopaper health --config all --config-dir "$CONFIG_DIR" --skip-network; then
        print_warning "健康检查未完全通过，请检查 .env 和飞书权限。"
    fi

    local check_notify send_notify
    prompt_yes_no check_notify \
        "是否检查飞书通知目标？不会发送消息" \
        yes \
        "只验证机器人能看到哪些群，以及 target_chat_ids 是否能匹配到目标。" \
        "推荐执行，能提前发现群 ID 错误或机器人未入群。"
    if [ "$check_notify" = "yes" ]; then
        run_autopaper feishu test-notify --config all --config-dir "$CONFIG_DIR" || true
    fi

    prompt_yes_no send_notify \
        "是否发送一条飞书测试通知？" \
        no \
        "会真实向目标群发送一条测试消息，用于确认通知链路。" \
        "不想打扰群聊就选择 no；上线前建议在测试群选择 yes。"
    if [ "$send_notify" = "yes" ]; then
        run_autopaper feishu test-notify --config all --config-dir "$CONFIG_DIR" --send || true
    fi
}

configure_cron() {
    print_section "4" "每日定时任务" "配置 cron，让 AutoPaper 每天自动同步并按条件发送飞书通知。"

    if [ ! -f "$SETUP_SCRIPT" ]; then
        print_warning "未找到定时任务管理脚本: $SETUP_SCRIPT"
        return
    fi

    local enable_cron schedule action
    prompt_yes_no enable_cron \
        "是否配置每日自动同步定时任务？" \
        yes \
        "写入当前用户 crontab，每天自动运行 scripts/daily_arxiv_sync.sh。" \
        "服务器长期运行时推荐开启；本地临时试用可跳过。"
    if [ "$enable_cron" != "yes" ]; then
        print_info "已跳过定时任务配置"
        return
    fi

    echo ""
    printf "%scron 表达式%s %s[0 10 * * *]%s\n" "$BOLD" "$NC" "$DIM" "$NC"
    print_help_text "含义" "5 段 cron 时间：分钟 小时 日期 月份 星期。"
    print_hint "默认每天北京时间 10:00 执行；例如 0 9 * * * 表示每天 09:00。"
    printf "%s›%s " "$CYAN" "$NC"
    read -r schedule
    finish_prompt_line
    schedule="${schedule:-0 10 * * *}"

    chmod +x "$SETUP_SCRIPT" "$SCRIPT_DIR/daily_arxiv_sync.sh" 2>/dev/null || true

    if crontab -l 2>/dev/null | grep -q "autopaper daily_arxiv_sync"; then
        action="update"
    else
        action="add"
    fi

    AUTOPAPER_PROJECT_DIR="$PROJECT_DIR" \
    AUTOPAPER_CONFIG_DIR="$CONFIG_DIR" \
    AUTOPAPER_ENV_FILE="$ENV_FILE" \
    AUTOPAPER_CRON_SCHEDULE="$schedule" \
    AUTOPAPER_UV_BIN="$UV_BIN" \
    AUTOPAPER_UV_PROJECT_DIR="$UV_PROJECT_DIR" \
    AUTOPAPER_CLI="$AUTOPAPER_CLI" \
    "$SETUP_SCRIPT" "$action"

    AUTOPAPER_PROJECT_DIR="$PROJECT_DIR" \
    AUTOPAPER_CONFIG_DIR="$CONFIG_DIR" \
    AUTOPAPER_ENV_FILE="$ENV_FILE" \
    AUTOPAPER_CRON_SCHEDULE="$schedule" \
    AUTOPAPER_UV_BIN="$UV_BIN" \
    AUTOPAPER_UV_PROJECT_DIR="$UV_PROJECT_DIR" \
    AUTOPAPER_CLI="$AUTOPAPER_CLI" \
    "$SETUP_SCRIPT" status
}

main() {
    case "${1:-}" in
        -h|--help|help)
            show_help
            exit 0
            ;;
        "")
            ;;
        *)
            print_error "未知参数: $1"
            show_help
            exit 1
            ;;
    esac

    require_project
    ensure_env_file

    print_banner
    print_kv "项目目录" "$PROJECT_DIR"
    print_kv "配置目录" "$CONFIG_DIR"
    print_kv ".env" "$ENV_FILE"
    if [ -n "$UV_BIN" ]; then
        print_kv "uv" "$UV_BIN"
    fi
    if [ -n "$UV_PROJECT_DIR" ]; then
        print_kv "uv 项目" "$UV_PROJECT_DIR"
    fi

    configure_env
    configure_all_yaml
    run_checks
    configure_cron

    echo ""
    rule
    print_success "AutoPaper 项目配置完成"
    echo ""
    echo "完整同步命令:"
    print_command "uv run autopaper --env-file \"$ENV_FILE\" sync --config all --config-dir \"$CONFIG_DIR\""
    echo "查看定时任务:"
    print_command "\"$SETUP_SCRIPT\" status"
    rule
}

main "$@"
