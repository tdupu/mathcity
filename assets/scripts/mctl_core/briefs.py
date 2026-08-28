"""Canonical, read-only brief inspection core for mctl."""
from __future__ import annotations

from dataclasses import dataclass, replace
import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Iterable, Mapping

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
from . import fields as field_provenance
from .fields import FieldReading
from .manifest import (
    CANONICAL_SOURCE_BEAD,
    CANONICAL_SOURCE_MANIFEST,
    SOURCE_BEAD,
    SOURCE_MANIFEST,
    ManifestReading,
    ManifestRecord,
    manifest_records,
)
from .stack import (
    CANONICAL_SOURCE_STACK,
    SOURCE_STACK,
    StackRecord,
    stack_records,
)
from .verdicts import (
    NON_BRIEF_MESSAGES,
    Verdict,
    brief_population,
    non_brief_code,
    read_verdict,
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
class BriefDocument:
    """One markdown document behind a brief, and which lane it came from.

    A brief can have more than one. 46 decisions-track rows also have a stack
    file, 19 of those two copies differ, and until this type existed the stack
    copy was not merely unshown -- the row carrying it was suppressed outright,
    so nothing reported that a second document existed at all.

    `lane` is stated rather than inferred from `path` so a consumer never has
    to pattern-match a directory name to know which copy it is holding.
    """

    lane: str
    path: str
    #: The document's text, verbatim. `None` means the file could not be read;
    #: `""` means it was read and is empty. The distinction is the same one
    #: `BriefRecord.body` makes, and for the same reason.
    body: str | None
    sections: tuple[BriefSection, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "body": self.body,
            "lane": self.lane,
            "path": self.path,
            "sections": [section.to_dict() for section in self.sections],
        }


@dataclass(frozen=True)
class BriefRecord:
    """One brief, from whichever store holds it.

    Three populations reach this type. Most records come from a decision bead.
    Next come the decisions-track manifest rows -- all 204 of the live city's,
    of which 158 were reachable by no reader at all and 46 more were suppressed
    outright for having a stack file that nothing read (see `manifest.py`). 203
    of the 204 have a markdown body in the manifest's own directory, and 46 a
    stack copy as well; both are carried, in `documents`. Last come the stack
    files no bead and no manifest row claims -- 41 live, and until this type
    grew a third `source` they reached no surface either.

    `source` is what separates them, and it is not decoration: a manifest row
    is a record that a brief existed with no bead attesting it, and a stack
    record is a file the pipeline deposited with neither a bead nor a manifest
    row behind it. Rendering either like a bead-backed brief would assert an
    attestation that does not exist.

    What a manifest row is *not* is bodiless. Slice 6 said 36 of them had
    "nothing readable in it"; 35 of those 36 have a markdown body in the same
    directory as the manifest, and now carry it. Exactly one live row has no
    document in any lane, and that -- not the absence of a verdict -- is what
    `unreadable` now means.

    Which is also why `bead_id` and `title` are nullable. Neither bead-less
    population has either. `""` would read as "this brief has no title"; `None`
    reads as "there is no bead here to have one", which is the true statement.
    """

    brief_id: str
    bead_id: str | None
    title: str | None
    status: str | None
    decision_state: str
    labels: tuple[str, ...]
    created_at: str | None
    updated_at: str | None
    redundant_artifacts: tuple[RedundantArtifact, ...]
    policy_references: tuple[PolicyReference, ...]
    #: Which store this record came from: `bead` or `manifest`.
    source: str = SOURCE_BEAD
    #: The verdict this brief carries, with the field and confidence it was
    #: read at. Populated for both populations -- a bead record that omitted
    #: it would report `null` beside a manifest record that reported one, and
    #: read as "the bead has no verdict" when the bead simply was not asked.
    verdict: Verdict | None = None
    #: The decisions-track lane a manifest row declares (33 distinct values
    #: live, `process-policy` the largest). None on a bead record: beads carry
    #: no track, and absent means absent.
    track: str | None = None
    #: The one timestamp this record can stand behind, or None. A bead reports
    #: its `updated_at`; a manifest row reports whichever of its own date
    #: fields it actually has, and 60 live rows have none. Nothing is
    #: synthesised, so a surface renders "no timestamp" rather than a false Age.
    timestamp: str | None = None
    #: Which field `timestamp` came from. None exactly when `timestamp` is.
    timestamp_field: str | None = None
    #: Every field this record's stores declare -- `unlock_count`, `priority`,
    #: `track`, `form`, `gates`, `verdict` -- each naming where it was read and
    #: flagging where two stores disagree. Fields no store holds are absent
    #: from the map rather than present and null.
    fields: tuple[FieldReading, ...] = ()
    #: The markdown file behind this record, when one exists. On a manifest
    #: record `None` is precisely the `unreadable` lane. On a bead record it
    #: names the cache the frontmatter was read from, so a reader can see which
    #: document a field came from rather than trusting `source` alone.
    body_path: str | None = None
    #: The brief body, verbatim. None means "not loaded" -- `list_briefs`
    #: deliberately leaves the *bead* body off, because fetching every bead
    #: description turns a roster read into a city-wide content read, and
    #: `show_brief` is where that belongs. A manifest record is the exception:
    #: `show`, `options`, `doctor` and `validate` all act on a bead, so the
    #: roster is the only surface a manifest row ever reaches, and a body
    #: withheld there is a body withheld everywhere. `""` means loaded and
    #: genuinely empty; `None` on a manifest record means no file exists.
    body: str | None = None
    sections: tuple[BriefSection, ...] = ()
    #: Why the parse produced what it did. A body that yields no sections
    #: reports the reason here instead of returning an empty array that
    #: reads like "this brief has no sections".
    body_diagnostics: tuple[Diagnostic, ...] = ()
    #: Every markdown document this record carries the text of, in authority
    #: order: the decisions-track file beside the manifest first, the stack
    #: file after it. `body`, `body_path` and `sections` mirror `documents[0]`,
    #: so a caller that only wants "the brief" reads exactly what it read
    #: before, and a caller that needs to see the pipeline's two copies drift
    #: apart has them both.
    #:
    #: Empty on a bead record: the roster withholds bead bodies deliberately,
    #: and listing a document whose text is not carried would report a body
    #: that is not there. `body_path` still names the cache a frontmatter field
    #: was read from.
    documents: tuple[BriefDocument, ...] = ()

    @property
    def canonical_source(self) -> str:
        """Which store is authoritative for this record.

        The bead store is canonical for a brief that has a bead. For a
        manifest-only row it is not merely unavailable -- there is no bead --
        so claiming `bead_store` would name a store that does not hold it. A
        stack-only brief is weaker still: the file the pipeline deposited is
        the only record of it anywhere, and `brief_stack` says so.
        """
        return {
            SOURCE_BEAD: CANONICAL_SOURCE_BEAD,
            SOURCE_MANIFEST: CANONICAL_SOURCE_MANIFEST,
            SOURCE_STACK: CANONICAL_SOURCE_STACK,
        }[self.source]

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "bead_id": self.bead_id,
            "body_path": self.body_path,
            "brief_id": self.brief_id,
            "canonical_source": self.canonical_source,
            "created_at": self.created_at,
            "decision_state": self.decision_state,
            "fields": field_provenance.readings_map(self.fields),
            "labels": list(self.labels),
            "policy_references": [reference.to_dict() for reference in self.policy_references],
            "redundant_artifacts": [artifact.to_dict() for artifact in self.redundant_artifacts],
            "source": self.source,
            "status": self.status,
            "timestamp": self.timestamp,
            "timestamp_field": self.timestamp_field,
            "title": self.title,
            "track": self.track,
            "updated_at": self.updated_at,
            "verdict": self.verdict.to_dict() if self.verdict is not None else None,
        }
        if self.body is not None:
            payload["body"] = self.body
            payload["sections"] = [section.to_dict() for section in self.sections]
            payload["body_diagnostics"] = [
                diagnostic.to_dict() for diagnostic in self.body_diagnostics
            ]
        if self.documents:
            payload["documents"] = [document.to_dict() for document in self.documents]
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
    """Every brief this rig can show, from both stores.

    The bead population first, then the decisions-track rows nothing else
    represents. They are concatenated rather than merged: no manifest row
    joins to a bead (`verdicts` measured that at 0 of 126 by every principled
    key), so there is nothing to merge, and a merge that never fires is a
    per-call cost plus a false suggestion that the two lanes overlap.

    Only this roster read carries manifest records. `show`, `options`,
    `doctor`, `validate`, and dispatch all act on a bead -- adjudicating,
    deferring, or cross-checking a cache against canonical state -- and a
    manifest row has no bead to act on. Listing it as decidable in those
    surfaces would be the `pending`-lane error one level up. The same holds,
    for the same reason, of the stack population.

    Three populations, not two, since the stack stopped being read only as a
    reason to throw manifest rows away. Their arithmetic is exact and each
    lane's dedup is by what the previous reader actually opened: a stack file
    a bead record resolved to, or a manifest row joined to, is not emitted
    again here. Measured 2026-08-20 that was 197 bead + 204 manifest + 41
    stack, against 197 + 158 + 0 before -- and 87 stack documents that had
    reached no surface at all now reach one.
    """
    layout = artifact_layout(ctx)
    beads = _records(ctx, layout=layout)
    manifest_reading = manifest_records(layout.legacy_manifest, layout.stack)
    records = (
        beads
        + tuple(_manifest_record(ctx, record) for record in manifest_reading.records)
        + _stack_records(ctx, layout, beads, manifest_reading)
    )
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
    records = tuple(records)
    brief_ids = {record.brief_id for record in records}
    return _legacy_gate_diagnostics(
        ctx, layout, legacy_state, brief_ids
    ) + _manifest_diagnostics(ctx, layout, records)


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



