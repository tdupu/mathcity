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


def test_the_page_says_what_an_UNLISTED_operation_does():
    """stick-dog's CONCERNS on #110, and it is the right attack.

    The page listed seven classified operations and said nothing about the
    eighth. A reader counts seven and concludes coverage is seven — that
    anything absent is unconstrained. **The opposite is true.** `classify()`
    for an operation not in the registry returns `gate: UNCLASSIFIED` with the
    reason "refused rather than permitted".

    So omission is the SAFE state, and a page that does not say so invites
    exactly the wrong inference from the number it leads with. The floor
    sentence is about escalation; this is about absence, and they are different
    mechanisms.
    """
    html = city_screen.blast_radius(
        {"registry_present": True,
         "operations": [{"operation": "briefs.create", "floor": "medium",
                         "reason": "x", "aspirational": False}],
         "awaiting_emitter": []}
    )
    low = html.lower()
    assert "refus" in low, "the page does not say what happens to an unlisted operation"
    assert "not in" in low or "absent" in low or "unlisted" in low


def test_the_unlisted_sentence_is_not_shown_when_the_registry_is_missing():
    """A missing registry is a different statement, and stacking both would
    imply the refusal behaviour is a reassurance about a file we could not
    read."""
    html = city_screen.blast_radius(
        {"registry_present": False, "operations": [], "awaiting_emitter": []}
    )
    assert "could not" in html.lower()


# ---------------------------------------------------------------------------
# queue (#113): six populations, next_up labeled a prediction, unreachable
# rendered as unknown rather than zero -- per-population, not just for the
# whole panel.
# ---------------------------------------------------------------------------


def test_a_failed_core_read_renders_the_whole_queue_as_unknown_not_zero():
    payload = {
        "state": "unreachable",
        "ready_unclaimed": None,
        "blocked": None,
        "tail": None,
        "starved": None,
        "deferred": None,
        "next_up": None,
        "next_up_is_prediction": True,
        "diagnostics": [
            {"code": "MQUE_QUEUE_UNREACHABLE", "message": "bd ready --explain unavailable: timeout"}
        ],
    }
    html = city_screen.queue(payload)
    low = html.lower()
    assert "unknown" in low
    assert "MQUE_QUEUE_UNREACHABLE" in html
    assert "0" not in html


def test_a_populated_queue_reports_each_population_and_labels_next_up_a_prediction():
    payload = {
        "state": "healthy",
        "ready_unclaimed": [{"bead_id": "mc-1", "title": "Ready work", "priority": 1}],
        "blocked": [
            {"bead_id": "mc-2", "title": "Blocked work", "blocked_on": "mc-9", "blocked_on_title": "The dependency"}
        ],
        "tail": [],
        "starved": [],
        "deferred": [{"bead_id": "mc-3", "title": "Parked", "until": "2026-09-01T00:00:00Z"}],
        "next_up": [{"bead_id": "mc-1", "title": "Ready work", "priority": 1}],
        "next_up_is_prediction": True,
        "diagnostics": [],
    }
    html = city_screen.queue(payload)
    assert "mc-1" in html
    assert "mc-2" in html
    assert "mc-9" in html, "blocked_on must render, not just the blocked bead itself"
    assert "2026-09-01T00:00:00Z" in html, "a deferred item's expiry must render"
    assert "predict" in html.lower(), "next_up must be explicitly labeled a prediction"


def test_a_genuinely_empty_queue_reports_zero_not_unknown():
    payload = {
        "state": "healthy",
        "ready_unclaimed": [],
        "blocked": [],
        "tail": [],
        "starved": [],
        "deferred": [],
        "next_up": [],
        "next_up_is_prediction": True,
        "diagnostics": [],
    }
    html = city_screen.queue(payload)
    assert "unknown" not in html.lower()
    assert "0" in html


