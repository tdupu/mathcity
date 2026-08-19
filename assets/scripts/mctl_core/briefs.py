"""Canonical, read-only brief inspection core for mctl."""
from __future__ import annotations

from dataclasses import dataclass, replace
import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Iterable

from .beads import BD_LIST_ARGS, Bead, BeadReadError, read_beads
from .context import MctlContext
from .diagnostics import Diagnostic, Severity
from .policy_refs import BRIEF_POLICY_REFERENCES, PolicyReference
from .redundant_state import (
    ArtifactLayout,
    LegacyManifestState,
    RedundantArtifact,
    artifact_layout,
    legacy_manifest_state,
    orphan_decision_cache_ids,
    orphan_markdown_cache_ids,
    scan_artifacts,
)


@dataclass(frozen=True)
class BriefFilters:
    status: str | None = None
    label: str | None = None


@dataclass(frozen=True)
class BriefSection:
    """One markdown section of a brief body.

    `section_index` is the `present-it` slot this heading fills (§1 What is
    being decided … §7 Plan membership) when the heading names one, and None
    when it does not. `match` says how that was decided, so a consumer can
    tell a heading that carried an explicit `§N` marker from one this module
    recognised by name -- and can see, rather than guess, when nothing
    matched.

    `body` runs to the next heading at the same or a shallower level, so a
    section keeps its own subsections and a §-level render is whole. Deeper
    headings also appear as entries of their own, carrying `level`; a caller
    wanting only top-level sections filters on the shallowest level present.
    """

    heading: str
    level: int
    start_line: int
    end_line: int
    body: str
    section_index: int | None
    section_key: str | None
    match: str

    def to_dict(self) -> dict[str, object]:
        return {
            "body": self.body,
            "end_line": self.end_line,
            "heading": self.heading,
            "level": self.level,
            "match": self.match,
            "section_index": self.section_index,
            "section_key": self.section_key,
            "start_line": self.start_line,
        }


@dataclass(frozen=True)
class BriefRecord:
    brief_id: str
    bead_id: str
    title: str
    status: str
    decision_state: str
    labels: tuple[str, ...]
    created_at: str | None
    updated_at: str | None
    redundant_artifacts: tuple[RedundantArtifact, ...]
    policy_references: tuple[PolicyReference, ...]
    #: The canonical bead description, verbatim. None means "not loaded" --
    #: `list_briefs` deliberately leaves it off, because fetching every body
    #: turns a roster read into a city-wide content read. `""` means loaded
    #: and genuinely empty. Only `show_brief` populates it.
    body: str | None = None
    sections: tuple[BriefSection, ...] = ()
    #: Why the parse produced what it did. A body that yields no sections
    #: reports the reason here instead of returning an empty array that
    #: reads like "this brief has no sections".
    body_diagnostics: tuple[Diagnostic, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "bead_id": self.bead_id,
            "brief_id": self.brief_id,
            "canonical_source": "bead_store",
            "created_at": self.created_at,
            "decision_state": self.decision_state,
            "labels": list(self.labels),
            "policy_references": [reference.to_dict() for reference in self.policy_references],
            "redundant_artifacts": [artifact.to_dict() for artifact in self.redundant_artifacts],
            "status": self.status,
            "title": self.title,
            "updated_at": self.updated_at,
        }
        if self.body is not None:
            payload["body"] = self.body
            payload["sections"] = [section.to_dict() for section in self.sections]
            payload["body_diagnostics"] = [
                diagnostic.to_dict() for diagnostic in self.body_diagnostics
            ]
        return payload


@dataclass(frozen=True)
class BriefOption:
    id: str
    label: str
    description: str
    enabled: bool
    disabled_reason: Diagnostic | None

    def to_dict(self) -> dict[str, object]:
        return {
            "description": self.description,
            "disabled_reason": (
                self.disabled_reason.to_dict() if self.disabled_reason is not None else None
            ),
            "enabled": self.enabled,
            "id": self.id,
            "label": self.label,
        }


