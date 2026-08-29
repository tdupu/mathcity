"""mc-p0wps Task 3: `plan_bead_close` closes ONE bead, with loud refusals.

The close verb mirrors `plan_molecule_cancel` but closes a single bead --
cascade-close is `molecule_cancel`'s explicit job. Its two conditional refusals
are the point (P6.2, each observed failing then passing):

- a molecule ROOT with open steps is refused (`MBCL_ROOT_HAS_OPEN_STEPS`), and
  `force` does NOT bypass it (deps-only downgrade, adjudicated 2026-08-28);
- a bead blocked by open dependencies is refused (`MBCL_BLOCKED_BY_OPEN_DEPS`)
  UNLESS `force`, which downgrades it and passes `bd update --force`.

The bead read is injected, so no store, no `bd`.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core import bead_writes  # noqa: E402
from mctl_core.bead_writes import BeadCloseInput, plan_bead_close  # noqa: E402
from mctl_core.beads import Bead  # noqa: E402
from mctl_core.context import MctlContext  # noqa: E402
from mctl_core.effects import MutationError, dry_run_payload  # noqa: E402


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
        trace_id="trace-close-1",
        warnings=(),
        discovery_path="test",
        city_active=None,
        city_endpoint=None,
    )


def _bead(bead_id, *, status="open", metadata=None, kind=None, deps=()):
    meta = dict(metadata or {})
    if kind is not None:
        meta["gc.kind"] = kind
    return Bead(
        id=bead_id,
        title="t",
        status=status,
        issue_type="task",
        labels=(),
        source_dependencies=tuple(deps),
        created_at="2026-08-27T00:00:00Z",
        updated_at="2026-08-27T00:00:00Z",
        raw={"metadata": meta},
    )


def _root(bead_id="mc-root", **kw):
    return _bead(bead_id, kind="workflow", **kw)


def _step(bead_id, root_id="mc-root", **kw):
    return _bead(bead_id, metadata={"gc.root_bead_id": root_id}, **kw)


def _inject(monkeypatch, beads):
    monkeypatch.setattr(bead_writes, "read_beads", lambda *a, **k: tuple(beads))


def _close(ctx, bead_id, *, force=False):
    return plan_bead_close(ctx, BeadCloseInput(bead_id=bead_id, reason=None, force=force))


# --- molecule root with open steps (FATAL, force-independent) ----------------


def test_root_with_open_step_is_refused(monkeypatch, tmp_path):
    _inject(monkeypatch, [_root("mc-root"), _step("mc-s1", status="open")])
    plan = _close(_ctx(tmp_path), "mc-root")
    codes = [d.code for d in plan.preconditions]
    assert "MBCL_ROOT_HAS_OPEN_STEPS" in codes
    assert plan.bead_updates == (), "a refused root must not plan a close"
    with pytest.raises(MutationError):
        dry_run_payload(plan)


def test_root_closes_once_its_steps_are_closed(monkeypatch, tmp_path):
    _inject(monkeypatch, [_root("mc-root"), _step("mc-s1", status="closed")])
    plan = _close(_ctx(tmp_path), "mc-root")
    assert not plan.preconditions
    assert len(plan.bead_updates) == 1
    assert plan.bead_updates[0].id == "mc-root"
    assert plan.bead_updates[0].status == "closed"


def test_force_does_not_bypass_the_root_open_steps_guard(monkeypatch, tmp_path):
    """Negative control: force is deps-only, never the false-success guard."""
    _inject(monkeypatch, [_root("mc-root"), _step("mc-s1", status="open")])
    plan = _close(_ctx(tmp_path), "mc-root", force=True)
    codes = [d.code for d in plan.preconditions]
    assert "MBCL_ROOT_HAS_OPEN_STEPS" in codes
    with pytest.raises(MutationError):
        dry_run_payload(plan)


# --- blocked by open dependencies (ERROR, force downgrades) ------------------


def test_blocked_by_open_deps_is_refused(monkeypatch, tmp_path):
    _inject(
        monkeypatch,
        [_bead("mc-b", deps=("mc-dep",)), _bead("mc-dep", status="open")],
    )
    plan = _close(_ctx(tmp_path), "mc-b")
    codes = [d.code for d in plan.preconditions]
    assert "MBCL_BLOCKED_BY_OPEN_DEPS" in codes
    with pytest.raises(MutationError):
        dry_run_payload(plan)


def test_force_downgrades_blocked_by_open_deps(monkeypatch, tmp_path):
    _inject(
        monkeypatch,
        [_bead("mc-b", deps=("mc-dep",)), _bead("mc-dep", status="open")],
    )
    plan = _close(_ctx(tmp_path), "mc-b", force=True)
    assert not plan.preconditions, "force downgrades the blocked-by-deps refusal"
    assert len(plan.bead_updates) == 1
    assert plan.bead_updates[0].force is True
    assert plan.bead_updates[0].status == "closed"


def test_closed_deps_do_not_block(monkeypatch, tmp_path):
    _inject(
        monkeypatch,
        [_bead("mc-b", deps=("mc-dep",)), _bead("mc-dep", status="closed")],
    )
    plan = _close(_ctx(tmp_path), "mc-b")
    assert not plan.preconditions
    assert len(plan.bead_updates) == 1


# --- non-existent bead (FATAL) -----------------------------------------------


def test_non_existent_bead_is_refused(monkeypatch, tmp_path):
    _inject(monkeypatch, [_bead("mc-other")])
    plan = _close(_ctx(tmp_path), "mc-missing")
    codes = [d.code for d in plan.preconditions]
    assert "MBCL_NO_SUCH_BEAD" in codes
    assert plan.bead_updates == ()
    with pytest.raises(MutationError):
        dry_run_payload(plan)


# --- a plain open bead closes with an if_status race guard --------------------


def test_plain_open_bead_closes_with_if_status(monkeypatch, tmp_path):
    _inject(monkeypatch, [_bead("mc-b", status="in_progress")])
    plan = _close(_ctx(tmp_path), "mc-b")
    assert not plan.preconditions
    assert len(plan.bead_updates) == 1
    update = plan.bead_updates[0]
    assert update.id == "mc-b"
    assert update.status == "closed"
    assert update.if_status == "in_progress", "inherits MCTL_BEAD_UPDATE_RACE_LOST"
    assert update.metadata["mctl_trace_id"] == "trace-close-1"
