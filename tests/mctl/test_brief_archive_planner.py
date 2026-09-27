"""#95: the planner that makes `_archive_brief` reachable.

`_archive_brief` was correct and unreachable. Repo-wide the kind string
`"brief_archive"` appeared in ONE place -- the applier's own dispatch -- and
nothing constructed the `CacheUpdate` that runs it, not even
`test_brief_archive_effect.py`, which imports the private function directly. So
28 briefs carrying a TERMINAL status sat on the PENDING stack (8 -> 27 -> 28 ->
28 across four measurements) with the move already written.

The load-bearing test here is `test_plan_and_apply_actually_move_the_brief`: it
is the only one that proves the planner and the applier CONNECT, which is the
entire defect. The rest guard the refusals.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.context import MctlContext  # noqa: E402
from mctl_core.effects import (  # noqa: E402
    _apply_cache_update,
    plan_brief_archive,
)


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
        trace_id="trace-archive-1",
        warnings=(),
        discovery_path="test",
        city_active=None,
        city_endpoint=None,
    )


def _stack_brief(ctx: MctlContext, brief_id: str, status: str) -> Path:
    stack = ctx.rig_root / ".beads" / "briefs" / "stack"
    stack.mkdir(parents=True, exist_ok=True)
    path = stack / f"{brief_id}-brief.md"
    path.write_text(
        f"---\nstatus: {status}\nverdict: C -- omit scope-audit\n---\n\nbody\n",
        encoding="utf-8",
    )
    index = stack / ".index.jsonl"
    index.write_text(
        f'{{"source": "{brief_id}", "path": "{path}"}}\n'
        '{"source": "other-1", "path": "/keep/me.md"}\n',
        encoding="utf-8",
    )
    return path


def test_a_terminal_brief_plans_one_archive_and_no_bead_write(tmp_path: Path):
    """The cache catches up to the bead; it does not rewrite it.

    Every other planner updates a bead because the bead is canonical (B2.8).
    This one must not: the bead is already terminal and already right, and the
    defect is entirely in the cache. A bead write here would invent a lifecycle
    transition that already happened.
    """
    ctx = _ctx(tmp_path)
    _stack_brief(ctx, "mc-t1", "adjudicated")

    plan = plan_brief_archive(ctx, "mc-t1")

    assert plan.preconditions == ()
    assert plan.bead_updates == (), "archiving must not write the bead"
    assert len(plan.cache_updates) == 1
    update = plan.cache_updates[0]
    assert update.kind == "brief_archive"
    assert update.fields["archive_path"].endswith(
        "/.adjudicated-archive/mc-t1-brief.md"
    )
    assert update.fields["index_path"].endswith("/stack/.index.jsonl")


def test_plan_and_apply_actually_move_the_brief(tmp_path: Path):
    """The whole point of #95: planner -> applier, end to end.

    Without this, a green planner test and a green applier test can both pass
    while nothing connects them -- which is exactly the state this issue was in.
    """
    ctx = _ctx(tmp_path)
    stack_path = _stack_brief(ctx, "mc-t2", "adjudicated")
    index = stack_path.parent / ".index.jsonl"

    plan = plan_brief_archive(ctx, "mc-t2")
    _apply_cache_update(plan.cache_updates[0])

    archived = ctx.rig_root / ".beads" / "briefs" / ".adjudicated-archive" / "mc-t2-brief.md"
    assert archived.is_file(), "the archive copy must exist"
    assert not stack_path.exists(), "the brief must leave the pending stack"
    rows = index.read_text(encoding="utf-8").splitlines()
    assert not any("mc-t2" in row for row in rows), "the index row must be gone"
    assert any("other-1" in row for row in rows), "unrelated rows must survive"


@pytest.mark.parametrize("status", ["pending", "pending-review", "in-review-iter-2", "open"])
def test_a_non_terminal_brief_is_refused(tmp_path: Path, status: str):
    """MBRF069 -- the whole safety property.

    Archiving removes a brief from the presentation queue. Doing it to a
    PENDING brief destroys live work and does it SILENTLY: the brief simply
    stops being shown. Refused at plan time, so a dry run shows the refusal.
    """
    ctx = _ctx(tmp_path)
    _stack_brief(ctx, "mc-t3", status)

    plan = plan_brief_archive(ctx, "mc-t3")

    assert [d.code for d in plan.preconditions] == ["MBRF069"]
    assert plan.preconditions[0].severity.name == "FATAL"


def test_an_archive_copy_with_different_text_is_refused(tmp_path: Path):
    """MBRF070 -- #95's defect 3 (one slug in BOTH lanes) is surfaced, not resolved.

    The applier also refuses this, but a plan-time precondition is reviewable
    and an exception is not.
    """
    ctx = _ctx(tmp_path)
    _stack_brief(ctx, "mc-t4", "adjudicated")
    archive = ctx.rig_root / ".beads" / "briefs" / ".adjudicated-archive"
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "mc-t4-brief.md").write_text("a DIFFERENT decision\n", encoding="utf-8")

    plan = plan_brief_archive(ctx, "mc-t4")

    assert [d.code for d in plan.preconditions] == ["MBRF070"]


def test_an_identical_archive_copy_is_not_a_refusal(tmp_path: Path):
    """Byte-identical is the resumable case: a half-finished archive, not a collision."""
    ctx = _ctx(tmp_path)
    stack_path = _stack_brief(ctx, "mc-t5", "adjudicated")
    archive = ctx.rig_root / ".beads" / "briefs" / ".adjudicated-archive"
    archive.mkdir(parents=True, exist_ok=True)
    (archive / "mc-t5-brief.md").write_bytes(stack_path.read_bytes())

    plan = plan_brief_archive(ctx, "mc-t5")

    assert plan.preconditions == ()
    assert len(plan.cache_updates) == 1


def test_a_brief_with_no_stack_file_plans_nothing(tmp_path: Path):
    """Already archived plans no work -- absence is the ordinary path, not a fault.

    Same contract as an absent decision TOML planning no write. This matters
    for a sweep: re-running it over an already-clean stack must be a no-op
    rather than 28 refusals.
    """
    ctx = _ctx(tmp_path)
    (ctx.rig_root / ".beads" / "briefs" / "stack").mkdir(parents=True, exist_ok=True)

    plan = plan_brief_archive(ctx, "mc-absent")

    assert plan.cache_updates == ()
    assert plan.preconditions == ()
    assert plan.bead_updates == ()
