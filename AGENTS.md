# AGENTS.md

Python package `ercot_ews_check` (src layout) that checks ERCOT EWS XML documents and holds a
catalogue of discrepancies in ERCOT's EWS documentation.

## Setup and checks

```sh
python -m pip install -e ".[dev]"
pytest                                   # offline: sockets refused, subprocess HTTP sent to a dead proxy
ruff check . && ruff format --check .
python scripts/check_boundaries.py       # imports: stdlib, xmlschema, yaml, pytest only
python scripts/build_index.py --check    # docs/discrepancies.md matches the YAML
```

## Layout

- `src/ercot_ews_check/checker.py`: `check()`; the XSD step (`schema.py`, explained by
  `explain.py`) then the prose rules.
- `src/ercot_ews_check/requirements.py`, `constraints.py`: requirement tables and Values-column
  rules, extracted at run time from `vendor/ercot/developer.ercot.com/search/search_index.json`.
- `src/ercot_ews_check/discrepancies.py`: loads `discrepancies/*.yaml`, runs probes, renders the
  index.
- `src/ercot_ews_check/mutate.py`: mutation testing; `scripts/measure.py` prints the README figures.
- `vendor/ercot/`: ERCOT's files, byte-identical to their sources, hashed in `vendor/MANIFEST.json`.

## Rules

- Never edit files under `vendor/ercot/`. Corrections go in code or the catalogue.
- Catalogue IDs are permanent. Add new entries at the next number. `quote` holds ERCOT's exact
  words; descriptions go in `observed`.
- Every README number comes from `scripts/measure.py`; `tests/test_readme.py` enforces it.
- Use ERCOT's terms for ERCOT's things (BidSet, ASOnlyOffer, mRID, COP, MIS, EWS).
- Keep tests offline. Mark a test that needs the internet with `@pytest.mark.network`; it runs
  with `pytest --network`.
