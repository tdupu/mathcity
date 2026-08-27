"""Typed molecule cancel (mc-x06e).

A running molecule could only be left to run, its worker session killed (leaving
wedged state), or its beads closed by hand (bypassing finalize). `plan_molecule_cancel`
is the typed reverse of a dispatch: it closes the molecule's OPEN steps and its
root with `cancelled` metadata, releases any live claim, never deletes, and
refuses a molecule a worker is actively running unless forced.

These tests pin the plan's shape directly -- the bead read is injected, so no
store, no `gc`, no `bd` -- and prove the refusals actually fire (P6.2).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core import effects  # noqa: E402
from mctl_core.beads import Bead  # noqa: E402
from mctl_core.context import MctlContext  # noqa: E402
from mctl_core.effects import MutationError, dry_run_payload, plan_molecule_cancel  # noqa: E402


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
        trace_id="trace-cancel-1",
        warnings=(),
        discovery_path="test",
        city_active=None,
        city_endpoint=None,
    )


def _bead(bead_id, *, status="open", metadata=None, assignee=None, kind=None):
    meta = dict(metadata or {})
    if kind is not None:
        meta["gc.kind"] = kind
    return Bead(
        id=bead_id,
        title="t",
        status=status,
        issue_type="task",
        labels=(),
        source_dependencies=(),
        created_at="2026-08-27T00:00:00Z",
        updated_at="2026-08-27T00:00:00Z",
        raw={"metadata": meta},
        assignee=assignee,
    )


def _root(bead_id="mc-root", **kw):
    return _bead(bead_id, kind="workflow", **kw)


def _step(bead_id, root_id="mc-root", **kw):
    return _bead(bead_id, metadata={"gc.root_bead_id": root_id}, **kw)


def _inject(monkeypatch, beads):
    monkeypatch.setattr(effects, "read_beads", lambda *a, **k: tuple(beads))


def _updates_by_id(plan):
    return {u.id: u for u in plan.bead_updates}


def test_cancel_closes_open_steps_and_the_root_steps_first(monkeypatch, tmp_path):
    beads = [
        _root("mc-root"),
        _step("mc-s1", status="open"),
        _step("mc-s2", status="closed"),  # already closed -- untouched
        _step("mc-s3", status="in_progress"),
    ]
    _inject(monkeypatch, beads)

    plan = plan_molecule_cancel(_ctx(tmp_path), root_bead_id="mc-root")

    ids = [u.id for u in plan.bead_updates]
    assert "mc-s2" not in ids, "an already-closed step must not be touched"
    assert set(ids) == {"mc-s1", "mc-s3", "mc-root"}
    assert ids[-1] == "mc-root", "the root must close LAST, after its open children"
    for update in plan.bead_updates:
        assert update.status == "closed"
        assert update.metadata["gc.cancelled"] == "true"
    assert not plan.preconditions, "an unattended molecule cancels without refusal"


def test_cancel_releases_the_claim_on_a_running_step_when_forced(monkeypatch, tmp_path):
    beads = [_root("mc-root"), _step("mc-s1", status="in_progress", assignee="gc__worker-7")]
    _inject(monkeypatch, beads)

    plan = plan_molecule_cancel(_ctx(tmp_path), root_bead_id="mc-root", force=True)

    updates = _updates_by_id(plan)
    assert updates["mc-s1"].assignee == "", "a forced cancel must RELEASE the worker's claim"
    assert not plan.preconditions, "force clears the mid-execution refusal"


def test_a_step_mid_execution_refuses_without_force(monkeypatch, tmp_path):
    beads = [_root("mc-root"), _step("mc-s1", status="in_progress", assignee="gc__worker-7")]
    _inject(monkeypatch, beads)

    plan = plan_molecule_cancel(_ctx(tmp_path), root_bead_id="mc-root", force=False)

    codes = [d.code for d in plan.preconditions]
    assert "MCTL_MOLECULE_CANCEL_STEP_MID_EXECUTION" in codes
    # The observed failing case (P6.2): a blocking precondition stops the dry run.
    with pytest.raises(MutationError):
        dry_run_payload(plan)


def test_an_unattended_open_step_is_not_a_wedge(monkeypatch, tmp_path):
    """The blocker-vs-wedge distinction: an OPEN step with no live assignee is a
    blocker to clear, not a running worker, so it cancels without force."""
    beads = [_root("mc-root"), _step("mc-s1", status="open", assignee=None)]
    _inject(monkeypatch, beads)

    plan = plan_molecule_cancel(_ctx(tmp_path), root_bead_id="mc-root")
    assert not plan.preconditions
    assert dry_run_payload(plan)["applied"] is False


def test_an_already_closed_molecule_is_refused_not_cancelled(monkeypatch, tmp_path):
    _inject(monkeypatch, [_root("mc-root", status="closed")])

    plan = plan_molecule_cancel(_ctx(tmp_path), root_bead_id="mc-root")
    assert [d.code for d in plan.preconditions] == ["MCTL_MOLECULE_CANCEL_ALREADY_CLOSED"]
    assert plan.bead_updates == (), "nothing is planned against a finished molecule"
    with pytest.raises(MutationError):
        dry_run_payload(plan)


def test_no_such_molecule_is_fatal_and_writes_nothing(monkeypatch, tmp_path):
    _inject(monkeypatch, [])

    plan = plan_molecule_cancel(_ctx(tmp_path), root_bead_id="mc-ghost")
    assert [d.code for d in plan.preconditions] == ["MCTL_MOLECULE_CANCEL_NO_SUCH_MOLECULE"]
    assert plan.bead_updates == ()


def test_cancelling_a_step_id_is_refused_as_not_a_root(monkeypatch, tmp_path):
    beads = [_root("mc-root"), _step("mc-s1", status="open")]
    _inject(monkeypatch, beads)

    plan = plan_molecule_cancel(_ctx(tmp_path), root_bead_id="mc-s1")
    assert [d.code for d in plan.preconditions] == ["MCTL_MOLECULE_CANCEL_NOT_A_ROOT"]


def test_the_plan_records_a_cancel_event_and_trace(monkeypatch, tmp_path):
    beads = [_root("mc-root"), _step("mc-s1", status="open")]
    _inject(monkeypatch, beads)

    plan = plan_molecule_cancel(_ctx(tmp_path), root_bead_id="mc-root")
    assert plan.operation == "molecule.cancel"
    assert plan.event_writes and plan.event_writes[0].row["operation"] == "molecule.cancel"
    assert plan.trace_writes and plan.trace_writes[0].row["operation"] == "molecule.cancel"
