"""Submission rules from ERCOT's market documents, which its EWS pages and XSDs do not state.

ERCOT's MMS Market Submission Validation Rules (NP4-450-M, version 3.2, posted
13 February 2026) and Nodal Protocols Section 4 (the version effective
1 August 2026) bound offer prices, fix the order of the points on energy curves,
set minimum quantities, order a COP's state of charge and restrict the AS Only
Offer products. :func:`check_payload` applies them to one BidSet payload; the
checker turns what it returns into findings.

ERCOT says it rejects a submission that breaks any of these rules, so each result
is an error, with one exception: a Three-Part Offer price above the RTSWCAP but
not above the DASWCAP, when the document does not show it was sent after the
RTSWCAP took over, is a warning.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from itertools import pairwise

from ercot_ews_check import constraints, discrepancies, xsd_rules
from ercot_ews_check.dst import CENTRAL, trading_date
from ercot_ews_check.namespaces import EWS, q

ERROR, WARNING = "error", "warning"

# ERCOT's MMS Market Submission Validation Rules, posted on ercot.com, not the EWS portal.
# Quoted from version 3.2, posted 13 Feb 2026; the .docx has SHA-256
# 61e377c3f4b948c97e61a636883614fb8297d9a5f5c8327f474629e87d44e7c6.
SRC_NP4_450 = "https://www.ercot.com/mp/data-products/data-product-details?id=NP4-450-M"
# Nodal Protocols Section 4, Day-Ahead Operations: the version effective 1 August 2026, which
# ERCOT's index of current Protocols (https://www.ercot.com/mktrules/nprotocols/current) listed
# on 9 Oct 2026. The .docx has SHA-256
# 6c0fc0882f574f8b5732cbd0a895b0a3c4678fec9b908fe03e080ca90c603fbd.
SRC_PROTOCOLS = "https://www.ercot.com/files/docs/2024/06/28/04-080126_Nodal.docx"
PROTOCOLS_VERSION = "1 August 2026"

# §4.4.11(1), the table's "Current Value" column: HCAP - DAM (DASWCAP) and HCAP - RTM
# (RTSWCAP). Its footnote says the ERCOT Board approves these values and ERCOT updates them, so
# every message that uses one says where it is from. The DASWCAP falls to the ECAP or LCAP
# (2,000 in the same table) during an Emergency Pricing Program or after the Peaker Net Margin
# threshold is passed (§4.4.11(1)(a)), which a document cannot show: 5,000 is its highest value.
DASWCAP = Decimal("5000")
RTSWCAP = Decimal("2000")
# The floor for energy offer prices: §4.4.9.3.1(2), §4.4.9.5.1(2), §4.4.9.7.1(2).
ENERGY_FLOOR = Decimal("-250.00")
# §4.4.9.3.1(2): "1430 in the Day-Ahead", from which the RTSWCAP applies.
RTSWCAP_FROM = time(14, 30)
# §4.4.9.3.1(3), §4.4.9.5.1(3), §4.4.9.6.1(2): one MW.
ENERGY_MIN_MW = Decimal("1")
# NP4-450-M §2.3 and Protocols §4.4.7.2.3(4); NP4-450-M §3.4 for an RTM Energy Bid's last point.
AS_ONLY_MIN_MW = Decimal("0.1")
RTM_BID_LAST_MW = Decimal("0.1")

# NP4-450-M §2.3 restricts the AS Type of an AS Only Offer to REGUP, REGDN, RRSPF, ONNS or
# ECRSS. The XSD spells the same five products as the keys below: its comments mark these
# five, and no other ASType value, "Used for ASOnlyOffer", and its note for version 0.3.33 says
# Non-Spin is used for ASOnlyOffer rather than On-Non-Spin (ONNS is On-line Non-Spin). The AS
# Only Offer page's asType row lists the same five. XSD value -> NP4-450-M's code.
AS_ONLY_TYPES = {
    "Reg-Up": "REGUP",
    "Reg-Down": "REGDN",
    "Non-Spin": "ONNS",
    "RRSPF": "RRSPF",
    "ECRSS": "ECRSS",
}

OFFER, BID = "offer", "bid"


@dataclass(frozen=True)
class Problem:
    rule: str
    severity: str
    message: str
    where: str
    fix: str
    source: str
    see: tuple[str, ...] = ()  # catalogue entries


def np4_450(section: str) -> str:
    return f"ERCOT's Market Submission Validation Rules (NP4-450-M, {section})"


def protocols(section: str) -> str:
    return f"Nodal Protocols {section} (version of {PROTOCOLS_VERSION})"


def _cap(name: str) -> str:
    if name == "DASWCAP":
        return (
            f"the DASWCAP, which is {DASWCAP:,} at most under the Nodal Protocols version of "
            f"{PROTOCOLS_VERSION} (§4.4.11(1))"
        )
    return (
        f"the RTSWCAP, which the Nodal Protocols version of {PROTOCOLS_VERSION} sets at "
        f"{RTSWCAP:,} (§4.4.11(1))"
    )


def number(text: str | None) -> Decimal | None:
    """A finite decimal, or None for anything else."""
    try:
        value = Decimal((text or "").strip())
    except InvalidOperation:
        return None
    return value if value.is_finite() else None


@dataclass(frozen=True)
class Curve:
    tag: str  # EnergyOfferCurve, PriceCurve or ASOnlyPriceCurve
    start: str  # startTime as written
    style: str  # curveStyle, or ""
    points: tuple[tuple[Decimal | None, Decimal | None], ...]  # (MW, price) per CurveData

    def complete(self) -> list[tuple[Decimal, Decimal]] | None:
        """The points, if every one has a numeric quantity and price."""
        out = [(x, y) for x, y in self.points if x is not None and y is not None]
        return out if len(out) == len(self.points) else None

    def prices(self) -> list[Decimal]:
        return [y for _, y in self.points if y is not None]

    def quantities(self) -> list[Decimal]:
        return [x for x, _ in self.points if x is not None]

    def label(self, payload: str) -> str:
        return f"{payload} {self.tag} from {self.start or '(no startTime)'}"


def curves(payload: ET.Element, tag: str) -> list[Curve]:
    out = []
    for el in payload.findall(q(EWS, tag)):
        points = tuple(
            (number(cd.findtext(q(EWS, "xvalue"))), number(cd.findtext(q(EWS, "y1value"))))
            for cd in el.findall(q(EWS, "CurveData"))
        )
        start = (el.findtext(q(EWS, "startTime")) or "").strip()
        style = (el.findtext(q(EWS, "curveStyle")) or "").strip()
        out.append(Curve(tag, start, style, points))
    return out


def below_zero(payload: ET.Element) -> bool:
    """True when a curve reaches below 0 MW, which only an Energy Storage Resource's can."""
    for el in payload.iter(q(EWS, "xvalue")):
        x = number(el.text)
        if x is not None and x < 0:
            return True
    return False


