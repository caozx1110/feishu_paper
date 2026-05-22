"""Keyword expansion, required-keyword logic, and enhanced matching."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple

try:
    from rapidfuzz import fuzz, process
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False
    print("⚠️  rapidfuzz 不可用，使用 difflib 作为备用方案")


class KeywordMatchingMixin:
    def check_required_keywords(
        self, paper: Dict[str, Any], required_keywords_config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        检查论文是否包含必须的关键词（支持AND和OR逻辑组合）

        支持的格式:
        - "robot" - 单个关键词
        - "A OR B" - A或B任选其一
        - ["mobile", "A OR B"] - 必须包含mobile且必须包含(A或B)

        Args:
            paper: 论文信息字典
            required_keywords_config: 必须包含关键词配置

        Returns:
            tuple: (是否通过检查, 实际匹配到的关键词列表)
        """
        if not required_keywords_config.get("enabled", False):
            return True, []

        required_keywords = required_keywords_config.get("keywords", [])
        if not required_keywords:
            return True, []

        # 提取论文文本信息
        title = paper.get("title", "").lower()
        summary = paper.get("summary", "").lower()
        categories = paper.get("categories", [])
        categories_str = " ".join(categories).lower()
        authors = paper.get("authors_str", "").lower()

        # 组合所有文本用于搜索
        full_text = f"{title} {summary} {categories_str} {authors}"

        fuzzy_match = required_keywords_config.get("fuzzy_match", True)
        similarity_threshold = required_keywords_config.get("similarity_threshold", 0.8)

        all_matched_keywords = []

        # 检查所有关键词项是否都匹配（AND逻辑：全部必须匹配）
        for keyword_item in required_keywords:
            matched_keywords = self._check_keyword_item_detailed(
                keyword_item, full_text, fuzzy_match, similarity_threshold
            )
            if matched_keywords:
                # 添加实际匹配到的关键词
                all_matched_keywords.extend(matched_keywords)
            else:
                # 如果有任何一个关键词项不匹配，则直接返回False
                return False, []

        # 所有关键词项都匹配才通过检查
        return True, all_matched_keywords

    def _check_keyword_item_detailed(
        self, keyword_item: str, full_text: str, fuzzy_match: bool, similarity_threshold: float
    ) -> List[str]:
        """
        检查单个关键词项并返回具体匹配的关键词

        Args:
            keyword_item: 关键词项，可能是单个关键词或包含OR的组合
            full_text: 论文全文
            fuzzy_match: 是否启用模糊匹配
            similarity_threshold: 模糊匹配阈值

        Returns:
            List[str]: 匹配到的具体关键词列表
        """
        # 检查是否包含OR逻辑
        if " or " in keyword_item.lower() or " OR " in keyword_item:
            return self._check_or_keyword_detailed(keyword_item, full_text, fuzzy_match, similarity_threshold)
        else:
            # 单个关键词
            if self._check_single_keyword(keyword_item, full_text, fuzzy_match, similarity_threshold):
                return [keyword_item]
            else:
                return []

    def _check_or_keyword_detailed(
        self, or_keyword: str, full_text: str, fuzzy_match: bool, similarity_threshold: float
    ) -> List[str]:
        """
        检查OR逻辑关键词并返回所有匹配的关键词

        Args:
            or_keyword: 包含OR的关键词字符串，如 "A OR B OR C"
            full_text: 论文全文
            fuzzy_match: 是否启用模糊匹配
            similarity_threshold: 模糊匹配阈值

        Returns:
            List[str]: 匹配到的具体关键词列表
        """
        # 分割OR关键词
        or_parts = []
        if " OR " in or_keyword:
            or_parts = [part.strip() for part in or_keyword.split(" OR ")]
        elif " or " in or_keyword:
            or_parts = [part.strip() for part in or_keyword.split(" or ")]

        if len(or_parts) < 2:
            return []

        matched_keywords = []
        # 检查所有部分，收集所有匹配的关键词
        for part in or_parts:
            if self._check_single_keyword(part, full_text, fuzzy_match, similarity_threshold):
                matched_keywords.append(part)

        return matched_keywords

    def _check_single_keyword(
        self, keyword: str, full_text: str, fuzzy_match: bool, similarity_threshold: float
    ) -> bool:
        """
        检查单个关键词是否匹配

        Args:
            keyword: 关键词
            full_text: 论文全文
            fuzzy_match: 是否启用模糊匹配
            similarity_threshold: 模糊匹配阈值

        Returns:
            bool: 是否匹配
        """
        keyword_lower = keyword.lower()

        # 精确匹配
        if keyword_lower in full_text:
            return True

        # 模糊匹配（如果启用）
        if fuzzy_match:
            # 检查关键词变体
            keyword_variants = self._generate_keyword_variants(keyword)

            for variant in keyword_variants:
                if variant.lower() in full_text:
                    return True

            # 使用字符串相似度匹配
            if self._fuzzy_match_required_keyword(keyword_lower, full_text, similarity_threshold):
                return True

        return False

    def _generate_keyword_variants(self, keyword: str) -> List[str]:
        """
        生成关键词变体

        Args:
            keyword: 原始关键词

        Returns:
            关键词变体列表
        """
        variants = [keyword]
        keyword_lower = keyword.lower()

        # 从同义词词典获取变体
        for syn_key, syn_list in self.synonyms.items():
            if syn_key in keyword_lower or keyword_lower in syn_key:
                variants.extend(syn_list)

        # 生成常见变体
        # 复数形式
        if not keyword.endswith("s"):
            variants.append(keyword + "s")
        if keyword.endswith("y"):
            variants.append(keyword[:-1] + "ies")

        # 形容词形式
        if keyword.endswith("e"):
            variants.append(keyword[:-1] + "ic")
        else:
            variants.append(keyword + "ic")

        # 连字符和空格变体
        if " " in keyword:
            variants.append(keyword.replace(" ", "-"))
            variants.append(keyword.replace(" ", "_"))
            variants.append(keyword.replace(" ", ""))
        if "-" in keyword:
            variants.append(keyword.replace("-", " "))
            variants.append(keyword.replace("-", "_"))
            variants.append(keyword.replace("-", ""))

        # 去除重复并返回
        return list(set(variants))

    def _fuzzy_match_required_keyword(self, keyword: str, text: str, threshold: float) -> bool:
        """
        对必须关键词进行模糊匹配

        Args:
            keyword: 关键词
            text: 待匹配文本
            threshold: 相似度阈值

        Returns:
            是否匹配
        """
        try:
            from difflib import SequenceMatcher

            # 分词处理
            words = text.split()

            # 检查与单个词的相似度
            for word in words:
                if len(word) >= 3:  # 只检查长度大于等于3的词
                    similarity = SequenceMatcher(None, keyword, word).ratio()
                    if similarity >= threshold:
                        return True

            # 检查与词组的相似度
            keyword_words = keyword.split()
            if len(keyword_words) > 1:
                for i in range(len(words) - len(keyword_words) + 1):
                    phrase = " ".join(words[i : i + len(keyword_words)])
                    similarity = SequenceMatcher(None, keyword, phrase).ratio()
                    if similarity >= threshold:
                        return True

            return False

        except ImportError:
            # 如果没有difflib，使用简单的包含检查
            return keyword in text

    def _expand_keywords(self, keywords: List[str]) -> List[str]:
        """扩展关键词列表，包含同义词和缩写"""
        expanded = set(keywords)

        for keyword in keywords:
            keyword_lower = keyword.lower()

            # 添加缩写扩展
            if keyword_lower in self.abbreviations:
                expanded.add(self.abbreviations[keyword_lower])

            # 添加同义词
            if keyword_lower in self.synonyms:
                expanded.update(self.synonyms[keyword_lower])

            # 反向查找 - 如果输入的是全称，也要包含缩写
            for abbr, full_term in self.abbreviations.items():
                if keyword_lower == full_term:
                    expanded.add(abbr)

        return list(expanded)

    def _fuzzy_match_score(self, keyword: str, text: str, threshold: float = 0.8) -> float:
        """计算模糊匹配分数 - 优化版本，使用 rapidfuzz"""
        if RAPIDFUZZ_AVAILABLE:
            return self._rapidfuzz_match_score(keyword, text, threshold)
        else:
            return self._fallback_fuzzy_match(keyword, text, threshold)

    def _rapidfuzz_match_score(self, keyword: str, text: str, threshold: float = 0.8) -> float:
        """使用 rapidfuzz 进行快速模糊匹配"""
        keyword_lower = keyword.lower()

        # 快速检查精确匹配
        if keyword_lower in text.lower():
            return 1.0

        # 分词并限制检查范围以提高效率
        words = re.findall(r"\b\w+\b", text.lower())
        if not words:
            return 0.0

        # 限制检查的词数以提高效率（rapidfuzz 很快，可以检查更多词）
        check_words = words[:100] if len(words) > 100 else words

        # 使用 rapidfuzz 进行快速模糊匹配
        best_match = process.extractOne(keyword_lower, check_words, scorer=fuzz.ratio, score_cutoff=threshold * 100)

        return best_match[1] / 100.0 if best_match else 0.0

    def _fallback_fuzzy_match(self, keyword: str, text: str, threshold: float = 0.8) -> float:
        """备用模糊匹配方法（rapidfuzz 不可用时使用 difflib）"""
        if not RAPIDFUZZ_AVAILABLE:
            import difflib

        keyword_lower = keyword.lower()

        # 快速检查精确匹配
        if keyword_lower in text.lower():
            return 1.0

        words = re.findall(r"\b\w+\b", text.lower())
        if not words:
            return 0.0

        max_similarity = 0.0
        # 限制检查的词数以提高效率（difflib 较慢，减少检查词数）
        check_words = words[:30] if len(words) > 30 else words

        for word in check_words:
            # 跳过过短的词
            if len(word) < 3:
                continue

            if RAPIDFUZZ_AVAILABLE:
                # 如果 rapidfuzz 可用，使用它
                similarity = fuzz.ratio(keyword_lower, word) / 100.0
            else:
                # 否则使用 difflib
                similarity = difflib.SequenceMatcher(None, keyword_lower, word).ratio()

            if similarity >= threshold:
                max_similarity = max(max_similarity, similarity)
                # 如果找到非常好的匹配，提前终止
                if similarity > 0.95:
                    break

        return max_similarity

    def _is_wildcard_match(self, keywords: List[str]) -> bool:
        """
        检查是否为通配符匹配（匹配所有文章）
        """
        if not keywords:
            return False

        # 检查是否包含通配符
        wildcard_patterns = ["*", "all", ".*", "全部", "所有"]
        for keyword in keywords:
            if keyword.lower().strip() in wildcard_patterns:
                return True

        # 如果只有一个关键词且为空或只有空白字符
        if len(keywords) == 1 and not keywords[0].strip():
            return True

        return False

    def _is_regex_keyword(self, keyword: str) -> bool:
        """
        检查关键词是否为正则表达式模式
        """
        return keyword.startswith("regex:") or keyword.startswith("re:")

    def _process_regex_keyword(self, keyword: str, text: str) -> bool:
        """
        处理正则表达式关键词匹配
        """
        try:
            if keyword.startswith("regex:"):
                pattern = keyword[6:].strip()  # 移除 "regex:" 前缀
            elif keyword.startswith("re:"):
                pattern = keyword[3:].strip()  # 移除 "re:" 前缀
            else:
                return False

            # 编译并匹配正则表达式
            regex = re.compile(pattern, re.IGNORECASE)
            return bool(regex.search(text))
        except re.error:
            # 如果正则表达式无效，回退到普通字符串匹配
            return keyword.lower() in text.lower()

    def _enhance_keyword_matching(self, keyword: str, text: str) -> Tuple[bool, float]:
        """
        增强的关键词匹配，支持正则表达式和通配符

        Returns:
            tuple: (是否匹配, 匹配分数)
        """
        # 正则表达式匹配
        if self._is_regex_keyword(keyword):
            matched = self._process_regex_keyword(keyword, text)
            return matched, 1.0 if matched else 0.0

        # 普通字符串匹配
        if keyword.lower() in text.lower():
            return True, 1.0

        # 模糊匹配
        fuzzy_score = self._fuzzy_match_score(keyword, text, threshold=0.8)
        if fuzzy_score > 0:
            return True, fuzzy_score

        return False, 0.0

    def _parse_keyword_weights(self, raw_keywords: List[str]) -> Dict[str, str]:
        """
        解析原始关键词列表，确定每个关键词的权重类别

        Args:
            raw_keywords: 包含注释行的原始关键词列表

        Returns:
            字典，键为关键词，值为权重类别 ('core', 'extended', 'default')
        """
        keyword_categories = {}
        current_category = "default"

        for keyword in raw_keywords:
            keyword = keyword.strip()

            # 跳过空行
            if not keyword:
                continue

            # 检查注释行，确定当前分类
            if keyword.startswith("#"):
                if "🎯" in keyword or "核心概念" in keyword or "高权重" in keyword:
                    current_category = "core"
                elif "🔧" in keyword or "扩展概念" in keyword or "中权重" in keyword:
                    current_category = "extended"
                elif "📝" in keyword or "相关概念" in keyword or "标准权重" in keyword:
                    current_category = "related"
                # 注释行本身不作为关键词
                continue

            # 为非注释的关键词分配类别
            keyword_categories[keyword] = current_category

        return keyword_categories

    def _get_keyword_weight(self, keyword: str, keyword_categories: Dict[str, str]) -> float:
        """
        获取关键词的权重倍数

        Args:
            keyword: 关键词
            keyword_categories: 关键词分类字典

        Returns:
            权重倍数
        """
        category = keyword_categories.get(keyword, "default")
        return self.keyword_weights.get(category, self.keyword_weights["default"])
