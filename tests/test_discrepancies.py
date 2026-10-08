import html
import re
import subprocess
import sys

import pytest
import yaml

from ercot_ews_check import checker, discrepancies, sources

from helpers import ROOT

ENTRIES = discrepancies.entries()
REQUIRED = (
    "id",
    "slug",
    "title",
    "kind",
    "resolution",
    "status",
    "ercot_says",
    "schema_says",
    "do",
)


def by_id(entry):
    return entry.id


def _spaced(text: str) -> str:
    return " ".join(text.split())


SOURCE_TEXT = [
    _spaced(html.unescape(re.sub(r"<[^>]+>", " ", d["text"]))) for d in sources.portal_docs()
]
SOURCE_TEXT += [
    _spaced(p.read_text(encoding="utf-8", errors="replace"))
    for p in (sources.vendor_dir() / "ercot" / "api-specs").rglob("*")
    if p.is_file()
]


@pytest.mark.parametrize("entry", ENTRIES, ids=by_id)
def test_quote_is_verbatim(entry):
    """Quotes are ERCOT's words (with ... for elisions); our descriptions go in `observed`."""
    says = entry.ercot_says
    assert says.get("quote") or says.get("observed")
    if not says.get("quote") or says.get("location", "").startswith("diagram"):
        return
    for piece in re.split(r"\s*\.\.\.\s*", says["quote"]):
        assert any(_spaced(piece) in text for text in SOURCE_TEXT), piece


def test_ids_are_sequential_and_match_file_names():
    assert [e.id for e in ENTRIES] == [f"D{i:03d}" for i in range(1, len(ENTRIES) + 1)]
    for e in ENTRIES:
        assert e.path.name == f"{e.id}-{e.slug}.yaml"


@pytest.mark.parametrize("entry", ENTRIES, ids=by_id)
def test_entry_shape(entry):
    raw = yaml.safe_load(entry.path.read_text(encoding="utf-8"))
    assert all(raw.get(k) for k in REQUIRED), [k for k in REQUIRED if not raw.get(k)]
    assert entry.kind in discrepancies.KINDS
    assert entry.resolution in discrepancies.RESOLUTIONS
    assert entry.status in ("open", "fixed")
    assert set(entry.lookup) <= set(discrepancies.LOOKUP_KEYS)
    assert entry.url.startswith("https://")
    assert entry.probes, "an entry needs at least one probe"
    assert entry.probes.keys() & {"portal", "diagram", "file"}, "a probe on ERCOT's side"
    for url in entry.reported:
        assert url.startswith("https://github.com/ercot/api-specs/")


@pytest.mark.parametrize("entry", ENTRIES, ids=by_id)
def test_probes_match_vendored_sources(entry):
    failed = [r.detail for r in discrepancies.run_probes(entry) if not r.ok]
    assert not failed


@pytest.mark.parametrize("entry", [e for e in ENTRIES if e.probes.get("schema")], ids=by_id)
def test_schema_citation_is_the_probe_line(entry):
    probe = entry.probes["schema"]
    text = (sources.xsd_dir() / probe["file"]).read_text(errors="replace")
    match = re.search(probe["pattern"], text)
    assert entry.schema_says["file"] == probe["file"]
    assert entry.schema_says["line"] == text[: match.start()].count("\n") + 1


@pytest.mark.parametrize("entry", [e for e in ENTRIES if e.reproducer], ids=by_id)
def test_reproducer(entry):
    bad = checker.check(entry.reproducer["invalid"])
    assert bad.blocked
    if "valid" in entry.reproducer:
        good = checker.check(entry.reproducer["valid"])
        assert good.schema == "valid" and good.findings == []


def test_probe_detects_a_change():
    entry = discrepancies.get("D020")
    docs = [
        {"location": d["location"], "text": d["text"].replace("plannedSart", "plannedStart")}
        for d in sources.portal_docs()
    ]
    results = {r.probe: r.ok for r in discrepancies.run_probes(entry, docs=docs)}
    assert results == {"portal": False, "schema": True}


def test_lookup_by_element_value_and_id():
    assert [e.id for e in discrepancies.search("yvalue")] == ["D001"]
    assert "D011" in [e.id for e in discrepancies.search("ERRORS")]
    assert discrepancies.get("d021").slug == "acknowledge-timestamp-case"
    assert discrepancies.get("acknowledge-timestamp-case").id == "D021"
    assert discrepancies.search("no-such-thing") == []


def test_verify_reports_every_open_entry():
    results = discrepancies.verify()
    assert {r.entry for r in results} == {e.id for e in ENTRIES if e.status == "open"}
    assert all(r.ok for r in results)


def test_markdown_index_is_current():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_index.py"), "--check"],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout
