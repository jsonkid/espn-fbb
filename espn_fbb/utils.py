from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

ET_ZONE = ZoneInfo("America/New_York")


def now_et() -> datetime:
    return datetime.now(tz=ET_ZONE)


def et_date_str(dt: datetime | None = None) -> str:
    target = dt or now_et()
    return target.astimezone(ET_ZONE).date().isoformat()


def iso_ts(dt: datetime | None = None) -> str:
    target = dt or now_et()
    return target.astimezone(ET_ZONE).replace(microsecond=0).isoformat()
