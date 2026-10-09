import json

import pytest

from ercot_ews_check import checker, examples, market_rules
from ercot_ews_check.checker import ERROR, SILENT, WARNING, check, check_file

from helpers import (
    EWS,
    EXAMPLES,
    bidset,
    cancel,
    energy_only_offer,
    message,
    notify,
    points,
    response,
)


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
    # NP4-450 §2.2 requires the plant name for a combined-cycle Resource, so not "Remove".
    assert "(NP4-450-M, §2.2)" in f.message and f.fix.startswith("Keep it")


def three_part_offer(low: str, fip_fop: bool = False) -> str:
    eoc = (
        "    <EocFipFop>\n      <startTime>2026-10-15T00:00:00-05:00</startTime>\n"
        "      <endTime>2026-10-16T00:00:00-05:00</endTime>\n"
        "      <fipPercent>0</fipPercent>\n      <fopPercent>0</fopPercent>\n    </EocFipFop>\n"
    )
    return bidset(f"""  <ThreePartOffer>
    <startTime>2026-10-15T00:00:00-05:00</startTime>
    <endTime>2026-10-16T00:00:00-05:00</endTime>
    <expirationTime>2026-10-14T10:00:00-05:00</expirationTime>
    <resource>RESOURCE1</resource>
{eoc if fip_fop else ""}    <EnergyOfferCurve>
      <startTime>2026-10-15T17:00:00-05:00</startTime>
      <endTime>2026-10-15T18:00:00-05:00</endTime>
      <CurveData><xvalue>{low}</xvalue><y1value>15.00</y1value></CurveData>
      <CurveData><xvalue>10.0</xvalue><y1value>35.50</y1value></CurveData>
      <incExcFlag>INC</incExcFlag>
      <reason>OTHR</reason>
    </EnergyOfferCurve>
  </ThreePartOffer>
""")


def test_storage_offer_without_fip_fop_is_a_warning():
    # NP4-450 §2.1: FIP and FOP for the curve are "not applicable to ESRs"; a point below
    # 0 MW is what marks an Energy Storage Resource's curve.
    rep = check(three_part_offer("-10.0"))
    f = finding(three_part_offer("-10.0"), "missing-required-field")
    assert not rep.blocked and f.severity == WARNING
    assert f.source == checker.SRC_NP4_450 and "not applicable to ESRs" in f.message
    assert check(three_part_offer("-10.0", fip_fop=True)).findings == []


def test_offer_without_fip_fop_is_blocked_when_nothing_marks_storage():
    f = finding(three_part_offer("0.0"), "missing-required-field")
    assert check(three_part_offer("0.0")).blocked and f.severity == ERROR
    assert "EocFipFop/fipPercent" in f.message and "Energy Storage Resource" in f.fix
    assert check(three_part_offer("0.0", fip_fop=True)).findings == []


def rtm_energy_bid(resource: str) -> str:
    return bidset(f"""  <RTMEnergyBid>
    <startTime>2026-10-15T00:00:00-05:00</startTime>
    <endTime>2026-10-16T00:00:00-05:00</endTime>
    <expirationTime>2026-10-15T12:00:00-05:00</expirationTime>
{resource}    <PriceCurve>
      <startTime>2026-10-15T17:00:00-05:00</startTime>
      <endTime>2026-10-15T18:00:00-05:00</endTime>
      <CurveData><xvalue>0</xvalue><y1value>50.00</y1value></CurveData>
      <CurveData><xvalue>5.0</xvalue><y1value>40.00</y1value></CurveData>
    </PriceCurve>
  </RTMEnergyBid>
""")


def test_rtm_energy_bid_resource_spelled_as_the_schema_does():
    # The REB table spells the key "Resource"; the XSD and ERCOT's own sample, "resource" (D034).
    assert check(rtm_energy_bid("    <resource>RESOURCE1</resource>\n")).findings == []
    f = finding(rtm_energy_bid(""), "missing-required-field")
    assert f.severity == ERROR and f.message.endswith("is minOccurs=0.")
    assert ": resource." in f.message


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
    # The Protocols give the emergency limits no sign (D047).
    assert found["Limits/lel"].severity == WARNING and found["Limits/lel"].see == ("D047",)


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


