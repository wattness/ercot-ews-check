import re
import subprocess
import sys

import pytest

from ercot_ews_check import notifications, sources
from ercot_ews_check.discrepancies import flatten, normalize

from helpers import ROOT

DOC = ROOT / "docs" / "notifications.md"
FORECASTS = {"Wind Generation Forecast", "Solar Generation Forecast"}


def portal_text(location: str) -> str:
    return " ".join(flatten(d["text"]) for d in sources.portal_docs() if location in d["location"])


def test_generated_block_is_current():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_notifications.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout


def test_every_name_on_the_list_has_its_own_page():
    """A notification ERCOT adds under a name no page carries fails here, not silently."""
    names = notifications.listed()
    prose = [p for p in notifications.listing() if p and p not in names]
    assert all(p.endswith(".") for p in prose), prose
    pages = [n.location for n in notifications.notifications()]
    assert len(set(pages)) == len(pages) == len(names)


def test_each_table_gives_verb_noun_and_payload():
    for n in notifications.notifications():
        for t in n.tables:
            assert t.verb and t.noun and t.carried[0], (n.name, t)


def test_each_payload_is_declared_unless_rtcb_removed_it():
    removed = set()
    for n in notifications.notifications():
        for t in n.tables:
            container, element = t.carried
            if notifications.declared(container) is None:
                assert notifications.declared(container, live=False).marker.startswith("RTC+B")
                removed.add(n.name)
            elif element and not element.startswith("<"):
                assert notifications.held(container, element), (n.name, element)
    assert removed == {n.name for n in notifications.notifications() if n.withdrawn}


@pytest.mark.parametrize("name", sorted(notifications.RTCB_REVISIONS))
def test_rtcb_changes_are_ercots_words(name):
    assert name in notifications.listed()
    assert notifications.RTCB_REVISIONS[name] in portal_text(notifications.REVISIONS)


def test_verbs_outside_the_past_tense():
    """The verbs docs/notifications.md and D045 name as outside ERCOT's convention."""
    tables = {
        (t.verb, n.name)
        for n in notifications.notifications()
        for t in n.tables
        if t.verb not in notifications.PAST_TENSE
    }
    assert tables == {("Created", "Confirmed and Unconfirmed Trades")} | {
        ("create", name) for name in FORECASTS
    }
    prose = {s.verb for s in notifications.statements() if s.verb not in notifications.PAST_TENSE}
    assert prose == {"reply"}
    assert {s.location for s in notifications.statements() if s.verb == "reply"} == {
        "applications/ews/Verbal%20Dispatch%20Instructions/#interfaces-provided"
    }


def test_no_sample_shows_the_header_of_these_notifications():
    nouns = {"UnconfirmedTrades", "ConfirmedTrades", "WindForecastData", "SolarForecastData"}
    nouns |= {"VDIs"}
    for text in notifications.code_blocks():
        if notifications.header_verbs(text):
            found = set(re.findall(r"<(?:[\w.-]+:)?Noun>\s*(\w+)", text))
            assert not found & nouns, found
    counted = notifications.sample_verbs()
    assert counted[("ResponseMessage", "Created")] == counted[("ResponseMessage", "create")] == 0


@pytest.mark.parametrize(
    "page, label",
    [
        ("Market%20Transaction%20Service/#interfaces-provided", "updated BidSet"),
        ("Resource%20Parameter%20Transaction%20Service/#interfaces", "Updated ResParametersSet"),
        ("Verbal%20Dispatch%20Instructions/#interfaces-provided", "Updated VDIs"),
    ],
)
def test_sequence_diagrams_label_pushes_updated(page, label):
    assert label in portal_text(page)


def test_cited_declarations_are_on_the_lines_cited():
    """Each "`Name` (`File:line`)" in docs/notifications.md names what is on that line."""
    cites = re.findall(r"`([\w:]+)` \(`(\w+\.(?:xsd|wsdl)):(\d+)`\)", DOC.read_text("utf-8"))
    assert cites
    for name, file, line in cites:
        path = next(sources.vendor_dir().rglob(file))
        text = path.read_text(encoding="utf-8").splitlines()[int(line) - 1]
        bare = name.rsplit(":", 1)[-1]
        assert f'"{name}"' in text or f':{bare}"' in text or f"<{name}" in text, (name, line)


def test_quotations_are_ercots_words():
    """Each quotation of three words or more is in ERCOT's vendored pages or schemas."""
    text = re.sub(r"`[^`]*`", "", DOC.read_text(encoding="utf-8"))
    quotes = [normalize(q) for q in re.findall(r'"([^"]+)"', text) if len(q.split()) >= 3]
    assert quotes
    corpus = [flatten(d["text"]) for d in sources.portal_docs()]
    corpus += [normalize(p.read_text(encoding="utf-8")) for p in sources.xsd_dir().glob("*.xsd")]
    for quote in quotes:
        assert any(quote in source for source in corpus), quote
