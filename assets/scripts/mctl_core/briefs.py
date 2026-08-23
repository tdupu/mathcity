"""Canonical, read-only brief inspection core for mctl."""
from __future__ import annotations

from dataclasses import dataclass, replace
import re
import tomllib
from datetime import date
from pathlib import Path
from typing import Callable, Iterable, Mapping

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
from .documents import (
    CANONICAL_SOURCE_STACK_FILE,
    SOURCE_STACK_FILE,
    BriefDocument,
    DocumentReading,
    read_documents,
)
from .fields import FieldReading
from .manifest import (
    CANONICAL_SOURCE_BEAD,
    CANONICAL_SOURCE_MANIFEST,
    SOURCE_BEAD,
    SOURCE_MANIFEST,
    ManifestIssue,
)
from .verdicts import (
    NON_BRIEF_MESSAGES,
    Verdict,
    brief_population,
    declares_no_subject,
    non_brief_code,
    read_verdict,
)


@dataclass(frozen=True)
class BriefFilters:
    status: str | None = None
    label: str | None = None


#: The lanes a roster read draws from, named so a degraded answer can say
#: which half of it is missing.
#:
#: `LANE_BEADS` is the bead store, reached through a `bd` subprocess against
#: Dolt. `LANE_DOCUMENTS` is the decisions-track manifest and the brief stack
#: directory -- **files on disk, which never touch the bead store.** Keeping
#: them named apart is the whole point: a slow or dead data plane is a fact
#: about one lane, and must not be able to hide the other.
LANE_BEADS = "beads"
LANE_DOCUMENTS = "documents"

#: Which record `source` values each lane produces, so a caller reading a
#: degraded listing can tell exactly which rows are absent rather than
#: inferring it from the lane name.
LANE_SOURCES: dict[str, tuple[str, ...]] = {
    LANE_BEADS: (SOURCE_BEAD,),
    LANE_DOCUMENTS: (SOURCE_MANIFEST, SOURCE_STACK_FILE),
}

#: Human names for the stores behind each lane, used in the one sentence a
#: partial answer has to get right.
LANE_DESCRIPTIONS: dict[str, str] = {
    LANE_BEADS: "the bead store",
    LANE_DOCUMENTS: "the decisions-track manifest and the brief stack",
}


@dataclass(frozen=True)
class SourceOutcome:
    """Whether one lane of a roster read answered, and why not if it did not.

    A roster read has two independent stores behind it and, until this
    existed, exactly one way to report them: all or nothing. A `bd` read that
    timed out took the manifest rows and stack files with it even though
    those had already been read off disk -- 245 of this city's 442 records,
    lost to a query none of them ran.
    """

    lane: str
    ok: bool
    reason: str = ""
    diagnostics: tuple[Diagnostic, ...] = ()

    @property
    def sources(self) -> tuple[str, ...]:
        return LANE_SOURCES.get(self.lane, ())

    def to_dict(self) -> dict[str, object]:
        return {
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "lane": self.lane,
            "ok": self.ok,
            "reason": self.reason,
            "sources": list(self.sources),
        }