def test_a_notify_reports_the_message_it_carries():
    xml = notify(response("Created", "ConfirmedTrades"))
    f = finding(xml, "schema")
    assert check(xml).blocked and f.where == "/ResponseMessage/Header/Verb" and "D015" in f.see


@pytest.mark.parametrize(
    "verb, blocked", [("create", False), ("created", False), ("Created", True)]
)
def test_notification_verb_is_checked_against_the_enumeration(verb, blocked):
    # D045: the forecast pages give create, which the enumeration allows.
    assert check(notify(response(verb, "WindForecastData"))).blocked is blocked


def test_a_notification_is_not_a_submission():
    offer = "  <EnergyOnlyOffer>\n    <mRID>QSE1.20261015.EOO.HB_HOUSTON.eoo01</mRID>\n"
    payload = bidset(offer + "  </EnergyOnlyOffer>\n")
    for xml in (
        notify(response("changed", "BidSet", payload)),
        response("changed", "BidSet", payload),
    ):
        rep = check(xml)
        assert rep.schema == "valid" and rep.findings == []


# --- ERCOT's Market Submission Validation Rules (NP4-450-M) and Nodal Protocols ---


def tpo(curve: str, start: str = "2026-10-15T17:00:00-05:00") -> str:
    """A Three-Part Offer for 15 October 2026 with one Energy Offer Curve."""
    return bidset(f"""  <ThreePartOffer>
    <startTime>2026-10-15T00:00:00-05:00</startTime>
    <endTime>2026-10-16T00:00:00-05:00</endTime>
    <expirationTime>2026-10-14T10:00:00-05:00</expirationTime>
    <resource>RESOURCE1</resource>
    <EocFipFop>
      <startTime>2026-10-15T00:00:00-05:00</startTime>
      <endTime>2026-10-16T00:00:00-05:00</endTime>
      <fipPercent>0</fipPercent>
      <fopPercent>0</fopPercent>
    </EocFipFop>
    <EnergyOfferCurve>
      <startTime>{start}</startTime>
      <endTime>2026-10-15T18:00:00-05:00</endTime>
      {curve}
      <incExcFlag>INC</incExcFlag>
      <reason>OTHR</reason>
    </EnergyOfferCurve>
  </ThreePartOffer>
""")


MARKET_RULES = {
    "price-below-floor",
    "price-above-cap",
    "curve-shape",
    "cop-soc-order",
    "quantity-below-minimum",
    "as-only-offer-type",
}


def market(xml: str) -> list[checker.Finding]:
    return [f for f in check(xml).findings if f.rule in MARKET_RULES]


def test_offer_price_floor():
    # Nodal Protocols §4.4.9.3.1(2): within -$250.00 per MWh and the DASWCAP or RTSWCAP.
    assert market(tpo(points(("0.0", "-250.00"), ("10.0", "35.50")))) == []
    (f,) = market(tpo(points(("0.0", "-250.01"), ("10.0", "35.50"))))
    assert (f.rule, f.severity, f.where) == ("price-below-floor", ERROR, "EnergyOfferCurve")
    assert "§4.4.9.3.1(2)" in f.message and f.source == market_rules.SRC_PROTOCOLS


def test_offer_price_above_the_day_ahead_cap_is_rejected():
    (f,) = market(tpo(points(("0.0", "15.00"), ("10.0", "5000.01"))))
    assert (f.rule, f.severity) == ("price-above-cap", ERROR)
    # The caps are dated: the message names the Protocols version they come from.
    assert "5,000" in f.message and "1 August 2026" in f.message


def test_offer_price_between_the_caps_without_a_time_is_a_warning():
    (f,) = market(tpo(points(("0.0", "15.00"), ("10.0", "5000.00"))))
    assert (f.rule, f.severity) == ("price-above-cap", WARNING)
    assert "2,000" in f.message and "14:30 CT on 2026-10-14" in f.message
    assert not check(tpo(points(("0.0", "15.00"), ("10.0", "2000.00")))).findings


