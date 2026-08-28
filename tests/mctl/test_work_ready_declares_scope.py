"""M3 / mc-uvl: `work_ready` returned rows with no denominator beside them.

TWO SEPARATE CLAIMS LIVE IN mc-uvl, AND THEY HAVE DIFFERENT ANSWERS.

1. "A CLOSED source bead reports `readiness: ready`." That is the correctness
   half, and #157 (`MWRK013`, `_closed_source_blockers`) already fixed it. The
   tests below re-assert it at the level mc-uvl actually described -- the
   CONSEQUENCE, "a store containing a closed bead must not yield that bead from
   `work_ready`" -- because the #157 tests only ever called the helper directly.
   A helper returning a Diagnostic is not the same fact as `ready_work` dropping
   the row, and only the second one is what a dispatcher acts on.

   `test_the_fixture_would_have_caught_the_old_behaviour` is the control. It
   neuters the guard back to its pre-#157 shape and asserts the closed bead
   REAPPEARS. Without it, a fixture that never contained a dispatchable closed
   bead in the first place would pass this file while proving nothing.

2. "The count is a phantom." That half is NOT fixed. `work_ready` returned a
   bare array: 33 rows for mathcity on 2026-08-28, with nothing saying how many
   briefs were examined to produce them, how many were dropped as blocked, or
   that two of those rows named the SAME bead (`mc-7h1`, via briefs `mc-02zyz`
   and `mc-u0ix`). "33 ready" was quotable as a total, and it is not one.

`work_scope` follows `beads_list`'s shipped shape (#245) field for field --
`matched` beside `total_in_store`, and an `_excluded` list naming what was
dropped -- with `total_in_store` counting the WHOLE store, never the narrowed
set. The name differs from `beads_list`'s `scope` for one measured reason: the
cross-rig merge already puts a STRING at the top-level `scope` key
(`city.py:ALL_RIGS_SCOPE`), so declaring an object there would make
`work_ready --all-rigs` fail its own output schema. The key is renamed; the
convention is not.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core import work  # noqa: E402
from mctl_core.context import MctlContext  # noqa: E402


def _bead(
    bead_id: str,
    *,
    status: str,
    issue_type: str = "task",
    sources: tuple[str, ...] = (),
    metadata: dict[str, object] | None = None,
) -> dict[str, object]:
    row: dict[str, object] = {
        "id": bead_id,
        "title": bead_id,
        "status": status,
        "issue_type": issue_type,
    }
    if sources:
        row["dependencies"] = [
            {"issue_id": bead_id, "depends_on_id": source, "type": "blocks"}
            for source in sources
        ]
    if metadata:
        row["metadata"] = metadata
    return row


#: An APPROVED brief is a CLOSED brief -- `_approved_for_dispatch` requires it,
#: because closing the brief is what adjudication IS. Spelled once here so no
#: fixture below accidentally builds an "approved" brief that is still open and
#: passes for the wrong reason.
APPROVED = {"status": "closed", "issue_type": "decision", "metadata": {"verdict": "approve"}}


def _rig(tmp_path: Path, rows: list[dict[str, object]]) -> MctlContext:
    rig_root = tmp_path / "rig"
    (rig_root / ".beads" / "briefs" / "stack").mkdir(parents=True)
    (rig_root / ".beads" / "briefs" / "decisions").mkdir(parents=True)
    (rig_root / ".beads" / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (rig_root / ".beads" / "decisions-track").mkdir(parents=True)
    (rig_root / ".beads" / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    fixture = rig_root / ".beads" / "issues.jsonl"
    fixture.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")
    return MctlContext(
        city_root=tmp_path,
        rig_id="mathcity",
        rig_root=rig_root,
        beads_fixture=fixture,
        rig_db=".beads",
        source_checkout=tmp_path,
        paths_toml=tmp_path / "paths.toml",
        gates_toml=tmp_path / "gates.toml",
        invocation_cwd=tmp_path,
        trace_id="trace-work-scope",
        warnings=(),
        discovery_path="test",
        city_active=None,
        city_endpoint=None,
    )


#: One closed source and one open source, each behind its own approved brief.
#: The two briefs are identical in every respect the readiness checks look at
#: EXCEPT the source's status, so anything that returns both, or neither, is
#: not discriminating on the thing under test.
CLOSED_AND_OPEN = [
    _bead("mc-brief-open", sources=("mc-src-open",), **APPROVED),
    _bead("mc-src-open", status="open"),
    _bead("mc-brief-closed", sources=("mc-src-closed",), **APPROVED),
    _bead("mc-src-closed", status="closed"),
]


# --- 1. the consequence, not the helper -------------------------------------


def test_a_closed_bead_is_not_yielded_as_ready_work(tmp_path: Path):
    """The claim mc-uvl actually makes, asserted where a dispatcher would read it."""
    ctx = _rig(tmp_path, CLOSED_AND_OPEN)
    assert "mc-src-closed" not in {item.bead_id for item in work.ready_work(ctx)}


def test_the_open_control_IS_yielded(tmp_path: Path):
    """The control. A filter that returned nothing would pass the test above."""
    ctx = _rig(tmp_path, CLOSED_AND_OPEN)
    assert [item.bead_id for item in work.ready_work(ctx)] == ["mc-src-open"]


def test_the_fixture_would_have_caught_the_old_behaviour(tmp_path: Path, monkeypatch):
    """Reverting the #157 guard alone must make the closed bead reappear.

    mc-uvl asked for exactly this ("reverting the fix alone must fail it"). It
    is the difference between a fixture that proves the guard works and one
    that merely never contained a closed bead worth blocking.
    """
    ctx = _rig(tmp_path, CLOSED_AND_OPEN)
    monkeypatch.setattr(work, "_closed_source_blockers", lambda *a, **k: [])
    assert "mc-src-closed" in {item.bead_id for item in work.ready_work(ctx)}


def test_a_brief_naming_itself_as_its_own_source_is_not_ready(tmp_path: Path):
    """The residual hole in the #173 exemption, closed here.

    #173 exempted the self-source case because a SOURCELESS brief is made its
    own source by the `source_id = brief_id` fallback, and adjudication closes
    it -- so asking "is the source closed?" there is meaningless. But the
    exemption keyed on `source.id == brief_id`, which is also true when a brief
    EXPLICITLY lists its own id as a source dependency. That brief has a real
    source_id, so MWRK011 never fires, the exemption swallows MWRK013, and a
    closed bead is dispatchable again by the very route #157 closed.

    Measured 2026-08-28 across the mathcity, hq and hecke stores (46,550
    beads): ZERO briefs currently name themselves. This is a latent hole, not a
    live one -- but it is the same hole, and it is one predicate wide.
    """
    ctx = _rig(tmp_path, [_bead("mc-self", sources=("mc-self",), **APPROVED)])
    assert [item.bead_id for item in work.ready_work(ctx)] == []


def test_a_sourceless_brief_still_reports_no_source_and_not_a_closed_one(tmp_path: Path):
    """#173 must survive: the two blockers describe incompatible worlds."""
    ctx = _rig(tmp_path, [_bead("mc-sourceless", **APPROVED)])
    item = work.work_status(ctx, "mc-sourceless")
    codes = {blocker.code for blocker in item.blockers}
    assert "MWRK011" in codes
    assert "MWRK013" not in codes