#: Where a set of decision options was parsed from. Recorded on every option
#: for the same reason `verdicts.Verdict` records it: the bead and the markdown
#: cache are different lanes with different authority, and a surface that
#: rendered them identically would assert a uniformity the corpus does not
#: have. `bead_description` is canonical (B2.4/B2.8); the two file lanes are
#: regenerable cache.
OPTION_SOURCE_BEAD_DESCRIPTION = "bead_description"
OPTION_SOURCE_STACK_FILE = "stack_file"
OPTION_SOURCE_PILE_FILE = "pile_file"


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
    #: Which of the brief's bodies these options were parsed out of.
    source: str = OPTION_SOURCE_BEAD_DESCRIPTION


# Real briefs enumerate options as list items under an options section:
#     ## §4 — Options
#     - **(A) Do it now.** *(recommended)* ...
# Scoping to the section keeps ordinary bolded prose elsewhere from
# fabricating options.
_OPTION_ITEM = re.compile(
    r"^\s*[-*]\s+\*\*\((?P<label>[A-Za-z0-9]+)\)\s*(?P<heading>[^*]+?)\*\*",
    re.MULTILINE,
)


def _heading_names_options(heading: str) -> bool:
    """True when the heading's own words say "options", whatever number it wears.

    `_classify_heading` lets an explicit `§N` prefix win over the vocabulary,
    which is right for §1 and §7 and wrong here: real briefs do not hold the
    options section at a fixed number. Across the 89 live city stack files,
    17 enumerate labeled options and only 5 head them `§4`; the rest write
    `§5 — Options`, `§6 — Options`, `§3 — Options`. Matching the number alone
    missed twelve briefs whose heading says Options in as many words.

    Reuses `_SECTION_TOKENS` rather than adding a second options vocabulary,
    so "Alternatives Considered" and "Decision options" keep resolving here
    exactly as they do everywhere else.
    """
    normalized = re.sub(r"[^a-z0-9]+", " ", heading.lower()).strip()
    for token, index in _SECTION_TOKENS:
        if token in normalized:
            return index == 4
    return False


