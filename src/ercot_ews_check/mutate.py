"""Mutation testing: break a valid document one rule at a time and see what objects.

Two families of mutants, reported separately:

* ``schema`` mutants break a constraint extracted from the XSDs: delete a required
  element, swap a sequence, exceed a cap, leave an enumeration, break a pattern.
  xmlschema should catch all of them; the checker's own rules are not meant to.
* ``rule`` mutants stay schema-valid where they can and break a rule ERCOT states
  in prose: a field the tables mark required, a bound or hour boundary from the
  Values column, 24:00, overlapping intervals, a wrong trading date, the wrong
  number of points for a curveStyle, MW with more than one decimal, an offset
  that is not Central time, value1 on an RRS self-arranged quantity. A rule
  mutant counts as caught only by the rule it targets (``TARGET``).

Every rule mutant targets a rule this tool implements, and the required-field and
bound mutants come from the same extracted tables the checker reads, so they
measure enforcement, not coverage of ERCOT's prose; see constraints.coverage() for
what the extraction leaves unparsed.
"""

from __future__ import annotations

import copy
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import timedelta, timezone

from ercot_ews_check import checker, constraints, requirements, schema, sources
from ercot_ews_check.namespaces import EWS, local, q
from ercot_ews_check.xsd_rules import Rule

# Rule mutant kind -> the checker rule that must report it.
TARGET = {
    "required-field": "missing-required-field",
    constraints.NUMERIC: "value-numeric-bound",
    constraints.HOUR_BOUNDARY: "silent-hour-rounding",
    constraints.ENUM: "value-enumerated",
    "trade-date": "trade-date-mismatch",
    "hour-24": "hour-24",
    "overlap": "overlapping-intervals",
    "utc-offset": "utc-offset",
    "rrs-value1": "silent-rrs-value1-ignored",
    "curve-style": "curve-style-points",
    "mw-precision": "mw-precision",
}


@dataclass(frozen=True)
class Mutant:
    family: str  # schema | rule
    kind: str
    how: str
    xml: str


@dataclass(frozen=True)
class Outcome:
    mutant: Mutant
    by_schema: bool
    by_rules: bool
    rules: tuple[str, ...] = ()

    @property
    def caught(self) -> bool:
        return self.by_schema or self.by_rules


def _tostring(root: ET.Element) -> str:
    return ET.tostring(root, encoding="unicode")


def _first(root: ET.Element, name: str) -> ET.Element | None:
    return next((e for e in root.iter() if local(e.tag) == name), None)


def _parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {c: p for p in root.iter() for c in p}


def _nth(root: ET.Element, target: ET.Element) -> int:
    return list(root.iter()).index(target)


def _clone_at(base: ET.Element, el: ET.Element) -> tuple[ET.Element, ET.Element]:
    """A deep copy of ``base`` and the copy of ``el`` inside it."""
    tree = copy.deepcopy(base)
    return tree, list(tree.iter())[_nth(base, el)]


# --- schema mutants -----------------------------------------------------------


def _leaf_types(base: ET.Element) -> dict[ET.Element, set[str]]:
    """Each leaf's XSD type names (with base types) and its own name, for matching facets."""
    out: dict[ET.Element, set[str]] = {}
    index = schema._index(str(sources.xsd_dir()))
    for doc in schema.documents(schema.payload_root(base)):
        hit = index.get(doc.tag)
        if hit is None:
            continue
        for el, path in _leaves(doc):
            out[el] = schema.type_names(hit[1], path) | {local(el.tag)}
    return out