# --- 2. the count that could not declare itself -----------------------------


def test_ready_work_payload_declares_what_it_examined(tmp_path: Path):
    """`matched` is meaningless without the denominator it was drawn from."""
    payload = work.ready_work_payload(_rig(tmp_path, CLOSED_AND_OPEN))
    scope = payload["work_scope"]
    assert scope["matched"] == 1
    assert scope["briefs_examined"] == 2
    assert scope["total_in_store"] == 4


def test_total_in_store_counts_the_whole_store_not_the_narrowed_set(tmp_path: Path):
    """#245's rule, restated: a denominator that shrinks with the filter is the
    bug with extra steps. Adding beads that no filter can reach must still move
    it."""
    rows = CLOSED_AND_OPEN + [
        _bead("mc-noise-1", status="open"),
        _bead("mc-noise-2", status="closed"),
    ]
    scope = work.ready_work_payload(_rig(tmp_path, rows))["work_scope"]
    assert scope["matched"] == 1
    assert scope["briefs_examined"] == 2
    assert scope["total_in_store"] == 6


def test_the_dropped_readiness_states_are_named(tmp_path: Path):
    """`statuses_excluded`'s analogue. The blocked brief is not simply absent."""
    scope = work.ready_work_payload(_rig(tmp_path, CLOSED_AND_OPEN))["work_scope"]
    assert scope["readiness_excluded"] == ["blocked"]


