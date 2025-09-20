#!/usr/bin/env python3
"""
AutoPaper CLI - 基于 Hydra 的 ArXiv 论文采集工具
重构自 arxiv_hydra.py，支持灵活的配置管理和专业领域关键词
"""

import os
import sys
import glob
import yaml
import traceback
import hydra
from datetime import datetime
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, OmegaConf
from pathlib import Path
from typing import List, Dict, Any, Optional

# 添加项目路径到sys.path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# 导入项目核心模块
try:
    from autopaper import ArxivAPI, PaperRanker, PaperDisplayer

    print("✅ 核心模块导入成功")
except ImportError as e:
    print(f"❌ 核心模块导入失败: {e}")
    sys.exit(1)

# 导入autopaper模块
try:
    from autopaper import FeishuConfig, SyncManager

    AUTOPAPER_AVAILABLE = True
    print("✅ AutoPaper模块导入成功")
except ImportError as e:
    AUTOPAPER_AVAILABLE = False
    print(f"⚠️ AutoPaper模块导入失败: {e}")


def find_sync_configs() -> List[str]:
    """查找所有以sync开头的配置文件"""
    config_dir = Path(__file__).parent.parent / "config"
    pattern = str(config_dir / "sync*.yaml")

    sync_configs = glob.glob(pattern)
    config_names = [Path(config).stem for config in sync_configs]

    print(f"🔍 发现 {len(config_names)} 个同步配置文件:")
    for config_name in config_names:
        print(f"   - {config_name}")

    return config_names


def process_single_config(config_name: str, enable_notification: bool = True) -> Dict[str, Any]:
    """处理单个配置文件并返回结果

    Args:
        config_name: 配置文件名
        enable_notification: 是否启用通知，默认为True
    """
    try:
        print(f"\n🚀 开始处理配置: {config_name}")
        print("=" * 60)

        # 加载配置文件
        config_dir = Path(__file__).parent.parent / "config"
        config_path = config_dir / f"{config_name}.yaml"

        if not config_path.exists():
            return {
                "config_name": config_name,
                "success": False,
                "error": f"配置文件不存在: {config_path}",
                "new_papers": 0,
                "total_papers": 0,
                "research_area": "",
                "table_name": "",
                "ranked_papers": [],
            }

        # 直接加载YAML配置文件
        with open(config_path, "r", encoding="utf-8") as f:
            cfg_dict = yaml.safe_load(f)

        cfg = OmegaConf.create(cfg_dict)

        # 检查是否是扩展配置结构
        if hasattr(cfg, "search_config") or hasattr(cfg, "user_profile"):
            # 创建基础配置结构
            base_cfg = OmegaConf.create(
                {
                    "search": {"days": 7, "max_results": 300, "max_display": 10, "min_score": 0.1, "field": "all"},
                    "download": {"enabled": False, "max_downloads": 10, "download_dir": "downloads"},
                    "intelligent_matching": {"enabled": False, "score_weights": {"base": 1.0, "semantic": 0.3}},
                    "display": {"show_ranking": True, "show_scores": True, "show_breakdown": False, "stats": True},
                    "output": {"save": True, "save_keywords": False, "include_scores": True, "format": "markdown"},
                }
            )
            final_cfg = merge_configs(base_cfg, cfg)
        else:
            final_cfg = cfg

        # 初始化组件
        download_dir = final_cfg.get("download", {}).get("download_dir", "downloads")
        arxiv_api = ArxivAPI(download_dir=download_dir)
        paper_ranker = PaperRanker()

        # 加载关键词
        interest_keywords, exclude_keywords, raw_interest_keywords, required_keywords_config = (
            load_keywords_from_config(final_cfg)
        )

        # 获取论文
        search_cfg = final_cfg.get("search", {})
        papers = arxiv_api.get_recent_papers(
            days=search_cfg.get("days", 7),
            max_results=search_cfg.get("max_results", 300),
            field_type=search_cfg.get("field", "all"),
        )

        if not papers:
            return {
                "config_name": config_name,
                "success": True,
                "new_papers": 0,
                "total_papers": 0,
                "research_area": final_cfg.get("user_profile", {}).get(
                    "research_area", config_name.replace("sync_", "")
                ),
                "table_name": final_cfg.get("user_profile", {}).get("name", "").replace("研究员", "") + "论文表",
                "ranked_papers": [],
            }

        # 智能排序处理
        ranked_papers = []
        synced_count = 0
        if interest_keywords or exclude_keywords:
            intelligent_cfg = final_cfg.get("intelligent_matching", {})
            use_intelligent = intelligent_cfg.get("enabled", False)
            score_weights = dict(intelligent_cfg.get("score_weights", {})) if use_intelligent else None

            ranked_papers, excluded_papers, score_stats = paper_ranker.filter_and_rank_papers(
                papers,
                interest_keywords,
                exclude_keywords,
                search_cfg.get("min_score", 0.1),
                use_advanced_scoring=use_intelligent,
                score_weights=score_weights,
                raw_interest_keywords=raw_interest_keywords,
                required_keywords_config=required_keywords_config,
            )

            # 同步到飞书多维表格
            if ranked_papers and AUTOPAPER_AVAILABLE:
                synced_count = sync_to_autopaper(ranked_papers, final_cfg, enable_notification)

            return {
                "config_name": config_name,
                "success": True,
                "new_papers": max(synced_count, 0),
                "total_papers": len(ranked_papers),
                "research_area": final_cfg.get("user_profile", {}).get(
                    "research_area", config_name.replace("sync_", "")
                ),
                "table_name": final_cfg.get("user_profile", {}).get("name", "").replace("研究员", "").strip()
                + "论文表",
                "ranked_papers": ranked_papers if ranked_papers else [],
            }

        return {
            "config_name": config_name,
            "success": True,
            "new_papers": 0,
            "total_papers": len(papers),
            "research_area": final_cfg.get("user_profile", {}).get("research_area", config_name.replace("sync_", "")),
            "table_name": final_cfg.get("user_profile", {}).get("name", "").replace("研究员", "").strip() + "论文表",
            "ranked_papers": [],
        }

    except Exception as e:
        print(f"❌ 配置 {config_name} 处理失败: {e}")
        traceback.print_exc()
        return {
            "config_name": config_name,
            "success": False,
            "error": str(e),
            "new_papers": 0,
            "total_papers": 0,
            "research_area": config_name.replace("sync_", ""),
            "table_name": f'{config_name.replace("sync_", "")}论文表',
            "ranked_papers": [],
        }