def _runs(values: list[Decimal], least: int = 3) -> list[tuple[int, int, Decimal]]:
    """(first, last, value) for each run of ``least`` or more equal values in a row, 1-based."""
    out, i = [], 0
    while i < len(values):
        j = i
        while j + 1 < len(values) and values[j + 1] == values[i]:
            j += 1
        if j - i + 1 >= least:
            out.append((i + 1, j + 1, values[i]))
        i = j + 1
    return out


def shape_problems(
    points: list[tuple[Decimal, Decimal]], prices: str, rtm_bid: bool = False
) -> list[str]:
    """What breaks ERCOT's rules for the shape of an energy curve; empty when nothing does.

    ``points`` are (MW, price) in document order. ``prices`` is OFFER (prices never
    fall from one point to the next) or BID (never rise). On every curve quantities
    never fall, and no more than two points in a row share a price or a quantity.
    ``rtm_bid`` adds the RTM Energy Bid's rules: the first quantity is 0 MW, the
    second is not, and the last is at least 0.1 MW.
    """
    out = []
    for i, ((x0, y0), (x1, y1)) in enumerate(pairwise(points), 1):
        if x1 < x0:
            out.append(f"the quantity falls from {x0} MW at point {i} to {x1} MW at point {i + 1}")
        if prices == OFFER and y1 < y0:
            out.append(f"the price falls from {y0} at point {i} to {y1} at point {i + 1}")
        elif prices == BID and y1 > y0:
            out.append(f"the price rises from {y0} at point {i} to {y1} at point {i + 1}")
    for first, last, y in _runs([y for _, y in points]):
        out.append(f"points {first} to {last} share the price {y}")
    for first, last, x in _runs([x for x, _ in points]):
        out.append(f"points {first} to {last} share the quantity {x} MW")
    if rtm_bid and points:
        if points[0][0] != 0:
            out.append(f"the first quantity is {points[0][0]} MW, not 0 MW")
        if len(points) > 1 and points[1][0] == 0:
            out.append("the second quantity is 0 MW")
        if points[-1][0] < RTM_BID_LAST_MW:
            out.append(f"the last quantity is {points[-1][0]} MW, less than 0.1 MW")
    return out


