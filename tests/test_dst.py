from datetime import date, datetime

import pytest

from ercot_ews_check import dst
from ercot_ews_check.dst import CENTRAL


def test_hours_in_day():
    assert dst.hours_in_day(date(2026, 3, 8)) == 23
    assert dst.hours_in_day(date(2026, 11, 1)) == 25
    assert dst.hours_in_day(date(2026, 10, 15)) == 24


def test_hour_tokens():
    assert dst.hour_tokens(date(2026, 11, 1))[:4] == ("01", "02", "2R", "03")
    assert dst.hour_tokens(date(2026, 3, 8))[:3] == ("01", "02", "04")


def test_hours_in_mrid():
    d = date(2026, 10, 15)
    start = datetime(2026, 10, 15, 13, tzinfo=CENTRAL)
    end = datetime(2026, 10, 15, 16, tzinfo=CENTRAL)
    assert dst.hours_in_mrid(start, end) == "14-16"
    assert (
        dst.hours_in_mrid(
            datetime(2026, 10, 15, tzinfo=CENTRAL), datetime(2026, 10, 16, tzinfo=CENTRAL)
        )
        is None
    )
    assert dst.trading_date(start) == d


def test_parse_hour_ending():
    assert dst.parse_hour_ending("01") == (1, False)
    assert dst.parse_hour_ending("2*") == (2, True)
    assert dst.parse_hour_ending("01:00") == (1, False)
    with pytest.raises(ValueError):
        dst.parse_hour_ending("25")


def test_naive_datetime_is_refused():
    with pytest.raises(ValueError):
        dst.trading_date(datetime(2026, 10, 15))
