"""mc-p0wps Task 3: `plan_bead_close` closes ONE bead, with loud refusals.

The close verb mirrors `plan_molecule_cancel` but closes a single bead --
cascade-close is `molecule_cancel`'s explicit job. Its two conditional refusals
are the point (P6.2, each observed failing then passing):

- a molecule ROOT with open steps is refused (`MBCL_ROOT_HAS_OPEN_STEPS`), and
  `force` does NOT bypass it (deps-only downgrade, adjudicated 2026-08-28);
- a bead blocked by open dependencies is refused (`MBCL_BLOCKED_BY_OPEN_DEPS`)
  UNLESS `force`, which downgrades it and passes `bd update --force`. Blocked
  is bd's sense of the word (mc-h8331): only an open dependency on a `blocks`,
  `conditional-blocks` or `waits-for` edge on which the bead is the dependent
  counts. `tracks`, `parent-child`, `related` and every other type never block.

The bead read is injected, so no store, no `bd`. Each fixture bead is parsed
from a `bd list --json`-shaped row by the production parser, so its raw edges
carry a type exactly as live rows do.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core import bead_writes  # noqa: E402
from mctl_core.bead_writes import BeadCloseInput, plan_bead_close  # noqa: E402
from mctl_core.beads import _bead_from_mapping  # noqa: E402
from mctl_core.context import MctlContext  # noqa: E402
from mctl_core.effects import MutationError, dry_run_payload  # noqa: E402


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
        trace_id="trace-close-1",
        warnings=(),
        discovery_path="test",
        city_active=None,
        city_endpoint=None,
    )


def _edge(bead_id, dep):
    """One raw edge as `bd list --json` writes it. A bare id is a `blocks` edge,
    bd's default type, so every test written before mc-h8331 keeps its meaning."""
    dep_id, dep_type = (dep, "blocks") if isinstance(dep, str) else dep
    return {"issue_id": bead_id, "depends_on_id": dep_id, "type": dep_type}


def _bead(bead_id, *, status="open", metadata=None, kind=None, deps=(), raw_deps=None):
    """A task bead, parsed by the production parser from a `bd list --json` row.

    `deps` takes bare ids (`blocks` edges) or `(id, type)` pairs. `raw_deps`
    replaces the edge list verbatim, for shapes live rows never carry.
    """
    meta = dict(metadata or {})
    if kind is not None:
        meta["gc.kind"] = kind
    if raw_deps is None:
        raw_deps = [_edge(bead_id, dep) for dep in deps]
    return _bead_from_mapping(
        {
            "id": bead_id,
            "title": "t",
            "status": status,
            "issue_type": "task",
            "labels": [],
            "created_at": "2026-08-27T00:00:00Z",
            "updated_at": "2026-08-27T00:00:00Z",
            "metadata": meta,
            "dependencies": list(raw_deps),
        }
    )


def _root(bead_id="mc-root", **kw):
    return _bead(bead_id, kind="workflow", **kw)


def _step(bead_id, root_id="mc-root", **kw):
    return _bead(bead_id, metadata={"gc.root_bead_id": root_id}, **kw)


def _inject(monkeypatch, beads):
    monkeypatch.setattr(bead_writes, "read_beads", lambda *a, **k: tuple(beads))


def _close(ctx, bead_id, *, force=False):
    return plan_bead_close(ctx, BeadCloseInput(bead_id=bead_id, reason=None, force=force))


# --- molecule root with open steps (FATAL, force-independent) ----------------


def test_root_with_open_step_is_refused(monkeypatch, tmp_path):
    _inject(monkeypatch, [_root("mc-root"), _step("mc-s1", status="open")])
    plan = _close(_ctx(tmp_path), "mc-root")
    codes = [d.code for d in plan.preconditions]
    assert "MBCL_ROOT_HAS_OPEN_STEPS" in codes
    assert plan.bead_updates == (), "a refused root must not plan a close"
    with pytest.raises(MutationError):
        dry_run_payload(plan)


def test_root_closes_once_its_steps_are_closed(monkeypatch, tmp_path):
    _inject(monkeypatch, [_root("mc-root"), _step("mc-s1", status="closed")])
    plan = _close(_ctx(tmp_path), "mc-root")
    assert not plan.preconditions
    assert len(plan.bead_updates) == 1
    assert plan.bead_updates[0].id == "mc-root"
    assert plan.bead_updates[0].status == "closed"