def test_offer_price_between_the_caps_uses_the_message_time():
    body = tpo(points(("0.0", "15.00"), ("10.0", "2500.00")))
    # 14:30 CDT on the day before the Operating Day is 19:30 UTC.
    (before,) = market(message(body, created="2026-10-14T19:29:59Z"))
    assert before.severity == WARNING and "before that time" in before.message
    (after,) = market(message(body, created="2026-10-14T19:30:00Z"))
    assert after.severity == ERROR and "received after 1430 in the Day-Ahead" in after.message
    # A time without an offset says nothing about the instant.
    (bare,) = market(message(body, created="2026-10-14T15:00:00"))
    assert bare.severity == WARNING
    # The same message inside a SOAP envelope.
    soap = message(body, created="2026-10-14T19:30:00Z")
    soap = (
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
        f"<soapenv:Body>{soap}</soapenv:Body></soapenv:Envelope>"
    )
    assert [f.severity for f in market(soap)] == [ERROR]


def test_storage_offer_price_cites_the_energy_bid_offer_curve():
    curve = points(("-10.0", "-250.01"), ("10.0", "2500.00"))
    found = {f.rule: f for f in market(message(tpo(curve), created="2026-10-15T08:00:00-05:00"))}
    assert "§4.4.9.7.1(2)" in found["price-below-floor"].message
    assert found["price-above-cap"].severity == ERROR
    assert "§4.4.9.7.1(2)" in found["price-above-cap"].message


def eoo(curve: str, style: str = "CURVE") -> str:
    """A DAM Energy-Only Offer for 15 October 2026 with one curve."""
    return bidset(f"""  <EnergyOnlyOffer>
    <startTime>2026-10-15T00:00:00-05:00</startTime>
    <endTime>2026-10-16T00:00:00-05:00</endTime>
    <expirationTime>2026-10-14T09:00:00-05:00</expirationTime>
    <sp>HB_HOUSTON</sp>
    <bidID>eoo01</bidID>
    <EnergyOfferCurve>
      <startTime>2026-10-15T17:00:00-05:00</startTime>
      <endTime>2026-10-15T18:00:00-05:00</endTime>
      <curveStyle>{style}</curveStyle>
      {curve}
    </EnergyOfferCurve>
  </EnergyOnlyOffer>
""")


def test_energy_only_offer_has_one_cap():
    # §4.4.9.5.1(2): within -$250.00 per MWh and the DASWCAP; the DAM is its only market.
    xml = eoo(points(("5.0", "20.00"), ("10.0", "4999.99")))
    assert check(xml).findings == []
    assert [f.rule for f in market(xml.replace("4999.99", "5000.01"))] == ["price-above-cap"]
    assert [f.rule for f in market(xml.replace("20.00", "-250.01"))] == ["price-below-floor"]


def test_rtm_energy_bid_price_cap():
    # NP4-450-M §3.4: rejected if "any price is higher than the Real-Time System-Wide Offer Cap".
    xml = rtm_energy_bid("    <resource>RESOURCE1</resource>\n")
    assert market(xml.replace("50.00", "2000.00")) == []
    (f,) = market(xml.replace("50.00", "2000.01"))
    assert f.severity == ERROR and f.source == market_rules.SRC_NP4_450


def test_dam_energy_bid_prices_are_not_bounded():
    # No ERCOT text bounds a DAM Energy Bid's prices, so this tool does not either.
    xml = bidset("""  <EnergyBid>
    <startTime>2026-10-15T00:00:00-05:00</startTime>
    <endTime>2026-10-16T00:00:00-05:00</endTime>
    <expirationTime>2026-10-14T10:00:00-05:00</expirationTime>
    <sp>HB_WEST</sp>
    <bidID>eb01</bidID>
    <PriceCurve>
      <startTime>2026-10-15T17:00:00-05:00</startTime>
      <endTime>2026-10-15T18:00:00-05:00</endTime>
      <curveStyle>FIXED</curveStyle>
      <CurveData><xvalue>8.0</xvalue><y1value>9000.00</y1value></CurveData>
    </PriceCurve>
  </EnergyBid>
""")
    assert check(xml).findings == []


