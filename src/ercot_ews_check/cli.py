"""Command-line interface: ``ercot-ews-check <command>``.

Exit status: 0 when nothing blocks, 1 when a document would be rejected or silently
changed (or, with --strict, has warnings), 2 when a file or download fails.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import textwrap
import urllib.request
from pathlib import Path

from ercot_ews_check import __version__, discrepancies, examples, mutate, sources, xsd_rules
from ercot_ews_check.checker import ERROR, SILENT, WARNING, check_file

FAILED = 2
INDEX = "ercot/developer.ercot.com/search/search_index.json"
XSDS = "ercot/api-specs/ews/xsds"


def _print_json(obj) -> None:
    print(json.dumps(obj, indent=2, default=str))


def _reports(args):
    """(file, report) for each readable file; unreadable ones are reported and skipped."""
    for name in args.files:
        try:
            yield name, check_file(name)
        except OSError as exc:
            print(f"{name}: cannot read: {exc.strerror or exc}", file=sys.stderr)
            args.failed = True


def _status(args, reports) -> int:
    if getattr(args, "failed", False):
        return FAILED
    bad = any(r.blocked or (args.strict and r.findings) for r in reports)
    return 1 if bad else 0


def cmd_check(args) -> int:
    done = []
    for name, rep in _reports(args):
        if args.json:
            _print_json({"file": name, **rep.to_dict()})
        else:
            print(f"{name}: {rep}")
        done.append(rep)
    return _status(args, done)


PLAIN = {
    ERROR: "Breaks a rule ERCOT states; expect rejection",
    SILENT: "ERCOT may change or ignore this without an error",
    WARNING: "Worth fixing or confirming",
}


def _paragraph(text: str) -> str:
    return textwrap.fill(
        " ".join(text.split()),
        88,
        initial_indent="   ",
        subsequent_indent="   ",
        break_long_words=False,
        break_on_hyphens=False,
    )


def cmd_explain(args) -> int:
    done = []
    order = {ERROR: 0, SILENT: 1, WARNING: 2}
    for name, rep in _reports(args):
        if rep.blocked:
            verdict = (
                "BLOCKED: breaks a rule ERCOT states, or ERCOT may change it without an error."
            )
        elif rep.findings:
            verdict = "Passes these checks, with warnings."
        else:
            verdict = (
                "Passes these checks. ERCOT still runs credit and market checks after receipt."
            )
        print(f"{name}\n{verdict}\n")
        for n, f in enumerate(sorted(rep.findings, key=lambda f: order.get(f.severity, 3)), 1):
            where = f" ({f.where})" if f.where else ""
            print(f"{n}. {PLAIN.get(f.severity, f.severity)}{where}.")
            print(_paragraph(f.message))
            if f.fix:
                print(_paragraph(f"Fix: {f.fix}"))
            for ref in f.see:
                e = discrepancies.get(ref)
                print(_paragraph(f"Possibly related catalogue entry {e.id}: {e.title}."))
            if f.source:
                print(_paragraph(f"ERCOT source: {f.source}"))
            print()
        done.append(rep)
    return _status(args, done)


def _entry_line(e: discrepancies.Entry) -> str:
    return f"{e.id}  {e.title}"


def cmd_lookup(args) -> int:
    found = discrepancies.search(args.query) if args.query else list(discrepancies.entries())
    if args.json:
        _print_json([_entry_dict(e) for e in found])
        return 0
    for e in found:
        print(_entry_line(e))
    if args.query and not found:
        print(f"no catalogued discrepancy matches {args.query!r}")
        return 1
    return 0


def _entry_dict(e: discrepancies.Entry) -> dict:
    d = {k: v for k, v in e.__dict__.items() if k != "path"}
    d["lookup"] = {k: list(v) for k, v in e.lookup.items()}
    d["reported"] = list(e.reported)
    return d


def _wrap(label: str, text: str) -> str:
    return textwrap.fill(
        " ".join(f"{label} {text}".split()),
        88,
        initial_indent="  ",
        subsequent_indent="      ",
        break_on_hyphens=False,
        break_long_words=False,
    )


def cmd_show(args) -> int:
    e = discrepancies.get(args.id)
    if e is None:
        print(f"no discrepancy {args.id!r}", file=sys.stderr)
        return 1
    if args.json:
        _print_json(_entry_dict(e))
        return 0
    says, schema = e.ercot_says, e.schema_says
    print(f"{e.id}  {e.title}")
    print(f"  kind: {e.kind}   resolution: {e.resolution}   status: {e.status}")
    where = "; ".join(x for x in (says.get("page"), says.get("location")) if x)
    if says.get("quote"):
        print(_wrap("ERCOT says:", f'{where}: "{says["quote"]}"'))
    else:
        print(_wrap("ERCOT's source:", where))
    print(f"      {e.url}")
    if says.get("observed"):
        print(_wrap("Observed:", says["observed"]))
    cite = f"{schema['file']}:{schema['line']}" if schema.get("file") else "no schema rule"
    print(_wrap(f"Schema ({cite}):", schema.get("rule", "")))
    if e.protocols_say:
        p = e.protocols_say
        print(_wrap(f"Protocols ({p.get('section', '')}):", f'"{p.get("quote", "")}"'))
        print(f"      {p.get('url', '')}")
    print(_wrap("Do:", e.do))
    if e.notes:
        print(_wrap("Note:", e.notes))
    for url in e.reported:
        print(f"  Reported: {url}")
    if e.reproducer:
        print(f"  Reproduce: ercot-ews-check reproduce {e.id}")
    return 0


def cmd_reproduce(args) -> int:
    e = discrepancies.get(args.id)
    if e is None or not e.reproducer:
        print(f"{args.id}: no reproducer", file=sys.stderr)
        return 1
    from ercot_ews_check.checker import check

    for label in ("invalid", "valid"):
        if label not in e.reproducer:
            continue
        rep = check(e.reproducer[label])
        print(f"--- {label} ---")
        print(e.reproducer[label].rstrip())
        print(f"=> {rep}\n")
    return 0


def _get(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "ercot-ews-check"})
    with urllib.request.build_opener().open(req, timeout=60) as resp:
        return resp.read()


def _fetch_live(tmp: Path) -> dict:
    """Today's portal index, schemas and every file a probe hashes, under ``tmp``."""
    docs = json.loads(_get(sources.live_url(INDEX)))["docs"]
    xsd = tmp / "ercot" / "api-specs" / "ews" / "xsds"
    xsd.mkdir(parents=True)
    for path in sources.xsd_dir().glob("*.xsd"):
        (xsd / path.name).write_bytes(_get(sources.live_url(f"{XSDS}/{path.name}")))
    for e in discrepancies.entries():
        for key in ("diagram", "file"):
            if key in e.probes:
                rel = e.probes[key]["path"]
                out = tmp / "ercot" / rel
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(_get(sources.live_url(f"ercot/{rel}")))
    return {"docs": docs, "xsd_dir": xsd, "files_dir": tmp / "ercot"}


