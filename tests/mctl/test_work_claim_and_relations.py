"""The typed replacements for the two bare `bd` calls in skills/work/SKILL.md.

Two things are under test, and they fail in different ways.

`work claim` replaces ``bd show <id> | grep -i assignee``. The grep reads a
human-readable rendering, so it cannot distinguish an unclaimed bead from a
missing one from a field bd renamed, and every caller re-derived the same four
`dispatch-provenance.v1` strings beside it by hand.

`work dispatch-event` replaces ``bd create --type event ...`` piped into
``bd dep relate``. Its interesting property is not that it writes the edge but
that it proves the edge is there afterwards, because bd will report success on
an edge that is not.

**The measurement these tests encode** (bd 1.1.0, two isolated stores,
2026-08-20):

* ``bd dep add <local-id> <foreign-id>`` exits **0** and prints
  "✓ Added dependency". ``bd show`` then reports ``dependency_count = 1``
  beside ``dependencies = null``; ``bd dep list`` returns ``[]``. The row IS
  in ``bd list --all --json`` -- which is how a reader can catch it at all.
* ``bd dep relate <local-id> <foreign-id>`` exits **1**:
  "failed to resolve <id>: no issue found". It does NOT share the defect.
* ``bd dep relate`` resolves ids fuzzily: ``bd dep relate aa-e11 aa-c``
  linked ``aa-e11`` to ``aa-cfi``. A zero exit does not say which beads were
  linked, which is the second reason the write is verified rather than
  trusted.
"""
from __future__ import annotations

from dataclasses import replace
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

MCTL = SCRIPTS_ROOT / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
WORK_STATE = FIXTURES / "work_state"

from mctl_core.beads import Bead, BeadRelate, apply_bead_relate, read_beads, verify_relation
from mctl_core.context import resolve_context
from mctl_core.effects import MutationError, apply_effect_plan, dry_run_payload
from mctl_core.work import WorkError, plan_dispatch_event, work_claim


DISPATCH_COMMAND = "gc sling mathcity/gc.run-operator source-open --on work-briefed"


def runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    schema_dst = source_checkout / "assets" / "bead-filter"
    schema_dst.mkdir(parents=True)
    shutil.copy2(
        REPO_ROOT / "assets" / "bead-filter" / "dispatch-provenance-schema.toml",
        schema_dst / "dispatch-provenance-schema.toml",
    )
    beads = rig_root / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    shutil.copy2(WORK_STATE / "beads.jsonl", beads / "issues.jsonl")
    shutil.copytree(WORK_STATE / "provenance", beads / "mctl" / "provenance")
    return city_root, rig_root


def fixture_path(rig_root: Path) -> Path:
    return rig_root / ".beads" / "issues.jsonl"


def context_for(city_root: Path, rig_root: Path):
    return resolve_context(
        city_root,
        city=city_root,
        rig="mathcity",
        require_runtime_city=True,
        env={"MCTL_BEADS_FIXTURE": str(fixture_path(rig_root))},
    )


def set_assignee(rig_root: Path, bead_id: str, assignee: str | None) -> None:
    path = fixture_path(rig_root)
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        if row["id"] == bead_id:
            row["assignee"] = assignee
    path.write_text(
        "".join(f"{json.dumps(row, sort_keys=True)}\n" for row in rows), encoding="utf-8"
    )


def run_mctl(*args: str, cwd: Path, rig_root: Path) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(fixture_path(rig_root))
    return subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def bead(bead_id: str, dependencies: tuple[str, ...] = ()) -> Bead:
    return Bead(
        id=bead_id,
        title=bead_id,
        status="open",
        issue_type="task",
        labels=(),
        source_dependencies=dependencies,
        created_at=None,
        updated_at=None,
        raw={},
    )


# --- part 1: the claim read -------------------------------------------------