def test_market_rules_skip_replies():
    xml = tpo(points(("0.0", "-300.00"), ("10.0", "35.50"))).replace(
        "<resource>RESOURCE1</resource>", "<resource>RESOURCE1</resource><status>ACCEPTED</status>"
    )
    assert market(xml) == []


def eb(curve: str, style: str = "CURVE") -> str:
    """A DAM Energy Bid for 15 October 2026 with one curve."""
    return bidset(f"""  <EnergyBid>
    <startTime>2026-10-15T00:00:00-05:00</startTime>
    <endTime>2026-10-16T00:00:00-05:00</endTime>
    <expirationTime>2026-10-14T09:00:00-05:00</expirationTime>
    <sp>HB_WEST</sp>
    <bidID>eb01</bidID>
    <PriceCurve>
      <startTime>2026-10-15T17:00:00-05:00</startTime>
      <endTime>2026-10-15T18:00:00-05:00</endTime>
      <curveStyle>{style}</curveStyle>
      {curve}
    </PriceCurve>
  </EnergyBid>
""")


def reb(curve: str) -> str:
    """An RTM Energy Bid for 15 October 2026 with one curve."""
    return bidset(f"""  <RTMEnergyBid>
    <startTime>2026-10-15T00:00:00-05:00</startTime>
    <endTime>2026-10-16T00:00:00-05:00</endTime>
    <expirationTime>2026-10-15T12:00:00-05:00</expirationTime>
    <resource>RESOURCE1</resource>
    <PriceCurve>
      <startTime>2026-10-15T17:00:00-05:00</startTime>
      <endTime>2026-10-15T18:00:00-05:00</endTime>
      {curve}
    </PriceCurve>
  </RTMEnergyBid>
""")


def shape(xml: str) -> list[checker.Finding]:
    return [f for f in check(xml).findings if f.rule == "curve-shape"]


def test_offer_curve_prices_and_quantities_never_fall():
    # Nodal Protocols §4.4.9.3.1(1)(c): non-decreasing "for both price ... and quantity".
    assert shape(tpo(points(("0.0", "15.00"), ("10.0", "15.00"), ("10.0", "35.50")))) == []
    (f,) = shape(tpo(points(("0.0", "35.50"), ("10.0", "15.00"))))
    assert (f.severity, f.where) == (ERROR, "EnergyOfferCurve")
    assert "the price falls from 35.50 at point 1 to 15.00 at point 2" in f.message
    assert "§4.4.9.3.1(1)(c)" in f.message and f.source == market_rules.SRC_PROTOCOLS
    (f,) = shape(tpo(points(("10.0", "15.00"), ("5.0", "35.50"))))
    assert "the quantity falls from 10.0 MW at point 1 to 5.0 MW at point 2" in f.message


def test_no_three_points_in_a_row_share_a_price_or_quantity():
    same_price = points(("0.0", "15.00"), ("5.0", "15.00"), ("10.0", "15.00"))
    (f,) = shape(tpo(same_price))
    assert "points 1 to 3 share the price 15.00" in f.message
    same_mw = points(("10.0", "15.00"), ("10.0", "20.00"), ("10.0", "25.00"))
    (f,) = shape(tpo(same_mw))
    assert "points 1 to 3 share the quantity 10.0 MW" in f.message


def test_storage_curve_shape_cites_the_energy_bid_offer_curve():
    (f,) = shape(tpo(points(("-10.0", "30.00"), ("10.0", "20.00"))))
    assert "§4.4.9.7.1(1)(c)" in f.message


def test_energy_only_offer_curve_shape_only_for_curves():
    # §4.4.9.5.1(1)(c)(iii) governs a curve; a FIXED block is one point (curve-style-points).
    (f,) = shape(eoo(points(("5.0", "35.50"), ("10.0", "20.00"))))
    assert "§4.4.9.5.1(1)(c)(iii)" in f.message
    fixed = eoo(points(("5.0", "35.50"), ("10.0", "20.00")), style="FIXED")
    assert check(fixed).by_rule() == {"curve-style-points"}


