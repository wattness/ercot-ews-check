from datetime import date

import pytest

from ercot_ews_check import mrid


def test_whole_day_cancel():
    scope = mrid.cancel_scope("QSE1.20261015.EOO.HB_HOUSTON.eoo01")
    assert scope.whole_day and "every hour" in str(scope)


def test_hour_range():
    scope = mrid.cancel_scope("QSE1.20261015.EOO.HB_HOUSTON.eoo01.14-16")
    assert scope.hours == ("14", "15", "16")


def test_repeated_hour_on_fall_back_day():
    scope = mrid.cancel_scope("QSE1.20261101.AOO.Reg-Up.b1.2R")
    assert scope.hours == ("2R",) and scope.day_hours == 25


def test_repeated_hour_absent_on_a_normal_day():
    scope = mrid.cancel_scope("QSE1.20261015.AOO.Reg-Up.b1.2R")
    assert scope.named_but_absent == ("2R",)


def test_numeric_key_is_not_read_as_an_hour():
    # AOO's key string ends in bidID; a bidID of "14" is a key, not hour 14.
    assert mrid.cancel_scope("QSE1.20261015.AOO.Reg-Up.14").whole_day


def test_hourless_families():
    scope = mrid.cancel_scope("QSE1.OTG.UN.PL.123")
    assert not scope.whole_day and "outage" in str(scope)


def test_short_mrid():
    assert mrid.short_mrid("QSE1", date(2026, 10, 15), "EnergyBid", "HB_HOUSTON") == (
        "QSE1.20261015.EB.HB_HOUSTON"
    )
    with pytest.raises(ValueError):
        mrid.short_mrid("QSE1", date(2026, 10, 15), "EnergyBid")