def test_nothing_excluded_is_reported_as_an_empty_list_not_omitted(tmp_path: Path):
    """A census must be distinguishable from a read that forgot to say."""
    rows = [
        _bead("mc-brief-open", sources=("mc-src-open",), **APPROVED),
        _bead("mc-src-open", status="open"),
    ]
    scope = work.ready_work_payload(_rig(tmp_path, rows))["work_scope"]
    assert scope["matched"] == 1
    assert scope["readiness_excluded"] == []


def test_rows_are_counted_separately_from_the_beads_they_name(tmp_path: Path):
    """Measured live 2026-08-28: `mc-7h1` occupied two of mathcity's 33 rows,
    via briefs `mc-02zyz` and `mc-u0ix`; `gt-byxtj` occupied two of hq's four.
    Two rows for one bead is one dispatchable bead and one double-dispatch
    waiting to happen, so the row count is not the work count and must not be
    the only number in the payload."""
    rows = [
        _bead("mc-brief-a", sources=("mc-shared",), **APPROVED),
        _bead("mc-brief-b", sources=("mc-shared",), **APPROVED),
        _bead("mc-shared", status="open"),
    ]
    payload = work.ready_work_payload(_rig(tmp_path, rows))
    assert len(payload["work"]) == 2
    assert payload["work_scope"]["matched"] == 2
    assert payload["work_scope"]["distinct_bead_ids"] == 1


def test_matched_always_equals_the_rows_actually_returned(tmp_path: Path):
    """The one invariant that makes the block worth trusting: a `matched` that
    could drift from the array is a second number to be wrong about."""
    for rows in (CLOSED_AND_OPEN, CLOSED_AND_OPEN[:2], []):
        payload = work.ready_work_payload(_rig(tmp_path / str(len(rows)), rows))
        assert payload["work_scope"]["matched"] == len(payload["work"])


# --- 3. the cross-rig total, which is the one that got quoted ---------------
#
# mc-uvl's measurement was `mctl work_ready --all-rigs`, not a single-rig read,
# so a `work_scope` that existed only per rig would leave the exact number in
# the defect report still undeclared. These pin `merge_outcomes` directly:
# the MCP and CLI adapters both route through it, and `test_all_rigs_reads.py`
# already pins that they route through it, so one set of assertions covers
# both without asserting the same fact twice in two dialects.


def _outcome(rig_id: str, payload: dict[str, object] | None, *, failed: bool = False):
    from mctl_core.city import RigOutcome

    return RigOutcome(
        rig_id=rig_id,
        rig_root=f"/tmp/{rig_id}",
        rig_db=f".beads-{rig_id}",
        payload=payload or {},
        failure=(
            ({"code": "MCTX001", "message": f"{rig_id} could not be read"},) if failed else ()
        ),
    )


def _city_scope(tmp_path: Path):
    from mctl_core.context import CityScope

    return CityScope(
        city_root=tmp_path,
        discovery_path="test",
        invocation_cwd=tmp_path,
        trace_id="trace-merge",
        rigs=(),
        config={},
    )


def _merge(tmp_path: Path, outcomes):
    from mctl_core.city import merge_outcomes

    return merge_outcomes(
        _city_scope(tmp_path),
        outcomes,
        arrays=("work",),
        scopes={"work_scope": dict(work.EMPTY_WORK_SCOPE)},
        trace_id="trace-merge",
    )


