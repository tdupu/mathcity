"""mc-p0wps Task 4: `plan_bead_hold` / `plan_bead_release`.

Hold and release set and clear a `hold:*` LABEL (mc-qcnaz option A -- not a
status change, not defer/undefer). Each plans exactly one `BeadLabelChange`.
Refusals (FATAL, dry-run-visible because the builder raises before returning):
a slash in the label (honoring MBRF033 -- colon-form or bare only) and a
non-existent bead.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core import bead_writes  # noqa: E402
from mctl_core.bead_writes import (  # noqa: E402
    BeadHoldInput,
    BeadReleaseInput,
    plan_bead_hold,
    plan_bead_release,
)
from mctl_core.beads import Bead  # noqa: E402
from mctl_core.context import MctlContext  # noqa: E402
from mctl_core.effects import MutationError  # noqa: E402


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
        trace_id="trace-hold-1",
        warnings=(),
        discovery_path="test",
        city_active=None,
        city_endpoint=None,
    )


def _bead(bead_id="mc-b"):
    return Bead(
        id=bead_id,
        title="t",
        status="open",
        issue_type="task",
        labels=(),
        source_dependencies=(),
        created_at="2026-08-27T00:00:00Z",
        updated_at="2026-08-27T00:00:00Z",
        raw={},
    )


def _inject(monkeypatch, beads):
    monkeypatch.setattr(bead_writes, "read_beads", lambda *a, **k: tuple(beads))


# --- hold --------------------------------------------------------------------


def test_hold_plans_a_label_add(monkeypatch, tmp_path):
    _inject(monkeypatch, [_bead("mc-b")])
    plan = plan_bead_hold(_ctx(tmp_path), BeadHoldInput(bead_id="mc-b"))
    assert plan.bead_updates == ()
    assert len(plan.bead_label_changes) == 1
    change = plan.bead_label_changes[0]
    assert change.bead_id == "mc-b"
    assert change.label == "hold"
    assert change.action == "add"


def test_hold_accepts_a_colon_form_label(monkeypatch, tmp_path):
    _inject(monkeypatch, [_bead("mc-b")])
    plan = plan_bead_hold(_ctx(tmp_path), BeadHoldInput(bead_id="mc-b", label="hold:soak"))
    assert plan.bead_label_changes[0].label == "hold:soak"


def test_hold_refuses_a_slashed_label(monkeypatch, tmp_path):
    _inject(monkeypatch, [_bead("mc-b")])
    with pytest.raises(MutationError) as excinfo:
        plan_bead_hold(_ctx(tmp_path), BeadHoldInput(bead_id="mc-b", label="hold/soak"))
    assert excinfo.value.diagnostic.code == "MBHD_LABEL_HAS_SLASH"


def test_hold_refuses_a_non_existent_bead(monkeypatch, tmp_path):
    _inject(monkeypatch, [_bead("mc-other")])
    with pytest.raises(MutationError) as excinfo:
        plan_bead_hold(_ctx(tmp_path), BeadHoldInput(bead_id="mc-missing"))
    assert excinfo.value.diagnostic.code == "MBHD_NO_SUCH_BEAD"


# --- release -----------------------------------------------------------------


def test_release_plans_a_label_remove(monkeypatch, tmp_path):
    _inject(monkeypatch, [_bead("mc-b")])
    plan = plan_bead_release(_ctx(tmp_path), BeadReleaseInput(bead_id="mc-b"))
    assert len(plan.bead_label_changes) == 1
    change = plan.bead_label_changes[0]
    assert change.label == "hold"
    assert change.action == "remove"


def test_release_refuses_a_slashed_label(monkeypatch, tmp_path):
    _inject(monkeypatch, [_bead("mc-b")])
    with pytest.raises(MutationError) as excinfo:
        plan_bead_release(_ctx(tmp_path), BeadReleaseInput(bead_id="mc-b", label="hold/x"))
    assert excinfo.value.diagnostic.code == "MBRL_LABEL_HAS_SLASH"


def test_release_refuses_a_non_existent_bead(monkeypatch, tmp_path):
    _inject(monkeypatch, [_bead("mc-other")])
    with pytest.raises(MutationError) as excinfo:
        plan_bead_release(_ctx(tmp_path), BeadReleaseInput(bead_id="mc-missing"))
    assert excinfo.value.diagnostic.code == "MBRL_NO_SUCH_BEAD"
