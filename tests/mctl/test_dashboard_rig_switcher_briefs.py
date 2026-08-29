"""The briefs manager lets the operator switch which rig's briefs they VIEW,
even on an instance launched pinned to one rig (`--rig`).

Taylor: "I can't seem to adjust my rig anymore when I'm using the briefs
dashboard." A briefs manager (`--dashboard briefs`) launched with `--rig X` is
`city_wide=False`, so the stack view rendered no rig switcher and `_rig_for`
ignored `?rig=`. That guard is right for MUTATIONS -- a verdict must never be
silently retargeted by a URL param -- but it also silenced the *view* switch,
which is a read-only choice of what to look at.

This file pins the split:

1. the switcher is offered on a pinned briefs manager, and `?rig=` changes
   which rig's briefs are READ (the bug);
2. switching the view does NOT retarget a mutation -- the write still lands in
   the rig the mutation explicitly named, never the one the URL was switched to
   (the safety invariant that must survive the fix);
3. a pinned CITY dashboard still shows no picker -- "pinned => no picker" stays
   correct for the city view (the control).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import multi_rig
from mctl_dashboard.app import Dashboard, Request
from mctl_dashboard.client import InProcessMcpClient


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def briefs_manager(tmp_path: Path, rig: str = "mathcity"):
    """A briefs manager (`--dashboard briefs`) pinned to one rig (`--rig`)."""
    fixture = multi_rig.build(tmp_path)
    inner = InProcessMcpClient(city=fixture.city_root, rig=rig, env=fixture.env)
    inner.server.cwd = fixture.city_root
    return Dashboard(inner, city_wide=False, rig=rig, dashboard="briefs"), fixture


def city_manager(tmp_path: Path, rig: str = "mathcity"):
    """A city dashboard (`--dashboard city`) pinned to one rig."""
    fixture = multi_rig.build(tmp_path)
    inner = InProcessMcpClient(city=fixture.city_root, rig=rig, env=fixture.env)
    inner.server.cwd = fixture.city_root
    return Dashboard(inner, city_wide=False, rig=rig, dashboard="city"), fixture


def beads(fixture: multi_rig.MultiRigCity, rig: str) -> list[dict]:
    path = fixture.beads_path(rig)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def bead(fixture: multi_rig.MultiRigCity, rig: str, bead_id: str) -> dict:
    return next(row for row in beads(fixture, rig) if row["id"] == bead_id)


def token_in(html: str) -> str:
    match = re.search(r'name="token" value="([^"]+)"', html)
    assert match, "the rendered preview carries no apply token"
    return match.group(1)


# --- 1. the bug: a pinned briefs manager can switch the viewed rig -----------


def test_a_pinned_briefs_manager_offers_a_rig_switcher(tmp_path: Path):
    dashboard, _ = briefs_manager(tmp_path)

    html = dashboard.handle(Request.get("/")).body

    assert 'data-region="rig-picker"' in html, (
        "a briefs manager pinned to one rig still lost the switcher -- the bug"
    )


def test_the_switcher_changes_which_rigs_briefs_are_shown(tmp_path: Path):
    dashboard, _ = briefs_manager(tmp_path, rig="mathcity")

    # Brief ids ride in the per-row hrefs (`/briefs/<id>?...`), so the raw body
    # is where a rig's briefs are provable -- the cells show slugs, not ids.
    default = dashboard.handle(Request.get("/")).body
    assert "/briefs/mc-open" in default, "the pinned rig's briefs are the default view"

    switched = dashboard.handle(Request.get("/", rig="gascity_packs")).body
    assert "/briefs/gs-open" in switched, "?rig= must switch which rig's briefs are read"
    assert "/briefs/mc-open" not in switched, (
        "the switched view must not still show the pinned rig"
    )


def test_an_unknown_rig_in_the_switcher_falls_back_to_the_pinned_rig(tmp_path: Path):
    """A bogus `?rig=` names no real store, so the view stays on the pinned rig
    rather than rendering an empty page under a fake label."""
    dashboard, _ = briefs_manager(tmp_path, rig="mathcity")

    body = dashboard.handle(Request.get("/", rig="not-a-rig")).body

    assert "/briefs/mc-open" in body, "an unknown rig must fall back to the pinned rig, not blank out"


def test_a_brief_opened_from_a_switched_view_resolves_in_the_viewed_rig(tmp_path: Path):
    """The switch is coherent end to end: a brief opened out of the switched
    stack resolves in the rig being viewed instead of 404-ing against the pinned
    one, and its adjudication panel names the viewed rig explicitly."""
    dashboard, _ = briefs_manager(tmp_path, rig="mathcity")

    detail = dashboard.handle(Request.get("/briefs/gs-open", rig="gascity_packs"))

    assert detail.status == 200, strip_tags(detail.body)
    assert 'name="rig" value="gascity_packs"' in detail.body, (
        "the panel must name the viewed rig explicitly, so a mutation carries its own target"
    )


# --- 2. safety: the switch is a VIEW switch, never a mutation retarget --------


def test_switching_the_view_does_not_retarget_a_mutation(tmp_path: Path):
    """The write lands in the rig the mutation names, never the switched view.

    The operator's URL is switched to `gascity_packs`; the adjudication still
    names `mathcity` (the pinned rig the panel emits). Even with the switched
    rig riding along on the confirm URL, the verdict must close `mc-open` in
    mathcity and leave `gs-open` in gascity_packs untouched.
    """
    dashboard, fixture = briefs_manager(tmp_path, rig="mathcity")

    previewed = dashboard.handle(
        Request.post(
            "/preview",
            operation="adjudicate",
            brief_id="mc-open",
            rig="mathcity",
            verdict="approve",
            reason="approved while viewing another rig",
        )
    )
    assert previewed.status == 200, strip_tags(previewed.body)

    # The confirm arrives with the switched view riding along in the query --
    # exactly the leak the guard exists to stop.
    applied = dashboard.handle(
        Request.post("/apply", token=token_in(previewed.body), rig="gascity_packs")
    )
    assert applied.status == 200, strip_tags(applied.body)

    assert bead(fixture, "mathcity", "mc-open")["status"] == "closed", (
        "the mutation must land in the rig it explicitly named"
    )
    assert bead(fixture, "gascity_packs", "gs-open")["status"] == "open", (
        "the switched-view rig must be untouched by the mutation"
    )


def test_the_mutation_path_still_ignores_a_rig_query_parameter(tmp_path: Path):
    """`_rig_for` -- the mutation router -- stays pinned whatever the URL says."""
    dashboard, _ = briefs_manager(tmp_path, rig="mathcity")

    assert dashboard._rig_for(Request.get("/apply", rig="gascity_packs")) == "mathcity"
    assert dashboard._rig_for(Request.post("/apply", rig="gascity_packs")) == "mathcity"


# --- 3. control: the pinned city dashboard is unchanged ----------------------


def test_a_pinned_city_dashboard_still_shows_no_switcher(tmp_path: Path):
    """"pinned => no picker" stays correct for the city view."""
    dashboard, _ = city_manager(tmp_path, rig="mathcity")

    landing = dashboard.handle(Request.get("/")).body
    stack = dashboard.handle(Request.get("/queue")).body

    assert 'data-region="rig-picker"' not in landing, "the city landing must show no picker"
    assert 'data-region="rig-picker"' not in stack, (
        "a city dashboard pinned to a rig shows no picker on the stack either"
    )
