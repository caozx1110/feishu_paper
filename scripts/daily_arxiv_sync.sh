#!/bin/bash
#
# ArXiv论文定时采集脚本
# 每天上午10点（中国时间）自动运行论文采集
#
# 作者: GitHub Copilot
# 创建时间: 2025-10-23
#

# 设置脚本路径
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

# 设置日志文件
LOG_DIR="$PROJECT_DIR/logs"
LOG_FILE="$LOG_DIR/daily_sync_$(date +%Y%m%d).log"

# 创建日志目录
mkdir -p "$LOG_DIR"

# 记录开始时间
echo "===========================================" >> "$LOG_FILE"
echo "🕒 $(date '+%Y-%m-%d %H:%M:%S CST') - 开始每日定时同步" >> "$LOG_FILE"
echo "📂 项目目录: $PROJECT_DIR" >> "$LOG_FILE"
echo "===========================================" >> "$LOG_FILE"

# 切换到项目目录
cd "$PROJECT_DIR" || {
    echo "❌ 无法切换到项目目录: $PROJECT_DIR" >> "$LOG_FILE"
    exit 1
}

# 初始化conda环境
if [ -f "/opt/miniconda3/etc/profile.d/conda.sh" ]; then
    echo "🐍 初始化conda环境..." >> "$LOG_FILE"
    source /opt/miniconda3/etc/profile.d/conda.sh
    conda activate base
    echo "✅ conda base环境已激活" >> "$LOG_FILE"
elif [ -f "$HOME/miniconda3/etc/profile.d/conda.sh" ]; then
    echo "🐍 初始化conda环境..." >> "$LOG_FILE"
    source "$HOME/miniconda3/etc/profile.d/conda.sh"
    conda activate base
    echo "✅ conda base环境已激活" >> "$LOG_FILE"
elif [ -f "$HOME/anaconda3/etc/profile.d/conda.sh" ]; then
    echo "🐍 初始化conda环境..." >> "$LOG_FILE"
    source "$HOME/anaconda3/etc/profile.d/conda.sh"
    conda activate base
    echo "✅ conda base环境已激活" >> "$LOG_FILE"
else
    echo "⚠️  未找到conda环境，尝试使用系统Python" >> "$LOG_FILE"
fi

# 备用：激活Python虚拟环境（如果存在）
if [ -f "venv/bin/activate" ]; then
    echo "🐍 激活Python虚拟环境..." >> "$LOG_FILE"
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo "🐍 激活Python虚拟环境..." >> "$LOG_FILE"
    source .venv/bin/activate
fi

# 检查Python和必要文件
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 未找到" >> "$LOG_FILE"
    exit 1
fi

if [ ! -f "arxiv_hydra.py" ]; then
    echo "❌ arxiv_hydra.py 文件未找到" >> "$LOG_FILE"
    exit 1
fi

if [ ! -f "conf/all.yaml" ]; then
    echo "❌ conf/all.yaml 配置文件未找到" >> "$LOG_FILE"
    exit 1
fi

# 执行论文采集
echo "🚀 开始执行论文采集..." >> "$LOG_FILE"
echo "📝 命令: python3 arxiv_hydra.py --config-name=all" >> "$LOG_FILE"

# 执行命令并记录输出
python3 arxiv_hydra.py --config-name=all >> "$LOG_FILE" 2>&1
EXIT_CODE=$?

# 记录结果
echo "===========================================" >> "$LOG_FILE"
if [ $EXIT_CODE -eq 0 ]; then
    echo "✅ $(date '+%Y-%m-%d %H:%M:%S CST') - 定时同步成功完成" >> "$LOG_FILE"
else
    echo "❌ $(date '+%Y-%m-%d %H:%M:%S CST') - 定时同步失败，退出码: $EXIT_CODE" >> "$LOG_FILE"
fi
echo "===========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# 清理旧日志文件（保留最近30天）
find "$LOG_DIR" -name "daily_sync_*.log" -type f -mtime +30 -delete 2>/dev/null

# 发送通知（可选）
if [ $EXIT_CODE -eq 0 ]; then
    echo "ArXiv论文采集任务已成功完成 - $(date '+%Y-%m-%d %H:%M:%S')"
else
    echo "ArXiv论文采集任务失败 - $(date '+%Y-%m-%d %H:%M:%S') - 退出码: $EXIT_CODE"
fi

exit $EXIT_CODE
