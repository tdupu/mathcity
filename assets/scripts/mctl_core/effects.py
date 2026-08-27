"""Dry-run-first effect planning for mctl mutations."""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import fcntl
import hashlib
import json
import os
import re
import tempfile
import tomllib
from pathlib import Path
from typing import Mapping, Sequence

from .beads import (
    BD_LIST_ARGS,
    BeadCreate,
    BeadRaceLostError,
    BeadReadError,
    BeadRelate,
    BeadUpdate,
    BeadWriteError,
    apply_bead_comment,
    apply_bead_create,
    apply_bead_relate,
    apply_bead_update,
    priority_from_labels,
    read_beads,
    verify_relation,
)
from .github_issues import (
    GithubIssueError,
    create_issue,
    edit_issue,
    fetch_issue,
    required_template_sections,
    rig_for_issue,
)
from .briefs import (
    cached_brief_documents,
    decision_options,
    doctor_briefs,
    legacy_gate_diagnostics,
    show_brief,
    validate_brief_input,
)
from .context import MctlContext
from .commission import brief_labels, tracker_metadata, validate_commission
from .diagnostics import Diagnostic, Severity
from .events import append_jsonl
from .materialize_plan import FRONTMATTER_LINE
from .redundant_state import ArtifactLayout, artifact_layout
from .trace import append_aborted, append_applied, append_planned, trace_path


#: Verdicts that send a brief BACK rather than ratifying it.
#:
#: The doctor's ERROR diagnostics are preconditions for *accepting* a brief:
#: they say the bead is not in a state where an approval would mean anything.
#: They are not preconditions for returning one. A brief with no body and no
#: source dependency is precisely the brief you revise, and refusing the
#: revision because the body is missing leaves the operator with no move at
#: all -- the queue's malformed population then cannot be cleared by the one
#: person authorised to clear it.
#:
#: So for these verdicts the blocking diagnostics are demoted to advisories:
#: still reported, still on the record, no longer a veto.
RETURN_VERDICTS = frozenset({"revise", "reject"})

VALID_VERDICTS = {
    "accept": "approve",
    "accepted": "approve",
    "approve": "approve",
    "approved": "approve",
    "reject": "reject",
    "rejected": "reject",
    "revise": "revise",
    "revision": "revise",
}


@dataclass(frozen=True)
class CacheUpdate:
    kind: str
    path: Path
    target_brief_id: str
    fields: Mapping[str, str]
    #: `decisions_track_row` only: the `n` of the legacy manifest row this
    #: update rewrites, resolved at plan time from the brief's stack index row
    #: (`legacy_n`, or the `NNN-` prefix of `legacy_source`).
    #:
    #: Resolved in the plan rather than at apply time so a dry run names the
    #: exact row it would touch. The legacy inventory is append-shaped and read
    #: by other tools; "some row matching this brief" is not a decision to
    #: leave to a writer that already has the file open.
    row_key: str = ""
    #: Keys this update REMOVES from the row. A terminal verdict clears
    #: `defer_until`, or a brief deferred and then approved keeps a defer
    #: window that outlived the decision it belonged to.
    drop_fields: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "fields": dict(sorted(self.fields.items())),
            "kind": self.kind,
            "path": str(self.path),
            "target_brief_id": self.target_brief_id,
        }
        # Absent unless they carry something: every existing consumer of this
        # payload was written against the four keys above, and a `row_key: ""`
        # on every decision-TOML update would be noise in the trace.
        if self.row_key:
            payload["row_key"] = self.row_key
        if self.drop_fields:
            payload["drop_fields"] = list(self.drop_fields)
        return payload


@dataclass(frozen=True)
class FileCreate:
    """A redundant cache file this operation brings into existence.

    Distinct from CacheUpdate: an update merges fields into a file that may
    already exist, while a create must refuse to touch one that does. The
    content is summarized rather than inlined so a dry-run plan stays readable
    for a brief body of any size.
    """

    kind: str
    path: Path
    content: str

    def to_dict(self) -> dict[str, object]:
        return {
            "content_bytes": len(self.content.encode("utf-8")),
            "content_sha256": hashlib.sha256(self.content.encode("utf-8")).hexdigest(),
            "kind": self.kind,
            "path": str(self.path),
        }


@dataclass(frozen=True)
class GithubWrite:
    """A GitHub tracker mutation this plan intends to make (#185).

    Distinct from every bead/cache effect: it touches no store, it shells `gh`,
    and it is the one effect whose target lives outside the city. `kind` is
    `create` (a new issue) or `edit` (an additive body rewrite, #52). The body
    is carried in full so a dry-run PREVIEW shows exactly what would be posted --
    for `edit` that is the whole point, since the operator must be able to see
    byte-for-byte that the original body is preserved and only appended to.
    """

    kind: str
    repo: str
    body: str
    title: str | None = None
    labels: tuple[str, ...] = ()
    number: int | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "kind": self.kind,
            "repo": self.repo,
            "body": self.body,
            "body_bytes": len(self.body.encode("utf-8")),
            "body_sha256": hashlib.sha256(self.body.encode("utf-8")).hexdigest(),
            "labels": list(self.labels),
        }
        if self.title is not None:
            payload["title"] = self.title
        if self.number is not None:
            payload["issue_number"] = self.number
        return payload


@dataclass(frozen=True)
class JsonlWrite:
    kind: str
    path: Path
    row: Mapping[str, object]

    def to_dict(self) -> dict[str, object]:
        return {"kind": self.kind, "path": str(self.path), "row": dict(self.row)}


@dataclass(frozen=True)
class BeadComment:
    """An append-only comment on an existing bead (mc-ilia).

    The typed surface's one way to CORRECT a record without rewriting it: the
    bead's description is never touched, so a refuted claim stays readable beside
    its correction rather than being silently overwritten. Wraps `bd comment`,
    which stamps its own author and time. `text` is carried in full so a dry-run
    shows exactly what would be appended.
    """

    bead_id: str
    text: str

    def to_dict(self) -> dict[str, object]:
        return {
            "bead_id": self.bead_id,
            "text": self.text,
            "text_bytes": len(self.text.encode("utf-8")),
        }


@dataclass(frozen=True)
class EffectPlan:
    trace_id: str
    operation: str
    target_brief_id: str
    preconditions: tuple[Diagnostic, ...]
    bead_updates: tuple[BeadUpdate, ...]
    cache_updates: tuple[CacheUpdate, ...]
    event_writes: tuple[JsonlWrite, ...]
    trace_writes: tuple[JsonlWrite, ...]
    # Creation-only. `preconditions` blocks the mutation outright, so advice
    # that should reach the operator without refusing the write lives here.
    bead_creates: tuple[BeadCreate, ...] = ()
    file_creates: tuple[FileCreate, ...] = ()
    advisories: tuple[Diagnostic, ...] = ()
    # Applied after `bead_creates`, so an edge may name a bead this plan is
    # about to mint: `BeadRelate` ids go through the same placeholder
    # substitution derived paths do.
    bead_relates: tuple[BeadRelate, ...] = ()
    # GitHub tracker writes (#185). Empty for every bead/brief mutation; the
    # only effects that leave the city.
    github_writes: tuple[GithubWrite, ...] = ()
    # Append-only comments on existing beads (mc-ilia). Empty for every create
    # and every brief verdict; the only effect that corrects a record in place
    # without editing it.
    bead_comments: tuple[BeadComment, ...] = ()

    def to_dict(self) -> dict[str, object]:
        return {
            "advisories": [diagnostic.to_dict() for diagnostic in self.advisories],
            "bead_comments": [comment.to_dict() for comment in self.bead_comments],
            "bead_creates": [create.to_dict() for create in self.bead_creates],
            "bead_relates": [relate.to_dict() for relate in self.bead_relates],
            "bead_updates": [update.to_dict() for update in self.bead_updates],
            "cache_updates": [update.to_dict() for update in self.cache_updates],
            "event_writes": [write.to_dict() for write in self.event_writes],
            "file_creates": [create.to_dict() for create in self.file_creates],
            "github_writes": [write.to_dict() for write in self.github_writes],
            "operation": self.operation,
            "preconditions": [diagnostic.to_dict() for diagnostic in self.preconditions],
            "target_brief_id": self.target_brief_id,
            "trace_id": self.trace_id,
            "trace_writes": [write.to_dict() for write in self.trace_writes],
        }


@dataclass(frozen=True)
class ApplyResult:
    trace_id: str
    effect_plan: EffectPlan
    actual_effects: tuple[Mapping[str, object], ...]
    diagnostics: tuple[Diagnostic, ...]

    def to_dict(self) -> dict[str, object]:
        return {
            "actual_effects": [dict(effect) for effect in self.actual_effects],
            "applied": True,
            "diagnostics": [diagnostic.to_dict() for diagnostic in self.diagnostics],
            "effect_plan": self.effect_plan.to_dict(),
            "trace_id": self.trace_id,
        }


