"""Documents from an untrusted source: nothing is fetched or expanded, and check() returns."""

import socket
import xml.etree.ElementTree as ET

import pytest

from ercot_ews_check import schema, sources
from ercot_ews_check.checker import ERROR, check
from ercot_ews_check.discrepancies import flatten, normalize

from helpers import EWS, cancel, energy_only_offer

NOTIFICATION = "http://www.ercot.com/schema/2007-06/nodal/notification"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
LAUGHS = "".join(
    [
        "<!DOCTYPE BidSet [",
        '<!ENTITY lol0 "lol">',
        *(f'<!ENTITY lol{i} "{f"&lol{i - 1};" * 10}">' for i in range(1, 10)),
        "]>\n",
    ]
)


def only(xml) -> tuple[str, str]:
    rep = check(xml)
    assert rep.blocked and len(rep.findings) == 1 and rep.schema == schema.INVALID, rep
    return rep.findings[0].rule, rep.findings[0].message


@pytest.fixture
def connections(monkeypatch):
    """Every connection attempted during the test, refused."""
    seen = []

    def record(address, *args, **kwargs):
        seen.append(address)
        raise OSError("refused")

    monkeypatch.setattr(socket, "create_connection", record)
    monkeypatch.setattr(socket.socket, "connect", lambda self, address: record(address))
    return seen


def test_doctype_is_refused_and_no_entity_text_reaches_the_report():
    rule, message = only(LAUGHS + energy_only_offer().replace("HB_HOUSTON", "&lol9;"))
    assert rule == "doctype" and "lol" not in message


def test_doctype_is_refused_in_utf16_and_in_str():
    xml = '<?xml version="1.0" encoding="UTF-16"?>\n' + LAUGHS + energy_only_offer()
    assert only(xml.encode("utf-16"))[0] == "doctype"
    assert only(xml.split("\n", 1)[1])[0] == "doctype"


def test_external_entity_is_never_read(tmp_path, connections):
    secret = tmp_path / "secret.txt"
    secret.write_text("NOT-FOR-THE-REPORT", encoding="utf-8")
    for target in (secret.as_uri(), "http://127.0.0.1:9/entity"):
        xml = f'<!DOCTYPE BidSet [<!ENTITY x SYSTEM "{target}">]>\n' + energy_only_offer().replace(
            "HB_HOUSTON", "&x;"
        )
        rep = check(xml)
        assert [f.rule for f in rep.findings] == ["doctype"]
        assert "NOT-FOR-THE-REPORT" not in rep.to_json()
        verdict = schema.validate(xml)
        assert verdict.state == schema.INVALID and "DOCTYPE" in verdict.detail
    assert connections == []


def test_doctype_cites_the_page_that_states_the_rule():
    rep = check(LAUGHS + energy_only_offer())
    location = rep.findings[0].source.split("developer.ercot.com/", 1)[1]
    pages = [flatten(d["text"]) for d in sources.portal_docs() if d["location"] == location]
    assert any(normalize("A SOAP message must NOT contain a DTD reference") in p for p in pages)


def test_a_document_cannot_make_xmlschema_fetch_a_schema(connections):
    # xmlschema maps the XSLT namespace to a schema on www.w3.org, and Message.xsd's Header
    # ends in a strict wildcard.
    xslt = '<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="1.0"/>'
    xml = cancel("QSE1.20261015.EOO.HB_HOUSTON.eoo01.14").replace("</Header>", xslt + "</Header>")
    rep = check(xml)
    assert rep.schema == schema.INVALID and connections == []


def test_schema_location_hints_are_ignored(tmp_path, connections):
    secret = tmp_path / "hint.xsd"
    secret.write_text("NOT-FOR-THE-REPORT", encoding="utf-8")
    hints = f'xmlns:xsi="{XSI}" xsi:schemaLocation="{EWS} http://127.0.0.1:9/a.xsd urn:x {secret}"'
    xml = energy_only_offer().replace(f'xmlns="{EWS}"', f'xmlns="{EWS}" {hints}')
    foreign = f'<f:x xmlns:f="urn:x" xmlns:xsi="{XSI}" xsi:noNamespaceSchemaLocation="{secret}"/>'
    for doc in (xml, energy_only_offer(extra=foreign)):
        assert "NOT-FOR-THE-REPORT" not in check(doc).to_json()
    assert connections == []