def parse_decision_options(
    markdown: str, *, source: str = OPTION_SOURCE_BEAD_DESCRIPTION
) -> tuple[BriefDecisionOption, ...]:
    """Extract the decision options a brief offers, if any.

    Scoped to the brief's options *section* -- §4, or any section whose
    heading names options -- via `parse_brief_sections`, rather than to a
    heading spelled exactly `Options`. The exact-match version found nothing
    on the live rig: the one hecke brief that enumerates options heads them
    "Options presented", and "Alternatives Considered" -- the second most
    common heading on that rig -- never matched at all.

    The scope is what keeps this honest. A bolded `**(B) …**` bullet under
    `§7 — Risks` is not an option, and live brief 243 has exactly one; so does
    the §7 of several others. Widening to the whole document would turn those
    into options and fire `MOPT001` on briefs that offered no choice.
    """
    lines = markdown.splitlines()
    options: list[BriefDecisionOption] = []
    for section in parse_brief_sections(markdown):
        if section.section_index != 4 and not _heading_names_options(section.heading):
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
                    source=source,
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
    cached = _cached_brief_file(ctx, brief_id)
    return "" if cached is None else cached[1]


def _cached_brief_file(ctx: MctlContext, brief_id: str) -> tuple[str, str] | None:
    """The brief's markdown cache, and which lane it came from."""
    document = _cached_brief_document(ctx, brief_id)
    return None if document is None else (document[0], document[2])


