#!/usr/bin/env python3
"""
ArXiv 论文同步系统 - 统一工具管理器

这个脚本整合了所有管理功能，包括：
- 定时同步脚本
- 健康检查
- 环境设置
- Docker 管理
- 系统维护

使用方法:
    python tools/manager.py <command> [options]

支持的命令:
    sync         - 执行同步
    schedule     - 定时同步
    health       - 健康检查
    setup        - 环境设置
    docker       - Docker 管理
    backup       - 数据备份
    clean        - 清理环境
"""

import os
import sys
import argparse
import subprocess
import shutil
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import yaml
import logging


class ArxivSyncManager:
    """ArXiv 同步系统管理器"""

    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.setup_logging()

    def setup_logging(self):
        """设置日志"""
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)

        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler(log_dir / 'manager.log', encoding='utf-8'),
            ],
        )
        self.logger = logging.getLogger(__name__)

    def sync_all(self, dry_run: bool = False, days: int = None) -> bool:
        """执行批量同步"""
        try:
            cmd = [sys.executable, str(self.project_root / "arxiv_hydra.py"), "--config-name=all"]

            self.logger.info("🚀 开始执行批量同步...")

            if dry_run:
                self.logger.info("🔍 模拟运行模式")
                return True

            result = subprocess.run(cmd, cwd=self.project_root, capture_output=False, text=True)

            if result.returncode == 0:
                self.logger.info("✅ 批量同步执行成功")
                return True
            else:
                self.logger.error("❌ 批量同步执行失败")
                return False

        except Exception as e:
            self.logger.error(f"❌ 同步过程中发生异常: {e}")
            return False

    def schedule_sync(self, days: int = 1, dry_run: bool = False, backup: bool = True) -> bool:
        """定时同步（带配置管理）"""
        try:
            from scripts.scheduled_sync import ScheduledSyncManager

            manager = ScheduledSyncManager(days=days, dry_run=dry_run, backup=backup)
            return manager.run()

        except ImportError:
            self.logger.warning("⚠️ scheduled_sync 模块不可用，使用简化同步")
            return self.sync_all(dry_run=dry_run)
        except Exception as e:
            self.logger.error(f"❌ 定时同步失败: {e}")
            return False

    def health_check(self) -> bool:
        """健康检查"""
        try:
            from scripts.health_check import main as health_main

            self.logger.info("🔍 开始健康检查...")
            health_main()
            return True

        except ImportError:
            return self._basic_health_check()
        except SystemExit as e:
            return e.code == 0
        except Exception as e:
            self.logger.error(f"❌ 健康检查失败: {e}")
            return False

    def _basic_health_check(self) -> bool:
        """基础健康检查"""
        checks_passed = 0
        total_checks = 4

        # 检查 Python 环境
        try:
            import yaml, requests, omegaconf

            self.logger.info("✅ Python 环境检查通过")
            checks_passed += 1
        except ImportError as e:
            self.logger.error(f"❌ Python 依赖检查失败: {e}")

        # 检查配置文件
        config_dir = self.project_root / "conf"
        if config_dir.exists() and list(config_dir.glob("sync*.yaml")):
            self.logger.info(f"✅ 找到配置文件")
            checks_passed += 1
        else:
            self.logger.error("❌ 未找到配置文件")

        # 检查环境变量
        required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_BITABLE_APP_TOKEN']
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if not missing_vars:
            self.logger.info("✅ 环境变量检查通过")
            checks_passed += 1
        else:
            self.logger.error(f"❌ 缺少环境变量: {', '.join(missing_vars)}")

        # 检查目录结构
        required_dirs = ['logs', 'backup', 'downloads']
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            dir_path.mkdir(exist_ok=True)

        self.logger.info("✅ 目录结构检查通过")
        checks_passed += 1

        success = checks_passed == total_checks
        if success:
            self.logger.info(f"🎉 健康检查通过 ({checks_passed}/{total_checks})")
        else:
            self.logger.error(f"⚠️ 健康检查部分失败 ({checks_passed}/{total_checks})")

        return success

    def setup_environment(self) -> bool:
        """环境设置"""
        try:
            self.logger.info("🔧 开始环境设置...")

            # 创建必要目录
            for dir_name in ['logs', 'backup', 'downloads']:
                dir_path = self.project_root / dir_name
                dir_path.mkdir(exist_ok=True)
                self.logger.info(f"📁 创建目录: {dir_name}")

            # 复制环境变量模板
            env_template = self.project_root / ".env.template"
            env_file = self.project_root / ".env"

            if env_template.exists() and not env_file.exists():
                shutil.copy2(env_template, env_file)
                self.logger.info("📄 已创建 .env 文件，请编辑其中的配置")
            elif env_file.exists():
                self.logger.info("📄 .env 文件已存在")
            else:
                self.logger.warning("⚠️ 未找到 .env.template 文件")

            self.logger.info("✅ 环境设置完成")
            return True

        except Exception as e:
            self.logger.error(f"❌ 环境设置失败: {e}")
            return False

    def docker_manage(self, action: str) -> bool:
        """Docker 管理"""
        docker_commands = {
            'up': ['docker-compose', 'up', '-d'],
            'down': ['docker-compose', 'down'],
            'build': ['docker-compose', 'build', '--no-cache'],
            'logs': ['docker-compose', 'logs', '-f'],
            'ps': ['docker-compose', 'ps'],
            'restart': ['docker-compose', 'restart'],
        }

        if action not in docker_commands:
            self.logger.error(f"❌ 不支持的 Docker 操作: {action}")
            return False

        try:
            cmd = docker_commands[action]
            self.logger.info(f"🐳 执行 Docker 命令: {' '.join(cmd)}")

            result = subprocess.run(cmd, cwd=self.project_root, capture_output=(action != 'logs'))

            if result.returncode == 0:
                self.logger.info(f"✅ Docker {action} 执行成功")
                return True
            else:
                self.logger.error(f"❌ Docker {action} 执行失败")
                return False

        except FileNotFoundError:
            self.logger.error("❌ 未找到 docker-compose 命令")
            return False
        except Exception as e:
            self.logger.error(f"❌ Docker 操作失败: {e}")
            return False

    def backup_data(self) -> bool:
        """备份数据"""
        try:
            backup_dir = self.project_root / "backups"
            backup_dir.mkdir(exist_ok=True)

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_file = backup_dir / f"arxiv_sync_backup_{timestamp}.tar.gz"

            # 要备份的目录和文件
            backup_items = ['logs', 'backup', 'downloads', '.env']
            existing_items = [item for item in backup_items if (self.project_root / item).exists()]

            if not existing_items:
                self.logger.warning("⚠️ 没有找到需要备份的文件")
                return False

            # 使用 tar 命令备份（如果可用）
            try:
                import tarfile

                with tarfile.open(backup_file, 'w:gz') as tar:
                    for item in existing_items:
                        item_path = self.project_root / item
                        tar.add(item_path, arcname=item)

                self.logger.info(f"✅ 备份完成: {backup_file}")
                return True

            except Exception as e:
                self.logger.error(f"❌ 备份失败: {e}")
                return False

        except Exception as e:
            self.logger.error(f"❌ 备份过程失败: {e}")
            return False

    def clean_environment(self, deep: bool = False) -> bool:
        """清理环境"""
        try:
            self.logger.info("🧹 开始清理环境...")

            # 清理临时文件
            temp_patterns = ['*.pyc', '*.pyo', '*.pyd', '__pycache__']
            cleaned_count = 0

            for pattern in temp_patterns:
                for file_path in self.project_root.rglob(pattern):
                    try:
                        if file_path.is_file():
                            file_path.unlink()
                        elif file_path.is_dir():
                            shutil.rmtree(file_path)
                        cleaned_count += 1
                    except Exception:
                        pass

            # 清理旧日志文件（保留最近7天）
            logs_dir = self.project_root / "logs"
            if logs_dir.exists():
                cutoff_date = datetime.now() - timedelta(days=7)
                for log_file in logs_dir.glob("*.log"):
                    if log_file.stat().st_mtime < cutoff_date.timestamp():
                        try:
                            log_file.unlink()
                            cleaned_count += 1
                        except Exception:
                            pass

            if deep:
                # 深度清理：删除所有生成的文件
                deep_clean_dirs = ['outputs', 'downloads', '__pycache__']
                for dir_name in deep_clean_dirs:
                    dir_path = self.project_root / dir_name
                    if dir_path.exists():
                        shutil.rmtree(dir_path)
                        cleaned_count += 1

            self.logger.info(f"✅ 清理完成，清理了 {cleaned_count} 个项目")
            return True

        except Exception as e:
            self.logger.error(f"❌ 清理失败: {e}")
            return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='ArXiv 论文同步系统管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  %(prog)s sync                    # 执行批量同步
  %(prog)s sync --dry-run          # 模拟同步
  %(prog)s schedule --days 7       # 7天周期定时同步
  %(prog)s health                  # 健康检查
  %(prog)s setup                   # 环境设置
  %(prog)s docker up               # 启动 Docker 服务
  %(prog)s backup                  # 备份数据
  %(prog)s clean                   # 清理环境
        """,
    )

    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # sync 命令
    sync_parser = subparsers.add_parser('sync', help='执行同步')
    sync_parser.add_argument('--dry-run', action='store_true', help='模拟运行')

    # schedule 命令
    schedule_parser = subparsers.add_parser('schedule', help='定时同步')
    schedule_parser.add_argument('--days', type=int, default=1, help='同步周期天数')
    schedule_parser.add_argument('--dry-run', action='store_true', help='模拟运行')
    schedule_parser.add_argument('--no-backup', action='store_true', help='不备份配置')

    # health 命令
    subparsers.add_parser('health', help='健康检查')

    # setup 命令
    subparsers.add_parser('setup', help='环境设置')

    # docker 命令
    docker_parser = subparsers.add_parser('docker', help='Docker 管理')
    docker_parser.add_argument('action', choices=['up', 'down', 'build', 'logs', 'ps', 'restart'], help='Docker 操作')

    # backup 命令
    subparsers.add_parser('backup', help='备份数据')

    # clean 命令
    clean_parser = subparsers.add_parser('clean', help='清理环境')
    clean_parser.add_argument('--deep', action='store_true', help='深度清理')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    manager = ArxivSyncManager()
    success = False

    try:
        if args.command == 'sync':
            success = manager.sync_all(dry_run=args.dry_run)
        elif args.command == 'schedule':
            success = manager.schedule_sync(days=args.days, dry_run=args.dry_run, backup=not args.no_backup)
        elif args.command == 'health':
            success = manager.health_check()
        elif args.command == 'setup':
            success = manager.setup_environment()
        elif args.command == 'docker':
            success = manager.docker_manage(args.action)
        elif args.command == 'backup':
            success = manager.backup_data()
        elif args.command == 'clean':
            success = manager.clean_environment(deep=args.deep)

    except KeyboardInterrupt:
        print("\n⚠️ 操作被用户中断")
        success = False
    except Exception as e:
        print(f"❌ 操作失败: {e}")
        success = False

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
