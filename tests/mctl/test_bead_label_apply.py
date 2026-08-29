"""mc-p0wps Task 2: a label-mutation apply path.

mctl had update/create/relate/comment apply paths but nothing that set or
cleared a label. `bead_hold`/`bead_release` need one, so `BeadLabelChange` is
carried on the `EffectPlan` and `apply_bead_label` shells `bd label add|remove
<label> <bead_id>` with the same subprocess discipline as the other
`_apply_bd_*` helpers.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import beads
from mctl_core.beads import BeadLabelChange, apply_bead_label


def _recorder(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="", stderr="")

    monkeypatch.setattr(beads.subprocess, "run", fake_run)
    return calls


def test_add_records_bd_label_add(monkeypatch, tmp_path):
    calls = _recorder(monkeypatch)
    apply_bead_label(tmp_path, BeadLabelChange("mc-1", "hold", "add"))
    assert calls
    assert calls[0][:5] == ["bd", "label", "add", "hold", "mc-1"]


def test_remove_records_bd_label_remove(monkeypatch, tmp_path):
    calls = _recorder(monkeypatch)
    apply_bead_label(tmp_path, BeadLabelChange("mc-1", "hold", "remove"))
    assert calls
    assert calls[0][:5] == ["bd", "label", "remove", "hold", "mc-1"]


def test_to_dict_shape():
    change = BeadLabelChange("mc-1", "hold:soak", "add")
    assert change.to_dict() == {
        "bead_id": "mc-1",
        "label": "hold:soak",
        "action": "add",
    }


def test_effect_plan_carries_label_changes():
    from mctl_core.effects import EffectPlan

    plan = EffectPlan(
        trace_id="t",
        operation="bead_hold",
        target_brief_id="mc-1",
        preconditions=(),
        bead_updates=(),
        cache_updates=(),
        event_writes=(),
        trace_writes=(),
        bead_label_changes=(BeadLabelChange("mc-1", "hold", "add"),),
    )
    assert plan.to_dict()["bead_label_changes"] == [
        {"bead_id": "mc-1", "label": "hold", "action": "add"}
    ]
