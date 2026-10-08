"""Rules about sending a document, from "Web Service Design Assumptions and Limitations"."""

from __future__ import annotations

from dataclasses import dataclass, field

# Message.xsd HeaderType/Verb, in ERCOT's order. All lower case.
VERBS = (
    "cancel", "canceled", "change", "changed", "create", "created", "close", "closed",
    "delete", "deleted", "get", "reply", "submit", "update", "updated",
)  # fmt: skip

# ERCOT processes these first-in-first-out per participant; for a BidSet, create,
# change and update are interchangeable, so arrival order decides the result.
SEQUENCED_VERBS = frozenset({"create", "change", "update", "cancel"})
SEQUENCED_NOUNS = frozenset({"BidSet", "OutageSet", "ResParametersSet", "Dispute", "VDIs"})

# Reply/ReplyCode is an unconstrained xsd:string; these are the documented values.
REPLY_CODES = ("OK", "ERROR", "FATAL")
# Error/severity in ErcotCommonTypes.xsd. INFORMATIVE appears on successful replies.
ERROR_SEVERITIES = ("ERROR", "WARNING", "INFORMATIVE")
# Union of three status lists ERCOT publishes that do not agree with each other.
RESPONSE_STATUSES = frozenset(
    {"SUBMITTED", "PENDING", "ACCEPTED", "UNCONFIRMED", "REJECTED", "ERRORS", "CANCELED"}
)

# "must be less than 3 Mb in size(Pre-compression)"; read as 3,000,000 bytes.
MAX_PAYLOAD_BYTES = 3_000_000
# "payloads that would otherwise exceed 1 megabyte ... should be zipped, base64 encoded".
COMPRESS_ABOVE_BYTES = 1_000_000


def error_is_trouble(severity: str | None) -> bool:
    """Whether an <error> should stop a reply being trusted. A missing severity counts."""
    s = (severity or "").strip().upper()
    return s in ("", "ERROR", "WARNING")


def check_size(payload_bytes: int, label: str = "BidSet") -> str | None:
    """None if the payload is under ERCOT's pre-compression limit, else the reason."""
    if payload_bytes < MAX_PAYLOAD_BYTES:
        return None
    return (
        f'{label} is {payload_bytes:,} bytes. ERCOT: a BidSet "must be less than 3 Mb in '
        'size(Pre-compression)"; this tool reads 3 Mb as 3,000,000 bytes.'
    )


def should_compress(payload_bytes: int) -> bool:
    return payload_bytes > COMPRESS_ABOVE_BYTES


@dataclass(frozen=True)
class Transaction:
    verb: str
    noun: str
    key: str  # the mRID, or the business key behind it
    payload_bytes: int = 0

    @property
    def sequenced(self) -> bool:
        return self.verb in SEQUENCED_VERBS and self.noun in SEQUENCED_NOUNS


@dataclass
class Plan:
    steps: list[Transaction] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)
    serial_groups: dict[str, list[Transaction]] = field(default_factory=dict)

    @property
    def safe(self) -> bool:
        return not self.problems


def plan(transactions: list[Transaction]) -> Plan:
    """Group related transactions that must be sent one at a time.

    ERCOT keeps first-in-first-out order for what it receives, but two
    concurrent requests have no defined arrival order.
    """
    p = Plan()
    for t in transactions:
        why = check_size(t.payload_bytes, t.noun)
        if why:
            p.problems.append(why)
        if t.verb not in VERBS:
            p.problems.append(f"{t.verb!r} is not an EWS verb")
        if t.sequenced:
            p.serial_groups.setdefault(f"{t.noun}:{t.key}", []).append(t)
    for k in sorted(p.serial_groups):
        p.steps.extend(p.serial_groups[k])
    p.steps.extend(t for t in transactions if not t.sequenced)
    for k, group in p.serial_groups.items():
        if len(group) > 1:
            p.problems.append(
                f"{len(group)} transactions on {k} ({', '.join(t.verb for t in group)}): send "
                "them one at a time and wait for each synchronous reply."
            )
    return p
