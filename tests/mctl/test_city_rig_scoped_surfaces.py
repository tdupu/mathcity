"""`/city` must not fan out its rig-scoped surfaces with no rig chosen.

Measured on the live dashboard at `f103989` (pid 82656, port 8471,
`dashboard_status` -> `stale: false`), fetching the served page rather than
reading the source:

    $ curl -s http://127.0.0.1:8471/city | grep -o 'data-region="city[^"]*"'
    data-region="city-blast-radius"
    data-region="city-failed-costs_summary"      <- FATAL
    data-region="city-failed-queue_status"       <- FATAL
    data-region="city-fleet"
    data-region="city-gates"
    data-region="city-health"
    data-region="city-unwired-events_list"
    data-region="city-worktrees"

Both failures carried the same diagnostic:

    FATAL MCTL_CONTEXT_RIG_REQUIRED
    The city has multiple registered rigs and none was selected.

`queue_status` and `costs_summary` are the only two tools in the `/city`
fan-out without `CITY_SCOPE` (`mctl_core/mcp_server.py`), so with no rig named
that FATAL was the *only* answer they could return -- a statement about the
request rendered in the slot where a measurement about the city belongs. The
control is that `/city?rig=mathcity` rendered both panels (`city-queue`,
`city-costs`) on the same commit, so the panels themselves were never broken.

`_molecules` already answers this shape with a rig picker instead of a
guaranteed failure. This route did not.

**How these tests could fail:** the first asserts a tool is NOT called, so an
implementation that fans all seven out fails it -- which is what the live
measurement above shows the pre-fix code doing. The second and third assert
positively that the five city-scoped panels and the picker are present, so an
over-broad fix that deferred everything, or dropped the deferred panels
silently, fails them.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.app import Dashboard, Request
from mctl_dashboard.screens import city as city_screen

#: The two tools in the `/city` fan-out that carry no `CITY_SCOPE`.
RIG_SCOPED = {"queue_status", "costs_summary"}

#: The five that do, and must keep rendering with no rig chosen.
CITY_SCOPED = {
    "fleet_sessions",
    "city_health",
    "gates_status",
    "blast_radius_registry",
    "worktrees_status",
}


class _RecordingClient:
    """Records every tool called and answers with an empty-but-valid payload."""

    def __init__(self, calls: list[str] | None = None):
        # Shared across clones: `fan_out` hands work to clones, so a per-instance
        # list would record only this object's share.
        self.calls: list[str] = [] if calls is None else calls

    def call(self, name, arguments=None):
        self.calls.append(name)

        class _R:
            payload = {
                "slots": [],
                "diagnostics": [],
                "data_plane": "healthy",
                "per_rig": [],
                "gates": [],
                "gates_readable": True,
                "rows": [],
                "rigs": [{"rig_id": "mathcity"}, {"rig_id": "hecke"}],
                "worktrees": [],
                "populations": [],
            }

        return _R()

    def clone(self):
        return _RecordingClient(self.calls)

    def list_tools(self):
        return []


def _render(rig: str | None) -> tuple[str, list[str]]:
    client = _RecordingClient()
    # `Request.get` takes the query as kwargs -- a "?rig=..." baked into the
    # path string is part of the path and silently selects no rig, which is the
    # no-rig case wearing the rig case's name.
    request = Request.get("/city") if rig is None else Request.get("/city", rig=rig)
    response = Dashboard(client, city_wide=True, rig=None).handle(request)
    return response.body, client.calls


def test_rig_scoped_surfaces_are_not_called_without_a_rig():
    """The defect: a call whose only possible answer is a request error."""
    _, calls = _render(None)
    called = RIG_SCOPED & set(calls)
    assert not called, (
        f"{sorted(called)} were called with no rig on a city-wide dashboard. "
        "Neither carries CITY_SCOPE, so the only answer either can return is "
        "FATAL MCTL_CONTEXT_RIG_REQUIRED -- rendered as a failed panel."
    )


def test_the_five_city_scoped_surfaces_still_render_without_a_rig():
    """The guard: deferring two must not cost the other five."""
    body, calls = _render(None)
    missing = CITY_SCOPED - set(calls)
    assert not missing, f"{sorted(missing)} stopped being read: {sorted(calls)}"
    for region in ("city-fleet", "city-health", "city-gates", "city-blast-radius"):
        assert f'data-region="{region}"' in body, f"{region} did not render"


def test_a_deferred_surface_renders_a_named_picker_not_an_absence():
    """An omitted panel reads as 'the city has none of these', which is false."""
    body, _ = _render(None)
    for tool in sorted(RIG_SCOPED):
        assert f'data-region="city-needs-rig-{tool}"' in body, (
            f"{tool} was deferred and then dropped -- an absent panel is not an "
            "honest answer, it is a quieter wrong one."
        )
    assert 'action="/city"' in body, "the picker must post back to /city"


def test_naming_a_rig_calls_both_rig_scoped_surfaces():
    """The control: the panels were never broken, only unreachable."""
    _, calls = _render("mathcity")
    missing = RIG_SCOPED - set(calls)
    assert not missing, f"{sorted(missing)} not called even with a rig named"


def test_rig_scoped_constant_matches_the_tools_the_route_defers():
    """Guards the constant against drift from the mcp_server scope table."""
    assert set(city_screen.RIG_SCOPED) == RIG_SCOPED