@dataclass(frozen=True)
class DoctorReport:
    records: tuple[BriefRecord, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def severity_counts(self) -> dict[str, int]:
        return {severity.value: sum(item.severity is severity for item in self.diagnostics) for severity in Severity}

    def to_dict(self) -> dict[str, object]:
        per_brief = []
        brief_ids = [record.brief_id for record in self.records]
        for diagnostic in self.diagnostics:
            brief_id = diagnostic.facts.get("brief_id")
            if brief_id and brief_id not in brief_ids:
                brief_ids.append(brief_id)
        for brief_id in brief_ids:
            per_brief.append(
                {
                    "brief_id": brief_id,
                    "diagnostics": [
                        diagnostic.to_dict()
                        for diagnostic in self.diagnostics
                        if diagnostic.facts.get("brief_id") == brief_id
                    ],
                }
            )
        return {
            "briefs": [record.to_dict() for record in self.records],
            "brief_diagnostics": per_brief,
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "severity_counts": self.severity_counts,
            "trace_id": self.diagnostics[0].trace_id if self.diagnostics else None,
        }


@dataclass(frozen=True)
class ValidationReport:
    """Proof that canonical and redundant brief state still agree.

    `briefs doctor` reports drift across the whole rig; validate is the
    stricter per-brief gate creation and mutation workflows lean on, so it
    composes doctor and adds the invariants doctor deliberately leaves out.
    Read-only: it never repairs what it reports.
    """

    scope: str
    records: tuple[BriefRecord, ...]
    diagnostics: tuple[Diagnostic, ...]

    @property
    def severity_counts(self) -> dict[str, int]:
        return {
            severity.value: sum(item.severity is severity for item in self.diagnostics)
            for severity in Severity
        }

    @property
    def valid(self) -> bool:
        return not any(
            diagnostic.severity in {Severity.ERROR, Severity.FATAL}
            for diagnostic in self.diagnostics
        )

    def to_dict(self) -> dict[str, object]:
        brief_ids = [record.brief_id for record in self.records]
        for diagnostic in self.diagnostics:
            brief_id = diagnostic.facts.get("brief_id")
            if brief_id and brief_id not in brief_ids:
                brief_ids.append(brief_id)
        return {
            "briefs": [record.to_dict() for record in self.records],
            "brief_diagnostics": [
                {
                    "brief_id": brief_id,
                    "diagnostics": [
                        diagnostic.to_dict()
                        for diagnostic in self.diagnostics
                        if diagnostic.facts.get("brief_id") == brief_id
                    ],
                }
                for brief_id in brief_ids
            ],
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "scope": self.scope,
            "severity_counts": self.severity_counts,
            "valid": self.valid,
        }


class BriefError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


def list_briefs(ctx: MctlContext, filters: BriefFilters) -> tuple[BriefRecord, ...]:
    records = _records(ctx)
    return tuple(record for record in records if _matches(record, filters))


def show_brief(ctx: MctlContext, brief_id: str) -> BriefRecord:
    """One brief, with its body -- the decision evidence -- attached.

    Detail is where the body belongs. `list_briefs` deliberately leaves it
    off: a city-wide roster read that also fetched ~200 brief bodies would be
    a performance regression for every caller that only wanted the titles.

    The bead snapshot this already reads carries the description, so
    attaching the body costs no extra `bd` subprocess.
    """
    beads = _beads(ctx)
    record = _find_record(ctx, _records(ctx, beads), brief_id)
    bead = next((item for item in beads if item.id == record.bead_id), None)
    body = brief_body(ctx, brief_id, bead)
    sections, diagnostics = brief_body_report(ctx, brief_id, body)
    return replace(record, body=body, sections=sections, body_diagnostics=diagnostics)


def brief_command_diagnostics(ctx: MctlContext, records: Iterable[BriefRecord]) -> tuple[Diagnostic, ...]:
    layout = artifact_layout(ctx)
    legacy_state = legacy_manifest_state(layout)
    brief_ids = {record.brief_id for record in records}
    return _legacy_gate_diagnostics(ctx, layout, legacy_state, brief_ids)


def legacy_gate_diagnostics(ctx: MctlContext) -> tuple[Diagnostic, ...]:
    """The #38 legacy-migration gate, independent of any single brief.

    Creation has no existing brief to scope the gate to, but it is still a
    mutation and must fail closed on unmigrated decisions-track rows.
    """
    layout = artifact_layout(ctx)
    return _legacy_gate_diagnostics(ctx, layout, legacy_manifest_state(layout), None)


# A brief label is a bd label: one lowercase token, no spaces.
_LABEL_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]*$")

# B2.4 keeps exactly one pile and expresses urgency through ordering, and
# B2.10 forbids an active side presentation lane. A label that names its own
# lane is a request for the thing both rules exclude.
_BYPASS_LABEL_TOKENS = ("urgent", "bypass", "side-pile", "sidepile", "hotfix", "jump-queue")