def schema_mutants(xml: str, rules: list[Rule]) -> list[Mutant]:
    base = ET.fromstring(xml)
    out: list[Mutant] = []
    types = _leaf_types(base)
    for r in rules:
        if r.kind == "required":
            host = next(
                (
                    h
                    for h in base.iter()
                    if local(h.tag) == r.owner and h.find(q(EWS, r.target)) is not None
                ),
                None,
            )
            if host is not None:
                tree, h2 = _clone_at(base, host)
                h2.remove(h2.find(q(EWS, r.target)))
                out.append(
                    Mutant(
                        "schema", r.kind, f"deleted <{r.target}> from <{r.owner}>", _tostring(tree)
                    )
                )
        elif r.kind == "order":
            seq = r.constraint.split(" -> ")
            for host in (h for h in base.iter() if local(h.tag) == r.owner):
                names = [local(c.tag) for c in host]
                if seq[0] in names and seq[1] in names:
                    tree, h2 = _clone_at(base, host)
                    kids = list(h2)
                    i, j = names.index(seq[0]), names.index(seq[1])
                    kids[i], kids[j] = kids[j], kids[i]
                    for c in list(h2):
                        h2.remove(c)
                    h2.extend(kids)
                    out.append(
                        Mutant(
                            "schema", r.kind, f"swapped <{seq[0]}> and <{seq[1]}>", _tostring(tree)
                        )
                    )
                    break
        elif (
            r.kind == "cardinality"
            and r.constraint.startswith("maxOccurs=")
            and r.constraint[10:].isdigit()
        ):
            cap = int(r.constraint[10:])
            host = next(
                (
                    h
                    for h in base.iter()
                    if local(h.tag) == r.owner and h.find(q(EWS, r.target)) is not None
                ),
                None,
            )
            if host is not None:
                tree, h2 = _clone_at(base, host)
                kid = h2.find(q(EWS, r.target))
                for _ in range(cap + 1 - len(h2.findall(q(EWS, r.target)))):
                    h2.insert(list(h2).index(kid) + 1, copy.deepcopy(kid))
                out.append(
                    Mutant(
                        "schema",
                        r.kind,
                        f"{cap + 1} <{r.target}> in <{r.owner}> (cap {cap})",
                        _tostring(tree),
                    )
                )
        elif r.kind == "enumeration":
            el = next(
                (
                    e
                    for e in base.iter()
                    if r.owner in types.get(e, ()) and (e.text or "").strip() == r.constraint
                ),
                None,
            )
            if el is not None:
                tree, e2 = _clone_at(base, el)
                e2.text = "NOT-A-VALID-VALUE"
                out.append(
                    Mutant(
                        "schema",
                        r.kind,
                        f"<{local(el.tag)}> outside its enumeration",
                        _tostring(tree),
                    )
                )
        elif r.kind == "pattern":
            for el in base.iter():
                text = (el.text or "").strip()
                if len(el) or not text or r.owner not in types.get(el, ()):
                    continue
                try:
                    if re.fullmatch(r.constraint, text) is None:
                        continue
                except re.error:
                    continue
                tree, e2 = _clone_at(base, el)
                e2.text = "!!"
                out.append(
                    Mutant(
                        "schema", r.kind, f"<{local(el.tag)}> breaks its pattern", _tostring(tree)
                    )
                )
                break
    return _dedupe(out)


# --- rule mutants -------------------------------------------------------------


def _shift_minutes(text: str, minutes: int) -> str | None:
    dt = constraints.parse_datetime(text)
    return (dt + timedelta(minutes=minutes)).isoformat() if dt else None


def rule_mutants(xml: str) -> list[Mutant]:
    base = ET.fromstring(xml)
    out: list[Mutant] = []
    root = schema.payload_root(base)

    for bidset in root.iter(q(EWS, "BidSet")):
        for payload in bidset:
            tag = local(payload.tag)
            if requirements.page_for(tag) is None:
                continue
            present = requirements.paths_in(payload)
            for path in requirements.required(tag):
                if path not in present:
                    continue
                tree, p2 = _clone_at(base, payload)
                parents = _parent_map(p2)
                for el in [e for e in p2.iter() if _path(e, p2, parents) == path]:
                    parents[el].remove(el)
                out.append(
                    Mutant(
                        "rule",
                        "required-field",
                        f"deleted {tag}/{path} (marked required)",
                        _tostring(tree),
                    )
                )
            rules = constraints.for_tag(tag)
            parents = _parent_map(payload)
            for el in payload.iter():
                if len(el) or not (el.text or "").strip() or el is payload:
                    continue
                rule = rules.get(_path(el, payload, parents))
                if rule is None or rule.advisory:
                    continue
                bad = _violate(rule, el.text.strip())
                if bad is None:
                    continue
                tree, e2 = _clone_at(base, el)
                e2.text = bad
                out.append(
                    Mutant("rule", rule.kind, f"{tag}/{rule.field} = {bad}", _tostring(tree))
                )
        trade = bidset.find(q(EWS, "tradingDate"))
        if trade is not None and (trade.text or "").strip():
            tree, t2 = _clone_at(base, trade)
            y, m, d = map(int, trade.text.strip().split("-"))
            t2.text = f"{y:04d}-{m:02d}-{d + 1:02d}" if d < 28 else f"{y:04d}-{m:02d}-01"
            out.append(Mutant("rule", "trade-date", f"tradingDate = {t2.text}", _tostring(tree)))

    for name in checker.TIME_FIELDS:
        el = next((e for e in root.iter() if local(e.tag) == name and (e.text or "").strip()), None)
        if el is not None and "T" in el.text:
            tree, e2 = _clone_at(base, el)
            date_part, rest = el.text.strip().split("T", 1)
            offset = re.search(r"(Z|[+\-]\d\d:\d\d)$", rest)
            e2.text = f"{date_part}T24:00:00{offset.group(1) if offset else ''}"
            out.append(Mutant("rule", "hour-24", f"{name} = {e2.text}", _tostring(tree)))

    for parent in root.iter():
        timed = [k for k in parent if k.find(q(EWS, "startTime")) is not None]
        names = [local(k.tag) for k in timed]
        for name in sorted(set(names)):
            group = [k for k in timed if local(k.tag) == name]
            if name in checker.BIDSET_PAYLOADS or len(group) < 2:
                continue
            first_start = group[0].find(q(EWS, "startTime")).text
            shifted = _shift_minutes(first_start, 30)
            if shifted:
                tree, k2 = _clone_at(base, group[1])
                k2.find(q(EWS, "startTime")).text = shifted
                out.append(
                    Mutant("rule", "overlap", f"second {name} starts {shifted}", _tostring(tree))
                )

    for bidset in root.iter(q(EWS, "BidSet")):
        for payload in bidset:
            start = payload.find(q(EWS, "startTime"))
            dt = constraints.parse_datetime(start.text or "") if start is not None else None
            if dt is None or dt.tzinfo is None:
                continue
            # Same wall-clock time; +01:00 is never UTC or Central time.
            tree, s2 = _clone_at(base, start)
            s2.text = dt.replace(tzinfo=timezone(timedelta(hours=1))).isoformat()
            how = f"{local(payload.tag)} startTime = {s2.text}"
            out.append(Mutant("rule", "utc-offset", how, _tostring(tree)))
            break

    for saa in root.iter(q(EWS, "SelfArrangedAS")):
        if (saa.findtext(q(EWS, "asType")) or "").strip().upper() != "RRS":
            continue
        v1 = saa.find(f".//{q(EWS, 'value1')}")
        if v1 is not None:
            tree, v2 = _clone_at(base, v1)
            v2.text = "5.0"
            out.append(
                Mutant(
                    "rule", "rrs-value1", "RRS SelfArrangedAS with value1 = 5.0", _tostring(tree)
                )
            )

    for curve in root.iter():
        style = (curve.findtext(q(EWS, "curveStyle")) or "").strip()
        points = curve.findall(q(EWS, "CurveData"))
        if style in ("FIXED", "VARIABLE") and len(points) == 1:
            tree, c2 = _clone_at(base, curve)
            p2 = c2.findall(q(EWS, "CurveData"))[0]
            c2.insert(list(c2).index(p2) + 1, copy.deepcopy(p2))
            out.append(
                Mutant("rule", "curve-style", f"{style} curve with 2 points", _tostring(tree))
            )
            break

    for doc in schema.documents(root):
        hit = schema._index(str(sources.xsd_dir())).get(doc.tag)
        if hit is None:
            continue
        for el, path in _leaves(doc):
            if "MWSingleDecimal" in schema.type_names(hit[1], path):
                tree, e2 = _clone_at(base, el)
                e2.text = f"{float(el.text):.1f}5"
                out.append(
                    Mutant("rule", "mw-precision", f"{local(el.tag)} = {e2.text}", _tostring(tree))
                )
                break
    return _dedupe(out)


