#!/usr/bin/env python3
"""
基于 Hydra 的 ArXiv 论文采集工具
支持灵活的配置管理和专业领域关键词
"""

import sys
import os
from datetime import datetime
import hydra
from hydra.core.hydra_config import HydraConfig
from omegaconf import DictConfig, OmegaConf
from pathlib import Path

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from arxiv_core import ArxivAPI, PaperRanker
from paper_display import PaperDisplayer

# 飞书集成导入
try:
    from feishu_bitable_connector import FeishuBitableConnector
    from sync_to_feishu import sync_papers_to_feishu

    FEISHU_AVAILABLE = True
except ImportError:
    FEISHU_AVAILABLE = False
    print("⚠️ 飞书模块未找到，将跳过飞书同步功能")


def sync_to_feishu(papers, cfg: DictConfig):
    """同步论文到飞书多维表格"""
    if not FEISHU_AVAILABLE:
        print("⚠️ 飞书模块不可用，跳过同步")
        return False

    feishu_cfg = cfg.get('feishu', {})
    if not feishu_cfg.get('enabled', True):
        print("ℹ️ 飞书同步已禁用")
        return False

    try:
        from dotenv import load_dotenv

        load_dotenv()

        # 检查环境变量
        required_vars = ['FEISHU_APP_ID', 'FEISHU_APP_SECRET', 'FEISHU_BITABLE_APP_TOKEN', 'FEISHU_PAPERS_TABLE_ID']

        missing_vars = []
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)

        # 检查访问令牌
        has_user_token = bool(os.getenv('FEISHU_USER_ACCESS_TOKEN')) and 'xxxx' not in os.getenv(
            'FEISHU_USER_ACCESS_TOKEN', ''
        )
        has_tenant_token = bool(os.getenv('FEISHU_TENANT_ACCESS_TOKEN')) and 'xxxx' not in os.getenv(
            'FEISHU_TENANT_ACCESS_TOKEN', ''
        )

        if missing_vars or (not has_user_token and not has_tenant_token):
            print("❌ 飞书配置不完整，请先运行 setup_feishu.py 配置")
            return False

        print("\n🔗 开始同步到飞书多维表格...")
        connector = FeishuBitableConnector()

        # 准备论文数据
        feishu_papers = []
        for paper in papers:
            # 处理不同的论文对象格式
            if isinstance(paper, dict):
                # 字典格式的论文对象
                paper_data = {
                    "ArXiv ID": paper.get('arxiv_id', ''),
                    "标题": paper.get('title', ''),
                    "作者": paper.get('authors_str', ''),
                    "摘要": (paper.get('summary', '')[:1000] if paper.get('summary') else ""),
                    "分类": paper.get('categories_str', ''),
                    "发布日期": paper.get('published_date').strftime("%Y-%m-%d") if paper.get('published_date') else "",
                    "更新日期": paper.get('updated_date').strftime("%Y-%m-%d") if paper.get('updated_date') else "",
                    "PDF链接": paper.get('pdf_url', ''),
                    "论文链接": paper.get('paper_url', ''),
                }
            else:
                # 对象格式的论文对象
                paper_data = {
                    "ArXiv ID": getattr(paper, 'id', getattr(paper, 'arxiv_id', '')),
                    "标题": getattr(paper, 'title', ''),
                    "作者": ", ".join(getattr(paper, 'authors', [])),
                    "摘要": (getattr(paper, 'summary', '')[:1000] if getattr(paper, 'summary') else ""),
                    "分类": ", ".join(getattr(paper, 'categories', [])),
                    "发布日期": (
                        getattr(paper, 'published', None).strftime("%Y-%m-%d")
                        if getattr(paper, 'published', None)
                        else ""
                    ),
                    "更新日期": (
                        getattr(paper, 'updated', None).strftime("%Y-%m-%d") if getattr(paper, 'updated', None) else ""
                    ),
                    "PDF链接": getattr(paper, 'pdf_url', ''),
                    "论文链接": getattr(paper, 'entry_id', ''),
                }
            feishu_papers.append(paper_data)

        # 批量同步到飞书
        sync_threshold = feishu_cfg.get('sync_threshold', 0.0)
        batch_size = feishu_cfg.get('batch_size', 20)

        # 过滤低分论文（如果有评分）
        papers_to_sync = []
        for i, paper_data in enumerate(feishu_papers):
            if hasattr(papers[i], 'score') and papers[i].score < sync_threshold:
                continue
            papers_to_sync.append(paper_data)

        if not papers_to_sync:
            print("ℹ️ 没有符合同步条件的论文")
            return True

        print(f"📊 准备同步 {len(papers_to_sync)} 篇论文到飞书...")

        # 分批同步
        synced_count = 0
        for i in range(0, len(papers_to_sync), batch_size):
            batch = papers_to_sync[i : i + batch_size]

            try:
                result = connector.batch_insert_paper_records(batch)
                if result and result.get('records'):
                    batch_synced = len(result.get('records', []))
                    synced_count += batch_synced
                    print(f"✅ 第 {i//batch_size + 1} 批同步成功: {batch_synced} 篇")
                else:
                    print(f"⚠️ 第 {i//batch_size + 1} 批同步可能失败")
            except Exception as e:
                print(f"❌ 第 {i//batch_size + 1} 批同步失败: {e}")
                continue

        print(f"🎉 飞书同步完成！成功同步 {synced_count} 篇论文")

        # 同步关系数据（可选）
        research_area = cfg.get('user_profile', {}).get('research_area', 'unknown')
        if research_area and research_area != 'unknown':
            relations_table_id = os.getenv('FEISHU_RELATIONS_TABLE_ID')
            if relations_table_id:
                try:
                    relation_data = {
                        "论文ID": "batch_" + datetime.now().strftime("%Y%m%d_%H%M%S"),
                        "领域ID": research_area,
                        "领域名称": cfg.get('user_profile', {}).get('name', research_area),
                        "相关性评分": 1.0,
                        "匹配关键词": ", ".join(cfg.get('interest_keywords', [])[:5]),
                    }

                    connector.insert_record(relations_table_id, relation_data)
                    print("✅ 领域关系数据同步完成")
                except Exception as e:
                    print(f"⚠️ 领域关系数据同步失败: {e}")

        return True

    except Exception as e:
        print(f"❌ 飞书同步失败: {e}")
        return False


