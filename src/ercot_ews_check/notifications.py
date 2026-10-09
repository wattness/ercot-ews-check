"""The notifications ERCOT documents pushing to a Market Participant's listener.

Read from the vendored files, not transcribed: the list on the portal's Notifications
page, the message table on each notification's page (Header/Verb, Header/Noun and the
Payload row), the verbs ERCOT's prose and XML samples give these messages, and where
ERCOT's schemas declare each payload. ``scripts/build_notifications.py`` writes the
result into ``docs/notifications.md``.
"""

from __future__ import annotations

import html
import re
import xml.etree.ElementTree as ET
import xml.parsers.expat
from collections import Counter
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

from ercot_ews_check import checker, discrepancies, schema, sources
from ercot_ews_check.discrepancies import flatten
from ercot_ews_check.namespaces import local

EWS_PAGES = "applications/ews/"
LISTING = "applications/ews/Notifications/#message-specifications"
NOTIFICATION_PAGES = "applications/ews/Notifications%20Messages/"
REVISIONS = "applications/ews/Document%20Revisions/"

# What RTC+B changed about a listed notification, in the words of ERCOT's Document
# Revisions page; tests/test_notifications.py finds each phrase on the vendored page.
RTCB_REVISIONS: dict[str, str] = {
    "Ancillary Service Awards": "AwardedAS: Removed SASM reference",
    "Ancillary Service Obligations": (
        "ASObligation: Updated noun to ASObligationsAdvisory and ASObligationsFinal"
    ),
    "Ancillary Service Only Offer Awards": "Ancillary Service Only Offer Awards: Newly Added",
    "DAM Ancillary Service Offer Insufficiency Report": (
        "Removed DAM Ancillary Service Offer Insufficiency Report"
    ),
    "DAM Phase II Validation Results": "DAM Phase II Validation: Added ASOnlyOffer",
}

# Header/Verb values in the past tense, which ERCOT says notification messages use.
PAST_TENSE = frozenset({"canceled", "changed", "closed", "created", "deleted", "updated"})

_PARAGRAPH = re.compile(r"<p>\s*(.*?)\s*</p>", re.S)
_CODE = re.compile(r"<pre><code[^>]*>(.*?)</code></pre>", re.S)
# The search index keeps a table as bare text between paragraphs; a cell can hold a
# paragraph of its own, as the Payload cell on DAM Phase II Validation Results does.
_TABLE = re.compile(r"Message Element Value\s+(.*?)(?=<p>|<pre>|$)(?:<p>(.*?)</p>)?", re.S)
_ROW_VERB = re.compile(r"Header/Verb\s+(\S+)")
_ROW_NOUN = re.compile(r"Header/Noun\s+(.*?)\s+Header/Source")
_ROW_PAYLOAD = re.compile(r"(Payload\b.*)$", re.S)
_WITHDRAWN = re.compile(r"Info Removed with RTC\+B Implementation")
_STATEMENT = re.compile(
    r"\bverb\s*[=:]\s*'?([A-Za-z]+)'?(?:,?\s*noun\s*[=:]\s*'?([A-Za-z]+)'?)?", re.I
)
_SENTENCE = re.compile(r"(?<=[.!?])\s+")
_MESSAGE_OR_VERB = re.compile(
    r"<(?:[\w.-]+:)?(RequestMessage|ResponseMessage|Message)\b"
    r"|<(?:[\w.-]+:)?Verb>\s*([^<]*?)\s*</(?:[\w.-]+:)?Verb>"
)
_FIRST_TAG = re.compile(r"<(?![?!])(?:[\w.-]+:)?([\w.-]+)")
_NOTIFY = re.compile(r"<(?:[\w.-]+:)?Notify\b")
_NOUN = re.compile(r"<(?:[\w.-]+:)?Noun>\s*([^<]*?)\s*</(?:[\w.-]+:)?Noun>")
_XS = "http://www.w3.org/2001/XMLSchema}"
_RAW_API_SPECS = "https://raw.githubusercontent.com/ercot/api-specs/"
_BLOB_API_SPECS = "https://github.com/ercot/api-specs/blob/"
# A finding longer than this is cut to its first sentence in the samples table.
_FINDING_CHARS = 140


# --- the portal --------------------------------------------------------------------------