class MutationError(Exception):
    def __init__(self, diagnostic: Diagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic


class StackIndexRowUnwritable(OSError):
    """No stack-index row matched the brief this write targeted.

    NOT a failed adjudication. The stack-index update is planned whenever the
    index FILE exists, so a brief with no row -- an archived one, for instance,
    which is de-indexed by construction under B2.15 -- plans a write that
    correctly matches nothing. The caller downgrades this to a per-brief WARN.

    It is raised rather than returned so the no-match cannot be dropped by a
    caller that ignores a return value, which is how #92 stayed invisible.
    """


class DecisionsTrackRowUnwritable(OSError):
    """The legacy manifest row this verdict should sync cannot be rewritten.

    An `OSError` subclass for the same reason `BriefFrontmatterUnwritable` is:
    every cache path already degrades per-brief on `OSError`, so a caller that
    has not learned about this case still fails per-brief rather than taking
    the adjudication down with it.

    Raised only when a row was *expected* -- the stack index named a
    `legacy_n` -- and the manifest cannot honour it: the row is gone, two rows
    claim the same `n`, or the file cannot be read. A brief with no legacy row
    at all is the ordinary stack-track case and plans no update, so it never
    reaches this exception.
    """


class BriefFrontmatterUnwritable(OSError):
    """This document has no frontmatter block a writer can rewrite faithfully.

    An `OSError` subclass on purpose. Every existing cache path already
    degrades on `OSError` rather than crashing, so a caller that has not
    learned about this case still fails per-brief instead of taking the
    adjudication down with it. `_apply_effects` catches it first, to report
    the WARN it deserves rather than the ERROR a real I/O failure deserves.
    """



def _pile_document(body: str) -> str:
    """The created document, WITH a frontmatter block adjudication can write into.

    Created documents used to be the raw body. Nothing reads a brief's status from
    the body, so `briefs_relay_adjudication` had no header to rewrite and raised
    `BriefFrontmatterUnwritable` -- at WARN, after the verdict had already landed
    on the bead. The operation reported success with one representation silently
    stale, and `classify_tier` (materialize_plan.py:292-298), which reads verdict,
    adjudicated_by and adjudicated_at from THIS block, saw an empty mapping. So an
    adjudicated brief classified `C-no-disposition`, and materialize_plan.py:379
    turns that tier into `status="open"` -- a decided brief re-materializing as open
    work.

    `status: open` and not `ready-for-adjudication`: the decision_toml written by
    this same call says `open`, and two representations created in one operation
    disagreeing on their own status is the defect the five-representation work
    exists to prevent.

    A body that already opens with its own block is passed through untouched --
    callers that supply frontmatter are honoured rather than given a second one.
    """
    if body.lstrip().startswith("---"):
        return body
    return f"---\nstatus: open\n---\n\n{body}"


@dataclass(frozen=True)
class BriefCreateInput:
    title: str
    body: str
    labels: tuple[str, ...]
    requested_by: str | None
    # Not in the plan's four-field sketch, but B2.1 makes a brief without a
    # source link malformed, and every downstream mctl command refuses to act
    # on a malformed brief. Optional, so creation without one still works and
    # warns instead of silently minting an unusable brief.
    sources: tuple[str, ...] = ()
    # Caller-supplied provenance, written onto the bead alongside mctl's own.
    # `commission_brief` (#190) carries tracker facts here -- `gh.issue`,
    # `gh.repo`, `gh.labels` -- rather than as bd labels, because GitHub labels
    # are namespaced (`kind/bug`) and bd rejects slashes as label tokens
    # (MBRF033). Dropping the namespace is lossy: `kind/bug` and `status/bug`
    # collapse to one token. Metadata values have no such restriction and stay
    # queryable via `--has-metadata-key`.
    metadata: Mapping[str, str] = field(default_factory=dict)


# The plan cannot name the bead it is about to create, because bd mints the
# id. Derived paths are planned against this token and rewritten once bd has
# answered.
NEW_BRIEF_ID_PLACEHOLDER = "(pending-bead-id)"


def plan_create_brief(ctx: MctlContext, request: BriefCreateInput) -> EffectPlan:
    """Plan a bead-first brief creation.

    The canonical decision bead is the only thing that must exist for the
    brief to exist (B2.8); the pile markdown and the decision TOML are cache
    written afterwards. The presentable stack index is deliberately NOT
    written: B2.10 makes brief-shuffle the single `.pile -> stack` writer.
    """
    title, body, labels = validate_brief_input(
        ctx, request.title, request.body, request.labels
    )
    # Creation is a mutation, so the same legacy-migration gate that blocks
    # adjudication blocks it. Doctor's per-brief findings are deliberately not
    # consulted: an unrelated malformed brief must not make the rig unable to
    # accept new ones.
    preconditions = _blocking_preconditions(legacy_gate_diagnostics(ctx))
    advisories: list[Diagnostic] = []
    if not request.sources:
        # #173, Taylor's ruling. This was a WARN in `advisories` -- reported to
        # the operator without blocking -- and warning did not stop the brick.
        #
        # A brief created without a source is made its OWN source bead at
        # dispatch time (work.py:636); `briefs_relay_adjudication` then closes that bead,
        # because closing the brief is what adjudication IS. So approving the
        # brief is what makes it permanently undispatchable -- and CT4.5
        # MANDATES adjudicating before dispatch. The tool was minting briefs
        # whose prescribed next step destroys them.
        #
        # A refusal at creation is CT13.4 working; a brick at approval is the
        # failure mode. Only the SEVERITY was ever wrong: the code already named
        # the right condition and cited the right policy.
        preconditions = preconditions + (
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MBRF034",
                "Created brief has no source dependency, so it is B2.1-incomplete.",
                brief_id=NEW_BRIEF_ID_PLACEHOLDER,
                policy_ref="B2.1",
                # The old remedy -- `bd link <new-brief-id> ...` -- was written
                # for a WARN that fired AFTER creation, when a brief id existed
                # to link. Refusing means there is no new brief id, so that
                # advice is now unfollowable. A refusal that names the rule and
                # not the remedy is a wall, so the remedy moves to the thing the
                # caller can actually do: supply the source on the call.
                suggested_next_command=(
                    "mctl briefs create --source <source-bead-id> ... "
                    "(or pass `sources` to briefs_create)"
                ),
            ),
        )
    metadata = {"created_by": "mctl", "mctl_trace_id": ctx.trace_id, "created_at": _now()}
    if request.requested_by:
        metadata["requested_by"] = request.requested_by
    # setdefault, not update: `created_by`, `mctl_trace_id` and `created_at` are
    # mctl's own attestation that IT made this bead. A caller able to overwrite
    # them could forge provenance, so caller keys fill gaps and never clobber.
    for key, value in (request.metadata or {}).items():
        if isinstance(value, str) and value.strip():
            metadata.setdefault(str(key), value)
    bead_create = BeadCreate(
        placeholder_id=NEW_BRIEF_ID_PLACEHOLDER,
        title=title,
        body=body,
        issue_type="decision",
        labels=labels,
        metadata=metadata,
        sources=request.sources,
    )
    layout = artifact_layout(ctx)
    _require_brief_root(ctx, layout)
    pile_create = FileCreate(
        "pile_markdown",
        layout.pile / f"{NEW_BRIEF_ID_PLACEHOLDER}.md",
        _pile_document(body),
    )
    cache_update = CacheUpdate(
        "decision_toml",
        layout.decisions / f"{NEW_BRIEF_ID_PLACEHOLDER}.toml",
        NEW_BRIEF_ID_PLACEHOLDER,
        {
            "brief_id": NEW_BRIEF_ID_PLACEHOLDER,
            "status": "open",
            "title": title,
        },
    )
    planned_effects = [bead_create.to_dict(), pile_create.to_dict(), cache_update.to_dict()]
    event_row = {
        "brief_id": NEW_BRIEF_ID_PLACEHOLDER,
        "operation": "briefs.create",
        "planned_effects": planned_effects,
        "trace_id": ctx.trace_id,
    }
    trace_row = {
        "brief_id": NEW_BRIEF_ID_PLACEHOLDER,
        "city_path": str(ctx.city_root),
        "operation": "briefs.create",
        "planned_effects": planned_effects,
        "rig_name": ctx.rig_id,
        "trace_id": ctx.trace_id,
    }
    today = date.today().isoformat()
    return EffectPlan(
        trace_id=ctx.trace_id,
        operation="briefs.create",
        target_brief_id=NEW_BRIEF_ID_PLACEHOLDER,
        preconditions=preconditions,
        bead_updates=(),
        cache_updates=(cache_update,),
        event_writes=(
            JsonlWrite(
                "event_write",
                ctx.rig_root / ".beads" / "mctl" / "events" / f"{today}.jsonl",
                event_row,
            ),
        ),
        trace_writes=(
            JsonlWrite(
                "trace_write",
                ctx.rig_root / ".beads" / "mctl" / "traces" / f"{today}.jsonl",
                trace_row,
            ),
        ),
        bead_creates=(bead_create,),
        file_creates=(pile_create,),
        advisories=tuple(advisories),
    )


def _require_brief_root(ctx: MctlContext, layout: ArtifactLayout) -> None:
    """Refuse to create a brief under a root the resolver could not find.

    `assets/brief-pipeline/paths.toml` declares rig-relative artifact paths,
    but the live city keeps its brief tree at the city root, and the shuffler
    never reads paths.toml at all — it is handed `--brief-root` explicitly. So
    the declared contract and the live layout currently disagree, and which
    root is correct is an open policy question, not something creation may
    decide.

    Reading through a missing root is harmless: it reports `missing`. Writing
    through one is not — `mkdir -p` would silently build a parallel shadow
    brief tree that diverges from the real one, with nothing downstream to
    notice. So creation aborts and names the path it resolved.
    """
    if layout.root.is_dir():
        return

    # #147: materialise the cache for a root that already resolves.
    #
    # The refusal below guards a MIS-RESOLVED root -- writing through one would
    # build a brief tree where nothing reads. That hazard needs the resolution
    # itself to be wrong. It is not wrong merely because the directory is absent:
    # `paths.toml` is rig-relative, `hq.rig_root` IS the city root (so the "city
    # keeps its tree at the city root" reading describes hq's own rig-relative
    # tree, not a competing convention), and B2.8 makes the bead store canonical
    # with this tree as redundant CACHE -- `hecke` serves 45 open briefs holding
    # `stack=0` on disk.
    #
    # So the distinguishing question is whether the rig's `.beads` directory
    # exists. If it does, the rig is real, the root resolved, and only the cache
    # is missing -- a directory mctl is entitled to make. If it does not, the
    # resolution landed somewhere unreal and the refusal stands.
    #
    # Measured before this change: 6 of 16 registered rigs could never receive a
    # FIRST brief, `agent_skills` among them while already holding 3 decision
    # beads. For `mathcity` it made CT4.5 unsatisfiable -- the rig owning `mctl`
    # had nowhere to land its own repair work.
    # NO mkdir HERE. This function runs while the plan is being BUILT, before
    # anything knows whether the caller asked for a dry run, so creating
    # directories here mutates the filesystem on `dry_run: true`. stripes measured
    # exactly that on the live city: a dry run against `mathcity` wrote zero files
    # and brought three directories into existence at the instant of the probe.
    # A dry run that mutates is not a dry run, and worse, the probe manufactured
    # its own precondition -- any survey of "which rigs can accept a brief" run
    # through this tool was contaminated by the act of asking.
    #
    # The directories do not need making here anyway: `_atomic_write` already does
    # `path.parent.mkdir(parents=True, exist_ok=True)`, so applying the plan
    # creates `.pile/` and `decisions/` as their files land. `stack/` is NOT
    # created, and should not be -- nothing writes it at creation time; it is the
    # shuffler's, per B2.10. Asserting it here was my over-reach.
    #
    # So the permission is all that belongs at plan time: refuse when the
    # resolution is unreal, permit when only the cache is absent, and let apply
    # do the making.
    parent = layout.root.parent
    if parent.is_dir() and not layout.root.exists():
        return

    raise MutationError(
        _diagnostic(
            ctx,
            Severity.FATAL,
            "MBRF035",
            (
                f"Resolved brief root {layout.root} does not exist; refusing to "
                "create a brief tree there."
            ),
            brief_id=NEW_BRIEF_ID_PLACEHOLDER,
            data_location=str(layout.root),
            policy_ref="B2.8",
            suggested_next_command=(
                "Check paths.brief_root in assets/brief-pipeline/paths.toml "
                "against the rig's actual brief tree."
            ),
        )
    )


