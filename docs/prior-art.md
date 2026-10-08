# Prior art

On 8 October 2026 we searched for a public tool that checks ERCOT EWS submissions against ERCOT's
XSDs and the rules in its EWS documentation, from 09:45 to 10:35 CT and in a second pass from 10:45
to 11:40 CT, and found none. This page lists the first pass's queries so that they can be
repeated, and summarises the second.

Every GitHub query ran signed out or from an account with no access to private repositories, so
the results cover public repositories only. The same search looked for public projects that
recreate the look of ERCOT's MMS screens, the subject of the sibling repository
[unofficial-ercot-mms-skin](https://github.com/wattness/unofficial-ercot-mms-skin); those queries
are listed below too, because the totals cover the whole search. Both repositories were public
when the search ran and are left out of the result.

## What exists

- **ERCOT's own.** [ercot/api-specs](https://github.com/ercot/api-specs) publishes ERCOT's API
  specifications, among them the EWS XSDs, WSDLs and example files that this repository vendors.
  [ercot/ews-client](https://github.com/ercot/ews-client) is ERCOT's sample Java client: it builds
  a RequestMessage, signs it and sends it to ERCOT's test endpoint (MOTE). It carries copies of the
  XSDs and does not validate what it sends. Neither repository has a licence file.
- **Other EWS client code.** Six other public repositories, in C# and Python, contain EWS client
  code. Three submit transactions (a DAM PTPObligation BidSet; outage groups; BidSet create and
  cancel), and three fetch reports, prices or system status. Four carry copies of ERCOT's XSDs.
  None uses them to validate a payload: we searched their sources for the .NET, Java and Python
  schema-validation calls and read their main programs. None applies the requirement tables, time
  rules or size limits in ERCOT's EWS documentation, apart from the few checks described below.
  Two of the six have a licence file (MIT and GPL-3.0), and both only fetch data.
- **Forks.** Seven more repositories are forks of ERCOT's sample client or of an earlier copy of
  it. One has commits of its own, from 2017, that restructure the project; none adds validation.
- **Closest to this tool.** One of the six, created in September 2026, includes a mock EWS
  endpoint for its own tests that rejects a few malformed messages: a payload with no BidSet, an
  unknown QSE or resource, a missing or non-monotonic offer curve, a missing AS price curve, a
  missing or reused nonce and, when enabled, a missing or bad signature. Its client also refuses
  two submissions before sending: a bid or offer curve for an Energy Storage Resource (ESR) sent
  for a resource not set up as one, and a three-part supply offer for an ESR. The nonce and
  signature rules are stated on ERCOT's EWS pages, and the two missing-curve checks overlap rows of
  the requirement tables. It does not use ERCOT's XSDs, and applies no other requirement-table
  rows, time rules or size limits from ERCOT's EWS documentation.
- **General-purpose XML validators.** These can apply ERCOT's XSDs to a document, but not the
  rules in ERCOT's prose. Given a whole RequestMessage, neither a validator nor a client generated
  from the WSDL checks the payload, because `Message.xsd` lets a `Payload` hold any element of
  another namespace unchecked (`xsd:any processContents="skip"`).

## What we searched

The first pass:

| Where | How | Found |
|---|---|---|
| GitHub repositories | `gh search repos`: 42 queries on names, descriptions and topics, 18 on README text | 1,278 repositories |
| GitHub code | `gh search code` (GitHub's REST code search): 45 queries, and 13 probes of the index's coverage | 2,591 repositories with a match; 87 with the query terms as whole words |
| Repository contents | the README and the full file list of each of the 1,278 repositories | 1,140 READMEs (138 repositories have none); 1,255 file lists (23 repositories are empty) |
| npm | registry search, 5 queries | 10 packages for `ercot`; none about EWS |
| PyPI | project names containing `ercot`, out of 908,766 | 5 projects; none about EWS |
| Hugging Face | Spaces, models and datasets matching `ercot` | 1 Space, 1 model, 6 datasets; none about EWS |

The second pass ran 261 more GitHub searches (topics, repositories, commits, issues and code). It
listed every non-fork repository that GitHub's repository search returns for ERCOT in a name,
description or README (2,165), and read the READMEs (890 fetched) and file lists (891 fetched) of
the 894 that the first pass had not scanned: no README uses EWS, QSE, SOAP, XSD or MMS as a whole
word, and no file list holds an `Ercot*.xsd` or `Nodal.wsdl` file. It also looked beyond GitHub's
repository and code search: gists (122 reported for `ercot`; none of the 115 that could be read is
about EWS or the MMS), an archive of deleted repositories, other code hosts, other package
registries and a web search engine. It found nothing that changes the result; the one deleted EWS
repository found in the archive is a copy of ERCOT's sample client, with no validation.

## Method

- **Repository search.** GitHub matches names, descriptions and topics, and README text with
  `--match readme`. The words of a query are combined with AND; a quoted string is a phrase. Forks
  are left out unless `--include-forks true` is given. Each query fetched every result, up to
  GitHub's cap of 1,000.
- **Code search.** GitHub considers default branches only, and files smaller than 384 KB. It also
  matches inside longer identifiers, so a result counted as a signal only when the matched text
  contains the query's terms as whole words.
- **Contents.** For each repository that repository search returned, we fetched the README and the
  full file list, and flagged whole-word mentions of EWS, External Web Services, eEDS, XSD, WSDL,
  SOAP, BidSet and the offer payload names, MMS, Market Manager, Market Management System and MOTE,
  and file names such as `Ercot*.xsd`, `Nodal.wsdl` and `*ews*`.
- **By hand.** Every repository with one of those flags or a whole-word code match, and others
  that the targeted queries returned, 125 in all, was checked by hand: the matched text, the
  README, the file list and, for anything that looked like EWS work, the source. The source was
  searched for schema-validation calls and for EWS transport and payload names. The other 3,664
  repositories were classified automatically, from what the searches returned, as public-data
  tools or unrelated; that split does not change the result.

## Limits

- Repository search finds a repository only if ERCOT appears in its name, description, topics or
  README. A tool that never names ERCOT there is missed unless code search finds it.
- Code search's index is incomplete. Of 16 public repositories with the word ERCOT in a README or
  source file under 384 KB, it returned nothing for 8, each with `incomplete_results` set, all
  created between November 2025 and 8 October 2026; among them are this repository,
  unofficial-ercot-mms-skin and the closest project described above. Two others created in that
  period are indexed, so the gap is not a simple date cut-off.
- Three code queries stopped at GitHub's cap of 1,000 (C32, C36, C41), and C39 at 300 after a
  time-out; for those four, the results not returned are the lowest ranked. Four others returned
  fewer results than their `total_count` although it was under 1,000 (C01, C21, C24, C30), and
  GitHub did not say which results it left out (`incomplete_results` was false).
- Private repositories, in-house tools and commercial products cannot be seen this way. Some
  other hosts' search needs an account; the second pass reached those only through the web
  search engine, which returns about ten results per query, and the archive.
- PyPI's search page refused automated access, so only project names were checked. npm's search
  matches names, descriptions and keywords, not READMEs.
- Public repositories count whether or not they carry a licence; most of the EWS client code found
  has none.
- Repositories created, published or indexed after 8 October 2026 are not covered.

## Queries

The first pass's queries. `total_count` is GitHub's count on 8 October 2026. The 13 coverage
probes, one `repo:` query per repository, are not listed. To repeat a query, with the GitHub CLI
signed in:

```sh
gh search repos ercot ews --limit 1000 --json fullName,url,description
gh search repos ercot ews --match readme --limit 1000 --json fullName,url,description
gh search code ErcotCommonTypes --limit 1000 --json path,repository,url
gh api -X GET search/repositories -f q='ercot ews' -f per_page=1 --jq .total_count
```

| ID | Searched | Query (`q`) | total_count |
|---|---|---|---:|
| R01 | names, descriptions, topics | `ercot mms` | 1 |
| R02 | names, descriptions, topics | `ercot market manager` | 0 |
| R03 | names, descriptions, topics | `market management system ercot` | 0 |
| R04 | names, descriptions, topics | `ercot ews` | 3 |
| R05 | names, descriptions, topics | `ercot web services` | 2 |
| R06 | names, descriptions, topics | `ercot nodal web services` | 0 |
| R07 | names, descriptions, topics | `ercot xsd` | 1 |
| R08 | names, descriptions, topics | `ercot bid submission` | 0 |
| R09 | names, descriptions, topics | `ercot bidset` | 0 |
| R10 | names, descriptions, topics | `ercot soap` | 1 |
| R11 | names, descriptions, topics | `ercot qse` | 0 |
| R12 | names, descriptions, topics | `ercot offer` | 4 |
| R13 | names, descriptions, topics | `ercot css` | 1 |
| R14 | names, descriptions, topics | `ercot ui` | 2 |
| R15 | names, descriptions, topics | `ercot bid` | 5 |
| R16 | names, descriptions, topics | `ercot submission validator` | 0 |
| R17 | names, descriptions, topics | `ercot` | 666 |
| R18 | topics | `topic:ercot` | 50 |
| R19 | names, descriptions, topics | `ercot wsdl` | 0 |
| R20 | names, descriptions, topics | `ercot validator` | 4 |
| R21 | names, descriptions, topics | `ercot validation` | 4 |
| R22 | names, descriptions, topics | `ercot schema` | 0 |
| R23 | names, descriptions, topics | `ercot xml` | 0 |
| R24 | names, descriptions, topics | `ercot mis` | 8 |
| R25 | names, descriptions, topics | `ercot "market information system"` | 0 |
| R26 | names, descriptions, topics | `ercot certificate` | 1 |
| R27 | names, descriptions, topics | `ercot mote` | 0 |
| R28 | names, descriptions, topics | `ercot nodal` | 9 |
| R29 | names, descriptions, topics | `ercot client` | 9 |
| R30 | names, descriptions, topics | `ercot api` | 38 |
| R31 | names, descriptions, topics | `ercot scraper` | 12 |
| R32 | names, descriptions, topics | `ercot trading` | 20 |
| R33 | names, descriptions, topics | `ercot bidding` | 5 |
| R34 | names, descriptions, topics | `ercot dashboard` | 55 |
| R35 | names, descriptions, topics | `ercot skin` | 1 |
| R36 | names, descriptions, topics | `ercot theme` | 0 |
| R37 | names, descriptions, topics | `ercot "external web services"` | 0 |
| R38 | names, descriptions, topics, with forks | `ercot ews fork:true` | 10 |
| R39 | names, descriptions, topics, with forks | `ercot mms fork:true` | 1 |
| R40 | README text | `ercot ews in:readme` | 6 |
| R41 | README text | `ercot mms in:readme` | 2 |
| R42 | README text | `ercot xsd in:readme` | 3 |
| R43 | README text | `ercot bidset in:readme` | 2 |
| R44 | README text | `ercot "external web services" in:readme` | 1 |
| R45 | README text | `ercot "market manager" in:readme` | 1 |
| R46 | README text | `ercot soap in:readme` | 8 |
| R47 | README text | `ercot wsdl in:readme` | 8 |
| R48 | README text | `ercot qse in:readme` | 13 |
| R49 | README text | `ercot "market management system" in:readme` | 1 |
| R50 | README text | `ercot css in:readme` | 167 |
| R51 | README text | `ercot validator in:readme` | 562 |
| R52 | README text | `ercot "digital certificate" in:readme` | 3 |
| R53 | README text | `ercot "energy offer" in:readme` | 4 |
| R54 | names, descriptions, topics | `ercot figma` | 0 |
| R55 | names, descriptions, topics | `ercot mockup` | 0 |
| R56 | names, descriptions, topics | `ercot clone` | 0 |
| R57 | README text | `ercot validate in:readme` | 560 |
| R58 | README text | `ercot mote in:readme` | 0 |
| R59 | README text | `ercot "web services" in:readme` | 41 |
| R60 | README text | `ercot submission in:readme` | 111 |
| C01 | code | `ErcotCommonTypes` | 101 |
| C02 | code | `ASOnlyOffer` | 12 |
| C03 | code | `EnergyOnlyOffer` | 76 |
| C04 | code | `ThreePartOffer` | 22 |
| C05 | code | `misapi.ercot.com` | 49 |
| C06 | code | `eEDS/EWS` | 43 |
| C07 | code | `Nodal.wsdl` | 25 |
| C08 | code | `BidSet ercot` | 25 |
| C09 | code | `MarketManager ercot` | 4 |
| C10 | code | `"Market Manager" ercot css` | 0 |
| C11 | code | `"Market Manager" ercot extension:css` | 0 |
| C12 | code | `ercot extension:css` | 184 |
| C13 | code | `ercot extension:scss` | 46 |
| C14 | code | `ercot mms extension:html` | 252 |
| C15 | code | `"Market Manager" ercot extension:html` | 0 |
| C16 | code | `nodal/ews/message` | 69 |
| C17 | code | `schema/2007-06/nodal/ews` | 295 |
| C18 | code | `ewsConcrete` | 185 |
| C19 | code | `NodalService.serviceagent` | 34 |
| C20 | code | `ErcotTransactions` | 1 |
| C21 | code | `ercot extension:xsd` | 386 |
| C22 | code | `ercot extension:wsdl` | 65 |
| C23 | code | `ReplayDetection ercot` | 59 |
| C24 | code | `zeep ercot` | 425 |
| C25 | code | `BinarySecurityToken ercot` | 15 |
| C26 | code | `testmisapi.ercot.com` | 9 |
| C27 | code | `IncDecOffer` | 32 |
| C28 | code | `PTPObligation` | 51 |
| C29 | code | `SelfArrangedAS` | 41 |
| C30 | code | `api.ercot.com` | 446 |
| C31 | code | `misapp/GetReports` | 95 |
| C32 | code | `ercot mms` | 15,136 |
| C33 | code | `schema filename:ErcotCommonTypes.xsd` | 10 |
| C34 | code | `definitions filename:Nodal.wsdl` | 16 |
| C35 | code | `EnergyBid ercot` | 98 |
| C36 | code | `ercot xsd validate` | 2,076 |
| C37 | code | `ercot "Market Management System"` | 22 |
| C38 | code | `misapitest.ercot.com` | 2 |
| C39 | code | `ercot ews` | 72,704 |
| C40 | code | `MarketTransactions ercot` | 41 |
| C41 | code | `BidSet validate` | 3,552 |
| C42 | code | `ercot mms extension:tsx` | 19 |
| C43 | code | `ercot mms extension:jsx` | 5 |
| C44 | code | `ercot mms extension:vue` | 0 |
| C45 | code | `ercot extension:less` | 4 |
