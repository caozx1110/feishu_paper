"""Advanced ranking signals beyond direct keyword matches."""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, Dict, List, Tuple


class AdvancedScoringMixin:
    def _calculate_time_decay(self, paper_date: datetime, decay_days: int = 30) -> float:
        """计算时间衰减权重 - 较新的论文权重更高"""
        # 处理时区问题
        if paper_date.tzinfo is not None:
            paper_date = paper_date.replace(tzinfo=None)

        days_ago = (datetime.now() - paper_date).days
        if days_ago <= 0:
            return 1.0
        elif days_ago <= decay_days:
            # 线性衰减
            return 1.0 - (days_ago / decay_days) * 0.3  # 最多衰减30%
        else:
            return 0.7  # 最小权重

    def _calculate_domain_relevance(self, categories: List[str]) -> float:
        """根据论文分类计算领域相关性权重"""
        max_weight = 1.0
        for category in categories:
            if category in self.domain_weights:
                max_weight = max(max_weight, self.domain_weights[category])
        return max_weight

    def _detect_cooccurrence(self, keywords: List[str], text: str) -> float:
        """检测关键词共现，提升相关性"""
        text_lower = text.lower()
        found_keywords = []

        for keyword in keywords:
            if keyword.lower() in text_lower:
                found_keywords.append(keyword)

        # 共现奖励 - 同时出现多个关键词时给予额外分数
        cooccurrence_count = len(found_keywords)
        if cooccurrence_count >= 2:
            # 共现奖励系数
            return 1.0 + (cooccurrence_count - 1) * 0.2
        return 1.0

    def _calculate_position_weight(self, keyword: str, title: str, summary: str) -> Dict[str, float]:
        """计算关键词在不同位置的权重"""
        weights = {"title": 0.0, "summary_start": 0.0, "summary_mid": 0.0}

        keyword_lower = keyword.lower()
        title_lower = title.lower()
        summary_lower = summary.lower()

        # 标题中的权重
        if keyword_lower in title_lower:
            title_words = title_lower.split()
            keyword_position = -1
            for i, word in enumerate(title_words):
                if keyword_lower in word:
                    keyword_position = i
                    break

            if keyword_position != -1:
                # 标题开头的词权重更高
                position_factor = max(0.5, 1.0 - (keyword_position / len(title_words)) * 0.5)
                weights["title"] = 3.0 * position_factor

        # 摘要中的权重 - 区分前半部分和后半部分
        if keyword_lower in summary_lower:
            summary_length = len(summary_lower)
            keyword_pos = summary_lower.find(keyword_lower)

            if keyword_pos < summary_length * 0.3:  # 前30%
                weights["summary_start"] = 2.5
            else:  # 其他位置
                weights["summary_mid"] = 1.5

        return weights

    def calculate_advanced_relevance_score(
        self,
        paper: Dict[str, Any],
        interest_keywords: List[str] = None,
        exclude_keywords: List[str] = None,
        use_semantic_boost: bool = True,
        use_author_analysis: bool = True,
        raw_interest_keywords: List[str] = None,
    ) -> Tuple[float, bool, List[str], List[str], Dict[str, Any]]:
        """
        高级相关性评分计算 (包含更多智能特性)

        Args:
            paper: 论文信息字典
            interest_keywords: 关注词条列表
            exclude_keywords: 排除词条列表
            use_semantic_boost: 是否使用语义增强
            use_author_analysis: 是否分析作者信息

        Returns:
            tuple: (relevance_score, is_excluded, matched_interests, matched_excludes, score_breakdown)
        """
        # 基础评分
        base_score, excluded, matched_interests, matched_excludes = self.calculate_relevance_score(
            paper, interest_keywords, exclude_keywords, raw_interest_keywords
        )

        if excluded:
            return base_score, excluded, matched_interests, matched_excludes, {}

        score_breakdown = {
            "base_score": base_score,
            "semantic_boost": 0.0,
            "author_boost": 0.0,
            "novelty_boost": 0.0,
            "citation_potential": 0.0,
        }

        total_score = base_score

        # 语义增强分析
        if use_semantic_boost and interest_keywords:
            semantic_boost = self._calculate_semantic_boost(paper, interest_keywords)
            score_breakdown["semantic_boost"] = semantic_boost
            total_score += semantic_boost

        # 作者分析增强
        if use_author_analysis:
            author_boost = self._calculate_author_relevance(paper, interest_keywords)
            score_breakdown["author_boost"] = author_boost
            total_score += author_boost

        # 新颖性分析
        novelty_boost = self._calculate_novelty_score(paper)
        score_breakdown["novelty_boost"] = novelty_boost
        total_score += novelty_boost

        # 引用潜力预测
        citation_potential = self._predict_citation_potential(paper)
        score_breakdown["citation_potential"] = citation_potential
        total_score += citation_potential

        return total_score, excluded, matched_interests, matched_excludes, score_breakdown

    def _calculate_semantic_boost(self, paper: Dict[str, Any], keywords: List[str]) -> float:
        """计算语义相关性增强分数"""
        title = paper.get("title", "").lower()
        summary = paper.get("summary", "").lower()

        # 技术术语共现分析
        tech_terms = [
            "neural",
            "learning",
            "model",
            "algorithm",
            "method",
            "approach",
            "framework",
            "system",
            "network",
            "optimization",
            "training",
            "inference",
            "prediction",
            "classification",
            "regression",
        ]

        tech_term_count = sum(1 for term in tech_terms if term in title + " " + summary)

        # 基于技术密度的语义增强
        semantic_boost = min(tech_term_count * 0.1, 1.0)

        # 关键词语境分析
        context_boost = 0.0
        for keyword in keywords:
            keyword_lower = keyword.lower()

            # 寻找关键词附近的相关术语
            for text in [title, summary]:
                sentences = re.split(r"[.!?]", text)
                for sentence in sentences:
                    if keyword_lower in sentence:
                        # 分析句子中的其他技术术语
                        sentence_tech_terms = sum(1 for term in tech_terms if term in sentence)
                        context_boost += sentence_tech_terms * 0.05

        return semantic_boost + min(context_boost, 0.5)

    def _calculate_author_relevance(self, paper: Dict[str, Any], keywords: List[str]) -> float:
        """基于作者信息计算相关性增强"""
        authors = paper.get("authors", [])
        if not authors:
            return 0.0

        # 作者数量对研究质量的影响 (适中的作者数量通常较好)
        author_count = len(authors)
        if 2 <= author_count <= 6:
            author_count_boost = 0.2
        elif author_count == 1:
            author_count_boost = 0.1  # 单作者可能是理论性强的工作
        else:
            author_count_boost = 0.0  # 作者过多可能质量参差不齐

        # 分析作者姓名中的机构信息 (通过邮箱域名等)
        institution_boost = 0.0
        # 这里可以扩展为从作者附加信息中提取机构相关性

        return author_count_boost + institution_boost

    def _calculate_novelty_score(self, paper: Dict[str, Any]) -> float:
        """计算论文新颖性分数"""
        title = paper.get("title", "").lower()
        summary = paper.get("summary", "").lower()

        # 新颖性指示词
        novelty_indicators = [
            "novel",
            "new",
            "first",
            "introduce",
            "propose",
            "present",
            "innovative",
            "breakthrough",
            "pioneer",
            "original",
            "unprecedented",
            "state-of-the-art",
            "sota",
            "outperform",
            "improve",
            "enhance",
            "advance",
            "superior",
            "better than",
        ]

        novelty_count = 0
        for indicator in novelty_indicators:
            novelty_count += len(re.findall(r"\b" + re.escape(indicator) + r"\b", title + " " + summary))

        # 标题中的新颖性词汇权重更高
        title_novelty = sum(1 for indicator in novelty_indicators if indicator in title)

        novelty_score = min((novelty_count * 0.1) + (title_novelty * 0.2), 1.0)
        return novelty_score

    def _predict_citation_potential(self, paper: Dict[str, Any]) -> float:
        """预测论文的引用潜力"""
        title = paper.get("title", "").lower()
        summary = paper.get("summary", "").lower()
        categories = paper.get("categories", [])

        # 高引用潜力指标
        high_impact_terms = [
            "benchmark",
            "dataset",
            "survey",
            "review",
            "framework",
            "open source",
            "code available",
            "reproducible",
            "evaluation",
            "comparison",
            "analysis",
            "comprehensive",
            "extensive",
        ]

        impact_count = sum(1 for term in high_impact_terms if term in title + " " + summary)

        # 热门领域加权
        hot_categories = ["cs.AI", "cs.LG", "cs.CV", "cs.CL", "cs.RO"]
        category_boost = 0.2 if any(cat in hot_categories for cat in categories) else 0.0

        # 论文长度预测 (更长的摘要通常表示更全面的工作)
        length_boost = min(len(summary) / 1000, 0.3)  # 摘要长度归一化

        citation_potential = min((impact_count * 0.15) + category_boost + length_boost, 1.0)
        return citation_potential
