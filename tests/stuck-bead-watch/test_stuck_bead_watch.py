"""Unit tests for the stuck-bead-watch detector's pure logic (no bd/gc calls)."""
import sys
import json
import tempfile
import tomllib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import importlib.util

_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "assets" / "scripts" / "stuck-bead-watch.py"
_spec = importlib.util.spec_from_file_location("stuck_bead_watch", _SCRIPT_PATH)
sbw = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sbw)

_FILTER_SCRIPT_PATH = Path(__file__).resolve().parents[2] / "assets" / "scripts" / "lost-bead-filter.py"
_filter_spec = importlib.util.spec_from_file_location("lost_bead_filter", _FILTER_SCRIPT_PATH)
lbf = importlib.util.module_from_spec(_filter_spec)
_filter_spec.loader.exec_module(lbf)


def _bead(bead_id, priority=2, assignee=None, routed_to="mathcity.brief-operator",
          status="open", created_at="2026-07-28T00:00:00Z", metadata=None):
    if metadata is not None:
        meta = dict(metadata)
    else:
        meta = {"gc.routed_to": routed_to} if routed_to else {}
    return {
        "id": bead_id,
        "status": status,
        "priority": priority,
        "assignee": assignee,
        "created_at": created_at,
        "metadata": meta,
    }


def _session(session_name, state="active"):
    return {"session_name": session_name, "state": state}


def test_never_claimed_bead_is_stuck_candidate():
    now = datetime(2026, 7, 28, 0, 10, 0, tzinfo=timezone.utc)
    beads = [_bead("gt-a1", assignee=None)]
    sessions = []
    candidates = sbw.find_stuck_candidates(beads, sessions, now, min_age_seconds=180)
    assert [c["id"] for c in candidates] == ["gt-a1"]


def test_claimed_by_live_session_is_not_stuck():
    now = datetime(2026, 7, 28, 0, 10, 0, tzinfo=timezone.utc)
    beads = [_bead("gt-a2", assignee="mathcity__brief-operator-gt-x5twj")]
    sessions = [_session("mathcity__brief-operator-gt-x5twj")]
    candidates = sbw.find_stuck_candidates(beads, sessions, now, min_age_seconds=180)
    assert candidates == []


def test_claimed_by_dead_session_is_stuck_candidate():
    now = datetime(2026, 7, 28, 0, 10, 0, tzinfo=timezone.utc)
    beads = [_bead("gt-a3", assignee="mathcity__brief-operator-gt-x5twj")]
    sessions = [_session("mathcity__brief-operator-gt-OTHER")]
    candidates = sbw.find_stuck_candidates(beads, sessions, now, min_age_seconds=180)
    assert [c["id"] for c in candidates] == ["gt-a3"]


def test_too_young_bead_is_not_yet_a_candidate():
    now = datetime(2026, 7, 28, 0, 0, 30, tzinfo=timezone.utc)
    beads = [_bead("gt-a4", assignee=None, created_at="2026-07-28T00:00:00Z")]
    candidates = sbw.find_stuck_candidates(beads, [], now, min_age_seconds=180)
    assert candidates == []


def test_bead_without_routed_to_is_ignored():
    now = datetime(2026, 7, 28, 0, 10, 0, tzinfo=timezone.utc)
    beads = [_bead("gt-a5", assignee=None, routed_to=None)]
    candidates = sbw.find_stuck_candidates(beads, [], now, min_age_seconds=180)
    assert candidates == []


def test_in_progress_bead_is_eligible():
    now = datetime(2026, 7, 28, 0, 10, 0, tzinfo=timezone.utc)
    beads = [_bead("gt-a6", assignee=None, status="in_progress")]
    candidates = sbw.find_stuck_candidates(beads, [], now, min_age_seconds=180)
    assert [c["id"] for c in candidates] == ["gt-a6"]


def test_closed_bead_is_ignored():
    now = datetime(2026, 7, 28, 0, 10, 0, tzinfo=timezone.utc)
    beads = [_bead("gt-a7", assignee=None, status="closed")]
    candidates = sbw.find_stuck_candidates(beads, [], now, min_age_seconds=180)
    assert candidates == []


def test_grace_window_seconds_maps_priority():
    windows = {0: 300, 1: 600, 2: 1200, 3: 2700, 4: 2700}
    assert sbw.grace_window_seconds(0, windows) == 300
    assert sbw.grace_window_seconds(2, windows) == 1200
    assert sbw.grace_window_seconds(4, windows) == 2700