@dataclass(frozen=True)
class BriefListing:
    """A roster read, with the lanes that did not answer named.

    `records` is always what *was* read, never a truncated stand-in for what
    should have been: a lane that failed contributes no rows and one
    `SourceOutcome` saying so. A caller that ignores `degraded_sources` sees
    a smaller list; a caller that reads it can say precisely which store is
    missing from it.
    """

    records: tuple[BriefRecord, ...] = ()
    degraded_sources: tuple[SourceOutcome, ...] = ()

    @property
    def complete(self) -> bool:
        """Whether every lane answered -- the question a total most needs."""
        return not self.degraded_sources

    @property
    def reason(self) -> str:
        """One sentence naming which stores were read and which were not."""
        if self.complete:
            return ""
        return "; ".join(outcome.reason for outcome in self.degraded_sources if outcome.reason)

    def degraded_payload(self) -> list[dict[str, object]]:
        """The lane report, wire-shaped. Empty when every lane answered."""
        return [outcome.to_dict() for outcome in self.degraded_sources]


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
    """One brief, from whichever store holds it.

    Three populations reach this type, named by `source`:

    ``bead``
        a canonical decision bead, with its redundant cache artifacts.

    ``stack_file``
        a markdown brief in `.beads/briefs/stack/`. 89 live files; before this
        slice **2** were reachable, and only as some bead's cached body.

    ``manifest``
        a decisions-track row that neither of the other two represents.

    `source` is not decoration: only a bead is an attested decision record.
    Rendering a deposited markdown file exactly like a bead-backed brief would
    assert an attestation that does not exist -- and rendering a manifest row
    that way would assert one twice over, since a row is an index entry about
    a brief rather than the brief.

    Where a stack file and a manifest row describe the same brief (46 live
    pairs) they produce **one** record, sourced `stack_file`, with the row's
    readings kept beside the file's and the row named in `also_recorded_in`.
    The dedup this replaces removed those 46 rows in favour of files nothing
    read, so it subtracted 46 briefs and added none -- see `documents.py`.

    What a document record is *not* is bodiless. Slice 6 said 36 manifest rows
    had "nothing readable in it"; 35 have a markdown body beside the manifest.
    Exactly one live row has no body file, and that -- not the absence of a
    verdict -- is what `unreadable` means.

    Which is also why `bead_id` and `title` are nullable. A document record has
    neither. `""` would read as "this brief has no title"; `None` reads as
    "there is no bead here to have one", which is the true statement.
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
    #: Which store this record came from: `bead`, `stack_file` or `manifest`.
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
    #: Why this record's body is not in this payload, when a body exists and
    #: was deliberately left out. `None` means nothing was elided: either the
    #: body is here, or there is none to carry (which `body_path` tells apart).
    #: A body is never *shortened* -- an elided body is absent and labelled,
    #: because a silently truncated brief is a brief that reads as complete.
    body_elided: str | None = None
    #: Other documents describing this same brief, folded into this record --
    #: `<manifest>:<line>` for a merged decisions-track row, and that row's own
    #: markdown snapshot. Empty when this record has only one document. This is
    #: what makes deduplication auditable: a suppressed document is always
    #: named by the record that represents it, never merely absent.
    also_recorded_in: tuple[str, ...] = ()

    @property
    def canonical_source(self) -> str:
        """Which store is authoritative for this record.

        The bead store is canonical for a brief that has a bead. For a
        document record it is not merely unavailable -- there is no bead -- so
        claiming `bead_store` would name a store that does not hold it. A
        merged stack/row pair is canonical to the **stack file**: the file is
        the brief, and the row is an index entry about it.
        """
        return {
            SOURCE_BEAD: CANONICAL_SOURCE_BEAD,
            SOURCE_STACK_FILE: CANONICAL_SOURCE_STACK_FILE,
        }.get(self.source, CANONICAL_SOURCE_MANIFEST)

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "also_recorded_in": list(self.also_recorded_in),
            "bead_id": self.bead_id,
            "body_elided": self.body_elided,
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


#: Why a roster read leaves bodies out by default, and how to get one.
#: Carried on the record rather than documented only here, so a consumer
#: holding a single record can tell "no body" from "body not requested".
BODY_ELIDED_ON_ROSTER = (
    "roster read: pass --bodies (or bodies=true) to briefs list, "
    "or read this brief through briefs show"
)


class BriefError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


def list_briefs(
    ctx: MctlContext, filters: BriefFilters, *, bodies: bool = False
) -> tuple[BriefRecord, ...]:
    """The plan's declared roster signature: records, or a raised failure.

    Kept because the MCP implementation plan names it, and because a caller
    that genuinely wants all-or-nothing should be able to say so. No mctl
    surface uses it: every one of them takes `list_briefs_report`, since a
    caller that cannot see `degraded_sources` cannot tell a small city from a
    broken one -- which is the whole defect.
    """
    listing = list_briefs_report(ctx, filters, bodies=bodies)
    failure = next(
        (
            diagnostic
            for outcome in listing.degraded_sources
            for diagnostic in outcome.diagnostics
        ),
        None,
    )
    if failure is not None:
        raise BriefError(failure)
    return listing.records


def list_briefs_report(
    ctx: MctlContext,
    filters: BriefFilters,
    *,
    bodies: bool = False,
    bead_timeout: int | None = None,
    on_documents: Callable[[BriefListing], None] | None = None,
) -> BriefListing:
    """Every brief this rig can show, from all three stores, lane by lane.

    The bead population first, then the decisions-track rows nothing else
    represents. They are concatenated rather than merged: no manifest row
    joins to a bead (`verdicts` measured that at 0 of 126 by every principled
    key), so there is nothing to merge, and a merge that never fires is a
    per-call cost plus a false suggestion that the two lanes overlap.

    Only this roster read carries document records. `show`, `options`,
    `doctor`, `validate`, and dispatch all act on a bead -- adjudicating,
    deferring, or cross-checking a cache against canonical state -- and a
    stack file or manifest row has no bead to act on. Listing one as decidable
    in those surfaces would be the `pending`-lane error one level up.

    ## The document lane is read first, and it is read whatever the bead store does

    The documents used to be read *behind* the beads, and only for the beads:
    the bead population is what tells the document read which stack files are
    already spoken for, so it was computed first and the document read was
    sequenced after it. That made a file read on disk depend on a query
    against Dolt. When `hq`'s bead query went to a full partition scan and
    blew the cross-rig deadline, the rig was dropped whole and its 158
    manifest rows and 87 stack files went with it -- 245 records that never
    touched the store that was slow, city total 442 to 8.

    So the order is inverted. The document lane runs first with an empty
    claim map, costs ~27 ms of file I/O against ~2.8 s for `hq`'s bead read,
    and is handed to `on_documents` the moment it exists. A cross-rig caller
    publishes that as its partial answer, so a deadline that expires during
    the bead read returns the document half instead of nothing.

    If the bead read then succeeds, the documents are re-read *with* the
    claim map, because suppressing a stack file a bead already carries is a
    fact about the pair and cannot be derived from the file alone. That
    second pass is the only cost this ordering adds -- 27 ms on the largest
    rig, nothing at all on the fourteen rigs that have no documents -- and it
    keeps a healthy listing byte-identical to what it was.

    If the bead read fails, the document half is returned with a
    `SourceOutcome` naming the bead store as unread. Nothing is suppressed
    then, and that is correct rather than a compromise: the two stack files a
    bead normally claims have no bead row to be duplicates *of*, so emitting
    them is the only way they appear at all.

    ## `bodies` defaults to off, and that is a payload decision

    Slice 7 put every manifest row's body and its parsed sections on the
    roster, taking `briefs list --all-rigs --json` from ~0.4 MB to 2.7 MB.
    Adding the stack population -- whose files are far larger, median 8,771
    bytes against the decisions-track median of ~3,000 -- measured **5.17 MB**,
    past the point where a roster read is a content read for every caller that
    wanted titles.

    So bodies are opt-in here and always present on `show_brief`. A record
    whose body was left out says so in `body_elided`; nothing is truncated,
    because a shortened brief still reads as a whole one.
    """
    layout = artifact_layout(ctx)

    def keep(records: Iterable[BriefRecord]) -> tuple[BriefRecord, ...]:
        return tuple(record for record in records if _matches(record, filters))

    # Claim map deliberately empty: nothing has been read from the bead store
    # yet, so nothing can be claimed. Two live stack files are affected.
    documents_alone = _document_records(ctx, (), layout, bodies=bodies)
    if on_documents is not None:
        on_documents(
            BriefListing(
                records=keep(documents_alone),
                degraded_sources=(_lane_unanswered(LANE_BEADS, LANE_DOCUMENTS),),
            )
        )
    try:
        beads = _records(ctx, layout=layout, timeout=bead_timeout)
    except BriefError as error:
        return BriefListing(
            records=keep(documents_alone),
            degraded_sources=(
                _lane_failed(LANE_BEADS, LANE_DOCUMENTS, error.diagnostic),
            ),
        )
    documents = _document_records(ctx, beads, layout, bodies=bodies)
    return BriefListing(records=keep(beads + documents))


def _lane_read(lane: str) -> str:
    return LANE_DESCRIPTIONS.get(lane, lane)


def _lane_unanswered(lane: str, read: str) -> SourceOutcome:
    """The lane has not answered *yet*, published mid-read.

    Only ever observed by a caller whose deadline expired before the read
    finished, so the sentence is written for that reader: it says what is in
    the rows they are holding and what is not.
    """
    return SourceOutcome(
        lane=lane,
        ok=False,
        reason=(
            f"{_lane_read(lane)} had not answered when this partial answer was "
            f"published; {_lane_read(read)} were read"
        ),
    )


def _lane_failed(lane: str, read: str, diagnostic: Diagnostic) -> SourceOutcome:
    return SourceOutcome(
        lane=lane,
        ok=False,
        reason=(
            f"{_lane_read(lane)} could not be read ({diagnostic.message}); "
            f"{_lane_read(read)} were read"
        ),
        diagnostics=(diagnostic,),
    )


def show_brief(ctx: MctlContext, brief_id: str) -> BriefRecord:
    """One brief, with its body -- the decision evidence -- attached.

    Detail is where the body belongs. `list_briefs` deliberately leaves it
    off: a city-wide roster read that also fetched ~200 brief bodies would be
    a performance regression for every caller that only wanted the titles.

    The bead snapshot this already reads carries the description, so
    attaching the body costs no extra `bd` subprocess.

    Document records are served here too, and that is what makes the roster's
    body elision safe: a stack file or a manifest row reaches no other detail
    surface -- `options`, `doctor`, `validate` and dispatch all act on a bead
    -- so if `show` did not carry their bodies, leaving bodies off the roster
    would put 247 briefs back in the state Slice 7 found them in.
    """
    beads = _beads(ctx)
    bead_records = _records(ctx, beads)
    documents = _document_records(ctx, bead_records, bodies=True)
    record = _find_record(ctx, bead_records + documents, brief_id)
    if record.source != SOURCE_BEAD:
        # Already whole: `_document_record` read the file, parsed its sections
        # and reported why a parse yielded nothing. Re-deriving the body from
        # a bead here would look up a bead that does not exist.
        return record
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
    ) + _document_diagnostics(ctx, layout, records)


def empty_scope_diagnostic(ctx: MctlContext) -> Diagnostic:
    """A rig-scoped read that came back empty names that fact, not just the emptiness.

    `#103`: `briefs list` / `briefs doctor` returned `briefs: []` for a rig
    with no briefs indistinguishably from a rig asked with the wrong scope --
    the reader who filed the issue nearly reported mctl as blind for exactly
    this reason, three minutes from filing before running the discriminator
    (`--all-rigs`) themselves. This does not compute the discriminator's
    answer -- doing that here would mean this single-rig call reaching across
    rig boundaries, the same shape of extra cost that dropped `hq` whole when
    a cross-rig deadline was too tight (see `list_briefs_report`'s own
    docstring) -- it names the check that would answer it.

    Shared by the MCP handlers and the CLI's single-rig `list`/`doctor`
    commands, both of which call `list_briefs_report`/`doctor_briefs` and
    both of which must name the same gap: a caller reading only one lane
    should not have to know there is a second lane to check.
    """
    return Diagnostic(
        severity=Severity.INFO,
        code="MCTL_BRIEFS_SCOPE_EMPTY",
        message=f"Rig {ctx.rig_id!r} has no briefs matching this read.",
        hint="Re-run with all_rigs=true (--all-rigs on the CLI) to check whether this is empty because of scope or because the city is.",
        facts={
            "city_path": str(ctx.city_root),
            "rig_name": ctx.rig_id,
            "implementation_provenance": "mctl empty-scope discriminator hint",
        },
        trace_id=ctx.trace_id,
    )


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
    # `ambiguous` counts as existing (#128). MBRF021 asks whether the bead has
    # NO cache artifact; an ambiguous pile means TWO files match, not zero.
    # Testing only for "present" would report "no redundant cache artifact"
    # about a brief that has two of them -- a false diagnostic introduced by
    # the fix for a false diagnostic.
    if not any(
        artifact.state in {"present", "ambiguous"}
        for artifact in record.redundant_artifacts
    ):
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

    The rule itself is `cached_brief_documents`; this is its first answer,
    read.
    """
    for source, path in cached_brief_documents(ctx, brief_id):
        try:
            return source, path, path.read_text(encoding="utf-8")
        except OSError:
            # The file exists and cannot be read: the lane and the path are
            # still true, and `""` here means "cached, unreadable" rather
            # than "no cache", which the caller distinguishes by `is None`.
            return source, path, ""
    return None


