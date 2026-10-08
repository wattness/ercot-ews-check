import json

import pytest

from ercot_ews_check import checker
from ercot_ews_check.checker import ERROR, SILENT, WARNING, check, check_file

from helpers import EWS, EXAMPLES, bidset, cancel, energy_only_offer


def rules(xml: str) -> set[str]:
    return check(xml).by_rule()


def finding(xml: str, rule: str) -> checker.Finding:
    return next(f for f in check(xml).findings if f.rule == rule)


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_examples_are_clean(path):
    rep = check_file(path)
    assert rep.schema == "valid"
    assert rep.findings == []


def test_clean_document_has_no_findings():
    assert check(energy_only_offer()).findings == []


def test_not_well_formed():
    rep = check("<BidSet>")
    assert rep.schema == "invalid" and rep.blocked


def test_hour_24():
    xml = energy_only_offer(curves=[("2026-10-15T23:00:00-05:00", "2026-10-15T24:00:00-05:00")])
    assert finding(xml, "hour-24").severity == ERROR


def test_off_hour_time_is_silent():
    xml = energy_only_offer(curves=[("2026-10-15T17:30:00-05:00", "2026-10-15T18:00:00-05:00")])
    found = [f for f in check(xml).findings if f.where == "EnergyOfferCurve/startTime"]
    assert [(f.rule, f.severity) for f in found] == [("silent-hour-rounding", SILENT)]
    assert "Valid hour boundary" in found[0].message


def test_hour_rounding_only_where_the_table_expects_an_hour():
    # Output Schedule times are on 5-minute boundaries.
    xml = bidset("""  <OutputSchedule>
    <startTime>2026-10-15T00:05:00-05:00</startTime>
    <endTime>2026-10-16T00:00:00-05:00</endTime>
  </OutputSchedule>
""")
    assert "silent-hour-rounding" not in rules(xml)


def test_overlapping_curves():
    xml = energy_only_offer(
        curves=[
            ("2026-10-15T17:00:00-05:00", "2026-10-15T18:00:00-05:00"),
            ("2026-10-15T17:00:00-05:00", "2026-10-15T19:00:00-05:00"),
        ]
    )
    assert finding(xml, "overlapping-intervals").severity == ERROR


def test_gap_between_curves_is_allowed():
    xml = energy_only_offer(
        curves=[
            ("2026-10-15T17:00:00-05:00", "2026-10-15T18:00:00-05:00"),
            ("2026-10-15T20:00:00-05:00", "2026-10-15T21:00:00-05:00"),
        ]
    )
    assert "interval-gap" not in rules(xml)


def test_gap_in_a_structure_that_tiles_the_day():
    xml = bidset("""  <COP>
    <resource>R1</resource>
    <ResourceStatus>
      <startTime>2026-10-15T00:00:00-05:00</startTime>
      <endTime>2026-10-15T06:00:00-05:00</endTime>
      <operatingMode>ONL</operatingMode>
    </ResourceStatus>
    <ResourceStatus>
      <startTime>2026-10-15T07:00:00-05:00</startTime>
      <endTime>2026-10-16T00:00:00-05:00</endTime>
      <operatingMode>ONL</operatingMode>
    </ResourceStatus>
  </COP>
""")
    assert finding(xml, "interval-gap").severity == WARNING


def test_trading_date_must_match_central_time():
    xml = energy_only_offer().replace("<tradingDate>2026-10-15", "<tradingDate>2026-10-16")
    f = finding(xml, "trade-date-mismatch")
    assert f.severity == ERROR and "for trade date" in f.message
    assert f.source.endswith("DAM%20Energy-Only%20Offer%20%28EOO%29/")


def test_utc_start_on_the_right_day_is_fine():
    xml = energy_only_offer(
        start="2026-10-15T05:00:00+00:00",
        end="2026-10-16T05:00:00+00:00",
        curves=[("2026-10-15T22:00:00+00:00", "2026-10-15T23:00:00+00:00")],
    )
    assert check(xml).findings == []


def test_foreign_offset_moving_the_trading_date():
    xml = energy_only_offer(start="2026-10-15T00:00:00+01:00")
    assert finding(xml, "utc-offset").severity == WARNING
    assert "trade-date-mismatch" not in rules(xml)


