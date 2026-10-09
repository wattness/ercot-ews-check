# Notifications ERCOT pushes

ERCOT sends some EWS messages without being asked: the outcome of validating a BidSet, confirmed
and unconfirmed trades, awards and obligations, outage state changes, startup and shutdown
instructions, wind and solar forecasts, validation results, and notices and alerts. These are
notifications. ERCOT's
[Notifications](https://developer.ercot.com/applications/ews/Notifications/#interfaces-provided)
page says the 'Notify' interface "is used as a means to asynchronously receive information by
Market Participants from ERCOT".

This page lists every notification ERCOT documents, the message each arrives in, where ERCOT's
schemas declare its payload and what RTC+B changed, and says what `ercot-ews-check check` does
with one. The [reference](#reference) is generated from the vendored portal pages and schemas by
`python scripts/build_notifications.py`; `tests/test_notifications.py` fails when it is out of
date.

## How a notification reaches a listener

- The Market Participant runs the listener: "Each Market Participant using the external interface
  would be required to provide a listener interface for the receipt of notification messages,
  compliant with the interface provided by ERCOT."
  ([Notifications](https://developer.ercot.com/applications/ews/Notifications/))
- "ERCOT will send notifications to port 443 of the specified URL using an HTTPS connection." It
  signs the SOAP message, and "The 'Acknowledge' message does not need to be signed."
  ([Notifications, Message Specifications](https://developer.ercot.com/applications/ews/Notifications/#message-specifications))
- A Market Participant may register up to two URLs (the same section), and a request to
  [Change Active Notification URL](https://developer.ercot.com/applications/ews/Utility%20Interface%20Messages/Change%20Active%20Notification%20URL/)
  switches ERCOT between them; it does not change the URLs themselves.
- The listener implements one operation: `Notify` (`Notification.wsdl:55`) on the
  `NotificationConsumer` port type takes a `Notify` (`Notification.wsdl:56`) and returns an
  `Acknowledge` (`Notification.wsdl:57`), or a `Fault` (`Notification.wsdl:58`).
- `Notify` (`Notification.xsd:34`) holds one or more `NotificationMessage`
  (`Notification.xsd:37`), each with a `Message` (`Notification.xsd:23`) whose content is one
  element of any namespace, validated laxly: `xsd:any` (`Notification.xsd:26`). ERCOT says what
  that element is: "The contents of the any structure would be wrapped using the ResponseMessage
  structure defined in section 2.1.4"
  ([Notifications, Interfaces Required](https://developer.ercot.com/applications/ews/Notifications/#interfaces-required)).
  Where a notification page has a table, it describes that ResponseMessage: Header/Verb,
  Header/Noun, Header/Source `ERCOT`, a Reply, and the Payload.
- The listener answers with `Acknowledge` (`Notification.xsd:42`): `ReplyCode`
  (`Notification.xsd:45`), then `Timestamp` (`Notification.xsd:46`). The Notifications page's
  table spells the second `TimeStamp`; follow the schema ([D021](discrepancies.md#d021)).

## What `ercot-ews-check check` does with one

`check` takes a notification as the listener receives it (a SOAP envelope holding a `Notify`), a
bare `Notify`, the message it carries, or the payload alone.

- It validates the `Notify` against `Notification.xsd`, the message in each `NotificationMessage`
  against `Message.xsd`, and each document in that message's `Payload` against the schema that
  declares it. `Notification.xsd` imports no schema that declares the message, so a `Notify` is
  valid on its own whatever message it carries. A `NotificationMessages`, the list of past
  notifications that Get Notifications returns, is opened the same way.
- A `Notify`, a `NotificationMessages` or a `ResponseMessage` is never a submission, so for the
  payloads it carries `check` skips the checks that only a submission needs: the fields a
  requirement table marks required (`missing-required-field`), the payloads RTC+B withdrew
  (`withdrawn-payload`), and the price, curve, quantity, AS Only Offer and COP state-of-charge
  rules from ERCOT's market documents (`price-below-floor`, `price-above-cap`, `curve-shape`,
  `quantity-below-minimum`, `as-only-offer-type`, `cop-soc-order`).
- For a bare payload, `check` reads one that carries a `status` as a reply or notification and
  skips the same checks for it. This covers a BidSet notification on its own, such as the one
  Offer and Bid Set Acceptance shows.
- The other rules apply as to any document: the values a requirement table bounds or lists,
  times (`hour-24`, `utc-offset`, `trade-date-mismatch`), intervals, curve styles and MW
  precision.
- Header/Verb is checked against the enumeration in `Message.xsd` only. `Created` fails it
  ([D015](discrepancies.md#d015)); `create` passes, although ERCOT says notification messages use
  past-tense verbs ([D045](discrepancies.md#d045)).
- [ERCOT's samples, checked](#ercots-samples-checked) gives the report on each of ERCOT's own
  samples of a notification.

## Notices, alerts and other pushes

The reference starts from the list on ERCOT's Notifications page. ERCOT's pages describe more
pushes to the same listener:

- Notices and alerts. The
  [MMS System-Generated Notices](https://developer.ercot.com/applications/ews/Notifications%20Messages/Notices%20and%20Alerts/MMS%20System-Generated%20Notices/)
  and
  [Operator notices](https://developer.ercot.com/applications/ews/Notifications%20Messages/Notices%20and%20Alerts/Operator%20notices/)
  pages give their verb and noun (`created` and `Alert`; an operator's cancellation is
  `canceled`). ERCOT's samples of a notice carry an `Event` (`ErcotEvents.xsd:21`) as the
  payload, and the
  [Notices and Alerts](https://developer.ercot.com/applications/ews/Notifications%20Messages/Notices%20and%20Alerts/Notices%20and%20Alerts/)
  page says "Event container is used to hold Alerts and Notices." The EMS and NMMS
  System-Generated Notices pages say their notices reach listeners too, without giving a verb or
  noun.
- Resource parameters. After it validates a `ResParametersSet` (`ErcotTransactions.xsd:24`),
  ERCOT sends a notification with the verb `changed` that gives each request's status
  ([Resource Parameter Transaction Service](https://developer.ercot.com/applications/ews/Resource%20Parameter%20Transaction%20Service/#interfaces-provided)).
- Verbal Dispatch Instructions. ERCOT acknowledges a change to `VDIs`
  (`ErcotTransactions.xsd:25`) with a notification sent with the verb `reply`, whose reply part
  says "Acknowledged"
  ([Verbal Dispatch Instructions](https://developer.ercot.com/applications/ews/Verbal%20Dispatch%20Instructions/#interfaces-provided)).
- Test notifications.
  [Request Test Notification](https://developer.ercot.com/applications/ews/Utility%20Interface%20Messages/Request%20Test%20Notification/)
  asks ERCOT to send one: "The payload provided on the request will then be used as the
  notification payload."
- [Get Notifications](https://developer.ercot.com/applications/ews/Get%20Notifications/) fetches
  past notifications instead: "This interface is used to retrieve notifications for previously
  submitted market transactions for the nouns BidSet, ResParametersSet and VDIs." The reply's
  payload is a `NotificationMessages` (`ErcotGetNotifications.xsd:35`) that holds them as
  ResponseMessages, with its content left unchecked: `xs:any` (`ErcotGetNotifications.xsd:38`).

## The verb

ERCOT's
[Message Header](https://developer.ercot.com/applications/ews/Services%20Organization/#message-header)
section says notification messages use past-tense verbs, and names `created`, `changed`,
`canceled` and `closed`. It adds "Implementations should treat verbs 'update' and 'updated' as
synonyms to 'change' and 'changed'." The sequence diagrams on the Market Transaction Service,
Resource Parameter Transaction Service and Verbal Dispatch Instructions pages label their
validation results "updated" or "Updated".

[Header/Verb](#headerverb) gives every verb ERCOT gives a notification, and where. Those outside
the convention:

- The Confirmed and Unconfirmed Trades tables write `Created`. The enumeration in `Message.xsd`
  has no capitalised value, so a message carrying it fails validation
  ([D015](discrepancies.md#d015)).
- The Wind Generation Forecast and Solar Generation Forecast tables write `create`. The
  enumeration allows it, but it is not past tense ([D045](discrepancies.md#d045)).
- The Verbal Dispatch Instructions page sends its acknowledgement with `reply`, which the
  enumeration allows.

No sample of ERCOT's shows the header of any of these notifications. A listener should route a
notification on Header/Noun rather than on the verb; where it reads the verb, it should take
`create` as `created` and, as ERCOT says, `updated` as `changed`.

## Reference

<!-- notifications:start -->
<!-- Written by scripts/build_notifications.py. -->

### The list

ERCOT's [Notifications](https://developer.ercot.com/applications/ews/Notifications/#message-specifications) page lists 19 notifications, each with a page of its own. 17 of the pages give the message a notification arrives in as a table of Header/Verb, Header/Noun and Payload; Offer and Bid Set Acceptance and Offer and Bid Set Errors show only a sample payload. Confirmed and Unconfirmed Trades has 4 tables.

Payload is the row as the page writes it. Container and Element give where ERCOT's schemas declare what that row names.

| Notification | Header/Verb | Header/Noun | Payload | Container | Element |
|---|---|---|---|---|---|
| [Offer and Bid Set Acceptance](https://developer.ercot.com/applications/ews/Notifications%20Messages/Offer%20and%20Bid%20Set%20Acceptance/) | no table | | | | |
| [Offer and Bid Set Errors](https://developer.ercot.com/applications/ews/Notifications%20Messages/Offer%20and%20Bid%20Set%20Errors/) | no table | | | | |
| [Confirmed and Unconfirmed Trades](https://developer.ercot.com/applications/ews/Notifications%20Messages/Confirmed%20and%20Unconfirmed%20Trades/) | `Created` | `UnconfirmedTrades` | `Payload UnconfirmedTrades` | `UnconfirmedTrades` (`ErcotAwards.xsd:32`) |  |
|  | `Created` | `ConfirmedTrades` | `Payload ConfirmedTrades` | `ConfirmedTrades` (`ErcotAwards.xsd:33`) |  |
|  | `canceled` | `UnconfirmedTrades` | `Payload UnconfirmedTrades` | `UnconfirmedTrades` (`ErcotAwards.xsd:32`) |  |
|  | `canceled` | `ConfirmedTrades` | `Payload ConfirmedTrades` | `ConfirmedTrades` (`ErcotAwards.xsd:33`) |  |
| [Energy Offer Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/Energy%20Offer%20Awards/) | `created` | `AwardedEnergyOffer` | `Payload/AwardSet AwardedEnergyOffer` | `AwardSet` (`ErcotAwards.xsd:22`) | `AwardedEnergyOffer` (`ErcotAwardTypes.xsd:71`) |
| [DAM Energy-Only Offer Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/DAM%20Energy-Only%20Offer%20Awards/) | `created` | `AwardedEnergyOnlyOffer` | `Payload/AwardSet AwardedEnergyOnlyOffer` | `AwardSet` (`ErcotAwards.xsd:22`) | `AwardedEnergyOnlyOffer` (`ErcotAwardTypes.xsd:72`) |
| [DAM Energy Bid Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/DAM%20Energy%20Bid%20Award/) (page title: DAM Energy Bid Award) | `created` | `AwardedEnergyBid` | `Payload/AwardSet AwardedEnergyBid` | `AwardSet` (`ErcotAwards.xsd:22`) | `AwardedEnergyBid` (`ErcotAwardTypes.xsd:70`) |
| [Ancillary Service Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/Ancillary%20Service%20Awards/) | `created` | `AwardedAS` | `Payload/AwardSet AwardedAS` | `AwardSet` (`ErcotAwards.xsd:22`) | `AwardedAS` (`ErcotAwardTypes.xsd:68`) |
| [CRR Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/CRR%20Awards/) | `created` | `AwardedCRR` | `Payload/AwardSet AwardedCRR` | `AwardSet` (`ErcotAwards.xsd:22`) | `AwardedCRR` (`ErcotAwardTypes.xsd:69`) |
| [PTP Obligation Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/PTP%20Obligation%20Awards/) | `created` | `AwardedPTPObligation` | `Payload/AwardSet AwardedPTPObligation` | `AwardSet` (`ErcotAwards.xsd:22`) | `AwardedPTPObligation` (`ErcotAwardTypes.xsd:73`) |
| [Ancillary Service Only Offer Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/Ancillary%20Service%20Only%20Offer%20Awards/) | `created` | `AwardedASOnlyOffer` | `Payload/AwardSet AwardedASOnlyOffer` | `AwardSet` (`ErcotAwards.xsd:22`) | `AwardedASOnlyOffer` (`ErcotAwardTypes.xsd:75`) |
| [Ancillary Service Obligations](https://developer.ercot.com/applications/ews/Notifications%20Messages/Ancillary%20Service%20Obligations/) | `created` | `ASObligationsAdvisory or ASObligationsFinal` | `Payload/ ASObligations` | `ASObligations` (`ErcotAwards.xsd:41`) |  |
| [Outage Notifications](https://developer.ercot.com/applications/ews/Notifications%20Messages/Outage%20Notifications/) | `changed` | `OutageSet` | `Payload/ OutageStateChange` | `OutageStateChange` (`ErcotOutages.xsd:35`) |  |
| [Startup/Shutdown Instructions](https://developer.ercot.com/applications/ews/Notifications%20Messages/Startup_Shutdown%20Instructions/) | `created` | `StartupShutdownInstructions` | `Payload/ StartupShutdownInstructions` | `StartupShutdownInstructions` (`ErcotAwards.xsd:34`) |  |
| [Wind Generation Forecast](https://developer.ercot.com/applications/ews/Notifications%20Messages/Wind%20Generation%20Forecast/) | `create` | `WindForecastData` | `Payload/ ForecastPayload` | `ForecastPayload` (`ErcotForecast.xsd:15`) |  |
| [DAM Ancillary Service Offer Insufficiency Report](https://developer.ercot.com/applications/ews/Notifications%20Messages/DAM%20Ancillary%20Service%20Offer%20Insufficiency%20Report/) | `created` | `InsufficiencyReport` | `Payload/ InsufficiencyReports` | `InsufficiencyReports` (commented out at `ErcotAwards.xsd:50`) |  |
| [End of Adjustment Period Results](https://developer.ercot.com/applications/ews/Notifications%20Messages/End%20of%20Adjustment%20Period%20Results/) | `created` | `EndAdjPeriod` | `Payload/ BidSet/OutputSchedule` | `BidSet` (`ErcotTransactions.xsd:26`) | `OutputSchedule` (`ErcotTransactionTypes.xsd:76`) |
| [Two Hour Warning Results](https://developer.ercot.com/applications/ews/Notifications%20Messages/Two%20Hour%20Warning%20Results/) | `created` | `TwoHrNotif` | `Payload/ BidSet/OutputSchedule` | `BidSet` (`ErcotTransactions.xsd:26`) | `OutputSchedule` (`ErcotTransactionTypes.xsd:76`) |
| [DAM Phase II Validation Results](https://developer.ercot.com/applications/ews/Notifications%20Messages/DAM%20Phase%20II%20Validation%20Results/) | `canceled` | `P2ValidationSet` | `Payload/ BidSet/<BidType>` | `BidSet` (`ErcotTransactions.xsd:26`) | any of its payloads (&lt;BidType&gt;) |
| [Solar Generation Forecast](https://developer.ercot.com/applications/ews/Notifications%20Messages/Solar%20Generation%20Forecast/) | `create` | `SolarForecastData` | `Payload/ ForecastSolarPayload` | `ForecastSolarPayload` (`ErcotSolarQSEForecast.xsd:13`) |  |

### What RTC+B changed

From ERCOT's [Document Revisions](https://developer.ercot.com/applications/ews/Document%20Revisions/) page, the notification pages, and the comments beginning "RTC+B" in the schemas:

- [Ancillary Service Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/Ancillary%20Service%20Awards/): Document Revisions: "AwardedAS: Removed SASM reference"; `ErcotAwardTypes.xsd:103`: SASMid in AwardedAS, commented out after "RTC+B: Removed".
- [Ancillary Service Only Offer Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/Ancillary%20Service%20Only%20Offer%20Awards/): Document Revisions: "Ancillary Service Only Offer Awards: Newly Added"; `ErcotAwardTypes.xsd:75`: AwardedASOnlyOffer in AwardSet, declared after "RTC+B: Addition".
- [Ancillary Service Obligations](https://developer.ercot.com/applications/ews/Notifications%20Messages/Ancillary%20Service%20Obligations/): Document Revisions: "ASObligation: Updated noun to ASObligationsAdvisory and ASObligationsFinal"; `ErcotAwardTypes.xsd:221`: SASMid in ASObligation, commented out after "RTC+B: Removed".
- [DAM Ancillary Service Offer Insufficiency Report](https://developer.ercot.com/applications/ews/Notifications%20Messages/DAM%20Ancillary%20Service%20Offer%20Insufficiency%20Report/): the page says "Info Removed with RTC+B Implementation"; Document Revisions: "Removed DAM Ancillary Service Offer Insufficiency Report"; `ErcotAwards.xsd:50`: InsufficiencyReports, commented out after "RTC+B: Removed".
- [DAM Phase II Validation Results](https://developer.ercot.com/applications/ews/Notifications%20Messages/DAM%20Phase%20II%20Validation%20Results/): Document Revisions: "DAM Phase II Validation: Added ASOnlyOffer"; `ErcotTransactionTypes.xsd:78`: IncDecOffer in BidSet, commented out after "RTC+B: Removed".

### Pushes ERCOT's prose describes

Each verb, with its noun where given, that a sentence on an EWS page gives a notification or notice:

| Page | Verb | Noun |
|---|---|---|
| [Market Transaction Service](https://developer.ercot.com/applications/ews/Market%20Transaction%20Service/#interfaces-provided) | `changed` |  |
| [Market Transaction Service](https://developer.ercot.com/applications/ews/Market%20Transaction%20Service/#interfaces-provided) | `created` | `AwardSet` |
| [Resource Parameter Transaction Service](https://developer.ercot.com/applications/ews/Resource%20Parameter%20Transaction%20Service/#interfaces-provided) | `changed` |  |
| [Verbal Dispatch Instructions](https://developer.ercot.com/applications/ews/Verbal%20Dispatch%20Instructions/#interfaces-provided) | `reply` |  |
| [MMS System-Generated Notices](https://developer.ercot.com/applications/ews/Notifications%20Messages/Notices%20and%20Alerts/MMS%20System-Generated%20Notices/#mms-system-generated-notices) | `created` | `Alert` |
| [Operator notices](https://developer.ercot.com/applications/ews/Notifications%20Messages/Notices%20and%20Alerts/Operator%20notices/#operator-notices) | `created` | `Alert` |
| [Operator notices](https://developer.ercot.com/applications/ews/Notifications%20Messages/Notices%20and%20Alerts/Operator%20notices/#operator-notices) | `canceled` | `Alert` |

### Header/Verb

`Message.xsd:72` declares Header/Verb as an enumeration of 15 values. For each verb ERCOT gives a notification: the line that allows it, the notification pages whose table gives it, the pages whose prose gives it to a push, how many of ERCOT's XML samples carry it in a ResponseMessage header, and the catalogue entries about it.

| Verb | Message.xsd | Notification tables | Prose | ResponseMessage samples | Catalogue |
|---|---|---|---|---|---|
| `canceled` | line 76 | 2 pages, 3 tables | Operator notices | 0 |  |
| `changed` | line 78 | 1 page | Market Transaction Service; Resource Parameter Transaction Service | 2 |  |
| `create` | line 79 | 2 pages: Wind Generation Forecast and Solar Generation Forecast |  | 0 | [D045](discrepancies.md#d045) |
| `Created` | not allowed | 1 page, 2 tables: Confirmed and Unconfirmed Trades |  | 0 | [D015](discrepancies.md#d015) |
| `created` | line 80 | 12 pages | Market Transaction Service; MMS System-Generated Notices; Operator notices | 4 |  |
| `reply` | line 86 |  | Verbal Dispatch Instructions | 4 |  |

No XML sample of ERCOT's carries `Created` or `create` in a ResponseMessage header.

### ERCOT's samples, checked

What `ercot-ews-check check` reports on each of ERCOT's 26 distinct samples of a notification: each XML sample on a notification page; each `Notify`, or `ResponseMessage` with a past-tense verb, on another EWS page; and each file in api-specs `ews/examples` whose root a table above names as a payload.

Sample is the document element, with the verb and noun of the first message header. Some samples are excerpts whose namespace prefixes are declared outside what the page shows, or that hold placeholders; for those, `not well-formed XML` describes the excerpt as the page shows it.

| Page | Sample | Report | First finding |
|---|---|---|---|
| [Ancillary Service Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/Ancillary%20Service%20Awards/#ancillary-service-awards) | `AwardedAS` | BLOCKED, schema invalid, 1 finding(s) | schema: not well-formed XML: unbound prefix: line 1, column 0 |
| [Ancillary Service Obligations](https://developer.ercot.com/applications/ews/Notifications%20Messages/Ancillary%20Service%20Obligations/#ancillary-service-obligations) | `ASObligations` | OK, schema valid, 0 finding(s) | none |
| [Ancillary Service Only Offer Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/Ancillary%20Service%20Only%20Offer%20Awards/#ancillary-service-only-awards) | `AwardedASOnlyOffer` | BLOCKED, schema invalid, 1 finding(s) | schema: not well-formed XML: not well-formed (invalid token): line 33, column 0 |
| [CRR Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/CRR%20Awards/#crr-awards) | `AwardedCRR` | BLOCKED, schema invalid, 1 finding(s) | schema: not well-formed XML: unbound prefix: line 1, column 0 |
| [Confirmed and Unconfirmed Trades](https://developer.ercot.com/applications/ews/Notifications%20Messages/Confirmed%20and%20Unconfirmed%20Trades/#confirmed-and-unconfirmed-trades) | `UnconfirmedTrades` | BLOCKED, schema invalid, 1 finding(s) | schema: not well-formed XML: mismatched tag: line 3, column 65 |
| [Confirmed and Unconfirmed Trades](https://developer.ercot.com/applications/ews/Notifications%20Messages/Confirmed%20and%20Unconfirmed%20Trades/#confirmed-and-unconfirmed-trades) | `ConfirmedTrades` | BLOCKED, schema invalid, 1 finding(s) | schema: not well-formed XML: mismatched tag: line 3, column 65 |
| [DAM Ancillary Service Offer Insufficiency Report](https://developer.ercot.com/applications/ews/Notifications%20Messages/DAM%20Ancillary%20Service%20Offer%20Insufficiency%20Report/#dam-ancillary-service-offer-insufficiency-report) | `InsufficiencyReports` | BLOCKED, schema invalid, 1 finding(s) | schema: No EWS schema declares &lt;InsufficiencyReports&gt; as a document root. |
| [DAM Energy Bid Award](https://developer.ercot.com/applications/ews/Notifications%20Messages/DAM%20Energy%20Bid%20Award/#dam-energy-bid-award) | `AwardedEnergyBid` | BLOCKED, schema invalid, 1 finding(s) | schema: not well-formed XML: unbound prefix: line 1, column 0 |
| [DAM Energy-Only Offer Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/DAM%20Energy-Only%20Offer%20Awards/#dam-energy-only-offer-awards) | `AwardedEnergyOnlyOffer` | BLOCKED, schema invalid, 1 finding(s) | schema: not well-formed XML: unbound prefix: line 1, column 0 |
| [DAM Phase II Validation Results](https://developer.ercot.com/applications/ews/Notifications%20Messages/DAM%20Phase%20II%20Validation%20Results/#dam-phase-ii-validation-results) | `BidSet` | BLOCKED, schema invalid, 1 finding(s) | schema: No EWS schema declares &lt;BidSet&gt; as a document root. It is in a retired 2007-05 namespace. |
| [End of Adjustment Period Results](https://developer.ercot.com/applications/ews/Notifications%20Messages/End%20of%20Adjustment%20Period%20Results/#end-of-adjustment-period-results) | `BidSet` | BLOCKED, schema invalid, 1 finding(s) | schema: not well-formed XML: unbound prefix: line 7, column 12 |
| [Energy Offer Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/Energy%20Offer%20Awards/#energy-offer-awards) | `AwardedEnergyOffer` | BLOCKED, schema invalid, 1 finding(s) | schema: not well-formed XML: unbound prefix: line 1, column 0 |
| [Offer and Bid Set Acceptance](https://developer.ercot.com/applications/ews/Notifications%20Messages/Offer%20and%20Bid%20Set%20Acceptance/#offer-and-bid-set-acceptance) | `BidSet` | BLOCKED, schema invalid, 1 finding(s) | schema: not well-formed XML: mismatched tag: line 4, column 52 |
| [Offer and Bid Set Errors](https://developer.ercot.com/applications/ews/Notifications%20Messages/Offer%20and%20Bid%20Set%20Errors/#offer-and-bid-set-errors) | `BidSet` | BLOCKED, schema invalid, 1 finding(s) | schema: not well-formed XML: mismatched tag: line 4, column 52 |
| [Outage Notifications](https://developer.ercot.com/applications/ews/Notifications%20Messages/Outage%20Notifications/#outage-notifications) | `OutageStateChange` | BLOCKED, schema invalid, 1 finding(s) | schema: No EWS schema declares &lt;OutageStateChange&gt; as a document root. It has no namespace; EWS documents declare one. |
| [PTP Obligation Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/PTP%20Obligation%20Awards/#ptp-obligation-awards) | `AwardedPTPObligation` | BLOCKED, schema invalid, 1 finding(s) | schema: not well-formed XML: unbound prefix: line 1, column 0 |
| [Solar Generation Forecast](https://developer.ercot.com/applications/ews/Notifications%20Messages/Solar%20Generation%20Forecast/#solar-generation-forecast) | `ForecastSolarPayload` | BLOCKED, schema invalid, 1 finding(s) | schema: not well-formed XML: mismatched tag: line 15, column 2 |
| [Startup/Shutdown Instructions](https://developer.ercot.com/applications/ews/Notifications%20Messages/Startup_Shutdown%20Instructions/#startupshutdown-instructions) | `StartupShutdownInstructions` | OK, schema valid, 0 finding(s) | none |
| [Wind Generation Forecast](https://developer.ercot.com/applications/ews/Notifications%20Messages/Wind%20Generation%20Forecast/#wind-generation-forecast) | `ForecastPayload` | OK, schema valid, 0 finding(s) | none |
| [Notices and Alerts](https://developer.ercot.com/applications/ews/Notifications%20Messages/Notices%20and%20Alerts/Notices%20and%20Alerts/#notices-and-alerts) | `Event` | OK, schema valid, 0 finding(s) | none |
| [Operator notices](https://developer.ercot.com/applications/ews/Notifications%20Messages/Notices%20and%20Alerts/Operator%20notices/#operator-notices) | `ResponseMessage` (`created` `Alert`) | OK, schema valid, 0 finding(s) | none |
| [Operator notices](https://developer.ercot.com/applications/ews/Notifications%20Messages/Notices%20and%20Alerts/Operator%20notices/#operator-notices) | `ResponseMessage` (`created` `Alert`) | OK, schema valid, 0 finding(s) | none |
| [Get Notifications](https://developer.ercot.com/applications/ews/Get%20Notifications/#message-specification) | `NotificationMessages` (`changed` `BidSet`) | BLOCKED, schema invalid, 1 finding(s) | schema: &lt;IncDecOffer&gt; is not an element of &lt;BidSet&gt;. |
| [Appendix E: SOAP Examples](https://developer.ercot.com/applications/ews/Appendices/Appendix%20E_%20SOAP%20Examples/) | `Notify` (`changed` `BidSet`) | BLOCKED, schema invalid, 1 finding(s) | schema: No EWS schema declares &lt;ResponseMessage&gt; as a document root. It is in a retired 2007-05 namespace. |
| [Appendix H: DST XML Examples](https://developer.ercot.com/applications/ews/Appendices/Appendix%20H_%20DST%20XML%20Examples/) | `ResponseMessage` (`created` `Alert`) | OK, schema valid, 0 finding(s) | none |
| [api-specs ews/examples/AwardedASOnly-Example.xml](https://github.com/ercot/api-specs/blob/7e785be50f0b0e5462f7d0e700ba82289f25390e/ews/examples/AwardedASOnly-Example.xml) | `AwardSet` | OK, schema valid, 0 finding(s) | none |

### Catalogue entries

Entries in the catalogue about notification pages:

- [D011](discrepancies.md#d011): Rejected-bid samples write &lt;status&gt;ERROR&lt;/status&gt;; the enumeration has ERRORS
- [D015](discrepancies.md#d015): Several request and notification tables give Header/Verb capitalised (Get, Change, Cancel, Reply, Created); the enumeration is lower case
- [D021](discrepancies.md#d021): The Acknowledge table names TimeStamp; Notification.xsd declares Timestamp
- [D022](discrepancies.md#d022): Wind Generation Forecast lists statistic values AVG, MIN, MAX, SDV; the schema allows SAMPLE, MEAN, SD, ME, MAE, RMS
- [D023](discrepancies.md#d023): Wind Generation Forecast says WGRs can submit an LTWPF; no interface or type exists for it
- [D032](discrepancies.md#d032): Some samples use the 2007-05 ews namespace; the schemas declare 2007-06
- [D038](discrepancies.md#d038): The Energy-Only Offer award pages show the AwardedEnergyOffer diagram (resource, startType, combinedCycleName); AwardedEnergyOnlyOffer holds awardedMWh, spp, bidId and sp
- [D043](discrepancies.md#d043): The Solar Generation Forecast diagram gives AnalogValue the base type xs:float; the schema's base type is xs:decimal
- [D045](discrepancies.md#d045): Wind and Solar Generation Forecast tables give Header/Verb create; notification verbs are documented as past tense
<!-- notifications:end -->
