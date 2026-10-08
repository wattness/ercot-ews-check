from urllib.parse import urlsplit

import pytest

from ercot_ews_check import checker, hazards, sources
from ercot_ews_check.discrepancies import flatten, normalize

DOCS = [(d["location"], flatten(d["text"])) for d in sources.portal_docs()]


@pytest.mark.parametrize("hazard", hazards.HAZARDS, ids=lambda h: h.id)
def test_quote_is_on_the_cited_page(hazard):
    page = urlsplit(hazard.source).path.split("/applications/ews/")[-1]
    hits = [
        loc
        for loc, text in DOCS
        if loc.startswith(f"applications/ews/{page}") and normalize(hazard.quote) in text
    ]
    assert hits


def test_ids_are_unique():
    assert len(hazards.BY_ID) == len(hazards.HAZARDS)


def test_checked_rrs_hazard_shares_its_id_with_the_checker():
    assert "silent-rrs-value1-ignored" in hazards.BY_ID
    assert checker.SILENT == hazards.SILENT