def _cached_brief_document(
    ctx: MctlContext, brief_id: str
) -> tuple[str, Path, str] | None:
    """The brief's markdown cache: its lane, its path, and its text.

    One lookup rule, shared by `brief_body`, `decision_options` and the
    frontmatter read, because two readers disagreeing about where a brief's
    text lives is the defect issue #65 removed. The path is returned rather
    than recomputed by a second walk for the same reason.

    The prefix form is the pipeline's own file-naming convention: the stack
    index records `source: he-a9cfa` beside `path: …/he-a9cfa-brief.md`. It is
    anchored on the whole id followed by `-`, so it cannot drift onto a
    neighbouring bead, and it is sorted so a brief with two snapshots resolves
    the same way twice.
    """
    layout = artifact_layout(ctx)
    for source, directory in (
        (OPTION_SOURCE_PILE_FILE, layout.pile),
        (OPTION_SOURCE_STACK_FILE, layout.stack),
    ):
        for path in cache_candidates(directory, brief_id):
            if not path.is_file():
                continue
            try:
                return source, path, path.read_text(encoding="utf-8")
            except OSError:
                # The file exists and cannot be read: the lane and the path are
                # still true, and `""` here means "cached, unreadable" rather
                # than "no cache", which the caller distinguishes by `is None`.
                return source, path, ""
    return None


def cache_candidates(directory: Path, brief_id: str) -> tuple[Path, ...]:
    """Every file in `directory` that this brief id addresses, in order.

    Factored out of `_cached_brief_document` so the stack dedup can ask the
    same question that lookup asks, rather than reimplementing the naming
    convention. The two must not drift: `_cached_brief_document` picks the
    first readable candidate, and `_stack_records` has to exclude *all* of
    them -- a brief whose pile copy won the lookup would otherwise have its
    stack copy emitted a second time as a brief nothing attests, which is the
    double-count the old dedup was reaching for and aimed at the wrong lane.
    """
    exact = directory / f"{brief_id}.md"
    if exact.is_file():
        return (exact,)
    try:
        return tuple(sorted(directory.glob(f"{brief_id}-*.md")))
    except OSError:
        return ()


def _bead_for(ctx: MctlContext, brief_id: str) -> Bead | None:
    return next((bead for bead in _beads(ctx) if bead.id == brief_id), None)


def decision_options(
    ctx: MctlContext, brief_id: str, body: str | None = None
) -> tuple[BriefDecisionOption, ...]:
    """Decision options for a brief, read from wherever the brief wrote them.

    Two sources, in B2.4/B2.8 order: the canonical bead description first, the
    markdown cache second. Both are needed, because the two lanes hold
    almost-disjoint populations. Measured across the live city on 2026-08-19:
    **1 of 280** decision beads carries labeled options in its `description`,
    while **17 of 89** city stack files do -- and all 17 are `form: full`. A
    reader that consults only the bead sees one brief; a reader that consults
    only the file loses the canonical lane the pipeline is migrating onto.

    Every option records its `source`, so a front end can show provenance
    instead of implying the cache and the bead speak with the same authority.
    When both offer options and they disagree, the bead wins and the
    disagreement is reported as `MOPT003` -- see `decision_options_report`.

    `body` lets a caller that already read the body pass it in, so resolving
    options costs no additional `bd` subprocess.
    """
    return decision_options_report(ctx, brief_id, body)[0]


