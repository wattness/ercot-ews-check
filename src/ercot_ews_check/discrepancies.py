"""The catalogue of known discrepancies in ERCOT's EWS documentation and schemas.

Entries are YAML files in ``discrepancies/``, one per discrepancy. Each carries
probes: a phrase that must still be on ERCOT's page and a pattern that must still
be in the schema. When ERCOT corrects a page, the probe stops matching and
:func:`verify` reports it.
"""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

from ercot_ews_check import sources

LOOKUP_KEYS = ("products", "messages", "elements", "values", "endpoints")
KINDS = {
    "cardinality": "the schema limits how many, or which combination of, elements may appear",
    "default-value": "the documented default differs from the schema's",
    "documentation": "the documentation describes a convention it does not follow",
    "element-name": "the documentation spells an element name the schema does not declare",
    "element-order": "the documentation orders elements differently from the schema sequence",
    "element-path": "the documentation places an element under the wrong parent",
    "enumeration-value": "the documentation uses a value the schema enumeration does not allow",
    "file-name": "the documentation names a file that is not published",
    "namespace": "an example puts elements in a namespace the schema does not expect",
    "required-field": "the documentation and the schema disagree on whether a field is required",
    "typo": "a misspelling in text that is not validated",
    "value-bound": "the documentation states a bound that ERCOT's rules or schema contradict",
    "value-format": "an example writes a value in a form the schema type does not accept",
    "withdrawn": "the documentation still describes something ERCOT has withdrawn",
}
RESOLUTIONS = {
    "schema-wins": "Follow the schema; the documentation is wrong.",
    "prose-wins": "The schema accepts it, but ERCOT's stated rule does not; follow the prose.",
    "neither": "Nothing validates it; pick one form and be consistent.",
    "prose-stale": "The page describes something ERCOT has removed.",
}


@dataclass(frozen=True)
class Entry:
    id: str
    slug: str
    title: str
    kind: str
    resolution: str
    status: str
    ercot_says: dict
    schema_says: dict
    do: str
    protocols_say: dict = field(default_factory=dict)
    lookup: dict = field(default_factory=dict)
    reproducer: dict | None = None
    probes: dict = field(default_factory=dict)
    reported: tuple[str, ...] = ()
    notes: str = ""
    path: Path | None = None

    def terms(self) -> set[str]:
        return {t for k in LOOKUP_KEYS for t in self.lookup.get(k, ())}

    def matches(self, query: str) -> bool:
        """Case-insensitive match on ID, slug, lookup terms, title and page."""
        q = query.lower()
        if q in (self.id.lower(), self.slug.lower()):
            return True
        if any(q == t.lower() for t in self.terms()):
            return True
        haystack = " ".join((self.title, self.ercot_says.get("page", ""), self.slug)).lower()
        return q in haystack

    @property
    def url(self) -> str:
        return self.ercot_says.get("url", "")


def _load(path: Path) -> Entry:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    return Entry(
        id=raw["id"],
        slug=raw["slug"],
        title=raw["title"],
        kind=raw["kind"],
        resolution=raw["resolution"],
        status=raw.get("status", "open"),
        ercot_says=raw.get("ercot_says") or {},
        schema_says=raw.get("schema_says") or {},
        do=raw.get("do", ""),
        protocols_say=raw.get("protocols_say") or {},
        lookup={k: tuple(v) for k, v in (raw.get("lookup") or {}).items()},
        reproducer=raw.get("reproducer"),
        probes=raw.get("probes") or {},
        reported=tuple(raw.get("reported") or ()),
        notes=raw.get("notes", ""),
        path=path,
    )


@lru_cache(maxsize=1)
def entries() -> tuple[Entry, ...]:
    return tuple(_load(p) for p in sorted(sources.discrepancies_dir().glob("D*.yaml")))


def get(entry_id: str) -> Entry | None:
    return next((e for e in entries() if entry_id.lower() in (e.id.lower(), e.slug)), None)


def search(query: str) -> list[Entry]:
    return [e for e in entries() if e.matches(query)]


def related(kinds, *, elements=(), values=()) -> tuple[str, ...]:
    """IDs of entries of one of ``kinds`` whose lookup lists one of ``elements`` or ``values``."""
    elements, values = set(elements), set(values)
    hits = []
    for e in entries():
        lists = set(e.lookup.get("elements", ())), set(e.lookup.get("values", ()))
        if e.kind in kinds and (elements & lists[0] or values & lists[1]):
            hits.append(e.id)
    return tuple(hits)


# --- probes -----------------------------------------------------------------

_SMART = str.maketrans({"‘": "'", "’": "'", "“": '"', "”": '"', "–": "-", "—": "-"})


def normalize(text: str) -> str:
    """Straight quotes and dashes, single spaces."""
    return re.sub(r"\s+", " ", text.translate(_SMART)).strip()


def flatten(text: str) -> str:
    """Portal HTML as a reader sees it: tags removed, entities decoded, spaces collapsed.

    Code samples survive as text because the portal escapes them.
    """
    return normalize(html.unescape(re.sub(r"<[^>]+>", " ", text)))


_last: list = [None, ()]  # the docs object last flattened, and the result


