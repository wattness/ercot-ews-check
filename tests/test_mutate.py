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


def test_soc_mutant_is_caught():
    """No example carries a state of charge, so build a COP that does."""
    cop = """<BidSet xmlns="http://www.ercot.com/schema/2007-06/nodal/ews">
  <tradingDate>2026-10-15</tradingDate>
  <COP>
    <resource>R1</resource>
    <Limits>
      <startTime>2026-10-15T00:00:00-05:00</startTime>
      <endTime>2026-10-16T00:00:00-05:00</endTime>
      <hsl>10.0</hsl><lsl>0.0</lsl><hel>10.0</hel><lel>0.0</lel>
      <maxSOC>20.0</maxSOC><minSOC>5.0</minSOC><targetBeginSOC>10.0</targetBeginSOC>
    </Limits>
  </COP>
</BidSet>
"""
    found = [o for o in mutate.run(cop, RULES) if o.mutant.kind == "soc-order"]
    assert [o.mutant.how for o in found] == ["COP targetBeginSOC = 21.0"]
    assert all(o.by_rules and not o.by_schema for o in found)