def process_all_configs() -> bool:
    """处理所有sync配置文件并发送汇总通知"""
    try:
        print("🚀 ArXiv论文批量同步模式")
        print("=" * 70)

        # 查找所有sync配置
        sync_configs = find_sync_configs()
        if not sync_configs:
            print("❌ 没有找到同步配置文件")
            return False

        print(f"\n🎯 开始处理 {len(sync_configs)} 个配置...")

        # 处理每个配置
        all_results = []
        total_new_papers = 0
        successful_configs = 0

        for config_name in sync_configs:
            # 在批量处理模式下禁用单个配置的通知
            result = process_single_config(config_name, enable_notification=False)
            all_results.append(result)

            if result["success"]:
                successful_configs += 1
                total_new_papers += result["new_papers"]
                print(f"✅ {config_name}: {result['new_papers']} 篇新论文")
            else:
                print(f"❌ {config_name}: {result.get('error', '未知错误')}")

        print(f"\n📊 批量处理完成!")
        print(f"✅ 成功: {successful_configs} 个")
        print(f"❌ 失败: {len(sync_configs) - successful_configs} 个")
        print(f"📚 总新增论文: {total_new_papers} 篇")

        # 发送汇总通知
        if total_new_papers > 0:
            print("\n📢 发送汇总通知...")
            return send_batch_summary_notification(all_results)
        else:
            print("\nℹ️ 没有新论文，跳过通知发送")
            return True

    except Exception as e:
        print(f"❌ 批量处理失败: {e}")
        traceback.print_exc()
        return False


