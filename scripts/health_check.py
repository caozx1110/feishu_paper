#!/usr/bin/env python3
"""
健康检查脚本

用于 Docker 容器健康检查，验证系统是否正常运行
"""

import sys
import os
import subprocess
from pathlib import Path


def check_python_env():
    """检查 Python 环境"""
    try:
        import yaml
        import requests
        import omegaconf

        return True
    except ImportError as e:
        print(f"❌ Python 依赖检查失败: {e}")
        return False


def check_config_files():
    """检查配置文件"""
    config_dir = Path("/app/conf")
    if not config_dir.exists():
        print("❌ 配置目录不存在")
        return False

    sync_configs = list(config_dir.glob("sync*.yaml"))
    if not sync_configs:
        print("❌ 未找到同步配置文件")
        return False

    print(f"✅ 找到 {len(sync_configs)} 个配置文件")
    return True


def check_env_vars():
    """检查必要的环境变量"""
    required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_BITABLE_APP_TOKEN']

    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)

    if missing_vars:
        print(f"❌ 缺少环境变量: {', '.join(missing_vars)}")
        return False

    print("✅ 环境变量检查通过")
    return True


def check_cron_service():
    """检查 cron 服务状态"""
    try:
        result = subprocess.run(['service', 'cron', 'status'], capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ Cron 服务运行正常")
            return True
        else:
            print("❌ Cron 服务未运行")
            return False
    except Exception as e:
        print(f"❌ 检查 Cron 服务失败: {e}")
        return False


def main():
    """主健康检查函数"""
    print("🔍 开始健康检查...")

    checks = [
        ("Python 环境", check_python_env),
        ("配置文件", check_config_files),
        ("环境变量", check_env_vars),
        ("Cron 服务", check_cron_service),
    ]

    all_passed = True
    for name, check_func in checks:
        print(f"\n📋 检查 {name}...")
        if not check_func():
            all_passed = False

    if all_passed:
        print("\n✅ 所有健康检查通过")
        sys.exit(0)
    else:
        print("\n❌ 健康检查失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