def cached_brief_documents(
    ctx: MctlContext, brief_id: str
) -> tuple[tuple[str, Path], ...]:
    """**Every** markdown cache this brief owns, pile lane before stack lane.

    The naming rule itself, in one place. `_cached_brief_document` is this
    function's first entry, so readers keep the single answer they have always
    had while a writer can reach all of them.

    The prefix form is the pipeline's own file-naming convention: the stack
    index records `source: he-a9cfa` beside `path: …/he-a9cfa-brief.md`. It is
    anchored on the whole id followed by `-`, so it cannot drift onto a
    neighbouring bead, and it is sorted so a brief with two snapshots resolves
    the same way twice.

    A writer needs all of them. Leaving a second copy carrying the
    pre-adjudication `status:` is the drift #77 is about, one directory over --
    and the pile and stack copies of one brief are exactly the pair that
    `brief-shuffle` is mid-move on when it is interrupted.
    """
    layout = artifact_layout(ctx)
    documents: list[tuple[str, Path]] = []
    for source, directory in (
        (OPTION_SOURCE_PILE_FILE, layout.pile),
        (OPTION_SOURCE_STACK_FILE, layout.stack),
    ):
        exact = directory / f"{brief_id}.md"
        candidates = [exact] if exact.is_file() else sorted(directory.glob(f"{brief_id}-*.md"))
        documents.extend((source, path) for path in candidates if path.is_file())
    return tuple(documents)


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
            # B2.1a: a brief that DECLARES it is about no bead is compliant.
            # A brief that merely omits the link is not -- silence must not
            # become compliance, or the diagnostic becomes a no-op for the
            # omissions it exists to surface. The declaring brief still gets a
            # record: dropping it silently from the diagnostics would be
            # indistinguishable from never having checked it, the same reason
            # the B2.1 exemptions above emit MBRF054/MBRF055.
            if declares_no_subject(bead):
                diagnostics.append(_diagnostic(ctx, Severity.INFO, "MBRF056", "Brief declares no bead subject.", brief_id=record.brief_id, data_location=_canonical_bead_location(ctx), policy_ref="B2.1a"))
            else:
                diagnostics.append(_diagnostic(ctx, Severity.WARN, "MBRF004", "Brief bead has no source dependency.", brief_id=record.brief_id, data_location=_canonical_bead_location(ctx), policy_ref="B2.1"))
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
    timeout: int | None = None,
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
    beads = _beads(ctx, timeout=timeout) if beads is None else beads
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
    return field_provenance.readings(
        {name: value for name, value in from_bead.items() if value is not None},
        field_provenance.frontmatter_store(frontmatter),
    )


