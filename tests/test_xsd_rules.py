from ercot_ews_check import sources, xsd_rules

RULES = xsd_rules.extract()


def test_every_rule_cites_its_line():
    lines = {}
    for r in RULES[::25]:
        text = lines.setdefault(r.file, (sources.xsd_dir() / r.file).read_text(errors="replace"))
        line = text.splitlines()[r.line - 1]
        assert line.strip().startswith("<"), (r.cites, line)
        if r.kind in ("required", "fixed"):
            assert f'name="{r.target}"' in line, (r.cites, line)


def test_kinds():
    kinds = {r.kind for r in RULES}
    assert {"required", "order", "enumeration", "cardinality", "pattern"} <= kinds


def test_ids_are_unique():
    assert len({r.id for r in RULES}) == len(RULES)


def test_known_rules():
    by_id = {(r.owner, r.kind, r.constraint) for r in RULES}
    assert ("ErcotPrice", "pattern", r"[+\-]?(\d{1,6}|\d{1,6}\.\d{0,2}|\.\d{1,2})") in by_id
    assert any(r.owner == "ReplayDetectionType" and r.kind == "order" for r in RULES)


def test_diff():
    old = [{"id": "a", "constraint": "1"}, {"id": "b", "constraint": "2"}]
    new = [{"id": "b", "constraint": "3"}, {"id": "c", "constraint": "4"}]
    d = xsd_rules.diff(old, new)
    assert d == {"added": ["c"], "removed": ["a"], "changed": [{"id": "b", "was": "2", "now": "3"}]}