@lru_cache(maxsize=1)
def _xsd_as_types() -> frozenset[str]:
    """Every ASType value ERCOT's XSD enumerates."""
    return frozenset(
        r.constraint for r in xsd_rules.extract() if r.kind == "enumeration" and r.owner == "ASType"
    )


def rtswcap_from(operating_day: date) -> datetime | None:
    """14:30 Central time on the day before the Operating Day; None on the calendar's first day."""
    try:
        return datetime.combine(operating_day - timedelta(days=1), RTSWCAP_FROM, tzinfo=CENTRAL)
    except OverflowError:
        return None


def operating_day(start: str) -> date | None:
    """The Operating Day an xs:dateTime with an offset falls on, or None."""
    when = constraints.parse_datetime(start) if start else None
    return trading_date(when) if when is not None and when.tzinfo is not None else None


# --- energy curves ----------------------------------------------------------------

CURVE_TAG = {
    "ThreePartOffer": "EnergyOfferCurve",
    "EnergyOnlyOffer": "EnergyOfferCurve",
    "EnergyBid": "PriceCurve",
    "RTMEnergyBid": "PriceCurve",
}
# What prices do along each payload's curve, the Protocols section and the words it uses.
SHAPES = {
    "ThreePartOffer": (
        OFFER,
        "§4.4.9.3.1(1)(c)",
        "monotonically non-decreasing offer curve for both price (in $/MWh) and quantity (in MW)",
    ),
    "EnergyOnlyOffer": (
        OFFER,
        "§4.4.9.5.1(1)(c)(iii)",
        "monotonically non-decreasing energy offer curve for both price (in $/MWh) and quantity "
        "(in MW)",
    ),
    "EnergyBid": (
        BID,
        "§4.4.9.6.1(1)(c)(iii)",
        "monotonically non-increasing energy bid curve for price (in $/MWh) and monotonically "
        "increasing for quantity (in MW)",
    ),
}
# An Energy Storage Resource's Energy Bid/Offer Curve, sent in a Three-Part Offer.
STORAGE_SHAPE = (
    "§4.4.9.7.1(1)(c)",
    "monotonically non-decreasing curve for both price (in $/MWh) and quantity (in MW)",
)
REPEATS = "no more than two consecutive price/quantity pairs at the same price or quantity"
MINIMUMS = {
    "ThreePartOffer": (
        "§4.4.9.3.1(3)",
        "The minimum amount per Resource for each Energy Offer Curve that may be offered is "
        "one MW.",
    ),
    "EnergyOnlyOffer": (
        "§4.4.9.5.1(3)",
        "The minimum amount for each DAM Energy-Only Offer Curve that may be offered is one MW.",
    ),
    "EnergyBid": (
        "§4.4.9.6.1(2)",
        "The minimum amount for each DAM Energy Bid that may be bid is one MW.",
    ),
}
REJECTS_OVER_CAP = (
    f'{protocols("§4.4.11(2)")}: "Any offers submitted that exceed the current respective '
    'DASWCAP or RTSWCAP shall be rejected by ERCOT."'
)