def _claimed_stack_files(
    layout: ArtifactLayout, records: Iterable[BriefRecord]
) -> dict[Path, str]:
    """Stack files a bead already owns, keyed by path, valued by that bead's id.

    Ownership is the naming rule `_cached_brief_document` uses -- `<id>.md` or
    `<id>-*.md`, anchored on the whole id followed by `-` -- applied to every
    bead in the population, and **not** merely to the cache each bead happens
    to be showing. `_cached_brief_document` searches the pile first, so a bead
    with copies in both lanes reports the pile path; claiming only that would
    leave the stack copy to be emitted as an independent brief under the
    bead's own id, which is the duplicate this whole slice is about avoiding.

    Matching is by path rather than by slug because these filenames carry a
    bead id, not a slug: `gt-1f2781-downstream-filter-…-brief` normalises to
    something no manifest row holds, so a slug comparison would never see it.
    """
    bead_ids = sorted(
        (record.brief_id for record in records if record.source == SOURCE_BEAD),
        key=len,
        reverse=True,
    )
    claimed: dict[Path, str] = {}
    for record in records:
        if record.source == SOURCE_BEAD and record.body_path:
            claimed[Path(record.body_path)] = record.brief_id
    try:
        entries = sorted(layout.stack.glob("*.md"))
    except OSError:
        return claimed
    for path in entries:
        if path in claimed:
            continue
        # Longest id first, so `mc-open-2` claims its own file rather than
        # `mc-open` claiming it through the prefix rule.
        owner = next(
            (
                bead_id
                for bead_id in bead_ids
                if path.stem == bead_id or path.stem.startswith(f"{bead_id}-")
            ),
            None,
        )
        if owner is not None:
            claimed[path] = owner
    return claimed


