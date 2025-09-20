"""
飞书数据同步管理器

整合多维表格和聊天通知功能，提供统一的数据同步接口。
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from .config import FeishuConfig
from .bitable import BitableManager
from .notification import ChatNotifier, ChatNotificationConfig
from .table_manager import ConfigBasedTableManager

logger = logging.getLogger(__name__)


class SyncManager:
    """飞书数据同步管理器"""

    def __init__(self, config: FeishuConfig, notification_config: ChatNotificationConfig = None):
        """
        初始化同步管理器

        Args:
            config: 飞书配置对象
            notification_config: 通知配置
        """
        self.config = config
        self.bitable_manager = BitableManager(config)
        self.chat_notifier = ChatNotifier(config, notification_config)

        logger.info("🔄 飞书同步管理器已初始化")

    def refresh_token_before_sync(self) -> bool:
        """在同步前刷新token以确保有效性

        Returns:
            bool: 是否成功刷新token
        """
        try:
            logger.info("🔄 检查并刷新飞书访问token...")
            # 强制获取新的token
            new_token = self.bitable_manager.connector.get_tenant_access_token()
            if new_token:
                logger.info(f"✅ Token刷新成功: {new_token[:20]}...")
                return True
            else:
                logger.error("❌ Token刷新失败")
                return False
        except Exception as e:
            logger.error(f"❌ Token刷新异常: {e}")
            return False

    def sync_papers_with_config(
        self,
        papers: List[Dict[str, Any]],
        cfg,
        enable_notification: bool = True,
    ) -> Dict[str, Any]:
        """根据配置文件同步论文到对应表格

        Args:
            papers: 论文列表
            cfg: Hydra配置对象
            enable_notification: 是否启用通知

        Returns:
            同步结果统计
        """
        logger.info(f"🚀 开始根据配置同步论文数据，共 {len(papers)} 篇论文")

        # 在同步前刷新token以确保有效性
        if not self.refresh_token_before_sync():
            logger.error("❌ Token刷新失败，同步终止")
            return {"success": False, "error": "Token刷新失败"}

        # 创建表格管理器
        table_manager = ConfigBasedTableManager(self.config)

        # 根据配置创建表格
        table_mapping = table_manager.create_tables_from_config(cfg)

        if not table_mapping:
            logger.warning("⚠️ 没有创建任何表格，同步终止")
            return {"synced_count": 0, "total_count": 0, "tables": {}}

        # 生成表格链接
        table_links = table_manager.get_table_links(table_mapping)

        # 获取研究领域信息
        user_profile = cfg.get("user_profile", {})
        research_area = user_profile.get("research_area", "general")
        table_id = list(table_mapping.values())[0]  # 获取第一个(也是唯一的)表格ID

        # 同步论文数据
        sync_result = self._sync_papers_to_table(papers, table_id, research_area)

        # 构建统计信息
        sync_stats = {
            research_area: {
                "table_id": table_id,
                "table_name": sync_result.get("table_name", f"{research_area}论文表"),
                "new_count": sync_result.get("synced_count", 0),
                "total_count": sync_result.get("total_count", 0),
            }
        }

        total_synced = sync_result.get("synced_count", 0)
        total_papers = sync_result.get("total_count", 0)

        logger.info(f"📊 同步完成：新增 {total_synced} 篇，总计 {total_papers} 篇")

        # 发送通知
        if enable_notification and total_synced > 0:
            logger.info("📢 发送群聊通知...")
            # 构建按领域分组的论文数据进行推荐
            papers_by_field = {research_area: papers}
            self.chat_notifier.notify_paper_updates(sync_stats, papers_by_field, table_links)

        return {
            "synced_count": total_synced,
            "total_count": total_papers,
            "tables": sync_stats,
            "table_links": table_links,
        }

    def _sync_papers_to_table(
        self,
        papers: List[Dict[str, Any]],
        table_id: str,
        research_area: str,
        batch_size: int = 20,
    ) -> Dict[str, Any]:
        """同步论文到指定表格

        Args:
            papers: 论文列表
            table_id: 目标表格ID
            research_area: 研究领域
            batch_size: 批量大小

        Returns:
            同步结果
        """
        if not papers:
            return {"synced_count": 0, "total_count": 0, "table_name": f"{research_area}论文表"}

        # 获取现有记录，避免重复
        existing_records = self.bitable_manager.get_all_records(table_id)
        existing_arxiv_ids = set()

        for record in existing_records:
            fields = record.get("fields", {})
            arxiv_id_field = fields.get("ArXiv ID", "")

            if isinstance(arxiv_id_field, dict):
                arxiv_id = arxiv_id_field.get("text", "")
            else:
                arxiv_id = str(arxiv_id_field) if arxiv_id_field else ""

            if arxiv_id:
                existing_arxiv_ids.add(arxiv_id)

        # 准备新论文数据
        new_papers_data = []
        new_papers_original = []  # 保存原始论文数据用于推荐
        for paper in papers:
            formatted_data = self._format_paper_for_sync(paper, research_area)
            if formatted_data:
                arxiv_id = paper.get("arxiv_id", "")
                if arxiv_id not in existing_arxiv_ids:
                    new_papers_data.append(formatted_data)
                    new_papers_original.append(paper)  # 保存原始论文数据

        logger.info(f"📝 {research_area}：需要同步 {len(new_papers_data)} 篇新论文")

        # 批量插入新论文
        synced_count = 0
        if new_papers_data:
            for i in range(0, len(new_papers_data), batch_size):
                batch = new_papers_data[i : i + batch_size]
                try:
                    self.bitable_manager.batch_insert_records(table_id, batch)
                    synced_count += len(batch)
                    logger.info(f"✅ 批量插入 {len(batch)} 条记录")
                except Exception as e:
                    logger.error(f"❌ 批量插入失败: {e}")

        # 获取总记录数
        total_count = len(existing_records) + synced_count

        # 获取表格名称
        try:
            table_info = self.bitable_manager.get_table_info(table_id)
            table_name = table_info.get("name", f"{research_area}论文表")
        except Exception:
            table_name = f"{research_area}论文表"

        return {
            "synced_count": synced_count,
            "total_count": total_count,
            "table_name": table_name,
            "table_id": table_id,
            "new_papers": new_papers_original,  # 返回新增的原始论文数据
        }

    def _format_paper_for_sync(self, paper: Any, research_area: str) -> Optional[Dict[str, Any]]:
        """格式化论文数据用于同步"""
        try:
            if isinstance(paper, dict):
                # 字典格式
                arxiv_id = paper.get("arxiv_id", "")
                title = paper.get("title", "")
                authors = paper.get("authors", [])
                summary = paper.get("summary", "")
                categories = paper.get("categories", [])
                # 修正日期字段映射
                published = paper.get("published_date", paper.get("published", None))
                updated = paper.get("updated_date", paper.get("updated", None))
                relevance_score = paper.get("final_score", paper.get("relevance_score", 0.0))
                paper_url = paper.get("paper_url", f"http://arxiv.org/abs/{arxiv_id}")
                pdf_url = paper.get("pdf_url", f"http://arxiv.org/pdf/{arxiv_id}.pdf")
                # 修正字段名映射
                matched_keywords = paper.get("matched_interests", paper.get("matched_keywords", []))
                required_keywords = paper.get("required_keyword_matches", paper.get("required_keywords_matched", []))
            else:
                # 对象格式
                arxiv_id = getattr(paper, "arxiv_id", "")
                title = getattr(paper, "title", "")
                authors = getattr(paper, "authors", [])
                summary = getattr(paper, "summary", "")
                categories = getattr(paper, "categories", [])
                published = getattr(paper, "published", None)
                updated = getattr(paper, "updated", None)
                relevance_score = getattr(paper, "final_score", getattr(paper, "relevance_score", 0.0))
                paper_url = getattr(paper, "paper_url", f"http://arxiv.org/abs/{arxiv_id}")
                pdf_url = getattr(paper, "pdf_url", f"http://arxiv.org/pdf/{arxiv_id}.pdf")
                matched_keywords = getattr(paper, "matched_keywords", [])
                required_keywords = getattr(paper, "required_keywords_matched", [])

            if not arxiv_id or not title:
                logger.warning(f"⚠️ 论文数据不完整，跳过: {arxiv_id}")
                return None

            # 格式化数据
            formatted_data = {
                "ArXiv ID": {"text": arxiv_id, "link": paper_url},
                "标题": title[:500],  # 限制长度
                "作者": [str(author)[:50] for author in (authors if isinstance(authors, list) else [str(authors)])][
                    :20
                ],
                "摘要": summary[:2000] if summary else "",  # 限制摘要长度
                "分类": [str(cat)[:30] for cat in (categories if isinstance(categories, list) else [str(categories)])][
                    :10
                ],
                "匹配关键词": [str(kw)[:30] for kw in (matched_keywords if isinstance(matched_keywords, list) else [])][
                    :20
                ],
                "相关性评分": float(relevance_score) if relevance_score else 0.0,
                "研究领域": [research_area],
                "PDF链接": {"text": "PDF", "link": pdf_url},
                "必须关键词匹配": [
                    str(kw)[:30] for kw in (required_keywords if isinstance(required_keywords, list) else [])
                ][:10],
            }

            # 处理日期字段
            if published:
                if isinstance(published, datetime):
                    formatted_data["发布日期"] = int(published.timestamp() * 1000)
                elif isinstance(published, str):
                    try:
                        dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                        formatted_data["发布日期"] = int(dt.timestamp() * 1000)
                    except ValueError:
                        pass

            if updated:
                if isinstance(updated, datetime):
                    formatted_data["更新日期"] = int(updated.timestamp() * 1000)
                elif isinstance(updated, str):
                    try:
                        dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                        formatted_data["更新日期"] = int(dt.timestamp() * 1000)
                    except ValueError:
                        pass

            return formatted_data

        except Exception as e:
            logger.error(f"❌ 格式化论文数据失败: {e}")
            return None

    def sync_papers_to_feishu(
        self,
        papers: List[Dict[str, Any]],
        research_area: str = "general",
        user_name: str = "研究员",
        sync_threshold: float = 0.0,
        batch_size: int = 20,
        enable_notification: bool = True,
    ) -> Dict[str, Any]:
        """同步论文数据到飞书（兼容旧接口）

        Args:
            papers: 论文列表
            research_area: 研究领域
            user_name: 用户名称
            sync_threshold: 同步阈值（相关性评分）
            batch_size: 批量同步大小
            enable_notification: 是否启用通知

        Returns:
            同步结果统计
        """
        if not papers:
            logger.info("ℹ️ 没有论文需要同步")
            return {"synced_count": 0, "total_count": 0, "table_name": "", "table_id": ""}

        logger.info(f"🔄 开始同步 {len(papers)} 篇论文到飞书...")

        # 在同步前刷新token以确保有效性
        if not self.refresh_token_before_sync():
            logger.error("❌ Token刷新失败，同步终止")
            return {"synced_count": 0, "total_count": 0, "table_name": "", "table_id": "", "error": "Token刷新失败"}

        # 创建或获取表格
        table_display_name = f"{user_name.replace('研究员', '')}论文表"
        target_table_id = self.bitable_manager.find_table_by_name(table_display_name)

        if not target_table_id:
            logger.info(f"🆕 创建新数据表: {table_display_name}")
            table_result = self.bitable_manager.create_domain_papers_table(table_display_name, research_area)
            if table_result:
                target_table_id = table_result.get("table_id")
                logger.info(f"✅ 数据表创建成功，ID: {target_table_id}")
            else:
                logger.error("❌ 数据表创建失败")
                return {"synced_count": 0, "total_count": 0, "table_name": "", "table_id": ""}
        else:
            logger.info(f"✅ 找到现有数据表: {table_display_name} (ID: {target_table_id})")

        # 使用新的同步方法
        sync_result = self._sync_papers_to_table(papers, target_table_id, research_area, batch_size)

        # 发送群聊通知
        if enable_notification and sync_result.get("synced_count", 0) > 0:
            # 获取新增的论文数据用于推荐
            new_papers = sync_result.get("new_papers", [])
            self._send_sync_notification(
                research_area=research_area,
                table_name=table_display_name,
                synced_count=sync_result.get("synced_count", 0),
                total_count=sync_result.get("total_count", 0),
                user_name=user_name,
                table_id=target_table_id,
                new_papers=new_papers,  # 传递新增的论文数据
            )

        return sync_result

    def _send_sync_notification(
        self,
        research_area: str,
        table_name: str,
        synced_count: int,
        total_count: int,
        user_name: str,
        table_id: str = None,
        new_papers: List[Dict[str, Any]] = None,
    ):
        """发送同步通知（单表格模式）"""
        try:
            # 构建更新统计信息
            update_stats = {
                research_area: {
                    "new_count": synced_count,
                    "total_count": total_count,
                    "table_name": table_name,
                }
            }

            # 构建表格链接
            table_links = {}
            if table_id:
                table_link = self.chat_notifier.generate_table_link(table_id=table_id)
                if table_link:
                    table_links[research_area] = table_link

            # 从新增论文中选择评分最高的论文作为推荐
            papers_by_field = {}
            if new_papers:
                # 按评分排序，选择最高分的论文
                sorted_papers = sorted(
                    new_papers, key=lambda p: p.get("relevance_score", p.get("final_score", 0)), reverse=True
                )
                papers_by_field[research_area] = sorted_papers

                logger.info(f"📊 推荐论文选择：从 {len(new_papers)} 篇新论文中选择评分最高的")
                if sorted_papers:
                    top_paper = sorted_papers[0]
                    top_score = top_paper.get("relevance_score", top_paper.get("final_score", 0))
                    logger.info(f"🏆 最高评分论文：{top_paper.get('title', '未知标题')[:50]}... (评分: {top_score})")

            # 发送通知
            self.chat_notifier.notify_paper_updates(update_stats, papers_by_field, table_links)  # 传递新增论文用于推荐

            logger.info("📢 群聊通知发送成功")

        except Exception as e:
            logger.error(f"❌ 发送群聊通知失败: {e}")

    def sync_multiple_configs_to_feishu(
        self,
        config_results: List[Dict[str, Any]],
        enable_notification: bool = True,
    ) -> Dict[str, Any]:
        """批量同步多个配置的论文到飞书，发送汇总通知

        Args:
            config_results: 配置结果列表，每个包含 {config_name, papers, research_area, user_name, ...}
            enable_notification: 是否启用通知

        Returns:
            批量同步结果统计
        """
        logger.info(f"🚀 开始批量同步 {len(config_results)} 个配置到飞书...")

        all_sync_stats = {}
        all_table_links = {}
        all_new_papers_by_field = {}
        total_synced = 0
        total_papers = 0

        # 逐个处理每个配置
        for config_result in config_results:
            config_name = config_result.get("config_name", "unknown")
            papers = config_result.get("papers", [])
            research_area = config_result.get("research_area", "general")
            user_name = config_result.get("user_name", "研究员")

            if not papers:
                logger.info(f"⏭️ 跳过配置 {config_name}：没有论文")
                continue

            logger.info(f"🔄 处理配置 {config_name}：{len(papers)} 篇论文")

            # 同步该配置的论文
            sync_result = self.sync_papers_to_feishu(
                papers=papers,
                research_area=research_area,
                user_name=user_name,
                enable_notification=False,  # 禁用单独通知
            )

            if sync_result.get("synced_count", 0) > 0:
                # 收集同步结果
                all_sync_stats[research_area] = {
                    "table_id": sync_result.get("table_id"),
                    "table_name": sync_result.get("table_name", f"{research_area}论文表"),
                    "new_count": sync_result.get("synced_count", 0),
                    "total_count": sync_result.get("total_count", 0),
                }

                # 生成表格链接
                table_id = sync_result.get("table_id")
                if table_id:
                    table_link = self.chat_notifier.generate_table_link(table_id=table_id)
                    if table_link:
                        all_table_links[research_area] = table_link

                # 收集新增论文用于推荐
                new_papers = sync_result.get("new_papers", [])
                if new_papers:
                    all_new_papers_by_field[research_area] = new_papers

                total_synced += sync_result.get("synced_count", 0)
                total_papers += sync_result.get("total_count", 0)

            logger.info(f"✅ 配置 {config_name} 完成：新增 {sync_result.get('synced_count', 0)} 篇")

        logger.info(f"📊 批量同步完成：{len(all_sync_stats)} 个领域，新增 {total_synced} 篇，总计 {total_papers} 篇")

        # 发送汇总通知
        if enable_notification and total_synced > 0:
            logger.info("📢 发送批量同步汇总通知...")
            self.chat_notifier.notify_paper_updates(all_sync_stats, all_new_papers_by_field, all_table_links)

        return {
            "synced_count": total_synced,
            "total_count": total_papers,
            "tables": all_sync_stats,
            "table_links": all_table_links,
            "processed_configs": len(config_results),
            "updated_areas": len(all_sync_stats),
        }


def create_sync_manager_from_config(cfg) -> SyncManager:
    """从配置创建同步管理器

    Args:
        cfg: Hydra配置对象

    Returns:
        同步管理器实例
    """
    from .config import FeishuConfig

    # 创建基础配置
    feishu_config = FeishuConfig.from_hydra_config(cfg)

    # 创建聊天配置
    feishu_cfg = cfg.get("feishu", {})
    chat_cfg = feishu_cfg.get("chat_notification", {})

    chat_config = ChatNotificationConfig(
        enabled=chat_cfg.get("enabled", True),
        notify_on_update=chat_cfg.get("notify_on_update", True),
        notify_on_new_papers=chat_cfg.get("notify_on_new_papers", True),
        min_papers_threshold=chat_cfg.get("min_papers_threshold", 1),
        max_recommended_papers=chat_cfg.get("max_recommended_papers", 1),
        message_template=chat_cfg.get("message_template", "default"),
    )

    return SyncManager(feishu_config, chat_config)