def _shape(tag: str, curve: Curve, storage: bool) -> list[Problem]:
    points = curve.complete()
    if not points:
        return []
    if tag == "RTMEnergyBid":
        problems = shape_problems(points, BID, rtm_bid=True)
        cite = (
            f'{np4_450("§3.4")} list each of these among the cases in which "Bid Curves will '
            'be rejected".'
        )
        source = SRC_NP4_450
    else:
        prices, section, words = SHAPES[tag]
        if storage:
            section, words = STORAGE_SHAPE
        problems = shape_problems(points, prices)
        cite = f'{protocols(section)} asks for a "{words}" with "{REPEATS}".'
        source = SRC_PROTOCOLS
    if not problems:
        return []
    shown = "; ".join(problems[:3])
    if len(problems) > 3:
        shown += f"; and {len(problems) - 3} more"
    direction = "never rise" if tag in ("EnergyBid", "RTMEnergyBid") else "never fall"
    fix = (
        f"List the points by quantity, with prices that {direction} from one point to the "
        "next, and drop a middle point that repeats the price or quantity of both neighbours."
    )
    if tag == "RTMEnergyBid":
        fix += " Start at 0 MW and end at 0.1 MW or more."
    return [
        Problem(
            "curve-shape", ERROR, f"{curve.label(tag)}: {shown}. {cite}", curve.tag, fix, source
        )
    ]


def _minimum(tag: str, curve: Curve) -> list[Problem]:
    """The curve's largest quantity is the amount it offers or bids, whichever point counts."""
    mw = curve.quantities()
    if not mw or max(mw) >= ENERGY_MIN_MW:
        return []
    section, words = MINIMUMS[tag]
    fix = f"{'Bid' if tag == 'EnergyBid' else 'Offer'} at least 1 MW, or leave the curve out."
    if tag == "ThreePartOffer":
        fix += (
            " An Energy Storage Resource's curve has no such minimum; this check treats a curve "
            "as one only when a quantity is below 0 MW."
        )
    return [
        Problem(
            "quantity-below-minimum",
            ERROR,
            f'{curve.label(tag)}: its largest quantity is {max(mw)} MW. {protocols(section)}: "'
            f'{words}"',
            curve.tag,
            fix,
            SRC_PROTOCOLS,
        )
    ]


def _floor(tag: str, curve: Curve, storage: bool) -> list[Problem]:
    low = min(curve.prices(), default=None)
    if low is None or low >= ENERGY_FLOOR:
        return []
    if tag == "EnergyOnlyOffer":
        cite = (
            f'{protocols("§4.4.9.5.1(2)")}: a DAM Energy-Only Offer Curve "must be within the '
            'range of -$250.00 per MWh and the DASWCAP".'
        )
    elif storage:
        cite = (
            f'{protocols("§4.4.9.7.1(2)")}: an Energy Bid/Offer Curve "shall be bounded by '
            '-$250.00 per MWh and either the DASWCAP or RTSWCAP".'
        )
    else:
        cite = (
            f'{protocols("§4.4.9.3.1(2)")}: an Energy Offer Curve "must be within the range '
            'of -$250.00 per MWh and either the DASWCAP or RTSWCAP".'
        )
    return [
        Problem(
            "price-below-floor",
            ERROR,
            f"{curve.label(tag)}: price {low} is below -250.00. {cite}",
            curve.tag,
            "Raise every price to -250.00 or more.",
            SRC_PROTOCOLS,
        )
    ]


def _over_cap(
    tag: str, curve: Curve, name: str, cap: Decimal, why: str, source: str
) -> list[Problem]:
    high = max(curve.prices(), default=None)
    if high is None or high <= cap:
        return []
    return [
        Problem(
            "price-above-cap",
            ERROR,
            f"{curve.label(tag)}: price {high} is above {_cap(name)}. {why}",
            curve.tag,
            f"Keep every price at or below the {name} in force; ERCOT changes the caps from time "
            "to time.",
            source,
        )
    ]