def load_keywords_from_config(cfg: DictConfig):
    """从配置中加载关键词"""
    # 新的扩展配置结构 - 优先使用关键词配置中的设置
    if hasattr(cfg, 'keywords'):
        # 传统结构支持
        raw_interest_keywords = cfg.keywords.get('interest_keywords', [])
        raw_exclude_keywords = cfg.keywords.get('exclude_keywords', [])
    else:
        # 直接从根级别获取
        raw_interest_keywords = cfg.get('interest_keywords', [])
        raw_exclude_keywords = cfg.get('exclude_keywords', [])

    # 转换为Python列表（如果是DictConfig）
    if hasattr(raw_interest_keywords, '_content'):
        raw_interest_keywords = list(raw_interest_keywords)
    if hasattr(raw_exclude_keywords, '_content'):
        raw_exclude_keywords = list(raw_exclude_keywords)

    # 过滤掉注释行和空行（用于实际匹配）
    interest_keywords = _filter_keywords(raw_interest_keywords)
    exclude_keywords = _filter_keywords(raw_exclude_keywords)

    # 加载必须包含关键词配置
    required_keywords_config = cfg.get('required_keywords', {})

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
        if keyword.strip().startswith('#'):
            continue

        # 保留有效关键词
        filtered.append(keyword.strip())

    return filtered


def merge_configs(global_cfg: DictConfig, keyword_cfg: DictConfig) -> DictConfig:
    """合并全局配置和关键词配置，关键词配置优先"""
    merged_cfg = OmegaConf.merge(global_cfg, keyword_cfg)

    # 如果关键词配置有search_config，则覆盖全局search配置
    if hasattr(keyword_cfg, 'search_config'):
        merged_cfg.search = OmegaConf.merge(merged_cfg.search, keyword_cfg.search_config)

    # 如果关键词配置有其他_config后缀的配置，则覆盖对应的全局配置
    config_mappings = {
        'intelligent_matching_config': 'intelligent_matching',
        'download_config': 'download',
        'display_config': 'display',
        'output_config': 'output',
    }

    for config_key, global_key in config_mappings.items():
        if hasattr(keyword_cfg, config_key):
            if not hasattr(merged_cfg, global_key):
                merged_cfg[global_key] = {}
            merged_cfg[global_key] = OmegaConf.merge(merged_cfg[global_key], keyword_cfg[config_key])

    return merged_cfg