def _path(el: ET.Element, top: ET.Element, parents: dict) -> str:
    parts = []
    while el is not top and el in parents:
        parts.append(local(el.tag))
        el = parents[el]
    return "/".join(reversed(parts))


def _leaves(doc: ET.Element):
    def walk(el, path):
        path = f"{path}/{el.tag}"
        if len(el) == 0 and (el.text or "").strip():
            yield el, path
        for c in el:
            yield from walk(c, path)

    yield from walk(doc, "")


def _violate(rule: constraints.Constraint, value: str) -> str | None:
    if rule.kind == constraints.HOUR_BOUNDARY:
        return _shift_minutes(value, 7)
    if rule.kind == constraints.NUMERIC:
        if rule.lo is not None:
            return f"{rule.lo - 1:g}"
        if rule.hi is not None:
            return f"{rule.hi + 1:g}"
    if rule.kind == constraints.ENUM and value in rule.values:
        return "NOT-A-VALID-VALUE"
    return None


def _dedupe(mutants: list[Mutant]) -> list[Mutant]:
    seen, out = set(), []
    for m in mutants:
        if m.xml not in seen:
            seen.add(m.xml)
            out.append(m)
    return out


def run(xml: str, rules: list[Rule]) -> list[Outcome]:
    """Every mutant, with whether the XSD and the checker's own rules each objected.

    A schema mutant counts as caught by the rules if any new rule fires; a rule
    mutant only if its target rule does.
    """
    baseline = checker.check(xml).by_rule() - {"schema"}
    out = []
    for m in schema_mutants(xml, rules) + rule_mutants(xml):
        rep = checker.check(m.xml)
        ours = tuple(sorted(rep.by_rule() - {"schema", "schema-unverified"} - baseline))
        by_rules = TARGET[m.kind] in ours if m.family == "rule" else bool(ours)
        out.append(Outcome(m, rep.schema == schema.INVALID, by_rules, ours))
    return out


def summary(outcomes: list[Outcome]) -> dict:
    out = {}
    for family in ("schema", "rule"):
        fam = [o for o in outcomes if o.mutant.family == family]
        kinds: dict[str, dict[str, int]] = {}
        for o in fam:
            k = kinds.setdefault(o.mutant.kind, {"mutants": 0, "caught_by_rules": 0})
            k["mutants"] += 1
            k["caught_by_rules"] += o.by_rules
        out[family] = {
            "mutants": len(fam),
            "caught_by_xsd": sum(o.by_schema for o in fam),
            "caught_by_rules": sum(o.by_rules for o in fam),
            "caught_by_rules_only": sum(o.by_rules and not o.by_schema for o in fam),
            "survived": [o.mutant.how for o in fam if not o.caught],
            "by_kind": kinds,
        }
    return out