def test_one_failed_population_renders_as_unknown_without_hiding_the_rest():
    """A partial failure (#113: `deferred` unreachable, everything else read
    fine) must not collapse the whole panel to "unknown" -- that would be
    exactly as dishonest in the other direction as printing zero."""
    payload = {
        "state": "degraded",
        "ready_unclaimed": [{"bead_id": "mc-1", "title": "Ready work", "priority": 1}],
        "blocked": [],
        "tail": [],
        "starved": [],
        "deferred": None,
        "next_up": [{"bead_id": "mc-1", "title": "Ready work", "priority": 1}],
        "next_up_is_prediction": True,
        "diagnostics": [
            {"code": "MQUE_DEFERRED_UNREACHABLE", "message": "bd list --deferred unavailable: timeout"}
        ],
    }
    html = city_screen.queue(payload)
    assert "mc-1" in html, "the successfully-read ready_unclaimed population must still render"
    assert "MQUE_DEFERRED_UNREACHABLE" in html
    assert "unknown" in html.lower()


# ---------------------------------------------------------------------------
# costs (#118): token totals + worker-hours + the meta-work ratio with its
# numerator/denominator, unpriced_count stated explicitly, unreachable
# rendered as unknown rather than zero.
# ---------------------------------------------------------------------------


def test_an_unreachable_costs_read_renders_as_unknown_not_zero():
    payload = {
        "state": "unreachable",
        "total_tokens": None,
        "worker_hours": None,
        "unpriced_count": None,
        "unclassified_tokens": None,
        "meta_work_ratio": {"numerator": None, "denominator": None, "ratio": None},
        "windows": None,
        "diagnostics": [
            {"code": "MCOS_USAGE_UNREACHABLE", "message": "usage facts unavailable: no such file"}
        ],
    }
    html = city_screen.costs(payload)
    low = html.lower()
    assert "unknown" in low
    assert "MCOS_USAGE_UNREACHABLE" in html
    assert "0" not in html


def test_a_populated_costs_summary_reports_totals_and_the_ratio_with_its_parts():
    payload = {
        "state": "healthy",
        "total_tokens": 300,
        "worker_hours": 2.5,
        "unpriced_count": 3,
        "unclassified_tokens": 10,
        "meta_work_ratio": {"numerator": 200, "denominator": 100, "ratio": 2.0},
        "windows": [
            {
                "window": "2026-08-20",
                "total_tokens": 300,
                "meta_tokens": 200,
                "math_tokens": 100,
                "unclassified_tokens": 10,
                "worker_hours": 2.5,
                "unpriced_count": 3,
                "meta_work_ratio": 2.0,
            }
        ],
        "diagnostics": [],
    }
    html = city_screen.costs(payload)
    assert "300" in html, "total tokens must render"
    assert "2.5" in html, "worker-hours must render beside the tokens"
    assert "200" in html and "100" in html, "the ratio's numerator and denominator must both render"
    assert "3" in html, "unpriced_count must be stated explicitly"
    assert "2026-08-20" in html, "the per-window series must render for the trend"


def test_a_genuinely_empty_costs_summary_reports_zero_not_unknown():
    payload = {
        "state": "healthy",
        "total_tokens": 0,
        "worker_hours": 0.0,
        "unpriced_count": 0,
        "unclassified_tokens": 0,
        "meta_work_ratio": {"numerator": 0, "denominator": 0, "ratio": None},
        "windows": [],
        "diagnostics": [],
    }
    html = city_screen.costs(payload)
    assert "unknown" not in html.lower()
    assert "0" in html


def test_unpriced_count_never_renders_as_folded_into_the_token_total():
    """#118 honesty specifics: unpriced runs are a separate, explicit count --
    never valued at zero and never silently merged into total_tokens."""
    payload = {
        "state": "healthy",
        "total_tokens": 500,
        "worker_hours": 1.0,
        "unpriced_count": 7,
        "unclassified_tokens": 0,
        "meta_work_ratio": {"numerator": 500, "denominator": 0, "ratio": None},
        "windows": [],
        "diagnostics": [],
    }
    html = city_screen.costs(payload)
    assert "7" in html
    assert "unpriced" in html.lower()