def print_config_info(cfg: DictConfig):
    """打印配置信息"""
    print("📚 ArXiv 论文采集工具 - 扩展配置版")
    print(f"🕒 {datetime.now().strftime('%Y年%m月%d日 %H:%M:%S')}")
    print("=" * 70)

    # 显示用户信息（新的扩展配置结构）
    if hasattr(cfg, 'user_profile'):
        print(f"👤 用户: {cfg.user_profile.get('name', 'Unknown')}")
        print(f"📝 描述: {cfg.user_profile.get('description', 'No description')}")
        print(f"🔬 研究领域: {cfg.user_profile.get('research_area', 'general')}")
    elif hasattr(cfg, 'keywords') and hasattr(cfg.keywords, 'description'):
        # 向后兼容传统结构
        keywords_name = cfg.defaults[0].keywords if hasattr(cfg, 'defaults') else "unknown"
        print(f"📋 当前配置: {keywords_name}")
        print(f"📝 配置描述: {cfg.keywords.description}")
    else:
        # 最基础的兼容性
        keywords_name = cfg.defaults[0].keywords if hasattr(cfg, 'defaults') else "unknown"
        print(f"� 当前配置: {keywords_name}")

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
    if required_keywords_config.get('enabled', False):
        required_keywords = required_keywords_config.get('keywords', [])
        fuzzy_match = required_keywords_config.get('fuzzy_match', True)
        threshold = required_keywords_config.get('similarity_threshold', 0.8)
        print(f"✅ 必须包含关键词 ({len(required_keywords)}个):")
        print(f"   {', '.join(required_keywords[:3])}{'...' if len(required_keywords) > 3 else ''}")
        print(f"   模糊匹配: {'启用' if fuzzy_match else '禁用'}, 阈值: {threshold}")
    else:
        print(f"✅ 必须包含关键词: 未启用")

    print(f"⚙️  搜索参数:")
    search_cfg = cfg.get('search', {})
    print(f"   天数: {search_cfg.get('days', 'N/A')}, 最大结果: {search_cfg.get('max_results', 'N/A')}")
    print(f"   领域: {search_cfg.get('field', 'N/A')}, 最小评分: {search_cfg.get('min_score', 'N/A')}")

    # 显示智能匹配配置
    intelligent_cfg = cfg.get('intelligent_matching', {})
    if intelligent_cfg.get('enabled', False):
        print(f"🧠 智能匹配: 启用")
        weights = intelligent_cfg.get('score_weights', {})
        print(
            f"   评分权重: 基础({weights.get('base', 0)}) 语义({weights.get('semantic', 0)}) 新颖性({weights.get('novelty', 0)})"
        )
    else:
        print(f"🧠 智能匹配: 关闭")

    # 显示下载配置
    download_cfg = cfg.get('download', {})
    if download_cfg.get('enabled', False):
        print(f"📥 PDF下载: 启用 (最多{download_cfg.get('max_downloads', 0)}篇)")
    else:
        print(f"📥 PDF下载: 关闭")

    print("=" * 70)


