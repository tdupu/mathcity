"""mc-ilia: append-only comments on an existing bead.

The write surface was create-only: `create_defect_bead`, `create_issue_bead`,
`briefs_create`/`commission_brief` all MINT new beads, and `briefs_adjudicate`
writes a verdict only to a brief. Nothing attached a note to an existing task
bead, so a record filed on a premise later refuted (mc-8ij1) stayed wrong
permanently and the correction had to become a whole second bead (mc-5ir2).

`plan_bead_comment` closes that gap the append-only way (P1.19 / P5.4): it plans
one `BeadComment` effect, which wraps `bd comment`. The bead's description is
never edited, so what was believed and when stays readable beside the
correction. Kept in its own module (not folded into `effects.py`) for the same
reason `defect_beads.py` is: it is a distinct intake seam that reuses the shared
effect-plan machinery and adds only its own two refusals.
"""
from __future__ import annotations

from dataclasses import dataclass

from .beads import read_beads
from .context import MctlContext
from .diagnostics import Diagnostic, Severity
from .effects import BeadComment, EffectPlan, MutationError


@dataclass(frozen=True)
class BeadCommentInput:
    bead_id: str
    text: str


def plan_bead_comment(ctx: MctlContext, request: BeadCommentInput) -> EffectPlan:
    """Plan appending one comment to an existing bead.

    Every branch is a read (the existence scan) or pure computation -- no
    `bd comment`, nothing that could make a dry run mutate (#188). Two refusals:
    an empty comment (a note that says nothing is not a correction), and a
    comment on a bead that does not exist (a correction with nothing to attach to
    is the very failure mc-ilia is about, inverted).
    """
    bead_id = request.bead_id.strip()
    facts = {
        "city_path": str(ctx.city_root),
        "rig_name": ctx.rig_id,
        "bead_id": bead_id,
    }
    if not request.text.strip():
        raise MutationError(
            Diagnostic(
                Severity.FATAL,
                "MBCM_EMPTY_COMMENT",
                "A comment must carry text; refusing to append an empty note.",
                hint="Pass the correction or annotation as `comment`.",
                facts=facts,
                trace_id=ctx.trace_id,
            )
        )
    if not _bead_exists(ctx, bead_id):
        raise MutationError(
            Diagnostic(
                Severity.FATAL,
                "MBCM_NO_SUCH_BEAD",
                f"No bead named {bead_id!r} exists to comment on.",
                hint="A comment must attach to an existing bead; check the id.",
                facts=facts,
                trace_id=ctx.trace_id,
            )
        )
    return EffectPlan(
        trace_id=ctx.trace_id,
        operation="bead_comment",
        target_brief_id=bead_id,
        preconditions=(),
        bead_updates=(),
        cache_updates=(),
        event_writes=(),
        trace_writes=(),
        # Stored verbatim: a comment is quoted evidence, not a field to normalise.
        bead_comments=(BeadComment(bead_id=bead_id, text=request.text),),
    )


def _bead_exists(ctx: MctlContext, bead_id: str) -> bool:
    """True if a bead of ANY type carries this id.

    `issue_type=None` reads every kind: a comment can correct a task, a decision
    brief, or a mirror bead, so the existence check must not narrow to one.
    """
    for bead in read_beads(ctx.rig_root, fixture_path=ctx.beads_fixture):
        if bead.id == bead_id:
            return True
    return False