def test_daylight_offset_after_fall_back():
    # 2026-11-01 is 25 hours long; at midnight on 2 November Central time is UTC-06:00.
    xml = energy_only_offer(
        start="2026-11-01T00:00:00-05:00",
        end="2026-11-02T00:00:00-05:00",
        curves=[("2026-11-01T17:00:00-06:00", "2026-11-01T18:00:00-06:00")],
    ).replace("2026-10-15</tradingDate>", "2026-11-01</tradingDate>")
    found = [f for f in check(xml).findings if f.rule == "utc-offset"]
    assert [f.where for f in found] == ["endTime"]
    assert "2026-11-01T23:00:00-06:00" in found[0].message


def test_curve_style_point_count():
    xml = energy_only_offer(style="FIXED").replace(
        "</CurveData>",
        "</CurveData>\n      <CurveData><xvalue>9.0</xvalue><y1value>30.00</y1value></CurveData>",
    )
    assert finding(xml, "curve-style-points").severity == ERROR


def test_mw_precision_beyond_one_decimal():
    xml = energy_only_offer(mw="5.25")
    f = finding(xml, "mw-precision")
    assert f.severity == WARNING and check(xml).schema == "valid"


def test_missing_required_field():
    xml = energy_only_offer().replace("    <bidID>eoo01</bidID>\n", "")
    f = finding(xml, "missing-required-field")
    assert f.severity == ERROR and "bidID" in f.message
    assert check(xml).schema == "valid"


def test_required_field_not_checked_on_a_reply():
    xml = bidset(
        "  <EnergyOnlyOffer>\n    <mRID>QSE1.20261015.EOO.HB_HOUSTON.eoo01</mRID>\n"
        "    <status>ACCEPTED</status>\n  </EnergyOnlyOffer>\n"
    )
    assert "missing-required-field" not in rules(xml)


def test_value_ignored():
    xml = bidset("""  <ASOffer>
    <startTime>2026-10-15T00:00:00-05:00</startTime>
    <endTime>2026-10-16T00:00:00-05:00</endTime>
    <expirationTime>2026-10-14T10:00:00-05:00</expirationTime>
    <resource>RESOURCE1</resource>
    <combinedCycle>CC1</combinedCycle>
    <asType>Off-Non-Spin</asType>
    <ASPriceCurve>
      <startTime>2026-10-15T14:00:00-05:00</startTime>
      <endTime>2026-10-15T15:00:00-05:00</endTime>
      <OffLineNonSpin>
        <xvalue>10.0</xvalue>
        <OFFNS>6.50</OFFNS>
        <block>VARIABLE</block>
      </OffLineNonSpin>
      <multiHourBlock>false</multiHourBlock>
    </ASPriceCurve>
  </ASOffer>
""")
    f = finding(xml, "value-ignored")
    assert f.severity == WARNING and "Ancillary%20Service%20Offer" in f.source


def test_rrs_value1_is_ignored_by_ercot():
    xml = bidset("""  <SelfArrangedAS>
    <startTime>2026-10-15T00:00:00-05:00</startTime>
    <endTime>2026-10-16T00:00:00-05:00</endTime>
    <asType>RRS</asType>
    <CapacitySchedule>
      <TmPoint>
        <time>2026-10-15T14:00:00-05:00</time>
        <ending>2026-10-15T15:00:00-05:00</ending>
        <value1>5.0</value1>
      </TmPoint>
    </CapacitySchedule>
  </SelfArrangedAS>
""")
    assert finding(xml, "silent-rrs-value1-ignored").severity == SILENT


def test_negative_cop_limit_is_a_warning_not_an_error():
    xml = bidset("""  <COP>
    <resource>R1</resource>
    <ResourceStatus>
      <startTime>2026-10-15T00:00:00-05:00</startTime>
      <endTime>2026-10-16T00:00:00-05:00</endTime>
      <operatingMode>ONL</operatingMode>
    </ResourceStatus>
    <Limits>
      <startTime>2026-10-15T00:00:00-05:00</startTime>
      <endTime>2026-10-16T00:00:00-05:00</endTime>
      <hsl>10.0</hsl>
      <lsl>-10.0</lsl>
      <hel>10.0</hel>
      <lel>-10.0</lel>
    </Limits>
  </COP>
""")
    found = {f.where: f for f in check(xml).findings if f.rule == "value-numeric-bound"}
    assert set(found) == {"Limits/lsl", "Limits/lel"}
    assert found["Limits/lsl"].severity == WARNING and found["Limits/lsl"].see == ("D033",)
    # D033's Protocols text covers HSL and LSL only.
    assert found["Limits/lel"].severity == ERROR and found["Limits/lel"].see == ()