def validate_brief_input(
    ctx: MctlContext, title: str | None, body: str | None, labels: Iterable[str]
) -> tuple[str, str, tuple[str, ...]]:
    """Check a proposed brief against brief-system policy before any write.

    Each check maps to a policy section reference rather than restating the
    prose; the reference is what the operator follows to see why.
    """
    clean_title = (title or "").strip()
    if not clean_title:
        raise BriefError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MBRF030",
                "A brief needs a non-empty title stating what is being decided.",
                policy_ref="B1.1",
            )
        )
    clean_body = (body or "").strip()
    if not clean_body:
        raise BriefError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MBRF031",
                "A brief needs a non-empty body carrying its decision evidence.",
                policy_ref="B1.5",
            )
        )
    clean_labels: list[str] = []
    for label in labels:
        candidate = label.strip()
        if not _LABEL_PATTERN.match(candidate):
            raise BriefError(
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MBRF033",
                    f"Brief label {label!r} is not a usable bd label token.",
                )
            )
        if any(token in candidate for token in _BYPASS_LABEL_TOKENS):
            raise BriefError(
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MBRF032",
                    f"Brief label {candidate!r} requests a side or bypass pile.",
                    policy_ref="B2.4",
                )
            )
        clean_labels.append(candidate)
    return clean_title, clean_body, tuple(dict.fromkeys(clean_labels))


def validation_scope(ctx: MctlContext, brief_id: str | None, all_briefs: bool) -> str | None:
    """Resolve the validate scope, or fail closed with MBRF014.

    "Exactly one of a brief id or every brief" is a domain rule, not an
    argparse limitation, so both adapters resolve it here rather than each
    inventing its own answer to "validate what?".
    """
    if all_briefs and brief_id:
        raise BriefError(_validation_scope_diagnostic(ctx, both=True))
    if all_briefs:
        return None
    if brief_id:
        return brief_id
    raise BriefError(_validation_scope_diagnostic(ctx, both=False))


def _validation_scope_diagnostic(ctx: MctlContext, *, both: bool) -> Diagnostic:
    message = (
        "briefs validate takes a brief id or --all, not both."
        if both
        else "briefs validate requires a brief id or --all."
    )
    return Diagnostic(
        severity=Severity.FATAL,
        code="MBRF014",
        message=message,
        hint="Run `mctl briefs validate <brief-id>` or `mctl briefs validate --all`.",
        facts={
            "city_path": str(ctx.city_root),
            "implementation_provenance": "mctl Slice 5 brief validation",
            "rig_name": ctx.rig_id,
            "rig_path": str(ctx.rig_root),
        },
        trace_id=ctx.trace_id,
    )


def validate_brief(ctx: MctlContext, brief_id: str | None) -> ValidationReport:
    """Validate one brief, or every brief when `brief_id` is None.

    The bead store is read exactly once and the snapshot threaded through
    every per-brief check, so `--all` costs the same number of bd calls as a
    single brief.
    """
    beads = _beads(ctx)
    layout = artifact_layout(ctx)
    report = _doctor_briefs(ctx, brief_id, beads)
    bead_by_id = {bead.id: bead for bead in beads}
    diagnostics = list(report.diagnostics)
    for record in report.records:
        diagnostics.extend(
            _strict_invariants(ctx, layout, record, bead_by_id[record.bead_id])
        )
    return ValidationReport(
        scope=brief_id if brief_id is not None else "--all",
        records=report.records,
        diagnostics=tuple(diagnostics),
    )


def _strict_invariants(
    ctx: MctlContext, layout: ArtifactLayout, record: BriefRecord, bead: Bead
) -> tuple[Diagnostic, ...]:
    diagnostics: list[Diagnostic] = []
    cache_path = layout.decisions / f"{record.brief_id}.toml"
    cached = _read_toml(cache_path)
    cached_status = cached.get("status")
    if isinstance(cached_status, str) and cached_status:
        if cached_status not in {record.status, record.decision_state}:
            diagnostics.append(
                _diagnostic(
                    ctx,
                    Severity.ERROR,
                    "MBRF020",
                    "Redundant decision cache disagrees with the canonical bead.",
                    brief_id=record.brief_id,
                    data_location=str(cache_path),
                    policy_ref="B2.8",
                    detail=(
                        f"cache status={cached_status!r}; canonical status="
                        f"{record.status!r}, decision_state={record.decision_state!r}"
                    ),
                )
            )
    cached_verdict = cached.get("verdict")
    if isinstance(cached_verdict, str) and cached_verdict:
        canonical_verdict = _verdict(bead)
        if (canonical_verdict or "").strip().lower() != cached_verdict.strip().lower():
            diagnostics.append(
                _diagnostic(
                    ctx,
                    Severity.ERROR,
                    "MBRF020",
                    "Redundant decision cache records a verdict the bead does not.",
                    brief_id=record.brief_id,
                    data_location=str(cache_path),
                    policy_ref="B2.8",
                    detail=(
                        f"cache verdict={cached_verdict!r}; canonical verdict="
                        f"{canonical_verdict!r}"
                    ),
                )
            )
    if not any(artifact.state == "present" for artifact in record.redundant_artifacts):
        diagnostics.append(
            _diagnostic(
                ctx,
                Severity.WARN,
                "MBRF021",
                "Canonical brief bead has no redundant cache artifact.",
                brief_id=record.brief_id,
                data_location=str(layout.pile / f"{record.brief_id}.md"),
                policy_ref="B2.8",
            )
        )
    return tuple(diagnostics)


