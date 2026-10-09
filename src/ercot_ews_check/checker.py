"""Check an EWS document: ERCOT's XSDs first, then the rules the XSDs cannot express.

A clean report means nothing was found by these checks against the vendored
schema release. It does not predict acceptance: ERCOT's market system validates
asynchronously, and credit and other checks run after anything done here.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta
from functools import lru_cache
from itertools import pairwise
from pathlib import Path

from ercot_ews_check import (
    constraints,
    discrepancies,
    examples,
    explain,
    hazards,
    market_rules,
    mrid,
    requirements,
    schema,
    sources,
)
from ercot_ews_check import withdrawn as wd
from ercot_ews_check.dst import CENTRAL, trading_date
from ercot_ews_check.namespaces import EWS, MESSAGE, NOTIFICATION, local, q
from ercot_ews_check.submission import check_size
from ercot_ews_check.values import CURVE_STYLE_POINTS, MW_DECIMALS, decimals

ERROR, SILENT, WARNING = "error", "silent", "warning"
BLOCKING = (ERROR, SILENT)

# Structures meant to tile the day: a gap between intervals is suspect, not only an overlap.
MUST_TILE = frozenset({"ResourceStatus", "MinimumEnergy", "StartupCost", "Limits", "ASCapacity"})
# BidSet's payload choice. Sibling payloads each span the day; they are not a timeline.
BIDSET_PAYLOADS = frozenset(
    {"COP", "ThreePartOffer", "OutputSchedule", "CRR", "ASOffer", "EnergyBid", "EnergyOnlyOffer",
     "PTPObligation", "SelfArrangedAS", "EnergyTrade", "CapacityTrade", "ASTrade",
     "DCTieSchedule", "SelfSchedule", "AVP", "RTMEnergyBid", "EFC", "ASOnlyOffer"}
)  # fmt: skip
TIME_FIELDS = ("startTime", "endTime", "expirationTime", "time", "Created", "ending")

PORTAL = "https://developer.ercot.com/applications/ews"
SRC_TIME = f"{PORTAL}/Services%20Organization/#representation-of-time"
SRC_CIM = f"{PORTAL}/Services%20Organization/#use-of-the-iec-cim"
SRC_CONVENTIONS = f"{PORTAL}/Services%20Organization/#other-conventions"
SRC_LIMITS = f"{PORTAL}/Services%20Organization/#web-service-design-assumptions-and-limitations"
SRC_CANCEL = f"{PORTAL}/Market%20Transaction%20Service/#canceling-bids-offers-trades-and-schedules"
SRC_REVISIONS = f"{PORTAL}/Document%20Revisions/"
# ERCOT lists SOAP's syntax rules in its MarkeTrak Developer Guide; the EWS pages do not.
SRC_SOAP = (
    "https://developer.ercot.com/applications/marketrak/MarkeTrak_API_Dev_v1_2/"
    "#71-basic-syntax-rules-of-soap"
)
# ERCOT's MMS Market Submission Validation Rules (NP4-450-M); see market_rules.
SRC_NP4_450 = market_rules.SRC_NP4_450
# Fields a product table calls "Value ignored if provided" that NP4-450 requires in some cases:
# (payload, path) -> (section, NP4-450's words, fix).
IGNORED_BUT_REQUIRED = {
    ("ASOffer", "combinedCycle"): (
        "§2.2",
        "required for Combined Cycle Resources only",
        "Keep it for a Resource in a combined cycle; leave it out otherwise.",
    ),
}


@dataclass(frozen=True)
class Finding:
    rule: str
    severity: str  # error | silent | warning
    message: str
    where: str = ""
    fix: str = ""
    see: tuple[str, ...] = ()  # discrepancy IDs
    source: str = ""  # the ERCOT page the rule comes from

    def __str__(self) -> str:
        at = f" at {self.where}" if self.where else ""
        return f"[{self.severity}] {self.rule}{at}: {self.message}"


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)
    schema: str = schema.UNVERIFIED
    schema_file: str = ""

    @property
    def blocked(self) -> bool:
        """True when any finding is an error or a silent change."""
        return any(f.severity in BLOCKING for f in self.findings)

    def by_rule(self) -> set[str]:
        return {f.rule for f in self.findings}

    def to_dict(self) -> dict:
        return {
            "blocked": self.blocked,
            "schema": self.schema,
            "schema_file": self.schema_file,
            "findings": [asdict(f) for f in self.findings],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def __str__(self) -> str:
        head = "BLOCKED" if self.blocked else ("OK" if not self.findings else "OK with warnings")
        lines = [f"{head}: schema {self.schema}, {len(self.findings)} finding(s)"]
        order = {ERROR: 0, SILENT: 1, WARNING: 2}
        for f in sorted(self.findings, key=lambda f: order.get(f.severity, 3)):
            lines.append(f"  {f}")
            if f.fix:
                lines.append(f"      fix: {f.fix}")
            if f.see:
                lines.append(f"      see: {', '.join(f.see)}")
        return "\n".join(lines)


@lru_cache(maxsize=1)
def _ignored_fields() -> dict[str, frozenset[str]]:
    out = {}
    for page, tag in requirements.PAGE_TO_TAG.items():
        rows = requirements.tables().get(page, {})
        ignored = {
            requirements._fix(p, tag)
            for p, r in rows.items()
            if constraints._IGNORED.search(str(r.get("spec") or ""))
        }
        out[tag] = frozenset(ignored)
    return out


def _see_required(paths) -> tuple[str, ...]:
    return discrepancies.related(
        ("required-field",), elements=[p.rsplit("/", 1)[-1] for p in paths]
    )


def _values_text(rule: constraints.Constraint) -> str:
    """ERCOT's Values cell for a table row; the search index runs the Description cell into it."""
    stated = constraints._STATED.search(rule.source)
    return rule.source[stated.start() :] if stated else rule.source


