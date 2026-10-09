"""Plain-English explanations, with a fix, for XSD validation failures."""

from __future__ import annotations

import re
from dataclasses import dataclass

from ercot_ews_check import discrepancies
from ercot_ews_check.namespaces import EWS, MESSAGE, RETIRED_EWS, local, namespace
from ercot_ews_check.schema import SchemaError

# Human descriptions of ERCOT's patterned types, keyed by the regex xmlschema reports.
PATTERN_NAMES = {
    r"[+\-]?(\d{1,6}|\d{1,6}\.\d{0,2}|\.\d{1,2})": "an ErcotPrice: at most 6 integer digits "
    "and 2 decimal places, e.g. 25.50",
    r"([a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9])": "a BidId: letters and digits, with _ or - "
    "allowed between, starting and ending with a letter or digit",
}
DATATYPE_HINTS = {
    "dateTime": "an xs:dateTime such as 2026-10-15T07:00:00-05:00 (a 'T' between date and "
    "time, and a UTC offset or Z)",
    "date": "an xs:date such as 2026-10-15",
    "decimal": "a decimal number",
    "integer": "a whole number",
    "boolean": "true or false",
}


@dataclass(frozen=True)
class Explanation:
    where: str
    message: str
    fix: str
    see: tuple[str, ...] = ()


def short_path(path: str) -> str:
    return re.sub(r"\{[^}]*\}", "", path) or "/"


# Catalogue kinds that can explain each kind of failure.
NAME_KINDS = ("element-name", "element-path", "typo")
see = discrepancies.related


def _children(e: SchemaError) -> Explanation:
    parent = local(e.element)
    where = short_path(e.path)
    model = [local(m) for m in e.model]
    expected = [local(x) for x in e.expected]
    present = {local(x) for x in e.present}
    need = " or ".join(f"<{x}>" for x in expected) or "a required element"
    if not e.invalid_tag:
        return Explanation(
            where,
            f"<{parent}> ends before a required element: expected {need}.",
            f"Add {need} to <{parent}>.",
            see(("required-field",), elements=expected),
        )
    tag = local(e.invalid_tag)
    ns = namespace(e.invalid_tag)
    missing = bool(expected) and not present & set(expected)
    same_name = [m for m in e.model if local(m) == tag]
    if same_name and namespace(same_name[0]) != ns:
        want = namespace(same_name[0]) or "no namespace"
        got = ns or "no namespace"
        hint = ""
        if ns == MESSAGE:
            hint = (
                " The message namespace is probably the default namespace in scope;"
                " a payload must declare its own."
            )
        return Explanation(
            where,
            f"<{tag}> is in the wrong namespace ({got}); <{parent}> expects it in {want}.{hint}",
            f'Declare xmlns="{want}" on <{tag}> or use a prefix bound to it.',
            see(("namespace",), elements=(tag,)),
        )
    if parent == "Payload" and tag not in model and ns in (MESSAGE, ""):
        got = "the message namespace, probably the default in scope" if ns else "no namespace"
        return Explanation(
            where,
            f"<{tag}> is in {got}. <Payload> takes a document from another namespace "
            '(xs:any namespace="##other").',
            f'Declare xmlns="{EWS}" on <{tag}>, or the namespace its schema declares.',
            see(("namespace",), elements=(tag,)),
        )
    casing = [m for m in model if m.lower() == tag.lower()]
    if tag not in model and casing:
        return Explanation(
            where,
            f"<{tag}> is not an element of <{parent}>; the schema spells it <{casing[0]}>. "
            "XML names are case-sensitive.",
            f"Rename <{tag}> to <{casing[0]}>.",
            see(("element-name",), elements=(tag,)),
        )
    if ns == RETIRED_EWS:
        return Explanation(
            where,
            f"<{tag}> uses the retired 2007-05 namespace, which no current EWS schema declares.",
            "Use http://www.ercot.com/schema/2007-06/nodal/ews.",
            see(("namespace",), values=(RETIRED_EWS,)),
        )
    if missing and tag in model:
        return Explanation(
            where,
            f"<{parent}> is missing {need}, which the schema requires before <{tag}>.",
            f"Add {need} before <{tag}>.",
            see(("required-field",), elements=expected),
        )
    if missing:
        return Explanation(
            where,
            f"<{tag}> is not an element of <{parent}>, and <{parent}> is missing {need}, which "
            "the schema requires at this position.",
            f"Add {need}; remove <{tag}> or move it to where the schema declares it.",
            see(("required-field",), elements=expected) + see(NAME_KINDS, elements=(tag,)),
        )
    if tag in model:
        order = " -> ".join(model)
        detail = f"<{parent}> is a sequence: {order}."
        if expected:
            detail += f" At this position it expects <{expected[0]}>."
        return Explanation(
            where,
            f"<{tag}> is out of order, or repeated more often than allowed, inside <{parent}>. "
            f"{detail}",
            "Put the children in the schema's order and check the element's maximum count.",
            see(("element-order",), elements=(tag,)),
        )
    allowed = ", ".join(f"<{m}>" for m in model) or "none"
    return Explanation(
        where,
        f"<{tag}> is not an element of <{parent}>. Allowed here: {allowed}.",
        f"Remove <{tag}> or replace it with the element the schema declares.",
        see(NAME_KINDS, elements=(tag,)),
    )