@hydra.main(version_base=None, config_path="conf", config_name="default")
def main(cfg: DictConfig) -> None:
    """主函数"""

    # 检查是否是扩展配置结构，如果是则进行配置合并
    if hasattr(cfg, 'search_config') or hasattr(cfg, 'user_profile'):
        # 创建基础配置结构
        base_cfg = OmegaConf.create(
            {
                'search': {'days': 7, 'max_results': 300, 'max_display': 10, 'min_score': 0.1, 'field': 'all'},
                'download': {
                    'enabled': False,
                    'max_downloads': 10,
                    'download_dir': 'downloads',
                    'create_metadata': True,
                    'create_index': True,
                    'force_download': False,
                },
                'intelligent_matching': {
                    'enabled': False,
                    'score_weights': {'base': 1.0, 'semantic': 0.3, 'author': 0.2, 'novelty': 0.4, 'citation': 0.3},
                    'fuzzy_threshold': 0.8,
                    'time_decay_days': 30,
                },
                'display': {'show_ranking': True, 'show_scores': True, 'show_breakdown': False, 'stats': True},
                'output': {'save': True, 'save_keywords': False, 'include_scores': True, 'format': 'markdown'},
            }
        )
        final_cfg = merge_configs(base_cfg, cfg)
    else:
        # 传统配置结构，直接使用
        final_cfg = cfg

    # 初始化组件
    download_dir = final_cfg.get('download', {}).get('download_dir', 'downloads')
    arxiv_api = ArxivAPI(download_dir=download_dir)
    paper_ranker = PaperRanker()
    displayer = PaperDisplayer()

    # 打印配置信息
    print_config_info(final_cfg)

    # 加载关键词
    interest_keywords, exclude_keywords, raw_interest_keywords, required_keywords_config = load_keywords_from_config(
        final_cfg
    )

    # 获取论文 - 使用新的字段类型
    search_cfg = final_cfg.get('search', {})
    papers = arxiv_api.get_recent_papers(
        days=search_cfg.get('days', 7),
        max_results=search_cfg.get('max_results', 300),
        field_type=search_cfg.get('field', 'all'),
    )

    if not papers:
        print("❌ 未找到相关论文")
        return

    # 领域筛选
    field_names = {'ai': '人工智能/机器学习', 'robotics': '机器人学', 'cv': '计算机视觉', 'nlp': '自然语言处理'}
    field = search_cfg.get('field', 'all')

    if field != 'all':
        field_name = field_names.get(field, field)
        print(f"\n🎯 {field_name} 领域筛选结果: {len(papers)} 篇")
    else:
        field_name = "全部"

    # 显示统计信息
    display_cfg = final_cfg.get('display', {})
    if display_cfg.get('stats', True):
        displayer.display_hot_categories(papers)

    # 智能排序处理
    if interest_keywords or exclude_keywords:
        # 检查是否启用智能匹配
        intelligent_cfg = final_cfg.get('intelligent_matching', {})
        use_intelligent = intelligent_cfg.get('enabled', False)
        score_weights = None

        if use_intelligent:
            # 获取智能匹配配置
            score_weights = dict(intelligent_cfg.get('score_weights', {}))
            print(f"\n🧠 使用智能匹配模式")
        else:
            print(f"\n🔍 使用基础匹配模式")

        ranked_papers, excluded_papers, score_stats = paper_ranker.filter_and_rank_papers(
            papers,
            interest_keywords,
            exclude_keywords,
            search_cfg.get('min_score', 0.1),
            use_advanced_scoring=use_intelligent,
            score_weights=score_weights,
            raw_interest_keywords=raw_interest_keywords,
            required_keywords_config=required_keywords_config,
        )

        if score_stats:
            if use_intelligent:
                displayer.display_advanced_ranking_stats(ranked_papers, score_stats)
            else:
                displayer.display_ranking_stats(score_stats, excluded_papers)

        if ranked_papers:
            # PDF下载处理
            download_cfg = final_cfg.get('download', {})
            if download_cfg.get('enabled', False) and ranked_papers:
                print(f"\n📥 开始下载PDF文件...")
                download_stats = arxiv_api.batch_download_pdfs(
                    ranked_papers[: download_cfg.get('max_downloads', 10)],
                    max_downloads=download_cfg.get('max_downloads', 10),
                    create_index=download_cfg.get('create_index', True),
                )

                print(
                    f"📊 下载统计: 成功 {download_stats['downloaded']}, "
                    f"跳过 {download_stats['skipped']}, 失败 {download_stats['failed']}"
                )

                if download_stats['failed_papers']:
                    print("❌ 下载失败的论文:")
                    for failed in download_stats['failed_papers']:
                        print(f"   - {failed['title'][:50]}... ({failed['error']})")

            # 同步到飞书多维表格
            if FEISHU_AVAILABLE:
                sync_papers_to_feishu(ranked_papers, final_cfg)

            display_cfg = final_cfg.get('display', {})
            if display_cfg.get('show_ranking', True):
                if use_intelligent:
                    show_breakdown = display_cfg.get('show_breakdown', False)
                    displayer.display_advanced_ranked_papers(
                        ranked_papers, search_cfg.get('max_display', 10), show_breakdown=show_breakdown
                    )
                else:
                    displayer.display_ranked_papers(
                        ranked_papers,
                        search_cfg.get('max_display', 10),
                        show_scores=display_cfg.get('show_scores', True),
                    )

            # 保存报告
            output_cfg = final_cfg.get('output', {})
            if output_cfg.get('save', True):
                # 获取配置文件名和研究领域名
                try:
                    hydra_cfg = HydraConfig.get()
                    actual_config_name = hydra_cfg.job.config_name
                except:
                    actual_config_name = "unknown"

                # 获取研究领域名或用户名
                research_area = ""
                if hasattr(final_cfg, 'user_profile'):
                    research_area = final_cfg.user_profile.get('research_area', '')
                elif hasattr(final_cfg, 'defaults'):
                    research_area = final_cfg.defaults[0].keywords if hasattr(final_cfg.defaults[0], 'keywords') else ''

                output_format = output_cfg.get('format', 'txt')

                if output_format == 'markdown':
                    displayer.save_papers_report_markdown(
                        ranked_papers,
                        field_name,
                        search_cfg.get('days', 7),
                        include_scores=output_cfg.get('include_scores', True),
                        config_name=actual_config_name,
                        research_area=research_area,
                    )
                else:
                    displayer.save_papers_report(
                        ranked_papers,
                        field_name,
                        search_cfg.get('days', 7),
                        include_scores=output_cfg.get('include_scores', True),
                        config_name=actual_config_name,
                        research_area=research_area,
                    )
        else:
            print("❌ 没有找到符合条件的相关论文")
    else:
        # 常规显示
        displayer.display_papers_detailed(papers, search_cfg.get('max_display', 10))

        # 同步到飞书多维表格（无关键词筛选）
        if FEISHU_AVAILABLE:
            sync_papers_to_feishu(papers, final_cfg)

        # PDF下载处理（无关键词筛选）
        download_cfg = final_cfg.get('download', {})
        if download_cfg.get('enabled', False) and papers:
            print(f"\n📥 开始下载PDF文件...")
            download_stats = arxiv_api.batch_download_pdfs(
                papers[: download_cfg.get('max_downloads', 10)],
                max_downloads=download_cfg.get('max_downloads', 10),
                create_index=download_cfg.get('create_index', True),
            )

            print(
                f"📊 下载统计: 成功 {download_stats['downloaded']}, "
                f"跳过 {download_stats['skipped']}, 失败 {download_stats['failed']}"
            )

        if final_cfg.output.save:
            # 获取配置文件名和研究领域名
            try:
                hydra_cfg = HydraConfig.get()
                actual_config_name = hydra_cfg.job.config_name
            except:
                actual_config_name = "unknown"

            # 获取研究领域名或用户名
            research_area = ""
            if hasattr(final_cfg, 'user_profile'):
                research_area = final_cfg.user_profile.get('research_area', '')
            elif hasattr(final_cfg, 'defaults'):
                research_area = final_cfg.defaults[0].keywords if hasattr(final_cfg.defaults[0], 'keywords') else ''

            output_format = final_cfg.output.get('format', 'txt')

            if output_format == 'markdown':
                displayer.save_papers_report_markdown(
                    papers,
                    field_name,
                    final_cfg.search.days,
                    include_scores=False,
                    config_name=actual_config_name,
                    research_area=research_area,
                )
            else:
                displayer.save_papers_report(
                    papers,
                    field_name,
                    final_cfg.search.days,
                    include_scores=False,
                    config_name=actual_config_name,
                    research_area=research_area,
                )

    print(f"\n✅ 采集完成！")


if __name__ == "__main__":
    main()