def test_grace_window_seconds_unknown_priority_falls_back_to_p4():
    windows = {0: 300, 1: 600, 2: 1200, 3: 2700, 4: 2700}
    assert sbw.grace_window_seconds(9, windows) == 2700


def test_cache_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp)
        assert sbw.read_cache_entry(cache_dir, "gt-b1") is None
        sbw.write_cache_entry(cache_dir, "gt-b1", "2026-07-28T00:00:00Z")
        entry = sbw.read_cache_entry(cache_dir, "gt-b1")
        assert entry["first_seen_stuck"] == "2026-07-28T00:00:00Z"
        sbw.clear_cache_entry(cache_dir, "gt-b1")
        assert sbw.read_cache_entry(cache_dir, "gt-b1") is None


def test_classify_and_escalate_writes_valid_schema_toml():
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"
        classification_root = Path(tmp) / "classifications"
        bead = _bead("gt-c1", assignee=None)
        create_calls = []
        relate_calls = []

        def fake_bd_create_event(title, description):
            create_calls.append((title, description))
            return "gt-event-1"

        def fake_bd_dep_relate(a, b):
            relate_calls.append((a, b))

        event_id = sbw.classify_and_escalate(
            bead, cache_dir, classification_root, "2026-07-28T01:00:00Z",
            bd_create_event=fake_bd_create_event,
            bd_dep_relate=fake_bd_dep_relate,
        )
        assert event_id == "gt-event-1"
        toml_path = classification_root / "gt-c1.toml"
        assert toml_path.exists()
        content = toml_path.read_text()
        assert 'schema = "lost-bead-classification.v1"' in content
        assert 'bead_id = "gt-c1"' in content
        assert len(create_calls) == 1
        # P1.19 — append a new LINKED bead: the event bead must be bd-dep-related
        # back to the source bead it classifies, not just referenced in prose.
        assert relate_calls == [("gt-event-1", "gt-c1")]


def test_classify_and_escalate_includes_routed_step_bead_reason_dead_assignee():
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"
        classification_root = Path(tmp) / "classifications"
        bead = _bead("gt-c2", assignee="mathcity__brief-operator-gt-dead")

        event_id = sbw.classify_and_escalate(
            bead, cache_dir, classification_root, "2026-07-28T01:00:00Z",
            bd_create_event=lambda t, d: "gt-event-2",
            bd_dep_relate=lambda a, b: None,
        )
        assert event_id == "gt-event-2"
        content = (classification_root / "gt-c2.toml").read_text()
        assert "mathcity__brief-operator-gt-dead" in content


# --- CT1.8 coverage: gc.routed_to / gc.run_target / gc.execution_routed_to ---

def test_bead_with_only_run_target_is_a_candidate():
    now = datetime(2026, 7, 28, 0, 10, 0, tzinfo=timezone.utc)
    beads = [_bead("gt-d1", assignee=None, routed_to=None,
                    metadata={"gc.run_target": "mathcity.brief-operator"})]
    candidates = sbw.find_stuck_candidates(beads, [], now, min_age_seconds=180)
    assert [c["id"] for c in candidates] == ["gt-d1"]


def test_bead_with_only_execution_routed_to_is_a_candidate():
    now = datetime(2026, 7, 28, 0, 10, 0, tzinfo=timezone.utc)
    beads = [_bead("gt-d2", assignee=None, routed_to=None,
                    metadata={"gc.execution_routed_to": "mathcity.brief-operator"})]
    candidates = sbw.find_stuck_candidates(beads, [], now, min_age_seconds=180)
    assert [c["id"] for c in candidates] == ["gt-d2"]


def test_bead_with_none_of_the_three_routed_keys_is_ignored():
    now = datetime(2026, 7, 28, 0, 10, 0, tzinfo=timezone.utc)
    beads = [_bead("gt-d3", assignee=None, routed_to=None,
                    metadata={"gc.formula_name": "brief-shuffle"})]
    candidates = sbw.find_stuck_candidates(beads, [], now, min_age_seconds=180)
    assert candidates == []


# --- schema-valid suspected_source (finding #1) ---

