"""Public paper-ranking facade."""

from __future__ import annotations

from .advanced import AdvancedScoringMixin
from .keywords import KeywordMatchingMixin
from .scoring import BaseScoringMixin


class PaperRanker(KeywordMatchingMixin, BaseScoringMixin, AdvancedScoringMixin):
    """论文智能排序和过滤类"""

    def __init__(self):
        """初始化排序器"""
        # 关键词权重分层
        self.keyword_weights = {
            "core": 2.5,  # 核心关键词权重（🎯标记的关键词）
            "extended": 1.5,  # 扩展关键词权重（🔧标记的关键词）
            "related": 1.0,  # 相关关键词权重
            "default": 1.0,  # 默认权重
        }

        # 匹配缓存
        self._match_cache = {}
        self._max_cache_size = 1000

        # 同义词词典 - 可以扩展
        self.synonyms = {
            "robot": ["robotics", "robotic", "autonomous agent", "android", "humanoid"],
            "ai": ["artificial intelligence", "machine intelligence", "intelligent system"],
            "ml": ["machine learning", "statistical learning", "automated learning"],
            "dl": ["deep learning", "neural network", "neural net", "deep neural network"],
            "cv": ["computer vision", "visual perception", "image analysis", "visual recognition"],
            "nlp": ["natural language processing", "language processing", "text processing"],
            "llm": ["large language model", "language model", "generative model"],
            "vla": ["vision language action", "vision-language-action", "multimodal action"],
            "slam": ["simultaneous localization and mapping", "localization and mapping"],
            "rl": ["reinforcement learning", "reward learning", "policy learning"],
            "transformer": ["attention mechanism", "self-attention", "multi-head attention"],
        }

        # 常见缩写扩展
        self.abbreviations = {
            "ai": "artificial intelligence",
            "ml": "machine learning",
            "dl": "deep learning",
            "cv": "computer vision",
            "nlp": "natural language processing",
            "llm": "large language model",
            "vla": "vision language action",
            "slam": "simultaneous localization and mapping",
            "rl": "reinforcement learning",
            "gnn": "graph neural network",
            "cnn": "convolutional neural network",
            "rnn": "recurrent neural network",
            "lstm": "long short term memory",
            "bert": "bidirectional encoder representations from transformers",
            "gpt": "generative pre-trained transformer",
        }

        # 技术领域关键词权重
        self.domain_weights = {
            "cs.AI": 1.5,
            "cs.LG": 1.4,
            "cs.RO": 1.3,
            "cs.CV": 1.2,
            "cs.CL": 1.2,
        }
