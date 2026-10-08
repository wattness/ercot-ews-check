# Contributing

## Reporting a discrepancy

Open an issue with the **Discrepancy** template. Include the ERCOT page or file, the exact sentence,
table row or example, the schema rule it contradicts (file and line), and a minimal document that
shows the failure with `ercot-ews-check check`.

## Adding a catalogue entry

1. Copy the nearest entry in `discrepancies/` to the next free ID, `DNNN-short-slug.yaml`. IDs are
   never reused or renumbered.
2. Fill in `ercot_says` (page, location, URL, and a short `quote` in ERCOT's exact words, with
   `...` for elisions), `schema_says` (file, line, rule) and `do`. A description of a diagram or a
   file goes in `observed`, never in `quote`. Quote only what identifies the problem.
3. Add probes. `portal` is a sentence that must still be on the page (matched against the vendored
   search index with spacing normalised); `schema` is a regex whose first match is the cited line;
   `diagram` or `file` is a vendored file's sha256.
4. Add a `reproducer` when a document shows the problem: `invalid` must be blocked by the checker and
   `valid` must pass with no findings.
5. Run `python scripts/build_index.py` and `pytest`.

When ERCOT fixes a page, `ercot-ews-check verify --live` reports the probe that stopped matching.
Set `status: fixed` in that entry; do not delete it.

## Changing the checker

- A rule that comes from ERCOT's prose cites the page it comes from (`Finding.source`).
- A rule that ERCOT's own documents contradict is reported as a warning, with a catalogue entry.
- A finding cites a catalogue entry only when the entry is about the same element and the same
  kind of error.
- New rules need a test in `tests/test_checker.py` and, where they can be broken mechanically, a
  mutant in `src/ercot_ews_check/mutate.py` with its target rule in `mutate.TARGET`.
- Update the README block with `python scripts/measure.py` when a figure changes.

## Vendored files

Never edit a file under `vendor/ercot/`. `python scripts/fetch_vendor.py refresh --write` replaces
files that changed at their pinned source; `python scripts/fetch_vendor.py update --commit <sha>`
moves the api-specs pin. Both rewrite `vendor/MANIFEST.json`.

## Development

```sh
python -m pip install -e ".[dev]"
ruff check . && ruff format --check .
pytest
python scripts/check_boundaries.py
```