@dataclass(frozen=True)
class IssueBeadCreateInput:
    repo: str
    issue_number: int


#: The plan cannot name the bead it is about to create, because bd mints the
#: id -- same reasoning as `NEW_BRIEF_ID_PLACEHOLDER`, a distinct token
#: because this placeholder never denotes a brief.
NEW_ISSUE_BEAD_ID_PLACEHOLDER = "(pending-issue-bead-id)"


def plan_create_issue_bead(ctx: MctlContext, request: IssueBeadCreateInput) -> EffectPlan:
    """Plan minting an OPEN bead that mirrors one GitHub issue (#170).

    `MWRK011` requires a brief's source dependency to be a real bead; nothing
    in mctl currently mints one from a tracker issue, so an issue-derived
    brief has no legal source to point at. This is the read-then-plan half of
    the fix -- fetch the issue, decide whether a bead should be minted, and
    describe that write without performing it.

    Every branch here is a read (the GitHub fetch, the existing-mirror scan
    over already-materialised beads) or pure computation. No `bd create`, no
    `mkdir`, nothing else that could make a dry run mutate -- #188 measured
    exactly that failure in `plan_create_brief`'s own `_require_brief_root`,
    and the fix there does not reach this function, so the discipline has to
    be held here independently rather than inherited.

    The target rig is DETERMINED by the issue's tracker, not chosen by the
    caller (Taylor, on #190/#170's shared seam) -- checked before the `gh`
    fetch, not after, so a caller pointed at the wrong rig fails cheaply
    rather than after a network round trip. A bead minted into the wrong
    store is exactly what #190's own `MCMS_CROSS_STORE_SOURCE` refuses
    downstream; this check puts the refusal where the information already
    is, on this side, rather than relying solely on that downstream catch.
    """
    issue_url = f"https://github.com/{request.repo}/issues/{request.issue_number}"
    expected_rig = rig_for_issue(issue_url)
    if expected_rig is not None and expected_rig != ctx.rig_id:
        raise MutationError(
            Diagnostic(
                Severity.FATAL,
                "MISS005",
                (
                    f"{request.repo}#{request.issue_number} belongs to rig "
                    f"{expected_rig!r}, not the requested rig {ctx.rig_id!r}."
                ),
                hint="The rig is determined by the tracker that holds the issue, not chosen by the caller.",
                facts={
                    "city_path": str(ctx.city_root),
                    "rig_name": ctx.rig_id,
                    "expected_rig": expected_rig,
                },
                trace_id=ctx.trace_id,
            )
        )

    try:
        issue = fetch_issue(request.repo, request.issue_number)
    except GithubIssueError as error:
        raise MutationError(
            Diagnostic(
                Severity.FATAL,
                "MISS004",
                f"Could not read {request.repo}#{request.issue_number}: {error}",
                facts={"city_path": str(ctx.city_root), "rig_name": ctx.rig_id},
                trace_id=ctx.trace_id,
            )
        ) from error

    reference = issue.reference

    if not issue.is_open:
        raise MutationError(
            Diagnostic(
                Severity.FATAL,
                "MISS001",
                f"{reference} is already {issue.state.lower()}; refusing to mint a bead for it.",
                hint="A closed issue has nothing left to dispatch work against.",
                facts={
                    "city_path": str(ctx.city_root),
                    "rig_name": ctx.rig_id,
                    "issue_state": issue.state,
                },
                trace_id=ctx.trace_id,
            )
        )

    if not issue.body.strip():
        raise MutationError(
            Diagnostic(
                Severity.FATAL,
                "MISS002",
                f"{reference} has an empty body; nothing to mirror into a bead.",
                facts={"city_path": str(ctx.city_root), "rig_name": ctx.rig_id},
                trace_id=ctx.trace_id,
            )
        )

    existing = _find_issue_mirror(ctx, reference)
    if existing is not None:
        # Idempotent by construction: report the existing bead rather than
        # minting a second mirror for the same issue.
        return EffectPlan(
            trace_id=ctx.trace_id,
            operation="create_issue_bead",
            target_brief_id=existing,
            preconditions=(),
            bead_updates=(),
            cache_updates=(),
            event_writes=(),
            trace_writes=(),
            advisories=(
                Diagnostic(
                    Severity.INFO,
                    "MISS003",
                    f"{reference} already has a mirror bead: {existing}.",
                    facts={
                        "city_path": str(ctx.city_root),
                        "rig_name": ctx.rig_id,
                        "bead_id": existing,
                    },
                    trace_id=ctx.trace_id,
                ),
            ),
        )

    metadata = {
        "created_by": "mctl",
        "mctl_trace_id": ctx.trace_id,
        "created_at": _now(),
        "gh.issue": reference,
        "gh.repo": issue.repo,
    }
    # Absent means the issue had none; an empty string is a value that looks
    # like a measurement and is not one. Matches #190's commission.py exactly
    # (stripes' own convention, adopted here rather than diverged from) --
    # `--has-metadata-key gh.labels` must not return a false positive for
    # every unlabelled issue. #170/#190 seam review, 2026-08-23.
    if issue.labels:
        metadata["gh.labels"] = ",".join(issue.labels)
    bead_create = BeadCreate(
        placeholder_id=NEW_ISSUE_BEAD_ID_PLACEHOLDER,
        title=issue.title,
        body=issue.body,
        issue_type="task",
        labels=(),
        metadata=metadata,
        sources=(),
        priority=priority_from_labels(issue.labels),
    )
    return EffectPlan(
        trace_id=ctx.trace_id,
        operation="create_issue_bead",
        target_brief_id=NEW_ISSUE_BEAD_ID_PLACEHOLDER,
        preconditions=(),
        bead_updates=(),
        cache_updates=(),
        event_writes=(),
        trace_writes=(),
        bead_creates=(bead_create,),
    )


def _find_issue_mirror(ctx: MctlContext, reference: str) -> str | None:
    """The existing task bead mirroring this issue, if creation already ran once."""
    for bead in read_beads(ctx.rig_root, fixture_path=ctx.beads_fixture, issue_type="task"):
        metadata = bead.raw.get("metadata")
        if isinstance(metadata, dict) and metadata.get("gh.issue") == reference:
            return bead.id
    return None


@dataclass(frozen=True)
class GithubIssueCreateInput:
    repo: str
    title: str
    body: str
    labels: tuple[str, ...] = ()


#: A markdown heading line, capturing the heading text. GitHub issue FORMS render
#: each required field's `label` as exactly this shape in the created body.
_HEADING = re.compile(r"^\s*#{1,6}\s+(?P<text>.+?)\s*$", re.MULTILINE)


def _body_headings(body: str) -> set[str]:
    return {match.group("text").strip().lower() for match in _HEADING.finditer(body)}


def plan_create_github_issue(
    ctx: MctlContext, request: GithubIssueCreateInput
) -> EffectPlan:
    """Plan filing a GitHub issue against `request.repo` (#185, loop step 1).

    The whole cost of this tool is that a Mayor who finds a defect can open the
    issue with no human carrying it. It is dry-run-first like every mctl
    mutation: the plan carries the fully rendered issue and the apply step is the
    only thing that shells `gh`.

    The target repo's LIVE issue template is the enforcement point (the
    `create-issue` skill's rule). A body missing a section the template marks
    REQUIRED is refused BEFORE the plan is built, so no subprocess can run for a
    body the template would reject. A template that cannot be READ is a different
    matter -- it is surfaced as an advisory and does not block, because refusing
    to file for want of a readable template turns a hygiene aid into a wall.
    """
    advisories: list[Diagnostic] = []
    try:
        templates = required_template_sections(request.repo)
    except GithubIssueError as error:
        templates = {}
        advisories.append(
            _diagnostic(
                ctx,
                Severity.WARN,
                "MGHW_TEMPLATE_UNREADABLE",
                (
                    f"Could not read {request.repo}'s issue template, so no "
                    "required-section check ran."
                ),
                brief_id="(github-issue)",
                detail=str(error),
            )
        )
    headings = _body_headings(request.body)
    # #211: a body is conformant if it satisfies ANY ONE of the repo's issue
    # forms -- NOT the union of every form's required sections. The old union
    # refused a valid bug_report body for lacking feature_request/docs_report
    # headings. Refuse only when NO template is satisfied, naming the CLOSEST.
    if templates:
        per_template_missing = {
            name: [
                section
                for section in reqs
                if section.strip().lower() not in headings
            ]
            for name, reqs in templates.items()
        }
        if all(missing for missing in per_template_missing.values()):
            closest, missing = min(
                per_template_missing.items(), key=lambda item: len(item[1])
            )
            raise MutationError(
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MGHW_TEMPLATE_SECTION_MISSING",
                    (
                        f"The issue body satisfies no {request.repo} issue "
                        f"template. Closest is `{closest}`, still missing "
                        f"section(s): {', '.join(missing)}."
                    ),
                    brief_id="(github-issue)",
                    data_location=f".github/ISSUE_TEMPLATE (of {request.repo})",
                    suggested_next_command=(
                        "Add the missing `### <section>` headings for one form "
                        "(you need to satisfy only ONE), or read the repo's "
                        "issue templates."
                    ),
                )
            )
    write = GithubWrite(
        kind="create",
        repo=request.repo,
        title=request.title,
        body=request.body,
        labels=request.labels,
    )
    return EffectPlan(
        trace_id=ctx.trace_id,
        operation="create_github_issue",
        target_brief_id="(github-issue)",
        preconditions=(),
        bead_updates=(),
        cache_updates=(),
        event_writes=(),
        trace_writes=(),
        github_writes=(write,),
        advisories=tuple(advisories),
    )


