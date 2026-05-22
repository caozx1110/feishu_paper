"""Base paper scoring and filtering."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Tuple


class BaseScoringMixin:
    def calculate_relevance_score(
        self,
        paper: Dict[str, Any],
        interest_keywords: List[str] = None,
        exclude_keywords: List[str] = None,
        raw_interest_keywords: List[str] = None,
    ) -> Tuple[float, bool, List[str], List[str]]:
        """
        计算论文与关注词条的相关性评分 (增强版)

        支持通配符匹配：
        - "*" 或 ["*"] 匹配所有文章
        - 以 "regex:" 开头的关键词会被当作正则表达式处理
        - 支持分层权重系统：🎯核心概念、🔧扩展概念

        Args:
            paper: 论文信息字典
            interest_keywords: 关注词条列表（已过滤的），越前面权重越高
            exclude_keywords: 排除词条列表
            raw_interest_keywords: 原始关键词列表（包含注释行，用于权重分析）

        Returns:
            tuple: (relevance_score, is_excluded, matched_interests, matched_excludes)
        """
        if not interest_keywords:
            return 0.0, False, [], []

        # 解析分层权重（如果提供了原始关键词列表）
        keyword_categories = {}
        if raw_interest_keywords:
            keyword_categories = self._parse_keyword_weights(raw_interest_keywords)

        # 检查通配符匹配（匹配所有文章）
        if self._is_wildcard_match(interest_keywords):
            return 1.0, False, ["*"], []

        # 提取论文文本信息
        title = paper.get("title", "").lower()
        summary = paper.get("summary", "").lower()
        categories = paper.get("categories", [])
        categories_str = " ".join(categories).lower()
        authors = paper.get("authors_str", "").lower()
        paper_date = paper.get("published_date", datetime.now())

        # 组合所有文本用于搜索
        full_text = f"{title} {summary} {categories_str} {authors}"

        # 扩展关键词
        expanded_interests = self._expand_keywords(interest_keywords)
        expanded_excludes = self._expand_keywords(exclude_keywords) if exclude_keywords else []

        # 检查排除词条 (使用扩展后的词条)
        excluded = False
        matched_excludes = []
        if expanded_excludes:
            for exclude_term in expanded_excludes:
                if self._contains_keyword(exclude_term, full_text):
                    excluded = True
                    matched_excludes.append(exclude_term)

                # 模糊匹配检查
                fuzzy_score = self._fuzzy_match_score(exclude_term, full_text, threshold=0.9)
                if fuzzy_score > 0:
                    excluded = True
                    matched_excludes.append(f"{exclude_term}(模糊匹配)")

        # 如果被排除，直接返回
        if excluded:
            return -999.0, True, [], matched_excludes

        # 计算关注词条匹配得分 (增强版)
        relevance_score = 0.0
        matched_interests = []

        # 时间衰减权重
        time_weight = self._calculate_time_decay(paper_date)

        # 领域相关性权重
        domain_weight = self._calculate_domain_relevance(categories)

        # 共现检测
        cooccurrence_bonus = self._detect_cooccurrence(expanded_interests, full_text)

        for i, keyword in enumerate(interest_keywords):
            keyword_lower = keyword.lower()

            # 基础权重：越靠前的词条权重越高
            base_weight = len(interest_keywords) - i

            # 增强的关键词匹配（支持正则表达式）
            enhanced_matched, enhanced_score = self._enhance_keyword_matching(keyword, full_text)

            if enhanced_matched:
                matched_interests.append(keyword)

                # 获取分层权重
                tier_weight = self._get_keyword_weight(keyword, keyword_categories)

                final_score = (
                    enhanced_score * base_weight * tier_weight * time_weight * domain_weight * cooccurrence_bonus
                )
                relevance_score += final_score
                continue  # 如果增强匹配成功，跳过后续处理

            # 检查原关键词和扩展关键词
            all_variants = [keyword_lower] + [syn.lower() for syn in self.synonyms.get(keyword_lower, [])]

            keyword_score = 0.0
            keyword_matched = False

            for variant in all_variants:
                # 精确匹配
                position_weights = self._calculate_position_weight(variant, title, summary)
                exact_score = sum(position_weights.values())

                if exact_score > 0:
                    keyword_matched = True
                    keyword_score += exact_score

                # 模糊匹配
                fuzzy_title_score = self._fuzzy_match_score(variant, title, threshold=0.8)
                fuzzy_summary_score = self._fuzzy_match_score(variant, summary, threshold=0.8)

                if fuzzy_title_score > 0:
                    keyword_matched = True
                    keyword_score += fuzzy_title_score * 2.0  # 标题模糊匹配权重

                if fuzzy_summary_score > 0:
                    keyword_matched = True
                    keyword_score += fuzzy_summary_score * 1.0  # 摘要模糊匹配权重

                # 分类匹配
                category_matches = len(re.findall(r"\b" + re.escape(variant) + r"\b", categories_str))
                if category_matches > 0:
                    keyword_matched = True
                    keyword_score += category_matches * 1.5

            if keyword_matched:
                matched_interests.append(keyword)

                # 获取分层权重
                tier_weight = self._get_keyword_weight(keyword, keyword_categories)

                # 综合计算最终分数（添加分层权重）
                final_score = (
                    keyword_score * base_weight * tier_weight * time_weight * domain_weight * cooccurrence_bonus
                )
                relevance_score += final_score

        return relevance_score, excluded, matched_interests, matched_excludes

    def filter_and_rank_papers(
        self,
        papers: List[Dict[str, Any]],
        interest_keywords: List[str] = None,
        exclude_keywords: List[str] = None,
        min_score: float = 0.1,
        use_advanced_scoring: bool = False,
        score_weights: Dict[str, float] = None,
        raw_interest_keywords: List[str] = None,
        required_keywords_config: Dict[str, Any] = None,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, Any]]:
        """
        根据关注词条过滤和排序论文 (支持高级评分和必须关键词)

        Args:
            papers: 论文列表
            interest_keywords: 关注词条列表 (按重要性排序)
            exclude_keywords: 排除词条列表
            min_score: 最小相关性分数阈值
            use_advanced_scoring: 是否使用高级智能评分
            score_weights: 评分权重配置
            required_keywords_config: 必须包含关键词配置

        Returns:
            tuple: (ranked_papers, excluded_papers, score_stats)
        """
        if not papers:
            return [], [], {}

        # 默认评分权重
        if score_weights is None:
            score_weights = {"base": 1.0, "semantic": 0.3, "author": 0.2, "novelty": 0.4, "citation": 0.3}

        # 计算每篇论文的相关性分数
        scored_papers = []
        excluded_papers = []

        for paper in papers:
            # 首先检查必须包含关键词
            if required_keywords_config:
                required_passed, required_matches = self.check_required_keywords(paper, required_keywords_config)
                if not required_passed:
                    paper["exclude_reason"] = "未包含必须关键词"
                    excluded_papers.append(paper)
                    continue
                else:
                    paper["required_keyword_matches"] = required_matches

            # 如果没有关注词条，只进行排除过滤
            if not interest_keywords:
                if exclude_keywords:
                    _, is_excluded, _, _ = self.calculate_relevance_score(
                        paper, [], exclude_keywords, raw_interest_keywords
                    )
                    if is_excluded:
                        excluded_papers.append(paper)
                    else:
                        scored_papers.append(paper)
                else:
                    scored_papers.append(paper)
                continue

            if use_advanced_scoring:
                # 使用高级评分
                total_score, is_excluded, matched_interests, matched_excludes, score_breakdown = (
                    self.calculate_advanced_relevance_score(
                        paper, interest_keywords, exclude_keywords, True, True, raw_interest_keywords
                    )
                )

                # 应用权重
                final_score = (
                    score_breakdown.get("base_score", 0) * score_weights["base"]
                    + score_breakdown.get("semantic_boost", 0) * score_weights["semantic"]
                    + score_breakdown.get("author_boost", 0) * score_weights["author"]
                    + score_breakdown.get("novelty_boost", 0) * score_weights["novelty"]
                    + score_breakdown.get("citation_potential", 0) * score_weights["citation"]
                )

                paper["score_breakdown"] = score_breakdown
                paper["final_score"] = final_score

            else:
                # 使用基础评分
                final_score, is_excluded, matched_interests, matched_excludes = self.calculate_relevance_score(
                    paper, interest_keywords, exclude_keywords, raw_interest_keywords
                )

            if is_excluded:
                paper["exclude_reason"] = matched_excludes
                excluded_papers.append(paper)
            else:
                paper["relevance_score"] = final_score
                paper["matched_interests"] = matched_interests
                paper["interest_match_count"] = len(matched_interests)

                if final_score >= min_score:
                    scored_papers.append(paper)

        # 按相关性分数降序排序
        sort_key = "final_score" if use_advanced_scoring else "relevance_score"
        ranked_papers = sorted(scored_papers, key=lambda x: x.get(sort_key, 0), reverse=True)

        # 统计信息
        scores = [p.get(sort_key, 0) for p in ranked_papers]
        required_filtered = len([p for p in excluded_papers if p.get("exclude_reason") == "未包含必须关键词"])

        score_stats = {
            "total_papers": len(papers),
            "ranked_papers": len(ranked_papers),
            "excluded_papers": len(excluded_papers),
            "required_filtered": required_filtered,
            "max_score": max(scores) if scores else 0,
            "min_score": min(scores) if scores else 0,
            "avg_score": sum(scores) / len(scores) if scores else 0,
            "use_advanced_scoring": use_advanced_scoring,
        }

        return ranked_papers, excluded_papers, score_stats

    def get_field_papers(self, papers: List[Dict[str, Any]], field_type: str) -> List[Dict[str, Any]]:
        """根据领域类型过滤论文"""
        field_keywords = {
            "ai": {
                "keywords": [
                    "artificial intelligence",
                    "AI",
                    "machine intelligence",
                    "deep learning",
                    "neural network",
                ],
                "categories": ["cs.AI", "cs.LG", "stat.ML"],
            },
            "robotics": {
                "keywords": [
                    "robot",
                    "robotics",
                    "robotic",
                    "autonomous",
                    "navigation",
                    "manipulation",
                    "SLAM",
                    "motion planning",
                    "path planning",
                    "humanoid",
                    "quadruped",
                    "mobile robot",
                ],
                "categories": ["cs.RO"],
            },
            "cv": {
                "keywords": [
                    "computer vision",
                    "image processing",
                    "visual",
                    "object detection",
                    "image recognition",
                    "video analysis",
                ],
                "categories": ["cs.CV", "eess.IV"],
            },
            "nlp": {
                "keywords": [
                    "natural language",
                    "NLP",
                    "language model",
                    "text processing",
                    "machine translation",
                    "sentiment analysis",
                ],
                "categories": ["cs.CL"],
            },
        }

        if field_type not in field_keywords:
            return papers

        field_config = field_keywords[field_type]
        filtered_papers = []

        for paper in papers:
            # 检查分类匹配
            if any(cat in paper.get("categories", []) for cat in field_config["categories"]):
                filtered_papers.append(paper)
                continue

            # 检查关键词匹配
            title_lower = paper["title"].lower()
            summary_lower = paper["summary"].lower()

            for keyword in field_config["keywords"]:
                if keyword.lower() in title_lower or keyword.lower() in summary_lower:
                    filtered_papers.append(paper)
                    break

        return filtered_papers
