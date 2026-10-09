import xml.etree.ElementTree as ET

from ercot_ews_check import requirements, schema, sources

from helpers import EXAMPLES


def _xsd_paths(tag: str) -> set[str]:
    """Element paths the XSD declares under a BidSet payload type."""
    index = schema._index(str(sources.xsd_dir()))
    sch = index["{http://www.ercot.com/schema/2007-06/nodal/ews}BidSet"][1]
    root = sch.find(
        f"{{http://www.ercot.com/schema/2007-06/nodal/ews}}BidSet/"
        f"{{http://www.ercot.com/schema/2007-06/nodal/ews}}{tag}"
    )
    out: set[str] = set()

    def walk(el, prefix, depth=0):
        if depth > 6 or el.type.is_simple():
            return
        for child in el.type.content.iter_elements():
            if getattr(child, "type", None) is None:  # xs:any
                continue
            name = child.local_name
            path = f"{prefix}/{name}" if prefix else name
            out.add(path)
            walk(child, path, depth + 1)

    walk(root, "")
    return out


def test_tables_cover_every_mapped_page():
    tables = requirements.tables()
    assert set(requirements.PAGE_TO_TAG) <= set(tables)


def test_corrected_paths_exist_in_the_schema():
    for (tag, _), fixed in requirements.PATH_CORRECTIONS.items():
        assert fixed in _xsd_paths(tag), (tag, fixed)


def test_casing_corrections_exist_in_the_schema():
    assert {"source", "sink"} <= _xsd_paths("CRR")
    assert "resource" in _xsd_paths("RTMEnergyBid")


def test_required_paths_resolve_for_submitted_products():
    for tag in ("ASOnlyOffer", "EnergyOnlyOffer", "EnergyBid", "PTPObligation"):
        missing = set(requirements.required(tag)) - _xsd_paths(tag)
        assert not missing, (tag, missing)


def test_examples_carry_every_required_field():
    for path in EXAMPLES:
        root = schema.payload_root(ET.parse(path).getroot())
        for bidset in root.iter("{http://www.ercot.com/schema/2007-06/nodal/ews}BidSet"):
            for payload in bidset:
                tag = payload.tag.rsplit("}", 1)[-1]
                if requirements.page_for(tag):
                    assert not requirements.missing(tag, requirements.paths_in(payload))


def test_aoo_requires_the_corrected_curve_paths():
    req = requirements.required("ASOnlyOffer")
    assert "ASOnlyPriceCurve/CurveData/y1value" in req
    assert "ASOnlyPriceCurve/yvalue" not in req
