"""Validate EWS documents against ERCOT's published XSDs."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from ercot_ews_check import sources
from ercot_ews_check.namespaces import MESSAGE, SOAP_ENV, q

VALID, INVALID, UNVERIFIED = "valid", "invalid", "unverified"


@dataclass(frozen=True)
class SchemaError:
    """One validation failure, kept structured so it can be explained."""

    path: str
    reason: str
    element: str = ""
    invalid_tag: str = ""
    expected: tuple[str, ...] = ()
    allowed: tuple[str, ...] = ()
    value: str = ""
    kind: str = ""  # children | enumeration | pattern | length | bound | datatype | other
    model: tuple[str, ...] = ()
    present: tuple[str, ...] = ()  # the parent's children, for children errors


@dataclass(frozen=True)
class Verdict:
    """``valid``, ``invalid`` or ``unverified``. Unverified is never a pass."""

    state: str
    schema: str = ""
    detail: str = ""
    errors: tuple[SchemaError, ...] = field(default_factory=tuple)

    @property
    def ok(self) -> bool:
        return self.state == VALID


def _uri_mapper() -> dict[str, str]:
    """Keep schema loading offline: WSS secext imports the W3C xml.xsd by URL."""
    import xmlschema

    local = Path(xmlschema.__file__).parent / "schemas" / "XML" / "xml.xsd"
    return {"http://www.w3.org/2001/xml.xsd": str(local)} if local.is_file() else {}


@lru_cache(maxsize=4)
def _index(xsd_dir: str) -> dict[str, tuple[str, object]]:
    """Global element (Clark name) -> (schema file, loaded schema)."""
    import xmlschema

    owner: dict[str, tuple[str, object]] = {}
    for path in sorted(Path(xsd_dir).glob("*.xsd")):
        sch = xmlschema.XMLSchema(str(path), uri_mapper=_uri_mapper())
        for el in sch.elements.values():
            declared = Path(el.schema.url or path).name
            if el.name not in owner or declared == path.name:
                owner[el.name] = (declared, sch)
    return owner


def payload_root(root: ET.Element) -> ET.Element:
    """The document inside a SOAP envelope, or the root itself."""
    if root.tag == q(SOAP_ENV, "Envelope"):
        body = root.find(q(SOAP_ENV, "Body"))
        if body is not None and len(body):
            return body[0]
    return root


def _structured(err) -> SchemaError:
    import xmlschema.validators as v

    reason = (err.reason or err.message or "").replace("\n", " ")
    elem = err.elem
    validator = err.validator
    common = {
        "path": err.path or "",
        "reason": reason,
        "element": elem.tag if elem is not None else "",
        "value": (elem.text or "").strip() if elem is not None and len(elem) == 0 else "",
    }
    if type(err).__name__ == "XMLSchemaChildrenValidationError":
        expected = tuple(getattr(x, "name", str(x)) for x in (getattr(err, "expected", None) or ()))
        model = ()
        if isinstance(validator, v.XsdGroup):
            model = tuple(e.name for e in validator.iter_elements() if getattr(e, "name", None))
        return SchemaError(
            **common,
            kind="children",
            invalid_tag=err.invalid_tag or "",
            expected=expected,
            model=model,
            present=tuple(c.tag for c in elem) if elem is not None else (),
        )
    name = type(validator).__name__
    if name == "XsdEnumerationFacets":
        return SchemaError(
            **common, kind="enumeration", allowed=tuple(map(str, validator.enumeration))
        )
    if name == "XsdPatternFacets":
        return SchemaError(**common, kind="pattern", allowed=tuple(validator.regexps))
    if "Length" in name:
        return SchemaError(**common, kind="length")
    if "Inclusive" in name or "Exclusive" in name:
        return SchemaError(**common, kind="bound")
    if type(err).__name__ == "XMLSchemaDecodeError":
        return SchemaError(**common, kind="datatype")
    return SchemaError(**common, kind="other")


def documents(root: ET.Element) -> list[ET.Element]:
    """The root, plus each payload inside a RequestMessage or ResponseMessage.

    Message.xsd declares Payload as ``xs:any processContents="skip"``, so validating
    an envelope alone never checks the BidSet inside it.
    """
    out = [root]
    payload = root.find(q(MESSAGE, "Payload"))
    if payload is not None:
        out.extend(
            c for c in payload if c.tag.startswith("{") and not c.tag.startswith(f"{{{MESSAGE}}}")
        )
    return out


def type_names(sch, path: str) -> set[str]:
    """Local names of the XSD type (and its base types) declared at a Clark-notation path."""
    t = getattr(sch.find(path), "type", None)
    names = set()
    while t is not None and getattr(t, "name", None):
        names.add(t.local_name)
        t = getattr(t, "base_type", None)
    return names


def validate(xml: str | bytes, xsd_dir: Path | None = None) -> Verdict:
    """Validate one EWS document; unwraps a SOAP envelope and checks message payloads too."""
    xsd_dir = Path(xsd_dir or sources.xsd_dir())
    if not xsd_dir.is_dir():
        return Verdict(UNVERIFIED, detail=f"no XSDs at {xsd_dir}")
    try:
        root = ET.fromstring(xml)
    except ET.ParseError as e:
        return Verdict(INVALID, detail=f"not well-formed XML: {e}")
    root = payload_root(root)
    index = _index(str(xsd_dir))
    names, errors = [], []
    for doc in documents(root):
        hit = index.get(doc.tag)
        if hit is None:
            errors.append(SchemaError(path="/", reason="unknown root element", element=doc.tag))
            continue
        names.append(hit[0])
        errors.extend(_structured(e) for e in hit[1].iter_errors(doc))
    if errors:
        detail = errors[0].reason
        if errors[0].reason == "unknown root element":
            detail = f"no EWS schema declares <{errors[0].element}> as a top-level element"
        return Verdict(INVALID, schema=", ".join(names), detail=detail, errors=tuple(errors))
    return Verdict(VALID, schema=", ".join(names))
