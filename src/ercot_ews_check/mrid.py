"""ERCOT transaction IDs (mRIDs): key strings, short forms, and what a cancel reaches.

A BidSet mRID is ``<QSE>.<YYYYMMDD>.<key string>[.<hour or hour range>]``. On a
cancel, a missing hour suffix means every hour of the trading date: "If the hour
is not provided, all hours will be canceled."
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from ercot_ews_check import dst

# Short key per payload, from "Querying Bids, Offers, Trades and Schedules".
SHORT_KEYS: dict[str, str] = {
    "ASOffer": "ASO",
    "ASOnlyOffer": "AOO",
    "ASTrade": "AST",
    "CapacityTrade": "CT",
    "COP": "COP",
    "CRR": "CRR",
    "EnergyBid": "EB",
    "EnergyOnlyOffer": "EOO",
    "EnergyTrade": "ET",
    "IncDecOffer": "IDO",
    "OutputSchedule": "OS",
    "PTPObligation": "PTP",
    "RTMEnergyBid": "REB",
    "SelfArrangedAS": "SAA",
    "SelfSchedule": "SS",
    "ThreePartOffer": "TPO",
}

# Full key string per payload, from "Management and use of transaction IDs (mRIDs)".
KEY_STRING: dict[str, str] = {
    "ASOffer": "ASO.resource.asType",
    "ASOnlyOffer": "AOO.asType.bidID",
    "ASTrade": "AST.asType.buyer.seller",
    "AVP": "AVP.resource.avpType",
    "CapacityTrade": "CT.buyer.seller",
    "COP": "COP.resource",
    "CRR": "CRR.crrId.offerid.crrAHId.source.sink",
    "EnergyBid": "EB.sp.bidID",
    "EnergyOnlyOffer": "EOO.sp.bidID",
    "EnergyTrade": "ET.sp.buyer.seller",
    "EFC": "EFC.resource",
    "OutputSchedule": "OS.resource",
    "PTPObligation": "PTP.bidID.source.sink",
    "RTMEnergyBid": "REB.resource",
    "SelfArrangedAS": "SAA.asType",
    "SelfSchedule": "SS.source.sink",
    "ThreePartOffer": "TPO.resource",
}

# Four short mRIDs carry tokens after the code. This is a table, not a prefix of
# KEY_STRING: PTP and CRR drop their middle tokens.
SHORT_MRID_EXTRA: dict[str, tuple[str, ...]] = {
    "CRR": ("Source", "Sink"),
    "EnergyBid": ("SP",),
    "EnergyOnlyOffer": ("SP",),
    "PTPObligation": ("Source", "Sink"),
}

# Resource-parameter, VDI and outage IDs have no trading date and no hour suffix.
RES_PARAM_CODES = {
    "GenResourceParameters": "GEN",
    "ControllableLoadResource": "CON",
    "NonControllableLoadResource": "NON",
    "ResourceParameters": "RES",
}
HOURLESS_FAMILIES = {
    "OTG": "an outage ID (<QSEID>.OTG.<outageType>.<outageCategory>.<outageIdent>)",
    "VDI": "a Verbal Dispatch Instruction ID (QSEID.VDI.<resource>)",
    **{c: f"a resource-parameter ID (QSEID.{c}.<resource>)" for c in RES_PARAM_CODES.values()},
}

# "a COP submission can not be canceled, as it is required and can otherwise only be updated."
CANNOT_BE_CANCELED = frozenset({"COP"})

# Code -> number of key-string tokens, so a numeric key value is not read as an hour.
_KEY_TOKENS = {ks.split(".")[0]: len(ks.split(".")) for ks in KEY_STRING.values()}

_DATE = re.compile(r"\d{8}")
_HOURS = re.compile(r"^(\d{1,2}R?)(?:-(\d{1,2}R?))?$", re.I)


def _rank(token: str) -> tuple[int, int]:
    t = token.upper()
    return int(t.rstrip("R")), 1 if t.endswith("R") else 0


def _trading_date(mrid: str) -> date | None:
    parts = mrid.split(".")
    if len(parts) < 2 or not _DATE.fullmatch(parts[1]):
        return None
    try:
        return date(int(parts[1][:4]), int(parts[1][4:6]), int(parts[1][6:]))
    except ValueError:
        return None


@dataclass(frozen=True)
class CancelScope:
    """What a cancel mRID reaches. ``hours`` holds ERCOT's tokens; None means every hour."""

    hours: tuple[str, ...] | None
    suffix: str
    day_hours: int | None = None
    named_but_absent: tuple[str, ...] = ()
    family: str = ""  # set when the ID is not a BidSet mRID at all

    @property
    def whole_day(self) -> bool:
        return self.hours is None and not self.family

    def __str__(self) -> str:
        if self.family:
            what = HOURLESS_FAMILIES.get(self.family, "not a BidSet mRID")
            return f"not a BidSet mRID: this is {what}; it has no hours"
        if self.whole_day:
            return "every hour of the trading date (no hour suffix)"
        if self.named_but_absent:
            return (
                f"the suffix names {', '.join(self.named_but_absent)}, which a "
                f"{self.day_hours}-hour day does not have"
            )
        if len(self.hours) == 1:
            return f"hour {self.hours[0]} only"
        return f"hours {self.hours[0]} through {self.hours[-1]}"


def cancel_scope(mrid: str) -> CancelScope:
    """Read what a cancel of ``mrid`` would reach, before sending it."""
    parts = mrid.split(".")
    if len(parts) < 2 or not _DATE.fullmatch(parts[1]):
        return CancelScope(None, "", family=parts[1] if len(parts) > 1 else "?")
    tail = parts[-1]
    key_tokens = _KEY_TOKENS.get(parts[2]) if len(parts) > 2 else None
    has_suffix = len(parts) == 3 + key_tokens if key_tokens else len(parts) > 3
    m = _HOURS.match(tail) if has_suffix else None
    if not m:
        return CancelScope(None, "")
    lo, hi = m.group(1).upper(), (m.group(2) or m.group(1)).upper()
    if _rank(hi) < _rank(lo):
        lo, hi = hi, lo
    d = _trading_date(mrid)
    seq = dst.hour_tokens(d) if d else dst.hour_tokens(date(2010, 11, 7))
    hours = tuple(t for t in seq if _rank(lo) <= _rank(t) <= _rank(hi))
    ranks = {_rank(t) for t in seq}
    absent = tuple(t for t in dict.fromkeys((lo, hi)) if _rank(t) not in ranks)
    return CancelScope(hours, tail, len(seq) if d else None, absent)


def short_mrid(qse: str, trading_date: date, payload: str, *values: str) -> str:
    """The partial mRID that names every transaction of one type for a day."""
    code = SHORT_KEYS.get(payload)
    if code is None:
        raise KeyError(f"{payload!r} is not in ERCOT's short-mRID table")
    want = SHORT_MRID_EXTRA.get(payload, ())
    if len(values) != len(want):
        raise ValueError(
            f"a short mRID for {payload} is <QSE>.<TradingDate>.{'.'.join((code, *want))}; "
            f"got {len(values)} extra token(s)"
        )
    return ".".join((qse, f"{trading_date:%Y%m%d}", code, *values))