def _read_toml(path: Path) -> dict[str, object]:
    if not path.is_file():
        return {}
    try:
        return dict(tomllib.loads(path.read_text(encoding="utf-8")))
    except (OSError, tomllib.TOMLDecodeError):
        return {}


def brief_options(ctx: MctlContext, brief_id: str) -> tuple[BriefOption, ...]:
    options, _ = brief_options_report(ctx, brief_id)
    return options


def brief_options_report(ctx: MctlContext, brief_id: str) -> tuple[tuple[BriefOption, ...], tuple[Diagnostic, ...]]:
    beads = _beads(ctx)
    records = _records(ctx, beads)
    record = _find_record(ctx, records, brief_id)
    bead_by_id = {bead.id: bead for bead in beads}
    bead = bead_by_id[record.bead_id]
    doctor = _doctor_briefs(ctx, brief_id, beads)
    blocker = _blocking_diagnostic(doctor.diagnostics)
    pending_blocker = blocker
    if pending_blocker is None and record.decision_state != "pending":
        pending_blocker = _diagnostic(
            ctx,
            Severity.ERROR,
            "MBRF011",
            f"Brief {brief_id!r} is not pending adjudication.",
            brief_id=brief_id,
            data_location=_canonical_bead_location(ctx),
            policy_ref="B2.2",
        )
    dispatch_blocker = blocker
    if dispatch_blocker is None and not _approved_for_dispatch(bead):
        dispatch_blocker = _diagnostic(
            ctx,
            Severity.ERROR,
            "MBRF011",
            f"Brief {brief_id!r} has no approving verdict for dispatch.",
            brief_id=brief_id,
            data_location=_canonical_bead_location(ctx),
            policy_ref="B2.2",
        )
    return (
        (
            BriefOption("validate", "Validate", "Inspect canonical state and cache drift.", True, None),
            BriefOption(
                "adjudicate",
                "Adjudicate",
                "Record a human verdict on the canonical brief bead.",
                pending_blocker is None,
                pending_blocker,
            ),
            BriefOption(
                "defer",
                "Defer",
                "Set a timed defer window on the canonical brief bead.",
                pending_blocker is None,
                pending_blocker,
            ),
            BriefOption(
                "dispatch-work",
                "Dispatch work",
                "Dispatch work unlocked by the canonical brief bead.",
                dispatch_blocker is None,
                dispatch_blocker,
            ),
        ),
        doctor.diagnostics,
    )



@dataclass(frozen=True)
class BriefDecisionOption:
    """One decision option offered by a brief, per plan §2.

    Distinct from the action options `brief_options` returns (adjudicate /
    defer / validate). The plan gives both types the name BriefOption; this is
    the §2 one, parsed out of the brief markdown.
    """

    label: str
    heading: str
    start_line: int
    end_line: int
    raw_text: str
    confidence: str


# Real briefs enumerate options as list items under an options section:
#     ## §4 — Options
#     - **(A) Do it now.** *(recommended)* ...
# Scoping to the section keeps ordinary bolded prose elsewhere from
# fabricating options.
_OPTION_ITEM = re.compile(
    r"^\s*[-*]\s+\*\*\((?P<label>[A-Za-z0-9]+)\)\s*(?P<heading>[^*]+?)\*\*",
    re.MULTILINE,
)


def parse_decision_options(markdown: str) -> tuple[BriefDecisionOption, ...]:
    """Extract the decision options a brief offers, if any.

    Scoped to §4 via `parse_brief_sections` rather than to a heading spelled
    exactly `Options`. The exact-match version found nothing on the live rig:
    the one open hecke brief that enumerates options heads them "Options
    presented", and "Alternatives Considered" -- the second most common
    heading on the rig -- never matched at all. Both are §4.
    """
    lines = markdown.splitlines()
    options: list[BriefDecisionOption] = []
    for section in parse_brief_sections(markdown):
        if section.section_index != 4:
            continue
        body = section.body
        # `body` is `lines[heading .. end]` rejoined after stripping blank
        # edges, so offsets are recovered against the original line list.
        first_body_line = section.start_line + 1
        while first_body_line <= section.end_line and not lines[first_body_line - 1].strip():
            first_body_line += 1
        matches = list(_OPTION_ITEM.finditer(body))
        for position, match in enumerate(matches):
            end_in_body = (
                matches[position + 1].start() if position + 1 < len(matches) else len(body)
            )
            options.append(
                BriefDecisionOption(
                    label=match.group("label"),
                    heading=match.group("heading").strip(),
                    start_line=first_body_line + body.count("\n", 0, match.start()),
                    end_line=first_body_line + body.count("\n", 0, end_in_body),
                    raw_text=body[match.start():end_in_body].strip(),
                    confidence="explicit",
                )
            )
    return tuple(options)