def _rig_payload(matched: int, briefs: int, total: int, excluded: list[str]) -> dict[str, object]:
    return {
        "work": [{"brief_id": f"b{i}", "bead_id": f"s{i}"} for i in range(matched)],
        "work_scope": {
            "matched": matched,
            "distinct_bead_ids": matched,
            "briefs_examined": briefs,
            "total_in_store": total,
            "readiness_excluded": excluded,
        },
    }


def test_the_city_wide_total_carries_a_denominator(tmp_path: Path):
    """The bare city-wide array is what got read as "two dispatchable, city-wide"."""
    merged = _merge(
        tmp_path,
        [
            _outcome("mathcity", _rig_payload(1, 40, 900, ["blocked"])),
            _outcome("hq", _rig_payload(2, 5, 100, ["blocked", "dispatched"])),
        ],
    )
    assert merged["work_scope"]["matched"] == 3 == len(merged["work"])
    assert merged["work_scope"]["briefs_examined"] == 45
    assert merged["work_scope"]["total_in_store"] == 1000
    assert merged["work_scope"]["readiness_excluded"] == ["blocked", "dispatched"]


def test_a_rig_that_could_not_be_read_adds_nothing_to_the_denominator(tmp_path: Path):
    """A denominator with no store behind it is the failure this block prevents.

    The unreadable rig must not appear to have been examined and found empty --
    `ok: false` beside it is the whole story, and `test_all_rigs_reads.py`
    pins that half.
    """
    merged = _merge(
        tmp_path,
        [
            _outcome("mathcity", _rig_payload(1, 40, 900, ["blocked"])),
            _outcome("sick", None, failed=True),
        ],
    )
    assert merged["work_scope"] == {
        "matched": 1,
        "distinct_bead_ids": 1,
        "briefs_examined": 40,
        "total_in_store": 900,
        "readiness_excluded": ["blocked"],
    }
    sick = next(entry for entry in merged["rigs"] if entry["rig_id"] == "sick")
    assert sick["ok"] is False
    assert "work_scope" not in sick, "a rig nobody could read has no scope to report"


def test_a_city_where_every_rig_failed_still_declares_zero_not_nothing(tmp_path: Path):
    """Absence would read as "the question was not asked". It always was.

    This is also what keeps `--all-rigs` inside `work_ready`'s own output
    schema, which requires `work_scope`.
    """
    merged = _merge(tmp_path, [_outcome("sick", None, failed=True)])
    assert merged["work_scope"] == dict(work.EMPTY_WORK_SCOPE)
    assert merged["work"] == []


def test_the_per_rig_scope_survives_the_merge(tmp_path: Path):
    """"1 of 40" and "2 of 5" are different reports; the sum alone hides which
    rig the rows came out of."""
    merged = _merge(
        tmp_path,
        [
            _outcome("mathcity", _rig_payload(1, 40, 900, ["blocked"])),
            _outcome("hq", _rig_payload(2, 5, 100, [])),
        ],
    )
    per_rig = {entry["rig_id"]: entry.get("work_scope") for entry in merged["rigs"]}
    assert per_rig["mathcity"]["briefs_examined"] == 40
    assert per_rig["hq"]["briefs_examined"] == 5


def test_the_merged_scope_matches_a_real_two_rig_read(tmp_path: Path):
    """The unit assertions above use hand-built outcomes; this one drives the
    real `ready_work_payload` for two disjoint stores and checks the merge
    against what those two reads actually said, so the fold cannot agree with
    a fixture while disagreeing with the core."""
    left = work.ready_work_payload(_rig(tmp_path / "left", CLOSED_AND_OPEN))
    right = work.ready_work_payload(
        _rig(tmp_path / "right", [_bead("mc-b", sources=("mc-s",), **APPROVED), _bead("mc-s", status="open")])
    )
    merged = _merge(tmp_path, [_outcome("left", left), _outcome("right", right)])
    assert merged["work_scope"]["matched"] == 2 == len(merged["work"])
    assert merged["work_scope"]["total_in_store"] == 6  # 4 + 2, not 4 and not 2
    assert merged["work_scope"]["briefs_examined"] == 3