def decision_options_report(
    ctx: MctlContext, brief_id: str, body: str | None = None
) -> tuple[tuple[BriefDecisionOption, ...], tuple[Diagnostic, ...]]:
    """`decision_options`, plus the reason to distrust what it returned.

    Split out for the same reason `brief_options_report` is: a caller that
    only wants the options should not have to handle diagnostics, and a
    caller that has to explain the answer to an operator needs the fact that
    the two lanes disagree -- which resolving silently in the bead's favour
    would destroy.
    """
    cached = _cached_brief_file(ctx, brief_id)
    cache_source, cache_text = cached if cached is not None else (None, "")
    resolved = brief_body(ctx, brief_id) if body is None else body
    # `brief_body` already applies B2.4/B2.8, so `resolved` is the description
    # whenever there is one. Comparing against the cache text is what says
    # which of the two it turned out to be -- no second bead read required.
    resolved_source = (
        cache_source
        if cache_source is not None and resolved == cache_text
        else OPTION_SOURCE_BEAD_DESCRIPTION
    )
    primary = (
        parse_decision_options(resolved, source=resolved_source) if resolved.strip() else ()
    )
    secondary: tuple[BriefDecisionOption, ...] = ()
    if cache_source is not None and cache_text.strip() and cache_text != resolved:
        secondary = parse_decision_options(cache_text, source=cache_source)
    if not primary:
        return secondary, ()
    if not secondary or _option_labels(primary) == _option_labels(secondary):
        return primary, ()
    return primary, (
        _diagnostic(
            ctx,
            Severity.WARN,
            "MOPT003",
            "The bead and its markdown cache offer different decision options; "
            "the bead is canonical and was used.",
            brief_id=brief_id,
            data_location=_canonical_bead_location(ctx),
            detail=(
                f"{resolved_source}=" + ", ".join(sorted(_option_labels(primary)))
                + f"; {cache_source}=" + ", ".join(sorted(_option_labels(secondary)))
            ),
            suggested_next_command=f"mctl briefs doctor {brief_id} --json",
        ),
    )


def _option_labels(options: Iterable[BriefDecisionOption]) -> frozenset[str]:
    return frozenset(option.label.upper() for option in options)


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
            # An operator who names a bead B2.1 exempted deserves to be told
            # that, not "no such brief" -- the bead is right there, it is
            # simply a standalone decision bead. `MBRF010` still fires for an
            # id that names nothing at all.
            exempt = next(
                (bead for bead in beads if bead.id == brief_id and bead.is_brief and non_brief_code(bead)),
                None,
            )
            if exempt is None:
                raise BriefError(
                    _diagnostic(ctx, Severity.FATAL, "MBRF010", f"No canonical brief bead named {brief_id!r} was found.", brief_id=brief_id)
                )
    bead_by_id = {bead.id: bead for bead in beads}
    diagnostics: list[Diagnostic] = []
    # A bead that left the population under B2.1 must still be accounted for.
    # Silently dropping it from every listing is indistinguishable, to an
    # operator, from losing it -- and the whole point of the exemption is that
    # these beads are fine, not that they are gone.
    for bead in beads:
        if not bead.is_brief:
            continue
        if brief_id is not None and bead.id != brief_id:
            continue
        code = non_brief_code(bead)
        if code is None:
            continue
        diagnostics.append(
            _diagnostic(
                ctx,
                Severity.INFO,
                code,
                NON_BRIEF_MESSAGES[code],
                brief_id=bead.id,
                data_location=_canonical_bead_location(ctx),
                policy_ref="B2.1",
            )
        )
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
    """The brief population: `type=decision`, minus B2.1's standalone beads.

    This filtered on `bead.is_brief` -- `issue_type == "decision"` and nothing
    else -- which counted every push-authorization receipt and kill-switch
    record as a brief, and then `MBRF004` flagged each of them for having no
    source dependency. They cannot have one: they are not deciding about
    another bead. That was 49 of the 120 open beads MBRF004 refused city-wide.

    B2.1's Definitions paragraph already exempted them; `verdicts.is_brief_bead`
    is that sentence, and this is where it applies. The beads it removes are
    reported by `_doctor_briefs` as `MBRF054`/`MBRF055` rather than vanishing.
    """
    layout = artifact_layout(ctx) if layout is None else layout
    legacy_state = legacy_manifest_state(layout) if legacy_state is None else legacy_state
    beads = _beads(ctx) if beads is None else beads
    return tuple(
        _bead_record(ctx, bead, layout, legacy_state) for bead in brief_population(beads)
    )


