"""Behavior tests for the Mayor read surface (`mctl_core.mayor`).

Two properties are load-bearing here, and both are properties this repo has
been wrong about in production rather than hypotheticals:

1. **A probe that could not run must not render as a probe that found nothing.**
   `ProbeResult.ok is None` and `ok is False` are different answers, and
   `city_state()` must escalate the first to `unknown` rather than `down`.
   Issue #100 is the live instance: a timed-out `gc rig status` rendered a
   partial agent roster as the roster.

2. **The conservation check must be shown to DETECT, not merely to pass.**
   Every assertion below that reports "clean" is paired with a fixture that
   contains a known dangling root and must report it. A conservation check
   exercised only against a clean store has not been shown to detect anything
   -- which is the exact defect class the tracker calls
   "a check that could not have failed must not render as a check that passed".
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import mayor
from mctl_core.diagnostics import Severity


# --------------------------------------------------------------------------
# fixtures: one clean store, one with a known dangling root
# --------------------------------------------------------------------------

CLEAN_ROWS = [
    {"id": "mc-root1", "created_at": "2026-08-01T00:00:00Z", "metadata": {}},
    {
        "id": "mc-step1",
        "created_at": "2026-08-01T00:01:00Z",
        "metadata": {"gc.root_bead_id": "mc-root1", "gc.root_store_ref": "city:gt"},
    },
    {
        "id": "mc-step2",
        "created_at": "2026-08-01T00:02:00Z",
        "metadata": {"gc.root_bead_id": "mc-root1", "gc.root_store_ref": "city:gt"},
    },
]

# mc-gone is referenced by two live members and does NOT appear as an id.
DANGLING_ROWS = CLEAN_ROWS + [
    {
        "id": "mc-orphan1",
        "created_at": "2026-07-15T12:00:00Z",
        "metadata": {"gc.root_bead_id": "mc-gone", "gc.root_store_ref": "city:gt"},
    },
    {
        "id": "mc-orphan2",
        "created_at": "2026-07-23T12:00:00Z",
        "metadata": {"gc.root_bead_id": "mc-gone", "gc.root_store_ref": "city:gt"},
    },
]


def test_clean_store_reports_clean() -> None:
    report = mayor.conservation_from_rows(CLEAN_ROWS)
    assert report.clean is True
    assert report.roots_dangling == 0
    assert report.orphaned_members == 0
    assert report.molecules == 1


def test_dangling_root_is_detected() -> None:
    """The positive control. If this passes while the clean case also passes,
    the check discriminates; if only the clean case passed, it proves nothing."""
    report = mayor.conservation_from_rows(DANGLING_ROWS)
    assert report.clean is False
    assert report.roots_dangling == 1
    assert report.dangling_root_ids == ("mc-gone",)
    assert report.orphaned_members == 2
    assert report.roots_resolving == 1
    assert report.molecules == 2


def test_dangling_root_raises_an_error_diagnostic() -> None:
    report = mayor.conservation_from_rows(DANGLING_ROWS)
    codes = {d.code for d in report.diagnostics}
    assert "MAYOR_CONSERVATION_DANGLING_ROOT" in codes
    diagnostic = next(d for d in report.diagnostics if d.code == "MAYOR_CONSERVATION_DANGLING_ROOT")
    assert diagnostic.severity is Severity.ERROR
    # The do-not-prune warning is the operationally load-bearing half: the
    # pointer is the only surviving evidence the workflow existed.
    assert "DO NOT prune" in (diagnostic.hint or "")


def test_clean_store_raises_no_dangling_diagnostic() -> None:
    report = mayor.conservation_from_rows(CLEAN_ROWS)
    assert [d for d in report.diagnostics if d.code == "MAYOR_CONSERVATION_DANGLING_ROOT"] == []


def test_window_bounds_the_orphans_not_the_whole_store() -> None:
    """Cluster-vs-spread is the question idleness-based detection cannot ask."""
    report = mayor.conservation_from_rows(DANGLING_ROWS)
    assert report.window_earliest == "2026-07-15T12:00:00Z"
    assert report.window_latest == "2026-07-23T12:00:00Z"
    # The clean members are August; they must not widen the window.
    assert "2026-08" not in (report.window_earliest or "")


def test_store_refs_are_counted_for_dangling_members_only() -> None:
    report = mayor.conservation_from_rows(DANGLING_ROWS)
    assert report.store_refs == {"city:gt": 2}


def test_metadata_accepts_a_json_string() -> None:
    """bd returns metadata as a mapping or a JSON string depending on version.
    A parser that handled only one shape would silently report every store
    clean -- no members found means no dangling roots found."""
    rows = [
        {"id": "mc-a", "metadata": '{"gc.root_bead_id": "mc-missing"}'},
    ]
    report = mayor.conservation_from_rows(rows)
    assert report.roots_dangling == 1
    assert report.orphaned_members == 1


def test_unparseable_metadata_does_not_crash_or_fabricate() -> None:
    rows = [{"id": "mc-a", "metadata": "not json at all"}]
    report = mayor.conservation_from_rows(rows)
    assert report.molecules == 0
    assert report.clean is True


# --------------------------------------------------------------------------
# probe honesty
# --------------------------------------------------------------------------


def test_probe_that_did_not_run_is_not_a_negative_answer() -> None:
    incomplete = mayor.ProbeResult("x", None, "probe exceeded 10s")
    looked_and_found_nothing = mayor.ProbeResult("x", False, "no tmux server running", value=0)
    assert incomplete.looked is False
    assert looked_and_found_nothing.looked is True
    assert incomplete.ok is not looked_and_found_nothing.ok


def test_city_state_is_unknown_when_a_load_bearing_probe_did_not_complete(monkeypatch) -> None:
    """The #100 property: a probe that timed out must not render as 'down'."""
    monkeypatch.setattr(mayor, "probe_tmux_panes", lambda: mayor.ProbeResult("tmux_panes", None, "probe exceeded 10s"))
    monkeypatch.setattr(mayor, "probe_supervisor", lambda _root=None: mayor.ProbeResult("supervisor", True, "running"))
    monkeypatch.setattr(mayor, "probe_rigs", lambda _root=None: (mayor.ProbeResult("rigs", True, "2 active, 0 suspended"), ("a", "b"), ()))
    state = mayor.city_state()
    assert state.state == "unknown"
    assert state.state != "down"
    assert "MAYOR_CITY_STATE_UNKNOWN" in {d.code for d in state.diagnostics}


