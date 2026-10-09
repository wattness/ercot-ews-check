# Rules

Severity `error`: breaks a rule ERCOT states, in a schema, on a documentation page, in its Market
Submission Validation Rules (NP4-450-M) or in its Nodal Protocols, so expect rejection; the one
exception is `nesting-depth`, a limit of this tool. `silent`: ERCOT may change or ignore this
without an error. `warning`: worth fixing or confirming; not a stated rejection. Errors and silent
changes block (exit status 1).

| Rule | Severity | Plain English |
|---|---|---|
| `schema` | error | ERCOT's schema does not allow this element, value, order or namespace. A report lists the first 100 schema errors; one more finding counts the rest. |
| `schema-unverified` | warning | The schemas could not be loaded, so nothing was validated. |
| `missing-required-field` | error, or warning | ERCOT's table for this product marks a field required (Y) or a key (K), and it is missing. The schema cannot catch this because every product field is optional there (D007). A warning when ERCOT's own create sample leaves the same field out, or when a Three-Part Offer whose curve goes below 0 MW (an Energy Storage Resource's) lacks `EocFipFop`: ERCOT's Market Submission Validation Rules (NP4-450-M, §2.1) say FIP and FOP do not apply to storage. |
| `value-numeric-bound` | error | A number is outside the range ERCOT's table states. For COP hsl and lsl this is a warning: the Protocols allow an Energy Storage Resource's HSL and LSL below zero (D033). For COP hel and lel it is a warning too: the Protocols give the emergency limits no sign (D047). |
| `value-enumerated` | warning | A value is not in the list ERCOT's table shows; the table may list examples only. |
| `value-before-trade-date` | warning | expirationTime is not before the trade date. ERCOT's own samples break this, so it is not enforced. |
| `value-ignored` | warning | ERCOT documents this field as ignored; sending it has no effect. Exception: an AS Offer's `combinedCycle`, which NP4-450-M §2.2 requires for a combined-cycle Resource; keep it there. |
| `withdrawn-payload` | error | ERCOT removed this payload type (IncDecOffer, removed with RTC+B; D010). |
| `trade-date-mismatch` | error | tradingDate is not the Central-time date on which the payload starts; the product's table requires a start hour "for trade date". |
| `utc-offset` | warning | A time's offset is neither UTC nor the Central-time offset in force at that instant, for example -05:00 after the November change to standard time. |
| `hour-24` | error | A time is written as 24:00. Use 00:00 on the next day. |
| `silent-hour-rounding` | silent | A time the product's table requires on an hour boundary is not on one; ERCOT may round it to the nearest hour without an error. |
| `overlapping-intervals` | error | Two time intervals of the same kind overlap. |
| `interval-gap` | warning | Intervals that should cover the day leave a gap. |
| `curve-style-points` | error | A FIXED or VARIABLE curve has more than one point. |
| `mw-precision` | warning | A MW value has more than one decimal place. Round toward zero. |
| `silent-rrs-value1-ignored` | silent | On an RRS self-arranged quantity ERCOT ignores value1; use the RRS sub-type fields. |
| `price-below-floor` | error | A Three-Part Offer or DAM Energy-Only Offer price is below -250.00 per MWh, the floor in ERCOT's Nodal Protocols (§4.4.9.3.1, §4.4.9.5.1, §4.4.9.7.1), or an AS Only Offer price is below 0 (NP4-450-M §2.3). |
| `price-above-cap` | error, or warning | A price is above ERCOT's System-Wide Offer Cap: the DASWCAP for a Three-Part Offer, DAM Energy-Only Offer or AS Only Offer, the RTSWCAP for an RTM Energy Bid. The values come from the Nodal Protocols version of 1 August 2026 (RTSWCAP 2,000; DASWCAP 5,000, or 2,000 during an Emergency Pricing Program or after the Peaker Net Margin threshold, which a document cannot show) and ERCOT changes them. A Three-Part Offer price between the two caps is an error if the message was created at or after 14:30 CT on the day before the Operating Day, and a warning otherwise: ERCOT accepts it only in an offer received before that time, and at that time cancels an Energy Offer Curve that contains it. |
| `curve-shape` | error | The points of an energy curve are out of the order ERCOT requires. Along a Three-Part Offer or DAM Energy-Only Offer curve prices never fall; along a DAM Energy Bid curve or RTM Energy Bid they never rise; quantities never fall; and no more than two points in a row share a price or a quantity (Nodal Protocols §4.4.9.3.1, §4.4.9.5.1, §4.4.9.6.1, §4.4.9.7.1). An RTM Energy Bid also starts at 0 MW, its second point is not 0 MW, and it ends at 0.1 MW or more (NP4-450-M §3.4). |
| `quantity-below-minimum` | error | An AS Only Offer amount is below 0.1 MW (NP4-450-M §2.3), or the largest quantity of a Three-Part Offer, DAM Energy-Only Offer or DAM Energy Bid curve is below 1 MW (Nodal Protocols §4.4.9.3.1, §4.4.9.5.1, §4.4.9.6.1). A Three-Part Offer curve that goes below 0 MW is an Energy Storage Resource's and has no such minimum. |
| `as-only-offer-type` | error | An AS Only Offer's asType is a schema value other than Reg-Up, Reg-Down, Non-Spin, RRSPF or ECRSS. NP4-450-M §2.3 restricts AS Only Offers to these five products (its codes: REGUP, REGDN, ONNS, RRSPF, ECRSS). |
| `cop-soc-order` | error | In a COP Limits element, minSOC is above targetBeginSOC (the Hour Beginning Planned SOC) or targetBeginSOC is above maxSOC. NP4-450-M §4.1 says COP validation rejects such a submission. |
| `cop-cancel` | error | A COP cannot be canceled, only updated. |
| `cancel-every-hour` | warning | The cancel ID has no hour suffix, so it cancels every hour of the day. |
| `payload-too-large` | error | ERCOT: a BidSet "must be less than 3 Mb in size(Pre-compression)". This tool reads 3 Mb as 3,000,000 bytes; split the BidSet. |
| `doctype` | error | The document has a document type declaration (`<!DOCTYPE ...>`). ERCOT's MarkeTrak Developer Guide lists among SOAP's syntax rules "A SOAP message must NOT contain a DTD reference"; the EWS pages do not state it. Nothing else was checked; remove it and check again. |
| `nesting-depth` | error | Elements nest more than 100 levels deep, far deeper than any ERCOT schema declares. This is this tool's limit, not a rule ERCOT states. Nothing else was checked; remove the extra levels and check again. |
