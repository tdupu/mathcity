"""Slice 8 dashboard: preview-before-apply, and the freshness of that preview.

The plan's rollout controls say to "keep dashboard mutation apply buttons
disabled until the dashboard can fetch and display a fresh dry-run preview".
`fresh` is the load-bearing word. A preview that is merely *present* is a
liability: an operator who previewed an approval, walked away, and confirmed
after the bead moved underneath would apply a decision against a brief that no
longer exists in the state they read.

So the guard here is not "was a preview shown" but "is the preview still true":
the confirm path re-resolves context, re-reads the target brief, and re-plans,
and applies only when all three still match what was previewed. Anything else
refuses and replaces the preview with a fresh one.
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_dashboard.app import Dashboard, Request
from mctl_dashboard.client import InProcessMcpClient
from mctl_dashboard.preview import stable_digest

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"


def runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track")
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return city_root, rig_root


def dashboard_for(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    client = InProcessMcpClient(
        city=city_root,
        rig="mathcity",
        env={"MCTL_BEADS_FIXTURE": str(rig_root / ".beads" / "issues.jsonl")},
    )
    return Dashboard(client), city_root, rig_root


def beads(rig_root: Path) -> list[dict]:
    path = rig_root / ".beads" / "issues.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def bead(rig_root: Path, bead_id: str) -> dict:
    return next(row for row in beads(rig_root) if row["id"] == bead_id)


def write_beads(rig_root: Path, rows: list[dict]) -> None:
    path = rig_root / ".beads" / "issues.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


def preview(dashboard, **form):
    fields = {
        "operation": "adjudicate",
        "brief_id": "mc-open",
        "verdict": "approve",
        "reason": "ready to ship",
        **form,
    }
    return dashboard.handle(Request.post("/preview", **fields))


def token_in(html: str) -> str:
    match = re.search(r'name="token" value="([^"]+)"', html)
    assert match, "the rendered preview carries no apply token"
    return match.group(1)


# --- a preview must exist before an apply action is enabled ------------------


def test_the_detail_view_offers_no_apply_control_before_a_preview_exists(tmp_path: Path):
    dashboard, _, _ = dashboard_for(tmp_path)

    html = dashboard.handle(Request.get("/briefs/mc-open")).body

    assert 'action="/preview"' in html, "the operator must be able to ask for a preview"
    assert 'action="/apply"' not in html, "apply must not be reachable without a preview"
    assert 'name="token"' not in html


def test_a_preview_enables_exactly_one_apply_control(tmp_path: Path):
    dashboard, _, _ = dashboard_for(tmp_path)

    response = preview(dashboard)

    assert response.status == 200
    assert 'action="/apply"' in response.body
    assert response.body.count('action="/apply"') == 1
    assert "briefs.adjudicate" in strip_tags(response.body)


def test_the_preview_shows_the_planned_effects_it_will_apply(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)

    text = strip_tags(preview(dashboard).body)

    assert "mc-open" in text
    assert "closed" in text, "the planned canonical bead status must be visible"
    assert "decision_toml" in text
    assert "stack_index" in text


def test_a_preview_writes_nothing(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    before = {p: p.read_bytes() for p in sorted(rig_root.rglob("*")) if p.is_file()}

    preview(dashboard)

    after = {p: p.read_bytes() for p in sorted(rig_root.rglob("*")) if p.is_file()}
    assert after == before
    assert bead(rig_root, "mc-open")["status"] == "open"


def test_apply_without_a_token_refuses_and_mutates_nothing(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)

    response = dashboard.handle(Request.post("/apply"))

    assert response.status == 400
    assert "MCTL_DASH_PREVIEW_REQUIRED" in strip_tags(response.body)
    assert bead(rig_root, "mc-open")["status"] == "open"


def test_apply_with_an_unknown_token_refuses_and_mutates_nothing(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)

    response = dashboard.handle(Request.post("/apply", token="not-a-token"))

    assert response.status == 400
    assert "MCTL_DASH_PREVIEW_REQUIRED" in strip_tags(response.body)
    assert bead(rig_root, "mc-open")["status"] == "open"


# --- the confirm applies exactly what was previewed --------------------------


def test_confirming_a_fresh_preview_applies_exactly_the_previewed_plan(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    previewed = preview(dashboard)
    previewed_digest = stable_digest(
        json.loads(re.search(r'data-plan-json="([^"]*)"', previewed.body).group(1).replace("&quot;", '"'))
    )

    response = dashboard.handle(Request.post("/apply", token=token_in(previewed.body)))

    assert response.status == 200, strip_tags(response.body)
    text = strip_tags(response.body)
    assert "Applied" in text
    applied = json.loads(re.search(r'data-plan-json="([^"]*)"', response.body).group(1).replace("&quot;", '"'))
    assert stable_digest(applied) == previewed_digest, "a different plan was applied"
    row = bead(rig_root, "mc-open")
    assert row["status"] == "closed"
    assert row["metadata"]["verdict"] == "approve"
    assert row["metadata"]["verdict_reason"] == "ready to ship"


def test_the_applied_trace_id_is_shown_so_the_mutation_can_be_audited(tmp_path: Path):
    dashboard, _, _ = dashboard_for(tmp_path)
    previewed = preview(dashboard)

    response = dashboard.handle(Request.post("/apply", token=token_in(previewed.body)))

    trace = re.search(r'data-trace-id="([0-9a-f-]{36})"', response.body)
    assert trace, "an applied mutation must surface its trace id"


def test_the_advance_control_is_focused_so_the_next_brief_needs_no_mouse(tmp_path: Path):
    """#125 (partial): adjudicate fast -- advance without touching the mouse.

    After a verdict is recorded the applied page offers "Next brief"; #125's DoD
    is that the next brief comes up "without touching the mouse or the back
    button". Autofocusing the advance control makes Enter advance -- a JS-off,
    honesty-preserving step (the applied page still renders, status stays 200,
    the trace id stays shown). The full POST->302 auto-advance and honest-skip
    of unadjudicable briefs remain.
    """
    dashboard, _, _ = dashboard_for(tmp_path)
    previewed = preview(dashboard)

    response = dashboard.handle(Request.post("/apply", token=token_in(previewed.body)))

    assert response.status == 200
    # The advance region is present, and its primary control takes focus so a
    # keyboard operator advances with Enter alone.
    assert 'data-region="advance"' in response.body
    advance = response.body.split('data-region="advance"', 1)[1]
    assert "Next brief" in advance, "the applied page must offer the next brief"
    next_anchor = advance.split("Next brief", 1)[0].rsplit("<a", 1)[1]
    assert "autofocus" in next_anchor, "the next-brief control must take focus for Enter-to-advance"


def test_a_token_is_single_use_so_a_resubmitted_form_cannot_apply_twice(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    token = token_in(preview(dashboard).body)
    dashboard.handle(Request.post("/apply", token=token))

    repeat = dashboard.handle(Request.post("/apply", token=token))

    assert repeat.status == 400
    assert "MCTL_DASH_PREVIEW_REQUIRED" in strip_tags(repeat.body)


# --- a stale preview cannot be applied ---------------------------------------


def test_a_preview_goes_stale_when_the_target_brief_changes_underneath(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    token = token_in(preview(dashboard).body)

    rows = beads(rig_root)
    for row in rows:
        if row["id"] == "mc-open":
            row["title"] = "Inspect open brief (retitled by another operator)"
    write_beads(rig_root, rows)
    response = dashboard.handle(Request.post("/apply", token=token))

    assert response.status == 409
    text = strip_tags(response.body)
    assert "MCTL_DASH_PREVIEW_STALE" in text
    assert "target" in text
    assert bead(rig_root, "mc-open")["status"] == "open", "a stale preview must not apply"


def test_a_stale_preview_is_replaced_by_a_fresh_one_rather_than_just_refused(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    stale_token = token_in(preview(dashboard).body)
    rows = beads(rig_root)
    for row in rows:
        if row["id"] == "mc-open":
            row["title"] = "Inspect open brief (retitled)"
    write_beads(rig_root, rows)

    refused = dashboard.handle(Request.post("/apply", token=stale_token))
    fresh_token = token_in(refused.body)

    assert fresh_token != stale_token
    assert "retitled" in strip_tags(refused.body), "the fresh preview must show the new state"
    applied = dashboard.handle(Request.post("/apply", token=fresh_token))
    assert applied.status == 200
    assert bead(rig_root, "mc-open")["status"] == "closed"


def test_the_stale_token_is_dead_even_after_the_fresh_preview_is_offered(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    stale_token = token_in(preview(dashboard).body)
    rows = beads(rig_root)
    for row in rows:
        if row["id"] == "mc-open":
            row["title"] = "Inspect open brief (retitled)"
    write_beads(rig_root, rows)
    dashboard.handle(Request.post("/apply", token=stale_token))

    retry = dashboard.handle(Request.post("/apply", token=stale_token))

    assert retry.status == 400
    assert bead(rig_root, "mc-open")["status"] == "open"


def test_a_preview_goes_stale_when_the_resolved_context_changes(tmp_path: Path):
    dashboard, city_root, rig_root = dashboard_for(tmp_path)
    token = token_in(preview(dashboard).body)

    # The city registry is re-pointed underneath the operator: same rig name,
    # different canonical database.
    registry = city_root / "city.toml"
    registry.write_text(
        registry.read_text(encoding="utf-8").replace("fixture_mathcity", "fixture_mathcity_v2"),
        encoding="utf-8",
    )
    response = dashboard.handle(Request.post("/apply", token=token))

    assert response.status == 409
    text = strip_tags(response.body)
    assert "MCTL_DASH_PREVIEW_STALE" in text
    assert "context" in text
    assert bead(rig_root, "mc-open")["status"] == "open"


def test_a_preview_goes_stale_when_the_planned_effects_change(tmp_path: Path):
    """The third axis: same context, same bead fields, different plan.

    Deleting the redundant decision cache removes a `cache_update` from the
    plan. Nothing the target-fingerprint watches has moved, so only comparing
    the plan itself catches it.
    """
    dashboard, _, rig_root = dashboard_for(tmp_path)
    token = token_in(preview(dashboard).body)

    (rig_root / ".beads" / "briefs" / "decisions" / "mc-open.toml").unlink()
    response = dashboard.handle(Request.post("/apply", token=token))

    assert response.status == 409
    assert "MCTL_DASH_PREVIEW_STALE" in strip_tags(response.body)
    assert "plan" in strip_tags(response.body)
    assert bead(rig_root, "mc-open")["status"] == "open"


def test_changing_the_operation_inputs_needs_a_new_preview(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    approve_token = token_in(preview(dashboard).body)

    # A second preview for a different verdict must not be applyable with the
    # first token, and the first token must still describe the first verdict.
    rejected = preview(dashboard, verdict="reject", reason="not ready")
    reject_token = token_in(rejected.body)
    assert reject_token != approve_token

    dashboard.handle(Request.post("/apply", token=reject_token))
    assert bead(rig_root, "mc-open")["metadata"]["verdict"] == "reject"


# --- blocked mutations never reach an apply control -------------------------


def test_a_blocked_preview_shows_the_blocking_code_and_offers_no_apply(tmp_path: Path):
    dashboard, _, _ = dashboard_for(tmp_path)

    response = preview(dashboard, brief_id="mc-closed")

    assert response.status == 409
    text = strip_tags(response.body)
    assert "MBRF" in text, "the blocking diagnostic code must be visible"
    assert 'action="/apply"' not in response.body


def test_an_under_review_block_is_not_dressed_as_a_hard_state_lock(tmp_path: Path):
    """§5: the 409 headline must name the refusal that fired, not mislabel it.

    `mc-closed` is blocked by MBRF005 -- an UNDER-REVIEW code ("closed with no
    verdict field", an instrumentation artifact per review.py), not a hard
    state lock. The page used to headline every `_blocking_option` result
    "This brief's state does not permit adjudication" and say "No way of filling
    in the form would change this answer" -- the hard-state-lock wording -- over
    a refusal that is explicitly under review. Reserve that wording for a real
    state lock; here, name the code that actually fired.
    """
    dashboard, _, _ = dashboard_for(tmp_path)

    response = preview(dashboard, brief_id="mc-closed")

    assert response.status == 409
    text = strip_tags(response.body)
    # the code that fired is named
    assert "MBRF005" in text
    # ...but NOT dressed as a permanent state lock
    assert "does not permit" not in text, (
        "an under-review refusal must not claim the brief's state forbids adjudication"
    )
    assert "No way of filling in the form" not in text
    assert 'action="/apply"' not in response.body


def test_an_empty_reason_is_refused_at_preview_time(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)

    response = preview(dashboard, reason="")

    assert response.status >= 400
    assert 'action="/apply"' not in response.body
    assert bead(rig_root, "mc-open")["status"] == "open"


def test_defer_uses_the_same_preview_gate_as_adjudicate(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)

    response = preview(dashboard, operation="defer", reason="waiting on Q5", days="7")

    assert response.status == 200
    assert "briefs.defer" in strip_tags(response.body)
    applied = dashboard.handle(Request.post("/apply", token=token_in(response.body)))
    assert applied.status == 200
    assert bead(rig_root, "mc-open")["status"] == "deferred"


def test_an_unknown_operation_is_refused_rather_than_forwarded(tmp_path: Path):
    dashboard, _, _ = dashboard_for(tmp_path)

    response = dashboard.handle(Request.post("/preview", operation="rm -rf", brief_id="mc-open"))

    assert response.status == 400
    assert "MCTL_DASH_UNKNOWN_OPERATION" in strip_tags(response.body)


# --- the digest that makes the guard meaningful ------------------------------


def test_the_plan_digest_ignores_timestamps_but_not_effects():
    """A digest that changed every second would make every preview stale."""
    first = {"trace_id": "a", "bead_updates": [{"id": "x", "metadata": {"adjudicated_at": "1"}}]}
    second = {"trace_id": "b", "bead_updates": [{"id": "x", "metadata": {"adjudicated_at": "2"}}]}
    third = {"trace_id": "c", "bead_updates": [{"id": "y", "metadata": {"adjudicated_at": "2"}}]}

    assert stable_digest(first) == stable_digest(second)
    assert stable_digest(first) != stable_digest(third)


def test_two_previews_of_the_same_operation_agree_on_the_digest(tmp_path: Path):
    dashboard, _, _ = dashboard_for(tmp_path)

    first = preview(dashboard).body
    second = preview(dashboard).body

    def plan(html: str) -> dict:
        return json.loads(re.search(r'data-plan-json="([^"]*)"', html).group(1).replace("&quot;", '"'))

    assert stable_digest(plan(first)) == stable_digest(plan(second))


# --- #135: a plan that did not fully land must not read as a past-tense report


def test_the_applied_page_does_not_claim_a_refused_write_as_past_tense(tmp_path: Path):
    """`mc-open`'s pile file has no frontmatter block, so the frontmatter
    write in its adjudication plan is refused (MCTL_BRIEF_FRONTMATTER_UNWRITABLE)
    -- it never lands. The page must not have a section titled in the past
    tense ("What was applied") that lists it as if it had.
    """
    dashboard, _, _ = dashboard_for(tmp_path)
    token = token_in(preview(dashboard).body)

    response = dashboard.handle(Request.post("/apply", token=token))

    text = strip_tags(response.body)
    assert "What was applied" not in text, (
        "a past-tense heading over the pre-write plan is what made #135 misleading"
    )
    assert "MCTL_BRIEF_FRONTMATTER_UNWRITABLE" in text, (
        "the refusal must still be visible on the same page, not just accurate underneath a bad title"
    )
    assert "brief_frontmatter" in response.body, (
        "the plan panel itself should still be there, honestly titled -- not removed"
    )


# --- multi-option approve names an option, so MOPT001 cannot be reached -------
#
# The `_resolve_recommendation` shim (mc-qlmh, 42f63d7) that used to back-fill an
# empty option with the brief's recommendation was removed with the panel
# rework: the legal-moves control never posts an approve-with-empty-option on a
# multi-option brief, so there is nothing to resolve. `_give_options` stays here
# as a shared fixture helper (used by test_dashboard_panel_moves.py); the move
# control's own coverage of the unnamed-option combo lives in that file.


def _give_options(rig_root: Path, brief_id: str) -> None:
    """Append a two-option §4 section (A recommended) to a fixture brief's body."""
    rows = beads(rig_root)
    for row in rows:
        if row["id"] == brief_id:
            row["description"] = (row.get("description") or "") + (
                "\n\n## §4 — Options\n\n"
                "- **(A) Ship it** *(recommended)*\n  Do the thing now.\n"
                "- **(B) Wait**\n  Hold off a week.\n"
            )
    write_beads(rig_root, rows)