def plan_commission_brief(
    ctx: MctlContext,
    *,
    bead_id: str,
    title: str,
    body: str,
    issue_url: str | None = None,
    issue_labels: Sequence[str] = (),
    bead_rig: str | None = None,
) -> EffectPlan:
    """A source bead becomes a commission brief in the pile (#190).

    Validation runs FIRST and raises `CommissionRefused` before anything is
    planned -- constraints 1 and 2 are cheap here and expensive afterwards. The
    MCP handler converts that refusal into a FATAL diagnostic; a library caller
    gets the exception, which is the right shape for each.

    Everything else delegates to `plan_create_brief`, so there is one brief
    creation path and this adds commission semantics on top rather than a
    parallel implementation.
    """
    validate_commission(
        sources=(bead_id,), bead_rig=bead_rig, brief_rig=ctx.rig_id
    )
    metadata = (
        tracker_metadata(issue_url=issue_url, labels=issue_labels) if issue_url else {}
    )
    return plan_create_brief(
        ctx,
        BriefCreateInput(
            title=title,
            body=body,
            labels=brief_labels(),
            requested_by=metadata.get("gh.issue"),
            sources=(bead_id,),
            metadata=metadata,
        ),
    )


def plan_adjudication(
    ctx: MctlContext,
    brief_id: str,
    *,
    verdict: str | None,
    reason: str | None,
    option: str | None = None,
    adjudicated_by: str | None = None,
    no_brainer: bool = False,
    no_brainer_reason: str | None = None,
) -> EffectPlan:
    """Record a verdict on a brief bead.

    `adjudicated_by` is the RECORDING half of #152. Three MCP calls compose
    into self-authorisation -- `briefs_create`, `briefs_relay_adjudication(approve)`,
    `work_dispatch` -- because step 2 supplies the approving verdict step 3
    demands. The rule that a reviewer must not be the author is enforced
    socially on branches and by nothing at all here.

    This does NOT refuse self-adjudication; that is a policy decision with its
    own blast radius. It makes self-adjudication VISIBLE, which is #152's own
    stated minimum: silent self-approval is the unacceptable case.

    `requested_by` is written at create and `adjudicated_by` is written here,
    onto the SAME bead -- so an auditor derives "did the author approve their
    own brief?" at read time. It is deliberately not computed at write time:
    that needs the bead's own metadata, `_beads()` is not cached, and every
    adjudication would pay a second `bd` subprocess (9-11s on the largest rig)
    to answer a question nobody is asking at that moment.

    Omitting it is allowed and LOUD: an adjudication with no recorded
    adjudicator is unattributable, so it emits MBRF_ADJUDICATOR_UNRECORDED at
    WARN. WARN and not ERROR because an ERROR would become a precondition and
    block the write, which is the gate half.
    """
    normalized = _normalize_verdict(ctx, verdict, brief_id)
    # mc-qlmh: the reason is OPTIONAL on the adjudicate path. The tool schema
    # types it `["string", "null"]`, the dashboard panel labels it optional and
    # always posts `reason=""` when the operator leaves it blank, and Taylor's
    # live instruction was "I shouldn't have to give a reason." Forcing it here
    # made the form invite a call the core then refused (409 on a bare verdict).
    # Deferral keeps `_require_reason` (a parked brief without a reason is a
    # different contract); only the verdict path is relaxed.
    reason = (reason or "").strip()
    observed = show_brief(ctx, brief_id)
    observed_diagnostics = tuple(doctor_briefs(ctx, brief_id).diagnostics)
    diagnostics = list(_blocking_preconditions(observed_diagnostics))
    # A return verdict ratifies nothing, so nothing about the brief's own
    # state can make it wrong. Keep the findings, drop the veto.
    #
    # The advisories are drawn from ALL observed diagnostics, not from the
    # blocking subset. Drawing them from `diagnostics` assumed findings and
    # blockers were the same set -- true only while every finding worth
    # reporting happened to be ERROR. #137 downgraded MBRF004 to WARN and the
    # finding vanished from the payload entirely: demoted to advisory became
    # suppressed outright, which is the "don't block -- record" rule failing in
    # the recording half. INFO is excluded because it is not a finding.
    returned_advisories: list[Diagnostic] = []
    if normalized in RETURN_VERDICTS:
        returned_advisories = [
            diagnostic
            for diagnostic in observed_diagnostics
            if diagnostic.severity is not Severity.INFO
        ]
        diagnostics = []
    # Plan §4 MOPT001/MOPT002: a verdict on a multi-option brief has to say
    # which option it is approving, or it records a decision against nothing.
    # `show_brief` already carries the canonical body, so options resolve
    # from it rather than costing a second `bd list` subprocess.
    offered = decision_options(ctx, brief_id, observed.body)
    # #215: only an APPROVING verdict selects an option. A revise/reject verdict
    # (RETURN_VERDICTS) ratifies nothing and consumes no option, so gating it on
    # "name an option" would forge a selection the adjudicator never made -- and it
    # blocked recording the return verdict at all. Scope the option gate to approve.
    if offered and normalized == "approve":
        labels = {item.label.upper() for item in offered}
        if option is None and len(offered) > 1:
            diagnostics.append(
                _diagnostic(
                    ctx,
                    Severity.ERROR,
                    "MOPT001",
                    "This brief offers multiple options; adjudication must name one.",
                    brief_id=brief_id,
                    detail="options=" + ", ".join(sorted(labels)),
                )
            )
        elif option is not None and option.upper() not in labels:
            diagnostics.append(
                _diagnostic(
                    ctx,
                    Severity.ERROR,
                    "MOPT002",
                    f"Option {option!r} is not offered by this brief.",
                    brief_id=brief_id,
                    detail="options=" + ", ".join(sorted(labels)),
                )
            )
    diagnostics = tuple(diagnostics)
    now = _now()
    metadata = {
        "adjudicated_at": now,
        "mctl_trace_id": ctx.trace_id,
        "verdict": normalized,
        "verdict_reason": reason,
    }
    if option:
        metadata["verdict_option"] = option
    # Pairs with `requested_by`, written at create. Both on one bead is what
    # makes self-approval auditable -- see this function's docstring.
    if adjudicated_by and adjudicated_by.strip():
        metadata["adjudicated_by"] = adjudicated_by.strip()
    else:
        # Loud, not blocking -- so it is an ADVISORY, not a precondition.
        # `diagnostics` is already frozen to a tuple by here and feeds
        # `preconditions`, which BLOCKS the mutation; appending there would
        # have made the recording half refuse writes, i.e. silently become the
        # gate half. An unattributable adjudication is the case #152 calls
        # unacceptable when it happens SILENTLY -- the fix is noise, not a
        # refusal.
        returned_advisories = [
            *returned_advisories,
            _diagnostic(
                ctx,
                Severity.WARN,
                "MBRF_ADJUDICATOR_UNRECORDED",
                "This verdict records no adjudicator, so it cannot be attributed "
                "and self-approval cannot be detected. Pass adjudicated_by.",
                brief_id=brief_id,
            ),
        ]
    # #208 Part 2 / #76 Field 7: the no-brainer classifier signal, as typed bead
    # metadata rather than a marker folded into `verdict_reason`. Written only
    # when set -- absent means absent, so an ordinary verdict is not stamped
    # `no_brainer: false`. The value is a string because bead metadata is
    # string-valued (like `adjudicated_by`), and it is orthogonal to the verdict:
    # a no-brainer is a comment on WHY this reached a human, not a disposition.
    if no_brainer:
        metadata["no_brainer"] = "true"
        if no_brainer_reason and no_brainer_reason.strip():
            metadata["no_brainer_reason"] = no_brainer_reason.strip()
    cache_fields = {
        "adjudicated_at": now,
        "status": "adjudicated",
        "verdict": normalized,
        "verdict_reason": reason,
    }
    # #77 gave the brief file's own frontmatter a writer, but only for `status`
    # and `verdict`. mc-9kwwv: the attribution and its date were written to bead
    # metadata ONLY, while every reader of them -- `materialize_plan.classify_tier`
    # (which needs verdict AND authorizer AND date together to reach
    # TIER_ADJUDICATED), `materialize_plan.build_row`, and
    # `mctl_dashboard/fields.py` -- reads the FRONTMATTER. So an mctl-adjudicated
    # brief could never reach TIER_ADJUDICATED and no surface ever showed who
    # decided. Both keys are single-line-safe (a name; an ISO instant whose
    # colons sit after the first `key:` and so parse cleanly), unlike
    # `verdict_reason`, which stays out of the line-format frontmatter and lives
    # in `decisions/<id>.toml`. `adjudicated_by` is written only when supplied --
    # absent authority stays absent, so classify_tier keeps an unattributed
    # verdict below TIER_ADJUDICATED rather than forging a value (#152).
    frontmatter_fields = {
        "status": "adjudicated",
        "verdict": normalized,
        "adjudicated_at": now,
    }
    if adjudicated_by and adjudicated_by.strip():
        frontmatter_fields["adjudicated_by"] = adjudicated_by.strip()
    return _plan(
        ctx,
        operation="briefs.adjudicate",
        brief_id=brief_id,
        preconditions=diagnostics,
        extra_advisories=tuple(returned_advisories),
        bead_update=BeadUpdate(
            brief_id,
            status="closed",
            metadata=metadata,
            if_status=observed.status,
        ),
        cache_fields=cache_fields,
        # #77: the brief file's own `status:` was owned by nobody, so 35 of 88
        # index rows pointed at a document still reading `present-it-pending`
        # after its brief had been decided. The frontmatter is a line format, so
        # `verdict_reason` (which may carry a newline or a colon) still stays out
        # and lives in `decisions/<id>.toml`; `status`, `verdict`, `adjudicated_at`
        # and (when supplied) `adjudicated_by` are all single-line-safe and go in
        # here, because that is the surface classify_tier reads (mc-9kwwv, above).
        frontmatter_fields=frontmatter_fields,
        # The legacy lane's decision record. `decisions/<id>.toml` holds the
        # decision for a stack-track brief; a decisions-track brief's decision
        # has always lived in its manifest row, and until now the only writer
        # was a `sed`/heredoc pair inside adjudicate-brief -- so adjudicating
        # from the dashboard, the CLI or the MCP left the row saying
        # `ready-for-adjudication` while the bead said closed. Measured
        # 2026-08-04: 17 briefs read `adjudicated` in the manifest while their
        # files read otherwise.
        #
        # Four keys here where the frontmatter takes two, because a JSON row
        # can hold what a `key: value` line cannot: `verdict_note` carries the
        # operator's reason verbatim, newlines and colons included.
        manifest_row_fields={
            "status": "adjudicated",
            "verdict": normalized,
            "verdict_note": reason,
            # A date, not a timestamp: 99 of the 101 timestamped live rows are
            # `YYYY-MM-DD`, and this writer joins a corpus rather than starting
            # one. The full-precision instant is on the bead and in the
            # decision TOML.
            "adjudicated_at": date.today().isoformat(),
        },
        manifest_drop_fields=("defer_until",),
    )


