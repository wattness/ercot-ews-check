from ercot_ews_check import examples


def test_counts_add_up():
    c = examples.counts()
    assert c["samples"] == (c["complete"] + c["abbreviated"] + c["fragments"] + c["not_xml"])
    assert c["complete"] == c["valid"] + c["invalid"]
    assert c["invalid"] == len(examples.invalid()) > 0


def test_every_invalid_sample_is_on_an_ews_page():
    for s in examples.invalid():
        assert s.page.startswith(examples.EWS_PREFIX)
        assert s.verdict.errors


def test_api_specs_examples():
    verdicts = examples.api_specs_examples()
    assert {k for k, v in verdicts.items() if not v.ok} == {
        "ASOnlyOffer-Example.xml",
        "GenResParams-SOC-Example.xml",
    }