def test_force_does_not_bypass_the_root_open_steps_guard(monkeypatch, tmp_path):
    """Negative control: force is deps-only, never the false-success guard."""
    _inject(monkeypatch, [_root("mc-root"), _step("mc-s1", status="open")])
    plan = _close(_ctx(tmp_path), "mc-root", force=True)
    codes = [d.code for d in plan.preconditions]
    assert "MBCL_ROOT_HAS_OPEN_STEPS" in codes
    with pytest.raises(MutationError):
        dry_run_payload(plan)


# --- blocked by open dependencies (ERROR, force downgrades) ------------------


def test_blocked_by_open_deps_is_refused(monkeypatch, tmp_path):
    _inject(
        monkeypatch,
        [_bead("mc-b", deps=("mc-dep",)), _bead("mc-dep", status="open")],
    )
    plan = _close(_ctx(tmp_path), "mc-b")
    codes = [d.code for d in plan.preconditions]
    assert "MBCL_BLOCKED_BY_OPEN_DEPS" in codes
    with pytest.raises(MutationError):
        dry_run_payload(plan)


def test_force_downgrades_blocked_by_open_deps(monkeypatch, tmp_path):
    _inject(
        monkeypatch,
        [_bead("mc-b", deps=("mc-dep",)), _bead("mc-dep", status="open")],
    )
    plan = _close(_ctx(tmp_path), "mc-b", force=True)
    assert not plan.preconditions, "force downgrades the blocked-by-deps refusal"
    assert len(plan.bead_updates) == 1
    assert plan.bead_updates[0].force is True
    assert plan.bead_updates[0].status == "closed"


def test_closed_deps_do_not_block(monkeypatch, tmp_path):
    _inject(
        monkeypatch,
        [_bead("mc-b", deps=("mc-dep",)), _bead("mc-dep", status="closed")],
    )
    plan = _close(_ctx(tmp_path), "mc-b")
    assert not plan.preconditions
    assert len(plan.bead_updates) == 1


# --- non-existent bead (FATAL) -----------------------------------------------


def test_non_existent_bead_is_refused(monkeypatch, tmp_path):
    _inject(monkeypatch, [_bead("mc-other")])
    plan = _close(_ctx(tmp_path), "mc-missing")
    codes = [d.code for d in plan.preconditions]
    assert "MBCL_NO_SUCH_BEAD" in codes
    assert plan.bead_updates == ()
    with pytest.raises(MutationError):
        dry_run_payload(plan)


# --- a plain open bead closes with an if_status race guard --------------------


def test_plain_open_bead_closes_with_if_status(monkeypatch, tmp_path):
    _inject(monkeypatch, [_bead("mc-b", status="in_progress")])
    plan = _close(_ctx(tmp_path), "mc-b")
    assert not plan.preconditions
    assert len(plan.bead_updates) == 1
    update = plan.bead_updates[0]
    assert update.id == "mc-b"
    assert update.status == "closed"
    assert update.if_status == "in_progress", "inherits MCTL_BEAD_UPDATE_RACE_LOST"
    assert update.metadata["mctl_trace_id"] == "trace-close-1"


# --- mc-h8331: only bd's blocking edge types block ----------------------------
#
# The type lists are written out here, not imported from bead_writes, so the
# tests are an independent oracle. Source: bd 1.3.0 (71c4cd08b),
# internal/types/types.go -- IsBlockingEdge and the DependencyType constants.

BLOCKING_TYPES = ("blocks", "conditional-blocks", "waits-for")
NON_BLOCKING_TYPES = (
    "tracks",
    "parent-child",
    "related",
    "relates-to",
    "discovered-from",
    "supersedes",
    "replies-to",
    "duplicates",
    "until",
    "caused-by",
    "validates",
    "delegated-from",
    "authored-by",
    "assigned-to",
    "approved-by",
    "attests",
)


def _blocked_message(plan):
    (diagnostic,) = [d for d in plan.preconditions if d.code == "MBCL_BLOCKED_BY_OPEN_DEPS"]
    return diagnostic.message


