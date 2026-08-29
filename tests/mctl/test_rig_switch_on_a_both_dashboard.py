"""A pinned `both` dashboard offered no way to change rigs at all.

Reported against the live instance 2026-08-29 (pid 76065, `rig=mathcity`,
`dashboard=both`, serving `c8e8241`): a pinned `both` instance still offered no
way to change rigs.

TWO GATES, AND A PINNED `both` CONFIGURATION FAILED BOTH:

    app.py:517   the view switch    `if self._is_briefs_manager and not self.city_wide`
    app.py:1135  the filter field   `... if self.city_wide else ""`

Pinned to a rig means `city_wide` is False, so the filter field never renders.
`_is_briefs_manager` was `self.dashboard == "briefs"`, so a `both` instance
failed that too. Neither branch fires; the control does not exist.

**`both` is the DEFAULT selector**, which made the out-of-the-box deployment the
broken one. And a `both` instance serves `/queue` — it *is* the briefs manager
on those routes — so denying it the briefs-manager affordance was simply wrong.

WHAT MUST NOT MOVE. `_rig_for` is the WRITE router and is deliberately blind to
`?rig=` when pinned, so a URL parameter can never retarget a verdict or a
dispatch. That is why widening the VIEW is safe, and the last two tests here
pin it: the fix must not have touched the write path. A version that made
`_rig_for` follow `?rig=` would "fix" this bug by introducing a far worse one.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_dashboard.app import Dashboard


class _Req:
    def __init__(self, query=None, form=None):
        self.query = query or {}
        self.form = form or {}


def _dash(dashboard, *, rig="mathcity", city_wide=False, rigs=("mathcity", "hecke", "hq")):
    d = Dashboard.__new__(Dashboard)
    d.dashboard = dashboard
    d.rig = rig
    d.city_wide = city_wide
    d._rig_ids = lambda: tuple(rigs)  # type: ignore[method-assign]
    return d


# --- the reported defect ---------------------------------------------------


def test_a_both_dashboard_is_a_briefs_manager() -> None:
    """`both` serves /queue, so it IS the briefs manager on those routes."""
    assert _dash("both")._is_briefs_manager is True


def test_a_pinned_both_dashboard_can_switch_the_viewed_rig() -> None:
    """The exact reported case: pinned, dashboard=both, wants another rig."""
    d = _dash("both", rig="mathcity")
    assert d._view_rig(_Req(query={"rig": "hecke"})) == "hecke"


def test_the_briefs_dashboard_still_switches() -> None:
    """Unchanged behaviour — this is what worked before the fix."""
    d = _dash("briefs", rig="mathcity")
    assert d._view_rig(_Req(query={"rig": "hecke"})) == "hecke"


def test_a_city_dashboard_still_refuses_to_switch_when_pinned() -> None:
    """Deliberate and unchanged: on the CITY dashboard a pinned deployment made
    a choice, and a picker there would imply otherwise."""
    d = _dash("city", rig="mathcity")
    assert d._is_briefs_manager is False
    assert d._view_rig(_Req(query={"rig": "hecke"})) == "mathcity"


# --- the guards on what a switch may do ------------------------------------


def test_an_unknown_rig_is_ignored() -> None:
    """A `?rig=` naming a rig that is not registered must not be honoured."""
    d = _dash("both", rig="mathcity")
    assert d._view_rig(_Req(query={"rig": "not-a-rig"})) == "mathcity"


def test_no_rig_param_falls_back_to_the_pinned_rig() -> None:
    d = _dash("both", rig="mathcity")
    assert d._view_rig(_Req()) == "mathcity"


# --- the write path must NOT have moved ------------------------------------


def test_the_write_router_still_ignores_the_url_on_a_pinned_instance() -> None:
    """THE load-bearing test. `_rig_for` routes MUTATIONS. If widening the view
    also widened this, a `?rig=` could retarget a verdict — a far worse bug than
    the one being fixed."""
    d = _dash("both", rig="mathcity")
    assert d._rig_for(_Req(query={"rig": "hecke"})) == "mathcity"


def test_the_write_router_ignores_a_form_rig_too() -> None:
    """POSTed forms carry `rig`; the same guard has to hold there."""
    d = _dash("both", rig="mathcity")
    assert d._rig_for(_Req(form={"rig": "hecke"})) == "mathcity"


def test_view_and_write_may_legitimately_disagree() -> None:
    """Looking at hecke while writes still route to the pinned mathcity is the
    intended state, not a bug — it is what makes the switch safe."""
    d = _dash("both", rig="mathcity")
    request = _Req(query={"rig": "hecke"})
    assert d._view_rig(request) == "hecke"
    assert d._rig_for(request) == "mathcity"


@pytest.mark.parametrize("dashboard", ["briefs", "both"])
def test_a_city_wide_instance_leaves_routing_to_the_url(dashboard) -> None:
    """When not pinned, `_rig_for` reads the URL — unchanged by this fix."""
    d = _dash(dashboard, rig=None, city_wide=True)
    assert d._rig_for(_Req(query={"rig": "hecke"})) == "hecke"
