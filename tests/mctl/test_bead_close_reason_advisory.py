"""A silent close is surfaced, not blocked (#238, BP4.1/BP4.3).

`POLICY-beads.md` states the reaping rules and NOTHING enforces them --
`grep -rn "BP4\\." assets/` returns zero hits. The audit behind #238 found
16 of 27 swept closures over-closed, and the sharpest consequence was a
circular duplicate collapse.

This does NOT make a reason mandatory, deliberately. BP4.1 scopes the
requirement to REAPING an old-useless bead ("a `bd close` with an explicit
reason naming the BP4.2 criterion met"), and nothing in the close path marks a
close as a reap. A blanket refusal would therefore over-enforce a rule the
policy scopes narrowly -- and closes that legitimately need no criterion would
start failing.

What IS enforceable without that distinction is BP4.3's "Sweeps never run
silently": a close carrying no reason at all is unattributable after the fact,
which is exactly what made the #238 audit necessary and expensive. So it
becomes a WARN advisory naming the rule, never a block.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core import bead_writes  # noqa: E402
from mctl_core.bead_writes import BeadCloseInput, plan_bead_close  # noqa: E402

from test_bead_close import _bead, _ctx, _inject  # noqa: E402


def _advisory_codes(plan):
    return {d.code for d in plan.advisories}


def test_a_close_with_no_reason_raises_a_BP4_advisory(monkeypatch, tmp_path):
    ctx = _ctx(tmp_path)
    _inject(monkeypatch, [_bead("mc-open1")])
    plan = plan_bead_close(ctx, BeadCloseInput(bead_id="mc-open1", reason=None))
    assert "MBCL_REASON_ABSENT" in _advisory_codes(plan)


def test_the_advisory_does_NOT_block_the_close(monkeypatch, tmp_path):
    """P6.2's other half: the check must not turn a legal close into a refusal."""
    ctx = _ctx(tmp_path)
    _inject(monkeypatch, [_bead("mc-open1")])
    plan = plan_bead_close(ctx, BeadCloseInput(bead_id="mc-open1", reason=None))
    blocking = [d for d in plan.preconditions]
    assert not blocking, f"a missing reason must advise, not block: {blocking}"


def test_a_close_WITH_a_reason_raises_no_advisory(monkeypatch, tmp_path):
    """The positive control. Without this, an always-firing advisory would pass."""
    ctx = _ctx(tmp_path)
    _inject(monkeypatch, [_bead("mc-open1")])
    plan = plan_bead_close(
        ctx, BeadCloseInput(bead_id="mc-open1", reason="BP4.2(a): superseded by mc-9")
    )
    assert "MBCL_REASON_ABSENT" not in _advisory_codes(plan)


def test_whitespace_is_not_a_reason(monkeypatch, tmp_path):
    ctx = _ctx(tmp_path)
    _inject(monkeypatch, [_bead("mc-open1")])
    plan = plan_bead_close(ctx, BeadCloseInput(bead_id="mc-open1", reason="   "))
    assert "MBCL_REASON_ABSENT" in _advisory_codes(plan)