_np4_450 = market_rules.np4_450


def _texts(root: ET.Element, name: str) -> list[ET.Element]:
    return [el for el in root.iter() if local(el.tag) == name and (el.text or "").strip()]


def _schema_findings(rep: Report, verdict: schema.Verdict) -> None:
    rep.schema, rep.schema_file = verdict.state, verdict.schema
    if verdict.state == schema.UNVERIFIED:
        rep.findings.append(
            Finding("schema-unverified", WARNING, f"Not checked against the XSDs: {verdict.detail}")
        )
        return
    if verdict.state == schema.INVALID and not verdict.errors:
        rep.findings.append(Finding("schema", ERROR, verdict.detail))
    for err in verdict.errors:
        x = explain.explain(err)
        rep.findings.append(Finding("schema", ERROR, x.message, x.where, x.fix, x.see))
    if verdict.unlisted:
        rep.findings.append(
            Finding(
                "schema",
                ERROR,
                f"{verdict.unlisted:,} more schema error(s), not listed; a report lists the "
                f"first {schema.MAX_ERRORS}.",
                fix="Fix the errors listed and check again.",
            )
        )


def _payload_findings(
    rep: Report,
    bidset: ET.Element,
    creating: bool,
    in_message: bool,
    created: datetime | None = None,
) -> None:
    trade_el = bidset.find(q(EWS, "tradingDate"))
    stated_day = _date((trade_el.text or "") if trade_el is not None else "")
    for payload in bidset:
        tag = local(payload.tag)
        if tag == "tradingDate":
            continue
        # Outside a message, a payload carrying a status is a reply or notification.
        submitting = creating and (in_message or payload.find(q(EWS, "status")) is None)
        w = wd.withdrawal_for(tag)
        if submitting and w is not None and not w.may_submit():
            rep.findings.append(
                Finding(
                    "withdrawn-payload",
                    ERROR,
                    w.why_not(),
                    tag,
                    f"Do not submit {tag}.",
                    discrepancies.related(("withdrawn",), elements=(tag,)),
                    SRC_REVISIONS,
                )
            )
            continue
        if submitting:
            for p in market_rules.check_payload(tag, payload, stated_day, created):
                rep.findings.append(
                    Finding(p.rule, p.severity, p.message, p.where, p.fix, p.see, p.source)
                )
        page = requirements.page_for(tag)
        if page is None:
            continue
        present = requirements.paths_in(payload)
        gone = requirements.missing(tag, present) if submitting else ()
        omitted = examples.create_omissions()
        hard = [p for p in gone if (tag, p) not in omitted]
        soft = [p for p in gone if (tag, p) in omitted]
        fip_fop = [p for p in hard if tag == "ThreePartOffer" and p.startswith("EocFipFop/")]
        storage = bool(fip_fop) and market_rules.below_zero(payload)
        if storage:
            hard = [p for p in hard if p not in fip_fop]
        source = f"{PORTAL}/Market%20Transaction%20Messages/{page}/"
        if hard:
            fix = "Add the fields listed."
            if fip_fop and not storage:
                fix += (
                    f" For an Energy Storage Resource, {_np4_450('§2.1')} say FIP and FOP do not"
                    " apply; this check treats an offer as one only when its curve goes below 0 MW."
                )
            rep.findings.append(
                Finding(
                    "missing-required-field",
                    ERROR,
                    f"{tag} lacks {len(hard)} field(s) ERCOT marks required (Y) or key (K): "
                    f"{', '.join(hard)}. The XSD cannot catch this: every payload field is "
                    "minOccurs=0.",
                    tag,
                    fix,
                    (*_see_required(hard), "D007"),
                    source,
                )
            )
        if storage:
            rep.findings.append(
                Finding(
                    "missing-required-field",
                    WARNING,
                    f"{tag} lacks {', '.join(fip_fop)}, which ERCOT's table marks required (Y). "
                    "Its curve goes below 0 MW, so the Resource is an Energy Storage Resource, and "
                    f"{_np4_450('§2.1')} say FIP and FOP for the curve are "
                    '"not applicable to ESRs".',
                    tag,
                    "Leave EocFipFop out only if you have confirmed ERCOT accepts the offer "
                    "without it.",
                    _see_required(fip_fop),
                    SRC_NP4_450,
                )
            )
        for path in soft:
            sample = sources.portal_url(omitted[(tag, path)])
            rep.findings.append(
                Finding(
                    "missing-required-field",
                    WARNING,
                    f"{tag}/{path} is marked required in ERCOT's table, but ERCOT's own create "
                    f"sample omits it ({sample}).",
                    tag,
                    "Send it unless you have confirmed ERCOT accepts the document without it.",
                    _see_required([path]),
                    source,
                )
            )
        rules = constraints.for_tag(tag)
        start = payload.find(q(EWS, "startTime"))
        start_dt = constraints.parse_datetime(start.text) if start is not None else None
        trade_day = trading_date(start_dt) if start_dt and start_dt.tzinfo else None
        for path, value in requirements.values_in(payload):
            rule = rules.get(path)
            if rule is None or rule.kind == constraints.IGNORED:
                continue
            why = rule.violation(value, trade_day)
            if not why:
                continue
            stated = f'ERCOT\'s table states: "{_values_text(rule)[:90]}"'
            if rule.kind == constraints.HOUR_BOUNDARY:
                h = hazards.BY_ID["silent-hour-rounding"]
                rep.findings.append(
                    Finding(
                        h.id,
                        SILENT,
                        f"{tag}/{path}: {why}. {stated}. ERCOT may move it to the nearest hour "
                        "without an error.",
                        path,
                        h.guard,
                        source=h.source,
                    )
                )
                continue
            message = f"{tag}/{path}: {why}. {stated}"
            if rule.advisory:
                message += f" Reported, not enforced: {rule.advisory_why}."
            rep.findings.append(
                Finding(
                    f"value-{rule.kind}",
                    WARNING if rule.advisory else ERROR,
                    message,
                    path,
                    see=rule.see,
                    source=source,
                )
            )
        for path in sorted(_ignored_fields().get(tag, ()) & present):
            message = (
                f'{tag}/{path} is documented as "Value ignored if provided"; whatever is '
                "sent here has no effect."
            )
            fix = "Remove the field, and do not expect ERCOT to echo it back."
            if (tag, path) in IGNORED_BUT_REQUIRED:
                section, words, fix = IGNORED_BUT_REQUIRED[(tag, path)]
                message = (
                    f'{tag}/{path} is documented as "Value ignored if provided", but '
                    f'{_np4_450(section)} list it as "{words}".'
                )
            rep.findings.append(
                Finding("value-ignored", WARNING, message, path, fix, source=source)
            )
        if trade_el is not None and start_dt is not None and start_dt.tzinfo is not None:
            stated = (trade_el.text or "").strip()
            _trade_date(
                rep, tag, stated, start.text.strip(), start_dt, rules.get("startTime"), source
            )