def plan_deferral(
    ctx: MctlContext,
    brief_id: str,
    *,
    reason: str | None,
    until: str | None,
    days: int | None = None,
) -> EffectPlan:
    reason = _require_reason(ctx, reason, brief_id)
    defer_until = _resolve_until(ctx, until, days, brief_id)
    observed = show_brief(ctx, brief_id)
    diagnostics = _blocking_preconditions(doctor_briefs(ctx, brief_id).diagnostics)
    metadata = {
        "defer_reason": reason,
        "deferred_at": _now(),
        "mctl_trace_id": ctx.trace_id,
    }
    cache_fields = {
        "defer_reason": reason,
        "defer_until": defer_until,
        "status": "deferred",
    }
    return _plan(
        ctx,
        operation="briefs.defer",
        brief_id=brief_id,
        preconditions=diagnostics,
        bead_update=BeadUpdate(
            brief_id,
            status="deferred",
            metadata=metadata,
            defer_until=defer_until,
            if_status=observed.status,
        ),
        cache_fields=cache_fields,
        # Deferral is the non-terminal verdict, so the legacy row stays `ready`
        # and gains the un-defer date. Both halves are load-bearing for #18:
        # present-briefs' legacy selector filters on `status` and skips a ready
        # brief whose `defer_until` is in the future, so writing the status
        # without the date resurfaces the brief on the next run.
        manifest_row_fields={"status": "ready", "defer_until": defer_until},
    )


def dry_run_payload(plan: EffectPlan) -> dict[str, object]:
    _raise_if_blocked(plan)
    return {
        "applied": False,
        "diagnostics": [diagnostic.to_dict() for diagnostic in plan.advisories],
        "effect_plan": plan.to_dict(),
        "trace_id": plan.trace_id,
    }


def apply_effect_plan(ctx: MctlContext, plan: EffectPlan) -> ApplyResult:
    _raise_if_blocked(plan)
    actual: list[Mapping[str, object]] = []
    diagnostics: list[Diagnostic] = []
    # Plan §4: the trace records the intent before anything is mutated, then
    # exactly one outcome row -- so a crash mid-mutation still leaves evidence.
    trace_file = trace_path(ctx.rig_root)
    for write in plan.trace_writes:
        append_planned(write.path, write.row)
        trace_file = write.path
    return _apply_effects(ctx, plan, actual, diagnostics, trace_file)


def _apply_effects(
    ctx: MctlContext,
    plan: EffectPlan,
    actual: list[Mapping[str, object]],
    diagnostics: list[Diagnostic],
    trace_file: Path,
) -> ApplyResult:
    minted: dict[str, str] = {}
    for create in plan.bead_creates:
        try:
            result = apply_bead_create(
                ctx.rig_root,
                create,
                fixture_path=ctx.beads_fixture,
            )
        except BeadWriteError as error:
            append_aborted(
                trace_file,
                plan.trace_id,
                [{"code": "MCTL_CANONICAL_BEAD_CREATE_FAILED", "detail": str(error)}],
            )
            raise MutationError(
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MCTL_CANONICAL_BEAD_CREATE_FAILED",
                    "Canonical decision bead creation failed; nothing was written.",
                    brief_id=create.placeholder_id,
                    detail=str(error),
                )
            ) from error
        minted[create.placeholder_id] = str(result["id"])
        actual.append({"kind": "bead_create", "target": result["id"], "result": result})
    for update in plan.bead_updates:
        try:
            result = apply_bead_update(
                ctx.rig_root,
                update,
                fixture_path=ctx.beads_fixture,
            )
        except BeadRaceLostError as error:
            append_aborted(trace_file, plan.trace_id, [{"code": "MCTL_BEAD_UPDATE_RACE_LOST", "detail": str(error)}])
            raise MutationError(
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MCTL_BEAD_UPDATE_RACE_LOST",
                    f"Another actor changed {update.id!r} before this mutation applied.",
                    brief_id=update.id,
                    detail=str(error),
                )
            ) from error
        except BeadWriteError as error:
            append_aborted(trace_file, plan.trace_id, [{"code": "MCTL_CANONICAL_BEAD_UPDATE_FAILED", "detail": str(error)}])
            raise MutationError(
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MCTL_CANONICAL_BEAD_UPDATE_FAILED",
                    f"Canonical bead update failed for {update.id!r}.",
                    brief_id=update.id,
                    detail=str(error),
                )
            ) from error
        actual.append({"kind": "bead_update", "target": update.id, "result": result})
    for comment in plan.bead_comments:
        try:
            result = apply_bead_comment(
                ctx.rig_root, comment.bead_id, comment.text, fixture_path=ctx.beads_fixture
            )
        except BeadWriteError as error:
            append_aborted(
                trace_file,
                plan.trace_id,
                [{"code": "MCTL_BEAD_COMMENT_FAILED", "detail": str(error)}],
            )
            raise MutationError(
                _diagnostic(
                    ctx,
                    Severity.FATAL,
                    "MCTL_BEAD_COMMENT_FAILED",
                    f"Appending a comment to {comment.bead_id!r} failed; nothing was written.",
                    brief_id=comment.bead_id,
                    detail=str(error),
                )
            ) from error
        actual.append({"kind": "bead_comment", "target": comment.bead_id, "result": result})
    for relate in plan.bead_relates:
        _apply_bead_relation(ctx, plan, relate, minted, actual, trace_file)
    for write in plan.github_writes:
        _apply_github_write(ctx, plan, write, actual, trace_file)
    if plan.bead_creates:
        _apply_created_artifacts(ctx, plan, minted, actual, diagnostics)
    else:
        for update in plan.cache_updates:
            try:
                _apply_cache_update(update)
            except StackIndexRowUnwritable as error:
                # #92. A WARN, not a failure, and the asymmetry with the
                # decisions-track case below is deliberate: THAT writer is
                # planned only when a row is expected (`row_key and
                # legacy_manifest.is_file()`), so a no-match there is a real
                # inconsistency. THIS one is planned whenever the index FILE
                # exists, so a brief with no row -- an archived brief is
                # de-indexed by construction under B2.15 -- plans a write that
                # legitimately matches nothing. Measured: 57 index rows against
                # 79 archived briefs.
                #
                # What #92 actually asks for is that the miss be REPORTED. It
                # used to write nothing and say nothing, which is
                # indistinguishable from a write that happened.
                diagnostics.append(
                    _diagnostic(
                        ctx,
                        Severity.WARN,
                        "MCTL_STACK_INDEX_ROW_ABSENT",
                        (
                            "No stack index row was updated for this brief; the "
                            "index holds no row targeting it."
                        ),
                        brief_id=plan.target_brief_id,
                        data_location=str(update.path),
                        detail=str(error),
                        policy_ref="B2.15",
                        suggested_next_command=(
                            f"mctl briefs doctor {plan.target_brief_id} --json"
                        ),
                    )
                )
                continue
            except DecisionsTrackRowUnwritable as error:
                # Per-brief, and a WARN, for the same reason the frontmatter
                # case is: the legacy row this brief's stack index pointed at
                # is not there to be synced, which is a fact about that one
                # brief's migration record rather than a failed adjudication.
                # The bead, the decision TOML, the index row and the brief's
                # own frontmatter all landed; the operator is told which row
                # still disagrees.
                #
                # A brief with NO legacy row never reaches here -- it plans no
                # manifest update at all. That is the ordinary stack-track
                # case, and warning on it would put a WARN on the majority
                # path.
                diagnostics.append(
                    _diagnostic(
                        ctx,
                        Severity.WARN,
                        "MCTL_DECISIONS_TRACK_ROW_UNWRITABLE",
                        (
                            "The legacy decisions-track row this brief was "
                            "migrated from was not updated; the manifest does "
                            "not hold exactly one row with that number."
                        ),
                        brief_id=plan.target_brief_id,
                        data_location=str(update.path),
                        detail=str(error),
                        policy_ref="B2.10",
                        suggested_next_command=(
                            "mctl briefs doctor "
                            f"{plan.target_brief_id} --json"
                        ),
                    )
                )
                continue
            except BriefFrontmatterUnwritable as error:
                # Per-brief, and a WARN rather than an ERROR: the document is
                # shaped in a way this writer will not rewrite, which is a
                # fact about that one brief, not a failed write. Adjudication
                # is not sunk by it -- the canonical bead, the decision TOML
                # and the index row all landed, and the operator is told which
                # file still disagrees.
                diagnostics.append(
                    _diagnostic(
                        ctx,
                        Severity.WARN,
                        "MCTL_BRIEF_FRONTMATTER_UNWRITABLE",
                        (
                            "The brief's own frontmatter was not updated; this "
                            "document has no header block that can be rewritten "
                            "without reformatting it."
                        ),
                        brief_id=plan.target_brief_id,
                        data_location=str(update.path),
                        detail=str(error),
                        policy_ref="B2.8a",
                        suggested_next_command=(
                            "Add a `---` frontmatter block to the brief file, "
                            "then re-run the adjudication to record the status."
                        ),
                    )
                )
                continue
            except OSError as error:
                diagnostic = _diagnostic(
                    ctx,
                    Severity.ERROR,
                    "MCTL_REDUNDANT_CACHE_UPDATE_FAILED",
                    "Redundant brief cache update failed after canonical bead update.",
                    brief_id=plan.target_brief_id,
                    data_location=str(update.path),
                    detail=str(error),
                )
                diagnostics.append(diagnostic)
                continue
            actual.append({"kind": "cache_update", "path": str(update.path)})
    for write in plan.event_writes:
        append_jsonl(write.path, _resolve_row(write.row, minted))
        actual.append({"kind": write.kind, "path": str(write.path)})
    append_applied(trace_file, plan.trace_id, actual)
    actual.append({"kind": "trace_write", "path": str(trace_file)})
    return ApplyResult(
        plan.trace_id, plan, tuple(actual), plan.advisories + tuple(diagnostics)
    )