def _between_caps(
    curve: Curve, storage: bool, day: date | None, created: datetime | None
) -> list[Problem]:
    """A Three-Part Offer price above the RTSWCAP but not above the DASWCAP."""
    high = max(curve.prices(), default=None)
    if high is None or not RTSWCAP < high <= DASWCAP:
        return []
    cutoff = rtswcap_from(day) if day else None
    when = (
        f"14:30 CT on {cutoff.date().isoformat()}, the day before the Operating Day"
        if cutoff
        else "14:30 CT on the day before the Operating Day"
    )
    if storage:
        rule = (
            f"{protocols('§4.4.9.7.1(2)')} bounds an Energy Bid/Offer Curve by the DASWCAP or "
            f'the RTSWCAP "depending on the timing of the submission", and {np4_450("§8.3")} '
            "apply the RTSWCAP to submissions used in Real-Time after 1430 in the Day-Ahead."
        )
    else:
        rule = (
            f'{protocols("§4.4.9.3.1(2)")}: "No Energy Offer Curve received after 1430 in the '
            'Day-Ahead may contain a price exceeding the RTSWCAP." At that time ERCOT also '
            "cancels any Energy Offer Curve that contains such a price."
        )
    head = (
        f"{curve.label('ThreePartOffer')}: price {high} is above {_cap('RTSWCAP')}, though "
        f"not above the DASWCAP ({DASWCAP:,} at most)."
    )
    if created is not None and cutoff is not None and created >= cutoff:
        return [
            Problem(
                "price-above-cap",
                ERROR,
                f"{head} The message was created at {created.isoformat()}, at or after {when}. "
                f"{rule}",
                curve.tag,
                "Keep every price at or below the RTSWCAP in force.",
                SRC_PROTOCOLS,
            )
        ]
    if created is not None and cutoff is not None:
        sent = f"The message was created at {created.isoformat()}, before that time."
    else:
        sent = (
            "This document gives no time this check can read: a RequestMessage's "
            "Header/ReplayDetection/Created, as an xs:dateTime with a UTC offset."
        )
    return [
        Problem(
            "price-above-cap",
            WARNING,
            f"{head} ERCOT accepts such a price only in an offer it receives before {when}. "
            f"{rule} {sent}",
            curve.tag,
            f"Keep the price only in an offer that reaches ERCOT before {when}; otherwise keep "
            "every price at or below the RTSWCAP.",
            SRC_PROTOCOLS,
        )
    ]


def _energy(
    tag: str, payload: ET.Element, trade_day: date | None, created: datetime | None
) -> list[Problem]:
    storage = tag == "ThreePartOffer" and below_zero(payload)
    out: list[Problem] = []
    for curve in curves(payload, CURVE_TAG[tag]):
        # A FIXED or VARIABLE block is a single point (curve-style-points checks that). The
        # Three-Part Offer page marks curveStyle "Not used"; the RTM Energy Bid page omits it.
        if tag in ("ThreePartOffer", "RTMEnergyBid") or curve.style in ("", "CURVE"):
            out += _shape(tag, curve, storage)
        if tag in MINIMUMS and not storage:
            out += _minimum(tag, curve)
        if tag == "EnergyBid":
            continue
        if tag == "RTMEnergyBid":
            why = (
                f'{np4_450("§3.4")}: ERCOT rejects an RTM Energy Bid curve if "any price is '
                'higher than the Real-Time System-Wide Offer Cap."'
            )
            out += _over_cap(tag, curve, "RTSWCAP", RTSWCAP, why, SRC_NP4_450)
            continue
        out += _floor(tag, curve, storage)
        out += _over_cap(tag, curve, "DASWCAP", DASWCAP, REJECTS_OVER_CAP, SRC_PROTOCOLS)
        if tag == "ThreePartOffer":
            day = operating_day(curve.start) or trade_day
            out += _between_caps(curve, storage, day, created)
    return out


# --- COP ---------------------------------------------------------------------------


def _cop(payload: ET.Element) -> list[Problem]:
    """NP4-450-M §4.1: MinSOC <= Hour Beginning Planned SOC <= MaxSOC in each Limits."""
    out = []
    for limits in payload.findall(q(EWS, "Limits")):
        low, plan, high = (
            number(limits.findtext(q(EWS, name))) for name in ("minSOC", "targetBeginSOC", "maxSOC")
        )
        broken = []
        if low is not None and plan is not None and low > plan:
            broken.append(f"minSOC {low} is above targetBeginSOC {plan}")
        if plan is not None and high is not None and plan > high:
            broken.append(f"targetBeginSOC {plan} is above maxSOC {high}")
        if not broken:
            continue
        start = (limits.findtext(q(EWS, "startTime")) or "").strip() or "(no startTime)"
        out.append(
            Problem(
                "cop-soc-order",
                ERROR,
                f"COP Limits from {start}: {'; '.join(broken)}. {np4_450('§4.1')} want the "
                "COP's MinSOC at most its Hour Beginning Planned SOC (targetBeginSOC), and that "
                'at most its MaxSOC; COP submissions validation "will reject those submissions '
                'that don’t meet these requirements".',
                "Limits",
                "Keep minSOC <= targetBeginSOC <= maxSOC in every Limits element.",
                SRC_NP4_450,
            )
        )
    return out