def _date(text: str) -> date | None:
    try:
        return date.fromisoformat(text.strip())
    except ValueError:
        return None


# xs:dateTime with a UTC offset. Created is typed wsu:AttributedDateTime, an extension of
# xs:string, so the schema accepts any text; only this form is read as a time.
_DATETIME_WITH_OFFSET = re.compile(r"-?\d{4,}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d+)?(Z|[+-]\d\d:\d\d)")


def _created(msg: ET.Element) -> datetime | None:
    """When a RequestMessage says it was created: Header/ReplayDetection/Created."""
    path = "/".join(q(MESSAGE, n) for n in ("Header", "ReplayDetection", "Created"))
    text = (msg.findtext(path) or "").strip()
    if not _DATETIME_WITH_OFFSET.fullmatch(text):
        return None
    when = constraints.parse_datetime(text)
    return when if when is not None and when.tzinfo is not None else None


def _trade_date(
    rep: Report,
    tag: str,
    stated: str,
    text: str,
    start: datetime,
    rule: constraints.Constraint | None,
    page: str,
) -> None:
    derived = trading_date(start).isoformat()
    if not stated or stated == derived or not _central_or_utc(start):
        return  # a foreign offset is reported once, by _offsets
    message = (
        f"BidSet tradingDate is {stated}, but {tag} starts at {text}, which falls on {derived} "
        "in Central time."
    )
    if rule is not None and "trade date" in rule.source:
        severity, source = ERROR, page
        message += f' The {tag} table states: "{_values_text(rule)[:90]}".'
    else:
        severity, source = WARNING, SRC_CONVENTIONS
        message += (
            ' ERCOT: "Trading dates are specified using YYYY-MM-DD, which indicates the '
            'operating day".'
        )
    rep.findings.append(
        Finding(
            "trade-date-mismatch",
            severity,
            message,
            tag,
            "Derive tradingDate from the payload's startTime in America/Chicago.",
            source=source,
        )
    )


