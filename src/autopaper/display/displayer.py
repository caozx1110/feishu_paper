"""Public display facade."""

from __future__ import annotations

import os

from .advanced import AdvancedDisplayMixin
from .console import ConsoleDisplayMixin
from .reports import ReportWriterMixin


class PaperDisplayer(ConsoleDisplayMixin, ReportWriterMixin, AdvancedDisplayMixin):
    """论文显示类"""

    def __init__(self, output_dir: str = "outputs"):
        """初始化显示器"""
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
