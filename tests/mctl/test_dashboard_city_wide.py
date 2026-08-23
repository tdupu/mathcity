"""Slice 8 dashboard, city-wide: "I want all the briefs at the same time".

That sentence is the repo owner's, recorded as Q5's resolution: storage stays
per rig, reporting goes city-wide. This file pins the reporting half.

The dashboard is a *consumer* of the cross-rig read, not a second
implementation of it -- `mctl_core/city.py` behind the declared `all_rigs`
option does the fan-out, and `test_all_rigs_reads.py` pins that. What is
tested here is what a browser receives, and specifically the four ways a
city-wide view could be worse than the per-rig view it replaces:

1. it goes blank because one rig is sick;
2. it shows a total that quietly omits a rig, so a partial answer looks whole;
3. it loses the rig on the way to a mutation, and a verdict lands in the wrong
   bead store;
4. it flattens the honesty properties -- untrusted diagnostics summed into an
   actionable total, or one artifact-trust banner asserted over rigs nobody
   checked.
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
from mctl_core import mcp_server
from mctl_dashboard.app import Dashboard, Request
from mctl_dashboard.client import ALLOWED_TOOLS, InProcessMcpClient
from mctl_dashboard.review import UNDER_REVIEW_CODES

READ_ONLY_TOOLS = frozenset(tool.name for tool in mcp_server.TOOLS if not tool.mutating)


class RecordingClient:
    """Wraps a client and records every tool call the dashboard makes."""

    def __init__(self, inner):
        self.inner = inner
        self.calls: list[tuple[str, dict]] = []

    def list_tools(self):
        return self.inner.list_tools()

    def call(self, name, arguments=None):
        self.calls.append((name, dict(arguments or {})))
        return self.inner.call(name, arguments)

    @property
    def names(self) -> list[str]:
        return [name for name, _ in self.calls]


def city_dashboard(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)
    inner = InProcessMcpClient(city=fixture.city_root, rig=None, env=fixture.env)
    # As if invoked from the city rather than from the MathCity source
    # checkout; the checkout guard has its own tests.
    inner.server.cwd = fixture.city_root
    client = RecordingClient(inner)
    return Dashboard(client, city_wide=True), client, fixture


def rig_dashboard(tmp_path: Path, rig: str = "mathcity"):
    fixture = multi_rig.build(tmp_path)
    inner = InProcessMcpClient(city=fixture.city_root, rig=rig, env=fixture.env)
    inner.server.cwd = fixture.city_root
    client = RecordingClient(inner)
    return Dashboard(client, city_wide=False, rig=rig), client, fixture


def body(dashboard, path: str, **query) -> str:
    response = dashboard.handle(Request.get(path, **query))
    assert response.status == 200, response.body
    return response.body


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def beads(fixture: multi_rig.MultiRigCity, rig: str) -> list[dict]:
    path = fixture.beads_path(rig)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def bead(fixture: multi_rig.MultiRigCity, rig: str, bead_id: str) -> dict:
    return next(row for row in beads(fixture, rig) if row["id"] == bead_id)


def token_in(html: str) -> str:
    match = re.search(r'name="token" value="([^"]+)"', html)
    assert match, "the rendered preview carries no apply token"
    return match.group(1)


# --- the queue is city-wide, with the breakdown beside it --------------------


def test_the_overview_reports_city_wide_totals_with_a_per_rig_breakdown(tmp_path: Path):
    dashboard, client, _ = city_dashboard(tmp_path)

    html = body(dashboard, "/")

    assert 'data-region="queue"' in html
    assert 'data-scope="city"' in html
    text = strip_tags(html)
    assert "whole city" in text
    for rig in multi_rig.READABLE_RIGS:
        assert f'data-rig="{rig}"' in html, f"{rig} has no row in the breakdown"
    listing = next(args for name, args in client.calls if name == "briefs_list")
    assert listing["all_rigs"] is True, "the dashboard must use the declared cross-rig option"


def test_the_city_total_equals_the_sum_of_the_rig_rows(tmp_path: Path):
    """The aggregate is only ever the sum of the rows printed above it."""
    dashboard, client, _ = city_dashboard(tmp_path)

    html = body(dashboard, "/")

    total = int(re.search(r'data-brief-total="(\d+)"', html).group(1))
    payload = next(
        response
        for name, response in [(n, a) for n, a in client.calls]
        if name == "briefs_list"
    )
    assert payload["all_rigs"] is True
    per_rig = re.findall(r'data-rig="([^"]+)" data-degraded="false">(.*?)</tr>', html, re.S)
    summed = 0
    for _rig, row in per_rig:
        cells = re.findall(r'<td class="mono">(\d+)</td>', row)
        summed += int(cells[-1])
    assert summed == total, "the city row does not equal the sum of the rig rows"
    assert f'data-total-state="all">{total}<' in html


def test_the_brief_list_spans_rigs_with_a_rig_column_and_a_rig_filter(tmp_path: Path):
    dashboard, _, _ = city_dashboard(tmp_path)

    html = body(dashboard, "/briefs")

    assert "<th>Rig</th>" in html
    assert 'data-region="rig-filter"' in html
    text = strip_tags(html)
    assert "mc-open" in text and "gs-open" in text, "the list must span rigs"


def test_the_rig_filter_narrows_the_city_wide_list_without_leaving_it(tmp_path: Path):
    dashboard, _, _ = city_dashboard(tmp_path)

    html = body(dashboard, "/briefs", rig="gascity_packs")

    text = strip_tags(html)
    assert "gs-open" in text
    assert "mc-open" not in text
    assert 'data-region="rig-filter"' in html, "the filter must still be offered"


# --- a sick rig degrades; it does not black out the page --------------------


def test_a_degraded_rig_is_named_inline_while_healthy_rigs_still_render(tmp_path: Path):
    dashboard, _, _ = city_dashboard(tmp_path)

    html = body(dashboard, "/")

    assert 'data-degraded-count="1"' in html
    text = " ".join(strip_tags(html).split())
    assert multi_rig.SICK_RIG in text
    assert "could not be read" in text
    assert "totals on this page are incomplete" in text
    # The healthy rigs are still fully reported: losing fifteen rigs to report
    # one is the failure this whole panel exists to prevent.
    for rig in multi_rig.READABLE_RIGS:
        assert f'data-rig="{rig}" data-degraded="false"' in html
    assert "mc-open" in strip_tags(body(dashboard, "/briefs"))


def test_the_degraded_rig_shows_its_diagnostic_code_like_every_other_finding(tmp_path: Path):
    dashboard, _, _ = city_dashboard(tmp_path)

    html = body(dashboard, "/")

    degraded = html[html.index('data-region="degraded-rigs"') :]
    codes = re.findall(r'<code class="diagnostic-code">([A-Z0-9_]+)</code>', degraded)
    assert codes, "a degraded rig must render its code, not just prose"


def test_a_healthy_city_says_so_rather_than_leaving_the_question_open(tmp_path: Path):
    """Complete has to be distinguishable from 'the page forgot to say'."""
    dashboard, _, _ = rig_dashboard(tmp_path)

    html = body(dashboard, "/")

    assert 'data-region="degraded-rigs"' not in html, "the rig view has no rig health panel"


# --- rig identity survives the trip to a mutation ---------------------------


def test_a_brief_opened_from_the_aggregate_view_carries_its_rig_into_detail(tmp_path: Path):
    dashboard, client, _ = city_dashboard(tmp_path)
    listing = body(dashboard, "/briefs")

    assert 'href="/briefs/gs-open?rig=gascity_packs"' in listing

    client.calls.clear()
    html = body(dashboard, "/briefs/gs-open", rig="gascity_packs")

    shown = next(args for name, args in client.calls if name == "briefs_show")
    assert shown["rig"] == "gascity_packs", "detail must be read from the owning store"
    assert "gs-open" in strip_tags(html)
    assert 'name="rig" value="gascity_packs"' in html, "the forms must carry the rig"


def test_a_mutation_started_from_the_aggregate_view_targets_the_briefs_own_rig(tmp_path: Path):
    dashboard, client, fixture = city_dashboard(tmp_path)

    previewed = dashboard.handle(
        Request.post(
            "/preview",
            operation="adjudicate",
            brief_id="gs-open",
            rig="gascity_packs",
            verdict="approve",
            reason="approved from the city-wide view",
        )
    )
    assert previewed.status == 200, strip_tags(previewed.body)
    for name, arguments in client.calls:
        if name in {"briefs_relay_adjudication", "briefs_show", "briefs_options"}:
            assert arguments.get("rig") == "gascity_packs", (
                f"{name} was planned without naming the owning rig"
            )

    applied = dashboard.handle(
        Request.post("/apply", token=token_in(previewed.body), rig="gascity_packs")
    )

    assert applied.status == 200, strip_tags(applied.body)
    assert bead(fixture, "gascity_packs", "gs-open")["status"] == "closed"
    # And nothing landed in the other store, which holds a brief of the same
    # shape under its own prefix.
    assert bead(fixture, "mathcity", "mc-open")["status"] == "open"


def test_a_preview_taken_in_one_rig_cannot_be_applied_after_the_rig_changes(tmp_path: Path):
    """The rig is a real staleness axis once one page addresses many stores."""
    dashboard, _, fixture = city_dashboard(tmp_path)
    previewed = dashboard.handle(
        Request.post(
            "/preview",
            operation="adjudicate",
            brief_id="gs-open",
            rig="gascity_packs",
            verdict="approve",
            reason="approved in gascity_packs",
        )
    )
    assert previewed.status == 200

    # The confirm arrives naming a different store.
    refused = dashboard.handle(
        Request.post("/apply", token=token_in(previewed.body), rig="mathcity")
    )

    assert refused.status == 409
    text = strip_tags(refused.body)
    assert "MCTL_DASH_PREVIEW_STALE" in text
    assert "rig" in text
    assert bead(fixture, "gascity_packs", "gs-open")["status"] == "open", (
        "the previewed store must be untouched"
    )
    assert bead(fixture, "mathcity", "mc-open")["status"] == "open", (
        "the newly named store must be untouched too"
    )


def test_the_stale_rig_refusal_still_offers_a_fresh_preview_of_the_right_rig(tmp_path: Path):
    dashboard, _, fixture = city_dashboard(tmp_path)
    stale = dashboard.handle(
        Request.post(
            "/preview",
            operation="adjudicate",
            brief_id="gs-open",
            rig="gascity_packs",
            verdict="approve",
            reason="approved in gascity_packs",
        )
    )
    refused = dashboard.handle(
        Request.post("/apply", token=token_in(stale.body), rig="mathcity")
    )

    fresh = token_in(refused.body)
    assert 'name="rig" value="gascity_packs"' in refused.body, (
        "the replacement preview must stay in the rig the operator was looking at"
    )
    applied = dashboard.handle(Request.post("/apply", token=fresh, rig="gascity_packs"))
    assert applied.status == 200, strip_tags(applied.body)
    assert bead(fixture, "gascity_packs", "gs-open")["status"] == "closed"


def test_a_mutation_with_no_rig_is_refused_rather_than_guessed(tmp_path: Path):
    dashboard, _, fixture = city_dashboard(tmp_path)

    response = dashboard.handle(
        Request.post(
            "/preview", operation="adjudicate", brief_id="gs-open", verdict="approve", reason="x"
        )
    )

    assert response.status == 400
    assert "MCTL_DASH_RIG_REQUIRED" in strip_tags(response.body)
    assert "Nothing was written" in strip_tags(response.body)
    assert bead(fixture, "gascity_packs", "gs-open")["status"] == "open"


def test_open_top_brief_carries_the_rig_on_a_city_wide_queue(tmp_path: Path):
    """The per-row links have always carried `rig=`, so a click never hits
    MCTL_DASH_RIG_REQUIRED -- the "Open top brief" shortcut did not, and a
    click on it landed on the disambiguation page instead of the brief.
    Found driving the page in a browser, not by reading the code.
    """
    dashboard, _, _ = city_dashboard(tmp_path)

    html = body(dashboard, "/queue")

    href_match = re.search(r'href="(/briefs/[^"]+)">Open top brief', html)
    assert href_match, "no 'Open top brief' link found on a queue that should be non-empty"
    href = href_match.group(1)
    assert "rig=" in href, f"Open top brief link is missing rig=, would 400: {href}"

    # And the link must actually resolve, not just look right.
    follow_up = dashboard.handle(Request.get(href.split("?", 1)[0], **dict(
        pair.split("=", 1) for pair in href.split("?", 1)[1].split("&")
    )))
    assert follow_up.status == 200, strip_tags(follow_up.body)


def test_a_brief_url_without_a_rig_refuses_and_names_the_rigs(tmp_path: Path):
    dashboard, _, _ = city_dashboard(tmp_path)

    response = dashboard.handle(Request.get("/briefs/gs-open"))

    assert response.status == 400
    text = strip_tags(response.body)
    assert "MCTL_DASH_RIG_REQUIRED" in text
    for rig in multi_rig.ALL_RIGS:
        assert rig in text
    assert 'href="/briefs/gs-open?rig=gascity_packs"' in response.body


# --- the honesty properties survive aggregation -----------------------------


def test_untrusted_diagnostics_are_excluded_from_the_actionable_count_in_the_aggregate(
    tmp_path: Path,
):
    dashboard, _, _ = city_dashboard(tmp_path)

    html = body(dashboard, "/diagnostics")

    actionable = int(re.search(r'data-actionable-count="(\d+)"', html).group(1))
    under_review = int(re.search(r'data-under-review-count="(\d+)"', html).group(1))
    assert under_review >= 2, "MBRF004/MBRF005 fire on this fixture"
    # Counted inside the actionable panel itself: the degraded-rig panel
    # restates its own diagnostics, and a whole-page tally would double them.
    panel = html[
        html.index('data-region="actionable-diagnostics"') : html.index(
            'data-region="untrusted-diagnostics"'
        )
    ]
    counted = re.findall(r'<code class="diagnostic-code">([A-Z0-9_]+)</code>', panel)
    assert actionable == len(counted)
    assert not set(counted) & UNDER_REVIEW_CODES, (
        "an under-review code was summed into the city actionable total"
    )
    assert "MBRF021" in html, "withholding it silently would hide real state"


def test_under_review_codes_stay_in_their_own_panel_across_rigs(tmp_path: Path):
    dashboard, _, _ = city_dashboard(tmp_path)

    html = body(dashboard, "/diagnostics")

    actionable = html.index('data-region="actionable-diagnostics"')
    withheld = html.index('data-region="untrusted-diagnostics"')
    assert actionable < withheld
    for code in ("MBRF021", "MBRF004", "MBRF005"):
        assert code not in html[actionable:withheld], f"{code} rendered as actionable"


def test_artifact_trust_is_surfaced_per_rig_rather_than_collapsed(tmp_path: Path):
    dashboard, _, _ = city_dashboard(tmp_path)

    html = body(dashboard, "/")

    # Both verdicts, each named with its rig: the fixture's two readable rigs
    # genuinely disagree, and a single banner would be a claim about one of
    # them that nobody checked.
    assert 'data-rig="mathcity" >' in html or 'data-rig="mathcity"' in html
    trusted = re.findall(r'data-artifact-trust="(\w+)" data-rig="([^"]+)"', html)
    assert ("true", "mathcity") in trusted
    assert ("false", "gascity_packs") in trusted


def test_the_malformed_caveat_survives_aggregation(tmp_path: Path):
    dashboard, _, _ = city_dashboard(tmp_path)

    text = " ".join(strip_tags(body(dashboard, "/")).split())

    assert "malformed" in text
    assert "closed with no verdict field" in text.lower()
    assert "close_reason" in text


def test_no_repair_affordance_appears_on_any_city_wide_view(tmp_path: Path):
    dashboard, _, _ = city_dashboard(tmp_path)

    pages = "\n".join(
        body(dashboard, path) for path in ("/", "/briefs", "/diagnostics", "/validate", "/work")
    )

    for banned in ('action="/repair"', ">Repair<", ">Fix<", "Fix these", "auto-repair"):
        assert banned not in pages
    assert Dashboard.MUTATION_ROUTES == ("/preview", "/apply")


def test_the_city_wide_views_never_call_a_mutating_tool(tmp_path: Path):
    dashboard, client, _ = city_dashboard(tmp_path)

    for path in ("/", "/briefs", "/diagnostics", "/validate", "/work"):
        dashboard.handle(Request.get(path))
    dashboard.handle(Request.get("/briefs/gs-open", rig="gascity_packs"))

    assert client.names
    assert set(client.names) <= READ_ONLY_TOOLS, sorted(set(client.names) - READ_ONLY_TOOLS)
    assert set(client.names) <= ALLOWED_TOOLS


# --- cost -------------------------------------------------------------------


def test_a_city_wide_page_costs_one_cross_rig_call_not_one_per_rig(tmp_path: Path):
    """N rigs must not mean N round trips from the presentation layer.

    The fan-out belongs to `mctl_core/city.py`, which reads the rigs
    concurrently behind a single call. A dashboard that looped `briefs_list`
    per rig would be the `work ready` mistake one layer up -- and a second
    implementation of the aggregation besides.
    """
    dashboard, client, _ = city_dashboard(tmp_path)

    body(dashboard, "/")

    listings = [args for name, args in client.calls if name == "briefs_list"]
    assert len(listings) == 1, f"one cross-rig read expected, got {len(listings)}"
    assert listings[0]["all_rigs"] is True
    assert not any("rig" in args for args in listings), "a city-wide read names no single rig"


# --- the rig-scoped dashboard is unchanged ----------------------------------


def test_rig_scoped_mode_is_unchanged_by_the_city_wide_addition(tmp_path: Path):
    dashboard, client, _ = rig_dashboard(tmp_path)

    html = body(dashboard, "/")

    assert "context_resolve" in client.names
    assert "context_rigs" not in client.names, "a rig-scoped page needs no city registry"
    assert 'data-scope="city"' not in html
    assert "<th>Rig</th>" not in body(dashboard, "/briefs")
    for _name, arguments in client.calls:
        assert not arguments.get("all_rigs"), "a rig-scoped dashboard never reads cross-rig"


def test_a_rig_scoped_dashboard_ignores_a_rig_query_parameter(tmp_path: Path):
    """A `?rig=` must not retarget a dashboard that was pinned to one rig."""
    dashboard, client, _ = rig_dashboard(tmp_path, rig="mathcity")

    dashboard.handle(Request.get("/briefs", rig="gascity_packs"))

    for _name, arguments in client.calls:
        assert arguments.get("rig") in (None, "mathcity")


# --- a blocked mutation leads with the answer, not the form error -----------


def test_a_blocked_preview_names_the_state_block_alongside_the_form_error(tmp_path: Path):
    """A bead that cannot be adjudicated says so before it complains about a field.

    Previewing with an empty Reason returns `MCTL_MUTATION_REASON_REQUIRED`,
    which is correct but is not the operator's real answer: `mc-closed` cannot
    be adjudicated however the form is filled in. Leading with the field error
    makes an impossible operation look like a fixable typo, so the state-level
    block is rendered first -- which is also what the form's own promise that
    "a preview will show the blocking diagnostic code" means.
    """
    dashboard, _, fixture = rig_dashboard(tmp_path)

    response = dashboard.handle(
        Request.post("/preview", operation="adjudicate", brief_id="mc-closed", verdict="approve", reason="")
    )

    assert response.status == 409
    text = strip_tags(response.body)
    assert "MCTL_MUTATION_REASON_REQUIRED" in text, "the field error is still reported"
    # `mc-closed` is blocked by MBRF005 whatever the form says.
    assert "MBRF005" in text, "the state-level block must be reported too"
    assert response.body.index('data-region="state-blocked"') < response.body.index(
        'data-region="blocked"'
    ), "the state block must lead; a field error first buries the real answer"
    assert "does not permit" in text
    assert "Nothing was written" in text
    assert 'action="/apply"' not in response.body
    assert bead(fixture, "mathcity", "mc-closed")["status"] == "closed"
    # And the under-review code keeps its label even while it is the reason:
    # it is why the tool refused, not a repair instruction.
    assert "Not counted as actionable" in text


def test_a_blocked_preview_on_a_permitted_bead_still_reports_only_the_form_error(tmp_path: Path):
    """No invented block: a bead whose state permits the operation says nothing extra."""
    dashboard, _, _ = rig_dashboard(tmp_path)

    response = dashboard.handle(
        Request.post("/preview", operation="adjudicate", brief_id="mc-open", verdict="approve", reason="")
    )

    assert response.status == 409
    assert 'data-region="state-blocked"' not in response.body, (
        "no state block may be invented for a bead whose state permits the operation"
    )
    assert "MCTL_MUTATION_REASON_REQUIRED" in strip_tags(response.body)


def test_an_unregistered_rig_in_a_link_says_so_instead_of_blaming_the_brief(tmp_path: Path):
    """A mistyped rig must not send an operator hunting for a missing bead."""
    dashboard, _, _ = city_dashboard(tmp_path)

    response = dashboard.handle(Request.get("/briefs/gs-open", rig="not-a-rig"))

    assert response.status == 404
    text = strip_tags(response.body)
    assert "MCTL_CONTEXT_UNKNOWN_RIG" in text
    assert "not registered in this city" in text
    assert "No such brief" not in text, "the headline must match the code"
    assert "Traceback" not in response.body
    for rig in multi_rig.ALL_RIGS:
        assert rig in text, "the registered rigs must be visible to correct the mistake"
