#!/usr/bin/env python3
"""
改进的飞书同步功能
支持：
1. 论文信息中添加匹配关键词和相关性评分
2. 每个主题/领域对应一个数据表
3. 避免重复同步，根据arxiv id进行去重
4. 群聊通知功能
"""

import os
from dotenv import load_dotenv
from ..configuration.runtime import FeishuEnvPolicy
from ..terminal import debug, key_values, print, success, table
from .bitable import FeishuBitableConnector


def sync_papers_to_feishu(papers, cfg, matched_keywords_map=None, score_map=None):
    """改进的飞书同步函数

    Args:
        papers: 论文列表
        cfg: 配置对象
        matched_keywords_map: 论文ID到匹配关键词的映射
        score_map: 论文ID到评分的映射
    """
    load_dotenv()

    # 检查飞书配置
    feishu_cfg = cfg.get('feishu', {})
    if not feishu_cfg.get('enabled', False):
        print("ℹ️ 飞书同步已禁用")
        return False

    env_policy = FeishuEnvPolicy.from_config(cfg)
    missing_vars = [var for var in env_policy.required if not _has_real_env_value(var, env_policy)]
    has_token = any(_has_real_env_value(var, env_policy) for var in env_policy.token_any_of)

    if missing_vars or not has_token:
        print("❌ 飞书配置不完整，请先检查 .env 或运行 autopaper health")
        return False

    try:
        print("\n🔗 开始飞书同步...")
        connector = FeishuBitableConnector()

        # 获取用户配置信息
        user_profile = cfg.get('user_profile', {})
        research_area = user_profile.get('research_area', 'general')
        user_name = user_profile.get('name', '研究员')

        # 根据研究领域创建表格名称
        table_display_name = f"{user_name.replace('研究员', '')}论文表"

        debug(f"📊 为研究领域 '{research_area}' 处理专用数据表...")

        # 查找或创建数据表
        target_table_id = connector.find_table_by_name(table_display_name)

        if not target_table_id:
            print(f"🆕 创建新数据表: {table_display_name}")
            table_result = connector.create_domain_papers_table(table_display_name, research_area)
            if table_result:
                target_table_id = table_result.get('table_id')
                debug(f"✅ 数据表创建成功，ID: {target_table_id}")
            else:
                print("❌ 数据表创建失败")
                return False
        else:
            debug(f"✅ 找到现有数据表: {table_display_name} (ID: {target_table_id})")

        # 获取现有记录，避免重复
        debug("🔍 检查现有记录，避免重复...")
        existing_records = connector.get_all_records(target_table_id)
        existing_arxiv_ids = set()

        for record in existing_records:
            fields = record.get('fields', {})
            arxiv_id_field = fields.get('ArXiv ID', '')

            # 处理ArXiv ID字段，可能是字符串或超链接格式
            if isinstance(arxiv_id_field, dict):
                # 超链接格式：{"text": "arxiv_id", "link": "url"}
                arxiv_id = arxiv_id_field.get('text', '')
            else:
                # 字符串格式
                arxiv_id = str(arxiv_id_field) if arxiv_id_field else ''

            if arxiv_id:
                existing_arxiv_ids.add(arxiv_id)

        debug(f"📋 发现 {len(existing_arxiv_ids)} 条现有记录")

        # 准备新的论文数据
        new_papers_data = []
        new_papers_count = 0

        for i, paper in enumerate(papers):
            # 提取论文基本信息
            if isinstance(paper, dict):
                arxiv_id = paper.get('arxiv_id', '')
                title = paper.get('title', '')
                summary = paper.get('summary', '')
                published_date = paper.get('published_date')
                updated_date = paper.get('updated_date')
                pdf_url = paper.get('pdf_url', '')
                paper_url = paper.get('paper_url', '')
            else:
                arxiv_id = getattr(paper, 'arxiv_id', getattr(paper, 'id', ''))
                title = getattr(paper, 'title', '')
                summary = getattr(paper, 'summary', '')
                published_date = getattr(paper, 'published_date', None)
                updated_date = getattr(paper, 'updated_date', None)
                pdf_url = getattr(paper, 'pdf_url', '')
                paper_url = getattr(paper, 'paper_url', getattr(paper, 'entry_id', ''))

            # 跳过已存在的记录
            if arxiv_id in existing_arxiv_ids:
                continue

            # 获取匹配关键词和评分
            matched_keywords = []
            relevance_score = 0.0

            # 从论文对象中获取匹配信息
            if isinstance(paper, dict):
                # 从ranking系统中获取匹配信息
                if 'matched_interests' in paper:
                    matched_keywords = paper['matched_interests']

                # 获取评分
                if 'final_score' in paper:
                    relevance_score = paper['final_score']
                elif 'relevance_score' in paper:
                    relevance_score = paper['relevance_score']
                elif 'score' in paper:
                    relevance_score = paper['score']
            else:
                # 对象格式
                if hasattr(paper, 'matched_interests'):
                    matched_keywords = paper.matched_interests
                elif hasattr(paper, 'matched_keywords'):
                    matched_keywords = paper.matched_keywords

                if hasattr(paper, 'final_score'):
                    relevance_score = paper.final_score
                elif hasattr(paper, 'relevance_score'):
                    relevance_score = paper.relevance_score
                elif hasattr(paper, 'score'):
                    relevance_score = paper.score

            # 从外部映射中获取信息（如果提供的话）
            if matched_keywords_map and arxiv_id in matched_keywords_map:
                matched_keywords = matched_keywords_map[arxiv_id]

            if score_map and arxiv_id in score_map:
                relevance_score = score_map[arxiv_id]

            # 处理作者、分类和关键词为多选项格式
            authors_list = []
            categories_list = []

            if isinstance(paper, dict):
                # 处理作者
                authors = paper.get('authors', [])
                if isinstance(authors, list):
                    authors_list = [author.strip() for author in authors if author and author.strip()]
                else:
                    authors_list = [author.strip() for author in str(authors).split(',') if author and author.strip()]

                # 处理分类
                categories = paper.get('categories', [])
                if isinstance(categories, list):
                    categories_list = [cat.strip() for cat in categories if cat and cat.strip()]
                else:
                    categories_list = [cat.strip() for cat in str(categories).split(',') if cat and cat.strip()]
            else:
                # 对象格式
                authors = getattr(paper, 'authors', [])
                if isinstance(authors, list):
                    authors_list = [author.strip() for author in authors if author and author.strip()]
                else:
                    authors_list = [author.strip() for author in str(authors).split(',') if author and author.strip()]

                categories = getattr(paper, 'categories', [])
                if isinstance(categories, list):
                    categories_list = [cat.strip() for cat in categories if cat and cat.strip()]
                else:
                    categories_list = [cat.strip() for cat in str(categories).split(',') if cat and cat.strip()]

            # 处理匹配关键词为多选项格式
            matched_keywords_list = []
            if matched_keywords:
                if isinstance(matched_keywords, list):
                    matched_keywords_list = [kw.strip() for kw in matched_keywords if kw and kw.strip()]
                else:
                    matched_keywords_list = [kw.strip() for kw in str(matched_keywords).split(',') if kw and kw.strip()]

            # 处理必须关键词匹配为多选项格式
            required_keywords_list = []
            if isinstance(paper, dict) and 'required_keyword_matches' in paper:
                required_matches = paper['required_keyword_matches']
                if required_matches:
                    if isinstance(required_matches, list):
                        required_keywords_list = [kw.strip() for kw in required_matches if kw and kw.strip()]
                    else:
                        required_keywords_list = [
                            kw.strip() for kw in str(required_matches).split(',') if kw and kw.strip()
                        ]
            elif hasattr(paper, 'required_keyword_matches'):
                required_matches = paper.required_keyword_matches
                if required_matches:
                    if isinstance(required_matches, list):
                        required_keywords_list = [kw.strip() for kw in required_matches if kw and kw.strip()]
                    else:
                        required_keywords_list = [
                            kw.strip() for kw in str(required_matches).split(',') if kw and kw.strip()
                        ]

            # 处理研究领域为多选项格式
            research_area_list = []
            if research_area:
                if isinstance(research_area, list):
                    research_area_list = [area.strip() for area in research_area if area and area.strip()]
                else:
                    research_area_list = [research_area.strip()] if research_area.strip() else []

            # 限制数量以避免字段过长
            authors_list = authors_list[:10]  # 最多10个作者
            categories_list = categories_list[:5]  # 最多5个分类
            matched_keywords_list = matched_keywords_list[:10]  # 最多10个关键词
            required_keywords_list = required_keywords_list[:5]  # 最多5个必须关键词
            research_area_list = research_area_list[:3]  # 最多3个研究领域

            # 构建论文数据
            paper_data = {
                "ArXiv ID": {"text": arxiv_id, "link": paper_url} if paper_url else arxiv_id,  # 超链接格式
                "标题": title,
                "作者": authors_list,  # 多选项字段
                "摘要": summary[:1000] if summary else "",  # 限制长度
                "分类": categories_list,  # 多选项字段
                "匹配关键词": matched_keywords_list,  # 多选项字段
                "相关性评分": round(relevance_score, 2),
                "研究领域": research_area_list,  # 多选项字段
                "PDF链接": {"text": "PDF", "link": pdf_url} if pdf_url else None,  # 超链接格式
                "必须关键词匹配": required_keywords_list,  # 多选项字段
                "发布日期": int(published_date.timestamp() * 1000) if published_date else None,  # 时间戳格式
                "更新日期": int(updated_date.timestamp() * 1000) if updated_date else None,  # 时间戳格式
            }

            new_papers_data.append(paper_data)
            new_papers_count += 1

        if not new_papers_data:
            print("ℹ️ 没有新的论文需要同步")
            return 0

        # 过滤低分论文
        sync_threshold = feishu_cfg.get('sync_threshold', 0.0)
        papers_to_sync = []

        for paper_data in new_papers_data:
            if paper_data.get('相关性评分', 0) < sync_threshold:
                continue
            papers_to_sync.append(paper_data)

        if not papers_to_sync:
            print(f"ℹ️ 没有符合同步条件的论文（阈值: {sync_threshold}）")
            return 0

        # 批量同步
        batch_size = feishu_cfg.get('batch_size', 20)
        print(f"📊 准备同步 {len(papers_to_sync)} 篇新论文到 '{table_display_name}'...")

        synced_count = 0
        for i in range(0, len(papers_to_sync), batch_size):
            batch = papers_to_sync[i : i + batch_size]

            try:
                result = connector.batch_insert_records(target_table_id, batch)
                if result and result.get('records'):
                    batch_synced = len(result.get('records', []))
                    synced_count += batch_synced
                    debug(f"✅ 第 {i//batch_size + 1} 批同步成功: {batch_synced} 篇")
                else:
                    print(f"⚠️ 第 {i//batch_size + 1} 批同步可能失败")
            except Exception as e:
                print(f"❌ 第 {i//batch_size + 1} 批同步失败: {e}")
                continue

        # 管理视图（如果配置了的话）
        view_config = feishu_cfg.get('views', {})
        if view_config.get('enabled', False):
            debug("🎯 管理表格视图...")
            view_configs = view_config.get('create_views', [])
            auto_cleanup = view_config.get('auto_cleanup', True)

            if view_configs:
                view_result = connector.manage_table_views(target_table_id, view_configs, auto_cleanup)
                key_values(
                    "视图管理结果",
                    {
                        "创建": f"{view_result['created']} 个",
                        "已存在": f"{view_result['existing']} 个",
                        "删除": f"{view_result['deleted']} 个",
                    },
                )

                if view_result['errors']:
                    print(f"   - 错误: {len(view_result['errors'])} 个")
                    for error in view_result['errors']:
                        print(f"     • {error}")

        success("飞书同步完成")
        table(
            "飞书同步摘要",
            ["表格名称", "研究领域", "新增论文", "总记录数"],
            [(table_display_name, research_area, synced_count, len(existing_arxiv_ids) + synced_count)],
        )

        # 发送群聊通知（如果有新论文且配置启用，且不在批量模式）
        if synced_count > 0:
            try:
                # 检查是否处于批量模式
                batch_mode = os.getenv('BATCH_MODE', '0') == '1'
                if batch_mode:
                    debug("ℹ️ 批量模式运行，跳过个别群聊通知")
                else:
                    chat_config = feishu_cfg.get('chat_notification', {})
                    if chat_config.get('enabled', False):
                        print("📢 准备发送群聊通知...")

                        from .notifications import create_chat_notifier_from_config

                        notifier = create_chat_notifier_from_config(cfg)
                        field_name = user_name.replace('研究员', '').strip() or research_area

                        update_stats = {
                            field_name: {
                                'new_count': synced_count,
                                'total_count': len(existing_arxiv_ids) + synced_count,
                                'table_name': table_display_name,
                            }
                        }

                        papers_for_notification = []
                        synced_paper_index = 0

                        for paper in papers:
                            if isinstance(paper, dict):
                                arxiv_id = paper.get('arxiv_id', '')
                            else:
                                arxiv_id = getattr(paper, 'arxiv_id', getattr(paper, 'id', ''))

                            if arxiv_id in existing_arxiv_ids:
                                continue

                            if isinstance(paper, dict):
                                score = paper.get('final_score', paper.get('relevance_score', paper.get('score', 0)))
                            else:
                                score = getattr(
                                    paper, 'final_score', getattr(paper, 'relevance_score', getattr(paper, 'score', 0))
                                )

                            if score < sync_threshold:
                                continue

                            if synced_paper_index < synced_count:
                                if isinstance(paper, dict):
                                    paper_for_notification = paper.copy()
                                    if 'summary' in paper_for_notification and paper_for_notification['summary']:
                                        summary = paper_for_notification['summary']
                                        paper_for_notification['summary'] = (
                                            summary[:200] + '...' if len(summary) > 200 else summary
                                        )
                                else:
                                    paper_for_notification = {
                                        'title': getattr(paper, 'title', ''),
                                        'arxiv_id': getattr(paper, 'arxiv_id', getattr(paper, 'id', '')),
                                        'authors_str': ", ".join(getattr(paper, 'authors', [])),
                                        'paper_url': getattr(paper, 'paper_url', getattr(paper, 'entry_id', '')),
                                        'relevance_score': getattr(
                                            paper,
                                            'final_score',
                                            getattr(paper, 'relevance_score', getattr(paper, 'score', 0)),
                                        ),
                                        'summary': (
                                            (getattr(paper, 'summary', '')[:200] + '...')
                                            if getattr(paper, 'summary', '')
                                            else ''
                                        ),
                                    }
                                papers_for_notification.append(paper_for_notification)
                                synced_paper_index += 1

                        papers_by_field = {field_name: papers_for_notification}
                        table_links = {}
                        table_link = notifier.generate_table_link(table_name=table_display_name, table_id=target_table_id)
                        if table_link:
                            table_links[field_name] = table_link
                            debug(f"📊 生成表格链接: {table_link}")
                        else:
                            print("⚠️ 无法生成表格链接")

                        notification_success = notifier.notify_paper_updates(update_stats, papers_by_field, table_links)

                        if notification_success:
                            print("✅ 群聊通知发送成功")
                        else:
                            print("⚠️ 群聊通知发送失败或跳过")

            except Exception as e:
                print(f"⚠️ 群聊通知功能异常: {e}")
                # 不影响主流程，继续执行

        return synced_count

    except Exception as e:
        print(f"❌ 飞书同步失败: {e}")
        return 0


def _has_real_env_value(name: str, env_policy: FeishuEnvPolicy) -> bool:
    value = os.getenv(name, "")
    return bool(value) and not any(marker in value for marker in env_policy.placeholder_markers)
