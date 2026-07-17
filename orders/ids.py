"""Szempont M4 — SZP- order id sequence (R4).

Format: SZP-YYMM-NNNN — human-readable month bucket + 4-digit sequence
(ClearVisio's SO- ids stay in legacy_order_id, R18; Szempont never mints
SO-). next_order_id derives max+1 from the ids already in the store, so the
allocator needs no extra sequence table.

Concurrency note (recorded in F-W3-02): max+1 over a read snapshot can race
under concurrent order creation. Accepted for the single-store terminal
reality (one POS, sub-hundred orders/day); both stores double-check id
uniqueness at save time and refuse duplicates, so a race surfaces as a loud
save error, never as two orders sharing an id. Revisit with M5 if a second
terminal appears.
"""

from __future__ import annotations

import datetime as dt
import re
from typing import Iterable

_ID_RE = re.compile(r"^SZP-(\d{4})-(\d{4,})$")


def format_order_id(month_bucket: str, seq: int) -> str:
    if seq < 1:
        raise ValueError(f"sequence starts at 1, got {seq}")
    return f"SZP-{month_bucket}-{seq:04d}"


def month_bucket(day: dt.date) -> str:
    return f"{day:%y%m}"


def next_order_id(existing_ids: Iterable[str], day: dt.date) -> str:
    """Smallest unused SZP-YYMM-NNNN for the given day's month bucket."""
    bucket = month_bucket(day)
    top = 0
    for oid in existing_ids:
        m = _ID_RE.match(oid or "")
        if m and m.group(1) == bucket:
            top = max(top, int(m.group(2)))
    return format_order_id(bucket, top + 1)