def send_batch_summary_notification(results: List[Dict[str, Any]]) -> bool:
    """发送批量处理的汇总通知"""
    try:
        if not AUTOPAPER_AVAILABLE:
            print("⚠️ AutoPaper模块不可用，跳过通知")
            return False

        # 加载默认配置用于通知
        config_dir = Path(__file__).parent.parent / "config"
        default_config_path = config_dir / "default.yaml"

        with open(default_config_path, "r", encoding="utf-8") as f:
            default_cfg_dict = yaml.safe_load(f)
        default_cfg = OmegaConf.create(default_cfg_dict)

        # 使用autopaper进行通知
        try:
            from dotenv import load_dotenv

            load_dotenv()

            config = FeishuConfig.from_env()
            sync_manager = SyncManager(config)

            # 构建汇总数据
            update_stats = {}
            papers_by_field = {}
            table_links = {}

            for result in results:
                if result["success"] and result["new_papers"] > 0:
                    field_name = result["research_area"]
                    update_stats[field_name] = {
                        "new_count": result["new_papers"],
                        "total_count": result["total_papers"],
                        "table_name": result["table_name"],
                    }
                    papers_by_field[field_name] = result["ranked_papers"]

                    # 获取实际的表格链接
                    try:
                        # 通过表格名称查找表格ID，然后构建链接
                        table_id = sync_manager.bitable_manager.find_table_by_name(result["table_name"])
                        if table_id:
                            table_links[field_name] = f"https://feishu.cn/base/{config.app_token}?table={table_id}"
                        else:
                            table_links[field_name] = f"https://feishu.cn/base/{config.app_token}"
                    except Exception as e:
                        print(f"⚠️ 获取表格链接失败: {e}")
                        table_links[field_name] = f"https://feishu.cn/base/{config.app_token}"

            if not update_stats:
                print("ℹ️ 没有需要通知的更新")
                return True

            # 发送通知
            success = sync_manager.chat_notifier.notify_paper_updates(
                update_stats=update_stats, papers_by_field=papers_by_field, table_links=table_links
            )

            if success:
                print("✅ 汇总通知发送成功")
            else:
                print("❌ 汇总通知发送失败")

            return success

        except Exception as e:
            print(f"❌ 使用autopaper发送通知失败: {e}")
            return False

    except Exception as e:
        print(f"❌ 发送汇总通知失败: {e}")
        traceback.print_exc()
        return False


def sync_to_autopaper(papers, cfg: DictConfig, enable_notification: bool = True) -> int:
    """使用autopaper同步论文到飞书多维表格

    Args:
        papers: 论文列表
        cfg: 配置对象
        enable_notification: 是否启用通知，默认为True
    """
    if not AUTOPAPER_AVAILABLE:
        print("⚠️ AutoPaper模块不可用，跳过同步")
        return 0

    try:
        from dotenv import load_dotenv

        load_dotenv()

        # 检查环境变量
        required_vars = ["FEISHU_APP_ID", "FEISHU_APP_SECRET", "FEISHU_BITABLE_APP_TOKEN"]
        missing_vars = [var for var in required_vars if not os.getenv(var)]

        if missing_vars:
            print(f"❌ 缺少环境变量: {missing_vars}")
            return 0

        print("\n🔗 开始使用AutoPaper同步到飞书多维表格...")

        # 创建配置和同步管理器
        config = FeishuConfig.from_env()
        sync_manager = SyncManager(config)

        # 强制刷新token确保连接有效
        print("🔄 检查并刷新飞书访问token...")
        try:
            new_token = sync_manager.bitable_manager.connector.get_tenant_access_token()
            if new_token:
                print(f"✅ Token刷新成功: {new_token[:20]}...")
            else:
                print("❌ Token刷新失败")
                return 0
        except Exception as e:
            print(f"❌ Token刷新失败: {e}")
            return 0

        # 准备论文数据
        print(f"🔍 调试: 检查传入的论文数据类型和结构...")
        print(f"   论文数量: {len(papers)}")
        if papers:
            first_paper = papers[0]
            print(f"   第一篇论文类型: {type(first_paper)}")
            if isinstance(first_paper, dict):
                print(f"   第一篇论文字典键: {list(first_paper.keys())}")
                print(f"   第一篇论文评分: {first_paper.get('score', '未找到score字段')}")
            else:
                print(f"   第一篇论文对象属性: {[attr for attr in dir(first_paper) if not attr.startswith('_')]}")

        feishu_papers = []
        for paper in papers:
            if isinstance(paper, dict):
                # 修复评分字段映射
                paper_data = paper.copy()
                if "relevance_score" in paper_data and "score" not in paper_data:
                    paper_data["score"] = paper_data["relevance_score"]
                # 确保有score字段
                if "score" not in paper_data:
                    paper_data["score"] = 0.0
            else:
                # 转换论文对象为字典格式
                paper_data = {
                    "title": getattr(paper, "title", ""),
                    "authors": getattr(paper, "authors", []),
                    "abstract": getattr(paper, "summary", ""),
                    "arxiv_id": getattr(paper, "id", "").split("/")[-1],
                    "published": getattr(paper, "published", None),
                    "categories": getattr(paper, "categories", []),
                    "pdf_url": getattr(paper, "pdf_url", ""),
                    "score": getattr(
                        paper, "score", getattr(paper, "final_score", getattr(paper, "relevance_score", 0.0))
                    ),
                    "matched_keywords": getattr(paper, "matched_keywords", []),
                }
            feishu_papers.append(paper_data)

        if not feishu_papers:
            print("ℹ️ 没有论文需要同步")
            return 0

        # 过滤低分论文
        sync_threshold = cfg.get("feishu", {}).get("sync_threshold", 0.0)
        papers_to_sync = [p for p in feishu_papers if p.get("score", 0) >= sync_threshold]

        print(f"📊 论文评分统计:")
        scores = [p.get("score", 0) for p in feishu_papers]
        if scores:
            print(f"   最高分: {max(scores):.3f}")
            print(f"   最低分: {min(scores):.3f}")
            print(f"   平均分: {sum(scores)/len(scores):.3f}")
            print(f"   同步阈值: {sync_threshold}")
            high_score_count = len([s for s in scores if s >= sync_threshold])
            print(f"   符合阈值的论文: {high_score_count}/{len(scores)}")

        if not papers_to_sync:
            print("ℹ️ 没有符合同步条件的论文")
            return 0

        print(f"📊 准备同步 {len(papers_to_sync)} 篇论文到飞书...")

        # 使用autopaper同步
        research_area = cfg.get("user_profile", {}).get("research_area", "unknown")

        try:
            print("🚀 开始同步到飞书...")
            result = sync_manager.sync_papers_to_feishu(
                papers=papers_to_sync,
                research_area=research_area,
                user_name=cfg.get("user_profile", {}).get("name", "研究员"),
                sync_threshold=sync_threshold,
                enable_notification=enable_notification,
            )

            # 正确处理返回值
            synced_count = result.get("synced_count", 0) if isinstance(result, dict) else 0

            print(f"🎉 AutoPaper同步完成！成功同步 {synced_count} 篇论文")
            return synced_count

        except Exception as e:
            print(f"❌ AutoPaper同步失败: {e}")
            return 0

    except Exception as e:
        print(f"❌ AutoPaper同步失败: {e}")
        traceback.print_exc()
        return 0


