from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = sorted((ROOT / "examples").glob("*.xml"))
EWS = "http://www.ercot.com/schema/2007-06/nodal/ews"
MSG = "http://www.ercot.com/schema/2007-06/nodal/ews/message"


def bidset(body: str, trading_date: str = "2026-10-15") -> str:
    return f'<BidSet xmlns="{EWS}">\n  <tradingDate>{trading_date}</tradingDate>\n{body}</BidSet>\n'


def energy_only_offer(
    start="2026-10-15T00:00:00-05:00",
    end="2026-10-16T00:00:00-05:00",
    curves=None,
    mw="5.0",
    style="CURVE",
    extra="",
) -> str:
    curves = curves or [("2026-10-15T17:00:00-05:00", "2026-10-15T18:00:00-05:00")]
    body = "".join(
        f"""    <EnergyOfferCurve>
      <startTime>{a}</startTime>
      <endTime>{b}</endTime>
      <curveStyle>{style}</curveStyle>
      <CurveData>
        <xvalue>{mw}</xvalue>
        <y1value>20.00</y1value>
      </CurveData>
    </EnergyOfferCurve>
"""
        for a, b in curves
    )
    return bidset(f"""  <EnergyOnlyOffer>
    <startTime>{start}</startTime>
    <endTime>{end}</endTime>
    <expirationTime>2026-10-14T09:00:00-05:00</expirationTime>
    <sp>HB_HOUSTON</sp>
    <bidID>eoo01</bidID>
{extra}{body}  </EnergyOnlyOffer>
""")


def cancel(mrid: str) -> str:
    return f"""<RequestMessage xmlns="{MSG}">
  <Header>
    <Verb>cancel</Verb>
    <Noun>BidSet</Noun>
    <ReplayDetection>
      <Nonce>8d3f1c2e</Nonce>
      <Created>2026-10-14T09:00:00-05:00</Created>
    </ReplayDetection>
    <Revision>1</Revision>
    <Source>QSE1</Source>
  </Header>
  <Request>
    <ID>{mrid}</ID>
  </Request>
</RequestMessage>
"""


NOTIFICATION = "http://www.ercot.com/schema/2007-06/nodal/notification"
SOAP = "http://schemas.xmlsoap.org/soap/envelope/"


def response(verb: str, noun: str, payload: str = "") -> str:
    """A ResponseMessage from ERCOT, as a notification page's table describes one."""
    carried = f"  <Payload>\n{payload}  </Payload>\n" if payload else ""
    return f"""<ResponseMessage xmlns="{MSG}">
  <Header>
    <Verb>{verb}</Verb>
    <Noun>{noun}</Noun>
    <ReplayDetection>
      <Nonce>69bfbe3a</Nonce>
      <Created>2026-10-14T14:24:53-05:00</Created>
    </ReplayDetection>
    <Revision>1</Revision>
    <Source>ERCOT</Source>
  </Header>
  <Reply>
    <ReplyCode>OK</ReplyCode>
    <Timestamp>2026-10-14T14:24:53-05:00</Timestamp>
  </Reply>
{carried}</ResponseMessage>
"""


def notify(message: str) -> str:
    """A SOAP envelope holding a Notify, as a listener receives a notification."""
    return f"""<soapenv:Envelope xmlns:soapenv="{SOAP}">
  <soapenv:Body>
    <Notify xmlns="{NOTIFICATION}">
      <NotificationMessage>
        <Message>
{message}        </Message>
      </NotificationMessage>
    </Notify>
  </soapenv:Body>
</soapenv:Envelope>
"""


def points(*pairs) -> str:
    """CurveData elements for (MW, price) pairs."""
    return "".join(
        f"<CurveData><xvalue>{x}</xvalue><y1value>{y}</y1value></CurveData>" for x, y in pairs
    )


def message(payload: str, created: str = "2026-10-14T09:00:00-05:00") -> str:
    """A create RequestMessage carrying ``payload``, created at ``created``."""
    return f"""<RequestMessage xmlns="{MSG}">
  <Header>
    <Verb>create</Verb>
    <Noun>BidSet</Noun>
    <ReplayDetection><Nonce>8d3f1c2e</Nonce><Created>{created}</Created></ReplayDetection>
    <Revision>1</Revision>
    <Source>QSE1</Source>
  </Header>
  <Payload>
{payload}  </Payload>
</RequestMessage>
"""
