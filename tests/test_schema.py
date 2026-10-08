from ercot_ews_check import schema

from helpers import EWS, EXAMPLES, MSG


def test_examples_validate():
    for path in EXAMPLES:
        assert schema.validate(path.read_bytes()).ok, path.name


def test_unknown_root():
    v = schema.validate(f'<Nothing xmlns="{EWS}"/>')
    assert v.state == schema.INVALID and "top-level" in v.detail


def test_missing_schemas_are_unverified_not_valid(tmp_path):
    v = schema.validate(EXAMPLES[0].read_bytes(), xsd_dir=tmp_path / "absent")
    assert v.state == schema.UNVERIFIED and not v.ok


def test_soap_envelope_is_unwrapped():
    inner = EXAMPLES[0].read_text().split("?>", 1)[-1]
    envelope = (
        '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/">'
        f"<soapenv:Body>{inner}</soapenv:Body></soapenv:Envelope>"
    )
    assert schema.validate(envelope).ok


def test_payload_inside_a_message_is_checked():
    # Message.xsd skips Payload contents, so the payload is validated separately.
    xml = f"""<RequestMessage xmlns="{MSG}"><Header><Verb>create</Verb><Noun>BidSet</Noun>
<ReplayDetection><Nonce>1</Nonce><Created>2026-10-14T09:00:00-05:00</Created></ReplayDetection>
<Revision>1</Revision><Source>QSE1</Source></Header>
<Payload><BidSet xmlns="{EWS}"><tradingDate>not-a-date</tradingDate></BidSet></Payload>
</RequestMessage>"""
    v = schema.validate(xml)
    assert v.state == schema.INVALID
    assert {e.kind for e in v.errors} == {"datatype"}