# --- brief body sections ----------------------------------------------------


#: The `present-it` full-form sections, in grill order. The dashboard's brief
#: detail screen renders these seven; the keys are what it addresses them by.
PRESENT_IT_SECTIONS: tuple[tuple[int, str], ...] = (
    (1, "what_is_being_decided"),
    (2, "recommended_answer"),
    (3, "assumptions_surfaced"),
    (4, "alternatives_named"),
    (5, "risks_foregrounded"),
    (6, "supporting_evidence"),
    (7, "plan_membership"),
)

_SECTION_KEYS = dict(PRESENT_IT_SECTIONS)


def present_it_label(section_index: int | None, section_key: str | None) -> str | None:
    """The canonical name of a present-it section, for display.

    Derived from the key rather than kept in a second table, so the two
    cannot drift into disagreeing about what §3 is called.
    """
    if section_index is None or not section_key:
        return None
    return f"§{section_index} {section_key.replace('_', ' ').capitalize()}"

#: Heading tokens that name a `present-it` section, most specific first: the
#: first token found in the normalised heading wins. Ordering matters --
#: "Decision options" is §4, not the §1 its "decision" substring would claim.
#:
#: Deliberately absent: "Related", "Affects", "Follow-up". They are common on
#: live hecke briefs and they are *link lists*, not §7 plan-membership and
#: gate statements. Rendering them under §7 would put a claim about required
#: gates on screen that the brief never made, so they stay unmapped.
_SECTION_TOKENS: tuple[tuple[str, int], ...] = (
    ("what is being decided", 1),
    ("what is decided", 1),
    ("decision option", 4),
    ("alternative", 4),
    ("option", 4),
    ("recommend", 2),
    ("rationale", 2),
    ("assumption", 3),
    ("risk", 5),
    ("safety", 5),
    ("supporting evidence", 6),
    ("evidence", 6),
    ("plan membership", 7),
    ("required gate", 7),
    ("gate", 7),
    ("blocking", 7),
    ("blocker", 7),
    ("decision required", 1),
    ("decision", 1),
    ("ruling", 1),
)

# `## §4 — Options`, `### §1 - What is being decided`, `## Section 4: Options`.
_EXPLICIT_SECTION = re.compile(r"^(?:§|section\s+|sec\.\s*)(\d+)\b", re.IGNORECASE)
# ATX headings only. Setext (`===` underlines) does not occur in brief bodies
# and guessing at it would invent sections rather than find them.
_HEADING_LINE = re.compile(r"^(?P<hashes>#{1,6})[ \t]+(?P<text>\S.*?)\s*$")
_FENCE_LINE = re.compile(r"^\s*(?P<fence>`{3,}|~{3,})")


def _classify_heading(heading: str) -> tuple[int | None, str | None, str]:
    """Map a heading to its `present-it` section slot, and say how."""
    explicit = _EXPLICIT_SECTION.match(heading.strip())
    if explicit is not None:
        index = int(explicit.group(1))
        if index in _SECTION_KEYS:
            return index, _SECTION_KEYS[index], "explicit"
    normalized = re.sub(r"[^a-z0-9]+", " ", heading.lower()).strip()
    for token, index in _SECTION_TOKENS:
        if token in normalized:
            return index, _SECTION_KEYS[index], "heading"
    return None, None, "unmapped"


def parse_brief_sections(markdown: str) -> tuple[BriefSection, ...]:
    """Split a brief body into its markdown sections.

    Never lossy by construction: this reports where sections *are*, and the
    caller keeps the raw body regardless of what comes back. Fenced code is
    skipped, so a `# comment` inside a shell block cannot fabricate a section
    -- which would be the same silent-corruption failure in the other
    direction.
    """
    lines = markdown.splitlines()
    headings: list[tuple[int, int, str]] = []
    fence: str | None = None
    for number, line in enumerate(lines):
        opened = _FENCE_LINE.match(line)
        if fence is not None:
            if opened is not None and opened.group("fence")[0] == fence[0]:
                fence = None
            continue
        if opened is not None:
            fence = opened.group("fence")
            continue
        matched = _HEADING_LINE.match(line)
        if matched is not None:
            text = matched.group("text").rstrip("#").strip()
            if text:
                headings.append((number, len(matched.group("hashes")), text))

    # A lone leading `#` is the document title, not a section: counting it
    # would report a section whose body is the entire brief, duplicating
    # every real section inside it. The text is still in `title` and in the
    # raw body, so nothing is lost by leaving it out here.
    if headings and headings[0][1] == 1 and sum(level == 1 for _, level, _ in headings) == 1:
        headings = headings[1:]

    sections: list[BriefSection] = []
    for position, (number, level, text) in enumerate(headings):
        end = len(lines)
        for later_number, later_level, _ in headings[position + 1 :]:
            if later_level <= level:
                end = later_number
                break
        index, key, match = _classify_heading(text)
        sections.append(
            BriefSection(
                heading=text,
                level=level,
                start_line=number + 1,
                end_line=end,
                body="\n".join(lines[number + 1 : end]).strip("\n"),
                section_index=index,
                section_key=key,
                match=match,
            )
        )
    return tuple(sections)


