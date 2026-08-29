"""mc-p0wps Task 1: `BeadUpdate.force` appends `bd update --force`.

`bead_close --force` must downgrade bd's own blocked-by-deps refusal, which bd
exposes through `bd update --force`. The flag reaches the argv only when the
plan set `force=True`; the default carries no `--force`, so a normal close is
never silently forced.
"""
from __future__ import annotations

import subprocess
import sys
import types
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import beads
from mctl_core.beads import BeadUpdate, _apply_bd_update


def _recorder(monkeypatch):
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(list(args))
        return subprocess.CompletedProcess(args, 0, stdout="{}", stderr="")

    monkeypatch.setattr(beads.subprocess, "run", fake_run)
    return calls


def test_force_true_appends_the_flag(monkeypatch, tmp_path):
    calls = _recorder(monkeypatch)
    _apply_bd_update(tmp_path, BeadUpdate("mc-1", status="closed", force=True), 5)
    assert calls, "bd update was never invoked"
    assert "--force" in calls[0]


def test_force_false_omits_the_flag(monkeypatch, tmp_path):
    calls = _recorder(monkeypatch)
    _apply_bd_update(tmp_path, BeadUpdate("mc-1", status="closed", force=False), 5)
    assert calls
    assert "--force" not in calls[0]


def test_to_dict_carries_force_only_when_true():
    assert "force" not in BeadUpdate("mc-1", status="closed").to_dict()
    assert BeadUpdate("mc-1", status="closed", force=True).to_dict()["force"] is True
