"""pools_status: the worker pool, made visible to the typed surface (#197).

Before this tool, zero matches for `pool_size`, `poolDesired`, `adjust_pool`,
`scale_pool`, `seats` or `capacity` anywhere in mctl_core. `fleet_sessions`
reports SLOTS but not the ceiling they fill, so "are we at the limit, or is
there no limit?" had no answer through the typed surface.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core.mcp_server import _handle_pools_status  # noqa: E402


def scope(config, rig_names=()):
    return SimpleNamespace(
        config=config,
        rigs=tuple(SimpleNamespace(name=n) for n in rig_names),
    )


def test_reports_configured_limits():
    out = _handle_pools_status(scope({"rigs": [{"name": "hecke", "max_active_sessions": 12}]}), {})
    assert out["config_readable"] is True
    assert out["pool_count"] == 1
    assert out["pools"][0]["max_active_sessions"] == 12


def test_every_registered_rig_is_a_row_even_with_no_limit():
    """The rig the city is named for was missing from its own pool report.

    A first version emitted only sections CARRYING a limit key. On the live
    city that dropped `rigs[mathcity]` -- which declares neither key -- so the
    uncapped rigs, the ones a reader most needs, were exactly the invisible
    ones. Same principle fleet_sessions states: absence renders like presence.
    """
    out = _handle_pools_status(
        scope({"rigs": [{"name": "hecke", "max_active_sessions": 12}]},
              rig_names=("hecke", "mathcity")),
        {},
    )
    names = {p["name"] for p in out["pools"]}
    assert "rigs[mathcity]" in names
    assert "rigs[mathcity]" in out["unlimited_pools"]


def test_unreadable_config_is_not_a_permissive_city():
    """An empty config must not render as 'this city sets no limits'.

    Same load-bearing distinction as `registry_present` on
    blast_radius_registry: rendered without it, "no limits configured" and "we
    failed to read the config" are both an empty list, and they demand
    opposite reactions.
    """
    out = _handle_pools_status(scope({}), {})
    assert out["config_readable"] is False
    assert out["pools"] == []


def test_repeated_identical_sections_collapse_to_one_pool():
    """The live city.toml repeats patches.agent[gc.run-operator].

    Two rows for one pool would read as two pools and double the apparent
    capacity of the city.
    """
    cfg = {"patches": {"agent": [
        {"name": "gc.run-operator", "max_active_sessions": 12, "min_active_sessions": 2},
        {"name": "gc.run-operator", "max_active_sessions": 12, "min_active_sessions": 2},
    ]}}
    assert _handle_pools_status(scope(cfg), {})["pool_count"] == 1


def test_is_read_only():
    """#197 also asks for adjust_worker_pool; this tool must not be it.

    Writing city.toml changes live concurrency for every agent in the city --
    and hand-editing that file broke `gc rig list` earlier in this campaign.
    Bundling a mutation into a reporting tool would hide that blast radius
    behind a name that reads as a query.
    """
    from mctl_core.mcp_server import TOOLS
    spec = next(t for t in TOOLS if t.name == "pools_status")
    assert not getattr(spec, "mutating", False)