def _text(raw: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", raw)).split())


def _key(name: str) -> str:
    """A page name compared loosely: case, spacing and a plural "s" aside."""
    return re.sub(r"s$", "", " ".join(name.casefold().split()))


@lru_cache(maxsize=1)
def _pages() -> dict[str, tuple[str, str]]:
    """Loose name -> (portal location, title) for each page under Notifications Messages."""
    return {
        _key(d["title"]): (d["location"], d["title"])
        for d in sources.portal_docs()
        if d["location"].startswith(NOTIFICATION_PAGES) and d["location"].endswith("/")
    }


def _raw(location: str) -> str:
    """A page's HTML: its own index entry and each of its anchors' entries."""
    return " ".join(d["text"] for d in sources.portal_docs() if d["location"].startswith(location))


def listing() -> tuple[str, ...]:
    """Each paragraph of the Notifications page's Message Specifications section."""
    doc = next(d for d in sources.portal_docs() if d["location"] == LISTING)
    return tuple(_text(p) for p in _PARAGRAPH.findall(doc["text"]))


def listed() -> tuple[str, ...]:
    """The notifications the Notifications page lists: its paragraphs that name a page."""
    return tuple(p for p in listing() if _key(p) in _pages())


@dataclass(frozen=True)
class MessageTable:
    """A "Message Element / Value" table: the message a notification arrives in."""

    verb: str
    noun: str
    payload: str  # the Payload row as the page writes it

    @property
    def carried(self) -> tuple[str, str]:
        """(container, element) the Payload row names; element is "" when it names one."""
        names = re.findall(r"<\w+>|\w+", self.payload.removeprefix("Payload"))
        return (names[0] if names else "", names[1] if len(names) > 1 else "")


@dataclass(frozen=True)
class Notification:
    """A notification on the Notifications page's list, read from its own page."""

    name: str  # as the Notifications page lists it
    title: str  # the page's own title
    location: str
    tables: tuple[MessageTable, ...]
    withdrawn: str  # the page's own notice that RTC+B removed it, if it has one

    @property
    def url(self) -> str:
        return sources.portal_url(self.location)


def message_tables(raw: str) -> tuple[MessageTable, ...]:
    """Each table on a page (its HTML in the search index) that gives a Header/Verb."""
    out = []
    for body, cell in _TABLE.findall(raw):
        body = _text(body)
        verb, noun, payload = (p.search(body) for p in (_ROW_VERB, _ROW_NOUN, _ROW_PAYLOAD))
        if not verb:
            continue
        row = payload.group(1) if payload else ""
        if row.rstrip("/ ") == "Payload" and cell:
            row = f"{row} {_text(cell)}"
        out.append(MessageTable(verb.group(1), noun.group(1) if noun else "", row))
    return tuple(out)


@lru_cache(maxsize=1)
def notifications() -> tuple[Notification, ...]:
    out = []
    for name in listed():
        location, title = _pages()[_key(name)]
        raw = _raw(location)
        withdrawn = _WITHDRAWN.search(_text(raw))
        out.append(
            Notification(
                name,
                title,
                location,
                message_tables(raw),
                withdrawn.group(0) if withdrawn else "",
            )
        )
    return tuple(out)


@dataclass(frozen=True)
class Statement:
    """A sentence of ERCOT's prose that gives the verb, and perhaps the noun, of a push."""

    location: str
    verb: str
    noun: str

    @property
    def url(self) -> str:
        return sources.portal_url(self.location)


@lru_cache(maxsize=1)
def statements() -> tuple[Statement, ...]:
    """Each "verb=..." in a sentence of an EWS page that speaks of a notification or notice."""
    out = []
    for d in sources.portal_docs():
        if not d["location"].startswith(EWS_PAGES):
            continue
        for sentence in _SENTENCE.split(flatten(d["text"])):
            if re.search(r"notif|notice", sentence, re.I):
                out += [Statement(d["location"], v, n) for v, n in _STATEMENT.findall(sentence)]
    return tuple(out)


def code_blocks() -> dict[str, str]:
    """Each distinct code block on an EWS page -> the first page that shows it."""
    seen: dict[str, str] = {}
    for d in sources.portal_docs():
        if d["location"].startswith(EWS_PAGES):
            for raw in _CODE.findall(d["text"]):
                text = html.unescape(raw).strip()
                if text.startswith("<"):
                    seen.setdefault(text, d["location"])
    return seen


def header_verbs(text: str) -> list[tuple[str, str]]:
    """(message element, Header/Verb) for each message header in a sample. Read as text,
    so that a sample that is not well-formed counts too."""
    out, message = [], ""
    for m in _MESSAGE_OR_VERB.finditer(text):
        if m.group(1):
            message = m.group(1)
        elif message:
            out.append((message, m.group(2)))
    return out


@lru_cache(maxsize=1)
def sample_verbs() -> Counter:
    """(message element, Header/Verb) -> how many of ERCOT's distinct XML samples carry it,
    counting the EWS pages and the api-specs ews/examples files."""
    texts = list(code_blocks())
    texts += [
        p.read_text(encoding="utf-8", errors="replace")
        for p in sorted(sources.api_specs_examples_dir().glob("*.xml"))
    ]
    return Counter(pair for text in texts for pair in set(header_verbs(text)))


def _is_notification(text: str) -> bool:
    """A Notify, or a ResponseMessage whose first verb is in the past tense."""
    verbs = header_verbs(text)
    response = bool(verbs) and verbs[0][0] == "ResponseMessage" and verbs[0][1] in PAST_TENSE
    return bool(_NOTIFY.search(text)) or response


@dataclass(frozen=True)
class Sample:
    """One of ERCOT's XML samples of a notification or of what one carries."""

    source: str  # the page title, or the api-specs file name
    url: str
    text: str


@lru_cache(maxsize=1)
def samples() -> tuple[Sample, ...]:
    """ERCOT's distinct samples of a notification: each XML sample on a notification page;
    each Notify, or ResponseMessage with a past-tense verb, on another EWS page; and each
    api-specs ews/examples file whose root a notification table names as its payload."""
    blocks: dict[str, str] = {}
    for d in sources.portal_docs():
        if d["location"].startswith(NOTIFICATION_PAGES):
            for raw in _CODE.findall(d["text"]):
                text = html.unescape(raw).strip()
                if text.startswith("<"):
                    blocks.setdefault(text, d["location"])
    for text, location in code_blocks().items():
        if text not in blocks and _is_notification(text):
            blocks[text] = location
    out = [Sample(page_title(loc), sources.portal_url(loc), text) for text, loc in blocks.items()]
    payloads = {t.carried[0] for n in notifications() for t in n.tables}
    for entry in sources.manifest()["files"]:
        path = sources.vendor_dir() / entry["path"]
        if path.parent == sources.api_specs_examples_dir() and path.suffix == ".xml":
            text = path.read_text(encoding="utf-8", errors="replace")
            if root_name(text) in payloads:
                url = entry["url"].replace(_RAW_API_SPECS, _BLOB_API_SPECS)
                out.append(Sample(f"api-specs ews/examples/{path.name}", url, text))
    return tuple(out)


def page_title(location: str) -> str:
    """The title of the page a portal location is on."""
    base = location.split("#", 1)[0]
    doc = next((d for d in sources.portal_docs() if d["location"] == base), None)
    return doc["title"] if doc else base


def root_name(text: str) -> str:
    """The sample's document element, inside a SOAP envelope if there is one."""
    try:
        return local(schema.payload_root(schema.parse(text)).tag)
    except (ET.ParseError, schema.DoctypeError, schema.DepthError):
        m = _FIRST_TAG.search(text)
        return m.group(1) if m else ""


# --- the schemas -------------------------------------------------------------------------


@dataclass(frozen=True)
class Declaration:
    """An xs:element declaration with a name, in force or commented out."""

    file: str
    line: int
    owner: str  # "" at the top level; else the named type or element that holds it
    name: str
    type: str  # the type attribute without its prefix; "" for an anonymous type
    marker: str = ""  # an "RTC+B: ..." comment just above it, if there is one
    live: bool = True  # False when ERCOT has commented it out

    @property
    def cites(self) -> str:
        return f"{self.file}:{self.line}"


def _scan(path: Path) -> list[Declaration]:
    data = path.read_bytes()
    lines = data.decode("utf-8", errors="replace").splitlines()
    found: list[Declaration] = []
    markers: dict[int, str] = {}  # last line of an "RTC+B: ..." comment -> its text
    stack: list[tuple[str, str]] = []  # (tag, name) of each open element
    parser = xml.parsers.expat.ParserCreate(namespace_separator="}")
    named = (_XS + "complexType", _XS + "simpleType", _XS + "element")

    def owner() -> str:
        return next((name for tag, name in reversed(stack) if name and tag in named), "")

    def start(tag, attrs):
        if tag == _XS + "element" and attrs.get("name"):
            kind = attrs.get("type", "").rsplit(":", 1)[-1]
            found.append(
                Declaration(path.name, parser.CurrentLineNumber, owner(), attrs["name"], kind)
            )
        stack.append((tag, attrs.get("name", "")))

    def comment(text):
        line = parser.CurrentLineNumber
        if text.strip().startswith("RTC+B"):
            markers[line + text.count("\n")] = " ".join(text.split())
            return
        for m in re.finditer(r'<xs:element\s+name="(\w+)"(?:\s+type="(?:\w+:)?(\w+)")?', text):
            at = line + text[: m.start()].count("\n")
            found.append(
                Declaration(path.name, at, owner(), m.group(1), m.group(2) or "", live=False)
            )

    parser.StartElementHandler = start
    parser.EndElementHandler = lambda _tag: stack.pop()
    parser.CommentHandler = comment
    parser.Parse(data, True)

    def above(d: Declaration) -> int:
        """The line above the declaration, or above the comment that holds it."""
        line = d.line
        while not d.live and line > 1 and "<!--" not in lines[line - 1]:
            line -= 1
        return line - 1

    return [replace(d, marker=markers.get(above(d), "")) for d in found]


@lru_cache(maxsize=1)
def declarations() -> tuple[Declaration, ...]:
    return tuple(d for p in sorted(sources.xsd_dir().glob("*.xsd")) for d in _scan(p))


def declared(name: str, owner: str = "", *, live: bool = True) -> Declaration | None:
    """The declaration of ``name``: top-level when ``owner`` is "", else inside ``owner``."""
    want = (name, owner, live)
    return next((d for d in declarations() if (d.name, d.owner, d.live) == want), None)


def _inside(owner: str) -> list[Declaration]:
    return [d for d in declarations() if d.owner == owner]


def held(container: str, element: str) -> Declaration | None:
    """``element`` as declared inside the top-level element ``container``."""
    top = declared(container)
    return declared(element, top.type or container) if top else None


def rtcb_marked(container: str, element: str) -> list[Declaration]:
    """Declarations ERCOT marked "RTC+B" along a Payload row's path: the container (or its
    commented-out declaration), the element inside it, and the fields of the element's
    type; with no element, what the container holds and the fields of each item's type."""
    top = declared(container) or declared(container, live=False)
    if top is None:
        return []
    found = [top]
    if element and not element.startswith("<"):
        inner = held(container, element)
        found += [inner, *_inside(inner.type)] if inner else []
    else:
        items = _inside(top.type or container)
        found += items + [d for item in items if item.live for d in _inside(item.type)]
    return [d for d in found if d.marker]


# --- docs/notifications.md ---------------------------------------------------------------

START, END = "<!-- notifications:start -->", "<!-- notifications:end -->"
_SEVERITY_ORDER = {"error": 0, "silent": 1, "warning": 2}


def _cell(text: str) -> str:
    """Plain text for a Markdown table cell."""
    text = " ".join(str(text).split())
    return text.replace("|", "\\|").replace("<", "&lt;").replace(">", "&gt;")


def _code(text: str) -> str:
    """A code span for a Markdown table cell; GitHub shows its text as written."""
    text = " ".join(str(text).split()).replace("|", "\\|")
    return f"`{text}`" if text else ""


def _link(title: str, url: str) -> str:
    return f"[{_cell(title)}]({url})"


def _names(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def _carried(table: MessageTable) -> tuple[str, str]:
    """The Container and Element cells for one table."""
    container, element = table.carried
    top = declared(container)
    if top is None:
        gone = declared(container, live=False)
        where = f"commented out at `{gone.cites}`" if gone else "not declared"
        return f"{_code(container)} ({where})", ""
    if element.startswith("<"):
        return f"{_code(container)} (`{top.cites}`)", f"any of its payloads ({_cell(element)})"
    inner = held(container, element) if element else None
    shown = f"{_code(element)} (`{inner.cites}`)" if inner else _code(element)
    return f"{_code(container)} (`{top.cites}`)", shown


def _list_section() -> list[str]:
    items = notifications()
    bare = [n.name for n in items if not n.tables]
    many = [n for n in items if len(n.tables) > 1]
    out = [
        "### The list",
        "",
        f"ERCOT's [Notifications]({sources.portal_url(LISTING)}) page lists {len(items)} "
        f"notifications, each with a page of its own. {len(items) - len(bare)} of the pages give "
        "the message a notification arrives in as a table of Header/Verb, Header/Noun and "
        f"Payload; {_names(bare)} show only a sample payload."
        + "".join(f" {n.name} has {len(n.tables)} tables." for n in many),
        "",
        "Payload is the row as the page writes it. Container and Element give where ERCOT's "
        "schemas declare what that row names.",
        "",
        "| Notification | Header/Verb | Header/Noun | Payload | Container | Element |",
        "|---|---|---|---|---|---|",
    ]
    for n in items:
        name = _link(n.name, n.url)
        if n.title != n.name:
            name += f" (page title: {_cell(n.title)})"
        if not n.tables:
            out.append(f"| {name} | no table | | | | |")
        for i, t in enumerate(n.tables):
            container, element = _carried(t)
            out.append(
                f"| {name if i == 0 else ''} | {_code(t.verb)} | {_code(t.noun)} | "
                f"{_code(t.payload)} | {container} | {element} |"
            )
    return out


def _rtcb_section() -> list[str]:
    out = [
        "### What RTC+B changed",
        "",
        f"From ERCOT's [Document Revisions]({sources.portal_url(REVISIONS)}) page, the "
        'notification pages, and the comments beginning "RTC+B" in the schemas:',
        "",
    ]
    for n in notifications():
        parts = [f'the page says "{n.withdrawn}"'] if n.withdrawn else []
        if n.name in RTCB_REVISIONS:
            parts.append(f'Document Revisions: "{RTCB_REVISIONS[n.name]}"')
        marked = {d.cites: d for t in n.tables for d in rtcb_marked(*t.carried)}
        for d in marked.values():
            state = "declared" if d.live else "commented out"
            inside = f" in {d.owner}" if d.owner else ""
            parts.append(f'`{d.cites}`: {d.name}{inside}, {state} after "{d.marker}"')
        if parts:
            out.append(f"- {_link(n.name, n.url)}: " + "; ".join(parts) + ".")
    return out


def _statement_section() -> list[str]:
    out = [
        "### Pushes ERCOT's prose describes",
        "",
        "Each verb, with its noun where given, that a sentence on an EWS page gives a "
        "notification or notice:",
        "",
        "| Page | Verb | Noun |",
        "|---|---|---|",
    ]
    for s in dict.fromkeys(statements()):
        out.append(
            f"| {_link(page_title(s.location), s.url)} | {_code(s.verb)} | {_code(s.noun)} |"
        )
    return out


def _enumeration(decl: Declaration) -> dict[str, int]:
    """Value -> line of each enumeration in an element's inline simpleType."""
    lines = (sources.xsd_dir() / decl.file).read_text(encoding="utf-8").splitlines()
    out = {}
    for number in range(decl.line, len(lines) + 1):
        line = lines[number - 1]
        m = re.search(r'enumeration value="([^"]+)"', line)
        if m:
            out[m.group(1)] = number
        if re.search(r"</\w+:element>", line):
            break
    return out


def _verb_section() -> list[str]:
    verb = declared("Verb", "HeaderType")
    allowed = _enumeration(verb)
    in_tables: dict[str, list[str]] = {}
    for n in notifications():
        for t in n.tables:
            in_tables.setdefault(t.verb, []).append(n.name)
    in_prose: dict[str, list[str]] = {}
    for s in statements():
        pages = in_prose.setdefault(s.verb, [])
        if page_title(s.location) not in pages:
            pages.append(page_title(s.location))
    counted = sample_verbs()
    out = [
        "### Header/Verb",
        "",
        f"`{verb.cites}` declares Header/Verb as an enumeration of {len(allowed)} values. For "
        "each verb ERCOT gives a notification: the line that allows it, the notification pages "
        "whose table gives it, the pages whose prose gives it to a push, how many of ERCOT's "
        "XML samples carry it in a ResponseMessage header, and the catalogue entries about it.",
        "",
        "| Verb | Message.xsd | Notification tables | Prose | ResponseMessage samples | "
        "Catalogue |",
        "|---|---|---|---|---|---|",
    ]
    for v in sorted(set(in_tables) | set(in_prose), key=lambda v: (v.lower(), v)):
        pages = in_tables.get(v, [])
        unique = list(dict.fromkeys(pages))
        where = f"{len(unique)} {'page' if len(unique) == 1 else 'pages'}" if pages else ""
        if len(pages) != len(unique):
            where += f", {len(pages)} tables"
        if pages and v not in PAST_TENSE:
            where += f": {_names(unique)}"
        ids = [e.id for e in discrepancies.entries() if v in e.lookup.get("values", ())]
        out.append(
            f"| {_code(v)} | {f'line {allowed[v]}' if v in allowed else 'not allowed'} | "
            f"{_cell(where)} | {_cell('; '.join(in_prose.get(v, [])))} | "
            f"{counted.get(('ResponseMessage', v), 0)} | "
            + ", ".join(f"[{i}](discrepancies.md#{i.lower()})" for i in ids)
            + " |"
        )
    unsampled = [
        v for v in in_tables if v not in PAST_TENSE and not counted.get(("ResponseMessage", v))
    ]
    if unsampled:
        out += [
            "",
            "No XML sample of ERCOT's carries "
            + _names([_code(v) for v in unsampled]).replace(" and ", " or ")
            + " in a ResponseMessage header.",
        ]
    return out


def _catalogue_section() -> list[str]:
    out = ["### Catalogue entries", "", "Entries in the catalogue about notification pages:", ""]
    for e in discrepancies.entries():
        page = e.ercot_says.get("page", "")
        if "Notifications" in e.lookup.get("endpoints", ()) or "Notification" in page:
            out.append(f"- [{e.id}](discrepancies.md#{e.id.lower()}): {_cell(e.title)}")
    return out


def _sample_section() -> list[str]:
    rows = []
    for sample in samples():
        rep = checker.check(sample.text)
        verdict = "BLOCKED" if rep.blocked else ("OK" if not rep.findings else "OK with warnings")
        found = sorted(rep.findings, key=lambda f: _SEVERITY_ORDER.get(f.severity, 3))
        first = f"{found[0].rule}: {found[0].message}" if found else "none"
        if len(first) > _FINDING_CHARS:
            first = re.split(r"(?<=\.)\s", first, maxsplit=1)[0]
        what = _code(root_name(sample.text))
        verbs, nouns = header_verbs(sample.text), _NOUN.findall(sample.text)
        if verbs:
            header = [_code(verbs[0][1])] + [_code(noun) for noun in nouns[:1]]
            what += f" ({' '.join(header)})"
        rows.append(
            f"| {_link(sample.source, sample.url)} | {what} | "
            f"{verdict}, schema {rep.schema}, {len(rep.findings)} finding(s) | {_cell(first)} |"
        )
    return [
        "### ERCOT's samples, checked",
        "",
        f"What `ercot-ews-check check` reports on each of ERCOT's {len(rows)} distinct samples of "
        "a notification: each XML sample on a notification page; each `Notify`, or "
        "`ResponseMessage` with a past-tense verb, on another EWS page; and each file in "
        "api-specs `ews/examples` whose root a table above names as a payload.",
        "",
        "Sample is the document element, with the verb and noun of the first message header. "
        "Some samples are excerpts whose namespace prefixes are declared outside what the page "
        "shows, or that hold placeholders; for those, `not well-formed XML` describes the "
        "excerpt as the page shows it.",
        "",
        "| Page | Sample | Report | First finding |",
        "|---|---|---|---|",
        *rows,
    ]


def render() -> str:
    """The generated block of docs/notifications.md, markers included."""
    sections = (
        _list_section,
        _rtcb_section,
        _statement_section,
        _verb_section,
        _sample_section,
        _catalogue_section,
    )
    lines = [START, "<!-- Written by scripts/build_notifications.py. -->"]
    for section in sections:
        lines += ["", *section()]
    return "\n".join([*lines, END]) + "\n"


def update(text: str) -> str:
    """``text`` with the block between START and END replaced by a fresh one."""
    head, rest = text.split(START, 1)
    tail = rest.split(END, 1)[1]
    return head + render().removesuffix("\n") + tail