def test_withdrawn_payload():
    xml = bidset("  <IncDecOffer/>\n")
    f = finding(xml, "withdrawn-payload")
    assert check(xml).blocked and f.see == ("D010",) and f.source


PROSE_RULE_DOCS = {
    "silent-hour-rounding": energy_only_offer(start="2026-10-15T00:30:00-05:00"),
    "trade-date-mismatch": energy_only_offer().replace(
        ">2026-10-15</tradingDate>", ">2026-10-16</tradingDate>"
    ),
    "utc-offset": energy_only_offer(start="2026-10-15T00:00:00+01:00"),
    "hour-24": energy_only_offer(end="2026-10-15T24:00:00-05:00"),
    "missing-required-field": energy_only_offer().replace("    <bidID>eoo01</bidID>\n", ""),
    "mw-precision": energy_only_offer(mw="5.25"),
    "curve-style-points": energy_only_offer(style="FIXED").replace(
        "</CurveData>",
        "</CurveData><CurveData><xvalue>9.0</xvalue><y1value>3.00</y1value></CurveData>",
    ),
    "withdrawn-payload": bidset("  <IncDecOffer/>\n"),
    "cancel-every-hour": cancel("QSE1.20261015.EOO.HB_HOUSTON.eoo01"),
    "cop-cancel": cancel("QSE1.20261015.COP.R1"),
}


@pytest.mark.parametrize("rule", sorted(PROSE_RULE_DOCS))
def test_prose_rules_cite_their_source(rule):
    f = finding(PROSE_RULE_DOCS[rule], rule)
    assert f.source.startswith("https://developer.ercot.com/"), f


def test_cancel_without_hours_reaches_the_whole_day():
    f = finding(cancel("QSE1.20261015.EOO.HB_HOUSTON.eoo01"), "cancel-every-hour")
    assert f.severity == WARNING


def test_cancel_with_hours():
    assert "cancel-every-hour" not in rules(cancel("QSE1.20261015.EOO.HB_HOUSTON.eoo01.14-16"))


def test_cop_cannot_be_canceled():
    assert finding(cancel("QSE1.20261015.COP.R1"), "cop-cancel").severity == ERROR


def test_payload_too_large():
    curves = [
        (f"2026-10-15T{h:02d}:00:00-05:00", f"2026-10-15T{h + 1:02d}:00:00-05:00")
        for h in range(23)
    ]
    one = energy_only_offer(curves=curves)
    offer = one.split("<EnergyOnlyOffer>", 1)[1].rsplit("</EnergyOnlyOffer>", 1)[0]
    body = "".join(
        f"  <EnergyOnlyOffer>{offer.replace('eoo01', f'eoo{i:05d}')}</EnergyOnlyOffer>\n"
        for i in range(1000)
    )
    f = finding(bidset(body), "payload-too-large")
    assert f.source.endswith("#web-service-design-assumptions-and-limitations")


def test_message_payload_is_validated():
    xml = f"""<RequestMessage xmlns="http://www.ercot.com/schema/2007-06/nodal/ews/message">
  <Header>
    <Verb>create</Verb>
    <Noun>BidSet</Noun>
    <ReplayDetection><Nonce>1</Nonce><Created>2026-10-14T09:00:00-05:00</Created></ReplayDetection>
    <Revision>1</Revision>
    <Source>QSE1</Source>
  </Header>
  <Payload>
    <BidSet xmlns="{EWS}"><tradingDate>2026-10-15</tradingDate><Bogus/></BidSet>
  </Payload>
</RequestMessage>"""
    rep = check(xml)
    assert rep.schema == "invalid" and "Bogus" in str(rep)


def test_report_serialises():
    rep = check(energy_only_offer(mw="5.25"))
    data = json.loads(rep.to_json())
    assert data["blocked"] is False
    assert data["findings"][0]["rule"] == "mw-precision"
    assert str(rep).startswith("OK with warnings")
