"""Value formats from ErcotCommonTypes.xsd, including the ones the schema does not enforce."""

from __future__ import annotations

import re
from decimal import ROUND_DOWN, Decimal, InvalidOperation

# ErcotPrice: at most six integer digits and two decimals.
PRICE = re.compile(r"\A[+\-]?(\d{1,6}|\d{1,6}\.\d{0,2}|\.\d{1,2})\Z")
PRICE_DECIMALS = 2

# MWSingleDecimal is declared as a bare xs:decimal, although its annotation and
# ERCOT's "Precision" section both say MW carries one decimal place.
MW_DECIMALS = 1
# From MWSingleDecimal_Orig, the constrained version ERCOT left unreferenced.
MW_MIN, MW_MAX = -9999.9, 9999.9

# Non-price quantities on obligations carry five decimals (Services Organization, "Precision").
OBLIGATION_DECIMALS = 5

# BidId: 2-12 characters, alphanumeric at both ends, "_" and "-" allowed between.
BID_ID = re.compile(r"\A[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]\Z")
BID_ID_MIN, BID_ID_MAX = 2, 12

# CurveData caps differ by curve type (maxOccurs in ErcotCommonTypes.xsd).
CURVE_POINT_CAP = {"PriceCurve": 10, "BidPriceCurve": 10, "ASOnlyPriceCurve": 5}

CURVE_STYLES = ("FIXED", "VARIABLE", "CURVE")
# FIXED and VARIABLE describe a single point; CURVE takes up to ten.
CURVE_STYLE_POINTS = {"FIXED": (1, 1), "VARIABLE": (1, 1), "CURVE": (1, 10)}

# The bidID element is not spelled the same way on every type. ERCOT's own
# footnote on the DAM Energy Bid page says to check the XSD.
BID_ID_ELEMENT = {
    "EnergyBid": "bidID",
    "EnergyOnlyOffer": "bidID",
    "ASOnlyOffer": "bidID",
    "PTPObligation": "bidId",
    "AwardedEnergyBid": "bidId",
    "AwardedEnergyOnlyOffer": "bidId",
    "AwardedPTPObligation": "bidId",
    "AwardedASOnlyOffer": "bidID",
}


class ValueFormatError(ValueError):
    """A value ERCOT's schema or stated rules would not accept."""


def decimals(text: str) -> int:
    """Digits after the decimal point in a numeric string."""
    t = text.strip().lstrip("+-")
    if "e" in t.lower():
        try:
            return max(0, -Decimal(t).normalize().as_tuple().exponent)
        except InvalidOperation:
            return 0
    return len(t.split(".", 1)[1]) if "." in t else 0


def check_price(text: str) -> str | None:
    """None if ``text`` is a valid ErcotPrice, else the reason."""
    if not PRICE.match(text.strip()):
        return f"{text!r} is not an ErcotPrice (at most 6 integer digits and 2 decimals)"
    return None


def check_mw(text: str) -> str | None:
    """None if ``text`` is a MW value with at most one decimal, else the reason."""
    try:
        value = float(text)
    except ValueError:
        return f"{text!r} is not a number"
    if not MW_MIN <= value <= MW_MAX:
        return f"{text} MW is outside [{MW_MIN}, {MW_MAX}]"
    if decimals(text) > MW_DECIMALS:
        return f"{text} MW has {decimals(text)} decimals; ERCOT states MW carries one"
    return None


def check_bid_id(text: str) -> str | None:
    if not BID_ID_MIN <= len(text) <= BID_ID_MAX:
        return f"bidID {text!r} is {len(text)} characters; BidId allows {BID_ID_MIN}-{BID_ID_MAX}"
    if not BID_ID.match(text):
        return f"bidID {text!r} must start and end alphanumeric, with only _ and - between"
    return None


def quantize_mw(value: float) -> float:
    """Round MW to one decimal toward zero, so a quantity is never rounded up past a limit."""
    if not MW_MIN <= value <= MW_MAX:
        raise ValueFormatError(f"MW {value} is outside [{MW_MIN}, {MW_MAX}]")
    q = Decimal(str(value)).quantize(Decimal("0.1"), rounding=ROUND_DOWN)
    return float(q) + 0.0


def quantize_price(value: float) -> float:
    if abs(value) >= 10**6:
        raise ValueFormatError(f"price {value} exceeds six integer digits")
    return round(value, PRICE_DECIMALS)


def bid_id_tag(parent: str) -> str:
    """The exact bidID spelling under ``parent``."""
    try:
        return BID_ID_ELEMENT[parent]
    except KeyError:
        raise KeyError(f"no bidID spelling recorded for {parent!r}; check the XSD") from None