def brief_body_report(
    ctx: MctlContext, brief_id: str, body: str
) -> tuple[tuple[BriefSection, ...], tuple[Diagnostic, ...]]:
    """Parse a brief body, reporting *why* when it yields nothing.

    A parser that quietly returns nothing is indistinguishable from a brief
    that genuinely has no sections, and the caller cannot tell which it got.
    These diagnostics ride on the record next to the raw body, so the body is
    always available whatever the parse did.
    """
    if not body.strip():
        return (), (
            _diagnostic(
                ctx,
                Severity.WARN,
                "MBRF040",
                "Canonical brief bead carries no description, so it has no body to show.",
                brief_id=brief_id,
                data_location=_canonical_bead_location(ctx),
                policy_ref="B1.5",
            ),
        )
    sections = parse_brief_sections(body)
    if not sections:
        return sections, (
            _diagnostic(
                ctx,
                Severity.WARN,
                "MBRF041",
                "Brief body has no markdown headings; only its raw text is available.",
                brief_id=brief_id,
                data_location=_canonical_bead_location(ctx),
                detail=f"body_characters={len(body)}",
            ),
        )
    if not any(section.section_index is not None for section in sections):
        return sections, (
            _diagnostic(
                ctx,
                Severity.WARN,
                "MBRF042",
                "No brief body heading maps to a present-it section (§1-§7).",
                brief_id=brief_id,
                data_location=_canonical_bead_location(ctx),
                detail="headings=" + ", ".join(section.heading for section in sections),
            ),
        )
    return sections, ()


def brief_body(ctx: MctlContext, brief_id: str, bead: Bead | None = None) -> str:
    """The brief's body text: the canonical bead description, else the cache.

    B2.4/B2.8 make the bead canonical and the markdown file a cache, so the
    description wins whenever it exists. The file remains a fallback for
    briefs written before bodies landed on the bead; it is never allowed to
    override a description that is present.
    """
    if bead is None:
        bead = _bead_for(ctx, brief_id)
    description = (bead.description or "") if bead is not None else ""
    if description.strip():
        return description
    return _cached_body(ctx, brief_id)


def _cached_body(ctx: MctlContext, brief_id: str) -> str:
    layout = artifact_layout(ctx)
    for directory in (layout.pile, layout.stack):
        path = directory / f"{brief_id}.md"
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                return ""
    return ""


def _bead_for(ctx: MctlContext, brief_id: str) -> Bead | None:
    return next((bead for bead in _beads(ctx) if bead.id == brief_id), None)


def decision_options(
    ctx: MctlContext, brief_id: str, body: str | None = None
) -> tuple[BriefDecisionOption, ...]:
    """Decision options for a brief, read from its canonical body.

    This used to read `<brief_root>/.pile/<brief_id>.md` only. That path does
    not resolve on the live rig -- 0 of 25 sampled hecke briefs returned an
    option -- and the function failed open, so §4 was empty for every real
    brief and MOPT001 could never fire. The bead description is canonical and
    present on 62 of 64 open hecke decision beads, so it is the source now;
    the cache remains a fallback via `brief_body`.

    `body` lets a caller that already read the body pass it in, so resolving
    options costs no additional `bd` subprocess.
    """
    resolved = brief_body(ctx, brief_id) if body is None else body
    if not resolved.strip():
        return ()
    return parse_decision_options(resolved)

def doctor_briefs(
    ctx: MctlContext, brief_id: str | None, beads: tuple[Bead, ...] | None = None
) -> DoctorReport:
    """Report canonical/cache drift.

    Callers that already hold a bead snapshot pass it in; each bead read is a
    full `bd list` subprocess, so re-reading per brief makes callers that loop
    over briefs scale with the size of the rig.
    """
    return _doctor_briefs(ctx, brief_id, beads)


