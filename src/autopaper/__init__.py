"""AutoPaper public package interface."""

from .arxiv_core import ArxivAPI, PaperRanker
from .feishu_bitable_connector import FeishuBitableConnector, FeishuBitableConfig
from .paper_display import PaperDisplayer
from .sync_to_feishu import sync_papers_to_feishu

__version__ = "0.1.0"


def find_sync_configs(*args, **kwargs):
    from .arxiv_hydra import find_sync_configs as _find_sync_configs

    return _find_sync_configs(*args, **kwargs)


def load_config(*args, **kwargs):
    from .arxiv_hydra import load_config as _load_config

    return _load_config(*args, **kwargs)


def process_all_configs(*args, **kwargs):
    from .arxiv_hydra import process_all_configs as _process_all_configs

    return _process_all_configs(*args, **kwargs)


def process_single_config(*args, **kwargs):
    from .arxiv_hydra import process_single_config as _process_single_config

    return _process_single_config(*args, **kwargs)


def get_default_config_dir():
    from .arxiv_hydra import DEFAULT_CONFIG_DIR

    return DEFAULT_CONFIG_DIR


def __getattr__(name: str):
    if name == "DEFAULT_CONFIG_DIR":
        return get_default_config_dir()
    raise AttributeError(f"module 'autopaper' has no attribute {name!r}")


__all__ = [
    "ArxivAPI",
    "PaperRanker",
    "PaperDisplayer",
    "FeishuBitableConnector",
    "FeishuBitableConfig",
    "sync_papers_to_feishu",
    "DEFAULT_CONFIG_DIR",
    "get_default_config_dir",
    "find_sync_configs",
    "load_config",
    "process_all_configs",
    "process_single_config",
]