def _document_reading(
    ctx: MctlContext,
    layout: ArtifactLayout | None = None,
    records: Iterable[BriefRecord] = (),
) -> DocumentReading:
    layout = artifact_layout(ctx) if layout is None else layout
    return read_documents(
        layout.legacy_manifest, layout.stack, claimed=_claimed_stack_files(layout, records)
    )


def _document_records(
    ctx: MctlContext,
    beads: Iterable[BriefRecord] = (),
    layout: ArtifactLayout | None = None,
    *,
    bodies: bool = True,
) -> tuple[BriefRecord, ...]:
    """Every stack file and decisions-track row no bead already carries.

    Read per rig, from that rig's own manifest and its own stack directory, so
    a city-wide listing is still exactly the per-rig answers assembled. Most
    rigs have neither and contribute nothing.
    """
    reading = _document_reading(ctx, layout, beads)
    return tuple(
        _document_record(ctx, document, bodies=bodies) for document in reading.records
    )


def _document_record(
    ctx: MctlContext, document: BriefDocument, *, bodies: bool = True
) -> BriefRecord:
    """One brief document -- stack file, manifest row, or the two merged.

    Everything a document does not have stays empty rather than being filled
    in: no bead id, no title, no labels, no created/updated stamps, and no
    redundant artifacts -- an artifact scan would report four `missing` caches
    for a brief that never had any, which reads as damage rather than absence.

    The body is the exception, and it is not an inconsistency with
    `list_briefs` withholding bead bodies. A bead-backed brief has `show`,
    `options`, `doctor` and `validate`; a document has none of them, because
    every one of those acts on a bead. The roster is the only surface this
    record ever reaches, so a body withheld there is a body withheld
    everywhere -- which is precisely the state 87 stack files were left in.

    The policy references stay, because they are the rules a reader needs to
    judge what they are looking at, and they do not depend on the store.
    """
    sections, diagnostics = (
        _document_body_report(ctx, document) if bodies else ((), ())
    )
    elided = (
        None if bodies or document.body is None else BODY_ELIDED_ON_ROSTER
    )
    return BriefRecord(
        brief_id=document.brief_id,
        bead_id=None,
        title=None,
        status=document.status,
        decision_state=document.decision_state,
        labels=(),
        created_at=None,
        updated_at=None,
        redundant_artifacts=(),
        policy_references=BRIEF_POLICY_REFERENCES,
        source=document.source,
        verdict=document.verdict,
        track=document.track,
        timestamp=document.timestamp,
        timestamp_field=document.timestamp_field,
        fields=document.fields,
        body_path=str(document.body_path) if document.body_path is not None else None,
        body=document.body if bodies else None,
        sections=sections,
        body_diagnostics=diagnostics,
        body_elided=elided,
        also_recorded_in=document.also_recorded_in,
    )