def cmd_verify(args) -> int:
    if args.live:
        with tempfile.TemporaryDirectory() as tmp:
            results = discrepancies.verify(**_fetch_live(Path(tmp)))
        where = "live sources (developer.ercot.com, ercot/api-specs main)"
    else:
        results = discrepancies.verify()
        where = f"vendored sources (api-specs {sources.api_specs_commit()[:7]})"
    failed = [r for r in results if not r.ok]
    for r in failed:
        print(f"{r.entry}  {r.probe} probe no longer matches: {r.detail}")
    entries = {r.entry for r in results}
    changed = {r.entry for r in failed}
    still = len(entries) - len(changed)
    print(f"{still} of {len(entries)} open discrepancies still present in {where}")
    return 1 if failed else 0


def cmd_examples(args) -> int:
    counts = examples.counts()
    bad = examples.invalid()
    if args.json:
        rows = [{"page": s.url, "root": s.root, "error": s.verdict.detail} for s in bad]
        _print_json({"counts": counts, "invalid": rows})
        return 0
    print(
        f"{counts['samples']} distinct XML blocks on the EWS portal pages: "
        f"{counts['complete']} complete documents ({counts['valid']} valid, "
        f"{counts['invalid']} invalid), {counts['abbreviated']} abbreviated with '...', "
        f"{counts['fragments']} fragments, {counts['not_xml']} not well-formed XML"
    )
    if args.invalid:
        from ercot_ews_check.explain import explain

        for s in bad:
            msg = explain(s.verdict.errors[0]).message if s.verdict.errors else s.verdict.detail
            print(f"\n{s.root}  {s.url}\n  {msg}")
    for name, verdict in examples.api_specs_examples().items():
        print(f"api-specs ews/examples/{name}: {verdict.state}")
    return 0


