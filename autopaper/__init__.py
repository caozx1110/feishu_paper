"""
autopaper - 自动化论文处理包

提供ArXiv论文抓取、处理和飞书同步功能。
"""

# 版本信息
__version__ = "0.1.0"

# 导入飞书核心模块
from .core.feishu import FeishuConfig, FeishuConnector, BitableManager, ChatNotifier, SyncManager

# 导入ArXiv和论文处理模块
from .core.arxiv_processor import ArxivAPI
from .core.paper_ranker import PaperRanker
from .utils.paper_display import PaperDisplayer

# 导出主要接口
__all__ = [
    # 飞书模块
    "FeishuConfig",
    "FeishuConnector",
    "BitableManager",
    "ChatNotifier",
    "SyncManager",
    # ArXiv和论文处理模块
    "ArxivAPI",
    "PaperRanker",
    "PaperDisplayer",
]