def _bead_record(
    ctx: MctlContext, bead: Bead, layout: ArtifactLayout, legacy_state: LegacyManifestState
) -> BriefRecord:
    decision_state = _decision_state(bead)
    cached = _cached_brief_document(ctx, bead.id)
    frontmatter = field_provenance.read_frontmatter(cached[2]) if cached is not None else {}
    return BriefRecord(
        brief_id=bead.id,
        bead_id=bead.id,
        title=bead.title,
        status=bead.status,
        decision_state=decision_state,
        labels=bead.labels,
        created_at=bead.created_at,
        updated_at=bead.updated_at,
        redundant_artifacts=scan_artifacts(layout, bead.id, decision_state, legacy_state),
        policy_references=BRIEF_POLICY_REFERENCES,
        source=SOURCE_BEAD,
        verdict=read_verdict(bead),
        fields=_bead_fields(bead, frontmatter),
        body_path=str(cached[1]) if cached is not None else None,
        # A bead has no decisions-track lane, and `updated_at` is the one date
        # every bead record can stand behind. Both are stated rather than left
        # to the reader to infer from `source`.
        track=None,
        timestamp=bead.updated_at,
        timestamp_field="updated_at" if bead.updated_at else None,
    )


def _bead_fields(bead: Bead, frontmatter: Mapping[str, str]) -> tuple[FieldReading, ...]:
    """Every exposed field a bead and its cached markdown declare.

    The bead column comes first where one exists, because the bead store is
    this record's `canonical_source`. Only `priority` and `verdict` are bd
    columns; `unlock_count`, `track`, `form` and `gates` exist nowhere in the
    bead store -- not as columns and not in `metadata`, checked across all 80
    live decision beads -- so on a bead record they are frontmatter or nothing.

    `unlock_count` in particular is **read, never derived.** Counting what a
    brief's bead unblocks returns ~0: 508 of the live store's 528 edges are
    `related`, and 1 bead in 264 carries a blocking edge. The number in the
    document was written by whoever knew what the brief unblocked.
    """
    verdict = read_verdict(bead)
    from_bead: dict[str, field_provenance.FieldValue | None] = {
        "priority": field_provenance.bead_value(bead.raw, "priority", field="priority"),
        "verdict": (
            field_provenance.FieldValue(
                verdict.text, field_provenance.SOURCE_BEAD, verdict.confidence, verdict.field
            )
            if verdict is not None
            else None
        ),
    }
    readings = []
    for name in field_provenance.EXPOSED_FIELDS:
        reading = field_provenance.reading(
            name,
            from_bead.get(name),
            field_provenance.frontmatter_value(frontmatter, name),
        )
        if reading is not None:
            readings.append(reading)
    return tuple(readings)


def _stack_records(
    ctx: MctlContext,
    layout: ArtifactLayout,
    bead_records: tuple[BriefRecord, ...],
    manifest_reading: ManifestReading,
) -> tuple[BriefRecord, ...]:
    """Stack files no bead record and no manifest row already accounts for.

    Both dedup channels are *paths another reader opened*, never a slug rule
    reimplemented here. `_cached_brief_document` addresses a stack file as
    `<bead-id>-*.md` and the manifest join addresses it by normalised stem;
    guessing either spelling a second time is how the same brief gets counted
    twice, or hidden twice.
    """
    claimed = manifest_reading.stack_paths | _bead_stack_paths(layout, bead_records)
    reading = stack_records(layout.stack, claimed=claimed)
    return tuple(_stack_record(ctx, record) for record in reading.records)


def _bead_stack_paths(
    layout: ArtifactLayout, records: Iterable[BriefRecord]
) -> frozenset[Path]:
    """Stack files a bead already addresses, as paths.

    Every candidate, not just the one `_cached_brief_document` returned: that
    lookup prefers the pile, so a brief cached in both lanes reports a pile
    `body_path` while its stack file sits there claimed by nobody. Excluding
    only the resolved path would emit that file as a brief with no bead --
    which is false, and is the double-count the old dedup was reaching for.

    Two live city-wide, both reached through the `<bead-id>-` prefix form.
    """
    return frozenset(
        path
        for record in records
        if record.bead_id is not None
        for path in cache_candidates(layout.stack, record.bead_id)
    )


