"""#185: mint a defect bead when no GitHub issue exists yet.

`create_issue_bead` mirrors an issue that already exists; this is the "not
conversely" case of the owner's rule -- *"all github issues paired with a bead,
but not conversely"*. A Mayor that finds a defect can record it as an OPEN task
bead carrying `metadata.defect_report=true` and NO `gh.issue` key, so the matter
enters the pipeline before any issue is filed.

Kept in its own module (not folded into `effects.py`) because it is a distinct
intake seam: it reuses the shared effect-plan machinery and the extracted
label->priority mapper, and adds one rule of its own -- refuse to mint an orphan
duplicate of an OPEN defect already recorded.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping

from .beads import BeadCreate, priority_from_labels, read_beads
from .context import MctlContext
from .diagnostics import Diagnostic, Severity
from .effects import EffectPlan, MutationError, _now


#: The plan cannot name the bead it is about to create -- bd mints the id -- so
#: derived text is planned against this token and rewritten once bd answers.
#: A distinct token from the brief/issue placeholders: this never denotes either.
NEW_DEFECT_BEAD_ID_PLACEHOLDER = "(pending-defect-bead-id)"

#: The metadata values that read as "this task bead is a filed defect report".
_TRUE = {"true", "1", "yes"}


@dataclass(frozen=True)
class DefectBeadCreateInput:
    title: str
    body: str
    labels: tuple[str, ...] = ()


def plan_create_defect_bead(
    ctx: MctlContext, request: DefectBeadCreateInput
) -> EffectPlan:
    """Plan minting an OPEN defect task bead with no paired GitHub issue.

    Every branch here is a read (the existing-defect scan over already-
    materialised beads) or pure computation -- no `bd create`, no `mkdir`,
    nothing that could make a dry run mutate (#188). The single refusal is the
    orphan-duplicate guard: §4 warns this tool must "refuse to mint orphans at
    scale", so an identical-title OPEN defect bead blocks a second mint. A CLOSED
    one does not -- a resolved defect that recurs is a new defect.
    """
    title = request.title.strip()
    existing = _find_open_defect(ctx, title)
    if existing is not None:
        raise MutationError(
            Diagnostic(
                Severity.FATAL,
                "MGHW_DUPLICATE_DEFECT",
                f"An open defect bead already records this report: {existing}.",
                hint=(
                    "Refusing to mint an orphan duplicate; update or close the "
                    "existing defect bead instead."
                ),
                facts={
                    "city_path": str(ctx.city_root),
                    "rig_name": ctx.rig_id,
                    "bead_id": existing,
                },
                trace_id=ctx.trace_id,
            )
        )

    metadata: dict[str, str] = {
        "created_by": "mctl",
        "mctl_trace_id": ctx.trace_id,
        "created_at": _now(),
        "defect_report": "true",
    }
    # Absent means the caller supplied none; an empty string is a value that
    # looks like a measurement and is not one -- the same `gh.labels`
    # absent-not-empty discipline `create_issue_bead` follows. Stored in
    # metadata rather than as bd labels because `priority/pN` and `kind/bug`
    # carry a slash, which bd rejects as a label token (MBRF033).
    if request.labels:
        metadata["defect.labels"] = ",".join(request.labels)
    bead_create = BeadCreate(
        placeholder_id=NEW_DEFECT_BEAD_ID_PLACEHOLDER,
        title=title,
        body=request.body,
        issue_type="task",
        labels=(),
        metadata=metadata,
        sources=(),
        priority=priority_from_labels(request.labels),
    )
    return EffectPlan(
        trace_id=ctx.trace_id,
        operation="create_defect_bead",
        target_brief_id=NEW_DEFECT_BEAD_ID_PLACEHOLDER,
        preconditions=(),
        bead_updates=(),
        cache_updates=(),
        event_writes=(),
        trace_writes=(),
        bead_creates=(bead_create,),
    )


def _find_open_defect(ctx: MctlContext, title: str) -> str | None:
    """The id of an OPEN defect bead with this exact title, if one exists.

    Title match is case-insensitive on the stripped string -- the same identity
    a human would use to say "we already filed that". Only OPEN defect beads
    count: a closed one is a resolved matter, not a live duplicate.
    """
    target = title.strip().lower()
    for bead in read_beads(ctx.rig_root, fixture_path=ctx.beads_fixture, issue_type="task"):
        metadata = bead.raw.get("metadata")
        is_defect = isinstance(metadata, Mapping) and str(
            metadata.get("defect_report", "")
        ).strip().lower() in _TRUE
        if is_defect and bead.is_open and bead.title.strip().lower() == target:
            return bead.id
    return None
