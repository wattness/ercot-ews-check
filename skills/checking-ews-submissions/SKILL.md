---
name: checking-ews-submissions
description: Checks ERCOT EWS XML documents (BidSet, ASOnlyOffer, EnergyOnlyOffer, EnergyBid, COP, PTPObligation, RequestMessage, Acknowledge and other EWS messages) against ERCOT's XSDs and the rules in ERCOT's EWS documentation, explains each failure in plain English with the fix, and looks up known discrepancies in ERCOT's documentation by element, value, product or ID. Use when someone asks whether an EWS submission or ERCOT example is valid, why ERCOT rejected one, or whether an ERCOT page or example is wrong.
license: Apache-2.0
compatibility: Needs Python 3.10 or later and the ercot-ews-check command-line tool from github.com/wattness/ercot-ews-check. Works offline once installed.
---

# Checking ERCOT EWS submissions

## Setup

Check whether the tool is installed:

```sh
ercot-ews-check --version
```

If the command is not found, install it into a virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install "git+https://github.com/wattness/ercot-ews-check"
```

Each shell call starts fresh, so call the tool by its path from then on: `.venv/bin/ercot-ews-check`
wherever this skill says `ercot-ews-check` (`.venv\Scripts\ercot-ews-check` on Windows).

## Check a document

```sh
ercot-ews-check explain path/to/document.xml
```

Replace the path with the user's file. The output has one numbered paragraph per finding: what is
wrong, the fix, the ERCOT page the rule comes from, and any catalogue entry that may be related.
Exit status 1 means the document breaks a rule ERCOT states, or ERCOT may change it without an
error; 0 means nothing blocking was found; 2 means a file could not be read. For a structured
report, run `ercot-ews-check check path/to/document.xml --json`.

When you report back:

1. Start with the verdict: blocked, or passes with or without warnings.
2. List errors, then silent changes, then warnings. Quote the element and value involved.
3. Give the fix for each, in the user's terms.
4. A catalogue entry (D001 and so on) next to a finding may be related; it does not show that
   ERCOT is wrong about this document. Run `ercot-ews-check show ID` and compare the entry with
   the finding before you tell the user that an ERCOT page or example is wrong.
5. Do not say the document will be accepted. A clean result means these checks found nothing;
   ERCOT also runs credit and market checks after receipt.

[references/rules.md](references/rules.md) explains each rule ID and its severity.

## Look up a discrepancy

```sh
ercot-ews-check lookup plannedSart
ercot-ews-check show D020
ercot-ews-check reproduce D020
```

`lookup` takes an element, value, product, page name or ID. `show` prints the evidence: ERCOT's
words, the schema rule with file and line, and what to do. `reproduce` checks the entry's minimal
invalid and valid documents.

## Is this ERCOT example wrong?

Save the example to a file and check it as above, then run `ercot-ews-check lookup` with the
failing element name. To list every complete sample on ERCOT's EWS pages that fails ERCOT's own
XSDs:

```sh
ercot-ews-check examples --invalid
```

## Do not

- Do not describe this tool, or its catalogue, as ERCOT's or as endorsed by ERCOT.
- Do not present a warning as a rejection; only errors and silent changes block.
