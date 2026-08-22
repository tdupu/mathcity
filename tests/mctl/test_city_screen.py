"""The city dashboard's first screens, and the one property they must not break.

Five city-dashboard slices were merged and closed while rendering nowhere
(`#153`). This is the front end that makes any of them visible. Two of the
five are reachable today -- `fleet_sessions` and `city_health` have MCP tools.
The other three have core modules and no tool, so no page can call them; those
render as a refusal that names the missing tool rather than as an empty panel.

**The property under test is P6.2: a probe that could not run must not render
as a measurement.** This is not hypothetical here -- it is the live condition.
Right now `gc` does not answer within 30s, so:

    fleet_sessions  ->  slots: []          + MCTL_FLEET_STATUS_PROBE_FAILED
    city_health     ->  data_plane: "unreachable"

A naive render shows "0 agents" and a dead city. Both are false: the fleet size
is **unknown**, and the city may be entirely healthy behind a probe that timed
out. An operator who reads "0 agents" goes looking for a fleet that never
stopped running.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.screens import city as city_screen


# ---------------------------------------------------------------------------
# P6.2 -- unknown is not zero
# ---------------------------------------------------------------------------


def test_a_failed_fleet_probe_does_not_render_as_zero_agents():
    payload = {
        "slots": [],
        "diagnostics": [
            {"code": "MCTL_FLEET_STATUS_PROBE_FAILED", "message": "gc did not answer within 30.0s"}
        ],
    }
    html = city_screen.fleet(payload)
    assert "unknown" in html.lower()
    assert "MCTL_FLEET_STATUS_PROBE_FAILED" in html


def test_a_genuinely_empty_fleet_is_allowed_to_say_zero():
    """The mirror. If the probe ANSWERED and there are no slots, zero is a
    measurement and must be reported as one -- a diagnostic that cannot pass
    is as bad as a check that cannot fail."""
    html = city_screen.fleet({"slots": [], "diagnostics": []})
    assert "0" in html
    assert "unknown" not in html.lower()


def test_a_populated_fleet_reports_its_slots():
    payload = {"slots": [{"agent": "a", "state": "occupied"}, {"agent": "b", "state": "empty"}], "diagnostics": []}
    html = city_screen.fleet(payload)
    assert "2" in html


def test_an_unreachable_data_plane_is_not_rendered_as_unhealthy():
    """"unreachable" means we could not ask. It does NOT mean "down"."""
    html = city_screen.health({"data_plane": "unreachable", "per_rig": [], "diagnostics": []})
    low = html.lower()
    assert "unreachable" in low
    assert "could not" in low or "unknown" in low


def test_a_healthy_data_plane_says_so():
    html = city_screen.health({"data_plane": "healthy", "per_rig": [], "diagnostics": []})
    assert "healthy" in html.lower()


# ---------------------------------------------------------------------------
# the unreachable surfaces name what is missing
# ---------------------------------------------------------------------------


def test_an_unwired_surface_names_its_missing_tool_and_module():
    """Not a placeholder that looks like loading. The gap must be legible
    from the screen, not from a grep."""
    html = city_screen.unwired("gates_status", module="mctl_core/gates.py", issue=119)
    assert "gates_status" in html
    assert "mctl_core/gates.py" in html
    assert "119" in html


def test_an_unwired_surface_does_not_pretend_to_be_empty():
    html = city_screen.unwired("gates_status", module="mctl_core/gates.py", issue=119)
    low = html.lower()
    assert "no data" not in low and "none found" not in low


# ---------------------------------------------------------------------------
# gates: now reachable, and the readable/empty distinction must survive
# ---------------------------------------------------------------------------


def test_unreadable_gates_are_not_rendered_as_no_gates():
    """The distinction `gates.py` protects, carried all the way to the pixel.

    An empty list means "this city defines no gates" OR "we could not look".
    A screen that prints "0 gates" for both destroys a fact the core module
    went out of its way to preserve.
    """
    html = city_screen.gates({"gates": [], "gates_readable": False, "diagnostics": []})
    low = html.lower()
    assert "could not" in low or "unknown" in low
    assert "0 gates" not in low


def test_a_city_that_genuinely_defines_no_gates_says_zero():
    html = city_screen.gates({"gates": [], "gates_readable": True, "diagnostics": []})
    assert "no gates" in html.lower()
    assert "could not" not in html.lower()


def test_gates_are_listed_by_id():
    html = city_screen.gates(
        {"gates": [{"gate_id": "latex-gate", "checks": 1}], "gates_readable": True, "diagnostics": []}
    )
    assert "latex-gate" in html


def test_an_unknown_data_plane_is_not_rendered_as_unreachable():
    """#159's fix reaching the page.

    The screen used to carry prose compensating for the core's conflation --
    "unreachable is not unhealthy" -- because `unreachable` was the only word
    available for "we could not ask". The core now says `unknown`, so the page
    can state the fact instead of hedging around a wrong one.
    """
    html = city_screen.health({"data_plane": "unknown", "per_rig": [], "diagnostics": []})
    low = html.lower()
    # Assert the MEANING. An earlier draft of this checked for the literal word
    # "unknown" and failed against a panel that says "was not established" --
    # which is the same fact in better English. Vocabulary assertions are how a
    # test ends up disagreeing with correct code.
    assert "not established" in low or "did not answer" in low
    assert "about the probe" in low
    # And it must not borrow the word for the state that IS a measurement.
    assert "unreachable" not in low


def test_a_genuinely_unreachable_data_plane_still_says_so():
    """The measurement must survive: when the probe answered and the answer
    was that Dolt is down, that is a real fact and must not be softened into
    'unknown'."""
    html = city_screen.health({"data_plane": "unreachable", "per_rig": [], "diagnostics": []})
    low = html.lower()
    assert "unreachable" in low
    # The first version of this test checked only that the word appeared, and
    # passed while the panel still said "unreachable is not unhealthy" -- prose
    # written when `unreachable` meant "could not ask", which #159 changed.
    # Assert the MEANING, not the vocabulary.
    assert "measurement" in low
    assert "is not" not in low.split("distinct from")[0].replace("is not a missing one", "")

# ---------------------------------------------------------------------------
# blast radius: the registry, with presence kept distinct from emptiness
# ---------------------------------------------------------------------------


def test_a_missing_registry_is_not_rendered_as_nothing_dangerous():
    html = city_screen.blast_radius(
        {"registry_present": False, "operations": [], "awaiting_emitter": []}
    )
    low = html.lower()
    assert "could not" in low or "not found" in low
    assert "no operations are classified" not in low


def test_an_empty_but_present_registry_says_the_city_classifies_none():
    html = city_screen.blast_radius(
        {"registry_present": True, "operations": [], "awaiting_emitter": []}
    )
    assert "classif" in html.lower()
    assert "could not" not in html.lower()


def test_operations_render_with_their_floor():
    html = city_screen.blast_radius(
        {"registry_present": True,
         "operations": [{"operation": "briefs.adjudicate", "floor": "medium",
                         "reason": "one-way door", "aspirational": False}],
         "awaiting_emitter": []}
    )
    assert "briefs.adjudicate" in html and "medium" in html


def test_awaiting_emitter_is_not_called_an_orphan():
    """Its own docstring insists on this: "N entries await an emitter" is a
    fact; "N orphans" is a warning about the wrong thing."""
    html = city_screen.blast_radius(
        {"registry_present": True, "operations": [],
         "awaiting_emitter": ["rig.suspend"]}
    )
    assert "rig.suspend" in html
    assert "orphan" not in html.lower()