def _apply_bead_relation(
    ctx: MctlContext,
    plan: EffectPlan,
    relate: BeadRelate,
    minted: Mapping[str, str],
    actual: list[Mapping[str, object]],
    trace_file: Path,
) -> None:
    """Write one relate edge, then prove from the store that it is there.

    The proof is the point. `bd dep add` exits 0 on an edge whose target it
    cannot resolve and leaves a row every hydrating read hides
    (`BeadRelate` carries the measurement); `bd dep relate` refuses that id
    today but resolves ids fuzzily, so a clean exit still does not say *which*
    beads got linked. Re-reading the canonical store answers both questions
    with the one source that is allowed to answer them.

    A failure aborts loudly rather than degrading to a diagnostic. A relate
    that did not land is not a cosmetic shortfall: the downstream lost-bead
    filter reads this edge, and a caller told "applied" would stop looking.
    """
    resolved = BeadRelate(
        source_id=minted.get(relate.source_id, relate.source_id),
        target_id=minted.get(relate.target_id, relate.target_id),
        link_type=relate.link_type,
    )
    try:
        result = apply_bead_relate(ctx.rig_root, resolved, fixture_path=ctx.beads_fixture)
    except BeadWriteError as error:
        _abort_relation(
            ctx,
            plan,
            trace_file,
            "MCTL_CANONICAL_BEAD_RELATE_FAILED",
            f"Relating {resolved.source_id!r} to {resolved.target_id!r} failed.",
            resolved,
            detail=str(error),
        )
    actual.append({"kind": "bead_relate", **result})

    try:
        beads = read_beads(ctx.rig_root, fixture_path=ctx.beads_fixture)
    except BeadReadError as error:
        _abort_relation(
            ctx,
            plan,
            trace_file,
            "MCTL_BEAD_RELATION_UNVERIFIED",
            (
                f"The edge {resolved.source_id!r} -> {resolved.target_id!r} was "
                "written but could not be verified: the canonical store did not "
                "answer the read-back."
            ),
            resolved,
            detail=str(error),
        )
    verification = verify_relation(beads, resolved.source_id, resolved.target_id)
    if verification.unresolved_endpoints:
        _abort_relation(
            ctx,
            plan,
            trace_file,
            "MCTL_BEAD_RELATION_DANGLING",
            (
                "The relate edge names a bead this rig's canonical store cannot "
                "resolve, so the edge exists only as a dangling row: `bd show` "
                "reports it in dependency_count and omits it from dependencies, "
                "and `bd dep list` does not return it at all."
            ),
            resolved,
            detail=f"unresolved={','.join(verification.unresolved_endpoints)}",
            suggested_next_command="mctl context rigs --json",
        )
    if not verification.edge_recorded:
        _abort_relation(
            ctx,
            plan,
            trace_file,
            "MCTL_BEAD_RELATION_UNVERIFIED",
            (
                f"The store records no edge between {resolved.source_id!r} and "
                f"{resolved.target_id!r} after the write reported success."
            ),
            resolved,
        )
    actual.append({"kind": "bead_relate_verified", **verification.to_dict()})


def _abort_relation(
    ctx: MctlContext,
    plan: EffectPlan,
    trace_file: Path,
    code: str,
    message: str,
    relate: BeadRelate,
    *,
    detail: str | None = None,
    suggested_next_command: str | None = None,
) -> None:
    """Record the abort phase and raise. Never returns."""
    append_aborted(
        trace_file,
        plan.trace_id,
        [
            {
                "code": code,
                "source_id": relate.source_id,
                "target_id": relate.target_id,
                "detail": detail or "",
            }
        ],
    )
    raise MutationError(
        _diagnostic(
            ctx,
            Severity.FATAL,
            code,
            message,
            brief_id=plan.target_brief_id,
            bead_id=relate.source_id,
            data_location=f"{' '.join(BD_LIST_ARGS)} (rig database {ctx.rig_db})",
            detail=detail,
            suggested_next_command=suggested_next_command,
        )
    )


def _apply_github_write(
    ctx: MctlContext,
    plan: EffectPlan,
    write: GithubWrite,
    actual: list[Mapping[str, object]],
    trace_file: Path,
) -> None:
    """Perform one GitHub tracker write, aborting loudly if `gh` cannot.

    A failed create or edit aborts rather than degrading to a diagnostic: an
    intake tool that reported `applied` while the issue was never filed is the
    exact false-success the whole typed surface exists to remove. The `gh`
    error becomes a typed `MGHW_GH_UNAVAILABLE` object -- never a bare string,
    which was #203 -- built through the shared `_diagnostic` constructor.
    """
    try:
        if write.kind == "edit":
            url = edit_issue(write.repo, int(write.number), write.body)
        else:
            url = create_issue(write.repo, write.title or "", write.body, write.labels)
    except GithubIssueError as error:
        append_aborted(
            trace_file,
            plan.trace_id,
            [{"code": "MGHW_GH_UNAVAILABLE", "detail": str(error)}],
        )
        raise MutationError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MGHW_GH_UNAVAILABLE",
                f"gh could not complete the {write.kind} on {write.repo}; nothing was filed.",
                brief_id=plan.target_brief_id,
                detail=str(error),
                suggested_next_command="gh auth status",
            )
        ) from error
    actual.append(
        {"kind": "github_issue", "operation": write.kind, "repo": write.repo, "url": url}
    )


def _apply_created_artifacts(
    ctx: MctlContext,
    plan: EffectPlan,
    minted: Mapping[str, str],
    actual: list[Mapping[str, object]],
    diagnostics: list[Diagnostic],
) -> None:
    """Write a new brief's redundant artifacts, all-or-nothing.

    The canonical bead already exists and cannot be un-created, but a cache
    that is half-written is worse than one that is absent: `briefs doctor`
    would read the orphan half as a real invariant violation. So every file
    this operation brought into existence is removed if any of them fails,
    and the operator is told the redundancy still has to be rebuilt.
    """
    created: list[Path] = []
    try:
        for file_create in plan.file_creates:
            resolved = _resolve_file_create(file_create, minted)
            apply_file_create(resolved)
            created.append(resolved.path)
            actual.append({"kind": resolved.kind, "path": str(resolved.path)})
        for update in plan.cache_updates:
            resolved_update = _resolve_cache_update(update, minted)
            existed = resolved_update.path.exists()
            _apply_cache_update(resolved_update)
            if not existed:
                created.append(resolved_update.path)
            actual.append({"kind": "cache_update", "path": str(resolved_update.path)})
    except OSError as error:
        for path in created:
            path.unlink(missing_ok=True)
        actual[:] = [
            effect
            for effect in actual
            if str(effect.get("path", "")) not in {str(path) for path in created}
        ]
        diagnostics.append(
            _diagnostic(
                ctx,
                Severity.ERROR,
                "MCTL_REDUNDANT_CACHE_ROLLED_BACK",
                (
                    "Redundant brief cache writes failed and were rolled back; the "
                    "canonical decision bead was created and is intact."
                ),
                brief_id=next(iter(minted.values()), plan.target_brief_id),
                data_location=str(getattr(error, "filename", "") or ""),
                detail=str(error),
                policy_ref="B2.8",
                suggested_next_command="mctl briefs validate <brief-id> --json",
            )
        )


def _resolve_file_create(file_create: FileCreate, minted: Mapping[str, str]) -> FileCreate:
    return FileCreate(
        file_create.kind, _resolve_path(file_create.path, minted), file_create.content
    )


def _resolve_cache_update(update: CacheUpdate, minted: Mapping[str, str]) -> CacheUpdate:
    return CacheUpdate(
        update.kind,
        _resolve_path(update.path, minted),
        _resolve_text(update.target_brief_id, minted),
        {key: _resolve_text(str(value), minted) for key, value in update.fields.items()},
    )


def _resolve_path(path: Path, minted: Mapping[str, str]) -> Path:
    return Path(_resolve_text(str(path), minted))


def _resolve_row(row: Mapping[str, object], minted: Mapping[str, str]) -> Mapping[str, object]:
    if not minted:
        return row
    return json.loads(_resolve_text(json.dumps(dict(row), sort_keys=True), minted))


def _resolve_text(value: str, minted: Mapping[str, str]) -> str:
    for placeholder, bead_id in minted.items():
        value = value.replace(placeholder, bead_id)
    return value


def apply_file_create(file_create: FileCreate) -> None:
    """Write a brand-new cache file, refusing to overwrite an existing one."""
    if file_create.path.exists():
        raise FileExistsError(
            f"refusing to overwrite existing cache file {file_create.path}"
        )
    _atomic_write(file_create.path, file_create.content)


