"""Tests for the tail-end-detector pure core (ready-but-never-dispatched tail).

RED-first: the module under test does not exist yet.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / "assets" / "scripts"
MODULE_PATH = SCRIPTS / "tail-end-detector.py"
VALIDATOR = SCRIPTS / "lost-bead-filter.py"

spec = importlib.util.spec_from_file_location("tail_end_detector", MODULE_PATH)
ted = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ted)

NOW = datetime(2026, 8, 4, 12, 0, 0, tzinfo=timezone.utc)


def bead(bid, *, days_idle, title="do the thing", itype="task",
         created=None, updated=None, desc="", status="open",
         parent=None, deps=None):
    """Build a bead whose real idle age is `days_idle` days."""
    ts = (NOW - timedelta(days=days_idle)).strftime("%Y-%m-%dT%H:%M:%SZ")
    b = {
        "id": bid,
        "title": title,
        "description": desc,
        "issue_type": itype,
        "status": status,
        "priority": 2,
        "created_at": created or ts,
        "updated_at": updated or ts,
    }
    if parent is not None:
        b["parent"] = parent
    if deps is not None:
        b["dependencies"] = deps
    return b


def dep(child, parent_or_target, dep_type):
    """A dependency edge as bd emits it (issue_id -> depends_on_id)."""
    return {"issue_id": child, "depends_on_id": parent_or_target, "type": dep_type}


# ---- Fork 1: idle measure = max(created, updated, last_activity) ----

def test_real_idle_uses_the_most_recent_activity():
    b = {
        "id": "x-1",
        "created_at": "2026-06-01T00:00:00Z",   # very old
        "updated_at": "2026-08-03T12:00:00Z",   # 1 day before NOW
        "last_activity": "2026-08-02T12:00:00Z",
    }
    idle_days = ted.real_idle_seconds(b, NOW) / 86400
    assert 0.9 < idle_days < 1.1  # keyed off the newest ts, not created_at


def test_three_day_idle_bead_registers_on_first_scan():
    # No cache / first-observation state involved: a 4-day-idle bead is
    # actionable immediately.
    b = bead("x-2", days_idle=4)
    out = ted.find_actionable_tail(
        [b], ready_ids={"x-2"}, routed_ids=set(), now=NOW,
        min_idle_seconds=3 * 86400,
    )
    assert [x["id"] for x in out] == ["x-2"]


def test_fresh_bead_under_three_days_is_excluded():
    b = bead("x-3", days_idle=2)
    out = ted.find_actionable_tail(
        [b], ready_ids={"x-3"}, routed_ids=set(), now=NOW,
        min_idle_seconds=3 * 86400,
    )
    assert out == []


# ---- Filter: work-type / scaffolding / gated / routed / blocked ----

def test_blocked_bead_not_in_ready_is_excluded():
    b = bead("x-4", days_idle=10)
    out = ted.find_actionable_tail(
        [b], ready_ids=set(), routed_ids=set(), now=NOW,
        min_idle_seconds=3 * 86400,
    )
    assert out == []


def test_routed_bead_is_excluded_dedup_with_stuck_bead_watch():
    b = bead("x-5", days_idle=10)
    out = ted.find_actionable_tail(
        [b], ready_ids={"x-5"}, routed_ids={"x-5"}, now=NOW,
        min_idle_seconds=3 * 86400,
    )
    assert out == []


@pytest.mark.parametrize("title", [
    "Refinery patrol sweep", "Deacon witness", "Polecat drain",
])
def test_scaffolding_titles_excluded(title):
    b = bead("x-6", days_idle=10, title=title)
    out = ted.find_actionable_tail(
        [b], ready_ids={"x-6"}, routed_ids=set(), now=NOW,
        min_idle_seconds=3 * 86400,
    )
    assert out == []


def test_rig_id_and_bare_rig_title_excluded():
    b1 = bead("he-rig-abc", days_idle=10)
    b2 = bead("x-7", days_idle=10, title="hecke")
    out = ted.find_actionable_tail(
        [b1, b2], ready_ids={"he-rig-abc", "x-7"}, routed_ids=set(),
        now=NOW, min_idle_seconds=3 * 86400,
    )
    assert out == []


def test_gated_titles_excluded():
    b = bead("x-8", days_idle=10, title="do X (human-gated)")
    out = ted.find_actionable_tail(
        [b], ready_ids={"x-8"}, routed_ids=set(), now=NOW,
        min_idle_seconds=3 * 86400,
    )
    assert out == []


def test_non_work_issue_types_excluded():
    for itype in ("spec", "convoy", "epic", "event", "decision"):
        b = bead("x-9", days_idle=10, itype=itype)
        out = ted.find_actionable_tail(
            [b], ready_ids={"x-9"}, routed_ids=set(), now=NOW,
            min_idle_seconds=3 * 86400,
        )
        assert out == [], itype


def test_actionable_tail_sorted_oldest_first():
    beads = [bead("young", days_idle=4), bead("old", days_idle=40),
             bead("mid", days_idle=10)]
    out = ted.find_actionable_tail(
        beads, ready_ids={"young", "old", "mid"}, routed_ids=set(),
        now=NOW, min_idle_seconds=3 * 86400,
    )
    assert [x["id"] for x in out] == ["old", "mid", "young"]


# ---- Fork 3 (real supersession detector, gsp-beo9sy) ----
#
# Age NO LONGER decides supersession. A never-dispatched idle bead is
# "superseded" only when a REAL signal fires:
#   1. parent-epic-closed          (parent field / parent-child dep -> closed)
#   2. subsumed-by-closed-ref      (related/tracks/... edge -> closed bead)
#   3. duplicate-of-closed-or-newer(title/desc token similarity, guarded)
# Everything else falls through to resling ("genuinely wanted, just old").

EMPTY_INDEX = None  # built per-test via ted.build_dedup_index([...])


# -- normalize_tokens / jaccard (pure helpers) --

def test_normalize_tokens_lowercases_strips_punct_and_stopwords():
    toks = ted.normalize_tokens("Implement the Hecke operator: T_p decomposition!")
    assert "hecke" in toks and "operator" in toks and "decomposition" in toks
    # stopwords + punctuation dropped
    assert "the" not in toks and ":" not in toks


def test_jaccard_identical_and_disjoint():
    assert ted.jaccard(frozenset("ab"), frozenset("ab")) == 1.0
    assert ted.jaccard(frozenset("ab"), frozenset("cd")) == 0.0
    assert ted.jaccard(frozenset(), frozenset()) == 0.0


# -- parent_of (field + dep edge) --

def test_parent_of_reads_parent_field():
    assert ted.parent_of(bead("c-1", days_idle=5, parent="ep-1")) == "ep-1"


def test_parent_of_reads_parent_child_dep_edge():
    b = bead("c-2", days_idle=5, deps=[dep("c-2", "ep-2", "parent-child")])
    assert ted.parent_of(b) == "ep-2"


def test_parent_of_none_when_no_parent():
    assert ted.parent_of(bead("c-3", days_idle=5)) is None


# -- Signal 1: parent-epic-closed --

def test_superseded_when_parent_epic_closed():
    closed_parent = bead("ep-c", days_idle=10, status="closed")
    child = bead("k-1", days_idle=40, parent="ep-c")
    idx = ted.build_dedup_index([closed_parent, child])
    bucket, ev = ted.classify_bead(child, idx)
    assert bucket == "superseded"
    assert ev["signal"] == "parent_epic_closed"
    assert ev["matched_bead"] == "ep-c"


def test_resling_when_parent_still_open():
    open_parent = bead("ep-o", days_idle=10, status="open")
    child = bead("k-2", days_idle=40, parent="ep-o")
    idx = ted.build_dedup_index([open_parent, child])
    assert ted.classify_bead(child, idx)[0] == "resling"


# -- Signal 2: subsumed-by-closed relational ref --

@pytest.mark.parametrize("edge", ["related", "relates-to", "tracks", "discovered-from"])
def test_superseded_when_relational_edge_targets_closed_bead(edge):
    done = bead("done-1", days_idle=10, status="closed")
    b = bead("k-3", days_idle=40, deps=[dep("k-3", "done-1", edge)])
    idx = ted.build_dedup_index([done, b])
    bucket, ev = ted.classify_bead(b, idx)
    assert bucket == "superseded"
    assert ev["signal"] == "subsumed_by_closed_ref"
    assert ev["matched_bead"] == "done-1"


def test_resling_when_relational_edge_targets_open_bead():
    other = bead("open-1", days_idle=10, status="open")
    b = bead("k-4", days_idle=40, deps=[dep("k-4", "open-1", "related")])
    idx = ted.build_dedup_index([other, b])
    assert ted.classify_bead(b, idx)[0] == "resling"


def test_blocks_dependency_on_closed_bead_is_not_supersession():
    # A satisfied *blocker* just unblocks the bead; it does NOT mean the
    # bead's own work is done. Must resling, not close.
    blocker = bead("blk-1", days_idle=10, status="closed")
    b = bead("k-5", days_idle=40, deps=[dep("k-5", "blk-1", "blocks")])
    idx = ted.build_dedup_index([blocker, b])
    assert ted.classify_bead(b, idx)[0] == "resling"


# -- Signal 3: title/description similarity (duplicate) --

DUP_TITLE = "compute newform coefficients for level fifty weight two"


def test_superseded_when_near_duplicate_of_closed_bead():
    closed = bead("dup-c", days_idle=10, status="closed", title=DUP_TITLE)
    # near-duplicate: one extra word, same core tokens
    b = bead("k-6", days_idle=40,
             title="compute newform coefficients for level fifty weight two now")
    idx = ted.build_dedup_index([closed, b])
    bucket, ev = ted.classify_bead(b, idx)
    assert bucket == "superseded"
    assert ev["signal"] == "duplicate_of_closed_or_newer"
    assert ev["matched_bead"] == "dup-c"


def test_superseded_when_duplicate_of_strictly_newer_open_bead():
    older = bead("k-7", days_idle=40, title=DUP_TITLE)          # candidate
    newer = bead("dup-n", days_idle=5, title=DUP_TITLE)         # newer open dup
    idx = ted.build_dedup_index([older, newer])
    bucket, ev = ted.classify_bead(older, idx)
    assert bucket == "superseded"
    assert ev["matched_bead"] == "dup-n"


def test_resling_when_only_match_is_an_older_open_bead():
    # An OLDER open twin must not supersede a newer candidate (only closed
    # or strictly-newer beads count as superseding duplicates).
    older_open = bead("older", days_idle=90, title=DUP_TITLE)
    candidate = bead("k-8", days_idle=40, title=DUP_TITLE)
    idx = ted.build_dedup_index([older_open, candidate])
    assert ted.classify_bead(candidate, idx)[0] == "resling"


def test_resling_when_similarity_below_threshold():
    closed = bead("far-c", days_idle=10, status="closed",
                  title="compute newform coefficients for level fifty weight two")
    b = bead("k-9", days_idle=40,
             title="prove the main theorem about elliptic curve ranks")
    idx = ted.build_dedup_index([closed, b])
    assert ted.classify_bead(b, idx)[0] == "resling"


def test_generic_short_title_does_not_trigger_duplicate_close():
    # Repeated generic titles (e.g. "Finalize build-basic") must NOT
    # auto-close: too few meaningful tokens to be a safe duplicate signal.
    closed = bead("g-c", days_idle=10, status="closed", title="Finalize build-basic")
    b = bead("k-10", days_idle=40, title="Finalize build-basic")
    idx = ted.build_dedup_index([closed, b])
    assert ted.classify_bead(b, idx)[0] == "resling"


# -- Fallthrough: age alone never supersedes (the core regression fix) --

def test_old_bead_with_no_signal_reslings_not_supersedes():
    b = bead("k-11", days_idle=365)   # ancient, but no supersession evidence
    idx = ted.build_dedup_index([b])
    assert ted.classify_bead(b, idx)[0] == "resling"


# -- select_batches over signal-based classification --

def test_select_batches_caps_and_prioritizes_oldest():
    # 5 superseded (parent-closed) + 5 resling (no signal); caps 2 and 3.
    closed_parent = bead("ep", days_idle=10, status="closed")
    sup = [bead(f"s{i}", days_idle=30 + i, parent="ep") for i in range(5)]
    res = [bead(f"r{i}", days_idle=4 + i) for i in range(5)]
    corpus = [closed_parent] + sup + res
    idx = ted.build_dedup_index(corpus)
    cands = ted.find_actionable_tail(
        sup + res, ready_ids={b["id"] for b in sup + res},
        routed_ids=set(), now=NOW, min_idle_seconds=3 * 86400,
    )
    superseded, resling = ted.select_batches(
        cands, NOW, idx, resling_cap=3, supersede_cap=2,
    )
    assert len(superseded) == 2 and len(resling) == 3
    # oldest-first within each bucket
    assert superseded[0]["id"] == "s4"
    assert resling[0]["id"] == "r4"
    # superseded beads carry their signal evidence for the downstream brief
    assert superseded[0]["_supersession"]["signal"] == "parent_epic_closed"


# ---- Fork 2: emitted record validates against the real pipeline schema ----

@pytest.mark.parametrize("kind", ["superseded", "resling"])
def test_rendered_record_passes_lost_bead_filter_validate(kind, tmp_path):
    b = bead("gsp-demo1", days_idle=40 if kind == "superseded" else 5)
    toml_text = ted.render_record(b, kind, NOW, observed_at="2026-08-04T12:00:00Z")
    (tmp_path / "gsp-demo1.tail.toml").write_text(toml_text)
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "validate", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
    # correct fingerprint per bucket so the rollup groups them apart
    assert f"ready_idle_tail_{kind}" in toml_text


def test_fingerprints_differ_between_buckets():
    sup = ted.render_record(bead("a", days_idle=40), "superseded", NOW,
                            observed_at="2026-08-04T12:00:00Z")
    res = ted.render_record(bead("b", days_idle=5), "resling", NOW,
                            observed_at="2026-08-04T12:00:00Z")
    assert "close_moot" in sup and "resling" in res


def test_superseded_record_carries_signal_evidence(tmp_path):
    # A bead classified superseded by a real signal must record WHICH signal
    # and WHICH bead subsumed it, so the downstream close brief is auditable.
    b = bead("gsp-sig", days_idle=40)
    b["_supersession"] = {"signal": "parent_epic_closed", "matched_bead": "ep-c"}
    toml_text = ted.render_record(b, "superseded", NOW,
                                  observed_at="2026-08-04T12:00:00Z")
    assert "parent_epic_closed" in toml_text and "ep-c" in toml_text
    # still schema-valid through the real pipeline validator
    (tmp_path / "gsp-sig.tail.toml").write_text(toml_text)
    proc = subprocess.run(
        [sys.executable, str(VALIDATOR), "validate", str(tmp_path)],
        capture_output=True, text=True,
    )
    assert proc.returncode == 0, proc.stderr
