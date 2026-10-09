"""docs/bidding-path.md and its diagram.

The SVGs must be well-formed, self-contained and at most 960 px wide, the dark one must differ
from the light one only in its colours, every numbered element must have a row in the sources
table, every local file the page cites must exist, and every quote from ERCOT's EWS pages must
still be on the page section it cites, in the vendored search index.
"""

import html
import re
import xml.etree.ElementTree as ET
from urllib.parse import unquote

import pytest

from ercot_ews_check.sources import portal_docs

from helpers import ROOT

DOCS = ROOT / "docs"
PAGE = (DOCS / "bidding-path.md").read_text(encoding="utf-8")
SVGS = [DOCS / "bidding-path-light.svg", DOCS / "bidding-path-dark.svg"]
SVG = "{http://www.w3.org/2000/svg}"
PORTAL = "https://developer.ercot.com/"
LINK = re.compile(r"\]\(([^)\s]+)\)")


def svg_texts(path, cls):
    return {t.text for t in ET.parse(path).getroot().iter(f"{SVG}text") if t.get("class") == cls}


def normalise(text: str) -> str:
    """Page text or a quote, without markup, with straight quotes and single spaces."""
    text = html.unescape(re.sub(r"<[^>]+>", " ", text))
    text = text.translate({0x2018: "'", 0x2019: "'", 0x201C: '"', 0x201D: '"'})
    return " ".join(text.split())


def test_page_says_unofficial_first():
    assert "Not affiliated with or endorsed by ERCOT" in "\n".join(PAGE.splitlines()[:4])


@pytest.mark.parametrize("path", SVGS, ids=lambda p: p.name)
def test_svg_is_well_formed_and_self_contained(path):
    root = ET.parse(path).getroot()
    assert root.tag == f"{SVG}svg"
    assert float(root.get("width")) <= 960
    assert root.find(f"{SVG}title").text
    # Text stays text in a generic font stack: nothing embedded, linked or scripted.
    source = path.read_text(encoding="utf-8")
    for banned in ("@font-face", "url(data:", "<image", "<foreignObject", "<script", "href="):
        assert banned not in source, banned
    assert "Unofficial: not affiliated with or endorsed by ERCOT" in "".join(root.itertext())


def test_dark_differs_from_light_only_in_its_colours():
    light, dark = (
        re.sub(r"<style>.*?</style>", "", p.read_text(encoding="utf-8"), flags=re.S) for p in SVGS
    )
    assert light == dark


def test_page_shows_both_svgs():
    for path in SVGS:
        assert f'"{path.name}"' in PAGE


def test_every_numbered_element_has_a_source_row():
    numbers = svg_texts(SVGS[0], "numt")
    rows = set(re.findall(r"^\| (\d+) \|", PAGE, re.M))
    assert numbers == rows == {str(n) for n in range(1, len(rows) + 1)}
    for mark in svg_texts(SVGS[0], "sect"):
        assert f"### {mark}. " in PAGE


def test_every_local_file_the_page_cites_exists():
    cited = [t for t in LINK.findall(PAGE) if "://" not in t and not t.startswith("#")]
    cited += [f"../{p}" for p in re.findall(r"`(vendor/[^`]+)`", PAGE)]
    assert any("vendor/ercot/api-specs/ews/" in t for t in cited)
    for target in cited:
        path, _, fragment = target.partition("#")
        file = (DOCS / unquote(path)).resolve()
        assert file.exists(), target
        if re.fullmatch(r"L\d+(-L\d+)?", fragment):
            count = len(file.read_text(encoding="utf-8").splitlines())
            assert all(1 <= int(n) <= count for n in re.findall(r"\d+", fragment)), target
        elif fragment:
            headings = re.findall(r"^#+ (.+)$", file.read_text(encoding="utf-8"), re.M)
            assert fragment in {h.strip().lower().replace(" ", "-") for h in headings}, target


def test_every_quote_from_the_portal_is_on_the_section_it_cites():
    sections = {d["location"]: normalise(d["text"]) for d in portal_docs()}
    # Quotes start after the picture's alt text; code spans may hold quote marks of their own.
    body = re.sub(r"`[^`]*`", "", PAGE.split("## Sources", 1)[1])
    checked = 0
    for quote in re.finditer(r'"([^"]+)"', body):
        link = LINK.search(body, quote.end())
        if not link or not link.group(1).startswith(PORTAL):
            continue  # NP4-450-M and library sources are not vendored here
        location = link.group(1)[len(PORTAL) :]
        assert location in sections, location
        assert normalise(quote.group(1)) in sections[location], (quote.group(1), location)
        checked += 1
    assert checked >= 40