def _central_or_utc(when: datetime) -> bool:
    return when.utcoffset() in (timedelta(0), when.astimezone(CENTRAL).utcoffset())


def _offsets(rep: Report, root: ET.Element) -> None:
    for name in TIME_FIELDS:
        for el in _texts(root, name):
            dt = constraints.parse_datetime(el.text)
            if dt is None or dt.tzinfo is None or _central_or_utc(dt):
                continue
            central = dt.astimezone(CENTRAL)
            rep.findings.append(
                Finding(
                    "utc-offset",
                    WARNING,
                    f"{name} {el.text.strip()} has offset {dt.isoformat()[-6:]}, but Central "
                    f"time at that instant is UTC{central.isoformat()[-6:]}: the value means "
                    f"{central.isoformat()}, trading date {central.date()}.",
                    name,
                    "Use the Central-time offset in force at that time, or UTC.",
                    source=SRC_TIME,
                )
            )


def _curve_style(rep: Report, root: ET.Element) -> None:
    for curve in root.iter():
        style_el = curve.find(q(EWS, "curveStyle"))
        if style_el is None or not (style_el.text or "").strip():
            continue
        style = style_el.text.strip()
        if style not in CURVE_STYLE_POINTS:
            continue
        lo, hi = CURVE_STYLE_POINTS[style]
        n = len(curve.findall(q(EWS, "CurveData")))
        if not lo <= n <= hi:
            want = f"exactly {lo}" if lo == hi else f"{lo} to {hi}"
            rep.findings.append(
                Finding(
                    "curve-style-points",
                    ERROR,
                    f"curveStyle {style} takes {want} CurveData point(s); this curve has {n}.",
                    local(curve.tag),
                    "Use CURVE for more than one point, or send a single point.",
                    source=SRC_CIM,
                )
            )


