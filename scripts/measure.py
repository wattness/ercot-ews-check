#!/usr/bin/env python3
"""Print every figure the README states, computed from this checkout.

    python scripts/measure.py

The README's "What it has found" block is this script's output, and
tests/test_readme.py fails when the two differ.
"""

from __future__ import annotations

import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ercot_ews_check import (  # noqa: E402
    constraints,
    discrepancies,
    examples,
    mutate,
    requirements,
    sources,
    xsd_rules,
)


def lines() -> list[str]:
    out = [
        f"Sources: ercot/api-specs {sources.api_specs_commit()[:7]}, retrieved "
        f"{sources.manifest()['files'][0]['retrieved']}"
    ]

    items = discrepancies.entries()
    res = Counter(e.resolution for e in items)
    probes = discrepancies.verify()
    out.append(
        f"Catalogue: {len(items)} discrepancies ("
        + ", ".join(f"{n} {r}" for r, n in sorted(res.items(), key=lambda kv: -kv[1]))
        + f"); {sum(p.ok for p in probes)} of {len(probes)} probes still match; "
        f"{sum(1 for e in items if e.reproducer)} with a reproducer; "
        f"{sum(1 for e in items if e.reported)} reported upstream"
    )

    c = examples.counts()
    out.append(
        f"Portal samples: {c['samples']} distinct XML blocks on EWS pages; {c['complete']} "
        f"complete documents, of which {c['invalid']} fail ERCOT's own XSDs"
    )
    specs = examples.api_specs_examples()
    bad = sorted(name for name, v in specs.items() if not v.ok)
    out.append(
        f"api-specs ews/examples: {len(bad)} of {len(specs)} fail ERCOT's own XSDs "
        f"({', '.join(bad)})"
    )

    rules = xsd_rules.extract()
    kinds = Counter(r.kind for r in rules)
    out.append(
        f"XSD constraints extracted: {len(rules)} ("
        + ", ".join(f"{n} {k}" for k, n in kinds.most_common())
        + ")"
    )

    tables = requirements.tables()
    cov = constraints.coverage()
    out.append(
        f"Requirement tables: {sum(len(t) for t in tables.values())} element rows on "
        f"{len(tables)} portal pages; {cov['constraints']} value rules parsed, "
        f"{cov['unparsed']} stated rules left unparsed"
    )

    totals: dict[str, Counter] = {"schema": Counter(), "rule": Counter()}
    kinds: Counter = Counter()
    files = sorted((ROOT / "examples").glob("*.xml"))
    for f in files:
        summary = mutate.summary(mutate.run(f.read_text(encoding="utf-8"), rules))
        for family, s in summary.items():
            totals[family].update(
                mutants=s["mutants"],
                xsd=s["caught_by_xsd"],
                rules=s["caught_by_rules"],
                rules_only=s["caught_by_rules_only"],
                survived=len(s["survived"]),
            )
        kinds.update({k: v["mutants"] for k, v in summary["rule"]["by_kind"].items()})
    s, r = totals["schema"], totals["rule"]
    out.append(
        f"Mutants of the {len(files)} files in examples/: {s['mutants']} break an XSD "
        f"constraint (XSD catches {s['xsd']}, this tool's rules {s['rules']}); {r['mutants']} "
        f"each break one of this tool's prose rules (the rule it targets catches {r['rules']}, "
        f"{r['rules_only']} of them pass the XSD; {r['survived']} survive)"
    )
    out.append(
        "Prose-rule mutants by rule: "
        + ", ".join(f"{n} {k}" for k, n in sorted(kinds.items(), key=lambda kv: (-kv[1], kv[0])))
    )
    return out


if __name__ == "__main__":
    print("\n".join(lines()))
