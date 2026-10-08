"""Payloads and fields ERCOT withdrew with RTC+B, per interface.

A withdrawal reaches the schemas, the query enumerations and the prose at
different times, so each item records its state on each surface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Release Date of the "RTC+B Updates" rows on the EWS Document Revisions page.
RTC_B_RELEASE = date(2025, 12, 5)

GONE = "gone"  # removed from the schema
ENUMERATED = "enumerated"  # still schema-legal, marked for removal
STALE = "stale"  # ERCOT's prose still mentions it


@dataclass(frozen=True)
class Withdrawn:
    name: str
    submit: str
    query: str
    docs: str
    released: date
    evidence: tuple[str, ...]
    stale_pages: tuple[str, ...] = ()
    also_known_as: tuple[str, ...] = ()  # wire nouns and codes for the same thing

    def may_submit(self) -> bool:
        return self.submit != GONE

    def why_not(self) -> str:
        return f"{self.name} was removed in the release of {self.released}: {self.evidence[0]}"


WITHDRAWN: dict[str, Withdrawn] = {
    "IncDecOffer": Withdrawn(
        name="IncDecOffer",
        submit=GONE,
        query=ENUMERATED,
        docs=STALE,
        released=RTC_B_RELEASE,
        evidence=(
            "ErcotTransactions.xsd and ErcotTransactionTypes.xsd comment it out behind "
            "<!-- RTC+B: Removed -->",
            'Document Revisions: "Remove Incremental and Decremental Energy Offer Curves (IDO)"',
            'ErcotGetNotifications.xsd keeps IDO in BidType behind "RTC+B: No longer used and '
            'will be removed in future release"',
        ),
        stale_pages=(
            "Market Information Messages/DAM Phase II Validation Results",
            "Market Transaction Messages/Incremental and Decremental Energy Offer Curves (IDO)",
            "Appendices/Appendix E: SOAP Examples",
        ),
        also_known_as=("IDO",),
    ),
    "SASM": Withdrawn(
        name="SASM",
        submit=GONE,
        query=GONE,
        docs=STALE,
        released=RTC_B_RELEASE,
        evidence=(
            'Message.xsd: "Version 0.3.5 RTC+B Changes: Removed SASM from MarketType"',
            'Document Revisions: "Removed Get SASM ID List request"',
        ),
        stale_pages=(
            "Utility Interface Messages/Get SASM ID List",
            "Market Information Messages/AwardSet",
        ),
        also_known_as=("SASMIDList", "Get SASM ID List"),
    ),
    "rrcUnprocuredL": Withdrawn(
        name="rrcUnprocuredL",
        submit=GONE,
        query=ENUMERATED,
        docs=STALE,
        released=RTC_B_RELEASE,
        evidence=(
            'System Parameters table: the description of rrcUnprocuredL is "This field will '
            'be removed"',
        ),
        stale_pages=("Market Information Messages/System Parameters",),
    ),
}

_BY_ANY_NAME = {
    alias: key for key, w in WITHDRAWN.items() for alias in (key, w.name, *w.also_known_as)
}


def withdrawal_for(name: str) -> Withdrawn | None:
    """The withdrawal a payload tag, noun or code refers to, if any."""
    key = _BY_ANY_NAME.get(name)
    return WITHDRAWN[key] if key else None


def may_submit(name: str) -> bool:
    w = withdrawal_for(name)
    return w is None or w.may_submit()
