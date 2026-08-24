"""`worktrees_status` (#120): worktree inventory, keyed by path, with the
honesty gaps the brief calls out -- `is_orphan` undeterminable, `is_registered`
always True by construction, `created_by`/`step`/`molecule` unrecorded.

Modeled on `test_queue_status.py` / `test_costs_summary.py`: an injected
reader, never a subprocess, so these tests exercise the pure shaper only.
`mctl_core.worktrees.city_reader` (the subprocess side) is exercised live by
the dashboard/harness, not here.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.worktrees import UNRECORDED, worktrees_status  # noqa: E402


def _reader(rigs, worktree_rows_by_rig, *, fail_rigs=()):
    def read(op, *args):
        if op == "rigs":
            return rigs
        if op == "worktree_rows":
            _name, root = args
            if root in fail_rigs:
                raise RuntimeError(f"git worktree list unavailable: {root}")
            return worktree_rows_by_rig.get(root, [])
        raise KeyError(op)

    return read


def _raw_row(path, branch="main", **overrides):
    row = {
        "path": path,
        "branch": branch,
        "head": "deadbeef",
        "bare": False,
        "detached": False,
        "locked_reason": None,
        "prunable_reason": None,
        "committed_at": "2026-08-01T00:00:00Z",
        "merged": False,
        "commits_ahead": 3,
        "size_bytes": 1024,
    }
    row.update(overrides)
    return row


def test_the_whole_roster_unreachable_reports_null_never_empty():
    def read(op, *args):
        raise RuntimeError("gc rig list unavailable")

    out = worktrees_status(read)

    assert out["state"] == "unreachable"
    assert out["total"] is None
    assert out["worktrees"] is None
    assert out["orphans"] is None
    codes = {d["code"] for d in out["diagnostics"]}
    assert "MWKT_WORKTREES_UNREACHABLE" in codes


def test_every_rig_failing_is_also_unreachable_not_an_empty_list():
    rigs = [{"name": "hecke", "root": "/rigs/hecke"}, {"name": "mathcity", "root": "/rigs/mathcity"}]
    read = _reader(rigs, {}, fail_rigs={"/rigs/hecke", "/rigs/mathcity"})

    out = worktrees_status(read)

    assert out["state"] == "unreachable"
    assert out["total"] is None
    assert out["worktrees"] is None
    codes = {d["code"] for d in out["diagnostics"]}
    assert "MWKT_RIG_UNREACHABLE" in codes


def test_one_rig_failing_degrades_without_discarding_the_others_rows():
    rigs = [{"name": "hecke", "root": "/rigs/hecke"}, {"name": "mathcity", "root": "/rigs/mathcity"}]
    read = _reader(
        rigs,
        {"/rigs/mathcity": [_raw_row("/rigs/mathcity")]},
        fail_rigs={"/rigs/hecke"},
    )

    out = worktrees_status(read)

    assert out["state"] == "degraded"
    assert out["total"] == 1
    assert out["worktrees"][0]["path"] == "/rigs/mathcity"
    codes = {d["code"] for d in out["diagnostics"]}
    assert "MWKT_RIG_UNREACHABLE" in codes


def test_a_genuinely_empty_roster_reports_zero_not_unknown():
    read = _reader([], {})

    out = worktrees_status(read)

    assert out["state"] == "healthy"
    assert out["total"] == 0
    assert out["worktrees"] == []
    assert out["orphans"] is None, "orphans stays null even at zero rows -- see is_orphan gap"


def test_row_key_is_path_not_id_two_ids_can_repeat_under_different_parents():
    """Measured 2026-08-20 (#120 brief): two ids appear twice with different
    parents. A row list keyed by anything but path would collapse them."""
    rigs = [{"name": "hecke", "root": "/rigs/hecke"}, {"name": "mathcity", "root": "/rigs/mathcity"}]
    read = _reader(
        rigs,
        {
            "/rigs/hecke": [_raw_row("/parent-a/w156")],
            "/rigs/mathcity": [_raw_row("/parent-b/w156")],
        },
    )

    out = worktrees_status(read)

    paths = {row["path"] for row in out["worktrees"]}
    assert paths == {"/parent-a/w156", "/parent-b/w156"}
    assert out["total"] == 2


def test_is_orphan_and_is_registered_are_separate_flags_never_merged():
    rigs = [{"name": "mathcity", "root": "/rigs/mathcity"}]
    read = _reader(rigs, {"/rigs/mathcity": [_raw_row("/rigs/mathcity/w1")]})

    out = worktrees_status(read)

    row = out["worktrees"][0]
    assert "is_orphan" in row and "is_registered" in row
    # Distinct keys, distinct (and here, different) values -- never folded
    # into one boolean.
    assert row["is_registered"] is True
    assert row["is_orphan"] is None


def test_created_by_and_step_render_unrecorded_not_null_not_empty_string():
    rigs = [{"name": "mathcity", "root": "/rigs/mathcity"}]
    read = _reader(rigs, {"/rigs/mathcity": [_raw_row("/rigs/mathcity/w1")]})

    out = worktrees_status(read)

    row = out["worktrees"][0]
    assert row["created_by"] == UNRECORDED
    assert row["step"] == UNRECORDED
    assert row["molecule"] == UNRECORDED
    # The sentinel is a real string, not None and not "" -- both of which
    # would be indistinguishable from a genuine future value.
    assert row["created_by"] is not None
    assert row["created_by"] != ""
    codes = {d["code"] for d in out["diagnostics"]}
    assert "MWKT_CREATED_BY_UNRECORDED" in codes


def test_harvestable_reflects_gits_own_prunable_flag():
    rigs = [{"name": "mathcity", "root": "/rigs/mathcity"}]
    read = _reader(
        rigs,
        {
            "/rigs/mathcity": [
                _raw_row("/rigs/mathcity/gone", prunable_reason="gitdir file points to non-existent location"),
                _raw_row("/rigs/mathcity/present", prunable_reason=None),
            ]
        },
    )

    out = worktrees_status(read)

    by_path = {row["path"]: row for row in out["worktrees"]}
    assert by_path["/rigs/mathcity/gone"]["harvestable"] is True
    assert by_path["/rigs/mathcity/present"]["harvestable"] is False
    assert out["harvestable_count"] == 1


def test_size_unknown_row_reports_null_with_an_aggregate_diagnostic_not_zero():
    rigs = [{"name": "mathcity", "root": "/rigs/mathcity"}]
    read = _reader(
        rigs,
        {"/rigs/mathcity": [_raw_row("/rigs/mathcity/w1", size_bytes=None)]},
    )

    out = worktrees_status(read)

    assert out["worktrees"][0]["size_bytes"] is None
    codes = {d["code"] for d in out["diagnostics"]}
    assert "MWKT_SIZE_UNKNOWN" in codes


def test_merged_and_commits_pass_through_from_the_reader():
    rigs = [{"name": "mathcity", "root": "/rigs/mathcity"}]
    read = _reader(
        rigs,
        {
            "/rigs/mathcity": [
                _raw_row("/rigs/mathcity/main", branch="main", merged=True, commits_ahead=0),
                _raw_row("/rigs/mathcity/feat", branch="feat", merged=False, commits_ahead=5),
            ]
        },
    )

    out = worktrees_status(read)

    by_path = {row["path"]: row for row in out["worktrees"]}
    assert by_path["/rigs/mathcity/main"]["merged"] is True
    assert by_path["/rigs/mathcity/main"]["commits"] == 0
    assert by_path["/rigs/mathcity/feat"]["merged"] is False
    assert by_path["/rigs/mathcity/feat"]["commits"] == 5


def test_age_seconds_is_derived_from_the_commit_timestamp():
    rigs = [{"name": "mathcity", "root": "/rigs/mathcity"}]
    read = _reader(
        rigs,
        {"/rigs/mathcity": [_raw_row("/rigs/mathcity/w1", committed_at="2026-08-01T00:00:00Z")]},
    )
    now = datetime(2026, 8, 2, 0, 0, 0, tzinfo=timezone.utc)

    out = worktrees_status(read, now=now)

    assert out["worktrees"][0]["age_seconds"] == 86400.0


def test_url_is_a_file_uri_for_the_path():
    rigs = [{"name": "mathcity", "root": "/rigs/mathcity"}]
    read = _reader(rigs, {"/rigs/mathcity": [_raw_row("/rigs/mathcity/w1")]})

    out = worktrees_status(read)

    assert out["worktrees"][0]["url"] == "file:///rigs/mathcity/w1"