def _stack_record(ctx: MctlContext, record: StackRecord) -> BriefRecord:
    """One unclaimed stack file as a brief record.

    Everything the file does not carry stays empty rather than being invented:
    no bead id, no title, no labels, no created/updated stamps, no redundant
    artifacts. An artifact scan would report caches `missing` for a brief that
    never had a bead to cache, which reads as damage rather than as absence.

    The body is carried for the reason it is carried on a manifest record: the
    roster is the only surface this record ever reaches, because `show`,
    `options`, `doctor` and `validate` all act on a bead and there is none.
    """
    documents, diagnostics = _documents(ctx, record.slug, record.documents)
    primary = documents[0] if documents else None
    return BriefRecord(
        brief_id=record.slug,
        bead_id=None,
        title=None,
        status=record.status,
        decision_state=record.decision_state,
        labels=(),
        created_at=None,
        updated_at=None,
        redundant_artifacts=(),
        policy_references=BRIEF_POLICY_REFERENCES,
        source=SOURCE_STACK,
        verdict=record.verdict,
        track=record.track,
        timestamp=record.timestamp,
        timestamp_field=record.timestamp_field,
        fields=record.fields,
        body_path=str(record.path),
        body=primary.body if primary is not None else None,
        sections=primary.sections if primary is not None else (),
        body_diagnostics=diagnostics,
        documents=documents,
    )


def _manifest_record(ctx: MctlContext, record: ManifestRecord) -> BriefRecord:
    """One manifest row as a brief record, body included.

    Everything a manifest row does not have stays empty rather than being
    filled in: no bead id, no title, no labels, no created/updated stamps, and
    no redundant artifacts -- an artifact scan would report four `missing`
    caches for a brief that never had any, which reads as damage rather than
    as absence.

    The body is the exception, and it is not an inconsistency with
    `list_briefs` withholding bead bodies. A bead-backed brief has `show`,
    `options`, `doctor` and `validate`; a manifest row has none of them,
    because every one of those acts on a bead. The roster is the only surface
    this record ever reaches, so a body withheld there is a body withheld
    everywhere -- which is precisely the state Slice 6 left 157 briefs in.

    The policy references stay, because they are the rules a reader needs to
    judge what they are looking at, and they do not depend on the store.

    A row can carry two documents -- the file beside the manifest and the stack
    file the pipeline presents from. Both are attached. `body`, `body_path` and
    `sections` mirror the first, so this record reads exactly as it did for the
    158 rows that have only one.
    """
    documents, diagnostics = _documents(ctx, record.slug, record.documents)
    primary = documents[0] if documents else None
    return BriefRecord(
        brief_id=record.slug,
        bead_id=None,
        title=None,
        status=record.status,
        decision_state=record.decision_state,
        labels=(),
        created_at=None,
        updated_at=None,
        redundant_artifacts=(),
        policy_references=BRIEF_POLICY_REFERENCES,
        source=SOURCE_MANIFEST,
        verdict=record.verdict,
        track=record.track,
        timestamp=record.timestamp,
        timestamp_field=record.timestamp_field,
        fields=record.fields,
        body_path=primary.path if primary is not None else None,
        body=primary.body if primary is not None else None,
        sections=primary.sections if primary is not None else (),
        body_diagnostics=diagnostics,
        documents=documents,
    )


def _documents(
    ctx: MctlContext,
    brief_id: str,
    documents: Iterable[tuple[str, Path, str | None, Mapping[str, str]]],
) -> tuple[tuple[BriefDocument, ...], tuple[Diagnostic, ...]]:
    """Every document a bead-less record has, each parsed into its sections.

    `brief_body_report` is not reused wholesale because its MBRF040 says the
    *bead* carries no description, and there is no bead here -- a diagnostic
    that names the wrong store is how a reader ends up looking in the wrong
    place. The parse itself is `parse_brief_sections`, the same call, so there
    is still exactly one section parser.

    Each document is parsed on its own and its diagnostics name its own path.
    A row whose stack copy has no §-headings and whose decisions-track copy
    does is a real and reportable difference between the pipeline's two copies;
    one diagnostic covering "the body" could not say which copy it meant.
    """
    parsed: list[BriefDocument] = []
    diagnostics: list[Diagnostic] = []
    for lane, path, body, _frontmatter in documents:
        sections, document_diagnostics = _document_sections(ctx, brief_id, str(path), body)
        parsed.append(BriefDocument(lane=lane, path=str(path), body=body, sections=sections))
        diagnostics.extend(document_diagnostics)
    return tuple(parsed), tuple(diagnostics)