def _assert_closes_unforced(plan, bead_id):
    codes = [d.code for d in plan.preconditions]
    assert "MBCL_BLOCKED_BY_OPEN_DEPS" not in codes, [d.message for d in plan.preconditions]
    assert len(plan.bead_updates) == 1
    update = plan.bead_updates[0]
    assert (update.id, update.status, update.force) == (bead_id, "closed", False)


@pytest.mark.parametrize("edge_type", NON_BLOCKING_TYPES)
def test_non_blocking_edge_types_never_block(monkeypatch, tmp_path, edge_type):
    """R1 / REQ-001: an open dependency on a non-blocking edge never refuses."""
    _inject(monkeypatch, [_bead("mc-b", deps=(("mc-dep", edge_type),)), _bead("mc-dep")])
    _assert_closes_unforced(_close(_ctx(tmp_path), "mc-b"), "mc-b")


def test_a_step_closes_despite_its_tracks_edge_to_its_root(monkeypatch, tmp_path):
    """R1, the measured class (mc-7r3nj on 2026-10-01): tracks -> the open root,
    blocks -> a closed sibling. Before mc-h8331 this was refused, naming the root."""
    _inject(
        monkeypatch,
        [
            _root("mc-6x7dx"),
            _step(
                "mc-7r3nj",
                root_id="mc-6x7dx",
                deps=(("mc-6x7dx", "tracks"), ("mc-wpbn4", "blocks")),
            ),
            _step("mc-wpbn4", root_id="mc-6x7dx", status="closed"),
        ],
    )
    _assert_closes_unforced(_close(_ctx(tmp_path), "mc-7r3nj"), "mc-7r3nj")


def test_a_related_edge_does_not_block(monkeypatch, tmp_path):
    """R1 (mc-5pwm6, refused before mc-h8331: trace 2efbaf5d-5262-4410-998f-0b233e05e3a9)."""
    _inject(monkeypatch, [_bead("mc-5pwm6", deps=(("mc-bjvz", "related"),)), _bead("mc-bjvz")])
    _assert_closes_unforced(_close(_ctx(tmp_path), "mc-5pwm6"), "mc-5pwm6")


def test_an_open_parent_does_not_block_its_child(monkeypatch, tmp_path):
    """R1 / REQ-003, a condition of mc-par6v: parent-child is structural, not blocking."""
    _inject(
        monkeypatch,
        [_bead("mc-child", deps=(("mc-parent", "parent-child"),)), _bead("mc-parent")],
    )
    _assert_closes_unforced(_close(_ctx(tmp_path), "mc-child"), "mc-child")


@pytest.mark.parametrize("edge_type", BLOCKING_TYPES)
def test_each_blocking_edge_type_still_blocks(monkeypatch, tmp_path, edge_type):
    """R2 / REQ-004, REQ-005: each blocking type refuses, naming the blocker."""
    _inject(monkeypatch, [_bead("mc-b", deps=(("mc-dep", edge_type),)), _bead("mc-dep")])
    plan = _close(_ctx(tmp_path), "mc-b")
    assert "is blocked by 1 open dependenc(ies): mc-dep." in _blocked_message(plan)
    with pytest.raises(MutationError):
        dry_run_payload(plan)


def test_the_refusal_names_only_the_real_blocker(monkeypatch, tmp_path):
    """R2 / REQ-005 (mc-a33jd): tracks -> the open root, blocks -> an open sibling.
    Refused, naming ONLY the sibling. Before mc-h8331 it named both, count 2."""
    _inject(
        monkeypatch,
        [
            _root("mc-ls8eq"),
            _step(
                "mc-a33jd",
                root_id="mc-ls8eq",
                deps=(("mc-ls8eq", "tracks"), ("mc-xnqb0", "blocks")),
            ),
            _step("mc-xnqb0", root_id="mc-ls8eq"),
        ],
    )
    message = _blocked_message(_close(_ctx(tmp_path), "mc-a33jd"))
    assert "is blocked by 1 open dependenc(ies): mc-xnqb0." in message
    assert "mc-ls8eq" not in message


def test_an_edge_on_which_this_bead_is_the_dependency_does_not_count(monkeypatch, tmp_path):
    """R3 / REQ-002: this edge says mc-other depends on mc-b, not the reverse."""
    _inject(
        monkeypatch,
        [
            _bead(
                "mc-b",
                raw_deps=[{"issue_id": "mc-other", "depends_on_id": "mc-b", "type": "blocks"}],
            ),
            _bead("mc-other"),
        ],
    )
    _assert_closes_unforced(_close(_ctx(tmp_path), "mc-b"), "mc-b")


