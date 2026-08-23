"""#182: `route_to` — set a step's dispatch route, the verb the fleet actually reads.

TAYLOR NAMED THE VERB and the name is the correction. It is not `assign`: the
thing a step carries is `gc.routed_to`, a POOL, stamped at cook time by
`ApplyGraphRouteBinding`. `assign` would have written an assignee (a session
bead) -- a different target, and one that duplicates a write cook already does.

MEASURED, and it is why this verb is not redundant. Across hecke's 746 step
beads:

    598 carry gc.routed_to
    148 carry NONE          <- 20% of steps are unrouted

An unrouted step is invisible to every pool query. `bd ready --metadata-field
gc.routed_to=<pool> --unassigned` cannot return it, so no worker can claim it,
and it never becomes work. `route_to` is the repair for those 148.

WHAT IT DOES NOT DO. It does not assign an assignee, does not claim, and does not
spawn a worker. If no session is alive the routed step still waits -- routing is
necessary and not sufficient, and saying so here stops the next reader from
believing this makes work execute.

OPTIMISTIC-CONCURRENCY, deliberately. The write carries `if_status`, so a step
whose status moved between plan and apply is refused rather than overwritten. bd
exits 13 and writes nothing.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core.beads import Bead  # noqa: E402
from mctl_core import work  # noqa: E402


class Ctx:
    city_root = Path("/tmp/stub-city")
    rig_root = Path("/tmp/stub-city/stub-rig")
    rig_id = "stub-rig"
    rig_db = "stub-db"
    trace_id = "stub-trace"


def step(bead_id: str, *, status: str = "open", routed: str | None = None) -> Bead:
    raw: dict = {"metadata": {"gc.root_bead_id": "root-1"}}
    if routed:
        raw["metadata"]["gc.routed_to"] = routed
    return Bead(
        id=bead_id, title=bead_id, status=status, issue_type="task", labels=(),
        source_dependencies=(), created_at=None, updated_at=None, raw=raw,
    )


def test_routing_an_unrouted_step_plans_a_metadata_write():
    """The 148. An unrouted step is invisible to every pool query."""
    plan = work.plan_route_to(Ctx(), step("s-1"), "hecke/gc.run-operator")
    assert plan.bead_update.metadata["gc.routed_to"] == "hecke/gc.run-operator"
    assert plan.bead_update.id == "s-1"


def test_the_write_carries_if_status_so_a_moved_step_is_refused():
    """Optimistic concurrency, not last-write-wins. bd exits 13 and writes nothing."""
    plan = work.plan_route_to(Ctx(), step("s-1", status="open"), "hecke/gc.run-operator")
    assert plan.bead_update.if_status == "open"


def test_rerouting_an_ALREADY_ROUTED_step_is_REFUSED_by_default():
    """598 steps already carry a route. Silently overwriting one moves work away
    from a pool that may be mid-claim. The caller must say so explicitly."""
    with pytest.raises(work.WorkError) as caught:
        work.plan_route_to(Ctx(), step("s-1", routed="hecke/core.control-dispatcher"),
                           "hecke/gc.run-operator")
    assert "MWRK014" in str(caught.value.diagnostic.code)


def test_an_explicit_reroute_is_allowed_and_names_the_previous_route():
    """Allowed, but never silent: the diagnostic trail must show what it displaced."""
    plan = work.plan_route_to(Ctx(), step("s-1", routed="hecke/core.control-dispatcher"),
                              "hecke/gc.run-operator", reroute=True)
    assert plan.bead_update.metadata["gc.routed_to"] == "hecke/gc.run-operator"
    assert "hecke/core.control-dispatcher" in plan.previous_route


def test_routing_to_an_empty_pool_name_is_REFUSED():
    """A step routed to '' is worse than unrouted: it looks routed and matches nothing."""
    with pytest.raises(work.WorkError):
        work.plan_route_to(Ctx(), step("s-1"), "")


def test_a_CLOSED_step_is_not_routable():
    """Routing finished work would resurrect it into a pool query."""
    with pytest.raises(work.WorkError):
        work.plan_route_to(Ctx(), step("s-1", status="closed"), "hecke/gc.run-operator")
