from __future__ import annotations
from datetime import datetime, timezone, timedelta

TR_TZ = timezone(timedelta(hours=3))

def now_tr() -> datetime:
    return datetime.now(TR_TZ)

def iso_now_tr() -> str:
    return now_tr().isoformat(timespec="seconds")
