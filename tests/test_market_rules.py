from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from ercot_ews_check import market_rules
from ercot_ews_check.market_rules import BID, OFFER, shape_problems


def pts(*pairs):
    return [(Decimal(x), Decimal(y)) for x, y in pairs]


def test_an_offer_curve_that_steps_up_is_fine():
    flat_then_vertical = pts(("0", "10"), ("5", "10"), ("5", "20"), ("10", "30"))
    assert shape_problems(flat_then_vertical, OFFER) == []


def test_a_bid_curve_that_steps_down_is_fine():
    assert shape_problems(pts(("0", "300"), ("15", "200"), ("100", "100")), BID) == []


@pytest.mark.parametrize(
    ("curve", "prices", "problem"),
    [
        (pts(("0", "30"), ("5", "20")), OFFER, "the price falls from 30 at point 1 to 20"),
        (pts(("0", "20"), ("5", "30")), BID, "the price rises from 20 at point 1 to 30"),
        (pts(("5", "20"), ("0", "30")), OFFER, "the quantity falls from 5 MW at point 1 to 0 MW"),
        (pts(("5", "30"), ("0", "20")), BID, "the quantity falls from 5 MW at point 1 to 0 MW"),
    ],
)
def test_order(curve, prices, problem):
    assert any(p.startswith(problem) for p in shape_problems(curve, prices))


def test_runs_of_three_or_more_are_reported_once():
    four = pts(("0", "10.00"), ("5", "10.0"), ("10", "10"), ("15", "10.00"))
    assert shape_problems(four, OFFER) == ["points 1 to 4 share the price 10.00"]
    vertical = pts(("5", "10"), ("5", "20"), ("5", "30"), ("6", "40"))
    assert shape_problems(vertical, OFFER) == ["points 1 to 3 share the quantity 5 MW"]


def test_rtm_bid_quantities():
    assert shape_problems(pts(("0", "50"), ("0.1", "40")), BID, rtm_bid=True) == []
    found = shape_problems(pts(("5", "50"), ("0", "40"), ("0.05", "30")), BID, rtm_bid=True)
    assert "the first quantity is 5 MW, not 0 MW" in found
    assert "the second quantity is 0 MW" in found
    assert "the last quantity is 0.05 MW, less than 0.1 MW" in found
    # One point cannot both start at 0 MW and end at 0.1 MW or more.
    assert shape_problems(pts(("0", "50")), BID, rtm_bid=True) != []
    # The RTM rules apply only to RTM Energy Bids.
    assert shape_problems(pts(("5", "50")), BID) == []


def test_numbers_must_be_finite_decimals():
    assert market_rules.number(" 5.0 ") == Decimal("5.0")
    for text in ("", "abc", "NaN", "Infinity", None):
        assert market_rules.number(text) is None


def test_the_rtswcap_takes_over_at_1430_central_the_day_before():
    cutoff = market_rules.rtswcap_from(date(2026, 10, 15))
    assert cutoff.astimezone(timezone.utc) == datetime(2026, 10, 14, 19, 30, tzinfo=timezone.utc)
    # After the November change Central time is UTC-06:00.
    cutoff = market_rules.rtswcap_from(date(2026, 11, 3))
    assert cutoff.astimezone(timezone.utc) == datetime(2026, 11, 2, 20, 30, tzinfo=timezone.utc)


def test_operating_day_needs_an_offset():
    assert market_rules.operating_day("2026-10-15T05:00:00+00:00") == date(2026, 10, 15)
    assert market_rules.operating_day("2026-10-15T04:00:00+00:00") == date(2026, 10, 14)
    assert market_rules.operating_day("2026-10-15T05:00:00") is None
    assert market_rules.operating_day("") is None


def test_as_only_products_are_xsd_values():
    from ercot_ews_check import requirements

    xsd = market_rules._xsd_as_types()
    assert set(market_rules.AS_ONLY_TYPES) < xsd
    assert set(market_rules.AS_ONLY_TYPES.values()) == {"REGUP", "REGDN", "RRSPF", "ONNS", "ECRSS"}
    # The AS Only Offer page's asType row lists the same five values.
    row = requirements.table("ASOnlyOffer")["asType"]["spec"]
    assert all(value in row.split() for value in market_rules.AS_ONLY_TYPES), row
    assert not {"RRSUF", "RRSFF", "On-Non-Spin", "Off-Non-Spin"} & set(row.split())
