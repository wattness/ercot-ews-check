"""Validate EWS documents against ERCOT's published XSDs."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from ercot_ews_check import sources
from ercot_ews_check.namespaces import EWS, MESSAGE, NOTIFICATION, SOAP_ENV, namespace, q

VALID, INVALID, UNVERIFIED = "valid", "invalid", "unverified"
# ERCOT's schemas declare no element more than a few levels below a top-level element.
# Validation recurses at every level, and a few hundred levels exhaust Python's stack.
MAX_DEPTH = 100
# Errors kept from one validation; the rest are counted. Explaining an error costs more
# than finding it, and one stray element repeated can raise one error per copy.
MAX_ERRORS = 100
# The message inside each NotificationMessage of a Notify.
_NOTIFIED = f"{q(NOTIFICATION, 'NotificationMessage')}/{q(NOTIFICATION, 'Message')}/*"
# Characters (or bytes) handed to expat at a time. A refusal stops the parse at the end
# of the chunk that holds it, so expat never reads far past a DOCTYPE or a deep nest.
CHUNK = 1 << 16


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
    present: tuple[str, ...] = ()  # the parent's child tags, each once, for children errors


@dataclass(frozen=True)
class Verdict:
    """``valid``, ``invalid`` or ``unverified``. Unverified is never a pass.

    ``errors`` holds at most MAX_ERRORS errors; ``unlisted`` counts the rest.
    """

    state: str
    schema: str = ""
    detail: str = ""
    errors: tuple[SchemaError, ...] = field(default_factory=tuple)
    unlisted: int = 0

    @property
    def ok(self) -> bool:
        return self.state == VALID


class DoctypeError(Exception):
    """A document type declaration, refused when expat reports it; no DTD text reaches the tree."""


class DepthError(Exception):
    """Elements nested more than MAX_DEPTH levels deep."""


class _TreeBuilder(ET.TreeBuilder):
    depth = 0

    def doctype(self, name, pubid, system):
        raise DoctypeError(
            "The document has a document type declaration (<!DOCTYPE ...>). A SOAP message "
            "must not contain one, and this tool does not use DTDs or entities, so nothing "
            "else was checked."
        )

    def start(self, tag, attrs):
        self.depth += 1
        if self.depth > MAX_DEPTH:
            raise DepthError(
                f"Elements nest more than {MAX_DEPTH} levels deep, far deeper than anything "
                "ERCOT's schemas declare, so nothing else was checked."
            )
        return super().start(tag, attrs)

    def end(self, tag):
        self.depth -= 1
        return super().end(tag)


def parse(xml: str | bytes) -> ET.Element:
    """Parse a document from an untrusted source.

    No DTD or entity text reaches the tree, and nothing is fetched. A DOCTYPE raises
    DoctypeError and nesting past MAX_DEPTH raises DepthError; either stops the parse at
    the end of the CHUNK being fed, of which expat still reads the rest, within its own
    entity-amplification limits. Anything else expat cannot read, including an encoding
    it does not support, raises ET.ParseError.
    """
    parser = ET.XMLParser(target=_TreeBuilder())
    try:
        for start in range(0, len(xml), CHUNK):
            parser.feed(xml[start : start + CHUNK])
        return parser.close()
    except (LookupError, ValueError) as e:  # an unusable encoding, or a str with a surrogate
        raise ET.ParseError(str(e)) from e


def _uri_mapper() -> dict[str, str]:
    """Keep schema loading offline: WSS secext imports the W3C xml.xsd by URL."""
    import xmlschema

    local = Path(xmlschema.__file__).parent / "schemas" / "XML" / "xml.xsd"
    return {"http://www.w3.org/2001/xml.xsd": str(local)} if local.is_file() else {}


@lru_cache(maxsize=4)
def _index(xsd_dir: str) -> dict[str, tuple[str, object]]:
    """Global element (Clark name) -> (schema file, loaded schema).

    Schemas load from local files only and without xmlschema's fallback locations. By
    default xmlschema maps some namespaces (XSLT among them) to schemas on www.w3.org and
    fetches one when a document puts an element of that namespace in a wildcard.
    """
    import xmlschema

    owner: dict[str, tuple[str, object]] = {}
    for path in sorted(Path(xsd_dir).glob("*.xsd")):
        sch = xmlschema.XMLSchema(
            str(path), uri_mapper=_uri_mapper(), allow="local", use_fallback=False
        )
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


def _structured(err, child_tags: dict[int, tuple[str, ...]]) -> SchemaError:
    """``child_tags`` caches each parent's child tags across the errors of one validation."""
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
        present = ()
        if elem is not None:
            if id(elem) not in child_tags:
                child_tags[id(elem)] = tuple(dict.fromkeys(c.tag for c in elem))
            present = child_tags[id(elem)]
        return SchemaError(
            **common,
            kind="children",
            invalid_tag=err.invalid_tag or "",
            expected=expected,
            model=model,
            present=present,
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
    """The root, plus each document it carries, and each document those carry.

    ERCOT's schemas leave what a document carries unchecked, so validating the outer
    document alone never checks it. Message.xsd lets a Payload hold any element of another
    namespace (``xsd:any processContents="skip"``). Notification.xsd holds the message in
    each NotificationMessage of a Notify in an ``xsd:any processContents="lax"``, and
    imports no schema that declares one. ErcotGetNotifications.xsd holds the notifications
    Get Notifications returns, in a NotificationMessages, as ``xsd:any processContents="skip"``.
    """
    if root.tag == q(NOTIFICATION, "Notify"):
        held = list(root.iterfind(_NOTIFIED))
    elif root.tag == q(EWS, "NotificationMessages"):
        held = list(root)
    elif (payload := root.find(q(MESSAGE, "Payload"))) is not None:
        held = [c for c in payload if c.tag.startswith("{") and namespace(c.tag) != MESSAGE]
    else:
        held = []
    return [root, *(doc for child in held for doc in documents(child))]


def type_names(sch, path: str) -> set[str]:
    """Local names of the XSD type (and its base types) declared at a Clark-notation path."""
    t = getattr(sch.find(path), "type", None)
    names = set()
    while t is not None and getattr(t, "name", None):
        names.add(t.local_name)
        t = getattr(t, "base_type", None)
    return names


def validate(xml: str | bytes, xsd_dir: Path | None = None) -> Verdict:
    """Validate one EWS document; unwraps a SOAP envelope and checks message payloads too.

    A document that cannot be parsed is invalid whether or not the XSDs can be loaded.
    """
    try:
        root = parse(xml)
    except ET.ParseError as e:
        return Verdict(INVALID, detail=f"not well-formed XML: {e}")
    except (DoctypeError, DepthError) as e:
        return Verdict(INVALID, detail=str(e))
    xsd_dir = Path(xsd_dir or sources.xsd_dir())
    if not xsd_dir.is_dir():
        return Verdict(UNVERIFIED, detail=f"no XSDs at {xsd_dir}")
    root = payload_root(root)
    index = _index(str(xsd_dir))
    names, errors, unlisted, child_tags = [], [], 0, {}
    for doc in documents(root):
        hit = index.get(doc.tag)
        if hit is None:
            errors.append(SchemaError(path="/", reason="unknown root element", element=doc.tag))
            continue
        names.append(hit[0])
        for err in hit[1].iter_errors(doc, use_location_hints=False):
            if len(errors) < MAX_ERRORS:
                errors.append(_structured(err, child_tags))
            else:
                unlisted += 1
    unlisted += max(0, len(errors) - MAX_ERRORS)
    errors = errors[:MAX_ERRORS]
    if errors:
        detail = errors[0].reason
        if errors[0].reason == "unknown root element":
            detail = f"no EWS schema declares <{errors[0].element}> as a top-level element"
        return Verdict(
            INVALID,
            schema=", ".join(names),
            detail=detail,
            errors=tuple(errors),
            unlisted=unlisted,
        )
    return Verdict(VALID, schema=", ".join(names))