def _hour_24(rep: Report, root: ET.Element) -> None:
    for name in TIME_FIELDS:
        for el in _texts(root, name):
            text = el.text.strip()
            if "T24:" in text:
                rep.findings.append(
                    Finding(
                        "hour-24",
                        ERROR,
                        f"{name} is {text}; ERCOT excludes 24:00 although xs:dateTime allows it.",
                        name,
                        "Write 00:00 on the following day.",
                        source=SRC_TIME,
                    )
                )


def _intervals(rep: Report, root: ET.Element) -> None:
    for parent in (el for bidset in root.iter(q(EWS, "BidSet")) for el in bidset.iter()):
        spans = []
        for kid in parent:
            s, e = kid.find(q(EWS, "startTime")), kid.find(q(EWS, "endTime"))
            if s is None or e is None:
                continue
            a, b = (
                constraints.parse_datetime(s.text or ""),
                constraints.parse_datetime(e.text or ""),
            )
            if a and b and (a.tzinfo is None) == (b.tzinfo is None):
                spans.append((a, b, local(kid.tag)))
        groups: dict[str, list] = {}
        for span in spans:
            groups.setdefault(span[2], []).append(span)
        for name, group in groups.items():
            if name in BIDSET_PAYLOADS:
                continue
            group.sort()
            for (_, end1, _), (start2, _, _) in pairwise(group):
                if start2 < end1:
                    rep.findings.append(
                        Finding(
                            "overlapping-intervals",
                            ERROR,
                            f"Two {name} intervals overlap: one ends {end1.isoformat()} and the "
                            f"next starts {start2.isoformat()}.",
                            local(parent.tag),
                            "Make each interval end where the next begins.",
                            source=SRC_TIME,
                        )
                    )
                elif start2 > end1 and name in MUST_TILE:
                    rep.findings.append(
                        Finding(
                            "interval-gap",
                            WARNING,
                            f"{name} leaves a gap from {end1.isoformat()} to "
                            f"{start2.isoformat()}; ERCOT expects consecutive intervals to meet.",
                            local(parent.tag),
                            source=SRC_TIME,
                        )
                    )


def _mw_precision(rep: Report, root: ET.Element) -> None:
    """MWSingleDecimal is a bare xs:decimal, so the XSD accepts submitted MW at any precision."""
    for doc in schema.documents(root):
        hit = schema._index(str(sources.xsd_dir())).get(doc.tag)
        if hit is None or doc.tag != q(EWS, "BidSet"):
            continue
        sch = hit[1]

        def walk(el: ET.Element, path: str, sch=sch) -> None:
            path = f"{path}/{el.tag}"
            text = (el.text or "").strip()
            if (
                len(el) == 0
                and text
                and decimals(text) > MW_DECIMALS
                and "MWSingleDecimal" in schema.type_names(sch, path)
            ):
                rep.findings.append(
                    Finding(
                        "mw-precision",
                        WARNING,
                        f"{local(el.tag)} = {text} has {decimals(text)} decimals. ERCOT "
                        "states MW values are enforced to one decimal, but MWSingleDecimal "
                        "does not enforce it, so the outcome is not documented.",
                        local(el.tag),
                        "Round MW to one decimal place, toward zero.",
                        source=f"{PORTAL}/Services%20Organization/#precision",
                    )
                )
            for child in el:
                walk(child, path)

        walk(doc, "")


def _rrs_value1(rep: Report, root: ET.Element) -> None:
    for saa in root.iter(q(EWS, "SelfArrangedAS")):
        if (saa.findtext(q(EWS, "asType")) or "").strip().upper() != "RRS":
            continue
        for v1 in saa.iter(q(EWS, "value1")):
            if (v1.text or "").strip() not in ("", "0", "0.0"):
                h = hazards.BY_ID["silent-rrs-value1-ignored"]
                rep.findings.append(
                    Finding(
                        h.id,
                        SILENT,
                        f"ASType is RRS and value1 is {v1.text.strip()}; ERCOT ignores value1 for "
                        "RRS.",
                        "SelfArrangedAS",
                        h.guard,
                        source=h.source,
                    )
                )


