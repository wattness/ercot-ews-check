"""ERCOT's per-element requirement tables, extracted from the developer portal.

Every element of the product payload types is ``minOccurs="0"``: ERCOT reuses one
schema for create, get and cancel ("The XML schema provided to describe product
types has all fields optional"). What a *create* must carry is stated only in the
Message Element table on each product page, with Y (required), N (optional) and
K (key) markers. This module reads those tables out of the vendored portal search
index rather than shipping a transcription of them.
"""

from __future__ import annotations

import html
import re
from functools import lru_cache

from ercot_ews_check import sources

DATATYPES = (
    "dateTime", "DateTime", "string", "String", "float", "Float",
    "decimal", "Decimal", "Boolean", "Integer",
)  # fmt: skip
SPEC_CAP = 600

# Portal page (URL path segment) -> the BidSet payload it documents.
PAGE_TO_TAG: dict[str, str] = {
    "Ancillary%20Service%20Offer%20%28ASO%29": "ASOffer",
    "Ancillary%20Service%20Only%20Offer%20%28AOO%29": "ASOnlyOffer",
    "Ancillary%20Service%20Trade%20%28AST%29": "ASTrade",
    "Availability%20Plan%20%28AVP%29": "AVP",
    "Capacity%20Trade%20%28CT%29": "CapacityTrade",
    "Current%20Operating%20Plan%20%28COP%29": "COP",
    "DAM%20Energy%20Bid%20%28EB%29": "EnergyBid",
    "DAM%20Energy-Only%20Offer%20%28EOO%29": "EnergyOnlyOffer",
    "Energy%20Trade%20%28ET%29": "EnergyTrade",
    "Exceptional%20Fuel%20Cost%20%28EFC%29": "EFC",
    "Incremental%20and%20Decremental%20Energy%20Offer%20Curves%20%28IDO%29": "IncDecOffer",
    "Output%20Schedule%20%28OS%29": "OutputSchedule",
    "PTP%20Obligation%20Bid%20%20%28PTP%29": "PTPObligation",
    "PTP%20Obligation%20with%20Links%20to%20Option%20%28CRR%29": "CRR",
    "Real-Time%20Market%20Energy%20Bid%20%28REB%29": "RTMEnergyBid",
    "Self-Arranged%20Ancillary%20Service%20Quantities%20%28SAA%29": "SelfArrangedAS",
    "Self-Schedule%20%28SS%29": "SelfSchedule",
    "Three-Part%20Supply%20Offer%20%28TPO%29": "ThreePartOffer",
}

# Paths the tables name that the schema spells differently. Each one is a catalogued
# discrepancy (see discrepancies/), and a test checks every corrected path exists in the XSD.
PATH_CORRECTIONS: dict[tuple[str, str], str] = {
    ("ASOnlyOffer", "ASOnlyPriceCurve/xvalue"): "ASOnlyPriceCurve/CurveData/xvalue",
    ("ASOnlyOffer", "ASOnlyPriceCurve/yvalue"): "ASOnlyPriceCurve/CurveData/y1value",
    ("ASOffer", "PriceCurve/startTime"): "ASPriceCurve/startTime",
    ("ASOffer", "PriceCurve/endTime"): "ASPriceCurve/endTime",
}
CASING_CORRECTIONS: dict[str, str] = {"Source": "source", "Sink": "sink"}

_HEADER_CELLS = frozenset(
    {"Element", "Req", "Req?", "REQ", "Data type", "Datatype", "DataType", "Description",
     "Values", "Value", "Y", "N", "K", *DATATYPES}
)  # fmt: skip
_P_ANY = re.compile(r"<p>\s*(.*?)\s*</p>", re.S)
_COND_MARKER = re.compile(r"If\s+[A-Z]")
_VALUE_SHAPE = re.compile(r"[A-Za-z][\w\- ]{0,29}")
# No "." in the name class: with one, a row boundary can land inside the previous
# row's Values text ("...359.99 inclusive. statistic").
_ROW = re.compile(
    r"([A-Za-z][\w/\- ]{0,60}?)\s+(K,\s*N|[YNK]|If [^,]{0,30}?)\s+(" + "|".join(DATATYPES) + r")\b"
)
_TABLE = re.compile(
    r"(?:Req\??|REQ)\s+Data\s?type\s+Description\s+Values(.*?)(?=(?:Req\??|REQ)\s+Data\s?type|$)",
    re.S,
)
_HAS_TABLE = re.compile(r"(?:Req\??|REQ)\s+Data\s?type", re.I)
_RANGE = re.compile(r"between\s+([\-\d.]+)\s+and\s+([\-\d.]+)", re.I)
_ENUM = re.compile(r"'([A-Za-z][\w\-]{0,30})'")
_ENUM_LIST = re.compile(r"Enumeration\s*\(([^)]{1,120})\)", re.I)


def _quote_values(raw: str) -> str:
    """Rewrite ``<p>value</p>`` as ``'value'`` where the paragraph is an enumerated value.

    ERCOT also wraps headers, markers, datatypes and halves of split paths
    (``<p>CapacitySchedule/</p> <p>TmPoint/time</p>``) in ``<p>``; those are left alone.
    """
    out, carry, pos = [], False, 0
    for m in _P_ANY.finditer(raw):
        body = m.group(1).strip()
        out.append(raw[pos : m.start()])
        keep = (
            carry
            or "/" in body
            or body in _HEADER_CELLS
            or _COND_MARKER.match(body)
            or not _VALUE_SHAPE.fullmatch(body)
        )
        out.append(m.group(0) if keep else f"'{body}'")
        carry = body.endswith("/") or bool(_COND_MARKER.match(body))
        pos = m.end()
    out.append(raw[pos:])
    return "".join(out)


