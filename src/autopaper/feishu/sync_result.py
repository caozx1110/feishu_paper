"""Structured result objects for Feishu paper sync."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class FeishuSyncResult:
    """Outcome of one Feishu Bitable sync attempt.

    ``success`` describes whether the write path completed without data-loss
    risk. Non-critical notification/view issues may be reported in ``errors``
    while still leaving ``success`` true.
    """

    success: bool
    synced_count: int = 0
    failed_count: int = 0
    would_sync_count: int = 0
    skipped_existing: int = 0
    skipped_threshold: int = 0
    total_existing: int = 0
    table_id: str = ""
    table_name: str = ""
    research_area: str = ""
    errors: list[str] = field(default_factory=list)
    notification_sent: bool | None = None
    disabled: bool = False
    reason: str = ""

    def __bool__(self) -> bool:
        return self.success

    def __int__(self) -> int:
        return self.synced_count

    @classmethod
    def skipped(cls, reason: str, *, disabled: bool = False) -> "FeishuSyncResult":
        return cls(success=True, disabled=disabled, reason=reason)

    @classmethod
    def failed(cls, error: str, **kwargs) -> "FeishuSyncResult":
        return cls(success=False, errors=[error], reason=error, **kwargs)