def _plan(
    ctx: MctlContext,
    *,
    operation: str,
    brief_id: str,
    preconditions: tuple[Diagnostic, ...],
    bead_update: BeadUpdate,
    cache_fields: Mapping[str, str],
    extra_advisories: tuple[Diagnostic, ...] = (),
    frontmatter_fields: Mapping[str, str] | None = None,
    manifest_row_fields: Mapping[str, str] | None = None,
    manifest_drop_fields: tuple[str, ...] = (),
) -> EffectPlan:
    cache_updates = _cache_updates(
        ctx,
        brief_id,
        cache_fields,
        frontmatter_fields=frontmatter_fields,
        manifest_row_fields=manifest_row_fields,
        manifest_drop_fields=manifest_drop_fields,
    )
    event_row = {
        "brief_id": brief_id,
        "operation": operation,
        "planned_effects": [bead_update.to_dict(), *[item.to_dict() for item in cache_updates]],
        "trace_id": ctx.trace_id,
    }
    trace_row = {
        "brief_id": brief_id,
        "city_path": str(ctx.city_root),
        "operation": operation,
        "planned_effects": event_row["planned_effects"],
        "rig_name": ctx.rig_id,
        "trace_id": ctx.trace_id,
    }
    today = date.today().isoformat()
    return EffectPlan(
        trace_id=ctx.trace_id,
        operation=operation,
        target_brief_id=brief_id,
        preconditions=preconditions,
        advisories=tuple(extra_advisories),
        bead_updates=(bead_update,),
        cache_updates=cache_updates,
        event_writes=(JsonlWrite("event_write", ctx.rig_root / ".beads" / "mctl" / "events" / f"{today}.jsonl", event_row),),
        trace_writes=(JsonlWrite("trace_write", ctx.rig_root / ".beads" / "mctl" / "traces" / f"{today}.jsonl", trace_row),),
    )


def _cache_updates(
    ctx: MctlContext,
    brief_id: str,
    fields: Mapping[str, str],
    *,
    frontmatter_fields: Mapping[str, str] | None = None,
    manifest_row_fields: Mapping[str, str] | None = None,
    manifest_drop_fields: tuple[str, ...] = (),
) -> tuple[CacheUpdate, ...]:
    updates: list[CacheUpdate] = []
    decision_toml = ctx.rig_root / ".beads" / "briefs" / "decisions" / f"{brief_id}.toml"
    if decision_toml.exists():
        updates.append(CacheUpdate("decision_toml", decision_toml, brief_id, fields))
    stack_index = ctx.rig_root / ".beads" / "briefs" / "stack" / ".index.jsonl"
    if stack_index.exists():
        updates.append(CacheUpdate("stack_index", stack_index, brief_id, fields))
    if frontmatter_fields:
        # Absent stays absent: a brief with no markdown cache plans no
        # frontmatter write, exactly as an absent decision TOML plans none.
        # The document that *exists* and has no header is the case that warns.
        for _lane, path in cached_brief_documents(ctx, brief_id):
            updates.append(
                CacheUpdate("brief_frontmatter", path, brief_id, frontmatter_fields)
            )
    if manifest_row_fields:
        # The decision record is split by track. A stack-track brief's decision
        # lives in `decisions/<id>.toml`; the legacy decisions-track lane keeps
        # its own row, and only that lane has one. So this plans a write ONLY
        # for a brief that already carries a legacy row -- absence is the
        # ordinary majority path, not a fault, and it is silent for the same
        # reason an absent decision TOML is. Minting a row for a stack-track
        # brief would invent a representation rather than sync an existing one.
        legacy_manifest = artifact_layout(ctx).legacy_manifest
        row_key = _decisions_track_row_key(ctx, brief_id)
        if row_key and legacy_manifest.is_file():
            updates.append(
                CacheUpdate(
                    "decisions_track_row",
                    legacy_manifest,
                    brief_id,
                    manifest_row_fields,
                    row_key=row_key,
                    drop_fields=manifest_drop_fields,
                )
            )
    return tuple(updates)


#: The `NNN-` ordering prefix a `legacy_source` path carries, anchored at the
#: start of the basename. `decisions-track/08-sigma18-done-vs-residual-brief.md`
#: names row 8. Anchored because an unanchored digit run would match the `18`
#: inside the slug and rewrite an unrelated row.
_LEGACY_SOURCE_N = re.compile(r"^0*(\d+)-")


def _decisions_track_row_key(ctx: MctlContext, brief_id: str) -> str:
    """The legacy manifest row this brief is the migrated form of, or "".

    The join is **read off the migration's own record**, never inferred from
    slugs. `brief-decisions-track-inventory.py` wrote `legacy_n` and
    `legacy_source` onto the stack index row when it copied a decisions-track
    brief forward, so the index already states which row a brief came from.
    Re-deriving that by matching slugs would be a second identity rule, and
    the two would drift the moment a slug was edited.

    Two lookups, because the index names a brief two ways: the row-identity
    keys `_update_stack_index` already matches on, and the `path` of a document
    `cached_brief_documents` resolves for this brief. The second is what
    catches the live shape `{"slug": "he-ckilh-dispatch-gate", "source":
    "he-ckilh", "path": ".../he-ckilh-dispatch-gate.md"}`, where the row's slug
    is the legacy slug and only the filename carries the bead id.

    Returns "" when this brief has no legacy row -- the ordinary case for a
    stack-track brief -- and also when two index rows name *different* legacy
    rows. Rewriting the wrong row of an append-shaped legacy inventory is
    worse than leaving it stale, so an ambiguous join writes nothing.
    """
    layout = artifact_layout(ctx)
    if not layout.stack_index.is_file():
        return ""
    try:
        lines = layout.stack_index.read_text(encoding="utf-8").splitlines()
    except OSError:
        return ""
    documents = {path.name for _lane, path in cached_brief_documents(ctx, brief_id)}
    keys: set[str] = set()
    for line in lines:
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        if not _row_targets_brief(row, brief_id) and not _row_names_document(row, documents):
            continue
        key = _legacy_row_key(row)
        if key:
            keys.add(key)
    return keys.pop() if len(keys) == 1 else ""


def _row_names_document(row: Mapping[str, object], documents: set[str]) -> bool:
    path = row.get("path")
    return isinstance(path, str) and Path(path).name in documents


def _legacy_row_key(row: Mapping[str, object]) -> str:
    """The manifest `n` a stack index row declares, as a string.

    `legacy_n` first because it is the key itself; `legacy_source` second
    because the migration wrote both and a hand-repaired row may carry only
    the path. `legacy_source: null` is the recorded way of saying "this brief
    has no legacy origin", so it resolves to nothing rather than to a guess.
    """
    n = row.get("legacy_n")
    if isinstance(n, bool):
        return ""
    if isinstance(n, int):
        return str(n)
    if isinstance(n, str) and n.strip().isdigit():
        return str(int(n.strip()))
    source = row.get("legacy_source")
    if isinstance(source, str) and source.strip():
        match = _LEGACY_SOURCE_N.match(Path(source.strip()).name)
        if match:
            return str(int(match.group(1)))
    return ""


def _blocking_preconditions(diagnostics: tuple[Diagnostic, ...]) -> tuple[Diagnostic, ...]:
    return tuple(
        diagnostic
        for diagnostic in diagnostics
        if diagnostic.severity in {Severity.ERROR, Severity.FATAL}
    )


def _raise_if_blocked(plan: EffectPlan) -> None:
    if not plan.preconditions:
        return
    legacy = next(
        (
            diagnostic
            for diagnostic in plan.preconditions
            if diagnostic.code == "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED"
        ),
        None,
    )
    if legacy is not None:
        raise MutationError(legacy)
    first = plan.preconditions[0]
    # The blocking diagnostic's own remedy is carried through. Without it the
    # refusal names a rule and not a way out: the operator is told
    # `blocking_code: MBRF034` and left to look it up. A refusal that cannot be
    # acted on is a wall, and walls get worked around rather than fixed.
    facts = {
        "blocking_code": first.code,
        "brief_id": plan.target_brief_id,
        "operation": plan.operation,
    }
    if first.policy_ref:
        facts["policy_ref"] = first.policy_ref
    if first.message:
        facts["blocking_reason"] = first.message
    if first.suggested_next_command:
        # Carried in `facts` rather than left on the field, because
        # `render_diagnostic` (diagnostics.py:78) prints severity, code,
        # message, hint, facts and trace_id -- and NEVER
        # `suggested_next_command`. Every diagnostic's remedy is invisible at
        # the CLI, which is a separate defect filed on its own; this line stops
        # THIS refusal being a wall while that is fixed properly.
        facts["remedy"] = first.suggested_next_command
    raise MutationError(
        Diagnostic(
            severity=Severity.FATAL,
            code="MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS",
            message="Mutation blocked because brief doctor reported ERROR or FATAL diagnostics.",
            facts=facts,
            trace_id=plan.trace_id,
            suggested_next_command=first.suggested_next_command,
        )
    )


def _normalize_verdict(ctx: MctlContext, verdict: str | None, brief_id: str) -> str:
    if not verdict:
        raise MutationError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MCTL_MUTATION_VERDICT_REQUIRED",
                "Adjudication requires --verdict.",
                brief_id=brief_id,
            )
        )
    normalized = VALID_VERDICTS.get(verdict.strip().lower())
    if normalized is None:
        raise MutationError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MCTL_MUTATION_INVALID_VERDICT",
                "Adjudication verdict must be approve, revise, or reject.",
                brief_id=brief_id,
            )
        )
    return normalized


def _require_reason(ctx: MctlContext, reason: str | None, brief_id: str) -> str:
    if reason is None or not reason.strip():
        raise MutationError(
            _diagnostic(
                ctx,
                Severity.FATAL,
                "MCTL_MUTATION_REASON_REQUIRED",
                "Brief mutations require a non-empty --reason.",
                brief_id=brief_id,
            )
        )
    return reason.strip()


def _resolve_until(ctx: MctlContext, until: str | None, days: int | None, brief_id: str) -> str:
    if until:
        return until
    if days is not None and days > 0:
        return (date.today() + timedelta(days=days)).isoformat()
    raise MutationError(
        _diagnostic(
            ctx,
            Severity.FATAL,
            "MCTL_MUTATION_DEFER_UNTIL_REQUIRED",
            "Deferral requires --until YYYY-MM-DD or --days N.",
            brief_id=brief_id,
        )
    )


def _apply_cache_update(update: CacheUpdate) -> None:
    if update.kind == "decision_toml":
        _update_simple_toml(update.path, update.fields)
        return
    if update.kind == "stack_index":
        _update_stack_index(update.path, update.target_brief_id, update.fields)
        return
    if update.kind == "brief_frontmatter":
        _update_brief_frontmatter(update.path, update.fields)
        return
    if update.kind == "decisions_track_row":
        _update_decisions_track_row(
            update.path, update.row_key, update.fields, update.drop_fields
        )
        return
    raise OSError(f"unknown cache update kind: {update.kind}")


