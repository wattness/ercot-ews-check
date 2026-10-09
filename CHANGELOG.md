# Changelog

## Unreleased

- `notebooks/field-note-01-ews-documentation.ipynb` recomputes the figures and the chart in the
  first field note, on where ERCOT's EWS documentation and its schemas disagree.

## 0.2.0 (2026-10-09)

### New checks

From ERCOT's MMS Market Submission Validation Rules (NP4-450-M, version 3.2) and Section 4 of its
Nodal Protocols (the version effective 1 August 2026), which the EWS pages and XSDs do not state:

- `price-below-floor` and `price-above-cap`: energy offer prices from -250.00 to the System-Wide
  Offer Caps, the AS Only Offer floor of 0 and its cap, and the RTSWCAP that applies to a
  Three-Part Offer received from 14:30 CT on the day before the Operating Day.
- `curve-shape`: the order of the points on energy offer and bid curves, and the RTM Energy Bid's
  quantity rules.
- `quantity-below-minimum`: 1 MW for energy offers and DAM Energy Bids, 0.1 MW for AS Only Offers.
- `as-only-offer-type`: the five products an AS Only Offer may carry.
- `cop-soc-order`: a COP's minimum, planned and maximum state of charge, in that order.

### Notifications

- `check` validates the message a `Notify` carries, and each message in a Get Notifications
  reply, against ERCOT's schemas; before, only the outer document was validated.
- A message inside a `Notify` is no longer checked as if it were a submission.
- [docs/notifications.md](docs/notifications.md) lists every notification ERCOT documents
  pushing, with its verb, noun and payload, built from the vendored pages and schemas by
  `scripts/build_notifications.py`.

### Catalogue

47 entries, from 33 in 0.1.0:

- D034: the RTM Energy Bid table spells the key `Resource`; the schema declares `resource`.
- D035 to D044: ERCOT's diagrams and its schemas disagree, each with the diagram vendored
  unmodified and probed by SHA-256.
- D045: the Wind and Solar Generation Forecast tables give the notification verb `create`.
- D046: ERCOT's api-specs AS Only Offer example offers `On-Non-Spin`; the schema's note and the AS
  Only Offer page say `Non-Spin`.
- D047: the COP table gives `hel` and `lel` >= 0; the Protocols set no sign for the emergency
  limits. A negative COP `hel` or `lel` is now a warning, not an error.

Corrections: D015's title now says request and notification tables; D028 names and links
Appendix C's current page; D034 and D038 are looked up by the right element names.

### Documentation

- [docs/bidding-path.md](docs/bidding-path.md): how a bid travels from a QSE's system through
  ERCOT's validation phases and back, each step cited, with a security note.

### Also since 0.1.0

- Untrusted input: a DOCTYPE or nesting deeper than 100 levels is refused before any check;
  schemas load from local files only; a report lists the first 100 schema errors and counts the
  rest.
- NP4-450-M where it changes a finding: a Three-Part Offer whose curve goes below 0 MW (an Energy
  Storage Resource's) may omit `EocFipFop`, with a warning; an RTM Energy Bid's `resource` is
  recognised; an AS Offer's `combinedCycle` is kept for a combined-cycle Resource.

## 0.1.0 (2026-10-08)

First release.
