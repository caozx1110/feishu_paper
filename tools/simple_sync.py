#!/usr/bin/env python3
"""
简化版定时同步脚本

直接运行 python arxiv_hydra.py --config-name=all
适用于 Docker 容器和 cron 定时任务

使用方法:
    python scripts/simple_sync.py

环境变量:
    SYNC_INTERVAL: 同步间隔（秒），默认86400（1天）
    LOG_LEVEL: 日志级别，默认INFO
"""

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path


def main():
    """简化版同步主函数"""
    project_root = Path(__file__).parent.parent

    # 设置默认值
    sync_interval = int(os.getenv('SYNC_INTERVAL', '86400'))  # 默认1天
    log_level = os.getenv('LOG_LEVEL', 'INFO')

    # 记录开始时间
    start_time = datetime.now()
    print(f"🕒 {start_time.strftime('%Y-%m-%d %H:%M:%S')} - 开始定时同步...")
    print(f"📅 同步间隔: {sync_interval} 秒")

    try:
        # 执行同步
        cmd = [sys.executable, str(project_root / "arxiv_hydra.py"), "--config-name=all"]

        result = subprocess.run(cmd, cwd=project_root, capture_output=False, text=True)  # 直接输出到控制台

        # 记录结果
        end_time = datetime.now()
        if result.returncode == 0:
            print(f"✅ {end_time.strftime('%Y-%m-%d %H:%M:%S')} - 同步完成")
            print(f"⏱️  耗时: {end_time - start_time}")
        else:
            print(f"❌ {end_time.strftime('%Y-%m-%d %H:%M:%S')} - 同步失败")
            print(f"⏱️  耗时: {end_time - start_time}")
            sys.exit(1)

    except Exception as e:
        end_time = datetime.now()
        print(f"❌ {end_time.strftime('%Y-%m-%d %H:%M:%S')} - 同步异常: {e}")
        print(f"⏱️  耗时: {end_time - start_time}")
        sys.exit(1)


if __name__ == "__main__":
    main()