def test_an_entry_whose_issue_id_names_another_bead_never_counts(monkeypatch, tmp_path):
    """R3 / REQ-002: even the legacy shape with no depends_on_id, which
    `beads._dependency_ids` reads as a dependency id. In bd, issue_id is the
    dependent, so this entry is never mc-b's own edge."""
    _inject(
        monkeypatch,
        [_bead("mc-b", raw_deps=[{"issue_id": "mc-other", "type": "blocks"}]), _bead("mc-other")],
    )
    _assert_closes_unforced(_close(_ctx(tmp_path), "mc-b"), "mc-b")


def test_an_unresolvable_blocker_is_not_counted(monkeypatch, tmp_path):
    """R4 / REQ-004: a blocks edge to a bead the task-only read cannot see (an
    event bead such as mc-5jf7n, or another rig's bead) is not counted."""
    _inject(monkeypatch, [_bead("mc-b", deps=("mc-5jf7n",))])
    _assert_closes_unforced(_close(_ctx(tmp_path), "mc-b"), "mc-b")


@pytest.mark.parametrize(
    "raw_edge",
    [
        "mc-dep",
        {"depends_on_id": "mc-dep"},
        {"issue_id": "mc-b", "depends_on_id": "mc-dep", "type": ""},
    ],
    ids=["bare-id", "dict-without-type", "empty-type"],
)
def test_an_untyped_edge_counts_as_blocks(monkeypatch, tmp_path, raw_edge):
    """R5 / REQ-006: no readable type means `blocks`, bd's default. Fail closed."""
    _inject(monkeypatch, [_bead("mc-b", raw_deps=[raw_edge]), _bead("mc-dep")])
    plan = _close(_ctx(tmp_path), "mc-b")
    assert "is blocked by 1 open dependenc(ies): mc-dep." in _blocked_message(plan)


@pytest.mark.parametrize(("dependency_type", "blocks"), [("tracks", False), ("blocks", True)])
def test_the_bd_show_shape_reads_dependency_type(monkeypatch, tmp_path, dependency_type, blocks):
    """TS-1: `bd show --json` lists each dependency as the target bead, with its
    edge type under `dependency_type` and no `issue_id`."""
    _inject(
        monkeypatch,
        [
            _bead("mc-b", raw_deps=[{"id": "mc-dep", "dependency_type": dependency_type}]),
            _bead("mc-dep"),
        ],
    )
    codes = [d.code for d in _close(_ctx(tmp_path), "mc-b").preconditions]
    assert ("MBCL_BLOCKED_BY_OPEN_DEPS" in codes) is blocks


def test_an_unknown_edge_type_does_not_block(monkeypatch, tmp_path):
    """REQ-001's "only if": a type bd does not define as blocking never blocks
    here. bd's apply-time guard stays the backstop for any future blocking type."""
    _inject(monkeypatch, [_bead("mc-b", deps=(("mc-dep", "not-a-bd-type"),)), _bead("mc-dep")])
    _assert_closes_unforced(_close(_ctx(tmp_path), "mc-b"), "mc-b")


def test_a_repeated_edge_is_named_once(monkeypatch, tmp_path):
    """REQ-005: the count is of blockers, not of the rows that name them."""
    edge = {"issue_id": "mc-b", "depends_on_id": "mc-dep", "type": "blocks"}
    _inject(monkeypatch, [_bead("mc-b", raw_deps=[edge, dict(edge)]), _bead("mc-dep")])
    plan = _close(_ctx(tmp_path), "mc-b")
    assert "is blocked by 1 open dependenc(ies): mc-dep." in _blocked_message(plan)


def test_a_row_without_a_dependencies_key_closes(monkeypatch, tmp_path):
    """A dependency-free row may carry no `dependencies` key at all."""
    row = {"id": "mc-b", "title": "t", "status": "open", "issue_type": "task"}
    _inject(monkeypatch, [_bead_from_mapping(row)])
    _assert_closes_unforced(_close(_ctx(tmp_path), "mc-b"), "mc-b")