def _doctor_briefs(ctx: MctlContext, brief_id: str | None, beads: tuple[Bead, ...] | None = None) -> DoctorReport:
    beads = _beads(ctx) if beads is None else beads
    layout = artifact_layout(ctx)
    legacy_state = legacy_manifest_state(layout)
    records = _records(ctx, beads, layout, legacy_state)
    if brief_id is not None:
        records = tuple(record for record in records if record.brief_id == brief_id)
        if not records:
            raise BriefError(
                _diagnostic(ctx, Severity.FATAL, "MBRF010", f"No canonical brief bead named {brief_id!r} was found.", brief_id=brief_id)
            )
    bead_by_id = {bead.id: bead for bead in beads}
    diagnostics: list[Diagnostic] = []
    for record in records:
        bead = bead_by_id[record.bead_id]
        if not bead.source_dependencies:
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF004", "Brief bead has no source dependency.", brief_id=record.brief_id, data_location=_canonical_bead_location(ctx), policy_ref="B2.1"))
        if bead.status.lower() in {"closed", "done"} and not _has_verdict(bead):
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF005", "Closed brief bead has no recorded verdict.", brief_id=record.brief_id, data_location=_canonical_bead_location(ctx), policy_ref="B2.2"))
        for artifact in record.redundant_artifacts:
            if artifact.kind == "stack_index" and artifact.state == "stale":
                diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF001", "Stack index row points at a missing file.", brief_id=record.brief_id, data_location=str(artifact.path), policy_ref="B2.8"))
            if artifact.kind == "stack_index" and artifact.state == "inconsistent":
                code = "MBRF006" if record.decision_state == "adjudicated" else "MBRF007"
                message = "Closed/adjudicated brief appears in presentable stack." if code == "MBRF006" else "Deferred brief appears before defer expiry."
                diagnostics.append(_diagnostic(ctx, Severity.ERROR, code, message, brief_id=record.brief_id, data_location=str(artifact.path), policy_ref="B2.3" if code == "MBRF006" else "B2.7"))
    for cached_id in orphan_decision_cache_ids(layout):
        if brief_id is not None and cached_id != brief_id:
            continue
        bead = bead_by_id.get(cached_id)
        if bead is None:
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF002", "Brief cache file exists with no matching decision bead.", brief_id=cached_id, data_location=str(layout.decisions / f"{cached_id}.toml"), policy_ref="B2.1"))
        elif bead.issue_type != "decision":
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF003", "Brief cache maps to a bead that is not type=decision.", brief_id=cached_id, data_location=str(layout.decisions / f"{cached_id}.toml"), policy_ref="B2.1"))
    for cached_id, path in orphan_markdown_cache_ids(layout):
        if brief_id is not None and cached_id != brief_id:
            continue
        if cached_id not in bead_by_id:
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF002", "Brief cache file exists with no matching decision bead.", brief_id=cached_id, data_location=str(path), policy_ref="B2.1"))
        elif bead_by_id[cached_id].issue_type != "decision":
            diagnostics.append(_diagnostic(ctx, Severity.ERROR, "MBRF003", "Brief cache maps to a bead that is not type=decision.", brief_id=cached_id, data_location=str(path), policy_ref="B2.1"))
    diagnostics.extend(
        _legacy_gate_diagnostics(
            ctx,
            layout,
            legacy_state,
            {brief_id} if brief_id is not None else None,
        )
    )
    return DoctorReport(records, tuple(diagnostics))


def _records(
    ctx: MctlContext,
    beads: tuple[Bead, ...] | None = None,
    layout: ArtifactLayout | None = None,
    legacy_state: LegacyManifestState | None = None,
) -> tuple[BriefRecord, ...]:
    layout = artifact_layout(ctx) if layout is None else layout
    legacy_state = legacy_manifest_state(layout) if legacy_state is None else legacy_state
    beads = _beads(ctx) if beads is None else beads
    return tuple(
        BriefRecord(
            brief_id=bead.id,
            bead_id=bead.id,
            title=bead.title,
            status=bead.status,
            decision_state=_decision_state(bead),
            labels=bead.labels,
            created_at=bead.created_at,
            updated_at=bead.updated_at,
            redundant_artifacts=scan_artifacts(layout, bead.id, _decision_state(bead), legacy_state),
            policy_references=BRIEF_POLICY_REFERENCES,
        )
        for bead in beads
        if bead.is_brief
    )


def _beads(ctx: MctlContext) -> tuple[Bead, ...]:
    try:
        return read_beads(ctx.rig_root, fixture_path=ctx.beads_fixture)
    except BeadReadError as error:
        raise BriefError(_diagnostic(ctx, Severity.FATAL, "MBRF012", str(error))) from error


def _canonical_bead_location(ctx: MctlContext) -> str:
    return f"{' '.join(BD_LIST_ARGS)} (rig database {ctx.rig_db})"


def _matches(record: BriefRecord, filters: BriefFilters) -> bool:
    if filters.status and filters.status not in {record.status, record.decision_state}:
        return False
    return not filters.label or filters.label in record.labels


