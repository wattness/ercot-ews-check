"""Hour tokens on 23- and 25-hour trading days.

ERCOT spells the repeated fall-back hour two ways: ``2R`` in an mRID hour suffix
and ``2*`` (or ``02*``) in an ``hourEnding`` element.
"""

from __future__ import annotations

from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

CENTRAL = ZoneInfo("America/Chicago")
MRID_REPEAT_MARK = "R"
HOUR_ENDING_REPEAT_MARK = "*"


def _midnight(d: date) -> datetime:
    return datetime.combine(d, time(0), tzinfo=CENTRAL)


def hours_in_day(d: date) -> int:
    """23, 24 or 25."""
    a = _midnight(d).astimezone(timezone.utc)
    b = _midnight(d + timedelta(days=1)).astimezone(timezone.utc)
    return round((b - a).total_seconds() / 3600)


def trading_date(when: datetime) -> date:
    """The ERCOT trading date an instant falls on (Central time)."""
    if when.tzinfo is None:
        raise ValueError(f"{when!r} has no UTC offset")
    return when.astimezone(CENTRAL).date()


def hour_tokens(d: date) -> tuple[str, ...]:
    """ERCOT's hour-ending tokens for a trading date, in order.

    24 hours: 01 .. 24. Fall back: 01 02 2R 03 .. 24. Spring forward: 01 02 04 .. 24.
    """
    start = _midnight(d).astimezone(timezone.utc)
    out: list[str] = []
    seen: set[str] = set()
    for i in range(hours_in_day(d)):
        local = (start + timedelta(hours=i)).astimezone(CENTRAL)
        token = f"{local.hour + 1:02d}"
        if token in seen:
            out.append(f"{int(token)}{MRID_REPEAT_MARK}")  # ERCOT writes 2R, not 02R
        else:
            seen.add(token)
            out.append(token)
    return tuple(out)


def hour_index(when: datetime, d: date | None = None) -> int:
    """Which hour of the trading day an instant starts, counted in elapsed hours."""
    if when.tzinfo is None:
        raise ValueError(f"{when!r} has no UTC offset")
    d = d or trading_date(when)
    secs = (when.astimezone(timezone.utc) - _midnight(d).astimezone(timezone.utc)).total_seconds()
    if secs % 3600:
        raise ValueError(f"{when.isoformat()} is not on an hour boundary")
    return int(secs // 3600)


def hours_in_mrid(start: datetime, end: datetime) -> str | None:
    """The mRID hour suffix for [start, end), or None when it spans the whole day."""
    d = trading_date(start)
    lo, hi = hour_index(start, d), hour_index(end, d)
    toks = hour_tokens(d)
    if hi <= lo:
        raise ValueError("the window covers no whole hour")
    if hi > len(toks):
        raise ValueError(f"the window runs past the end of {d} ({len(toks)} hours)")
    if lo == 0 and hi == len(toks):
        return None
    return toks[lo] if hi - lo == 1 else f"{toks[lo]}-{toks[hi - 1]}"


def parse_hour_ending(text: str) -> tuple[int, bool]:
    """``'01'`` -> (1, False); ``'2*'`` -> (2, True); ``'01:00'`` -> (1, False)."""
    s = str(text).strip()
    repeated = s.endswith(HOUR_ENDING_REPEAT_MARK)
    s = s.rstrip(HOUR_ENDING_REPEAT_MARK).split(":")[0]
    if not s.isdigit() or not 1 <= int(s) <= 24:
        raise ValueError(f"hourEnding {text!r} is not 1-24 with an optional '*'")
    return int(s), repeated
