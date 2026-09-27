"""#86/#84: the `review_gate` write path, and the root B2.8a implies for it.

`fields.py` READ `review_gate` among ~100 live keys and nothing could set it. So
`formulas/brief-review-patrol.toml` instructed an agent to patch the brief's
frontmatter in place -- a B2.11/B2.14 violation as written, and one that could
NOT be fixed by "route it through mctl", because mctl had no call to route to.
The only frontmatter writer was `plan_adjudication`, hardcoded to
`status`/`verdict`/`adjudicated_at`.

The load-bearing assertion here is `test_no_bead_is_written`. B2.8a declares the
frontmatter canonical for this class, following B2.8a: the bead is scoped to
"identity, status, timestamps and labels, and little else", and a PRE-adjudication
field is none of those -- so a bead-first repair would resolve `review_gate` by
DELETING it. Measured 2026-09-27 on `~/gt/mathcity` (2,364 beads): `review_gate`
appears in 0 bead metadata records.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.context import MctlContext  # noqa: E402
from mctl_core.effects import (  # noqa: E402
    REVIEW_GATE_VALUES,
    _apply_cache_update,
    is_review_gate,
    plan_review_gate,
)


def _ctx(tmp_path: Path) -> MctlContext:
    return MctlContext(
        city_root=tmp_path,
        rig_id="mathcity",
        rig_root=tmp_path / "rig",
        beads_fixture=tmp_path / "issues.jsonl",
        rig_db=".beads",
        source_checkout=tmp_path,
        paths_toml=tmp_path / "paths.toml",
        gates_toml=tmp_path / "gates.toml",
        invocation_cwd=tmp_path,
        trace_id="trace-gate-1",
        warnings=(),
        discovery_path="test",
        city_active=None,
        city_endpoint=None,
    )


def _brief(ctx: MctlContext, brief_id: str, *, gate: str, status: str) -> Path:
    stack = ctx.rig_root / ".beads" / "briefs" / "stack"
    stack.mkdir(parents=True, exist_ok=True)
    path = stack / f"{brief_id}-brief.md"
    path.write_text(
        f"---\nstatus: {status}\nreview_gate: {gate}\nform: full\n---\n\nbody\n",
        encoding="utf-8",
    )
    return path


def test_no_bead_is_written(tmp_path: Path):
    """B2.8a: frontmatter is the canonical root for this class, so the bead stays out.

    Writing `review_gate` to a bead would mint a SECOND root for one artifact
    class, which is exactly the P1.22 failure the declaration exists to prevent.
    """
    ctx = _ctx(tmp_path)
    _brief(ctx, "mc-g1", gate="pending", status="pending-review")

    plan = plan_review_gate(ctx, "mc-g1", gate="approved")

    assert plan.bead_updates == (), "review_gate must not be written to a bead"
    assert len(plan.cache_updates) == 1
    assert plan.cache_updates[0].kind == "brief_frontmatter"


def test_an_approving_advance_carries_status_and_applies(tmp_path: Path):
    """The patrol's own contract: pending -> approved moves `status:` with it."""
    ctx = _ctx(tmp_path)
    path = _brief(ctx, "mc-g2", gate="pending", status="pending-review")

    plan = plan_review_gate(ctx, "mc-g2", gate="approved", from_gate="pending")
    assert plan.preconditions == ()
    assert plan.cache_updates[0].fields == {"review_gate": "approved", "status": "approved"}

    _apply_cache_update(plan.cache_updates[0])
    text = path.read_text(encoding="utf-8")
    assert "review_gate: approved" in text
    assert "status: approved" in text
    assert "form: full" in text, "an unrelated frontmatter field must survive"


def test_a_failing_advance_does_not_touch_status(tmp_path: Path):
    """review-failed moves the gate only; `status:` is not an outcome here."""
    ctx = _ctx(tmp_path)
    _brief(ctx, "mc-g3", gate="pending", status="pending-review")

    plan = plan_review_gate(ctx, "mc-g3", gate="review-failed")

    assert plan.cache_updates[0].fields == {"review_gate": "review-failed"}