def _update_decisions_track_row(
    path: Path,
    row_key: str,
    fields: Mapping[str, str],
    drop_fields: tuple[str, ...] = (),
) -> None:
    """Rewrite one legacy manifest row; leave every other line byte-identical.

    The same discipline as `_update_stack_index`, held harder. The skill this
    replaces re-serialised **every** row and dropped blank lines, so one
    adjudication rewrote all 204 lines of an append-shaped inventory that other
    tools read -- and a line those tools could parse but `json` could not would
    have been silently deleted. Here the file is split on newlines, exactly one
    element of that list is replaced, and the list is rejoined: every other
    line survives byte for byte, including malformed ones, blank ones, and the
    trailing newline.

    A malformed line is never a *match*, only a survivor. Matching on a line we
    could not parse would mean guessing which row it is.

    The rewritten row keeps the file's own convention -- insertion order, and
    `json.dumps` defaults, which is how the corpus came to hold `\\u2014`
    escapes. Sorting keys or widening to UTF-8 here would make the file's
    convention "whoever wrote last wins".

    Idempotent. A row that already carries these values is not rewritten and
    the file is not touched.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    matches: list[int] = []
    parsed: dict[int, dict[str, object]] = {}
    for index, line in enumerate(lines):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and _manifest_row_key(row) == row_key:
            matches.append(index)
            parsed[index] = row
    if not matches:
        raise DecisionsTrackRowUnwritable(
            f"{path}: no decisions-track row n={row_key}"
        )
    if len(matches) > 1:
        # Two rows claiming one `n` is a corrupt inventory, not a choice to
        # make quietly: picking one would record the verdict against a brief
        # nobody named.
        raise DecisionsTrackRowUnwritable(
            f"{path}: {len(matches)} rows claim n={row_key}"
        )
    index = matches[0]
    original = parsed[index]
    updated = dict(original)
    updated.update(fields)
    for key in drop_fields:
        updated.pop(key, None)
    if updated == original:
        return
    lines[index] = json.dumps(updated)
    _atomic_write(path, "\n".join(lines))


def _manifest_row_key(row: Mapping[str, object]) -> str:
    """A manifest row's `n`, normalised to the string form the plan carries.

    `bool` is excluded before `int`: `True` is an `int` in Python, and a row
    carrying `"n": true` would otherwise answer to key `1`.
    """
    n = row.get("n")
    if isinstance(n, bool):
        return ""
    if isinstance(n, int):
        return str(n)
    if isinstance(n, str) and n.strip().isdigit():
        return str(int(n.strip()))
    return ""


def _update_brief_frontmatter(path: Path, fields: Mapping[str, str]) -> None:
    """Set `fields` in a brief's frontmatter, leaving every other line alone.

    The same discipline as `_update_stack_index`: only the lines this write
    actually changes are re-emitted, and everything else -- key order,
    spelling, spacing, values a YAML loader would reject outright -- survives
    byte for byte. There is no second serializer here, because a brief that
    round-tripped through one would lose the ~100 producer keys the corpus
    carries and the unquoted `needs-revision(check-zero:partial;option-A)`
    values that only a line matcher can hold.

    The block is delimited exactly as `materialize_plan.parse_stack_file`
    delimits it -- a `---` first line and the next line that opens `---` --
    so the reader and the writer cannot disagree about what the header is.
    Anything else raises `BriefFrontmatterUnwritable`: a header we cannot
    reproduce is a header we must not rewrite.

    Idempotent. A second call with the same fields rewrites nothing and does
    not touch the file.
    """
    text = path.read_text(encoding="utf-8")
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        raise BriefFrontmatterUnwritable(f"{path}: no frontmatter block to write into")
    closing = next(
        (index for index in range(1, len(lines)) if lines[index].startswith("---")),
        None,
    )
    if closing is None:
        raise BriefFrontmatterUnwritable(f"{path}: frontmatter block is never closed")
    header = list(lines[1:closing])
    for key, value in fields.items():
        line = f"{key}: {value}"
        # Anchored on the whole key: `FRONTMATTER_LINE` is what the reader
        # matches, so `status` never matches `status_note` or a body line that
        # merely mentions the word.
        matched = [
            index
            for index, existing in enumerate(header)
            if (match := FRONTMATTER_LINE.match(existing)) and match.group(1) == key
        ]
        if matched:
            # Every occurrence, not the first: the reader takes the last one,
            # so a stale duplicate left behind would be the value it reports.
            for index in matched:
                header[index] = line
        else:
            header.append(line)
    if header == lines[1:closing]:
        return
    _atomic_write(path, "\n".join([lines[0], *header, *lines[closing:]]))


def _atomic_write(path: Path, text: str) -> None:
    """Write via a same-directory temp file and os.replace.

    A whole-file rewrite that is interrupted between truncate and write
    destroys the cache it was updating. os.replace is atomic within a
    filesystem, so readers see either the old file or the new one.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.", suffix=".tmp")
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise


# brief-shuffle-fast-drain.py::append_index locks `<stack>/.manifest.lock`.
# flock only serializes writers that take the SAME lock file, so mctl must use
# that exact path -- a lock of our own would serialize mctl against mctl and
# leave the shuffler race wide open while looking like it was handled.
STACK_INDEX_LOCK_NAME = ".manifest.lock"


def _stack_index_lock_path(path: Path) -> Path:
    return path.parent / STACK_INDEX_LOCK_NAME


@contextmanager
def _stack_index_lock(path: Path):
    """Serialize stack-index writers.

    formulas/brief-prep.toml and the fast-drain plan both name the shuffler as
    the single writer that promotes stack entries and appends .index.jsonl.
    mctl now writes it too, so the boundary needs an explicit lock rather than
    two documents that quietly contradict the code.
    """
    lock_path = _stack_index_lock_path(path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        handle.close()


def _toml_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return f'"{_toml_escape(str(value))}"'


def _update_simple_toml(path: Path, fields: Mapping[str, object]) -> None:
    """Rewrite a decision TOML through a real parser.

    The previous writer split each line on the first `=`, so any line inside a
    multi-line string that looked like `key = ...` was rewritten instead of the
    real key -- silently losing the verdict and mutating unrelated prose.
    """
    existing: dict[str, object] = {}
    if path.exists():
        existing = dict(tomllib.loads(path.read_text(encoding="utf-8")))
    existing.update(fields)
    lines = [f"{key} = {_toml_value(value)}" for key, value in existing.items()]
    _atomic_write(path, "\n".join(lines) + "\n")


def _update_stack_index(path: Path, target_brief_id: str, fields: Mapping[str, str]) -> None:
    """Splice the matching row; leave every other line byte-identical.

    The stack index has two producers with different json.dumps settings, so
    re-serializing untouched rows makes the file's convention "whoever wrote
    last wins" -- one adjudication would rewrite every unrelated line. Only the
    row we actually change is re-emitted, in the file's compact convention and
    without escaping non-ASCII.

    Read and write happen inside the lock: the shuffler drains this same file,
    so a read-modify-write outside it is a lost update either way.
    """
    with _stack_index_lock(path):
        lines = path.read_text(encoding="utf-8").splitlines()
        spliced: list[str] = []
        changed = False
        matched = False
        for line in lines:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                spliced.append(line)
                continue
            if isinstance(row, dict) and _row_targets_brief(row, target_brief_id):
                matched = True
                row.update(fields)
                spliced.append(
                    json.dumps(
                        row,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=False,
                    )
                )
                changed = True
            else:
                # Untouched: preserve the original bytes exactly.
                spliced.append(line)
        if not matched:
            # #92: this used to return silently. The file is deliberately not
            # written -- reporting must not become a write.
            raise StackIndexRowUnwritable(
                f"{path}: no stack index row targets brief {target_brief_id!r}"
            )
        if changed:
            _atomic_write(path, "\n".join(spliced) + "\n")


def _row_targets_brief(row: Mapping[str, object], target_brief_id: str) -> bool:
    # `source` is in the tuple because of the migrated legacy shape, where the
    # row's `slug` is the LEGACY slug and the bead id appears nowhere else:
    #   {"slug": "he-ckilh-dispatch-gate", "source": "he-ckilh",
    #    "path": ".../he-ckilh-dispatch-gate.md", "legacy_n": 79}
    # Without it, adjudicating `he-ckilh` updated the bead, the decision TOML
    # and the brief's frontmatter while its own index row kept the pre-verdict
    # status -- the same class of drift #77 fixed, one representation over.
    #
    # Safe because `source` is the index's own record of which bead the row is
    # for. Measured across the live index: 53 of 53 rows carry a string
    # `source`, and NO row's `source` equals a different row's `slug`, so the
    # key cannot pull one brief's verdict onto another's row. The non-bead
    # spellings it also holds (`decisions-track`, `72-...-brief.md`) match no
    # bead id and are therefore inert here.
    for key in ("brief_id", "bead_id", "slug", "id", "source"):
        value = row.get(key)
        if value == target_brief_id:
            return True
    path = row.get("path")
    if isinstance(path, str):
        stem = Path(path).stem
        return stem == target_brief_id or stem.removesuffix("-brief") == target_brief_id
    return False


def _diagnostic(
    ctx: MctlContext,
    severity: Severity,
    code: str,
    message: str,
    *,
    brief_id: str,
    bead_id: str | None = None,
    data_location: str | None = None,
    detail: str | None = None,
    policy_ref: str | None = None,
    suggested_next_command: str | None = None,
) -> Diagnostic:
    facts = {
        "brief_id": brief_id,
        "city_path": str(ctx.city_root),
        "implementation_provenance": "mctl Slice 3 safe brief mutations",
        "operation_context": "brief mutation",
        "rig_name": ctx.rig_id,
        "rig_path": str(ctx.rig_root),
    }
    if bead_id:
        facts["bead_id"] = bead_id
    if data_location:
        facts["data_location"] = data_location
    if detail:
        facts["detail"] = detail
    if policy_ref:
        facts["policy_reference"] = policy_ref
    if suggested_next_command:
        facts["suggested_next_command"] = suggested_next_command
    return Diagnostic(severity, code, message, facts=facts, trace_id=ctx.trace_id)


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _toml_escape(value: str) -> str:
    # Control characters are illegal raw inside a TOML basic string, so a
    # reason carrying newlines must be escaped rather than emitted literally.
    return (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\r", "\\r")
        .replace("\t", "\\t")
    )
