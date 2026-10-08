import re

import pytest

from ercot_ews_check import sources, values


def xsd(name: str) -> str:
    return (sources.xsd_dir() / name).read_text(errors="replace")


def test_patterns_match_the_schema():
    common = xsd("ErcotCommonTypes.xsd")
    assert re.search(
        r'name="ErcotPrice">\s*<xs:restriction base="xs:decimal">\s*<xs:pattern value="'
        + re.escape(values.PRICE.pattern[2:-2])
        + '"',
        common,
    )
    assert values.BID_ID.pattern[2:-2] in common


def test_mw_bounds_come_from_the_unreferenced_type():
    common = xsd("ErcotCommonTypes.xsd")
    block = common[common.index('name="MWSingleDecimal_Orig"') :][:600]
    assert "-9999.9" in block and "9999.9" in block


def test_curve_point_caps_match_the_schema():
    common = xsd("ErcotCommonTypes.xsd")
    for curve, cap in values.CURVE_POINT_CAP.items():
        start = common.index(f'<xs:complexType name="{curve}">')
        block = common[start : common.index("</xs:complexType>", start)]
        assert f'name="CurveData" maxOccurs="{cap}"' in block, curve


def test_check_price_and_mw():
    assert values.check_price("25.50") is None
    assert values.check_price("25.505")
    assert values.check_mw("10.0") is None
    assert values.check_mw("10.05")
    assert values.check_mw("10000")


def test_quantize_mw_rounds_toward_zero():
    assert values.quantize_mw(4.99) == 4.9
    assert values.quantize_mw(-4.99) == -4.9
    with pytest.raises(values.ValueFormatError):
        values.quantize_mw(10_000)


def test_bid_id():
    assert values.check_bid_id("eoo01") is None
    assert values.check_bid_id("a")
    assert values.check_bid_id("-bad")
    assert values.bid_id_tag("PTPObligation") == "bidId"
    with pytest.raises(KeyError):
        values.bid_id_tag("Nope")


def test_decimals():
    assert values.decimals("1.25") == 2
    assert values.decimals("1.6E0") == 1
    assert values.decimals("7") == 0
