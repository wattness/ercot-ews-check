"""Field rules from the Values column of ERCOT's requirement tables, as runnable checks.

Only rules the prose states plainly are parsed: hour boundaries, numeric bounds,
enumerations, "before trade date" and "value ignored". Anything else is counted
by :func:`coverage` as unparsed rather than approximated.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from datetime import date, datetime
from functools import lru_cache

from ercot_ews_check import requirements

HOUR_BOUNDARY = "hour-boundary"
NUMERIC = "numeric-bound"
ENUM = "enumerated"
BEFORE_DATE = "before-trade-date"
IGNORED = "value-ignored"

_HOUR = re.compile(r"valid\s+(?:start\s+|end\s+)?hour\s+boundary", re.I)
_BEFORE = re.compile(r"valid\s+time\s+(before|before or during)\s+(?:the\s+)?trade\s+date", re.I)
_IGNORED = re.compile(r"value\s+ignored\s+if\s+provided|^\s*not used", re.I)
_GE = re.compile(r"(?:&gt;=|>=)\s*(-?\d+(?:\.\d+)?)")
_LE = re.compile(r"(?:&lt;=|<=)\s*(-?\d+(?:\.\d+)?)")
_BETWEEN = re.compile(r"between\s+(-?\d+(?:\.\d+)?)\s+and\s+(-?\d+(?:\.\d+)?)", re.I)
_STATED = re.compile(r"\bValid\b|Required if|Must be|cannot|only if|Default \(|Enumeration", re.I)


@dataclass(frozen=True)
class Constraint:
    kind: str
    field: str
    source: str  # ERCOT's Values text, verbatim
    lo: float | None = None
    hi: float | None = None
    values: tuple[str, ...] = ()
    advisory: bool = False  # reported, never blocking
    advisory_why: str = ""
    see: tuple[str, ...] = ()  # discrepancy IDs

    def check(self, value: str) -> str | None:
        """None if ``value`` satisfies the rule, else why not."""
        if self.kind == HOUR_BOUNDARY:
            if "T24:" in value:  # reported by the checker's hour-24 rule
                return None
            dt = parse_datetime(value)
            if dt is None:
                return f"{value!r} is not a timestamp"
            if (dt.minute, dt.second, dt.microsecond) != (0, 0, 0):
                return f"{value} is not on an hour boundary"
        elif self.kind == NUMERIC:
            try:
                x = float(value)
            except ValueError:
                return f"{value!r} is not a number"
            if self.lo is not None and x < self.lo:
                return f"{value} is below ERCOT's minimum of {self.lo:g}"
            if self.hi is not None and x > self.hi:
                return f"{value} is above ERCOT's maximum of {self.hi:g}"
        elif self.kind == ENUM and value not in self.values:
            return f"{value!r} is not one of {list(self.values)}"
        return None

    def check_before(self, value: str, trade_date: date) -> str | None:
        dt = parse_datetime(value)
        if dt is None:
            return f"{value!r} is not a timestamp"
        if dt.date() >= trade_date:
            return f"{value} is not before the trade date {trade_date}"
        return None

    def violation(self, value: str, trade_date: date | None) -> str | None:
        """Why ``value`` breaks the rule, or None. Date rules need the trade date."""
        if self.kind == BEFORE_DATE:
            return self.check_before(value, trade_date) if trade_date else None
        return self.check(value)


def parse_datetime(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError:
        return None


def _parse(field: str, cell: dict) -> Constraint | None:
    spec = str(cell.get("spec") or "")
    if not spec:
        return None
    if _IGNORED.search(spec):
        return Constraint(IGNORED, field, spec)
    if _HOUR.search(spec):
        return Constraint(HOUR_BOUNDARY, field, spec)
    if _BEFORE.search(spec):
        # ERCOT's Appendix E samples put expirationTime on the trade date itself,
        # so the strict reading would reject documents ERCOT publishes.
        return Constraint(
            BEFORE_DATE,
            field,
            spec,
            advisory=True,
            advisory_why=(
                "ERCOT's own Appendix E samples set expirationTime on the trade date, "
                'and the pages differ ("before" vs "before or during")'
            ),
        )
    if cell.get("enum") and len(cell["enum"]) > 1:
        # A single extracted value usually means the rest of the list was not quoted, and
        # a longer list may still be examples, so a value outside it is only reported.
        return Constraint(
            ENUM,
            field,
            spec,
            values=tuple(cell["enum"]),
            advisory=True,
            advisory_why="the table may list examples rather than every value; the schema "
            "enumeration decides what is legal",
        )
    between = _BETWEEN.search(spec)
    if between:
        return Constraint(NUMERIC, field, spec, lo=float(between[1]), hi=float(between[2]))
    ge, le = _GE.search(spec), _LE.search(spec)
    if ge or le:
        return Constraint(
            NUMERIC, field, spec, lo=float(ge[1]) if ge else None, hi=float(le[1]) if le else None
        )
    if cell.get("range"):
        lo, hi = cell["range"]
        try:
            return Constraint(NUMERIC, field, spec, lo=float(lo), hi=float(hi))
        except ValueError:
            return None
    return None


@lru_cache(maxsize=1)
def _all() -> tuple[dict[str, dict[str, Constraint]], int]:
    out: dict[str, dict[str, Constraint]] = {}
    unparsed = 0
    for page, cells in requirements.tables().items():
        got = {}
        for field, cell in cells.items():
            c = _parse(field, cell)
            if c is not None:
                got[field] = c
            elif _STATED.search(str(cell.get("spec") or "")):
                unparsed += 1
        if got:
            out[page] = got
    return out, unparsed


# Table bounds that ERCOT's Protocols contradict for some resources: reported, not blocking.
CONTRADICTED_BOUNDS: dict[tuple[str, str], tuple[str, str]] = {
    ("COP", f"Limits/{name}"): (
        "the Protocols allow an Energy Storage Resource's HSL and LSL below zero",
        "D033",
    )
    for name in ("hsl", "lsl")
}


def for_tag(tag: str) -> dict[str, Constraint]:
    """Constraints for a BidSet payload, keyed by corrected element path."""
    page = requirements.page_for(tag)
    found = _all()[0].get(page, {}) if page else {}
    out = {}
    for path, c in found.items():
        path = requirements._fix(path, tag)
        if (tag, path) in CONTRADICTED_BOUNDS:
            why, ref = CONTRADICTED_BOUNDS[(tag, path)]
            c = replace(c, advisory=True, advisory_why=why, see=(ref,))
        out[path] = c
    return out


def coverage() -> dict[str, int]:
    found, unparsed = _all()
    by_kind: dict[str, int] = {}
    for fields in found.values():
        for c in fields.values():
            by_kind[c.kind] = by_kind.get(c.kind, 0) + 1
    return {
        "pages": len(found),
        "constraints": sum(len(f) for f in found.values()),
        "unparsed": unparsed,
        **by_kind,
    }