def _decision_state(bead: Bead) -> str:
    status = bead.status.lower()
    if status in {"closed", "done"}:
        return "adjudicated" if _has_verdict(bead) else "malformed"
    if status == "deferred" or _defer_until(bead):
        return "deferred"
    return "pending"


def _has_verdict(bead: Bead) -> bool:
    return _verdict(bead) is not None


def _verdict(bead: Bead) -> str | None:
    for key in ("verdict", "decision", "recorded_verdict"):
        value = bead.raw.get(key)
        if isinstance(value, str) and value:
            return value
    metadata = bead.raw.get("metadata")
    if isinstance(metadata, dict):
        for key in ("verdict", "decision", "recorded_verdict"):
            value = metadata.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def _approved_for_dispatch(bead: Bead) -> bool:
    verdict = _verdict(bead)
    if verdict is None:
        return False
    return bead.status.lower() in {"closed", "done"} and verdict.strip().lower() in {
        "accept",
        "accepted",
        "approve",
        "approved",
    }


def _defer_until(bead: Bead) -> bool:
    for key in ("deferred_until", "defer_until"):
        value = bead.raw.get(key)
        if isinstance(value, str) and value >= date.today().isoformat():
            return True
    return False


def _row_slug(row: dict[str, object]) -> str | None:
    for key in ("slug", "brief_id", "id"):
        value = row.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _find_record(ctx: MctlContext, records: Iterable[BriefRecord], brief_id: str) -> BriefRecord:
    for record in records:
        if record.brief_id == brief_id:
            return record
    raise BriefError(
        _diagnostic(
            ctx,
            Severity.FATAL,
            "MBRF010",
            f"No canonical brief bead named {brief_id!r} was found.",
            brief_id=brief_id,
            suggested_next_command="mctl briefs list --json",
        )
    )


def _blocking_diagnostic(diagnostics: Iterable[Diagnostic]) -> Diagnostic | None:
    return next(
        (diagnostic for diagnostic in diagnostics if diagnostic.severity in {Severity.ERROR, Severity.FATAL}),
        None,
    )


def _legacy_gate_diagnostics(
    ctx: MctlContext,
    layout: ArtifactLayout,
    legacy_state: LegacyManifestState,
    brief_ids: set[str] | None,
) -> tuple[Diagnostic, ...]:
    if legacy_state.parse_error is not None:
        return (
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MBRF013",
                "Legacy decisions-track manifest could not be parsed.",
                data_location=str(layout.legacy_manifest),
                policy_ref="B2.10",
            ),
            _legacy_migration_blocker(ctx, layout),
        )
    legacy_rows = legacy_state.nonterminal_rows
    if brief_ids is not None:
        legacy_rows = tuple(row for row in legacy_rows if _row_slug(row) in brief_ids)
    if not legacy_rows:
        return ()
    diagnostics: list[Diagnostic] = []
    for row in legacy_rows:
        slug = _row_slug(row)
        diagnostics.append(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MBRF008",
                "Legacy decisions-track row is non-terminal and not migration-visible.",
                brief_id=slug,
                data_location=str(layout.legacy_manifest),
                policy_ref="B2.10",
            )
        )
    diagnostics.append(_legacy_migration_blocker(ctx, layout))
    return tuple(diagnostics)


def _legacy_migration_blocker(ctx: MctlContext, layout: ArtifactLayout) -> Diagnostic:
    return _diagnostic(
        ctx,
        Severity.FATAL,
        "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED",
        "Legacy decisions-track state requires the authorized #38 migration proof/canary.",
        data_location=str(layout.legacy_manifest),
        policy_ref="B2.10",
        suggested_next_command="bash tests/decisions-track-migration/smoke_test.sh",
    )


def _diagnostic(
    ctx: MctlContext,
    severity: Severity,
    code: str,
    message: str,
    *,
    brief_id: str | None = None,
    data_location: str | None = None,
    detail: str | None = None,
    policy_ref: str | None = None,
    suggested_next_command: str | None = None,
) -> Diagnostic:
    facts = {
        "city_path": str(ctx.city_root),
        "implementation_provenance": "mctl Slice 2 read-only brief inspection",
        "rig_name": ctx.rig_id,
        "rig_path": str(ctx.rig_root),
    }
    if brief_id:
        facts["brief_id"] = brief_id
        facts["bead_id"] = brief_id
    if data_location:
        facts["data_location"] = data_location
    if detail:
        facts["detail"] = detail
    if policy_ref:
        facts["policy_reference"] = policy_ref
    if suggested_next_command:
        facts["suggested_next_command"] = suggested_next_command
    return Diagnostic(severity, code, message, facts=facts, trace_id=ctx.trace_id)
