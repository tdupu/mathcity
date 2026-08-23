"""`decisions-to-briefs` as a typed operation: a brief that can be acted on.

#85 records the damage this exists to stop. `decisions-to-briefs/SKILL.md` writes
`.pile/manifest.jsonl` and `decisions-track/` **directly, behind mctl's back**, and
it does that because no typed tool exists to do it properly -- the CT13.2 shape,
capability present, surface absent.

The bar is therefore not "a brief was created". It is that `work_status` on the
result returns `readiness: "ready"` with `blockers: []`. A tool that emits briefs
which cannot then be dispatched does not fix #85, it relocates it: the skill keeps
writing directly, because the sanctioned path still does not work.

`readiness == "ready"` requires ALL of, from `work.py`:

    MWRK011  a source dependency exists
    MWRK012  the source bead resolves
             the source bead is NOT closed
    MWRK010  the brief carries an approving verdict
    MWRK001  the source has no active assignee
    MWRK002  no open child workflow on the source
             no prior dispatch provenance

which is the pair requirement:

    ADJUDICATED BRIEF --(source dependency)--> OPEN SOURCE BEAD
      closed + approving verdict                  status NOT closed

Everything this module refuses is one of those conditions checked BEFORE the write,
so a caller is told at creation rather than discovering it at dispatch.

**This module does NOT create its own source bead.** #173 is the shape that
forbids it: a brief made its own source, then bricked the moment its own approval
closed that source. The source must already exist and be open, and the caller names
it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .beads import Bead
from .diagnostics import Diagnostic, Severity


#: Refusals that mean "this brief would be born undispatchable". Each maps to the
#: `work.py` blocker it prevents, so the two surfaces cannot drift on what
#: "dispatchable" means.
MDTB_NO_SOURCE = "MDTB001"        # -> MWRK011
MDTB_SOURCE_NOT_FOUND = "MDTB002"  # -> MWRK012
MDTB_SOURCE_CLOSED = "MDTB003"     # -> the closed-source blocker
MDTB_SOURCE_ASSIGNED = "MDTB004"   # -> MWRK001
MDTB_SOURCE_HAS_WORKFLOW = "MDTB005"  # -> MWRK002


@dataclass(frozen=True)
class DecisionBriefInput:
    """One already-made decision, and the open bead it decides about."""

    decision: str
    source_bead_id: str
    title: str | None = None
    labels: tuple[str, ...] = ()
    requested_by: str | None = None


def dispatchability_refusals(
    make_diagnostic,
    *,
    source_bead_id: str,
    beads: tuple[Bead, ...],
    open_child_workflow_of,
) -> tuple[Diagnostic, ...]:
    """Every reason this brief would be undispatchable, checked before the write.

    `make_diagnostic` is injected rather than imported so this stays testable
    without a context, and `open_child_workflow_of` is passed in because the
    canonical implementation lives in `work.py` and duplicating it here is how the
    two definitions of "dispatchable" would drift apart.

    Returned as a tuple rather than raising on the first: a caller fixing one
    condition should not have to re-run to discover the next.
    """
    refusals: list[Diagnostic] = []
    if not (source_bead_id or "").strip():
        refusals.append(
            make_diagnostic(
                Severity.ERROR,
                MDTB_NO_SOURCE,
                "A dispatchable brief must name the open bead it decides about.",
                suggested_next_command="mctl work ready --json   # pick an open source bead",
            )
        )
        return tuple(refusals)

    source = next((b for b in beads if b.id == source_bead_id), None)
    if source is None:
        refusals.append(
            make_diagnostic(
                Severity.ERROR,
                MDTB_SOURCE_NOT_FOUND,
                f"Source bead {source_bead_id!r} was not found in this rig.",
                suggested_next_command=f"bd show {source_bead_id}",
            )
        )
        return tuple(refusals)

    if source.status.strip().lower() in {"closed", "done"}:
        # The #173 shape. A closed source cannot be worked, so the brief is born
        # bricked -- and it would report success at creation and fail only later
        # at dispatch.
        refusals.append(
            make_diagnostic(
                Severity.ERROR,
                MDTB_SOURCE_CLOSED,
                f"Source bead {source_bead_id!r} is {source.status}, so the brief "
                "would be undispatchable the moment it is created.",
                suggested_next_command="mctl work ready --json   # pick an open source bead",
            )
        )
    if source.has_active_assignee:
        refusals.append(
            make_diagnostic(
                Severity.ERROR,
                MDTB_SOURCE_ASSIGNED,
                f"Source bead {source_bead_id!r} already has an active assignee.",
                suggested_next_command=f"bd show {source_bead_id}",
            )
        )
    existing = open_child_workflow_of(source_bead_id)
    if existing is not None:
        refusals.append(
            make_diagnostic(
                Severity.ERROR,
                MDTB_SOURCE_HAS_WORKFLOW,
                f"An open child workflow already exists for {source_bead_id!r}.",
                suggested_next_command=f"mctl work status {existing} --json",
            )
        )
    return tuple(refusals)