def load_keywords_from_config(cfg: DictConfig):
    """从配置中加载关键词"""
    # 新的扩展配置结构 - 优先使用关键词配置中的设置
    if hasattr(cfg, "keywords"):
        # 传统结构支持
        raw_interest_keywords = cfg.keywords.get("interest_keywords", [])
        raw_exclude_keywords = cfg.keywords.get("exclude_keywords", [])
    else:
        # 直接从根级别获取
        raw_interest_keywords = cfg.get("interest_keywords", [])
        raw_exclude_keywords = cfg.get("exclude_keywords", [])

    # 转换为Python列表（如果是DictConfig）
    if hasattr(raw_interest_keywords, "_content"):
        raw_interest_keywords = list(raw_interest_keywords)
    if hasattr(raw_exclude_keywords, "_content"):
        raw_exclude_keywords = list(raw_exclude_keywords)

    # 过滤掉注释行和空行（用于实际匹配）
    interest_keywords = _filter_keywords(raw_interest_keywords)
    exclude_keywords = _filter_keywords(raw_exclude_keywords)

    # 加载必须包含关键词配置
    required_keywords_config = cfg.get("required_keywords", {})

    return interest_keywords, exclude_keywords, raw_interest_keywords, required_keywords_config


def _filter_keywords(keywords):
    """过滤关键词列表，移除注释行和空行"""
    if not keywords:
        return []

    filtered = []
    for keyword in keywords:
        # 跳过空字符串
        if not keyword or not keyword.strip():
            continue

        # 跳过注释行（以 # 开头）
        if keyword.strip().startswith("#"):
            continue

        # 保留有效关键词
        filtered.append(keyword.strip())

    return filtered