def _document_body_report(
    ctx: MctlContext, document: BriefDocument
) -> tuple[tuple[BriefSection, ...], tuple[Diagnostic, ...]]:
    """Sections for a document's body, via the one section parser.

    `brief_body_report` is not reused wholesale because its MBRF040 says the
    *bead* carries no description, and there is no bead here -- a diagnostic
    that names the wrong store is how a reader ends up looking in the wrong
    place. The parse itself is `parse_brief_sections`, the same call, so there
    is still exactly one section parser.
    """
    body = document.body
    if body is None:
        return (), ()
    location = str(document.body_path)
    if not body.strip():
        return (), (
            _diagnostic(
                ctx,
                Severity.WARN,
                "MBRF064",
                "Brief body file is empty, so this record has no body to show.",
                brief_id=document.brief_id,
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
                brief_id=document.brief_id,
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
                brief_id=document.brief_id,
                data_location=location,
                detail="headings=" + ", ".join(section.heading for section in sections),
            ),
        )
    return sections, ()


def _document_diagnostics(
    ctx: MctlContext,
    layout: ArtifactLayout | None = None,
    records: Iterable[BriefRecord] = (),
) -> tuple[Diagnostic, ...]:
    """Documents the reader could not use, and pairs stored twice differently.

    WARN, not ERROR: the stack and the manifest are supplementary read-side
    sources, and a document either of them cannot use costs that brief's
    visibility and nothing else. The fail-closed reading of the manifest --
    `MBRF013` plus the B2.10 migration blocker -- is a separate, stricter pass
    that still runs.
    """
    layout = artifact_layout(ctx) if layout is None else layout
    reading = _document_reading(ctx, layout, records)
    manifest_path = layout.legacy_manifest
    return tuple(
        _diagnostic(
            ctx,
            Severity.WARN,
            issue.code,
            issue.message,
            data_location=_issue_location(issue, manifest_path),
            detail=issue.detail,
            policy_ref="B2.10",
        )
        for issue in reading.issues
    )


def _issue_location(issue: ManifestIssue, manifest_path: Path) -> str:
    """Where an operator should look for the document an issue is about.

    A stack-file issue names its own file; a manifest-row issue names the
    manifest and the line, because a row has no other address.
    """
    if issue.location is not None:
        return issue.location
    return f"{manifest_path}:{issue.line}" if issue.line is not None else str(manifest_path)


def _beads(ctx: MctlContext, *, timeout: int | None = None) -> tuple[Bead, ...]:
    """The rig's bead store, or MBRF012 naming why it would not answer.

    `timeout` lets a caller working against a wall clock of its own bound the
    `bd` subprocess below its remaining budget. Without it the default is 30 s
    -- *above* the 25 s cross-rig deadline -- so on a slow store the fan-out
    always gave up before this read could report its own failure, and the
    caller got "the rig did not answer" instead of "the bead store did not".
    """
    try:
        return read_beads(
            ctx.rig_root,
            fixture_path=ctx.beads_fixture,
            timeout=timeout,
            # B2.1: only a decision bead can be a brief, so the other 99.7% of
            # the store was fetched, parsed, and thrown away. See read_beads.
            issue_type="decision",
        )
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
