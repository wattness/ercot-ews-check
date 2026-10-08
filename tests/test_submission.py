import re

from ercot_ews_check import sources, submission
from ercot_ews_check.submission import Transaction


def test_verbs_match_message_xsd():
    text = (sources.xsd_dir() / "Message.xsd").read_text(errors="replace")
    block = text[text.index('name="Verb"') : text.index('name="Noun"')]
    assert tuple(re.findall(r'enumeration value="([^"]+)"', block)) == submission.VERBS


def test_size_limit():
    assert submission.check_size(2_999_999) is None
    assert "less than 3 Mb in size(Pre-compression)" in submission.check_size(3_000_000)
    assert submission.should_compress(1_000_001)


def test_related_transactions_are_serialised():
    p = submission.plan(
        [
            Transaction("create", "BidSet", "QSE1.20261015.EOO.HB_HOUSTON.eoo01"),
            Transaction("cancel", "BidSet", "QSE1.20261015.EOO.HB_HOUSTON.eoo01"),
            Transaction("get", "BidSet", "x"),
        ]
    )
    assert not p.safe and "one at a time" in p.problems[0]
    assert [t.verb for t in p.steps] == ["create", "cancel", "get"]


def test_unknown_verb():
    assert not submission.plan([Transaction("Create", "BidSet", "k")]).safe


def test_error_severity():
    assert submission.error_is_trouble(None)
    assert not submission.error_is_trouble("INFORMATIVE")