def test_classify_and_escalate_uses_schema_valid_suspected_source():
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"
        classification_root = Path(tmp) / "classifications"
        bead = _bead("gt-e1", assignee=None, routed_to="mathcity.brief-operator")

        sbw.classify_and_escalate(
            bead, cache_dir, classification_root, "2026-07-28T01:00:00Z",
            bd_create_event=lambda t, d: "gt-event-e1",
            bd_dep_relate=lambda a, b: None,
        )
        content = (classification_root / "gt-e1.toml").read_text()
        parsed = tomllib.loads(content)
        # root_cause.suspected_source must be one of lost-bead-schema.toml's
        # dispatch_sources enum -- "mathcity.brief-operator" is NOT.
        assert parsed["root_cause"]["suspected_source"] == "formula"
        # the actual worker/pool target is preserved, just outside the
        # schema-validated root_cause block.
        assert parsed["stuck_bead_watch"]["routed_target"] == "mathcity.brief-operator"
        assert parsed["stuck_bead_watch"]["routed_metadata_key"] == "gc.routed_to"


def test_classify_and_escalate_records_which_routed_key_matched_run_target():
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"
        classification_root = Path(tmp) / "classifications"
        bead = _bead("gt-e2", assignee=None, routed_to=None,
                      metadata={"gc.run_target": "mathcity.brief-operator"})

        sbw.classify_and_escalate(
            bead, cache_dir, classification_root, "2026-07-28T01:00:00Z",
            bd_create_event=lambda t, d: "gt-event-e2",
            bd_dep_relate=lambda a, b: None,
        )
        parsed = tomllib.loads((classification_root / "gt-e2.toml").read_text())
        assert parsed["stuck_bead_watch"]["routed_metadata_key"] == "gc.run_target"


# --- idempotency / dedupe (finding #3) ---

def test_classify_and_escalate_is_idempotent_after_successful_link():
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"
        classification_root = Path(tmp) / "classifications"
        bead = _bead("gt-f1", assignee=None)
        create_calls = []
        relate_calls = []

        def fake_create(t, d):
            create_calls.append((t, d))
            return f"gt-event-{len(create_calls)}"

        def fake_relate(a, b):
            relate_calls.append((a, b))

        first_id = sbw.classify_and_escalate(
            bead, cache_dir, classification_root, "2026-07-28T01:00:00Z",
            bd_create_event=fake_create, bd_dep_relate=fake_relate,
        )
        # bead re-enters the waiting room on a later tick (still stuck,
        # same underlying condition) -- must NOT create a second event.
        second_id = sbw.classify_and_escalate(
            bead, cache_dir, classification_root, "2026-07-28T02:00:00Z",
            bd_create_event=fake_create, bd_dep_relate=fake_relate,
        )
        assert first_id == second_id
        assert len(create_calls) == 1
        assert len(relate_calls) == 1


def test_classify_and_escalate_does_not_duplicate_event_when_relate_fails_then_recovers():
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"
        classification_root = Path(tmp) / "classifications"
        bead = _bead("gt-f2", assignee=None)
        create_calls = []
        relate_attempts = {"count": 0}

        def fake_create(t, d):
            create_calls.append((t, d))
            return "gt-event-f2"

        def flaky_relate(a, b):
            relate_attempts["count"] += 1
            if relate_attempts["count"] <= 2:
                raise RuntimeError("bd dep relate: transient failure")
            # succeeds on the 3rd attempt (within classify_and_escalate's
            # own retry loop) -- no duplicate event should have been created.

        event_id = sbw.classify_and_escalate(
            bead, cache_dir, classification_root, "2026-07-28T01:00:00Z",
            bd_create_event=fake_create, bd_dep_relate=flaky_relate,
        )
        assert event_id == "gt-event-f2"
        assert len(create_calls) == 1  # never duplicated despite relate flakiness