def test_claim_reports_an_unclaimed_bead_as_an_immediate_strand(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    claim = work_claim(context_for(city_root, rig_root), "source-open", window_seconds=60)

    assert claim.assignee is None
    assert claim.verified_assignee is False
    assert claim.assignee_state == "empty_after_60s"
    assert claim.classification_hint == "immediate_strand"
    assert claim.fingerprint == "empty_assignee_after_verified_sling"


def test_claim_reports_a_held_bead_as_healthy(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    set_assignee(rig_root, "source-open", "polecat-7")

    claim = work_claim(context_for(city_root, rig_root), "source-open", window_seconds=60)

    assert claim.assignee == "polecat-7"
    assert claim.verified_assignee is True
    assert claim.assignee_state == "non_empty"
    assert claim.classification_hint == "healthy"
    assert claim.fingerprint == "verified_sling_claimed"


def test_claim_without_a_window_does_not_invent_one(tmp_path: Path):
    """`empty` and `empty_after_60s` are different claims about the world."""
    city_root, rig_root = runtime_fixture(tmp_path)

    claim = work_claim(context_for(city_root, rig_root), "source-open")

    assert claim.window_seconds is None
    assert claim.assignee_state == "empty"


def test_claim_treats_whitespace_as_unclaimed(tmp_path: Path):
    """`grep -i assignee` matched a line here and called it a claim."""
    city_root, rig_root = runtime_fixture(tmp_path)
    set_assignee(rig_root, "source-open", "   ")

    claim = work_claim(context_for(city_root, rig_root), "source-open")

    assert claim.verified_assignee is False
    assert claim.classification_hint == "immediate_strand"


def test_claim_on_a_missing_bead_is_a_typed_refusal_not_an_empty_answer(tmp_path: Path):
    """The grep could not tell these two apart; both printed nothing."""
    city_root, rig_root = runtime_fixture(tmp_path)

    with pytest.raises(WorkError) as raised:
        work_claim(context_for(city_root, rig_root), "source-does-not-exist")

    assert raised.value.diagnostic.code == "MWRK_BEAD_NOT_FOUND"
    assert raised.value.diagnostic.bead_id == "source-does-not-exist"


def test_claim_is_reachable_from_the_cli_as_json(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    set_assignee(rig_root, "source-open", "polecat-7")

    result = run_mctl(
        "work", "claim", "source-open", "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT, rig_root=rig_root,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["claim"]["assignee"] == "polecat-7"
    assert payload["claim"]["classification_hint"] == "healthy"


def test_a_missing_bead_exits_non_zero_from_the_cli(tmp_path: Path):
    """`bd show | grep` exited 0 on a bead that was not there."""
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        "work", "claim", "nope", "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT, rig_root=rig_root,
    )

    assert result.returncode == 1
    assert "MWRK_BEAD_NOT_FOUND" in result.stderr


# --- part 2a: verify_relation, the check itself -----------------------------


def test_verify_relation_accepts_an_edge_recorded_in_either_direction():
    """`bd dep relate` writes both rows; one row is still the relationship."""
    forward = verify_relation((bead("a", ("b",)), bead("b")), "a", "b")
    reverse = verify_relation((bead("a"), bead("b", ("a",))), "a", "b")

    assert forward.verified is True
    assert reverse.verified is True


def test_verify_relation_rejects_an_edge_the_store_never_recorded():
    verification = verify_relation((bead("a"), bead("b")), "a", "b")

    assert verification.edge_recorded is False
    assert verification.verified is False
    assert verification.unresolved_endpoints == ()


def test_verify_relation_names_a_cross_store_endpoint_the_rig_cannot_resolve():
    """The measured shape: the row is written, the target is not a bead here.

    `bd show` reports this as dependency_count=1 with dependencies=null, so
    every hydrating read agrees the edge is absent while the count insists it
    is there. Only the raw listing shows the row -- which is exactly the
    listing `read_beads` already fetches.
    """
    store = (bead("aa-e11", ("bb-wlb",)),)

    verification = verify_relation(store, "aa-e11", "bb-wlb")

    assert verification.edge_recorded is True, "the dangling row IS in the listing"
    assert verification.unresolved_endpoints == ("bb-wlb",)
    assert verification.verified is False


# --- part 2b: the write refuses, and proves ---------------------------------


def test_dispatch_event_refuses_a_cross_store_source_bead_before_writing(tmp_path: Path):
    """A foreign-store id is stopped as a precondition, not detected after.

    This is the latent hazard's fix: `bd dep add` would have written a
    dangling row and exited 0. Nothing is created, so there is no orphan
    event bead to explain either.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    ctx = context_for(city_root, rig_root)
    before = fixture_path(rig_root).read_text(encoding="utf-8")

    plan = plan_dispatch_event(
        ctx, "gt-8omhm", dispatch_command=DISPATCH_COMMAND, formula="work-briefed"
    )

    assert [diagnostic.code for diagnostic in plan.preconditions] == ["MWRK_BEAD_NOT_FOUND"]
    with pytest.raises(MutationError):
        apply_effect_plan(ctx, plan)
    with pytest.raises(MutationError):
        dry_run_payload(plan)
    assert fixture_path(rig_root).read_text(encoding="utf-8") == before


def test_dispatch_event_creates_the_event_bead_and_the_verified_edge(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    ctx = context_for(city_root, rig_root)
    set_assignee(rig_root, "source-open", "polecat-7")

    result = apply_effect_plan(
        ctx,
        plan_dispatch_event(
            ctx, "source-open", dispatch_command=DISPATCH_COMMAND, formula="work-briefed"
        ),
    )

    kinds = [effect["kind"] for effect in result.actual_effects]
    assert "bead_create" in kinds
    assert "bead_relate" in kinds
    assert "bead_relate_verified" in kinds
    verified = next(
        effect for effect in result.actual_effects if effect["kind"] == "bead_relate_verified"
    )
    assert verified["verified"] is True

    beads = {item.id: item for item in read_beads(ctx.rig_root, fixture_path=ctx.beads_fixture)}
    event_id = next(effect for effect in result.actual_effects if effect["kind"] == "bead_create")[
        "target"
    ]
    assert beads[event_id].issue_type == "event"
    assert "source-open" in beads[event_id].source_dependencies
    payload = json.loads(beads[event_id].raw["event_payload"])
    assert payload["schema"] == "dispatch-provenance.v1"
    assert payload["classification_hint"] == "healthy"
    assert payload["fingerprint"] == "verified_sling_claimed"
    assert payload["dispatch_command"] == DISPATCH_COMMAND


def test_the_event_payload_cannot_claim_a_handoff_the_store_does_not_show(tmp_path: Path):
    """The four provenance strings are derived, never asserted by the caller."""
    city_root, rig_root = runtime_fixture(tmp_path)
    ctx = context_for(city_root, rig_root)

    result = apply_effect_plan(
        ctx,
        plan_dispatch_event(
            ctx,
            "source-open",
            dispatch_command=DISPATCH_COMMAND,
            formula="work-briefed",
            window_seconds=60,
        ),
    )

    beads = {item.id: item for item in read_beads(ctx.rig_root, fixture_path=ctx.beads_fixture)}
    event_id = next(effect for effect in result.actual_effects if effect["kind"] == "bead_create")[
        "target"
    ]
    payload = json.loads(beads[event_id].raw["event_payload"])
    assert payload["verified_assignee"] is False
    assert payload["assignee_state"] == "empty_after_60s"
    assert payload["classification_hint"] == "immediate_strand"
    assert payload["fingerprint"] == "empty_assignee_after_verified_sling"


def test_a_dry_run_writes_nothing_and_still_shows_the_planned_edge(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    ctx = context_for(city_root, rig_root)
    before = fixture_path(rig_root).read_text(encoding="utf-8")

    payload = dry_run_payload(
        plan_dispatch_event(
            ctx, "source-open", dispatch_command=DISPATCH_COMMAND, formula="work-briefed"
        )
    )

    assert payload["applied"] is False
    relates = payload["effect_plan"]["bead_relates"]
    assert relates[0]["target_id"] == "source-open"
    assert relates[0]["link_type"] == "relates-to"
    assert fixture_path(rig_root).read_text(encoding="utf-8") == before


def test_a_dangling_edge_aborts_the_mutation_instead_of_reporting_success(tmp_path: Path):
    """The headline: a silently-lost cross-store edge is detected, not accepted.

    The relate is driven straight at a target the store cannot resolve --
    reproducing what `bd dep add <local> <foreign>` leaves behind, with the
    same faithfulness the fixture writer has: the row lands, the endpoint does
    not exist. The write path must refuse to call that applied.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    ctx = context_for(city_root, rig_root)
    plan = plan_dispatch_event(
        ctx, "source-open", dispatch_command=DISPATCH_COMMAND, formula="work-briefed"
    )
    hijacked = replace(
        plan,
        bead_creates=(),
        bead_relates=(BeadRelate(source_id="source-open", target_id="hq-foreign"),),
    )

    with pytest.raises(MutationError) as raised:
        apply_effect_plan(ctx, hijacked)

    assert raised.value.diagnostic.code == "MCTL_BEAD_RELATION_DANGLING"
    assert "hq-foreign" in raised.value.diagnostic.facts["detail"]

    # And the abort is recorded, not merely raised: a mutation that vanished
    # without a trace row is the failure the phased trace exists to prevent.
    traces = sorted((rig_root / ".beads" / "mctl" / "traces").glob("*.jsonl"))
    rows = [
        json.loads(line)
        for path in traces
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    aborted = [row for row in rows if row.get("phase") == "aborted"]
    assert aborted, "the aborted phase must be recorded"
    assert aborted[-1]["blocking_diagnostics"][0]["code"] == "MCTL_BEAD_RELATION_DANGLING"


def test_the_fixture_seam_writes_a_dangling_row_the_way_bd_does(tmp_path: Path):
    """If the seam refused, the case above could not be tested at all."""
    city_root, rig_root = runtime_fixture(tmp_path)
    path = fixture_path(rig_root)

    apply_bead_relate(
        rig_root,
        BeadRelate(source_id="source-open", target_id="hq-foreign"),
        fixture_path=path,
    )

    beads = read_beads(rig_root, fixture_path=path)
    by_id = {item.id: item for item in beads}
    assert "hq-foreign" in by_id["source-open"].source_dependencies
    assert "hq-foreign" not in by_id
    assert verify_relation(beads, "source-open", "hq-foreign").verified is False


def test_dispatch_event_is_reachable_from_the_cli_and_defaults_to_applying(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        "work", "dispatch-event", "source-open",
        "--dispatch-command", DISPATCH_COMMAND,
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT, rig_root=rig_root,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    assert any(
        effect["kind"] == "bead_relate_verified" and effect["verified"]
        for effect in payload["actual_effects"]
    )


def test_the_cli_exits_non_zero_when_the_source_bead_is_not_in_this_store(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        "work", "dispatch-event", "hq-foreign",
        "--dispatch-command", DISPATCH_COMMAND,
        "--city", str(city_root), "--rig", "mathcity", "--json",
        cwd=REPO_ROOT, rig_root=rig_root,
    )

    assert result.returncode == 1
    assert "MWRK_BEAD_NOT_FOUND" in result.stderr