def cmd_rules(args) -> int:
    rules = xsd_rules.extract()
    if args.owner:
        rules = [r for r in rules if r.owner == args.owner or r.target == args.owner]
    if args.kind:
        rules = [r for r in rules if r.kind == args.kind]
    if args.json:
        print(xsd_rules.to_json(rules))
        return 0
    for r in rules:
        print(f"{r.cites:<34} {r.kind:<12} {r.statement}")
    print(f"{len(rules)} rule(s)")
    return 0


def cmd_mutate(args) -> int:
    xml = Path(args.file).read_text(encoding="utf-8")
    outcomes = mutate.run(xml, xsd_rules.extract())
    summary = mutate.summary(outcomes)
    if args.json:
        _print_json(summary)
        return 0
    for family, label in (("schema", "XSD-rule mutants"), ("rule", "prose-rule mutants")):
        s = summary[family]
        print(
            f"{label}: {s['mutants']}; caught by the XSD {s['caught_by_xsd']}, by this tool's "
            f"rules {s['caught_by_rules']} ({s['caught_by_rules_only']} the XSD missed); "
            f"survived {len(s['survived'])}"
        )
        for how in s["survived"]:
            print(f"    survived: {how}")
    return 0


def cmd_sources(_args) -> int:
    m = sources.manifest()
    print(f"ercot/api-specs commit {m['api_specs_commit']}")
    for e in m["files"]:
        if not e["path"].startswith("ercot/api-specs/"):
            print(f"{e['path']}  retrieved {e['retrieved']}  sha256 {e['sha256'][:12]}")
    bad = sources.verify()
    print("\n".join(bad) if bad else f"all {len(m['files'])} vendored files match MANIFEST.json")
    return 1 if bad else 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="ercot-ews-check",
        description="Check ERCOT EWS documents and look up known discrepancies in ERCOT's "
        "EWS documentation.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("check", help="check one or more EWS XML files")
    c.add_argument("files", nargs="+")
    c.add_argument("--json", action="store_true")
    c.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    c.set_defaults(func=cmd_check)

    x = sub.add_parser("explain", help="check files and explain each finding in plain English")
    x.add_argument("files", nargs="+")
    x.add_argument("--strict", action="store_true", help="exit 1 on warnings too")
    x.set_defaults(func=cmd_explain)

    lk = sub.add_parser("lookup", help="search discrepancies by element, value, product or page")
    lk.add_argument("query", nargs="?")
    lk.add_argument("--json", action="store_true")
    lk.set_defaults(func=cmd_lookup)

    s = sub.add_parser("show", help="show one discrepancy")
    s.add_argument("id")
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=cmd_show)

    r = sub.add_parser("reproduce", help="run a discrepancy's reproducer through the checker")
    r.add_argument("id")
    r.set_defaults(func=cmd_reproduce)

    v = sub.add_parser("verify", help="check each discrepancy is still present in ERCOT's sources")
    v.add_argument(
        "--live", action="store_true", help="download today's copy of every probed source"
    )
    v.set_defaults(func=cmd_verify)

    e = sub.add_parser("examples", help="validate ERCOT's own XML samples")
    e.add_argument("--invalid", action="store_true", help="list the samples that fail")
    e.add_argument("--json", action="store_true")
    e.set_defaults(func=cmd_examples)

    ru = sub.add_parser("rules", help="list the constraints extracted from ERCOT's XSDs")
    ru.add_argument("--owner", help="complexType, simpleType or element name")
    ru.add_argument(
        "--kind",
        choices=sorted(
            {
                "required",
                "order",
                "enumeration",
                "cardinality",
                "pattern",
                "length",
                "bound",
                "fixed",
            }
        ),
    )
    ru.add_argument("--json", action="store_true")
    ru.set_defaults(func=cmd_rules)

    m = sub.add_parser("mutate", help="mutation-test the checker against a valid document")
    m.add_argument("file")
    m.add_argument("--json", action="store_true")
    m.set_defaults(func=cmd_mutate)

    so = sub.add_parser("sources", help="show and verify the vendored ERCOT files")
    so.set_defaults(func=cmd_sources)
    return p


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        # A console that cannot show a character (Windows code pages) must not crash a check.
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except BrokenPipeError:
        # The reader went away (e.g. `| head`); stop quietly.
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        return 141
    except OSError as exc:
        print(f"ercot-ews-check: {exc}", file=sys.stderr)
        return FAILED


if __name__ == "__main__":
    sys.exit(main())
