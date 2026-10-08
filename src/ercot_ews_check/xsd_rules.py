"""Every constraint in ERCOT's XSDs, extracted as data with a file:line citation.

Useful as a reference ("what can make this element fail?"), as a list of rules to
mutate, and as a diff between schema releases.
"""

from __future__ import annotations

import json
import xml.parsers.expat
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ercot_ews_check import sources

XS = "{http://www.w3.org/2001/XMLSchema}"
_GROUPS = (XS + "sequence", XS + "all", XS + "choice")


@dataclass(frozen=True)
class Rule:
    id: str
    kind: str  # required | order | enumeration | cardinality | pattern | length | bound | fixed
    owner: str  # the complexType, simpleType or element that carries it
    target: str
    constraint: str
    statement: str
    file: str
    line: int
    tags: tuple[str, ...] = field(default=())

    @property
    def cites(self) -> str:
        return f"{self.file}:{self.line}"


class _Node:
    __slots__ = ("attrs", "kids", "line", "parent", "tag")

    def __init__(self, tag, attrs, line, parent):
        self.tag, self.attrs, self.line, self.parent, self.kids = tag, attrs, line, parent, []


def _parse(data: bytes) -> _Node:
    """Parse with expat so every node keeps its line number."""
    root = _Node("#root", {}, 0, None)
    stack = [root]
    parser = xml.parsers.expat.ParserCreate(namespace_separator="}")

    def start(name, attrs):
        node = _Node(
            "{" + name if "}" in name else name, attrs, parser.CurrentLineNumber, stack[-1]
        )
        stack[-1].kids.append(node)
        stack.append(node)

    parser.StartElementHandler = start
    parser.EndElementHandler = lambda _name: stack.pop()
    parser.Parse(data, True)
    return root


def _walk(node: _Node):
    for kid in node.kids:
        yield kid
        yield from _walk(kid)


def _owner(node: _Node) -> str:
    cur = node.parent
    named = (XS + "complexType", XS + "simpleType", XS + "element", XS + "attributeGroup")
    while cur is not None:
        if cur.attrs.get("name") and cur.tag in named:
            return cur.attrs["name"]
        cur = cur.parent
    return "(anonymous)"


def _children(node: _Node) -> list[_Node]:
    return [k for k in node.kids if k.tag == XS + "element" and k.attrs.get("name")]


def extract(xsd_dir: Path | None = None) -> list[Rule]:
    rules: list[Rule] = []
    for path in sorted(Path(xsd_dir or sources.xsd_dir()).glob("*.xsd")):
        root = _parse(path.read_bytes())
        fname = path.name

        def add(kind, owner, target, constraint, statement, line, tags=(), fname=fname):
            rules.append(
                Rule(
                    f"{fname}:{line}:{owner}:{target}:{kind}",
                    kind,
                    owner,
                    target,
                    str(constraint),
                    statement,
                    fname,
                    line,
                    tags,
                )
            )

        for el in _walk(root):
            tag, a, owner = el.tag, el.attrs, _owner(el)
            if tag == XS + "element" and a.get("name"):
                name, mino, maxo = a["name"], a.get("minOccurs"), a.get("maxOccurs")
                if mino is None and el.parent is not None and el.parent.tag in _GROUPS:
                    add(
                        "required",
                        owner,
                        name,
                        "minOccurs defaults to 1",
                        f"{name} is required inside {owner}",
                        el.line,
                    )
                if maxo and maxo != "1":
                    stmt = (
                        f"{owner} accepts any number of {name}"
                        if maxo == "unbounded"
                        else f"{owner} accepts at most {maxo} {name}"
                    )
                    tags = () if maxo == "unbounded" else ("cap",)
                    add("cardinality", owner, name, f"maxOccurs={maxo}", stmt, el.line, tags)
                if a.get("fixed") is not None:
                    add("fixed", owner, name, a["fixed"], f'{name} must be "{a["fixed"]}"', el.line)
            elif tag == XS + "sequence":
                kids = [k.attrs["name"] for k in _children(el)]
                if len(kids) > 1:
                    add(
                        "order",
                        owner,
                        ", ".join(kids),
                        " -> ".join(kids),
                        f"{owner} is a sequence: its children must appear in this order",
                        el.line,
                    )
            elif tag == XS + "choice":
                kids = _children(el)
                # A choice of one branch states nothing; skip it.
                if len(kids) > 1 and a.get("maxOccurs", "1") == "1":
                    optional = a.get("minOccurs") == "0" or all(
                        k.attrs.get("minOccurs") == "0" for k in kids
                    )
                    how = "at most one" if optional else "exactly one"
                    names = [k.attrs["name"] for k in kids]
                    add(
                        "cardinality",
                        owner,
                        " | ".join(names[:6]),
                        "xs:choice maxOccurs=1" + (" minOccurs=0" if optional else ""),
                        f"{owner} carries {how} of its {len(names)} branches, not a mixture",
                        el.line,
                        ("choice",),
                    )
            elif tag == XS + "enumeration":
                add(
                    "enumeration",
                    owner,
                    owner,
                    a.get("value"),
                    f'{owner} accepts only its listed values; "{a.get("value")}" is one',
                    el.line,
                )
            elif tag == XS + "pattern":
                add(
                    "pattern",
                    owner,
                    owner,
                    a.get("value"),
                    f"{owner} must match {a.get('value')}",
                    el.line,
                )
            elif tag in (XS + "minLength", XS + "maxLength", XS + "length"):
                facet = tag[len(XS) :]
                add(
                    "length",
                    owner,
                    owner,
                    f"{facet}={a.get('value')}",
                    f"{owner} has {facet} {a.get('value')}",
                    el.line,
                )
            elif tag in (
                XS + "minInclusive",
                XS + "maxInclusive",
                XS + "minExclusive",
                XS + "maxExclusive",
            ):
                facet = tag[len(XS) :]
                add(
                    "bound",
                    owner,
                    owner,
                    f"{facet}={a.get('value')}",
                    f"{owner} is bounded: {facet} {a.get('value')}",
                    el.line,
                )
    return rules


def summarise(rules: list[Rule]) -> dict:
    by_kind: dict[str, int] = {}
    by_file: dict[str, int] = {}
    for r in rules:
        by_kind[r.kind] = by_kind.get(r.kind, 0) + 1
        by_file[r.file] = by_file.get(r.file, 0) + 1
    return {
        "total": len(rules),
        "by_kind": dict(sorted(by_kind.items(), key=lambda kv: -kv[1])),
        "by_file": dict(sorted(by_file.items(), key=lambda kv: -kv[1])),
    }


def to_json(rules: list[Rule]) -> str:
    rows = [asdict(r) for r in sorted(rules, key=lambda r: (r.file, r.line, r.id))]
    return json.dumps({"summary": summarise(rules), "rules": rows}, indent=1)


def diff(old: list[dict], new: list[dict]) -> dict:
    """Rules added, removed or changed between two extractions (e.g. two schema releases)."""
    o = {r["id"]: r for r in old}
    n = {r["id"]: r for r in new}
    changed = [
        {"id": k, "was": o[k]["constraint"], "now": n[k]["constraint"]}
        for k in sorted(o.keys() & n.keys())
        if o[k]["constraint"] != n[k]["constraint"]
    ]
    return {
        "added": sorted(n.keys() - o.keys()),
        "removed": sorted(o.keys() - n.keys()),
        "changed": changed,
    }
