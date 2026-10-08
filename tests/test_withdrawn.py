import re

from ercot_ews_check import discrepancies, sources, withdrawn


def test_aliases():
    assert withdrawn.withdrawal_for("IDO").name == "IncDecOffer"
    assert withdrawn.withdrawal_for("Get SASM ID List").name == "SASM"
    assert withdrawn.withdrawal_for("EnergyOnlyOffer") is None


def test_may_submit():
    assert not withdrawn.may_submit("IncDecOffer")
    assert withdrawn.may_submit("ASOnlyOffer")


def test_schema_evidence_is_present():
    xsd = sources.xsd_dir()
    text = (xsd / "ErcotTransactionTypes.xsd").read_text(encoding="utf-8", errors="replace")
    assert "RTC+B: Removed" in text
    text = (xsd / "Message.xsd").read_text(encoding="utf-8", errors="replace")
    assert "Removed SASM from MarketType" in text


def test_release_date_is_the_document_revisions_date():
    page = next(
        discrepancies.flatten(d["text"])
        for d in sources.portal_docs()
        if d["location"] == "applications/ews/Document%20Revisions/"
    )
    # Columns are Date, Description, Release Date; a row's release date precedes the next row.
    released = re.findall(r"RTC\+B Updates .*?(\d\d/\d\d/\d{4}) \d\d/\d\d/\d{4} ", page)
    assert released and set(released) == {withdrawn.RTC_B_RELEASE.strftime("%m/%d/%Y")}