def merge_configs(global_cfg: DictConfig, keyword_cfg: DictConfig) -> DictConfig:
    """合并全局配置和关键词配置，关键词配置优先"""
    merged_cfg = OmegaConf.merge(global_cfg, keyword_cfg)

    # 如果关键词配置有search_config，则覆盖全局search配置
    if hasattr(keyword_cfg, "search_config"):
        merged_cfg.search = OmegaConf.merge(merged_cfg.search, keyword_cfg.search_config)

    # 如果关键词配置有其他_config后缀的配置，则覆盖对应的全局配置
    config_mappings = {
        "intelligent_matching_config": "intelligent_matching",
        "download_config": "download",
        "display_config": "display",
        "output_config": "output",
    }

    for config_key, global_key in config_mappings.items():
        if hasattr(keyword_cfg, config_key):
            if not hasattr(merged_cfg, global_key):
                merged_cfg[global_key] = OmegaConf.create({})
            merged_cfg[global_key] = OmegaConf.merge(merged_cfg[global_key], keyword_cfg[config_key])

    return merged_cfg


def print_config_info(cfg: DictConfig):
    """打印配置信息"""
    print("📚 AutoPaper CLI - ArXiv 论文采集工具")
    print(f"🕒 {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
    print("=" * 70)

    # 显示用户信息（新的扩展配置结构）
    if hasattr(cfg, "user_profile"):
        print(f"👤 用户: {cfg.user_profile.get('name', 'Unknown')}")
        print(f"📝 描述: {cfg.user_profile.get('description', 'No description')}")
        print(f"🔬 研究领域: {cfg.user_profile.get('research_area', 'general')}")
    elif hasattr(cfg, "keywords") and hasattr(cfg.keywords, "description"):
        # 向后兼容传统结构
        keywords_name = cfg.defaults[0].keywords if hasattr(cfg, "defaults") else "unknown"
        print(f"📋 当前配置: {keywords_name}")
        print(f"📝 配置描述: {cfg.keywords.description}")
    else:
        # 最基础的兼容性
        keywords_name = cfg.defaults[0].keywords if hasattr(cfg, "defaults") else "unknown"
        print(f"📋 当前配置: {keywords_name}")

    # 显示关键词
    interest_keywords, exclude_keywords, raw_interest_keywords, required_keywords_config = load_keywords_from_config(
        cfg
    )

    if interest_keywords:
        print(f"\n🎯 关注词条 ({len(interest_keywords)}个):")
        print(f"   {' > '.join(interest_keywords[:5])}{'...' if len(interest_keywords) > 5 else ''}")

    if exclude_keywords:
        print(f"🚫 排除词条 ({len(exclude_keywords)}个):")
        print(f"   {', '.join(exclude_keywords[:5])}{'...' if len(exclude_keywords) > 5 else ''}")

    # 显示必须关键词
    if required_keywords_config.get("enabled", False):
        required_keywords = required_keywords_config.get("keywords", [])
        fuzzy_match = required_keywords_config.get("fuzzy_match", True)
        threshold = required_keywords_config.get("similarity_threshold", 0.8)
        print(f"✅ 必须包含关键词 ({len(required_keywords)}个):")
        print(f"   {', '.join(required_keywords[:3])}{'...' if len(required_keywords) > 3 else ''}")
        print(f"   模糊匹配: {'启用' if fuzzy_match else '禁用'}, 阈值: {threshold}")
    else:
        print(f"✅ 必须包含关键词: 未启用")

    print(f"⚙️  搜索参数:")
    search_cfg = cfg.get("search", {})
    print(f"   天数: {search_cfg.get('days', 'N/A')}, 最大结果: {search_cfg.get('max_results', 'N/A')}")
    print(f"   领域: {search_cfg.get('field', 'N/A')}, 最小评分: {search_cfg.get('min_score', 'N/A')}")

    # 显示智能匹配配置
    intelligent_cfg = cfg.get("intelligent_matching", {})
    if intelligent_cfg.get("enabled", False):
        print(f"🧠 智能匹配: 启用")
        weights = intelligent_cfg.get("score_weights", {})
        print(
            f"   评分权重: 基础({weights.get('base', 0)}) 语义({weights.get('semantic', 0)}) 新颖性({weights.get('novelty', 0)})"
        )
    else:
        print(f"🧠 智能匹配: 关闭")

    # 显示下载配置
    download_cfg = cfg.get("download", {})
    if download_cfg.get("enabled", False):
        print(f"📥 PDF下载: 启用 (最多{download_cfg.get('max_downloads', 0)}篇)")
    else:
        print(f"📥 PDF下载: 关闭")

    print("=" * 70)


@hydra.main(version_base=None, config_path="../config", config_name="default")
def main(cfg: DictConfig) -> None:
    """主函数"""
    try:
        # 检查是否是批量处理模式
        try:
            hydra_cfg = HydraConfig.get()
            config_name = hydra_cfg.job.config_name

            if config_name == "all":
                process_all_configs()
                return
        except:
            pass  # 如果无法获取配置名，继续正常处理

        # 检查是否是扩展配置结构，如果是则进行配置合并
        if hasattr(cfg, "search_config") or hasattr(cfg, "user_profile"):
            # 创建基础配置结构
            base_cfg = OmegaConf.create(
                {
                    "search": {"days": 7, "max_results": 300, "max_display": 10, "min_score": 0.1, "field": "all"},
                    "download": {"enabled": False, "max_downloads": 10, "download_dir": "downloads"},
                    "intelligent_matching": {"enabled": False, "score_weights": {"base": 1.0, "semantic": 0.3}},
                    "display": {"show_ranking": True, "show_scores": True, "show_breakdown": False, "stats": True},
                    "output": {"save": True, "save_keywords": False, "include_scores": True, "format": "markdown"},
                }
            )
            final_cfg = merge_configs(base_cfg, cfg)
        else:
            final_cfg = cfg

        # 初始化组件
        download_dir = final_cfg.get("download", {}).get("download_dir", "downloads")
        arxiv_api = ArxivAPI(download_dir=download_dir)
        paper_ranker = PaperRanker()
        displayer = PaperDisplayer()

        # 打印配置信息
        print_config_info(final_cfg)

        # 加载关键词
        interest_keywords, exclude_keywords, raw_interest_keywords, required_keywords_config = (
            load_keywords_from_config(final_cfg)
        )

        # 获取论文 - 使用新的字段类型
        search_cfg = final_cfg.get("search", {})
        papers = arxiv_api.get_recent_papers(
            days=search_cfg.get("days", 7),
            max_results=search_cfg.get("max_results", 300),
            field_type=search_cfg.get("field", "all"),
        )

        if not papers:
            print("❌ 未获取到任何论文")
            return

        # 领域筛选
        field_names = {"ai": "人工智能/机器学习", "robotics": "机器人学", "cv": "计算机视觉", "nlp": "自然语言处理"}
        field = search_cfg.get("field", "all")

        if field != "all":
            field_name = field_names.get(field, field)
            print(f"\n🎯 专业领域: {field_name}")
        else:
            print(f"\n🌐 全领域搜索")

        # 显示统计信息
        display_cfg = final_cfg.get("display", {})
        if display_cfg.get("stats", True):
            print(f"📊 获取论文: {len(papers)} 篇")

        # 智能排序处理
        if interest_keywords or exclude_keywords:
            intelligent_cfg = final_cfg.get("intelligent_matching", {})
            use_intelligent = intelligent_cfg.get("enabled", False)
            score_weights = dict(intelligent_cfg.get("score_weights", {})) if use_intelligent else None

            ranked_papers, excluded_papers, score_stats = paper_ranker.filter_and_rank_papers(
                papers,
                interest_keywords,
                exclude_keywords,
                search_cfg.get("min_score", 0.1),
                use_advanced_scoring=use_intelligent,
                score_weights=score_weights,
                raw_interest_keywords=raw_interest_keywords,
                required_keywords_config=required_keywords_config,
            )

            print(f"✅ 筛选后论文: {len(ranked_papers)} 篇")
            print(f"❌ 排除论文: {len(excluded_papers)} 篇")

            # 显示论文
            max_display = search_cfg.get("max_display", 10)
            if max_display > 0:
                displayer.display_papers(ranked_papers[:max_display], final_cfg)

            # 同步到飞书
            if ranked_papers and AUTOPAPER_AVAILABLE:
                sync_to_autopaper(ranked_papers, final_cfg)  # 默认enable_notification=True

        else:
            print(f"ℹ️ 未配置关键词，显示所有论文")
            max_display = search_cfg.get("max_display", 10)
            if max_display > 0:
                displayer.display_papers(papers[:max_display], final_cfg)

        print(f"\n✅ 采集完成！")

    except Exception as e:
        print(f"❌ 程序执行失败: {e}")
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
