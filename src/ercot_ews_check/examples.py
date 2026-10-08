"""ERCOT's own XML samples from the EWS developer portal, validated against ERCOT's XSDs.

Samples are the ``<pre><code>`` blocks on pages under ``applications/ews/``. A
sample is checked only when it is a complete document: it parses, and its root
(after unwrapping a SOAP envelope) is a top-level element of an EWS schema in
that schema's namespace. Fragments, placeholder text and samples that elide rows
with "..." are counted, not checked.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
from collections import Counter
from dataclasses import dataclass
from functools import lru_cache

from ercot_ews_check import schema, sources

EWS_PREFIX = "applications/ews/"
_CODE = re.compile(r"<pre><code[^>]*>(.*?)</code></pre>", re.S)

NOT_XML = "not-xml"
FRAGMENT = "fragment"
ABBREVIATED = "abbreviated"  # rows elided with "..."
VALID = schema.VALID
INVALID = schema.INVALID


@dataclass(frozen=True)
class Sample:
    page: str  # portal location of the first page that shows it
    root: str  # local name of the document root, after unwrapping SOAP
    text: str
    state: str  # valid | invalid | abbreviated | fragment | not-xml
    verdict: schema.Verdict | None = None

    @property
    def url(self) -> str:
        return sources.portal_url(self.page)


def _elided(text: str | None) -> bool:
    return (text or "").strip() in ("...", "…")


def _blocks(docs) -> dict[str, str]:
    """Distinct code blocks -> the first page they appear on."""
    seen: dict[str, str] = {}
    for d in docs:
        if not d["location"].startswith(EWS_PREFIX):
            continue
        for raw in _CODE.findall(d["text"]):
            text = html.unescape(raw).strip()
            if text.startswith("<"):
                seen.setdefault(text, d["location"])
    return seen


@lru_cache(maxsize=1)
def samples() -> tuple[Sample, ...]:
    index = schema._index(str(sources.xsd_dir()))
    out = []
    for text, page in _blocks(sources.portal_docs()).items():
        try:
            root = schema.payload_root(ET.fromstring(text))
        except ET.ParseError:
            out.append(Sample(page, "", text, NOT_XML))
            continue
        name = root.tag.rsplit("}", 1)[-1]
        if root.tag not in index:
            out.append(Sample(page, name, text, FRAGMENT))
            continue
        if any(_elided(el.tail) or (len(el) and _elided(el.text)) for el in root.iter()):
            out.append(Sample(page, name, text, ABBREVIATED))
            continue
        verdict = schema.validate(text)
        out.append(Sample(page, name, text, verdict.state, verdict))
    return tuple(out)


def counts() -> dict[str, int]:
    c = Counter(s.state for s in samples())
    return {
        "samples": len(samples()),
        "complete": c[VALID] + c[INVALID],
        "valid": c[VALID],
        "invalid": c[INVALID],
        "abbreviated": c[ABBREVIATED],
        "fragments": c[FRAGMENT],
        "not_xml": c[NOT_XML],
    }


def invalid() -> list[Sample]:
    return [s for s in samples() if s.state == INVALID]


def api_specs_examples() -> dict[str, schema.Verdict]:
    """The example files in ercot/api-specs ews/examples, each validated."""
    return {
        p.name: schema.validate(p.read_bytes())
        for p in sorted(sources.api_specs_examples_dir().glob("*.xml"))
    }


@lru_cache(maxsize=1)
def create_omissions() -> dict[tuple[str, str], str]:
    """(payload, path) that a required-field check would flag in ERCOT's own valid create
    samples, mapped to the page showing the sample."""
    from ercot_ews_check import requirements
    from ercot_ews_check.namespaces import EWS, MESSAGE, q

    out: dict[tuple[str, str], str] = {}
    for s in samples():
        if s.state != VALID:
            continue
        root = schema.payload_root(ET.fromstring(s.text))
        in_message = root.tag == q(MESSAGE, "RequestMessage")
        if in_message:
            verb = root.findtext(f"{q(MESSAGE, 'Header')}/{q(MESSAGE, 'Verb')}") or ""
            if verb.strip() != "create":
                continue
        elif root.tag != q(EWS, "BidSet"):
            continue
        for bidset in root.iter(q(EWS, "BidSet")):
            for payload in bidset:
                tag = payload.tag.rsplit("}", 1)[-1]
                if not requirements.page_for(tag):
                    continue
                if not in_message and payload.find(q(EWS, "status")) is not None:
                    continue
                for path in requirements.missing(tag, requirements.paths_in(payload)):
                    out.setdefault((tag, path), s.page)
    return out