def test_an_adjudicated_brief_is_not_walked_back_to_approved(tmp_path: Path):
    """A recorded verdict must not be contradicted by a review-lane write.

    `status: adjudicated` is post-verdict. Rewriting it to `approved` would make
    the document disagree with its own decision, which is the #77 drift one
    field over.
    """
    ctx = _ctx(tmp_path)
    _brief(ctx, "mc-g4", gate="pending", status="adjudicated")

    plan = plan_review_gate(ctx, "mc-g4", gate="approved")

    assert plan.cache_updates[0].fields == {"review_gate": "approved"}
    assert "status" not in plan.cache_updates[0].fields


def test_from_gate_refuses_a_stale_observation(tmp_path: Path):
    """MBRF071 -- the frontmatter analogue of `BeadUpdate.if_status`.

    The patrol advances briefs it observed at `pending`; between observing and
    writing, another writer can move the gate. Without this guard the patrol
    would overwrite a decision it never saw.
    """
    ctx = _ctx(tmp_path)
    _brief(ctx, "mc-g5", gate="review-failed", status="pending-review")

    plan = plan_review_gate(ctx, "mc-g5", gate="approved", from_gate="pending")

    assert [d.code for d in plan.preconditions] == ["MBRF071"]
    assert plan.cache_updates == (), "a refused plan must propose no write"


def test_omitting_from_gate_is_an_unconditional_set(tmp_path: Path):
    """A human repairing one brief by hand has no prior observation to declare."""
    ctx = _ctx(tmp_path)
    _brief(ctx, "mc-g6", gate="review-failed", status="pending-review")

    plan = plan_review_gate(ctx, "mc-g6", gate="pending")

    assert plan.preconditions == ()
    assert plan.cache_updates[0].fields["review_gate"] == "pending"


def test_an_undeclared_gate_value_is_refused(tmp_path: Path):
    """MBRF072 -- typed, not a generic frontmatter setter.

    This codebase forbids generic passthrough tools (`FORBIDDEN_TOOL_NAMES`), and
    a write path that accepted any string would be one for frontmatter.
    """
    ctx = _ctx(tmp_path)
    _brief(ctx, "mc-g7", gate="pending", status="pending-review")

    plan = plan_review_gate(ctx, "mc-g7", gate="looks-fine-to-me")

    assert [d.code for d in plan.preconditions] == ["MBRF072"]
    assert plan.cache_updates == ()


@pytest.mark.parametrize("gate", sorted(REVIEW_GATE_VALUES) + ["iter-1", "iter-12"])
def test_every_declared_value_is_accepted(gate: str):
    """`iter-N` is a PATTERN: an enum listing `iter-1` goes stale at iteration two."""
    assert is_review_gate(gate)


@pytest.mark.parametrize("gate", ["iter-", "iter-x", "approved!", "", "ITER-1", "pending "])
def test_near_misses_are_rejected(gate: str):
    assert not is_review_gate(gate)


def test_the_escalation_lane_values_are_carried(tmp_path: Path):
    """`escalation-*` exist so the escalation lane need not borrow `review-failed`.

    Borrowing it asserts a review ran and failed; in that lane no external review
    was obtainable, which is a different fact. So the vocabulary must carry them.
    """
    assert "escalation-self-checked" in REVIEW_GATE_VALUES
    assert "escalation-unreviewed" in REVIEW_GATE_VALUES


def test_a_brief_with_no_stack_file_plans_nothing(tmp_path: Path):
    """Absence is the ordinary path, as with an absent decision TOML."""
    ctx = _ctx(tmp_path)
    (ctx.rig_root / ".beads" / "briefs" / "stack").mkdir(parents=True, exist_ok=True)

    plan = plan_review_gate(ctx, "mc-absent", gate="approved")

    assert plan.cache_updates == ()
    assert plan.preconditions == ()
