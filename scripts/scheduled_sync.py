#!/usr/bin/env python3
"""
定时全部同步脚本

这个脚本会：
1. 自动检测所有sync*.yaml配置文件
2. 临时修改每个配置的search.days为指定的周期天数
3. 运行批量同步
4. 恢复原始配置

使用方法:
    python scripts/scheduled_sync.py                    # 使用默认1天周期
    python scripts/scheduled_sync.py --days 7           # 使用7天周期
    python scripts/scheduled_sync.py --config           # 显示当前配置
    python scripts/scheduled_sync.py --dry-run          # 模拟运行，不实际执行

环境变量:
    SYNC_DAYS: 默认同步天数（默认: 1）
    LOG_LEVEL: 日志级别（默认: INFO）
    BACKUP_CONFIGS: 是否备份配置文件（默认: true）
"""

import os
import sys
import argparse
import shutil
import tempfile
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any
import yaml
import logging


# 配置日志
def setup_logging(level: str = "INFO"):
    """设置日志配置"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stdout), logging.FileHandler('logs/scheduled_sync.log', encoding='utf-8')],
    )
    return logging.getLogger(__name__)


class ScheduledSyncManager:
    """定时同步管理器"""

    def __init__(self, days: int = 1, dry_run: bool = False, backup: bool = True):
        self.days = days
        self.dry_run = dry_run
        self.backup = backup
        self.project_root = Path(__file__).parent.parent
        self.conf_dir = self.project_root / "conf"
        self.backup_dir = self.project_root / "backup" / f"configs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # 确保日志目录存在
        log_dir = self.project_root / "logs"
        log_dir.mkdir(exist_ok=True)

        self.logger = setup_logging(os.getenv('LOG_LEVEL', 'INFO'))

    def find_sync_configs(self) -> List[Path]:
        """查找所有sync配置文件"""
        sync_configs = list(self.conf_dir.glob("sync*.yaml"))
        self.logger.info(f"发现 {len(sync_configs)} 个同步配置文件:")
        for config in sync_configs:
            self.logger.info(f"  - {config.name}")
        return sync_configs

    def backup_configs(self, config_files: List[Path]) -> bool:
        """备份配置文件"""
        if not self.backup:
            return True

        try:
            self.backup_dir.mkdir(parents=True, exist_ok=True)

            for config_file in config_files:
                backup_file = self.backup_dir / config_file.name
                shutil.copy2(config_file, backup_file)
                self.logger.debug(f"已备份: {config_file.name} -> {backup_file}")

            self.logger.info(f"✅ 配置文件已备份到: {self.backup_dir}")
            return True

        except Exception as e:
            self.logger.error(f"❌ 备份配置文件失败: {e}")
            return False

    def modify_config_days(self, config_file: Path, days: int) -> Dict[str, Any]:
        """修改配置文件的search.days参数，返回原始配置"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 保存原始值
            original_days = config.get('search', {}).get('days', 7)

            # 修改天数
            if 'search' not in config:
                config['search'] = {}
            config['search']['days'] = days

            # 写回文件
            if not self.dry_run:
                with open(config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            self.logger.debug(f"修改 {config_file.name}: days {original_days} -> {days}")
            return {'original_days': original_days, 'config': config}

        except Exception as e:
            self.logger.error(f"❌ 修改配置文件 {config_file.name} 失败: {e}")
            raise

    def restore_config_days(self, config_file: Path, original_days: int) -> bool:
        """恢复配置文件的原始search.days参数"""
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # 恢复原始值
            if 'search' not in config:
                config['search'] = {}
            config['search']['days'] = original_days

            # 写回文件
            if not self.dry_run:
                with open(config_file, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            self.logger.debug(f"恢复 {config_file.name}: days -> {original_days}")
            return True

        except Exception as e:
            self.logger.error(f"❌ 恢复配置文件 {config_file.name} 失败: {e}")
            return False

    def run_batch_sync(self) -> bool:
        """运行批量同步"""
        try:
            cmd = [sys.executable, str(self.project_root / "arxiv_hydra.py"), "--config-name=all"]

            self.logger.info(f"🚀 开始执行批量同步...")
            self.logger.debug(f"执行命令: {' '.join(cmd)}")

            if self.dry_run:
                self.logger.info("🔍 模拟运行模式，跳过实际执行")
                return True

            # 切换到项目根目录执行
            result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True, encoding='utf-8')

            if result.returncode == 0:
                self.logger.info("✅ 批量同步执行成功")
                self.logger.debug(f"输出: {result.stdout}")
                return True
            else:
                self.logger.error(f"❌ 批量同步执行失败 (退出码: {result.returncode})")
                self.logger.error(f"错误输出: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"❌ 执行批量同步时发生异常: {e}")
            return False

    def run(self) -> bool:
        """执行完整的定时同步流程"""
        start_time = datetime.now()
        self.logger.info("=" * 80)
        self.logger.info(f"🕒 定时同步开始 - {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"📅 同步周期: {self.days} 天")
        self.logger.info(f"🔍 模拟运行: {'是' if self.dry_run else '否'}")
        self.logger.info(f"💾 备份配置: {'是' if self.backup else '否'}")
        self.logger.info("=" * 80)

        success = False
        config_files = []
        original_configs = {}

        try:
            # 1. 查找配置文件
            config_files = self.find_sync_configs()
            if not config_files:
                self.logger.warning("⚠️ 未找到任何sync配置文件")
                return False

            # 2. 备份配置文件
            if not self.backup_configs(config_files):
                return False

            # 3. 修改配置文件的天数
            self.logger.info(f"🔧 修改配置文件天数为 {self.days} 天...")
            for config_file in config_files:
                original_config = self.modify_config_days(config_file, self.days)
                original_configs[config_file] = original_config['original_days']

            # 4. 执行批量同步
            success = self.run_batch_sync()

        except Exception as e:
            self.logger.error(f"❌ 定时同步过程中发生异常: {e}")
            success = False

        finally:
            # 5. 恢复配置文件
            if original_configs and not self.dry_run:
                self.logger.info("🔄 恢复配置文件原始天数...")
                for config_file, original_days in original_configs.items():
                    self.restore_config_days(config_file, original_days)

        # 6. 输出结果
        end_time = datetime.now()
        duration = end_time - start_time

        self.logger.info("=" * 80)
        if success:
            self.logger.info("✅ 定时同步完成!")
        else:
            self.logger.error("❌ 定时同步失败!")

        self.logger.info(f"⏱️  总耗时: {duration}")
        self.logger.info(f"🕒 结束时间: {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info("=" * 80)

        return success


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='ArXiv论文定时同步脚本',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s                     # 使用默认1天周期
  %(prog)s --days 7            # 使用7天周期
  %(prog)s --config            # 显示当前配置
  %(prog)s --dry-run           # 模拟运行
  %(prog)s --days 3 --dry-run  # 模拟使用3天周期运行
        """,
    )

    parser.add_argument(
        '--days', '-d', type=int, default=int(os.getenv('SYNC_DAYS', '1')), help='同步周期天数 (默认: 1天)'
    )

    parser.add_argument('--dry-run', '-n', action='store_true', help='模拟运行，不实际执行同步')

    parser.add_argument('--no-backup', action='store_true', help='不备份配置文件')

    parser.add_argument('--config', '-c', action='store_true', help='显示当前配置信息')

    parser.add_argument(
        '--log-level',
        '-l',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default=os.getenv('LOG_LEVEL', 'INFO'),
        help='日志级别 (默认: INFO)',
    )

    args = parser.parse_args()

    # 设置日志级别
    os.environ['LOG_LEVEL'] = args.log_level

    if args.config:
        print("📋 当前配置:")
        print(f"  同步周期: {args.days} 天")
        print(f"  模拟运行: {'是' if args.dry_run else '否'}")
        print(f"  备份配置: {'否' if args.no_backup else '是'}")
        print(f"  日志级别: {args.log_level}")
        return

    # 验证参数
    if args.days <= 0:
        print("❌ 错误: 同步周期天数必须大于0")
        sys.exit(1)

    # 创建同步管理器并运行
    manager = ScheduledSyncManager(days=args.days, dry_run=args.dry_run, backup=not args.no_backup)

    success = manager.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