def test_deep_nesting_is_refused():
    deep = "<x>" * schema.MAX_DEPTH + "</x>" * schema.MAX_DEPTH
    assert only(energy_only_offer(extra=deep))[0] == "nesting-depth"
    # Foreign content in Notification.xsd's lax wildcard made xmlschema recurse until it failed.
    foreign = '<f:x xmlns:f="urn:x">' * 400 + "</f:x>" * 400
    notify = (
        f'<Notify xmlns="{NOTIFICATION}"><NotificationMessage><Message>{foreign}</Message>'
        "</NotificationMessage></Notify>"
    )
    assert only(notify)[0] == "nesting-depth"
    assert schema.validate(notify).state == schema.INVALID


def test_a_refusal_stops_the_parse_at_the_chunk_that_holds_it(monkeypatch):
    fed = []

    class Recording(ET.XMLParser):
        def feed(self, data):
            fed.append(len(data))
            return super().feed(data)

    monkeypatch.setattr(ET, "XMLParser", Recording)
    filler = "<x/>" * schema.CHUNK
    deep = "<x>" * schema.MAX_DEPTH + "</x>" * schema.MAX_DEPTH
    for xml, refusal in [
        (LAUGHS + energy_only_offer(extra=filler), schema.DoctypeError),
        (energy_only_offer(extra=deep + filler), schema.DepthError),
    ]:
        fed.clear()
        with pytest.raises(refusal):
            schema.parse(xml)
        assert fed == [schema.CHUNK]


def test_a_malformed_document_is_blocked_when_the_schemas_are_missing(tmp_path):
    rep = check("<BidSet", xsd_dir=tmp_path / "absent")
    assert rep.blocked and rep.schema == schema.INVALID


def _deepest(element, seen=frozenset()) -> int:
    content = getattr(element.type, "content", None)
    kids = [e for e in getattr(content, "iter_elements", list)() if getattr(e, "name", None)]
    return 1 + max((_deepest(k, seen | {k.name}) for k in kids if k.name not in seen), default=0)


def test_every_declared_element_sits_far_inside_the_depth_limit():
    index = schema._index(str(sources.xsd_dir()))
    deepest = max(_deepest(sch.maps.elements[name]) for name, (_, sch) in index.items())
    assert deepest * 10 <= schema.MAX_DEPTH


def test_errors_past_the_cap_are_counted_not_explained():
    xml = energy_only_offer(extra="    " + "<junk/>" * (schema.MAX_ERRORS + 50) + "\n")
    verdict = schema.validate(xml)
    assert len(verdict.errors) == schema.MAX_ERRORS and verdict.unlisted == 50
    found = [f for f in check(xml).findings if f.rule == "schema"]
    assert len(found) == schema.MAX_ERRORS + 1
    assert found[-1].severity == ERROR and found[-1].message.startswith("50 more schema error")


@pytest.mark.parametrize("encoding", ["utf-7", "x-unknown", "rot13", "idna"])
def test_an_encoding_expat_cannot_use_is_not_well_formed(encoding):
    xml = f'<?xml version="1.0" encoding="{encoding}"?><BidSet xmlns="{EWS}"/>'
    rule, message = only(xml.encode("ascii"))
    assert rule == "schema" and message.startswith("not well-formed XML")


def test_a_str_that_cannot_be_encoded_is_not_well_formed():
    rule, message = only(energy_only_offer().replace("HB_HOUSTON", "HB_\ud800"))
    assert rule == "schema" and message.startswith("not well-formed XML")


@pytest.mark.parametrize(
    "xml",
    [
        energy_only_offer(start="9999-12-31T23:00:00-05:00"),
        energy_only_offer(start="0001-01-01T00:00:00+05:00"),
        energy_only_offer(mw="1e9999999"),
        cancel("QSE1.99991231.EOO.HB_HOUSTON.eoo01.14"),
        f'<BidSet xmlns="{EWS}"><tradingDate>0001-01-01</tradingDate><ThreePartOffer>'
        "<EnergyOfferCurve><CurveData><xvalue>50</xvalue><y1value>3000</y1value></CurveData>"
        "</EnergyOfferCurve></ThreePartOffer></BidSet>",
    ],
    ids=["year-9999", "year-1", "huge-exponent", "cancel-9999-12-31", "offer-cap-on-day-1"],
)
def test_values_at_the_edges_of_the_calendar_and_of_decimal_return_a_report(xml):
    assert check(xml).schema in (schema.VALID, schema.INVALID)
