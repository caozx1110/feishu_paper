"""Date conversion helpers for Feishu Bitable payloads."""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from typing import Any

FEISHU_DATE_TIMEZONE = timezone(timedelta(hours=8))


def to_feishu_timestamp_millis(value: Any) -> int | None:
    """Convert date-like values to Feishu millisecond timestamps.

    Feishu date fields are displayed as calendar dates in the tenant's local
    timezone. Historical AutoPaper configs use China Standard Time, so naive
    dates are interpreted as Asia/Shanghai midnight instead of the host
    machine's timezone.
    """
    if value is None:
        return None

    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=FEISHU_DATE_TIMEZONE)
        return int(dt.timestamp() * 1000)

    if isinstance(value, date):
        dt = datetime.combine(value, time.min, tzinfo=FEISHU_DATE_TIMEZONE)
        return int(dt.timestamp() * 1000)

    if isinstance(value, str):
        try:
            dt = datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=FEISHU_DATE_TIMEZONE)
        except ValueError:
            return None
        return int(dt.timestamp() * 1000)

    return None