def test_classify_and_escalate_retries_only_the_relate_on_next_run_after_total_relate_failure():
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"
        classification_root = Path(tmp) / "classifications"
        bead = _bead("gt-f3", assignee=None)
        create_calls = []

        def fake_create(t, d):
            create_calls.append((t, d))
            return "gt-event-f3"

        def always_fails(a, b):
            raise RuntimeError("bd dep relate: still down")

        def always_succeeds(a, b):
            pass

        # First run: create succeeds, relate exhausts all retries and fails.
        event_id_1 = sbw.classify_and_escalate(
            bead, cache_dir, classification_root, "2026-07-28T01:00:00Z",
            bd_create_event=fake_create, bd_dep_relate=always_fails,
        )
        assert event_id_1 == "gt-event-f3"
        assert len(create_calls) == 1

        # Second run (relate is healthy again): must reuse the SAME event,
        # not create a new one -- only the relate is retried.
        event_id_2 = sbw.classify_and_escalate(
            bead, cache_dir, classification_root, "2026-07-28T02:00:00Z",
            bd_create_event=fake_create, bd_dep_relate=always_succeeds,
        )
        assert event_id_2 == "gt-event-f3"
        assert len(create_calls) == 1  # still just the one event ever created


# --- real integration with lost-bead-filter.py's validator (finding #4) ---
# This is the TDD anchor for finding #1: it must FAIL against the
# pre-fix code (Codex reproduced: "invalid root_cause.suspected_source
# mathcity.brief-operator") and PASS after the fix.

def test_watchdog_output_passes_the_real_lost_bead_filter_validator():
    with tempfile.TemporaryDirectory() as tmp:
        cache_dir = Path(tmp) / "cache"
        classification_root = Path(tmp) / "classifications"
        bead = _bead("gt-g1", assignee=None, routed_to="mathcity.brief-operator")

        sbw.classify_and_escalate(
            bead, cache_dir, classification_root, "2026-07-28T01:00:00Z",
            bd_create_event=lambda t, d: "gt-event-g1",
            bd_dep_relate=lambda a, b: None,
        )

        # Runs the REAL validator (lost-bead-filter.py's load_records ->
        # validate_lost_record), not a hand-written fixture.
        classifications, provenance = lbf.load_records(classification_root)
        assert len(classifications) == 1
        assert classifications[0]["bead_id"] == "gt-g1"


# --- P6.1 fail-loud on subprocess hang (Codex review, 2026-07-28 17:37) ---
# A hung `gc`/`bd` call must not freeze this 90s-cooldown order indefinitely
# -- it must fail loud with SystemExit(1) and an actionable message, never
# an unhandled TimeoutExpired traceback and never a silent/partial result.

# --- gsp-2bowrk: escalation must be gated on REAL idle age, not on the ---
# --- moment the detector first observed the bead. A bead already idle    ---
# --- longer than its priority grace window must escalate on the FIRST     ---
# --- detection pass -- not first-detection + a fresh grace window.        ---

def _run_main_with_beads(tmp_path, beads, sessions=None):
    """Drive main() end-to-end with the network/subprocess boundary stubbed
    out, returning the list of bead ids that got escalated this run."""
    import tempfile
    cache_dir = Path(tmp_path) / "cache"
    classification_root = Path(tmp_path) / "classifications"
    escalated_ids = []

    import unittest.mock as _mock
    patches = [
        _mock.patch.object(sbw, "_preflight", lambda: None),
        _mock.patch.object(sbw, "_gc_bd_list_routed", lambda: beads),
        _mock.patch.object(sbw, "_gc_session_list_active", lambda: (sessions or [])),
        _mock.patch.object(
            sbw, "classify_and_escalate",
            lambda bead, cd, cr, observed_at, **kw: (escalated_ids.append(bead["id"]) or f"evt-{bead['id']}"),
        ),
    ]
    for p in patches:
        p.start()
    try:
        sbw.main(["--cache-dir", str(cache_dir), "--classification-root", str(classification_root)])
    finally:
        for p in patches:
            p.stop()
    return escalated_ids


def _iso(dt):
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_old_strand_escalates_on_first_detection_pass():
    # A bead whose REAL idle age (updated_at 200 days ago) already exceeds
    # its p0 grace window (300s), first observed by the detector RIGHT NOW.
    # It must escalate on the very first pass -- the grace window measures
    # the bead's real idle time, not wall-clock since first observation.
    now = datetime.now(timezone.utc)
    old = _iso(now - timedelta(days=200))
    with __import__("tempfile").TemporaryDirectory() as tmp:
        bead = _bead("gt-old-strand", priority=0, assignee=None,
                     routed_to="mathcity.brief-operator",
                     created_at=old)
        bead["updated_at"] = old
        escalated = _run_main_with_beads(tmp, [bead])
    assert escalated == ["gt-old-strand"], (
        "a 200-day-idle p0 strand must escalate on first detection; "
        f"got escalated={escalated}"
    )


