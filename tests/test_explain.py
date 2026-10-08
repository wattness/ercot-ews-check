from ercot_ews_check import schema
from ercot_ews_check.explain import explain

from helpers import MSG, ROOT, bidset, energy_only_offer


def first(xml: str):
    v = schema.validate(xml)
    assert v.errors
    return explain(v.errors[0])


def test_wrong_case_element_suggests_the_schema_spelling():
    x = first(
        '<Acknowledge xmlns="http://www.ercot.com/schema/2007-06/nodal/notification">'
        "<ReplyCode>OK</ReplyCode><TimeStamp>2026-10-15T09:00:00-05:00</TimeStamp>"
        "</Acknowledge>"
    )
    assert "<Timestamp>" in x.message and x.see == ("D021",)


def test_enumeration_case_hint():
    x = first(f"""<RequestMessage xmlns="{MSG}"><Header><Verb>Get</Verb><Noun>BidSet</Noun>
<ReplayDetection><Nonce>1</Nonce><Created>2026-10-14T09:00:00-05:00</Created></ReplayDetection>
<Revision>1</Revision><Source>QSE1</Source></Header></RequestMessage>""")
    assert "'get'" in x.fix and "D015" in x.see


def test_payload_in_the_message_namespace():
    x = first(f"""<RequestMessage xmlns="{MSG}"><Header><Verb>create</Verb><Noun>BidSet</Noun>
<ReplayDetection><Nonce>1</Nonce><Created>2026-10-14T09:00:00-05:00</Created></ReplayDetection>
<Revision>1</Revision><Source>QSE1</Source></Header>
<Payload><BidSet><tradingDate>2026-10-15</tradingDate></BidSet></Payload></RequestMessage>""")
    assert "BidSet" in x.message and "D029" in x.see


def test_retired_namespace():
    x = first(bidset("").replace("2007-06", "2007-05"))
    assert "retired 2007-05" in x.message


def test_out_of_order_names_the_sequence():
    xml = bidset("""  <EnergyOnlyOffer>
    <startTime>2026-10-15T00:00:00-05:00</startTime>
    <endTime>2026-10-16T00:00:00-05:00</endTime>
    <sp>HB_HOUSTON</sp>
    <bidID>eoo01</bidID>
    <expirationTime>2026-10-14T09:00:00-05:00</expirationTime>
  </EnergyOnlyOffer>
""")
    x = first(xml)
    assert "out of order" in x.message and "expirationTime" in x.message
    assert "D004" in x.see


def test_price_pattern_is_described():
    xml = (ROOT / "examples" / "ptp-obligation.xml").read_text()
    x = first(xml.replace("<price>12.00</price>", "<price>12.005</price>"))
    assert "ErcotPrice" in x.fix


def test_missing_element_is_not_called_out_of_order():
    xml = bidset("").replace("  <tradingDate>2026-10-15</tradingDate>\n", "")
    xml = xml.replace("</BidSet>", "  <EnergyBid/>\n</BidSet>")
    x = first(xml)
    assert x.message.startswith("<BidSet> is missing <tradingDate>")
    assert "out of order" not in x.message and x.see == ()


def test_unknown_element_cites_nothing_unrelated():
    x = first(
        bidset("  <tradeDate>2026-10-15</tradeDate>\n").replace(
            "  <tradingDate>2026-10-15</tradingDate>\n", ""
        )
    )
    assert "<tradeDate> is not an element of <BidSet>" in x.message and x.see == ()
    x = first(bidset("  <foo>1</foo>\n"))
    assert x.see == ()


def test_root_without_namespace_cites_nothing():
    x = first("<BidSet><tradingDate>2026-10-15</tradingDate></BidSet>")
    assert "no namespace" in x.message and x.see == ()


def test_retired_namespace_root_cites_d032():
    x = first(bidset("").replace("2007-06", "2007-05"))
    assert x.see == ("D032",)


def test_element_typo_from_the_docs_cites_its_entry():
    xml = """<OutageSet xmlns="http://www.ercot.com/schema/2007-06/nodal/ews"><Outage><Schedule>
<plannedSart>2026-11-03T08:00:00-06:00</plannedSart></Schedule></Outage></OutageSet>"""
    assert first(xml).see == ("D020",)


def test_date_and_datetime_hints_differ():
    x = first(bidset("").replace("2026-10-15</tradingDate>", "2026-10-15T00:00</tradingDate>"))
    assert "xs:date such as 2026-10-15" in x.fix
    x = first(energy_only_offer(start="2026-10-15 00:00"))
    assert "xs:dateTime" in x.fix