def test_dam_energy_bid_prices_never_rise():
    # §4.4.9.6.1(1)(c)(iii): "monotonically non-increasing energy bid curve for price".
    assert check(eb(points(("5.0", "35.50"), ("10.0", "20.00")))).findings == []
    (f,) = shape(eb(points(("5.0", "20.00"), ("10.0", "35.50"))))
    assert "the price rises from 20.00 at point 1 to 35.50 at point 2" in f.message
    assert "§4.4.9.6.1(1)(c)(iii)" in f.message
    # "monotonically increasing for quantity" may or may not allow a repeat; only a fall is
    # certain to break it.
    assert shape(eb(points(("5.0", "35.50"), ("5.0", "20.00")))) == []
    (f,) = shape(eb(points(("10.0", "35.50"), ("5.0", "20.00"))))
    assert "the quantity falls" in f.message


def test_rtm_energy_bid_quantities():
    # NP4-450-M §3.4: the first quantity is 0 MW, the second is not, the last is >= 0.1 MW.
    assert shape(reb(points(("0", "50.00"), ("0.1", "40.00")))) == []
    (f,) = shape(reb(points(("1.0", "50.00"), ("5.0", "40.00"))))
    assert "the first quantity is 1.0 MW, not 0 MW" in f.message
    assert f.source == market_rules.SRC_NP4_450 and "§3.4" in f.message
    (f,) = shape(reb(points(("0", "50.00"), ("0", "40.00"), ("5.0", "30.00"))))
    assert "the second quantity is 0 MW" in f.message
    (f,) = shape(reb(points(("0", "50.00"))))
    assert "the last quantity is 0 MW, less than 0.1 MW" in f.message
    (f,) = shape(reb(points(("0", "40.00"), ("5.0", "50.00"))))
    assert "the price rises" in f.message


def test_ercot_samples_pass_the_market_rules():
    checked = 0
    for s in examples.samples():
        if s.state == examples.VALID:
            checked += 1
            assert market(s.text) == [], s.url
    assert checked > 80


def cop_soc(max_soc: str, min_soc: str, target: str | None) -> str:
    """A COP whose one Limits element carries state of charge, in the XSD's element order."""
    begin = f"<targetBeginSOC>{target}</targetBeginSOC>" if target is not None else ""
    return bidset(f"""  <COP>
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
      <lsl>0.0</lsl>
      <hel>10.0</hel>
      <lel>0.0</lel>
      <maxSOC>{max_soc}</maxSOC>
      <minSOC>{min_soc}</minSOC>
      {begin}
    </Limits>
  </COP>
""")


def test_cop_state_of_charge_order():
    # NP4-450-M §4.1: MinSOC <= Hour Beginning Planned SOC <= MaxSOC, else rejected.
    assert market(cop_soc("20.0", "5.0", "5.0")) == []
    assert market(cop_soc("20.0", "5.0", "20.0")) == []
    xml = cop_soc("20.0", "5.0", "40.0")
    (f,) = market(xml)
    assert check(xml).schema == "valid"  # minSOC, maxSOC and targetBeginSOC are the XSD's names
    assert (f.rule, f.severity, f.where) == ("cop-soc-order", ERROR, "Limits")
    assert "targetBeginSOC 40.0 is above maxSOC 20.0" in f.message
    assert f.source == market_rules.SRC_NP4_450 and "§4.1" in f.message
    (f,) = market(cop_soc("20.0", "8.0", "6.0"))
    assert "minSOC 8.0 is above targetBeginSOC 6.0" in f.message


def test_cop_state_of_charge_without_a_planned_value():
    # The stated order runs through the Hour Beginning Planned SOC; without it nothing is compared.
    assert market(cop_soc("5.0", "20.0", None)) == []


def aoo(as_type: str = "Reg-Up", curve: str = points(("10.0", "15.50"))) -> str:
    """An AS Only Offer for 15 October 2026 with one hour's curve."""
    return bidset(f"""  <ASOnlyOffer>
    <startTime>2026-10-15T00:00:00-05:00</startTime>
    <endTime>2026-10-16T00:00:00-05:00</endTime>
    <asType>{as_type}</asType>
    <bidID>aoo01</bidID>
    <ASOnlyPriceCurve>
      <startTime>2026-10-15T14:00:00-05:00</startTime>
      <endTime>2026-10-15T15:00:00-05:00</endTime>
      {curve}
    </ASOnlyPriceCurve>
  </ASOnlyOffer>
""")