def _message(rep: Report, msg: ET.Element) -> None:
    header = msg.find(q(MESSAGE, "Header"))
    if header is None:
        return
    verb = (header.findtext(q(MESSAGE, "Verb")) or "").strip()
    if verb != "cancel":
        return
    for rid in msg.iter(q(MESSAGE, "ID")):
        text = (rid.text or "").strip()
        scope = mrid.cancel_scope(text)
        code = text.split(".")[2] if text.count(".") >= 2 else ""
        if code == "COP":
            rep.findings.append(
                Finding(
                    "cop-cancel",
                    ERROR,
                    "A COP cannot be canceled; ERCOT says it can only be updated.",
                    text,
                    source=SRC_CANCEL,
                )
            )
        elif scope.whole_day:
            rep.findings.append(
                Finding(
                    "cancel-every-hour",
                    WARNING,
                    f"{text} has no hour suffix, so this cancel reaches every hour of the "
                    "trading date.",
                    text,
                    "Append the hour or hour range (e.g. .14 or .14-16) unless the whole day is "
                    "meant.",
                    source=SRC_CANCEL,
                )
            )


def _verb(root: ET.Element, default: str) -> str:
    if root.tag == q(MESSAGE, "RequestMessage"):
        return (root.findtext(f"{q(MESSAGE, 'Header')}/{q(MESSAGE, 'Verb')}") or "").strip()
    if root.tag == q(MESSAGE, "ResponseMessage"):
        return "reply"
    if root.tag in (q(NOTIFICATION, "Notify"), q(EWS, "NotificationMessages")):
        return "notify"  # notifications ERCOT sent, pushed or fetched; none is a submission
    return default


def check(xml: str | bytes, xsd_dir: Path | None = None, *, verb: str = "create") -> Report:
    """Run every check on one document: a payload, a RequestMessage, or a SOAP envelope.

    ``verb`` applies to a bare payload such as a BidSet (a message carries its own
    Header/Verb). Required-field checks run only for create, change and update.
    """
    rep = Report()
    verdict = schema.validate(xml, xsd_dir)
    try:
        root = schema.payload_root(schema.parse(xml))
    except schema.DoctypeError as e:
        rep.schema = verdict.state
        fix = "Remove the DOCTYPE, and write out the text of any entity it declares."
        rep.findings.append(Finding("doctype", ERROR, str(e), fix=fix, source=SRC_SOAP))
        return rep
    except schema.DepthError as e:
        rep.schema = verdict.state
        fix = "Remove the extra levels; no ERCOT schema nests elements this deep."
        rep.findings.append(Finding("nesting-depth", ERROR, str(e), fix=fix))
        return rep
    except ET.ParseError:
        root = None
    _schema_findings(rep, verdict)
    if root is None:
        return rep
    if root.tag == q(MESSAGE, "RequestMessage"):
        _message(rep, root)
    creating = _verb(root, verb) in ("create", "change", "update")
    in_message = root.tag == q(MESSAGE, "RequestMessage")
    created = _created(root) if in_message else None
    for bidset in root.iter(q(EWS, "BidSet")):
        _payload_findings(rep, bidset, creating, in_message, created)
    _curve_style(rep, root)
    _hour_24(rep, root)
    _offsets(rep, root)
    _intervals(rep, root)
    _mw_precision(rep, root)
    _rrs_value1(rep, root)
    raw = xml.encode("utf-8") if isinstance(xml, str) else xml
    for bidset in root.iter(q(EWS, "BidSet")):
        why = check_size(len(ET.tostring(bidset)) if bidset is not root else len(raw))
        if why:
            rep.findings.append(
                Finding(
                    "payload-too-large",
                    ERROR,
                    why,
                    "BidSet",
                    "Split it by resource or by half day.",
                    source=SRC_LIMITS,
                )
            )
    return rep


def check_file(path: str | Path, *, verb: str = "create") -> Report:
    return check(Path(path).read_bytes(), verb=verb)
