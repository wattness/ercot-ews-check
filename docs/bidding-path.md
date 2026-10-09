# How a bid travels through ERCOT's External Web Services

**Unofficial.** Not affiliated with or endorsed by ERCOT.

This page draws the path of one BidSet through ERCOT's External Web Services (EWS): the QSE's
Market Participant System builds, signs and sends it; ERCOT validates it in three phases and
answers; notifications and awards reach the QSE's listener later. The names are ERCOT's. Each
numbered element has its source in the table below, and S1 and S2 point to the security note. The
page is drawn from ERCOT's documents, and the security note also from one library's source code;
nothing on it was tested against ERCOT's systems.

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="bidding-path-dark.svg">
  <img src="bidding-path-light.svg" alt="Diagram. The QSE's Market Participant System sends a SOAP envelope over HTTPS with mutual authentication; its header holds wsse:Security with the signer's X.509 certificate and a Signature over the Body, and the Body holds a RequestMessage (create BidSet) whose Payload is one BidSet. At ERCOT's Nodal External Interface (Market Transaction Service), Phase Zero checks message structure and certificates, and a synchronous ResponseMessage returns each bid SUBMITTED with its mRID. The MMS runs Phase One MMS Validation, and a signed Notify to the QSE's listener (Market Participant Notification Service) reports each bid ACCEPTED, PENDING or ERRORS; the listener answers with an Acknowledge. At 07:00 CT the day before the Operating Day, Phase Two MMS Validation runs, and cancellations arrive as a P2ValidationSet. After the close of the market, awards arrive in an AwardSet. Get Notifications fetches notifications already sent.">
</picture>

## Sources

