"""B3.1 acceptance is RECORDED on close, and its absence is advised (#233).

B3.1 requires one of four things before closing: (a) acceptance criteria checked
off, (b) a linked test passes, (c) an external review says PASS, or (d) the
adjudicator said "close it". `grep -rn acceptance assets/scripts/mctl_core/`
returned nothing: stated policy, zero code.

DETECTING acceptance is not possible here and is not attempted. (b) and (c)
live outside the bead entirely, so a checker that inferred acceptance from the
description would fire on legitimate test-backed and review-backed closes -- the
over-refusal trap that made #219 revert and that #195's detector deliberately
avoids.

So the close ASKS instead: an optional `acceptance` records WHICH limb was
satisfied and its evidence, stored on the bead where an audit can read it. Its
absence is a WARN, never a refusal -- the same shape as MBCL_REASON_ABSENT
(#238/BP4.3), and for the same reason: a rule scoped to some closes must not
block all of them.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core.bead_writes import BeadCloseInput, plan_bead_close  # noqa: E402

from test_bead_close import _bead, _ctx, _inject  # noqa: E402


def _codes(plan):
    return {d.code for d in plan.advisories}


def _updates(plan):
    out = {}
    for update in plan.bead_updates:
        out.update(dict(update.metadata or {}))
    return out


def test_a_close_with_no_acceptance_raises_a_B3_1_advisory(monkeypatch, tmp_path):
    ctx = _ctx(tmp_path)
    _inject(monkeypatch, [_bead("mc-open1")])
    plan = plan_bead_close(ctx, BeadCloseInput(bead_id="mc-open1", reason="done"))
    assert "MBCL_ACCEPTANCE_ABSENT" in _codes(plan)


def test_recorded_acceptance_is_stored_on_the_bead(monkeypatch, tmp_path):
    """It must land in metadata, or 'recorded' is a claim with no artifact."""
    ctx = _ctx(tmp_path)
    _inject(monkeypatch, [_bead("mc-open1")])
    plan = plan_bead_close(
        ctx,
        BeadCloseInput(bead_id="mc-open1", reason="done", acceptance="b: tests/x passes"),
    )
    assert _updates(plan).get("mctl_close_acceptance") == "b: tests/x passes"


def test_recorded_acceptance_silences_the_advisory(monkeypatch, tmp_path):
    """Positive control: an always-firing advisory would pass the first test."""
    ctx = _ctx(tmp_path)
    _inject(monkeypatch, [_bead("mc-open1")])
    plan = plan_bead_close(
        ctx,
        BeadCloseInput(bead_id="mc-open1", reason="done", acceptance="d: owner said close it"),
    )
    assert "MBCL_ACCEPTANCE_ABSENT" not in _codes(plan)


def test_the_advisory_does_NOT_block(monkeypatch, tmp_path):
    ctx = _ctx(tmp_path)
    _inject(monkeypatch, [_bead("mc-open1")])
    plan = plan_bead_close(ctx, BeadCloseInput(bead_id="mc-open1", reason="done"))
    assert not list(plan.preconditions), "B3.1 must advise, not refuse"