@pytest.mark.parametrize("as_type", ["Reg-Up", "Reg-Down", "Non-Spin", "RRSPF", "ECRSS"])
def test_as_only_offer_products(as_type):
    assert check(aoo(as_type)).findings == []


@pytest.mark.parametrize("as_type", ["RRSUF", "RRSFF", "ECRSM", "NSPNM", "On-Non-Spin"])
def test_as_only_offer_other_products(as_type):
    # NP4-450-M §2.3: "AS Type (restricted to REGUP, REGDN, RRSPF, ONNS, or ECRSS)".
    xml = aoo(as_type)
    assert check(xml).schema == "valid"
    (f,) = market(xml)
    assert (f.rule, f.severity, f.where) == ("as-only-offer-type", ERROR, "asType")
    assert f.source == market_rules.SRC_NP4_450
    assert ("0.3.33" in f.message) == (as_type == "On-Non-Spin")


def test_as_only_offer_type_outside_the_xsd_is_left_to_the_schema():
    rep = check(aoo("REGUP"))  # NP4-450-M's code; the XML value is Reg-Up
    assert rep.schema == "invalid" and "as-only-offer-type" not in rep.by_rule()


def test_as_only_offer_amounts_and_prices():
    # NP4-450-M §2.3: amounts of at least 0.1 MW, prices from $0 to the DASWCAP.
    assert check(aoo(curve=points(("0.1", "0.00"), ("5.0", "5000.00")))).findings == []
    (f,) = market(aoo(curve=points(("0.05", "15.50"), ("5.0", "16.00"))))
    assert (f.rule, f.severity) == ("quantity-below-minimum", ERROR)
    assert "0.1" in f.message and f.source == market_rules.SRC_NP4_450
    # A 0 MW amount is below the minimum only if the minimum is read per amount: a warning.
    (f,) = market(aoo(curve=points(("0.0", "15.50"), ("5.0", "16.00"))))
    assert (f.rule, f.severity) == ("quantity-below-minimum", WARNING)
    (f,) = market(aoo(curve=points(("5.0", "-0.01"))))
    assert (f.rule, f.severity) == ("price-below-floor", ERROR)
    (f,) = market(aoo(curve=points(("5.0", "5000.01"))))
    assert (f.rule, f.severity) == ("price-above-cap", ERROR) and "5,000" in f.message


def test_as_only_offer_amounts_need_no_order():
    # The amounts are separate blocks, each with its own price, as in NP4-450-M's example.
    blocks = points(("10.0", "5.00"), ("5.0", "10.00"), ("20.0", "3.00"))
    assert check(aoo(curve=blocks)).findings == []


def test_energy_minimum_quantity():
    # §4.4.9.5.1(3), §4.4.9.6.1(2), §4.4.9.3.1(3): one MW, read as the curve's largest quantity.
    assert market(eoo(points(("0.5", "20.00"), ("1.0", "35.50")))) == []
    (f,) = market(eoo(points(("0.5", "20.00"), ("0.9", "35.50"))))
    assert (f.rule, f.severity) == ("quantity-below-minimum", ERROR)
    assert "§4.4.9.5.1(3)" in f.message and "0.9 MW" in f.message
    (f,) = market(eoo(points(("0.9", "20.00")), style="FIXED"))
    assert f.rule == "quantity-below-minimum"
    (f,) = market(eb(points(("0.9", "20.00")), style="VARIABLE"))
    assert "§4.4.9.6.1(2)" in f.message and f.fix.startswith("Bid at least 1 MW")
    (f,) = market(tpo(points(("0.0", "15.00"), ("0.5", "35.50"))))
    assert "§4.4.9.3.1(3)" in f.message and "Energy Storage Resource" in f.fix
    # An Energy Storage Resource's Energy Bid/Offer Curve (§4.4.9.7.1) states no minimum.
    assert market(tpo(points(("-0.5", "15.00"), ("0.5", "35.50")))) == []
