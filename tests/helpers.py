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