def _document_sections(
    ctx: MctlContext, brief_id: str, location: str, body: str | None
) -> tuple[tuple[BriefSection, ...], tuple[Diagnostic, ...]]:
    if body is None:
        return (), ()
    if not body.strip():
        return (), (
            _diagnostic(
                ctx,
                Severity.WARN,
                "MBRF064",
                "Brief body file is empty, so it has no body to show.",
                brief_id=brief_id,
                data_location=location,
                policy_ref="B2.10",
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
                data_location=location,
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
                data_location=location,
                detail="headings=" + ", ".join(section.heading for section in sections),
            ),
        )
    return sections, ()


def _manifest_diagnostics(
    ctx: MctlContext,
    layout: ArtifactLayout | None = None,
    records: Iterable[BriefRecord] = (),
) -> tuple[Diagnostic, ...]:
    """Rows and stack files the read-side sources had to skip.

    WARN, not ERROR: both are supplementary read-side sources, and a row or a
    file one of them cannot use costs that brief's visibility and nothing else.
    The fail-closed reading of the manifest -- `MBRF013` plus the B2.10
    migration blocker -- is a separate, stricter pass that still runs.
    """
    layout = artifact_layout(ctx) if layout is None else layout
    reading = manifest_records(layout.legacy_manifest, layout.stack)
    stack_reading = stack_records(
        layout.stack,
        claimed=reading.stack_paths | _bead_stack_paths(layout, records),
    )
    return tuple(
        _diagnostic(
            ctx,
            Severity.WARN,
            issue.code,
            issue.message,
            data_location=(
                f"{reading.path}:{issue.line}" if issue.line is not None else str(reading.path)
            ),
            detail=issue.detail,
            policy_ref="B2.10",
        )
        for issue in reading.issues
    ) + tuple(
        _diagnostic(
            ctx,
            Severity.WARN,
            issue.code,
            issue.message,
            data_location=str(stack_reading.path),
            detail=issue.detail,
            policy_ref="B2.10",
        )
        for issue in stack_reading.issues
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
    """adjudicated / deferred / pending / malformed for one decision bead.

    `malformed` still means exactly "closed, and no verdict could be read".
    What changed in Slice 2 is what can be read: a verdict recorded only in
    `close_reason` or in the canonical `notes` block now resolves, so
    `malformed` no longer swallows briefs that were adjudicated perfectly well
    and simply written to a field nothing looked at.

    It stays a deliberately narrow judgement. A `close_reason` that supersedes,
    reports execution, or withdraws the brief is *not* read as a verdict, so
    those beads stay `malformed` -- correctly, since no verdict was ever
    recorded on them. `verdicts.read_verdict_reading` carries the code saying
    which of those it was.
    """
    status = bead.status.lower()
    if status in {"closed", "done"}:
        return "adjudicated" if _has_verdict(bead) else "malformed"
    if status == "deferred" or _defer_until(bead):
        return "deferred"
    return "pending"


def _has_verdict(bead: Bead) -> bool:
    return _verdict(bead) is not None


def _verdict(bead: Bead) -> str | None:
    """The verdict text this bead carries, or None.

    Delegates to `verdicts.read_verdict`, which reads `close_reason` -- the
    field `bd close` actually writes, non-empty on 138 of the 139 closed
    decision beads in the live city and previously never consulted -- and the
    canonical `VERDICT: ... | AUTHORIZER: ...` block in `notes`, in addition to
    the typed fields this function used to check on its own.

    It returns a plain string because callers compare it to a cached verdict
    string. Use `verdicts.read_verdict` directly for the `source` and
    `confidence` a front end needs to show provenance, and
    `verdicts.read_verdict_reading` for the typed reason a brief has no
    readable verdict.
    """
    verdict = read_verdict(bead)
    return verdict.text if verdict is not None else None


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
