"""Structural tests for the City dashboard visual port (#68 / #153).

The city-operations and molecules screens were merged functionally complete
(`queue_status`, `costs_summary`, `worktrees_status`, `/molecules` all render)
but visually bare: they emitted `reason-list` / `muted` / `note` / `kv`
classes the stylesheet never defined, and painted every STATE as plain mono
text where the design prototype paints stoplight pills. This file covers the
visual pieces that fail *silently* in a browser if they regress:

* the shared stoplight pill family is generated from the one `STOP` scale, so
  a tone can never drift from the color the design assigns it (the prototype's
  `TONE` map IS `theme.STOP`);
* the city screens' four previously-unstyled classes are now defined in the
  shared sheet, so the design language actually reaches them;
* a probe that could not run wears NO pass/fail stoplight -- P6.2 carried to
  the pixel: an `unknown` data plane is neutral, never green and never red;
* a measurement that the data plane is down DOES wear the error stoplight;
* the fleet capacity strip has exactly one cell per slot in the payload (F33 --
  derived from the list, never an authored count) and vanishes when the probe
  did not answer (no fabricated cells for an unknown fleet);
* the worktree and molecule tables carry the shared `.ntdata` metric class;
* the city page shell still embeds the fonts and the FIXTURES badge, so the
  #68 DRIFT flag is present on the city surface too.

Kept out of `test_dashboard_briefs_visual.py` so the two surfaces move
independently.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))


# --------------------------------------------------------------------------
# the stoplight pill family is single-sourced from STOP
# --------------------------------------------------------------------------


def test_every_stop_tone_has_a_pill_rule_colored_from_its_own_scale():
    """A pill's border is the STOP edge for that tone -- no new hex literal.

    The prototype's `TONE` map and `theme.STOP` are the same five entries; the
    pill CSS must be generated from STOP so retuning a tone can never leave a
    pill painted the old color.
    """
    from mctl_dashboard import theme

    assert ".mc-stop " in theme.STYLESHEET or ".mc-stop{" in theme.STYLESHEET
    for tone, colors in theme.STOP.items():
        assert f".mc-stop-{tone}" in theme.STYLESHEET
        # The edge color for the tone appears in the sheet (the pill border),
        # and it came from STOP, not from a literal typed into the CSS.
        assert colors["edge"] in theme.STYLESHEET


def test_the_previously_unstyled_city_classes_are_now_defined():
    from mctl_dashboard import theme

    for selector in ("ul.reason-list", ".muted", ".note", "dl.kv"):
        assert selector in theme.STYLESHEET, selector


# --------------------------------------------------------------------------
# P6.2 at the pixel: unknown wears no pass/fail stoplight
# --------------------------------------------------------------------------


def test_a_healthy_data_plane_carries_the_go_stoplight():
    from mctl_dashboard.screens import city

    html = city.health({"data_plane": "healthy", "per_rig": [], "diagnostics": []})
    assert "mc-stop-go" in html
    assert "healthy" in html.lower()


def test_an_unknown_data_plane_wears_no_pass_or_fail_stoplight():
    """The probe did not answer. That is not green and it is not red."""
    from mctl_dashboard.screens import city

    html = city.health({"data_plane": "unknown", "per_rig": [], "diagnostics": []})
    assert "mc-stop-go" not in html
    assert "mc-stop-error" not in html


def test_an_unreachable_data_plane_is_a_measurement_and_wears_the_error_stoplight():
    """The probe answered and reported the server down -- a real failure."""
    from mctl_dashboard.screens import city

    html = city.health({"data_plane": "unreachable", "per_rig": [], "diagnostics": []})
    assert "mc-stop-error" in html
    assert "unreachable" in html.lower()


def test_per_rig_states_carry_stoplights_but_unknown_stays_neutral():
    from mctl_dashboard.screens import city

    # data_plane `unknown` paints no pill of its own, so the pills counted below
    # are exactly the per-rig ones -- one go (reachable), one error
    # (unreachable), and the unknown rig painted as neither.
    html = city.health(
        {
            "data_plane": "unknown",
            "per_rig": [
                {"rig_id": "hecke", "state": "reachable"},
                {"rig_id": "lmfdb", "state": "unreachable", "reason": "dolt down"},
                {"rig_id": "diffval", "state": "unknown"},
            ],
            "diagnostics": [],
        }
    )
    assert "mc-stop-go" in html  # reachable rig
    assert "mc-stop-error" in html  # unreachable rig
    # the unknown rig must not be painted as either
    assert html.count("mc-stop-go") == 1
    assert html.count("mc-stop-error") == 1


# --------------------------------------------------------------------------
# fleet capacity strip: F33 (one cell per slot) + honesty (none when unknown)
# --------------------------------------------------------------------------


def test_the_capacity_strip_has_one_cell_per_slot_from_the_payload():
    from mctl_dashboard.screens import city

    payload = {
        "slots": [
            {"state": "occupied"},
            {"state": "empty"},
            {"state": "occupied"},
        ],
        "diagnostics": [],
    }
    html = city.fleet(payload)
    assert html.count('class="mc-cap ') == 3  # one cell per slot, from len(slots)
    assert html.count("mc-cap-occupied") == 2
    assert html.count("mc-cap-free") == 1


def test_a_failed_fleet_probe_draws_no_capacity_cells():
    """An unknown fleet must not fabricate a capacity strip of any width."""
    from mctl_dashboard.screens import city

    html = city.fleet(
        {"slots": [], "diagnostics": [{"code": "MCTL_FLEET_STATUS_PROBE_FAILED"}]}
    )
    assert "mc-cap" not in html
    assert "unknown" in html.lower()


# --------------------------------------------------------------------------
# molecule is_complete stoplight (P6.2 mirror: unknown is not a failure)
# --------------------------------------------------------------------------


def test_a_complete_step_is_go_and_an_incomplete_step_is_warn():
    from mctl_dashboard.screens import molecules

    assert "mc-stop-go" in molecules._is_complete_cell({"is_complete": "complete"})
    assert "mc-stop-warn" in molecules._is_complete_cell({"is_complete": "incomplete"})


def test_an_undeclared_step_completeness_wears_no_pass_or_fail_stoplight():
    from mctl_dashboard.screens import molecules

    cell = molecules._is_complete_cell({"is_complete": "unknown"})
    assert "mc-stop-go" not in cell
    assert "mc-stop-error" not in cell
    assert "unknown" in cell.lower()


# --------------------------------------------------------------------------
# shared metric tables reach the city surface
# --------------------------------------------------------------------------


def test_the_worktree_table_uses_the_shared_metric_table_class():
    from mctl_dashboard.screens import city

    html = city.worktrees(
        {"state": "ok", "total": 1, "worktrees": [{"path": "/x", "rig": "hecke"}]}
    )
    assert 'class="ntdata"' in html


def test_the_molecule_roster_table_uses_the_shared_metric_table_class():
    from mctl_dashboard.screens import molecules

    html = molecules.molecules_list(
        {"molecules": [{"id": "m1", "formula": "f", "status": "open"}]}
    )
    assert 'class="ntdata"' in html


# --------------------------------------------------------------------------
# the #68 DRIFT flag: the city shell embeds fonts and the FIXTURES badge
# --------------------------------------------------------------------------


def test_the_city_page_shell_embeds_fonts_and_the_fixtures_badge():
    from mctl_dashboard import render
    from mctl_dashboard.provenance import DataProvenance
    from mctl_dashboard.screens import city

    section = city.health({"data_plane": "healthy", "per_rig": [], "diagnostics": []})
    page = render.page(
        "City",
        "/city",
        [section],
        provenance=DataProvenance(fixtures=(("hecke", "/x/fix.json"),)),
    )
    # fonts travel inside the page, not over a /fonts/ request
    assert "data:font/woff2;base64," in page
    assert "url('/fonts/" not in page
    # the FIXTURES badge the DRIFT demands is present on the city surface too
    assert "FIXTURES" in page and "NOT LIVE DATA" in page
    assert 'data-region="data-provenance"' in page
    # and the stoplight the section painted survives into the shell
    assert "mc-stop-go" in page