def _flat(docs) -> tuple[tuple[str, str], ...]:
    if _last[0] is not docs:
        _last[:] = [docs, tuple((d["location"], flatten(d["text"])) for d in docs)]
    return _last[1]


@lru_cache(maxsize=1)
def _vendored_flat() -> tuple[tuple[str, str], ...]:
    return _flat(sources.portal_docs())


@dataclass(frozen=True)
class ProbeResult:
    entry: str
    probe: str
    ok: bool
    detail: str = ""


def run_probes(entry: Entry, *, docs=None, xsd_dir: Path | None = None, files_dir=None):
    """Check each probe of ``entry`` against the given sources (vendored by default).

    ``docs`` is a portal search index's ``docs`` list.
    """
    flat = _vendored_flat() if docs is None else _flat(docs)
    xsd_dir = Path(xsd_dir or sources.xsd_dir())
    files_dir = Path(files_dir or sources.vendor_dir() / "ercot")
    results = []
    portal = entry.probes.get("portal")
    if portal:
        page, text = portal["page"], normalize(portal["text"])
        hit = any(page in loc and text in body for loc, body in flat)
        results.append(
            ProbeResult(entry.id, "portal", hit, "" if hit else f"{text!r} not on {page}")
        )
    schema = entry.probes.get("schema")
    if schema:
        path = xsd_dir / schema["file"]
        text = path.read_text(encoding="utf-8", errors="replace") if path.is_file() else ""
        hit = re.search(schema["pattern"], text)
        results.append(
            ProbeResult(entry.id, "schema", bool(hit), "" if hit else f"{schema['file']} changed")
        )
    for key in ("diagram", "file"):
        probe = entry.probes.get(key)
        if probe:
            path = files_dir / probe["path"]
            got = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""
            ok = got == probe["sha256"]
            results.append(ProbeResult(entry.id, key, ok, "" if ok else f"{probe['path']} changed"))
    return results


def verify(**kwargs) -> list[ProbeResult]:
    """Run every open entry's probes; failures mean ERCOT changed something."""
    return [r for e in entries() if e.status == "open" for r in run_probes(e, **kwargs)]


# --- Markdown index -----------------------------------------------------------

_LOOKUP_TITLES = {
    "products": "By product",
    "messages": "By message",
    "elements": "By element",
    "endpoints": "By service",
}


def _cell(text: str) -> str:
    text = " ".join(str(text).split())
    return text.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def render_index(items: tuple[Entry, ...] | None = None) -> str:
    """The catalogue as one Markdown page."""
    items = entries() if items is None else items
    out = [
        "# Known discrepancies in ERCOT's EWS documentation and schemas",
        "",
        "Built from `discrepancies/*.yaml` by `scripts/build_index.py`. "
        "Edit the YAML, not this file.",
        "Each entry's probes are re-checked by `ercot-ews-check verify`.",
        "",
        f"{len(items)} entries. Resolutions:",
        "",
    ]
    out += [f"- `{k}`: {v}" for k, v in RESOLUTIONS.items()]
    out += ["", "| ID | Discrepancy | Kind | Resolution | Status |", "|---|---|---|---|---|"]
    for e in items:
        out.append(
            f"| [{e.id}](#{e.id.lower()}) | {_cell(e.title)} | {e.kind} | {e.resolution} | "
            f"{e.status} |"
        )
    for key, heading in _LOOKUP_TITLES.items():
        index: dict[str, list[str]] = {}
        for e in items:
            for term in e.lookup.get(key, ()):
                index.setdefault(term, []).append(e.id)
        if not index:
            continue
        out += ["", f"## {heading}", ""]
        for term in sorted(index, key=str.lower):
            refs = ", ".join(f"[{i}](#{i.lower()})" for i in index[term])
            out.append(f"- `{term}`: {refs}")
    out += ["", "## Entries"]
    for e in items:
        out += ["", f"### {e.id}", "", f"**{_cell(e.title)}**", ""]
        out.append(f"- Kind: {e.kind} ({KINDS.get(e.kind, '')}). Resolution: {e.resolution}.")
        says = e.ercot_says
        where = "; ".join(x for x in (says.get("page"), says.get("location")) if x)
        if says.get("quote"):
            out.append(f'- ERCOT says ({where}): "{_cell(says["quote"])}" <{says.get("url", "")}>')
        else:
            out.append(f"- ERCOT's source ({where}): <{says.get('url', '')}>")
        if says.get("observed"):
            out.append(f"- Observed: {_cell(says['observed'])}")
        schema = e.schema_says
        cite = f"`{schema['file']}:{schema['line']}`" if schema.get("file") else "no schema rule"
        out.append(f"- Schema ({cite}): {_cell(schema.get('rule', ''))}")
        if e.protocols_say:
            p = e.protocols_say
            out.append(
                f'- Protocols ({_cell(p.get("section", ""))}): "{_cell(p.get("quote", ""))}" '
                f"<{p.get('url', '')}>"
            )
        out.append(f"- Do: {_cell(e.do)}")
        if e.reproducer:
            out.append(f"- Reproduce: `ercot-ews-check reproduce {e.id}`")
        if e.notes:
            out.append(f"- Note: {_cell(e.notes)}")
        for url in e.reported:
            out.append(f"- Reported upstream: <{url}>")
    return "\n".join(out) + "\n"