def test_fresh_strand_does_not_escalate_prematurely():
    # A genuinely fresh strand: real idle age (200s) is under its p0 grace
    # window (300s). It must NOT escalate on the first pass -- it enters the
    # waiting room and only escalates once its real idle age crosses 300s.
    now = datetime.now(timezone.utc)
    recent = _iso(now - timedelta(seconds=200))
    with __import__("tempfile").TemporaryDirectory() as tmp:
        bead = _bead("gt-fresh-strand", priority=0, assignee=None,
                     routed_to="mathcity.brief-operator",
                     created_at=recent)
        bead["updated_at"] = recent
        escalated = _run_main_with_beads(tmp, [bead])
    assert escalated == [], (
        "a 200s-idle p0 strand (under the 300s window) must not escalate "
        f"prematurely; got escalated={escalated}"
    )


def test_real_idle_age_seconds_uses_updated_at():
    now = datetime(2026, 8, 4, 0, 0, 0, tzinfo=timezone.utc)
    bead = {"id": "gt-x", "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-08-03T00:00:00Z"}
    # last activity was 1 day before `now` -> real idle age = 86400s,
    # NOT the ~7-month age since creation.
    assert sbw.real_idle_age_seconds(bead, now) == 86400.0


def test_gc_session_list_active_fails_loud_on_timeout(monkeypatch):
    import subprocess as _subprocess

    def _raise_timeout(cmd, **kwargs):
        raise _subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout"))

    monkeypatch.setattr(sbw.subprocess, "run", _raise_timeout)
    try:
        sbw._gc_session_list_active()
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert exc.code == 1


def test_gc_bd_list_routed_fails_loud_on_timeout(monkeypatch):
    import subprocess as _subprocess

    def _raise_timeout(cmd, **kwargs):
        raise _subprocess.TimeoutExpired(cmd=cmd, timeout=kwargs.get("timeout"))

    monkeypatch.setattr(sbw.subprocess, "run", _raise_timeout)
    try:
        sbw._gc_bd_list_routed()
        assert False, "expected SystemExit"
    except SystemExit as exc:
        assert exc.code == 1


def test_run_wrapper_passes_configured_timeout_to_subprocess(monkeypatch):
    seen = {}

    def _fake_run(cmd, **kwargs):
        seen["timeout"] = kwargs.get("timeout")
        return _subprocess_completed(cmd)

    def _subprocess_completed(cmd):
        import subprocess as _subprocess
        return _subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(sbw.subprocess, "run", _fake_run)
    sbw._run(["true"])
    assert seen["timeout"] == sbw.SUBPROCESS_TIMEOUT_SECONDS


# --- gt-jzb8n regression guard: classification_root must resolve to the ---
# --- default rollup input path lost-bead-classification-rollup.toml     ---
# --- reads from, both at the script's own argparse default and in the   ---
# --- order wrapper's exec command -- a live-run test against the real   ---
# --- gt-vxhen bead (2026-07-28, QUIMBY 33) proved write-path/event/link ---
# --- logic already correct; this guard exists so a future edit to      ---
# --- either default can't silently drift them apart again.             ---
_DEFAULT_CLASSIFICATION_ROOT = ".beads/lost-bead-classifications"


def test_argparse_default_classification_root_matches_rollup_formula_default():
    parser_defaults = {}
    import argparse as _argparse
    orig_init = _argparse.ArgumentParser.add_argument

    def _capture(self, *args, **kwargs):
        if args and args[0] == "--classification-root":
            parser_defaults["value"] = kwargs.get("default")
        return orig_init(self, *args, **kwargs)

    _argparse.ArgumentParser.add_argument = _capture
    try:
        sbw.main(["--help"])
    except SystemExit:
        pass
    finally:
        _argparse.ArgumentParser.add_argument = orig_init

    assert str(parser_defaults["value"]) == _DEFAULT_CLASSIFICATION_ROOT


def test_order_toml_exec_command_passes_matching_classification_root():
    order_path = Path(__file__).resolve().parents[2] / "orders" / "stuck-bead-watch.toml"
    exec_line = [
        line for line in order_path.read_text().splitlines() if line.strip().startswith("exec")
    ][0]
    assert f"--classification-root {_DEFAULT_CLASSIFICATION_ROOT}" in exec_line
