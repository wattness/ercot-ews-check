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
python scripts/build_notifications.py --check   # docs/notifications.md matches the vendored files
```

## Layout

- `src/ercot_ews_check/checker.py`: `check()`; the XSD step (`schema.py`, explained by
  `explain.py`) then the prose rules.
- `src/ercot_ews_check/requirements.py`, `constraints.py`: requirement tables and Values-column
  rules, extracted at run time from `vendor/ercot/developer.ercot.com/search/search_index.json`.
- `src/ercot_ews_check/market_rules.py`: price, curve-shape, minimum-quantity, COP
  state-of-charge and AS Only Offer rules from ERCOT's Market Submission Validation Rules
  (NP4-450-M) and Nodal Protocols Section 4, which the EWS pages do not state. The offer caps are
  dated values; each message names the Protocols version they come from.
- `src/ercot_ews_check/discrepancies.py`: loads `discrepancies/*.yaml`, runs probes, renders the
  index.
- `src/ercot_ews_check/mutate.py`: mutation testing; `scripts/measure.py` prints the README figures.
- `src/ercot_ews_check/notifications.py`: the notifications ERCOT documents, read from the vendored
  portal and schemas; `scripts/build_notifications.py` writes them into `docs/notifications.md`.
- `vendor/ercot/`: ERCOT's files, byte-identical to their sources, hashed in `vendor/MANIFEST.json`.

## Rules

- Never edit files under `vendor/ercot/`. Corrections go in code or the catalogue.
- Catalogue IDs are permanent. Add new entries at the next number. `quote` holds ERCOT's exact
  words; descriptions go in `observed`.
- Every figure in the README's measured block comes from `scripts/measure.py`, and the limits and
  image description the README states must match the code; `tests/test_readme.py` enforces both.
- The terminal images in `docs/img/` come from `scripts/render_terminal.py`;
  `tests/test_render_terminal.py` fails when one no longer shows what its command prints.
- Documents given to `check()` are untrusted. Parse them with `schema.parse`, which refuses a
  DOCTYPE and nesting past `schema.MAX_DEPTH`, and load schemas from local files only;
  `tests/test_untrusted_input.py` covers each of these.
- A new rule ID goes in the README's rule table and in
  `skills/checking-ews-submissions/references/rules.md`.
- Use ERCOT's terms for ERCOT's things (BidSet, ASOnlyOffer, mRID, COP, MIS, EWS).
- Keep tests offline. Mark a test that needs the internet with `@pytest.mark.network`; it runs
  with `pytest --network`.
