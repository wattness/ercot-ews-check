# Rules

Severity `error`: breaks a rule ERCOT states, in a schema or on a documentation page, so expect
rejection; the one exception is `nesting-depth`, a limit of this tool. `silent`: ERCOT may change
or ignore this without an error. `warning`: worth fixing or confirming; not a stated rejection.
Errors and silent changes block (exit status 1).

| Rule | Severity | Plain English |
|---|---|---|
| `schema` | error | ERCOT's schema does not allow this element, value, order or namespace. A report lists the first 100 schema errors; one more finding counts the rest. |
| `schema-unverified` | warning | The schemas could not be loaded, so nothing was validated. |
| `missing-required-field` | error, or warning | ERCOT's table for this product marks a field required (Y) or a key (K), and it is missing. The schema cannot catch this because every product field is optional there (D007). A warning when ERCOT's own create sample leaves the same field out. |
| `value-numeric-bound` | error | A number is outside the range ERCOT's table states. For COP hsl and lsl this is a warning: the Protocols allow an Energy Storage Resource's HSL and LSL below zero (D033). |
| `value-enumerated` | warning | A value is not in the list ERCOT's table shows; the table may list examples only. |
| `value-before-trade-date` | warning | expirationTime is not before the trade date. ERCOT's own samples break this, so it is not enforced. |
| `value-ignored` | warning | ERCOT documents this field as ignored; sending it has no effect. |
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
| `cop-cancel` | error | A COP cannot be canceled, only updated. |
| `cancel-every-hour` | warning | The cancel ID has no hour suffix, so it cancels every hour of the day. |
| `payload-too-large` | error | ERCOT: a BidSet "must be less than 3 Mb in size(Pre-compression)". This tool reads 3 Mb as 3,000,000 bytes; split the BidSet. |
| `doctype` | error | The document has a document type declaration (`<!DOCTYPE ...>`). ERCOT's MarkeTrak Developer Guide lists among SOAP's syntax rules "A SOAP message must NOT contain a DTD reference"; the EWS pages do not state it. Nothing else was checked; remove it and check again. |
| `nesting-depth` | error | Elements nest more than 100 levels deep, far deeper than any ERCOT schema declares. This is this tool's limit, not a rule ERCOT states. Nothing else was checked; remove the extra levels and check again. |
