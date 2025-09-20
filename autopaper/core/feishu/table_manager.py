"""
配置驱动的表格管理器

根据配置文件自动创建和管理对应的飞书多维表格。
"""

import logging
from typing import Dict, List, Any, Optional
from .config import FeishuConfig
from .bitable import BitableManager

logger = logging.getLogger(__name__)


class ConfigBasedTableManager:
    """基于配置的表格管理器"""

    def __init__(self, config: FeishuConfig):
        """
        初始化配置驱动的表格管理器

        Args:
            config: 飞书配置对象
        """
        self.config = config
        self.bitable_manager = BitableManager(config)
        self.created_tables = {}  # 存储已创建的表格信息 {领域名: table_id}

    def create_tables_from_config(self, cfg) -> Dict[str, str]:
        """根据配置文件创建所有必要的表格

        Args:
            cfg: Hydra配置对象

        Returns:
            表格映射字典 {领域名称: table_id}
        """
        logger.info("🏗️ 开始根据配置创建表格...")

        table_mapping = {}

        # 获取用户配置信息
        user_profile = cfg.get("user_profile", {})
        research_area = user_profile.get("research_area", "general")
        user_name = user_profile.get("name", "通用研究员")

        # 生成表格名称
        display_name = user_name.replace("研究员", "")
        table_name = f"{display_name}论文表"

        logger.info(f"📋 为研究领域 '{research_area}' 创建表格: {table_name}")

        try:
            # 检查表格是否已存在
            existing_table_id = self.bitable_manager.find_table_by_name(table_name)

            if existing_table_id:
                logger.info(f"📋 表格已存在: {table_name} (ID: {existing_table_id})")
                table_mapping[research_area] = existing_table_id
                self.created_tables[research_area] = existing_table_id
            else:
                # 创建新表格
                logger.info(f"🆕 创建新表格: {table_name}")
                result = self.bitable_manager.create_domain_papers_table(table_name, research_area)

                table_id = result.get("table_id")
                if table_id:
                    logger.info(f"✅ 成功创建表格: {table_name} (ID: {table_id})")
                    table_mapping[research_area] = table_id
                    self.created_tables[research_area] = table_id
                else:
                    logger.error(f"❌ 创建表格失败: {table_name}")

        except Exception as e:
            logger.error(f"❌ 创建表格 {table_name} 时发生错误: {e}")

        logger.info(f"🏁 表格创建完成，共 {len(table_mapping)} 个表格")
        return table_mapping

    def _generate_table_name(self, area_name: str, area_config: Dict[str, Any]) -> str:
        """生成表格名称

        Args:
            area_name: 研究领域名称
            area_config: 领域配置

        Returns:
            生成的表格名称
        """
        # 使用配置中的自定义表格名称，或生成默认名称
        custom_name = area_config.get("table_name")
        if custom_name:
            return custom_name

        # 生成默认表格名称
        display_name = area_config.get("display_name", area_name)
        return f"{display_name}论文表"

    def get_table_links(self, table_mapping: Dict[str, str] = None) -> Dict[str, str]:
        """生成表格访问链接

        Args:
            table_mapping: 表格映射字典，如果为None则使用内部存储的映射

        Returns:
            表格链接映射 {领域名称: 表格链接}
        """
        if table_mapping is None:
            table_mapping = self.created_tables

        links = {}

        for area_name, table_id in table_mapping.items():
            link = self._generate_table_link(table_id)
            if link:
                links[area_name] = link

        return links

    def _generate_table_link(self, table_id: str) -> Optional[str]:
        """生成单个表格的访问链接

        Args:
            table_id: 表格ID

        Returns:
            表格访问链接
        """
        try:
            app_token = self.config.app_token
            if not app_token:
                logger.warning("⚠️ 未配置app_token，无法生成表格链接")
                return None

            # 生成飞书多维表格访问链接
            return f"https://feishu.cn/base/{app_token}?table={table_id}&view=vew"

        except Exception as e:
            logger.warning(f"⚠️ 生成表格链接失败: {e}")
            return None

    def update_table_config(self, cfg, table_mapping: Dict[str, str] = None) -> Dict[str, Any]:
        """更新配置中的表格信息

        Args:
            cfg: Hydra配置对象
            table_mapping: 表格映射字典

        Returns:
            更新后的表格统计信息
        """
        if table_mapping is None:
            table_mapping = self.created_tables

        updated_stats = {}

        for area_name, table_id in table_mapping.items():
            try:
                # 获取表格记录数量
                record_count = self.bitable_manager.get_record_count(table_id)

                # 获取表格信息
                table_info = self.bitable_manager.get_table_info(table_id)
                table_name = table_info.get("name", f"{area_name}论文表")

                updated_stats[area_name] = {
                    "table_id": table_id,
                    "table_name": table_name,
                    "total_count": record_count,
                    "new_count": 0,  # 这个需要在同步时更新
                }

                logger.debug(f"📊 {area_name}: {table_name} ({record_count} 条记录)")

            except Exception as e:
                logger.warning(f"⚠️ 获取表格 {area_name} 信息失败: {e}")
                updated_stats[area_name] = {
                    "table_id": table_id,
                    "table_name": f"{area_name}论文表",
                    "total_count": 0,
                    "new_count": 0,
                }

        return updated_stats

    def validate_table_structure(self, table_id: str, required_fields: List[str] = None) -> bool:
        """验证表格结构是否符合要求

        Args:
            table_id: 表格ID
            required_fields: 必需的字段列表

        Returns:
            表格结构是否有效
        """
        if required_fields is None:
            required_fields = ["ArXiv ID", "标题", "作者", "摘要", "分类", "相关性评分", "PDF链接", "发布日期"]

        try:
            fields = self.bitable_manager.get_table_fields(table_id)
            existing_fields = [field.get("field_name", "") for field in fields]

            missing_fields = []
            for required_field in required_fields:
                if required_field not in existing_fields:
                    missing_fields.append(required_field)

            if missing_fields:
                logger.warning(f"⚠️ 表格缺少必需字段: {missing_fields}")
                return False

            return True

        except Exception as e:
            logger.error(f"❌ 验证表格结构失败: {e}")
            return False

    def get_table_summary(self) -> Dict[str, Any]:
        """获取所有已创建表格的摘要信息

        Returns:
            表格摘要信息
        """
        summary = {
            "total_tables": len(self.created_tables),
            "tables": {},
            "app_token": self.config.app_token[:10] + "..." if self.config.app_token else None,
        }

        for area_name, table_id in self.created_tables.items():
            try:
                table_info = self.bitable_manager.get_table_info(table_id)
                record_count = self.bitable_manager.get_record_count(table_id)

                summary["tables"][area_name] = {
                    "table_id": table_id,
                    "table_name": table_info.get("name", "未知"),
                    "record_count": record_count,
                    "table_link": self._generate_table_link(table_id),
                }

            except Exception as e:
                logger.warning(f"⚠️ 获取表格 {area_name} 摘要失败: {e}")
                summary["tables"][area_name] = {
                    "table_id": table_id,
                    "table_name": f"{area_name}论文表",
                    "record_count": 0,
                    "table_link": None,
                    "error": str(e),
                }

        return summary

    def cleanup_empty_tables(self, min_records: int = 0) -> List[str]:
        """清理空表格或记录数少于指定数量的表格

        Args:
            min_records: 最少记录数阈值

        Returns:
            清理的表格列表
        """
        cleaned_tables = []

        for area_name, table_id in list(self.created_tables.items()):
            try:
                record_count = self.bitable_manager.get_record_count(table_id)

                if record_count <= min_records:
                    logger.info(f"🧹 清理表格: {area_name} (记录数: {record_count})")
                    # 注意：这里不实际删除表格，只是从跟踪列表中移除
                    # 实际删除需要通过飞书界面操作
                    del self.created_tables[area_name]
                    cleaned_tables.append(area_name)

            except Exception as e:
                logger.warning(f"⚠️ 检查表格 {area_name} 时出错: {e}")

        if cleaned_tables:
            logger.info(f"🧹 已清理 {len(cleaned_tables)} 个表格: {cleaned_tables}")
        else:
            logger.info("✅ 无需清理表格")

        return cleaned_tables


def create_table_manager_from_config(cfg) -> ConfigBasedTableManager:
    """从配置创建表格管理器

    Args:
        cfg: Hydra配置对象

    Returns:
        配置驱动的表格管理器
    """
    from .config import FeishuConfig

    feishu_config = FeishuConfig.from_hydra_config(cfg)
    return ConfigBasedTableManager(feishu_config)