ERCOT's EWS pages are cited by section. `tests/test_docs.py` checks every quote from them against
this repository's copy of the developer portal's search index
(`vendor/ercot/developer.ercot.com/search/search_index.json`, retrieved 2026-10-07). Schema and
WSDL lines are in the files vendored from [ercot/api-specs](https://github.com/ercot/api-specs) at
commit 7e785be (`vendor/ercot/api-specs/ews/`). NP4-450-M is ERCOT's MMS Market Submission
Validation Rules, version 3.2, cited by section and by the page its table of contents gives; it is
not vendored here.

| # | In the diagram | ERCOT's words, and where |
|---|---|---|
| 1 | HTTPS with mutual authentication | "Mutual authentication with SSL, using the server certificate as well as the client certificate, so that both parties can authenticate to each other." ([Services Organization: Secure the Transport layer](https://developer.ercot.com/applications/ews/Services%20Organization/#secure-the-transport-layer)) |
| 2 | `wsse:Security` in the SOAP header: the signer's certificate, and a `Signature` over the Body | "Sign all SOAP messages, using Web Services Security Standards and its X.509 Certificate Token Profile" ([Services Organization: Secure SOAP messages](https://developer.ercot.com/applications/ews/Services%20Organization/#secure-soap-messages)); "The first element in this section is the signer's X.509 certificate" and "This one points to the entire message body" ([Appendix D: Annotated SOAP Message](https://developer.ercot.com/applications/ews/Appendices/Appendix%20D_%20Annotated%20SOAP%20Message/), sections 2 and 4) |
| 3 | `RequestMessage` `Header`: `Verb` create, `Noun` BidSet, `ReplayDetection` (`Nonce`, then `Created`), `Revision`, `Source`, `UserID` | `ReplayDetectionType` and `HeaderType` in [`Message.xsd`, lines 64 to 102](../vendor/ercot/api-specs/ews/xsds/Message.xsd#L64-L102); "Header/Verb create/get/change/cancel Header/Noun BidSet" ([Market Transaction Service: Interfaces Required](https://developer.ercot.com/applications/ews/Market%20Transaction%20Service/#interfaces-required)); "A unique number that would not be repeated by the Market Participant within the period of at least a day." and "ERCOT will verify that this value is consistent with the Market Participant as identified by the certificate" ([Services Organization: Message Header](https://developer.ercot.com/applications/ews/Services%20Organization/#message-header)). The interface tables leave out `ReplayDetection` and `Revision`, which the schema requires: [D017](discrepancies.md#d017). |
| 4 | `Payload`: one `BidSet`, its `tradingDate`, then one product type; under 3 MB before compression | `MarketRequest` and `BidSet` in [`ErcotTransactionTypes.xsd`, lines 56 to 97](../vendor/ercot/api-specs/ews/xsds/ErcotTransactionTypes.xsd#L56-L97): `tradingDate`, then an `xs:choice` of product types; "Note that only one BidSet is permitted for a given message, and all transactions within the BidSet must be for the same trading date." and "In the cases of payloads that would otherwise exceed 1 megabyte, the payloads should be zipped, base64 encoded and stored within the Payload/Compressed tag" ([Market Transaction Service: Interfaces Required](https://developer.ercot.com/applications/ews/Market%20Transaction%20Service/#interfaces-required)); "must be limited to a single Product Type (Bid Type)" and "must be less than 3 Mb in size(Pre-compression)" ([Services Organization: Web Service Design Assumptions and Limitations](https://developer.ercot.com/applications/ews/Services%20Organization/#web-service-design-assumptions-and-limitations)); "The Gnu Zip compression shall be used" ([Services Organization: Payload Structures](https://developer.ercot.com/applications/ews/Services%20Organization/#payload-structures)) |
| 5 | `RequestMessage`, create BidSet, to the WSDL operation `MarketTransactions` | "Market participant sends a RequestMessage for 'create BidSet' with an initial BidSet to ERCOT for a specific market" ([Market Transaction Service: Interfaces Provided](https://developer.ercot.com/applications/ews/Market%20Transaction%20Service/#interfaces-provided)); operation `MarketTransactions` of port type `Operations`, with input `RequestMessage`, in [`Nodal.wsdl`, lines 8 to 22](../vendor/ercot/api-specs/ews/wsdls/Nodal.wsdl#L8-L22). The pages do not say which operation carries a BidSet; the diagram matches the Market Transaction Service to `MarketTransactions` by name. Appendix B describes the WSDL as "a set of operations for servicing all market requests" ([Appendix B: WSDL for Market Requests](https://developer.ercot.com/applications/ews/Appendices/Appendix%20B_WSDL%20for%20Market%20Requests/)). |
| 6 | Phase Zero, at the External Interface: message structure and certificate checks | NP4-450-M §8.1 (p. 30), "Prior to Receipt by MMS – Phase Zero External Interface (TIBCO) Validation": submissions that "passed the simple XML message structure and certificate security validations, will be marked as ‘received.’" ([NP4-450-M](https://www.ercot.com/mp/data-products/data-product-details?id=NP4-450-M)); "BidSet is syntax scanned, where only basic validity checks are performed." ([Market Transaction Messages: Error Handling](https://developer.ercot.com/applications/ews/Market%20Transaction%20Messages/Error%20Handling/#error-handling)) |
| 7 | `ResponseMessage`, synchronous: `ReplyCode` OK, ERROR or FATAL; each bid SUBMITTED, with its mRID | "ERCOT performs a simple syntax scan and typically sends a ResponseMessage with ReplyCode=OK." and "each bid/offer/trade/schedule will identify a 'SUBMITTED' status and an mRID value" and "This reply is synchronous." ([Market Transaction Service: Interfaces Provided](https://developer.ercot.com/applications/ews/Market%20Transaction%20Service/#interfaces-provided)); "Reply code, success=OK, error=ERROR or FATAL" ([Market Transaction Service: Interfaces Required](https://developer.ercot.com/applications/ews/Market%20Transaction%20Service/#interfaces-required)); output `ResponseMessage` and fault `FaultMessage` in [`Nodal.wsdl`, lines 11 to 22](../vendor/ercot/api-specs/ews/wsdls/Nodal.wsdl#L11-L22). For related submissions, the QSE should "wait for the synchronous response from ERCOT before submitting the second create/change/cancel BidSet request" ([Services Organization: Web Service Design Assumptions and Limitations](https://developer.ercot.com/applications/ews/Services%20Organization/#web-service-design-assumptions-and-limitations)). |
| 8 | To the MMS; Phase One MMS Validation, asynchronous | NP4-450-M §8.2 (p. 30): "Immediately upon receipt by the MMS, each submission is subjected to a series of validation rules." and "These rules check for the proper XML format of the submission, proper QSE permission to make the submission, and other content criteria based on the Protocols." ([NP4-450-M](https://www.ercot.com/mp/data-products/data-product-details?id=NP4-450-M)); "A more thorough validity check is performed asynchronously by the Market Management System (MMS)" ([Market Transaction Messages: Error Handling](https://developer.ercot.com/applications/ews/Market%20Transaction%20Messages/Error%20Handling/#error-handling)); "This could take several minutes." ([Market Transaction Service: Interfaces Provided](https://developer.ercot.com/applications/ews/Market%20Transaction%20Service/#interfaces-provided)) |
| 9 | `Notify` with the BidSet, each bid ACCEPTED, PENDING or ERRORS; signed by ERCOT; HTTPS to the listener's URL, port 443 | "A notification message (using verb=changed) is sent to the notification interface provided by the Market Participant." and "The status of the bids within the BidSet will indicate whether the bid/offer/trade/schedule was PENDING/ACCEPTED or had ERRORS." ([Market Transaction Service: Interfaces Provided](https://developer.ercot.com/applications/ews/Market%20Transaction%20Service/#interfaces-provided)); "ERCOT will send notifications to port 443 of the specified URL using an HTTPS connection." and "ERCOT will sign the SOAP message, where the signature can be verified using the ERCOT public key." ([Notifications: Message Specifications](https://developer.ercot.com/applications/ews/Notifications/#message-specifications)); operation `Notify` of port type `NotificationConsumer` in [`Notification.wsdl`, lines 42 to 60](../vendor/ercot/api-specs/ews/wsdls/Notification.wsdl#L42-L60). The sample on the Get Notifications page shows notified BidSets with the verb changed and with the verb created, so the diagram leaves the verb out. |
| 10 | `Acknowledge`: `ReplyCode` OK or ERROR; need not be signed | "ReplyCode OK or ERROR" ([Notifications: Interfaces Required](https://developer.ercot.com/applications/ews/Notifications/#interfaces-required)); "The 'Acknowledge' message does not need to be signed." ([Notifications: Message Specifications](https://developer.ercot.com/applications/ews/Notifications/#message-specifications)); `Acknowledge` in [`Notification.xsd`, lines 42 to 50](../vendor/ercot/api-specs/ews/xsds/Notification.xsd#L42-L50). The page's table names its timestamp TimeStamp, where the schema declares Timestamp: [D021](discrepancies.md#d021). |
| 11 | Phase Two MMS Validation: at 07:00 CT the day before the Operating Day, or at receipt after 07:00; it adds rules such as credit exposure | NP4-450-M §8.3 (p. 30): "At 0700 on the day before the Operating Day, all Market Participant submissions for the applicable Operating Day that were submitted prior to 0700 that have passed Phase One validation are subjected to a second series of validation rules, referred to as Phase Two." and "Any submission for the applicable Operating Day made after 0700 in the Day-Ahead will be subjected to both Phase One and Phase Two Validations." Market Participants "should avoid making any submissions for the next Operating Day" while Phase Two is prepared and runs, "generally between 6:55am and 7:05am". Among the rules used "in Phase Two only": "Credit Exposure vs. available credit" ([NP4-450-M](https://www.ercot.com/mp/data-products/data-product-details?id=NP4-450-M)) |
| 12 | `Notify`, verb canceled, noun P2ValidationSet | "Header/Verb canceled Header/Noun P2ValidationSet" and "The payload will hold the Bid Validation results (bid cancellations only) for the specified trading date." ([Notifications Messages: DAM Phase II Validation Results](https://developer.ercot.com/applications/ews/Notifications%20Messages/DAM%20Phase%20II%20Validation%20Results/#dam-phase-ii-validation-results)) |
| 13 | The DAM submission deadline, normally 10:00 CT; after the close of the market, `Notify`, verb created, with an `AwardSet` payload | NP4-450-M §2.1 (pp. 2 to 5): "until the DAM submission deadline (normally 1000)" ([NP4-450-M](https://www.ercot.com/mp/data-products/data-product-details?id=NP4-450-M)); "After the close of the market, awards and obligations are determined." and "The notification message uses verb='created', noun='AwardSet'." ([Market Transaction Service: Interfaces Provided](https://developer.ercot.com/applications/ews/Market%20Transaction%20Service/#interfaces-provided)); "Header/Verb created Header/Noun AwardedEnergyOffer" and "Payload/AwardSet AwardedEnergyOffer" ([Notifications Messages: Energy Offer Awards](https://developer.ercot.com/applications/ews/Notifications%20Messages/Energy%20Offer%20Awards/#energy-offer-awards)) |
| 14 | `get BidSetNotifications` (Get Notifications): notifications up to 4 days old, 24 hours per query; the reply holds `NotificationMessages` | "Service supports querying historical notifications upto 4 days old and is based on transaction submitted time." and "A single query cannot span more than 24hours." ([Get Notifications](https://developer.ercot.com/applications/ews/Get%20Notifications/)); "Header/Noun BidSetNotifications/ ResParameterSetNotifications/ VDIsNotifications" ([Get Notifications: Message Specification](https://developer.ercot.com/applications/ews/Get%20Notifications/#message-specification)); `NotificationQuery` and `NotificationMessages` in [`ErcotGetNotifications.xsd`, lines 16 to 40](../vendor/ercot/api-specs/ews/xsds/ErcotGetNotifications.xsd#L16-L40) |

The lifelines take their names from the sequence diagram on the Market Transaction Service page,
whose participants are "Market Participant Notification Service", "Market Participant System" and
"ERCOT Nodal External Interface"
([Market Transaction Service: Interfaces Provided](https://developer.ercot.com/applications/ews/Market%20Transaction%20Service/#interfaces-provided)).
MMS is the "Market Management System, a system implemented at ERCOT"
([Introduction: Definitions, Acronyms, and Abbreviations](https://developer.ercot.com/applications/ews/Introduction/#definitions-acronyms-and-abbreviations)).
The QSE's listener is the "listener interface for the receipt of notification messages" that each
Market Participant provides ([Notifications](https://developer.ercot.com/applications/ews/Notifications/)).

## Security note

### S1. ERCOT signs with RSA-SHA1, which SignXML refuses by default

ERCOT's pages say: "ERCOT will sign outbound messages using SHA-1/RSA and strongly recommends its
use by market participants for signing messages."
([Services Organization: Secure SOAP messages](https://developer.ercot.com/applications/ews/Services%20Organization/#secure-soap-messages)).
Appendix D's annotated message, the one signed sample on the pages, names
"http://www.w3.org/2000/09/xmldsig#rsa-sha1" as its SignatureMethod and
"http://www.w3.org/2000/09/xmldsig#sha1" as the DigestMethod of each reference
([Appendix D: Annotated SOAP Message](https://developer.ercot.com/applications/ews/Appendices/Appendix%20D_%20Annotated%20SOAP%20Message/),
sections 3 to 5). Notifications are among ERCOT's outbound messages: "ERCOT will sign the SOAP
message, where the signature can be verified using the ERCOT public key."
([Notifications: Message Specifications](https://developer.ercot.com/applications/ews/Notifications/#message-specifications)).

[SignXML](https://github.com/XML-Security/signxml) 5.1.0, the release current on PyPI on 9 October
2026, leaves every SHA-1 algorithm out of its verifier's defaults.
`SignatureConfiguration.signature_methods` defaults to
`frozenset(sm for sm in SignatureMethod if "SHA1" not in sm.name)`, and `digest_algorithms` to the
same filter over `DigestAlgorithm`
([`signxml/verifier.py`, lines 67 to 74](https://github.com/XML-Security/signxml/blob/v5.1.0/signxml/verifier.py#L67-L74)).
A signature or digest outside those sets raises `InvalidInput`, "forbidden by configuration"
([lines 342 to 348](https://github.com/XML-Security/signxml/blob/v5.1.0/signxml/verifier.py#L342-L348)),
and the library's documentation says its SHA-1 algorithms are "included for legacy compatibility
only and disabled by default"
([`signxml/algorithms.py`, lines 124 to 125](https://github.com/XML-Security/signxml/blob/v5.1.0/signxml/algorithms.py#L124-L125)).

So a listener that checks ERCOT's notifications with SignXML's defaults rejects a signature made as
ERCOT describes. To accept it, the listener has to name `SignatureMethod.RSA_SHA1` and
`DigestAlgorithm.SHA1` in the `SignatureConfiguration` it verifies ERCOT's messages with. This
follows from the two sources above; it was not tested against ERCOT's systems. For messages the
QSE signs, ERCOT lists the methods that "will be supported for incoming messages", among them
"SHA-256 and SHA-512 with RSA"
([Services Organization: Secure SOAP messages](https://developer.ercot.com/applications/ews/Services%20Organization/#secure-soap-messages)).

### S2. Appendix D writes Created before Nonce

ERCOT asks that "Message headers MUST include a timestamp and a nonce"
([Services Organization: Secure SOAP messages](https://developer.ercot.com/applications/ews/Services%20Organization/#secure-soap-messages)).
In Appendix D they are not in the WS-Security header: "the message body includes an element called
ReplayDetection", inside the message `Header`, and the Body is the first reference the signature
covers
([Appendix D: Annotated SOAP Message](https://developer.ercot.com/applications/ews/Appendices/Appendix%20D_%20Annotated%20SOAP%20Message/),
sections 4 and 8). There Appendix D writes `wsu:Created` before `wsse:Nonce`, while `Message.xsd`
requires `Nonce`, then `Created`, both in the message namespace
([lines 64 to 69](../vendor/ercot/api-specs/ews/xsds/Message.xsd#L64-L69)). Follow the schema.
Catalogue entry [D014](discrepancies.md#d014) has the evidence and a reproducer;
`ercot-ews-check check` reports Appendix D's form, and `Created` before `Nonce` in the message
namespace, as schema errors.