def test_city_state_down_names_the_fleet_host_wedge(monkeypatch) -> None:
    """Supervisor alive + no tmux server is the S8 wedge and must say so."""
    monkeypatch.setattr(mayor, "probe_tmux_panes", lambda: mayor.ProbeResult("tmux_panes", False, "no tmux server running", value=0))
    monkeypatch.setattr(mayor, "probe_supervisor", lambda _root=None: mayor.ProbeResult("supervisor", True, "running"))
    monkeypatch.setattr(mayor, "probe_rigs", lambda _root=None: (mayor.ProbeResult("rigs", True, "2 active, 0 suspended"), ("a", "b"), ()))
    state = mayor.city_state()
    assert state.state == "down"
    codes = {d.code for d in state.diagnostics}
    assert "MAYOR_FLEET_HOST_ABSENT" in codes
    wedge = next(d for d in state.diagnostics if d.code == "MAYOR_FLEET_HOST_ABSENT")
    assert wedge.suggested_next_command == "gc restart"


def test_city_state_up_warns_about_suspended_rigs(monkeypatch) -> None:
    """A suspended rig's agents are skipped by the reconciler, so ready work in
    it is never dispatched. QUIMBY 44 found all sixteen suspended."""
    monkeypatch.setattr(mayor, "probe_tmux_panes", lambda: mayor.ProbeResult("tmux_panes", True, "16 pane(s)", value=16))
    monkeypatch.setattr(mayor, "probe_supervisor", lambda _root=None: mayor.ProbeResult("supervisor", True, "running"))
    monkeypatch.setattr(mayor, "probe_rigs", lambda _root=None: (mayor.ProbeResult("rigs", True, "1 active, 3 suspended"), ("a",), ("x", "y", "z")))
    state = mayor.city_state()
    assert state.state == "up"
    assert "MAYOR_RIGS_SUSPENDED" in {d.code for d in state.diagnostics}


def test_city_state_serialises_every_probe(monkeypatch) -> None:
    """The consumer must be able to see WHICH instrument said what, rather than
    a single collapsed verdict -- three instruments gave three answers in S44."""
    monkeypatch.setattr(mayor, "probe_tmux_panes", lambda: mayor.ProbeResult("tmux_panes", False, "no tmux server running", value=0))
    monkeypatch.setattr(mayor, "probe_supervisor", lambda _root=None: mayor.ProbeResult("supervisor", True, "running"))
    monkeypatch.setattr(mayor, "probe_rigs", lambda _root=None: (mayor.ProbeResult("rigs", None, "gc is not installed"), (), ()))
    payload = mayor.city_state().to_dict()
    assert {p["name"] for p in payload["probes"]} == {"tmux_panes", "supervisor", "rigs"}
    by_name = {p["name"]: p for p in payload["probes"]}
    assert by_name["rigs"]["ok"] is None
    assert by_name["tmux_panes"]["ok"] is False


# --------------------------------------------------------------------------
# unreadable != clean  (regression: caught by a flaky end-to-end control)
# --------------------------------------------------------------------------


def test_unreadable_store_is_not_clean() -> None:
    """The bug this pins was live in this module's own bring-up.

    `clean` was `roots_dangling == 0`, so a report built from a FAILED store
    read -- zero of everything -- announced `clean=True`. The end-to-end
    positive control skipped intermittently because of it: a conservation
    check giving a clean bill of health to a store it never read.
    """
    unreadable = mayor.ConservationReport(
        molecules=0,
        roots_resolving=0,
        roots_dangling=0,
        orphaned_members=0,
        dangling_root_ids=(),
        window_earliest=None,
        window_latest=None,
        store_refs={},
        readable=False,
    )
    assert unreadable.clean is None
    assert unreadable.clean is not True
    assert unreadable.to_dict()["readable"] is False


def test_readable_empty_store_is_genuinely_clean() -> None:
    """The discriminating case: an empty store that WAS read is clean."""
    empty = mayor.conservation_from_rows([])
    assert empty.readable is True
    assert empty.clean is True


def test_clean_and_unreadable_are_distinguishable_in_the_payload() -> None:
    empty = mayor.conservation_from_rows([]).to_dict()
    unreadable = mayor.ConservationReport(
        molecules=0, roots_resolving=0, roots_dangling=0, orphaned_members=0,
        dangling_root_ids=(), window_earliest=None, window_latest=None,
        store_refs={}, readable=False,
    ).to_dict()
    assert empty["clean"] != unreadable["clean"]