# --- AS Only Offer -----------------------------------------------------------------


def _as_only(payload: ET.Element) -> list[Problem]:
    """NP4-450-M §2.3: the five products, each amount at least 0.1 MW, prices 0 to DASWCAP."""
    out = []
    as_type = (payload.findtext(q(EWS, "asType")) or "").strip()
    # A value outside the XSD's ASType enumeration is the schema check's to report.
    if as_type and as_type not in AS_ONLY_TYPES and as_type in _xsd_as_types():
        note = ""
        if as_type == "On-Non-Spin":
            note = (
                " The XSD's note for version 0.3.33 says Non-Spin is used for ASOnlyOffer "
                "rather than On-Non-Spin."
            )
        out.append(
            Problem(
                "as-only-offer-type",
                ERROR,
                f"ASOnlyOffer asType is {as_type}. {np4_450('§2.3')} restrict the AS Type of an "
                "AS Only Offer to REGUP, REGDN, RRSPF, ONNS or ECRSS, the products the XSD calls "
                f"Reg-Up, Reg-Down, RRSPF, Non-Spin and ECRSS.{note}",
                "asType",
                "Use Reg-Up, Reg-Down, Non-Spin, RRSPF or ECRSS.",
                SRC_NP4_450,
                discrepancies.related(("enumeration-value",), values=(as_type,)),
            )
        )
    for curve in curves(payload, "ASOnlyPriceCurve"):
        mw, prices = curve.quantities(), curve.prices()
        minimum = (
            f'{np4_450("§2.3")}: "The minimum amount that may be offered is one-tenth (0.1) MW."'
        )
        low = min((x for x in mw if x != 0), default=None)
        if low is not None and low < AS_ONLY_MIN_MW:
            out.append(
                Problem(
                    "quantity-below-minimum",
                    ERROR,
                    f"{curve.label('ASOnlyOffer')}: an amount of {low} MW. {minimum}",
                    curve.tag,
                    "Offer at least 0.1 MW in each amount, or leave the amount out.",
                    SRC_NP4_450,
                )
            )
        elif any(x == 0 for x in mw):
            # Read per amount, 0 MW is below the minimum; ERCOT does not say how it treats one.
            out.append(
                Problem(
                    "quantity-below-minimum",
                    WARNING,
                    f"{curve.label('ASOnlyOffer')}: an amount of 0 MW. {minimum} Read per "
                    "amount, 0 MW is below it; ERCOT's documents do not say whether it rejects "
                    "an offer with one.",
                    curve.tag,
                    "Leave the 0 MW amount out.",
                    SRC_NP4_450,
                )
            )
        if prices and min(prices) < 0:
            out.append(
                Problem(
                    "price-below-floor",
                    ERROR,
                    f"{curve.label('ASOnlyOffer')}: price {min(prices)} is below 0. "
                    f'{np4_450("§2.3")}: "Ancillary Service Only Offer prices may not be less '
                    'than $0 per MW."',
                    curve.tag,
                    "Raise every price to 0.00 or more.",
                    SRC_NP4_450,
                )
            )
        why = (
            f'{np4_450("§2.3")}: "No Ancillary Service Only Offer price may exceed the DASWCAP '
            '(in $/MW)."'
        )
        out += _over_cap("ASOnlyOffer", curve, "DASWCAP", DASWCAP, why, SRC_NP4_450)
    return out


def check_payload(
    tag: str,
    payload: ET.Element,
    trade_day: date | None = None,
    created: datetime | None = None,
) -> list[Problem]:
    """Every problem these rules find in one BidSet payload that is being submitted.

    ``trade_day`` is the BidSet's tradingDate, used when a curve's own startTime does
    not give its Operating Day. ``created`` is when the message was created
    (Header/ReplayDetection/Created), when the document is a RequestMessage that says.
    """
    if tag == "COP":
        return _cop(payload)
    if tag == "ASOnlyOffer":
        return _as_only(payload)
    if tag in CURVE_TAG:
        return _energy(tag, payload, trade_day, created)
    return []