# ---------------------------------------------------------------------------
# worktrees (#120): inventory keyed by path, created_by/step/molecule render
# `-` when unrecorded, is_orphan/is_registered stay separate, unreachable
# renders as unknown rather than empty.
# ---------------------------------------------------------------------------


def test_an_unreachable_worktrees_read_renders_as_unknown_not_zero():
    payload = {
        "state": "unreachable",
        "total": None,
        "orphans": None,
        "harvestable_count": None,
        "worktrees": None,
        "diagnostics": [
            {"code": "MWKT_WORKTREES_UNREACHABLE", "message": "rig roster unavailable: timeout"}
        ],
    }
    html = city_screen.worktrees(payload)
    low = html.lower()
    assert "unknown" in low
    assert "MWKT_WORKTREES_UNREACHABLE" in html
    assert "0" not in html


def test_a_genuinely_empty_worktrees_read_reports_zero_not_unknown():
    payload = {
        "state": "healthy",
        "total": 0,
        "orphans": None,
        "harvestable_count": 0,
        "worktrees": [],
        "diagnostics": [],
    }
    html = city_screen.worktrees(payload)
    assert "unknown" not in html.lower()
    assert "0" in html


def test_a_populated_worktrees_table_renders_unrecorded_distinctly_from_a_real_value():
    payload = {
        "state": "healthy",
        "total": 2,
        "orphans": None,
        "harvestable_count": 1,
        "worktrees": [
            {
                "path": "/rigs/mathcity/w1",
                "rig": "mathcity",
                "branch": "dash-city",
                "molecule": "unrecorded",
                "created_by": "unrecorded",
                "step": "unrecorded",
                "merged": False,
                "age_seconds": 86400.0,
                "size_bytes": 2048,
                "is_orphan": None,
                "is_registered": True,
                "harvestable": False,
                "commits": 3,
                "url": "file:///rigs/mathcity/w1",
            },
            {
                "path": "/rigs/mathcity/gone",
                "rig": "mathcity",
                "branch": None,
                "molecule": "unrecorded",
                "created_by": "molecule-runner",
                "step": "unrecorded",
                "merged": None,
                "age_seconds": None,
                "size_bytes": None,
                "is_orphan": None,
                "is_registered": True,
                "harvestable": True,
                "commits": None,
                "url": "file:///rigs/mathcity/gone",
            },
        ],
        "diagnostics": [
            {"code": "MWKT_ORPHAN_UNDERIVABLE", "message": "is_orphan is null for every row"},
            {"code": "MWKT_CREATED_BY_UNRECORDED", "message": "created_by/step/molecule are unrecorded"},
        ],
    }
    html = city_screen.worktrees(payload)
    assert "/rigs/mathcity/w1" in html
    assert "/rigs/mathcity/gone" in html
    assert "molecule-runner" in html, "a real recorded created_by must render as itself"
    # The unrecorded sentinel renders distinctly (an em/en-dash placeholder),
    # never as the literal word the row carries and never as a blank cell.
    assert "—" in html or "&mdash;" in html or "&#8212;" in html
    table = html[html.index("<table") : html.index("</table>")]
    assert "unrecorded" not in table.lower(), (
        "the raw sentinel string must not leak into a table cell (diagnostic codes below the "
        "table may legitimately contain the word, e.g. MWKT_CREATED_BY_UNRECORDED)"
    )


def test_harvestable_and_registered_and_orphan_render_as_separate_signals():
    payload = {
        "state": "healthy",
        "total": 1,
        "orphans": None,
        "harvestable_count": 1,
        "worktrees": [
            {
                "path": "/rigs/mathcity/gone",
                "rig": "mathcity",
                "branch": None,
                "molecule": "unrecorded",
                "created_by": "unrecorded",
                "step": "unrecorded",
                "merged": None,
                "age_seconds": None,
                "size_bytes": None,
                "is_orphan": None,
                "is_registered": True,
                "harvestable": True,
                "commits": None,
                "url": None,
            }
        ],
        "diagnostics": [],
    }
    html = city_screen.worktrees(payload)
    assert "harvestable" in html.lower()
    assert "registered" in html.lower()
