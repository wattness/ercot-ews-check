import pytest

from ercot_ews_check import mutate, xsd_rules

from helpers import EXAMPLES

RULES = xsd_rules.extract()


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_no_mutant_survives(path):
    outcomes = mutate.run(path.read_text(), RULES)
    assert outcomes
    survivors = [o.mutant.how for o in outcomes if not o.caught]
    assert not survivors


@pytest.mark.parametrize("path", EXAMPLES, ids=lambda p: p.name)
def test_schema_mutants_are_invalid(path):
    for m in mutate.schema_mutants(path.read_text(), RULES):
        assert mutate.checker.check(m.xml).schema == "invalid", m.how


def test_rule_mutants_need_this_tools_rules():
    xml = (EXAMPLES[0].parent / "energy-only-offer.xml").read_text()
    s = mutate.summary(mutate.run(xml, RULES))["rule"]
    assert s["caught_by_rules"] == s["mutants"]
    assert s["caught_by_rules_only"] > 0
