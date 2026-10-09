# Known discrepancies in ERCOT's EWS documentation and schemas

Built from `discrepancies/*.yaml` by `scripts/build_index.py`. Edit the YAML, not this file.
Each entry's probes are re-checked by `ercot-ews-check verify`.

47 entries. Resolutions:

- `schema-wins`: Follow the schema; the documentation is wrong.
- `prose-wins`: The schema accepts it, but ERCOT's stated rule does not; follow the prose.
- `neither`: Neither source settles it; pick one form and be consistent.
- `prose-stale`: The page describes something ERCOT has removed.

| ID | Discrepancy | Kind | Resolution | Status |
|---|---|---|---|---|
| [D001](#d001) | AOO table names ASOnlyPriceCurve/xvalue and /yvalue; the schema nests CurveData/xvalue and y1value | element-path | schema-wins | open |
| [D002](#d002) | ASO table puts startTime and endTime under PriceCurve; ASOffer's curve element is ASPriceCurve | element-path | schema-wins | open |
| [D003](#d003) | CRR table capitalises Source, Sink and MinimumReservationPrice/Price; the schema declares source, sink and price | element-name | schema-wins | open |
| [D004](#d004) | EOO table lists expirationTime after sp and bidID; the schema requires it before them | element-order | schema-wins | open |
| [D005](#d005) | expirationTime is drawn as the one required field of ASOffer; the schema makes it optional | required-field | prose-wins | open |
| [D006](#d006) | EB table marks PriceCurve/curveStyle required; the schema makes it optional | required-field | prose-wins | open |
| [D007](#d007) | Every product payload field is optional in the schema; the tables mark many required | required-field | prose-wins | open |
| [D008](#d008) | Services Organization says AS price curves use ASCurveData with NSRS values; neither name exists | element-name | schema-wins | open |
| [D009](#d009) | COP samples use operatingMode ONRL, which RTC+B removed from the schema | enumeration-value | schema-wins | open |
| [D010](#d010) | IncDecOffer is still documented as a bid type; RTC+B removed it from BidSet | withdrawn | prose-stale | open |
| [D011](#d011) | Rejected-bid samples write &lt;status&gt;ERROR&lt;/status&gt;; the enumeration has ERRORS | enumeration-value | schema-wins | open |
| [D012](#d012) | A BidSet response sample writes &lt;severity&gt;error&lt;/severity&gt;; the enumeration is upper case | enumeration-value | schema-wins | open |
| [D013](#d013) | The 'K, N' marker is defined but no table uses it | documentation | neither | open |
| [D014](#d014) | Appendix D's ReplayDetection has Created before Nonce, in the wsu and wsse namespaces | element-order | schema-wins | open |
| [D015](#d015) | Several request and notification tables give Header/Verb capitalised (Get, Change, Cancel, Reply, Created); the enumeration is lower case | enumeration-value | schema-wins | open |
| [D016](#d016) | Header/Revision 'should be 1 by default'; the schema default is 001 | default-value | neither | open |
| [D017](#d017) | Per-interface request tables omit ReplayDetection and Revision, which the header requires | required-field | schema-wins | open |
| [D018](#d018) | Some Market Information pages write Request/startTime, endTime and option in lower case | element-name | schema-wins | open |
| [D019](#d019) | ResParametersSet is described as holding requests of different types; the schema allows one type per set | cardinality | schema-wins | open |
| [D020](#d020) | Outage Creation and Outage Update tables spell Schedule/plannedSart | element-name | schema-wins | open |
| [D021](#d021) | The Acknowledge table names TimeStamp; Notification.xsd declares Timestamp | element-name | schema-wins | open |
| [D022](#d022) | Wind Generation Forecast lists statistic values AVG, MIN, MAX, SDV; the schema allows SAMPLE, MEAN, SD, ME, MAE, RMS | enumeration-value | schema-wins | open |
| [D023](#d023) | Wind Generation Forecast says WGRs can submit an LTWPF; no interface or type exists for it | enumeration-value | schema-wins | open |
| [D024](#d024) | Forecast samples write AnalogValue in exponent form (1.6E0); the schema types it xs:decimal | value-format | schema-wins | open |
| [D025](#d025) | SCED-interval MCPC samples use MCPC and MCPCOriginal; the schema now has Capped and Uncapped variants | element-name | prose-stale | open |
| [D026](#d026) | VDI InstructionType PROT_UNIT is described as 'PROTECT UNIT AGAIN FREEZING CONDITIONSE' | typo | neither | open |
| [D027](#d027) | GetReports table names filename, Created, Size and Format; the schema declares fileName, created, size and format | element-name | schema-wins | open |
| [D028](#d028) | Appendix C's diagram names ErcotDispute.xsd and ErcotDisputeTypes.xsd; the files are ErcotDisputes.xsd and ErcotDisputesTypes.xsd | file-name | schema-wins | open |
| [D029](#d029) | api-specs ews/examples/ASOnlyOffer-Example.xml puts BidSet in the message namespace | namespace | schema-wins | open |
| [D030](#d030) | api-specs ews/examples/GenResParams-SOC-Example.xml leaves ReplayDetection, Payload and ResParametersSet in no namespace | namespace | schema-wins | open |
| [D031](#d031) | Appendix H's spring-forward example has TmPoint/ending 2011-03-13T01400:00-05:00 | value-format | schema-wins | open |
| [D032](#d032) | Some samples use the 2007-05 ews namespace; the schemas declare 2007-06 | namespace | schema-wins | open |
| [D033](#d033) | COP table requires hsl and lsl &gt;= 0; the Protocols allow an ESR's HSL and LSL below zero | value-bound | schema-wins | open |
| [D034](#d034) | REB table capitalises Resource; the schema and ERCOT's own REB sample use resource | element-name | schema-wins | open |
| [D035](#d035) | The Message Header diagram draws ReplayDetection's children as wsse:Nonce and wsu:Created; the schema declares Nonce and Created in the message namespace | namespace | schema-wins | open |
| [D036](#d036) | The COP diagram expands ASCapacity with rrs and no ecrs; the schema has rrsPF, rrsFF, rrsUF and ecrs | element-name | schema-wins | open |
| [D037](#d037) | The ASO page's price-curve diagram captions OFFEC 'Offline Non-Spin price', as it does OFFNS; the schema documents OFFEC as the Offline ECRS price | annotation | schema-wins | open |
| [D038](#d038) | The Energy-Only Offer award pages show the AwardedEnergyOffer diagram (resource, startType, combinedCycleName); AwardedEnergyOnlyOffer holds awardedMWh, spp, bidId and sp | element-path | schema-wins | open |
| [D039](#d039) | The TotalLoad diagram names a TmPoint child multiHrIndicator; TmPoint declares multiHourBlock | element-name | schema-wins | open |
| [D040](#d040) | The RT15MinPriceAdder diagram names RTRDPECR; the schema, the page's element list and its example have RTRDPECRS | element-name | schema-wins | open |
| [D041](#d041) | The RTD Indicative Price Adders page draws and names a payload RTDIndicativePriceAdders; no schema declares it | element-name | neither | open |
| [D042](#d042) | The LoadRatioShare diagram draws a TmSchedule TmPoint with netTrade, multiHourBlock and tradeConfirmedFlag; LoadRatioShare's TmPoint is a ReportsTmPoint without them | element-path | schema-wins | open |
| [D043](#d043) | The Solar Generation Forecast diagram gives AnalogValue the base type xs:float; the schema's base type is xs:decimal | value-format | schema-wins | open |
| [D044](#d044) | The SOTG/SODG 15-minute price correction diagram types PriceOriginal and PriceCorrected xs:float; the schema types them xs:decimal | value-format | schema-wins | open |
| [D045](#d045) | Wind and Solar Generation Forecast tables give Header/Verb create; notification verbs are documented as past tense | documentation | neither | open |
| [D046](#d046) | api-specs ews/examples/ASOnlyOffer-Example.xml offers On-Non-Spin; the schema's note and the AS Only Offer page say Non-Spin | enumeration-value | schema-wins | open |
| [D047](#d047) | COP table gives hel and lel &gt;= 0, describing lel as a low sustained limit; the Protocols set no sign for the emergency limits and let an ESR's sustained limits go below zero | value-bound | neither | open |

## By product

- `ASOffer`: [D002](#d002), [D005](#d005), [D007](#d007), [D037](#d037)
- `ASOnlyOffer`: [D001](#d001), [D007](#d007), [D008](#d008), [D029](#d029), [D046](#d046)
- `COP`: [D007](#d007), [D009](#d009), [D033](#d033), [D036](#d036), [D047](#d047)
- `CRR`: [D003](#d003)
- `EnergyBid`: [D005](#d005), [D006](#d006), [D007](#d007)
- `EnergyOnlyOffer`: [D004](#d004), [D005](#d005), [D006](#d006), [D007](#d007), [D038](#d038)
- `IncDecOffer`: [D010](#d010)
- `PTPObligation`: [D007](#d007)
- `RTMEnergyBid`: [D034](#d034)

## By message

- `Acknowledge`: [D021](#d021)
- `ASObligations`: [D031](#d031)
- `AwardSet`: [D038](#d038)
- `BidSet`: [D001](#d001), [D002](#d002), [D003](#d003), [D004](#d004), [D005](#d005), [D006](#d006), [D007](#d007), [D008](#d008), [D009](#d009), [D010](#d010), [D011](#d011), [D012](#d012), [D029](#d029), [D032](#d032), [D033](#d033), [D034](#d034), [D036](#d036), [D037](#d037), [D046](#d046), [D047](#d047)
- `Dispute`: [D028](#d028)
- `ForecastPayload`: [D022](#d022), [D023](#d023), [D024](#d024), [D045](#d045)
- `ForecastSolarPayload`: [D024](#d024), [D043](#d043), [D045](#d045)
- `GetReports`: [D027](#d027)
- `LoadRatioShares`: [D042](#d042)
- `Notify`: [D021](#d021)
- `Offer and Bid Set Errors`: [D011](#d011)
- `OutageSet`: [D015](#d015), [D020](#d020)
- `Reports`: [D027](#d027)
- `RequestMessage`: [D014](#d014), [D015](#d015), [D016](#d016), [D017](#d017), [D018](#d018), [D029](#d029), [D030](#d030), [D035](#d035)
- `ResParametersSet`: [D019](#d019), [D030](#d030)
- `ResponseMessage`: [D035](#d035), [D045](#d045)
- `RT15MinPriceAdders`: [D040](#d040)
- `RTDIndicativePriceAdders`: [D041](#d041)
- `RTMPriceCorrectionMCPCSCEDs`: [D025](#d025)
- `RTMPriceCorrectionSOGPRICES`: [D044](#d044)
- `SCEDMCPCS`: [D025](#d025)
- `TotalLoad`: [D039](#d039)
- `VDIs`: [D026](#d026)
- `WindForecast`: [D022](#d022), [D023](#d023)

## By element

- `AnalogValue`: [D022](#d022), [D023](#d023), [D024](#d024), [D043](#d043)
- `ASCapacity`: [D036](#d036)
- `ASCurveData`: [D008](#d008)
- `ASOnlyPriceCurve`: [D001](#d001), [D008](#d008)
- `ASPriceCurve`: [D002](#d002)
- `asType`: [D046](#d046)
- `AwardedEnergyOnlyOffer`: [D038](#d038)
- `bidID`: [D004](#d004)
- `BidSet`: [D029](#d029)
- `CappedMCPC`: [D025](#d025)
- `CappedMCPCOriginal`: [D025](#d025)
- `combinedCycleName`: [D038](#d038)
- `ControllableLoadResource`: [D019](#d019)
- `Created`: [D014](#d014), [D027](#d027), [D035](#d035)
- `created`: [D027](#d027)
- `CurveData`: [D001](#d001), [D008](#d008)
- `curveStyle`: [D006](#d006)
- `ecrs`: [D036](#d036)
- `ending`: [D031](#d031)
- `endTime`: [D002](#d002), [D018](#d018)
- `EndTime`: [D018](#d018)
- `error`: [D012](#d012)
- `expirationTime`: [D004](#d004), [D005](#d005), [D013](#d013)
- `fileName`: [D027](#d027)
- `filename`: [D027](#d027)
- `format`: [D027](#d027)
- `Format`: [D027](#d027)
- `GenResourceParameters`: [D019](#d019), [D030](#d030)
- `Header`: [D015](#d015), [D016](#d016), [D017](#d017), [D045](#d045)
- `hel`: [D047](#d047)
- `hsl`: [D033](#d033)
- `IncDecOffer`: [D010](#d010)
- `InstructionType`: [D026](#d026)
- `lel`: [D047](#d047)
- `Limits`: [D033](#d033), [D047](#d047)
- `LoadRatioShare`: [D042](#d042)
- `lsl`: [D033](#d033)
- `MCPC`: [D025](#d025)
- `MCPCOriginal`: [D025](#d025)
- `MinimumReservationPrice`: [D003](#d003)
- `multiHrIndicator`: [D039](#d039)
- `netTrade`: [D042](#d042)
- `Nonce`: [D014](#d014), [D035](#d035)
- `NonControllableLoadResource`: [D019](#d019)
- `OFFEC`: [D037](#d037)
- `OffLineNonSpin`: [D037](#d037)
- `OFFNS`: [D037](#d037)
- `operatingMode`: [D009](#d009)
- `Option`: [D018](#d018)
- `option`: [D018](#d018)
- `Payload`: [D029](#d029), [D030](#d030)
- `plannedSart`: [D020](#d020)
- `plannedStart`: [D020](#d020)
- `price`: [D003](#d003)
- `Price`: [D003](#d003)
- `PriceCorrected`: [D044](#d044)
- `PriceCurve`: [D002](#d002), [D006](#d006)
- `PriceOriginal`: [D044](#d044)
- `ReplayDetection`: [D014](#d014), [D017](#d017), [D030](#d030), [D035](#d035)
- `ReplyCode`: [D021](#d021)
- `Resource`: [D034](#d034)
- `resource`: [D038](#d038)
- `ResourceParameters`: [D019](#d019)
- `ResourceStatus`: [D009](#d009)
- `ResParametersSet`: [D030](#d030)
- `Revision`: [D016](#d016), [D017](#d017)
- `rrs`: [D036](#d036)
- `RTDIndicativePriceAdder`: [D041](#d041)
- `RTDIndicativePriceAdders`: [D041](#d041)
- `RTRDPECR`: [D040](#d040)
- `RTRDPECRS`: [D040](#d040)
- `Schedule`: [D020](#d020)
- `severity`: [D012](#d012)
- `sink`: [D003](#d003)
- `Sink`: [D003](#d003)
- `size`: [D027](#d027)
- `Size`: [D027](#d027)
- `SOC`: [D030](#d030)
- `source`: [D003](#d003)
- `Source`: [D003](#d003)
- `sp`: [D004](#d004)
- `startTime`: [D002](#d002), [D018](#d018)
- `StartTime`: [D018](#d018)
- `startType`: [D038](#d038)
- `statistic`: [D022](#d022)
- `status`: [D011](#d011)
- `Timestamp`: [D021](#d021)
- `TimeStamp`: [D021](#d021)
- `TmPoint`: [D031](#d031)
- `tradeConfirmedFlag`: [D042](#d042)
- `type`: [D023](#d023)
- `UncappedMCPC`: [D025](#d025)
- `URL`: [D027](#d027)
- `Verb`: [D015](#d015), [D045](#d045)
- `xvalue`: [D001](#d001)
- `y1value`: [D001](#d001)
- `yvalue`: [D001](#d001)

## By service

- `Dispute Service`: [D028](#d028)
- `Market Information Service`: [D010](#d010), [D014](#d014), [D018](#d018), [D024](#d024), [D025](#d025), [D031](#d031), [D035](#d035), [D038](#d038), [D039](#d039), [D040](#d040), [D041](#d041), [D042](#d042), [D044](#d044)
- `Market Transaction Service`: [D001](#d001), [D002](#d002), [D003](#d003), [D004](#d004), [D005](#d005), [D006](#d006), [D007](#d007), [D008](#d008), [D009](#d009), [D010](#d010), [D011](#d011), [D012](#d012), [D014](#d014), [D029](#d029), [D032](#d032), [D033](#d033), [D034](#d034), [D035](#d035), [D036](#d036), [D037](#d037), [D046](#d046), [D047](#d047)
- `Notifications`: [D011](#d011), [D021](#d021), [D022](#d022), [D023](#d023), [D038](#d038), [D043](#d043), [D045](#d045)
- `Outage Scheduling Service`: [D015](#d015), [D020](#d020)
- `Report Service`: [D027](#d027)
- `Resource Parameter Transaction Service`: [D019](#d019), [D030](#d030)
- `Utility Interface`: [D015](#d015)
- `Verbal Dispatch Instructions`: [D026](#d026)

## Entries

### D001

**AOO table names ASOnlyPriceCurve/xvalue and /yvalue; the schema nests CurveData/xvalue and y1value**

- Kind: element-path (the documentation places an element under the wrong parent). Resolution: schema-wins.
- ERCOT says (Market Transaction Messages / Ancillary Service Only Offer (AOO); Message Element table): "ASOnlyPriceCurve/xvalue Y float Megawatts ... ASOnlyPriceCurve/yvalue Y float $/MWh" <https://developer.ercot.com/applications/ews/Market%20Transaction%20Messages/Ancillary%20Service%20Only%20Offer%20%28AOO%29/>
- Schema (`ErcotCommonTypes.xsd:689`): ASOnlyPriceCurve is a sequence of startTime, endTime and CurveData; CurveData holds xvalue and y1value. No ERCOT schema declares yvalue.
- Do: Write &lt;CurveData&gt;&lt;xvalue/&gt;&lt;y1value/&gt;&lt;/CurveData&gt; inside each ASOnlyPriceCurve.
- Reproduce: `ercot-ews-check reproduce D001`
- Reported upstream: <https://github.com/ercot/api-specs/issues/149>

### D002

**ASO table puts startTime and endTime under PriceCurve; ASOffer's curve element is ASPriceCurve**

- Kind: element-path (the documentation places an element under the wrong parent). Resolution: schema-wins.
- ERCOT says (Market Transaction Messages / Ancillary Service Offer (ASO); Message Element table): "PriceCurve/startTime Y dateTime Start time for curve Valid hour boundary PriceCurve/endTime Y dateTime" <https://developer.ercot.com/applications/ews/Market%20Transaction%20Messages/Ancillary%20Service%20Offer%20%28ASO%29/>
- Schema (`ErcotTransactionTypes.xsd:360`): ASOffer declares ASPriceCurve. PriceCurve is a different element, used by EnergyBid and RTMEnergyBid; the same table's other rows already say ASPriceCurve.
- Do: Put startTime and endTime inside ASPriceCurve.
- Reproduce: `ercot-ews-check reproduce D002`
- Reported upstream: <https://github.com/ercot/api-specs/issues/150>

### D003

**CRR table capitalises Source, Sink and MinimumReservationPrice/Price; the schema declares source, sink and price**

- Kind: element-name (the documentation spells an element name the schema does not declare). Resolution: schema-wins.
- ERCOT says (Market Transaction Messages / PTP Obligation with Links to Option (CRR); Message Element table): "Source K string Source settlement point ... Sink K string Sink settlement point" <https://developer.ercot.com/applications/ews/Market%20Transaction%20Messages/PTP%20Obligation%20with%20Links%20to%20Option%20%28CRR%29/>
- Schema (`ErcotTransactionTypes.xsd:388`): The CRR type declares source and sink, and MinimumPrice declares price, in lower case. XML names are case-sensitive.
- Do: Write &lt;source&gt;, &lt;sink&gt; and &lt;price&gt;.
- Reproduce: `ercot-ews-check reproduce D003`

### D004

**EOO table lists expirationTime after sp and bidID; the schema requires it before them**

- Kind: element-order (the documentation orders elements differently from the schema sequence). Resolution: schema-wins.
- ERCOT says (Market Transaction Messages / DAM Energy-Only Offer (EOO); Message Element table (the 1 after bidID is a footnote marker)): "sp K string Settlement point ... bidID 1 K string Bid ID ... expirationTime Y dateTime Time of offer expiration" <https://developer.ercot.com/applications/ews/Market%20Transaction%20Messages/DAM%20Energy-Only%20Offer%20%28EOO%29/>
- Schema (`ErcotTransactionTypes.xsd:636`): EnergyOnlyOffer extends Offer, which extends Bid. An extension appends to its base's sequence, so Offer's expirationTime comes before EnergyOnlyOffer's sp and bidID.
- Do: Order the children startTime, endTime, expirationTime, sp, bidID, then the curves.
- Reproduce: `ercot-ews-check reproduce D004`
- Note: The table is a list of fields, but a reader building the document from it top to bottom produces an order the schema rejects.

### D005

**expirationTime is drawn as the one required field of ASOffer; the schema makes it optional**

- Kind: required-field (the documentation and the schema disagree on whether a field is required). Resolution: prose-wins.
- ERCOT's source (Market Transaction Messages / Ancillary Service Offer (ASO); structure diagram (ASOffer_Structure.png)): <https://developer.ercot.com/applications/ews/Market%20Transaction%20Messages/Ancillary%20Service%20Offer%20%28ASO%29/>
- Observed: expirationTime is the only solid (required) box; every sibling is dashed (optional).
- Schema (`ErcotTransactionTypes.xsd:276`): expirationTime is minOccurs="0" on Offer and EnergyBid, like every other payload field.
- Do: Always send expirationTime on ASOffer, EnergyOnlyOffer and EnergyBid. The EOO and EB tables also mark it Y.
- Reproduce: `ercot-ews-check reproduce D005`
- Note: ERCOT's diagrams use solid boxes for required elements: on the Message Header diagram the solid boxes are exactly the five fields Message.xsd requires. See D007 for why the payload schemas cannot express a requirement.

### D006

**EB table marks PriceCurve/curveStyle required; the schema makes it optional**

- Kind: required-field (the documentation and the schema disagree on whether a field is required). Resolution: prose-wins.
- ERCOT says (Market Transaction Messages / DAM Energy Bid (EB); Message Element table): "PriceCurve/curveStyle Y string Used as an indicator to describe the type of ‘curve’ FIXED, VARIABLE or CURVE" <https://developer.ercot.com/applications/ews/Market%20Transaction%20Messages/DAM%20Energy%20Bid%20%28EB%29/>
- Schema (`ErcotCommonTypes.xsd:391`): curveStyle is minOccurs="0".
- Do: Always send curveStyle, with one of FIXED, VARIABLE or CURVE.
- Reproduce: `ercot-ews-check reproduce D006`

### D007

**Every product payload field is optional in the schema; the tables mark many required**

- Kind: required-field (the documentation and the schema disagree on whether a field is required). Resolution: prose-wins.
- ERCOT says (Services Organization; Market Products): "The XML schema provided to describe product types has all fields optional. This is because the schemas can be used for 'create', 'get' and 'cancel' operations." <https://developer.ercot.com/applications/ews/Services%20Organization/#market-products>
- Schema (`ErcotTransactionTypes.xsd:428`): Every child of ASOnlyOffer, COP, EnergyBid, EnergyOnlyOffer and the other payloads is minOccurs="0"; an empty &lt;ASOnlyOffer/&gt; validates.
- Do: Check a create against the Y and K markers in each product's Message Element table. `ercot-ews-check check` does this.
- Reproduce: `ercot-ews-check reproduce D007`

### D008

**Services Organization says AS price curves use ASCurveData with NSRS values; neither name exists**

- Kind: element-name (the documentation spells an element name the schema does not declare). Resolution: schema-wins.
- ERCOT says (Services Organization; Use of the IEC CIM): "For PriceCurve for ancillary services, ASCurveData elements are used (instead of CurveData elements) to define points for REGUP, REGDN, RRS and NSRS values." <https://developer.ercot.com/applications/ews/Services%20Organization/#use-of-the-iec-cim>
- Schema (`ErcotCommonTypes.xsd:689`): No ERCOT schema declares ASCurveData. ASOnlyPriceCurve uses CurveData. NSRS is not an AS type in any schema, and the list omits ECRS.
- Do: Use CurveData inside ASOnlyPriceCurve, and ERCOT's ASType values (for example Reg-Up, Reg-Down, RRSPF, ECRSS, Non-Spin).
- Reproduce: `ercot-ews-check reproduce D008`

### D009

**COP samples use operatingMode ONRL, which RTC+B removed from the schema**

- Kind: enumeration-value (the documentation uses a value the schema enumeration does not allow). Resolution: schema-wins.
- ERCOT says (Appendices / Appendix E: SOAP Examples; Market Transaction Messages / Current Operating Plan (COP); COP XML examples): "&lt;ns1:operatingMode&gt;ONRL&lt;/ns1:operatingMode&gt;" <https://developer.ercot.com/applications/ews/Appendices/Appendix%20E_%20SOAP%20Examples/>
- Schema (`ErcotCommonTypes.xsd:237`): ONRL is commented out of the operating-mode enumeration behind "RTC+B: Removed". ONL and ONSC were added.
- Do: Use a current operating mode such as ONL. Do not copy operating modes from the samples.
- Reproduce: `ercot-ews-check reproduce D009`
- Note: Appendix E repeats it 48 times; the COP page's own example carries it once.

### D010

**IncDecOffer is still documented as a bid type; RTC+B removed it from BidSet**

- Kind: withdrawn (the documentation still describes something ERCOT has withdrawn). Resolution: prose-stale.
- ERCOT says (Market Information Messages / DAM Phase II Validation Results; list of bid types): "IncDecOffer Inc Dec Energy Offer" <https://developer.ercot.com/applications/ews/Market%20Information%20Messages/DAM%20Phase%20II%20Validation%20Results/>
- Schema (`ErcotTransactionTypes.xsd:77`): BidSet's IncDecOffer element is commented out behind "RTC+B: Removed". ERCOT's Document Revisions record "Remove Incremental and Decremental Energy Offer Curves (IDO)".
- Do: Do not submit IncDecOffer. Treat the IDO page and the Appendix E IDO example as historical.
- Reproduce: `ercot-ews-check reproduce D010`

### D011

**Rejected-bid samples write &lt;status&gt;ERROR&lt;/status&gt;; the enumeration has ERRORS**

- Kind: enumeration-value (the documentation uses a value the schema enumeration does not allow). Resolution: schema-wins.
- ERCOT says (Notifications Messages / Offer and Bid Set Errors; Market Transaction Service; XML examples of rejected bids): "&lt;status&gt;ERROR&lt;/status&gt;" <https://developer.ercot.com/applications/ews/Notifications%20Messages/Offer%20and%20Bid%20Set%20Errors/>
- Schema (`ErcotCommonTypes.xsd:310`): TransactionStatusType enumerates SUBMITTED, ACCEPTED, PENDING, REJECTED, ERRORS, UNCONFIRMED, CANCELED and ACKNOWLEDGED. There is no ERROR.
- Do: When reading replies and notifications, treat ERROR, ERRORS and REJECTED alike rather than discard the message. Never write ERROR.
- Reproduce: `ercot-ews-check reproduce D011`

### D012

**A BidSet response sample writes &lt;severity&gt;error&lt;/severity&gt;; the enumeration is upper case**

- Kind: enumeration-value (the documentation uses a value the schema enumeration does not allow). Resolution: schema-wins.
- ERCOT says (Market Transaction Service; Offer and bid set submission, response example): "&lt;error&gt;&lt;severity&gt;error&lt;/severity&gt;&lt;text&gt;Unknown bid type XYZ&lt;/text&gt;&lt;/error&gt;" <https://developer.ercot.com/applications/ews/Market%20Transaction%20Service/#offer-and-bid-set-submission>
- Schema (`ErcotCommonTypes.xsd:367`): Error/severity is restricted to ERROR, WARNING and INFORMATIVE.
- Do: Compare severity case-insensitively when reading; write it in upper case.
- Reproduce: `ercot-ews-check reproduce D012`
- Note: The Error Handling prose calls the third level 'informational'; the schema value is INFORMATIVE.

### D013

**The 'K, N' marker is defined but no table uses it**

- Kind: documentation (the documentation describes a convention it does not follow). Resolution: neither.
- ERCOT says (Services Organization; Market Products): "There are some exception cases where identified key fields are identified as not being required (e.g. expiration), and are notated as 'K, N'." <https://developer.ercot.com/applications/ews/Services%20Organization/#market-products>
- Schema (no schema rule): Not a schema matter.
- Do: Expect Y, N, K or a condition in the Req column. A parser may accept 'K, N' but should not depend on it.

### D014

**Appendix D's ReplayDetection has Created before Nonce, in the wsu and wsse namespaces**

- Kind: element-order (the documentation orders elements differently from the schema sequence). Resolution: schema-wins.
- ERCOT says (Appendices / Appendix D: Annotated SOAP Message; annotated envelope, section 8): "&lt;msg:ReplayDetection&gt; &lt;wsu:Created&gt; 2006-11-29T20:05:55.022Z &lt;/wsu:Created&gt; &lt;wsse:Nonce EncodingType="#Base64Binary"&gt;" <https://developer.ercot.com/applications/ews/Appendices/Appendix%20D_%20Annotated%20SOAP%20Message/>
- Schema (`Message.xsd:64`): ReplayDetectionType is a sequence of Nonce then Created, both declared locally in the message namespace (elementFormDefault qualified).
- Do: Write msg:Nonce, then msg:Created, both in the message namespace. Appendix E, Appendix H and the service pages already do.
- Reproduce: `ercot-ews-check reproduce D014`

### D015

**Several request and notification tables give Header/Verb capitalised (Get, Change, Cancel, Reply, Created); the enumeration is lower case**

- Kind: enumeration-value (the documentation uses a value the schema enumeration does not allow). Resolution: schema-wins.
- ERCOT says (Utility Interface Messages / Get SASM ID List; Outage Scheduling Messages / Outage Update, Outage Cancellation, Outage Query; Change Active Notification URL; Confirmed and Unconfirmed Trades; request and response tables): "Header/Verb Get Header/Noun SASMIDList" <https://developer.ercot.com/applications/ews/Utility%20Interface%20Messages/Get%20SASM%20ID%20List/>
- Schema (`Message.xsd:77`): HeaderType/Verb is an enumeration of fifteen lower-case values: cancel, canceled, change, changed, create, created, close, closed, delete, deleted, get, reply, submit, update, updated.
- Do: Write the verb in lower case.
- Reproduce: `ercot-ews-check reproduce D015`
- Note: Get SASM ID List itself was withdrawn with RTC+B; the same capitalisation remains on the Outage pages.

### D016

**Header/Revision 'should be 1 by default'; the schema default is 001**

- Kind: default-value (the documented default differs from the schema's). Resolution: neither.
- ERCOT says (Services Organization; Message Header): "Revision: To indicate the revision of the message definition. This should be '1' by default." <https://developer.ercot.com/applications/ews/Services%20Organization/#message-header>
- Schema (`Message.xsd:95`): Revision is xsd:string with default="001"; any string validates.
- Do: Pick one value and send it consistently. ERCOT's samples use at least seven (1, 001, 1.0 and others).

### D017

**Per-interface request tables omit ReplayDetection and Revision, which the header requires**

- Kind: required-field (the documentation and the schema disagree on whether a field is required). Resolution: schema-wins.
- ERCOT says (Every interface page (for example Get SASM ID List); request parameter tables): "The following table describes the request parameters: Message Element Value Header/Verb ... Header/Noun ... Header/Source ... Header/UserID" <https://developer.ercot.com/applications/ews/Services%20Organization/#message-header>
- Schema (`Message.xsd:94`): HeaderType requires Verb, Noun, ReplayDetection, Revision and Source, in that order.
- Do: Build the header from Services Organization's Message Header section, not from an interface's request table.
- Reproduce: `ercot-ews-check reproduce D017`

### D018

**Some Market Information pages write Request/startTime, endTime and option in lower case**

- Kind: element-name (the documentation spells an element name the schema does not declare). Resolution: schema-wins.
- ERCOT says (Market Information Messages: Total ERCOT Load, Short-Term Wind Power Forecast, Short-Term Photovoltaic Power Forecast, WGR and PVGR Production Potential, Market Totals, Total DAM Energy; request parameter tables): "Request/startTime Start time Request/endTime End time" <https://developer.ercot.com/applications/ews/Market%20Information%20Messages/Total%20ERCOT%20Load%20-%20Same%20as%20System%20Load/>
- Schema (`Message.xsd:36`): RequestType declares StartTime, EndTime and Option with a capital initial, followed by a ##other wildcard that does not admit message-namespace elements.
- Do: Write StartTime, EndTime and Option.
- Reproduce: `ercot-ews-check reproduce D018`
- Reported upstream: <https://github.com/ercot/api-specs/issues/150>

### D019

**ResParametersSet is described as holding requests of different types; the schema allows one type per set**

- Kind: cardinality (the schema limits how many, or which combination of, elements may appear). Resolution: schema-wins.
- ERCOT says (Resource Parameter Transaction Service; Interfaces Provided): "A single container class 'ResParametersSet' is used to hold a request for changing resource parameters within the Payload section of the message, where each of the requests may be of a different type." <https://developer.ercot.com/applications/ews/Resource%20Parameter%20Transaction%20Service/#interfaces-provided>
- Schema (`ErcotTransactionTypes.xsd:652`): ResParametersSet is an xs:choice of GenResourceParameters, ControllableLoadResource, NonControllableLoadResource and ResourceParameters, each unbounded. Many requests of one type validate; two types do not.
- Do: Send one parameter type per ResParametersSet.
- Reproduce: `ercot-ews-check reproduce D019`

### D020

**Outage Creation and Outage Update tables spell Schedule/plannedSart**

- Kind: element-name (the documentation spells an element name the schema does not declare). Resolution: schema-wins.
- ERCOT says (Outage Scheduling Messages / Outage Creation; Outage Update; Message Element tables): "Schedule/ plannedSart N dateTime This is the date/time at which the Outage is planned to start." <https://developer.ercot.com/applications/ews/Outage%20Scheduling%20Messages/Outage%20Creation/>
- Schema (`ErcotOutageTypes.xsd:182`): The schema declares plannedStart (also new_plannedStart, plannedStartFrom, plannedStartTo). plannedSart appears in no schema.
- Do: Write plannedStart.
- Reproduce: `ercot-ews-check reproduce D020`
- Reported upstream: <https://github.com/ercot/api-specs/issues/150>

### D021

**The Acknowledge table names TimeStamp; Notification.xsd declares Timestamp**

- Kind: element-name (the documentation spells an element name the schema does not declare). Resolution: schema-wins.
- ERCOT says (Notifications; Interfaces Required, Acknowledge message): "ReplyCode OK or ERROR TimeStamp Current time string" <https://developer.ercot.com/applications/ews/Notifications/#interfaces-required>
- Schema (`Notification.xsd:46`): Acknowledge is a sequence of ReplyCode (string) and Timestamp (xsd:dateTime), then a ##other wildcard; &lt;TimeStamp&gt; in the notification namespace matches neither.
- Do: Reply with &lt;Timestamp&gt; carrying an xsd:dateTime.
- Reproduce: `ercot-ews-check reproduce D021`
- Reported upstream: <https://github.com/ercot/api-specs/issues/150>

### D022

**Wind Generation Forecast lists statistic values AVG, MIN, MAX, SDV; the schema allows SAMPLE, MEAN, SD, ME, MAE, RMS**

- Kind: enumeration-value (the documentation uses a value the schema enumeration does not allow). Resolution: schema-wins.
- ERCOT says (Notifications Messages / Wind Generation Forecast; AnalogValue table): "statistic Y String Statistic used to create data Enumeration (AVG, MIN, MAX, SDV)" <https://developer.ercot.com/applications/ews/Notifications%20Messages/Wind%20Generation%20Forecast/>
- Schema (`ErcotForecast.xsd:100`): AnalogValue/@statistic is required and restricted to SAMPLE, MEAN, SD, ME, MAE and RMS, in ErcotForecast.xsd and ErcotSolarQSEForecast.xsd alike.
- Do: Expect and write SAMPLE, MEAN, SD, ME, MAE or RMS. ERCOT's own solar example uses MEAN.
- Reproduce: `ercot-ews-check reproduce D022`

### D023

**Wind Generation Forecast says WGRs can submit an LTWPF; no interface or type exists for it**

- Kind: enumeration-value (the documentation uses a value the schema enumeration does not allow). Resolution: schema-wins.
- ERCOT says (Notifications Messages / Wind Generation Forecast; purpose): "Additionally the purpose is to allow WGRs to submit the LTWPF for their Resources to ERCOT and their respective QSE." <https://developer.ercot.com/applications/ews/Notifications%20Messages/Wind%20Generation%20Forecast/>
- Schema (`ErcotForecast.xsd:84`): AnalogValue/@type allows STWPF, WGRPP, TE, PR, WS, WD, PWR and BPAVG. LTWPF appears in no schema, and this page documents a notification ERCOT sends, not a submission.
- Do: Do not build an LTWPF submission; EWS has none.
- Reproduce: `ercot-ews-check reproduce D023`

### D024

**Forecast samples write AnalogValue in exponent form (1.6E0); the schema types it xs:decimal**

- Kind: value-format (an example writes a value in a form the schema type does not accept). Resolution: schema-wins.
- ERCOT says (Market Information Messages: Short-Term Wind Power Forecast, Short-Term Photovoltaic Power Forecast, WGR and PVGR Production Potential; XML examples): "&lt;ns1:AnalogValue statistic="MEAN" timeStamp="2016-01-14T10:00:00-06:00" type="STWPF" units="MW"&gt;1.6E0&lt;/ns1:AnalogValue&gt;" <https://developer.ercot.com/applications/ews/Market%20Information%20Messages/Short-Term%20Wind%20Power%20Forecast/>
- Schema (`ErcotForecast.xsd:78`): AnalogValue extends xs:decimal, whose lexical form has no exponent. 1.6E0 is an xs:float or xs:double literal.
- Do: When reading forecasts, parse the value as a float and do not reject the message on schema grounds alone. When writing, use plain decimals.
- Reproduce: `ercot-ews-check reproduce D024`
- Note: Found by validating the portal's samples (`ercot-ews-check examples --invalid`): four pages.

### D025

**SCED-interval MCPC samples use MCPC and MCPCOriginal; the schema now has Capped and Uncapped variants**

- Kind: element-name (the documentation spells an element name the schema does not declare). Resolution: prose-stale.
- ERCOT says (Market Information Messages: RT Clearing Prices for Capacity by SCED Interval; Price Corrected RTM MCPCs by SCED Interval; XML examples): "&lt;ns1:SCEDMCPC&gt; &lt;ns1:SCEDTimestamp&gt;10/01/2025 11:10:25&lt;/ns1:SCEDTimestamp&gt; &lt;ns1:RepeatedHourFlag&gt;N&lt;/ns1:RepeatedHourFlag&gt; &lt;ns1:ASType&gt;ECRS&lt;/ns1:ASType&gt; &lt;ns1:MCPC&gt;" <https://developer.ercot.com/applications/ews/Market%20Information%20Messages/RT%20Clearing%20Prices%20for%20Capacity%20by%20SCED%20Interval/>
- Schema (`ErcotInformationTypes.xsd:446`): Version 0.3.34 (NPRR1290/NPRR1323) replaced SCEDMCPC/MCPC with CappedMCPC and UncappedMCPC, and RTMPriceCorrectionMCPCSCED's MCPCOriginal/MCPCCorrected with capped and uncapped pairs.
- Do: Read CappedMCPC and UncappedMCPC (and their Original/Corrected pairs). The 15-minute and SPP variants keep MCPC.
- Reproduce: `ercot-ews-check reproduce D025`
- Note: Found by validating the portal's samples (`ercot-ews-check examples --invalid`).

### D026

**VDI InstructionType PROT_UNIT is described as 'PROTECT UNIT AGAIN FREEZING CONDITIONSE'**

- Kind: typo (a misspelling in text that is not validated). Resolution: neither.
- ERCOT says (Verbal Dispatch Instructions; InstructionType values): "PROT_UNIT PROTECT UNIT AGAIN FREEZING CONDITIONSE" <https://developer.ercot.com/applications/ews/Verbal%20Dispatch%20Instructions/>
- Schema (no schema rule): InstructionType is not enumerated in any schema.
- Do: Match on the code PROT_UNIT, not on the description. Text search for 'against freezing conditions' will miss this row.

### D027

**GetReports table names filename, Created, Size and Format; the schema declares fileName, created, size and format**

- Kind: element-name (the documentation spells an element name the schema does not declare). Resolution: schema-wins.
- ERCOT says (Report Messages / GetReports; report list table): "filename String Report file name Created dateTime Date of report creation. Size Integer File size in Bytes Format string" <https://developer.ercot.com/applications/ews/Report%20Messages/GetReports/>
- Schema (`ErcotReportTypes.xsd:30`): Report is a sequence of operatingDate, reportGroup, fileName, created, size, format and URL (typed URL, an xs:anyURI restriction). The page's own XML example uses the schema's spelling.
- Do: Read fileName, created, size and format.
- Reproduce: `ercot-ews-check reproduce D027`
- Reported upstream: <https://github.com/ercot/api-specs/issues/150>

### D028

**Appendix C's diagram names ErcotDispute.xsd and ErcotDisputeTypes.xsd; the files are ErcotDisputes.xsd and ErcotDisputesTypes.xsd**

- Kind: file-name (the documentation names a file that is not published). Resolution: schema-wins.
- ERCOT says (Appendices / Appendix C: XML Schemas for Message and Payload Definitions; diagram (XSD Relationships for Submissions.png)): "ErcotDispute.xsd, ErcotDisputeTypes.xsd" <https://developer.ercot.com/applications/ews/Appendices/Appendix%20C_%20XML%20Schemas%20for%20Message%20and%20Payload%20Definitions/>
- Schema (`ErcotDisputes.xsd:12`): The published files are ErcotDisputes.xsd and ErcotDisputesTypes.xsd; ErcotDisputes.xsd includes schemaLocation="ErcotDisputesTypes.xsd".
- Do: Use the plural file names.

### D029

**api-specs ews/examples/ASOnlyOffer-Example.xml puts BidSet in the message namespace**

- Kind: namespace (an example puts elements in a namespace the schema does not expect). Resolution: schema-wins.
- ERCOT says (github.com/ercot/api-specs: ews/examples/ASOnlyOffer-Example.xml; lines 6 and 20-21): "&lt;RequestMessage xmlns="http://www.ercot.com/schema/2007-06/nodal/ews/message"&gt; ... &lt;Payload&gt; &lt;BidSet&gt;" <https://github.com/ercot/api-specs/blob/7e785be50f0b0e5462f7d0e700ba82289f25390e/ews/examples/ASOnlyOffer-Example.xml>
- Observed: BidSet declares no namespace, so it takes the message namespace declared on RequestMessage.
- Schema (`Message.xsd:57`): Payload holds xsd:any namespace="##other", which excludes the message namespace. BidSet belongs to http://www.ercot.com/schema/2007-06/nodal/ews.
- Do: Declare xmlns="http://www.ercot.com/schema/2007-06/nodal/ews" on BidSet (or use a prefix bound to it).
- Reproduce: `ercot-ews-check reproduce D029`
- Note: A one-line fix was proposed upstream; the pull request was closed without merging on 2026-10-06.
- Reported upstream: <https://github.com/ercot/api-specs/pull/148>

### D030

**api-specs ews/examples/GenResParams-SOC-Example.xml leaves ReplayDetection, Payload and ResParametersSet in no namespace**

- Kind: namespace (an example puts elements in a namespace the schema does not expect). Resolution: schema-wins.
- ERCOT says (github.com/ercot/api-specs: ews/examples/GenResParams-SOC-Example.xml; lines 9-10 and 19-20): "&lt;ReplayDetection&gt; &lt;Nonce&gt;1359652204&lt;/Nonce&gt; ... &lt;Payload&gt; &lt;ResParametersSet&gt;" <https://github.com/ercot/api-specs/blob/7e785be50f0b0e5462f7d0e700ba82289f25390e/ews/examples/GenResParams-SOC-Example.xml>
- Observed: These elements are unprefixed and no default namespace is in scope, so they are in no namespace.
- Schema (`Message.xsd:64`): Message.xsd and ErcotTransactions.xsd are elementFormDefault qualified: ReplayDetection, Nonce, Created and Payload belong to the message namespace, ResParametersSet to the ews namespace.
- Do: Qualify every element: the header children with the message namespace, the payload with the ews namespace.
- Reproduce: `ercot-ews-check reproduce D030`
- Note: Proposed upstream together with D029; closed without merging on 2026-10-06.
- Reported upstream: <https://github.com/ercot/api-specs/pull/148>

### D031

**Appendix H's spring-forward example has TmPoint/ending 2011-03-13T01400:00-05:00**

- Kind: value-format (an example writes a value in a form the schema type does not accept). Resolution: schema-wins.
- ERCOT says (Appendices / Appendix H: DST XML Examples; ASObligations example, spring-forward day): "&lt;ns1:ending&gt;2011-03-13T01400:00-05:00&lt;/ns1:ending&gt;" <https://developer.ercot.com/applications/ews/Appendices/Appendix%20H_%20DST%20XML%20Examples/>
- Schema (`ErcotCommonTypes.xsd:899`): TmPoint/ending is xs:dateTime; '01400' is not an hour.
- Do: On the spring-forward day, the hour after 01:00-02:00 CST starts at 03:00 CDT; write ending as a valid dateTime such as 2011-03-13T04:00:00-05:00.
- Reproduce: `ercot-ews-check reproduce D031`
- Note: Found by validating the portal's samples (`ercot-ews-check examples --invalid`).

### D032

**Some samples use the 2007-05 ews namespace; the schemas declare 2007-06**

- Kind: namespace (an example puts elements in a namespace the schema does not expect). Resolution: schema-wins.
- ERCOT says (Market Transaction Service, the Appendices, and some Market Information and Notifications pages; XML examples): "xmlns="http://www.ercot.com/schema/2007-05/nodal/ews"" <https://developer.ercot.com/applications/ews/Market%20Transaction%20Service/#offer-and-bid-set-submission>
- Schema (`ErcotTransactions.xsd:19`): targetNamespace="http://www.ercot.com/schema/2007-06/nodal/ews". No current schema declares the 2007-05 namespace.
- Do: Use http://www.ercot.com/schema/2007-06/nodal/ews.
- Reproduce: `ercot-ews-check reproduce D032`
- Note: Most samples use 2007-06; a minority are stale.

### D033

**COP table requires hsl and lsl &gt;= 0; the Protocols allow an ESR's HSL and LSL below zero**

- Kind: value-bound (the documentation states a bound that ERCOT's rules or schema contradict). Resolution: schema-wins.
- ERCOT says (Market Transaction Messages / Current Operating Plan (COP); Message Element table): "Limits/hsl Y float High sustained limit in MW &gt;=0 Limits/lsl Y float Low sustained limit in MW &gt;=0" <https://developer.ercot.com/applications/ews/Market%20Transaction%20Messages/Current%20Operating%20Plan%20%28COP%29/>
- Schema (`ErcotCommonTypes.xsd:1247`): hsl and lsl are MWSingleDecimal, a plain xs:decimal; negative values validate.
- Protocols (Nodal Protocols 3.9.1(5)(c)(ii); 2.1, definition of Low Sustained Limit (LSL) for an Energy Storage Resource (ESR). Version of 1 August 2026.): "For ESRs, the HSL may be negative ... [the LSL for an ESR is] expressed as a MW value that may be less than, equal to, or greater than zero" <https://www.ercot.com/mktrules/nprotocols/current>
- Do: For an Energy Storage Resource, send the HSL and LSL the Protocols define, negative where the resource charges. The checker reports a negative COP hsl or lsl as a warning.
- Note: The cited Protocols text covers HSL and LSL only; D047 covers the table's &gt;=0 on hel and lel. The same table carries the ESR state-of-charge fields (maxSOC, minSOC, targetBeginSOC), and its lel row repeats the lsl description, 'Low sustained limit in MW'.

### D034

**REB table capitalises Resource; the schema and ERCOT's own REB sample use resource**

- Kind: element-name (the documentation spells an element name the schema does not declare). Resolution: schema-wins.
- ERCOT says (Market Transaction Messages / Real-Time Market Energy Bid (REB); Message Element table): "Resource K string Resource Valid resource name" <https://developer.ercot.com/applications/ews/Market%20Transaction%20Messages/Real-Time%20Market%20Energy%20Bid%20%28REB%29/>
- Schema (`ErcotTransactionTypes.xsd:292`): RTMEnergyBid declares resource in lower case, as the XML example under the table writes it. XML names are case-sensitive.
- Do: Write &lt;resource&gt;.
- Reproduce: `ercot-ews-check reproduce D034`

### D035

**The Message Header diagram draws ReplayDetection's children as wsse:Nonce and wsu:Created; the schema declares Nonce and Created in the message namespace**

- Kind: namespace (an example puts elements in a namespace the schema does not expect). Resolution: schema-wins.
- ERCOT says (Services Organization; diagram (Message_Header_Structure.png), Message Header): "msg:ReplayDetection ... wsse:Nonce ... wsu:Created" <https://developer.ercot.com/applications/ews/Services%20Organization/#message-header>
- Observed: The header's named children carry the msg prefix. ReplayDetection's two children are drawn as wsse:Nonce and wsu:Created, in that order, which are the WS-Security elements' names, and the caption under wsu:Created is the WS-Security utility schema's own description of that element.
- Schema (`Message.xsd:66`): ReplayDetectionType declares Nonce and Created locally (name=, not ref=), typed wsse:EncodedString and wsu:AttributedDateTime. Message.xsd is elementFormDefault qualified, so both elements are in the message namespace; wsse:Nonce and wsu:Created are different elements.
- Do: Write Nonce and then Created in the message namespace, like the header's other children. Only their types come from WS-Security.
- Reproduce: `ercot-ews-check reproduce D035`
- Note: The reproducer binds wsse and wsu to the namespaces Message.xsd imports. D014 records the same two namespaces, in the reverse order, in Appendix D's annotated message.

### D036

**The COP diagram expands ASCapacity with rrs and no ecrs; the schema has rrsPF, rrsFF, rrsUF and ecrs**

- Kind: element-name (the documentation spells an element name the schema does not declare). Resolution: schema-wins.
- ERCOT says (Market Transaction Messages / Current Operating Plan (COP); diagram (COP_Structure.png)): "ASCapacity ... regUp ... regDown ... rrs ... nonSpin" <https://developer.ercot.com/applications/ews/Market%20Transaction%20Messages/Current%20Operating%20Plan%20%28COP%29/>
- Observed: Inside the COP diagram, ASCapacity expands to startTime, endTime, regUp, regDown, rrs and nonSpin, and ends there. The same page's ASCapacity diagram (ASCapacity_Structure.png) and its Message Element table give rrsPF, rrsFF, rrsUF and ecrs.
- Schema (`ErcotTransactionTypes.xsd:187`): ASCapacity is startTime, endTime, regUp, regDown, rrsPF, rrsFF, rrsUF, nonSpin and ecrs. The comment on the line above rrsPF records that NPRR863 removed rrs; no schema declares it.
- Do: Send rrsPF, rrsFF and rrsUF in place of rrs, and ecrs after nonSpin. Build ASCapacity from the page's separate ASCapacity diagram or its table, not from the COP diagram.
- Reproduce: `ercot-ews-check reproduce D036`

### D037

**The ASO page's price-curve diagram captions OFFEC 'Offline Non-Spin price', as it does OFFNS; the schema documents OFFEC as the Offline ECRS price**

- Kind: annotation (the documentation describes an element differently from the schema's annotation). Resolution: schema-wins.
- ERCOT says (Market Transaction Messages / Ancillary Service Offer (ASO); diagram (PriceCurves_Using_ASPriceCurve.jpg)): "OFFNS ... Offline Non-Spin price ... OFFEC ... Offline Non-Spin price" <https://developer.ercot.com/applications/ews/Market%20Transaction%20Messages/Ancillary%20Service%20Offer%20%28ASO%29/>
- Observed: Under OffLineNonSpin, OFFEC carries the same caption as OFFNS, and the drawn sequence is xvalue, OFFNS, OFFEC, block, with no ECRS. The ASPriceCurve diagram on the Ancillary Service Awards and AwardedAS pages captions OFFEC 'Offline ECRS price' and draws ECRS after it.
- Schema (`ErcotCommonTypes.xsd:662`): In OffLineNonSpin, OFFNS is documented 'Offline Non-Spin price' and OFFEC 'Offline ECRS price', an NPRR863 Phase 2 (ECRS) element used in ASOffer submissions. An optional ECRS element, used in awards, follows OFFEC.
- Do: Put the Offline Non-Spin price in OFFNS and the Offline ECRS price in OFFEC; OFFEC is not a second Non-Spin price. Expect ECRS inside OffLineNonSpin when reading awards.
- Note: The page's table names OFFEC without saying what it prices, so the diagram's caption is the page's only description of it. No document can show the caption error, so there is no reproducer.

### D038

**The Energy-Only Offer award pages show the AwardedEnergyOffer diagram (resource, startType, combinedCycleName); AwardedEnergyOnlyOffer holds awardedMWh, spp, bidId and sp**

- Kind: element-path (the documentation places an element under the wrong parent). Resolution: schema-wins.
- ERCOT says (Market Information Messages / AwardedEnergyOnlyOffer; Notifications Messages / DAM Energy-Only Offer Awards; diagram (AwardedEnergyOnlyOffer_Structure.png)): "AwardedEnergyOffer ... EnergyAward Offer ... resource ... awardedMWh ... startType ... combinedCycleName" <https://developer.ercot.com/applications/ews/Market%20Information%20Messages/AwardedEnergyOnlyOffer/>
- Observed: Both pages present this image as the AwardedEnergyOnlyOffer structure. Its root is labelled AwardedEnergyOffer, and after the Award fields it draws resource, awardedMWh, startType and combinedCycleName, with no spp, bidId or sp. The Market Information page's own table and XML example list awardedMWh, spp, bidId and sp.
- Schema (`ErcotAwardTypes.xsd:180`): AwardedEnergyOnlyOffer extends Award with awardedMWh, spp (optional), bidId and sp. resource, startType and combinedCycleName belong to AwardedEnergyOffer (line 108), the Energy Offer award.
- Do: Read an Energy-Only Offer award as the Award fields followed by awardedMWh, spp, bidId and sp; expect no resource, startType or combinedCycleName.
- Reproduce: `ercot-ews-check reproduce D038`
- Note: The Energy Offer award pages' own diagram (AwardedEnergyOffer_Structure.png) draws the same structure. AwardedEnergyOnlyOffer's fields are the same as AwardedEnergyBid's, which the DAM Energy Bid award diagram (AwardedEnergyBid_Structure.png) draws.

### D039

**The TotalLoad diagram names a TmPoint child multiHrIndicator; TmPoint declares multiHourBlock**

- Kind: element-name (the documentation spells an element name the schema does not declare). Resolution: schema-wins.
- ERCOT says (Market Information Messages / Total ERCOT Load - Same as System Load; diagram (TotalLoad_Structure.png)): "netTrade ... multiHrIndicator ... tradeConfirmedFlag" <https://developer.ercot.com/applications/ews/Market%20Information%20Messages/Total%20ERCOT%20Load%20-%20Same%20as%20System%20Load/>
- Observed: TmPoint is drawn with eight children: time, ending, value1, value2, value3, netTrade, multiHrIndicator and tradeConfirmedFlag.
- Schema (`ErcotCommonTypes.xsd:936`): TotalLoad extends TmSchedule, whose TmPoint has multiHourBlock between netTrade and tradeConfirmedFlag. No schema declares multiHrIndicator.
- Do: Read multiHourBlock.
- Reproduce: `ercot-ews-check reproduce D039`
- Note: The drawing also goes straight from value3 to netTrade. TmPoint gained nspnm_value and ecrsm_value there in 2022 for Self-Arranged AS quantities; the TmPoint drawings on the System Load, Forecasted Load, Market Totals, Total DAM Energy and Energy Trade pages omit them too.

### D040

**The RT15MinPriceAdder diagram names RTRDPECR; the schema, the page's element list and its example have RTRDPECRS**

- Kind: element-name (the documentation spells an element name the schema does not declare). Resolution: schema-wins.
- ERCOT says (Market Information Messages / RT 15-Minute Price Adders; diagram (RT15MinPriceAdder.png)): "RTRDPRRS ... RTRDPECR ... RTRDPNS" <https://developer.ercot.com/applications/ews/Market%20Information%20Messages/RT%2015-Minute%20Price%20Adders/>
- Observed: RT15MinPriceAdder is drawn with ten children; the eighth is labelled RTRDPECR. The page's list of elements and its XML example use RTRDPECRS.
- Schema (`ErcotInformationTypes.xsd:339`): RT15MinPriceAdder declares RTRDPECRS (xs:decimal, required) between RTRDPRRS and RTRDPNS. No schema declares RTRDPECR.
- Do: Read RTRDPECRS.
- Reproduce: `ercot-ews-check reproduce D040`

### D041

**The RTD Indicative Price Adders page draws and names a payload RTDIndicativePriceAdders; no schema declares it**

- Kind: element-name (the documentation spells an element name the schema does not declare). Resolution: neither.
- ERCOT says (Market Information Messages / RTD Indicative Price Adders; diagram (RTDIndicativePriceAdders.png), with the request and response tables and the XML example): "RTDIndicativePriceAdders ... RTDIndicativePriceAdder" <https://developer.ercot.com/applications/ews/Market%20Information%20Messages/RTD%20Indicative%20Price%20Adders/>
- Observed: The diagram draws RTDIndicativePriceAdders holding any number of RTDIndicativePriceAdder. The page's second diagram (RTDIndicativePriceAdder.png) gives that element 28 children, among them BatchID and RTMCPCRUS. The page's tables use RTDIndicativePriceAdders as the noun and the payload, and its XML example has that root.
- Schema (`ErcotInformation.xsd:211`): The RTD price-adder payload ErcotInformation.xsd declares is RTDPriceAdders, with RTDPriceAdder children (the RTD Price Adders page). No schema declares RTDIndicativePriceAdders, RTDIndicativePriceAdder, RTMCPCRUS or the other RTMCPC elements, and BatchID survives only inside commented-out types, although ErcotInformationTypes.xsd's change log (line 73) says "Added RTDIndicativePriceAdder".
- Do: Do not expect RTDIndicativePriceAdders replies to validate against the published XSDs; read them by element name. RTDPriceAdders, which the schema declares, is a different report with different fields.
- Reproduce: `ercot-ews-check reproduce D041`
- Note: The reproducer has only an invalid document, because nothing declares the element. The page is not marked as removed, unlike RTD Indicative ORDC Price Adders.

### D042

**The LoadRatioShare diagram draws a TmSchedule TmPoint with netTrade, multiHourBlock and tradeConfirmedFlag; LoadRatioShare's TmPoint is a ReportsTmPoint without them**

- Kind: element-path (the documentation places an element under the wrong parent). Resolution: schema-wins.
- ERCOT says (Market Information Messages / Load Ratio Share; diagram (LoadRatioShare_Structure.png)): "TmSchedule (extension) ... netTrade ... multiHourBlock ... tradeConfirmedFlag" <https://developer.ercot.com/applications/ews/Market%20Information%20Messages/Load%20Ratio%20Share/>
- Observed: LoadRatioShare is drawn as an extension of TmSchedule, and its TmPoint as time, ending, value1, value2, value3, netTrade, multiHourBlock and tradeConfirmedFlag.
- Schema (`ErcotInformationTypes.xsd:166`): LoadRatioShare extends LRSTmSchedule, whose TmPoint is a ReportsTmPoint (ErcotCommonTypes.xsd:838 and 940) holding time, ending, value1, value2 and value3, each xs:decimal. netTrade, multiHourBlock and tradeConfirmedFlag belong to TmSchedule's TmPoint and are not allowed here.
- Do: Read a LoadRatioShare TmPoint as time, ending and value1 to value3; value1 carries the share.
- Reproduce: `ercot-ews-check reproduce D042`
- Note: ErcotInformationTypes.xsd's change log dates the switch to LRSTmSchedule to 03/12/2010 (0.3.16).

### D043

**The Solar Generation Forecast diagram gives AnalogValue the base type xs:float; the schema's base type is xs:decimal**

- Kind: value-format (an example writes a value in a form the schema type does not accept). Resolution: schema-wins.
- ERCOT says (Notifications Messages / Solar Generation Forecast; diagram (Solar_Forecast_AnalogValue_Structure.jpeg)): "Base Type xs:float" <https://developer.ercot.com/applications/ews/Notifications%20Messages/Solar%20Generation%20Forecast/>
- Observed: The AnalogValue node gives its base type as xs:float, and the base-type box carries the description of xs:float as an IEEE single-precision floating point type. The page's table describes the value as a valid floating point value.
- Schema (`ErcotSolarQSEForecast.xsd:76`): AnalogValue is simple content extending xs:decimal, as in ErcotForecast.xsd (line 78). xs:decimal has no exponent form, INF or NaN; xs:float has all three.
- Do: Write AnalogValue as a plain decimal such as 4.4. When reading, also accept the float forms ERCOT's samples use (D024).
- Reproduce: `ercot-ews-check reproduce D043`
- Note: D024 records ERCOT's forecast samples writing values such as 1.6E0, a form xs:float allows and xs:decimal does not.

### D044

**The SOTG/SODG 15-minute price correction diagram types PriceOriginal and PriceCorrected xs:float; the schema types them xs:decimal**

- Kind: value-format (an example writes a value in a form the schema type does not accept). Resolution: schema-wins.
- ERCOT says (Market Information Messages / Price Corrected SOTG/SODG 15-min Prices; diagram (RTMPriceCorrectionSOGPRICE_Structure.png)): "PriceOriginal Type xs:float ... PriceCorrected Type xs:float" <https://developer.ercot.com/applications/ews/Market%20Information%20Messages/Price%20Corrected%20SOTG_SODG%2015-min%20Prices/>
- Observed: Of the ten children drawn, PriceOriginal and PriceCorrected are typed xs:float; every other drawn type matches the schema.
- Schema (`ErcotInformationTypes.xsd:408`): RTMPriceCorrectionSOGPRICE declares PriceOriginal and PriceCorrected as xs:decimal (lines 408 and 409). xs:decimal has no exponent form, INF or NaN.
- Do: Read both prices as decimals rather than binary floating point; a value in exponent form does not validate.
- Reproduce: `ercot-ews-check reproduce D044`

### D045

**Wind and Solar Generation Forecast tables give Header/Verb create; notification verbs are documented as past tense**

- Kind: documentation (the documentation describes a convention it does not follow). Resolution: neither.
- ERCOT says (Notifications Messages / Wind Generation Forecast, Solar Generation Forecast; response message structure table): "Header/Verb create Header/Noun WindForecastData" <https://developer.ercot.com/applications/ews/Notifications%20Messages/Wind%20Generation%20Forecast/>
- Schema (`Message.xsd:79`): HeaderType/Verb enumerates both create (line 79) and created (line 80), so either validates; no schema ties a tense to a notification.
- Do: In a listener, accept create as well as created on a WindForecastData or SolarForecastData notification, and route on Header/Noun rather than on the verb.
- Note: Services Organization (Message Header, https://developer.ercot.com/applications/ews/Services%20Organization/#message-header) says notification messages use past-tense verbs, naming created, changed, canceled and closed. Every other notification page's table gives a past-tense verb; Confirmed and Unconfirmed Trades writes it Created, which D015 covers. No ERCOT sample shows the header of a forecast notification.

### D046

**api-specs ews/examples/ASOnlyOffer-Example.xml offers On-Non-Spin; the schema's note and the AS Only Offer page say Non-Spin**

- Kind: enumeration-value (the documentation uses a value the schema enumeration does not allow). Resolution: schema-wins.
- ERCOT says (github.com/ercot/api-specs: ews/examples/ASOnlyOffer-Example.xml; line 86): "&lt;asType&gt;On-Non-Spin&lt;/asType&gt;" <https://github.com/ercot/api-specs/blob/7e785be50f0b0e5462f7d0e700ba82289f25390e/ews/examples/ASOnlyOffer-Example.xml>
- Schema (`ErcotCommonTypes.xsd:78`): The change note for version 0.3.33 (03/05/2025) says "Non-Spin is used for ASOnlyOffer submission rather than On-Non-Spin", and the AS Only Offer page limits the offer to Reg-Up, Reg-Down, Non-Spin, RRSPF and ECRSS. On-Non-Spin is in the ASType enumeration, so the XSD accepts the example.
- Do: Write &lt;asType&gt;Non-Spin&lt;/asType&gt; in an AS Only Offer.
- Reproduce: `ercot-ews-check reproduce D046`

### D047

**COP table gives hel and lel &gt;= 0, describing lel as a low sustained limit; the Protocols set no sign for the emergency limits and let an ESR's sustained limits go below zero**

- Kind: value-bound (the documentation states a bound that ERCOT's rules or schema contradict). Resolution: neither.
- ERCOT says (Market Transaction Messages / Current Operating Plan (COP); Message Element table): "Limits/hel Y float High emergency limit in MW &gt;=0 Limits/lel Y float Low sustained limit in MW &gt;=0" <https://developer.ercot.com/applications/ews/Market%20Transaction%20Messages/Current%20Operating%20Plan%20%28COP%29/>
- Schema (`ErcotTransactionTypes.xsd:171`): hel and lel are MWSingleDecimal, a plain xs:decimal; negative values validate.
- Protocols (Nodal Protocols 2.1, definitions of Low Emergency Limit (LEL) and of Low Sustained Limit (LSL) for an Energy Storage Resource (ESR); 3.9.1(5)(c) to (f). Version of 1 August 2026.): "The limit established by the QSE describing the minimum temporary unsustainable energy production capability of a Resource ... A negative LSL for an ESR describes the maximum sustained energy charging capability of the ESR." <https://www.ercot.com/mktrules/nprotocols/current>
- Do: Neither source settles whether ERCOT accepts a negative HEL or LEL for an Energy Storage Resource. The checker reports a negative COP hel or lel as a warning, not an error.
- Note: The lel row repeats the lsl row's description, 'Low sustained limit in MW'. D033 covers hsl and lsl, which the Protocols say may be negative for an ESR. No ERCOT sample shows a negative COP limit.