def _name_span(hit) -> tuple[str, int]:
    """The element name of a row match, and where in the body it starts.

    The lazy name group can start inside the previous row's Values text, so the
    name is the last token (rejoining paths split after a slash).
    """
    raw = hit.group(1)
    toks = [(m.group(0), m.start()) for m in re.finditer(r"\S+", raw)]
    while len(toks) > 1 and toks[-1][0].isdigit():  # footnote markers: "bidID 1 K string"
        toks.pop()
    if not toks:
        return "", hit.start()
    i = len(toks) - 1
    name = toks[i][0]
    while i > 0 and toks[i - 1][0].endswith("/"):
        i -= 1
        name = toks[i][0] + name
    return name, hit.start(1) + toks[i][1]


def _enum_values(tail: str) -> list[str] | None:
    found = set(_ENUM.findall(tail))
    for listed in _ENUM_LIST.findall(tail):
        found |= {v.strip() for v in listed.split(",") if v.strip()}
    return sorted(found) or None


def extract(docs) -> dict[str, dict[str, dict]]:
    """Page -> element path -> {req, datatype, spec, range, enum}."""
    out: dict[str, dict[str, dict]] = {}
    for doc in docs:
        text = html.unescape(re.sub(r"<[^>]+>", " ", _quote_values(doc["text"])))
        if not _HAS_TABLE.search(text):
            continue
        page = doc["location"].split("/")[-2] or doc["location"]
        rows: dict[str, dict] = {}
        for table in _TABLE.finditer(text):
            body = table.group(1)
            parent = ""
            hits = list(_ROW.finditer(body))
            for i, hit in enumerate(hits):
                _, marker, datatype = hit.groups()
                end = _name_span(hits[i + 1])[1] if i + 1 < len(hits) else len(body)
                tail = re.sub(r"\s+", " ", body[hit.end() : end]).strip()
                name, _ = _name_span(hit)
                if not name:
                    continue
                # Continuation rows drop the parent: "Limits/startTime" then "/endTime".
                if name.startswith("/"):
                    name = parent + name if parent else name.lstrip("/")
                elif "/" in name:
                    parent = name.rsplit("/", 1)[0]
                else:
                    parent = ""
                if name not in rows:
                    rng = _RANGE.search(tail)
                    rows[name] = {
                        "req": re.sub(r"\s+", " ", marker).strip(),
                        "datatype": datatype,
                        "spec": tail[:SPEC_CAP],
                        "range": [rng.group(1), rng.group(2)] if rng else None,
                        "enum": _enum_values(tail),
                    }
        if not rows:
            continue
        # A <p> run can list sibling element names rather than values.
        own = {k.rsplit("/", 1)[-1] for k in rows}
        for spec in rows.values():
            if spec["enum"]:
                spec["enum"] = [v for v in spec["enum"] if v not in own] or None
        # A page appears as several index entries (one per anchor); merge them.
        merged = out.setdefault(page, {})
        for k, v in rows.items():
            merged.setdefault(k, v)
    return out


@lru_cache(maxsize=1)
def tables() -> dict[str, dict[str, dict]]:
    return extract(sources.portal_docs())


def _fix(path: str, tag: str) -> str:
    path = PATH_CORRECTIONS.get((tag, path), path)
    return "/".join(CASING_CORRECTIONS.get(p, p) for p in path.split("/"))


def page_for(tag: str) -> str | None:
    return next((page for page, t in PAGE_TO_TAG.items() if t == tag), None)


def table(tag: str) -> dict[str, dict]:
    """Element path -> row, for one BidSet payload tag, with corrections applied."""
    page = page_for(tag)
    rows = tables().get(page, {}) if page else {}
    return {_fix(p, tag): row for p, row in rows.items()}


def required(tag: str) -> tuple[str, ...]:
    """Paths marked Y or K: what a create must carry."""
    return tuple(sorted(p for p, r in table(tag).items() if r["req"] in ("Y", "K")))


def key_fields(tag: str) -> tuple[str, ...]:
    return tuple(sorted(p for p, r in table(tag).items() if r["req"] == "K"))


def conditional(tag: str) -> dict[str, str]:
    """Paths whose requirement depends on the submission, with ERCOT's condition."""
    return {p: r["req"] for p, r in table(tag).items() if r["req"] not in ("Y", "N", "K")}


def paths_in(element) -> set[str]:
    """Every element path under ``element``, slash-joined and namespace-free."""
    found: set[str] = set()

    def walk(node, prefix: str) -> None:
        for child in node:
            path = (
                f"{prefix}/{child.tag.rsplit('}', 1)[-1]}"
                if prefix
                else child.tag.rsplit("}", 1)[-1]
            )
            found.add(path)
            walk(child, path)

    walk(element, "")
    return found


def values_in(element) -> list[tuple[str, str]]:
    """(path, text) for every leaf with text, and (name, value) for every attribute."""
    out: list[tuple[str, str]] = []

    def walk(node, prefix: str) -> None:
        for child in node:
            name = child.tag.rsplit("}", 1)[-1]
            path = f"{prefix}/{name}" if prefix else name
            text = (child.text or "").strip()
            if text and len(child) == 0:
                out.append((path, text))
            for attr, val in child.attrib.items():
                out.append((attr.rsplit("}", 1)[-1], val))
            walk(child, path)

    walk(element, "")
    return out


def missing(tag: str, present: set[str]) -> tuple[str, ...]:
    return tuple(p for p in required(tag) if p not in present)
