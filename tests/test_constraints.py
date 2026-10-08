from datetime import date

from ercot_ews_check import constraints


def test_hour_boundary():
    c = constraints.Constraint(constraints.HOUR_BOUNDARY, "startTime", "Valid hour boundary")
    assert c.check("2026-10-15T14:00:00-05:00") is None
    assert "hour boundary" in c.check("2026-10-15T14:30:00-05:00")


def test_numeric_bounds():
    c = constraints.Constraint(constraints.NUMERIC, "f", "between 0 and 100", lo=0, hi=100)
    assert c.check("50") is None
    assert "below" in c.check("-1") and "above" in c.check("101")


def test_before_trade_date_needs_the_date():
    c = constraints.Constraint(constraints.BEFORE_DATE, "expirationTime", "", advisory=True)
    assert c.violation("2026-10-15T09:00:00-05:00", None) is None
    assert c.violation("2026-10-15T09:00:00-05:00", date(2026, 10, 15))


def test_cop_hsl_and_lsl_are_advisory():
    rules = constraints.for_tag("COP")
    for name in ("hsl", "lsl", "hel", "lel"):
        rule = rules[f"Limits/{name}"]
        assert rule.kind == constraints.NUMERIC and rule.lo == 0
        assert rule.advisory == (name in ("hsl", "lsl"))


def test_enumerations_from_prose_are_advisory():
    rule = constraints.for_tag("SelfArrangedAS")["asType"]
    assert rule.kind == constraints.ENUM and rule.advisory
    assert {"RRS", "Reg-Up", "ECRS"} <= set(rule.values)


def test_coverage_counts_what_it_could_not_parse():
    cov = constraints.coverage()
    assert cov["constraints"] > 0 and cov["unparsed"] > 0