def explain(e: SchemaError) -> Explanation:
    where = short_path(e.path)
    name = local(e.element)
    if e.kind == "children":
        return _children(e)
    if e.kind == "enumeration":
        close = [a for a in e.allowed if a.lower() == e.value.lower()]
        fix = (
            f"Use {close[0]!r} (enumerations are case-sensitive)."
            if close
            else f"Use one of: {', '.join(e.allowed)}."
        )
        return Explanation(
            where,
            f"{e.value!r} is not an allowed value of <{name}>.",
            fix,
            see(("enumeration-value",), values=(e.value,)),
        )
    if e.kind == "pattern":
        what = next((PATTERN_NAMES[p] for p in e.allowed if p in PATTERN_NAMES), None)
        what = what or f"the pattern {' or '.join(e.allowed)}"
        return Explanation(
            where,
            f"{e.value!r} in <{name}> does not match the schema's format.",
            f"Write it as {what}.",
            see(("value-format",), elements=(name,)),
        )
    if e.kind == "datatype":
        # elementpath names the type it tried: ...datetime.DateTime10 or ...datetime.Date10.
        m = re.search(r"xs:(\w+)", e.reason)
        if "DateTime" in e.reason:
            key = "dateTime"
        elif "Date" in e.reason:
            key = "date"
        else:
            key = m.group(1) if m else ""
        hint = DATATYPE_HINTS.get(key, "the type the schema declares")
        return Explanation(
            where,
            f"{e.value!r} is not a valid value for <{name}>.",
            f"Write {hint}.",
            see(("value-format",), elements=(name,)),
        )
    if e.kind in ("length", "bound"):
        return Explanation(
            where,
            f"<{name}>: {e.reason}.",
            "Bring the value within the stated limit.",
            see(("value-bound",), elements=(name,)),
        )
    if e.reason == "unknown root element":
        ns = namespace(e.element)
        if ns.startswith(RETIRED_EWS):
            hint = " It is in a retired 2007-05 namespace."
        elif not ns:
            hint = " It has no namespace; EWS documents declare one."
        else:
            hint = ""
        return Explanation(
            "/",
            f"No EWS schema declares <{name}> as a document root.{hint}",
            "Check the root element's name and namespace.",
            see(("namespace",), values=("2007-05",)) if ns.startswith(RETIRED_EWS) else (),
        )
    return Explanation(where, e.reason, "See the schema rule cited in the message.")
