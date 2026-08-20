"""A slow bead store may cost the bead rows, and nothing else.

`briefs list --all-rigs` returned **8** records where an hour earlier it had
returned 442. Nothing in the reader had changed. `hq`'s bead query had become
a full partition scan of `leases`, it outlived the 25s cross-rig deadline, and
the fan-out did what it was written to do: report the rig degraded and drop
it. What went with it were `hq`'s 158 decisions-track rows and 87 stack files
-- **documents on disk, which never ran the query that was slow.**

The defect was a coupling, not a timeout. `list_briefs` computed the bead
population first because the document read needs it to know which stack files
a bead already carries, and so a file read on disk was sequenced behind a
query against Dolt and inherited its failures.

This file pins the decoupling, and pins it in the shape the incident had:

* a rig whose bead store will not read still emits its manifest rows and its
  stack files, still labelled with their `source`;
* a rig whose bead store outlives the deadline does too -- the document lane
  is published before the bead read starts, so there is something to harvest;
* those rows survive aggregation into the city-wide payload;
* and none of that is allowed to look like success. The rig stays `ok: false`,
  carries `MCTL_CITY_RIG_PARTIAL`, and names which store answered and which
  did not. `valid` is false and the CLI exit code is non-zero.

The last point is the one worth guarding hardest. A partial answer rendered
as a clean one is strictly worse than the failure it replaced: 442 dropping
to 8 was at least visible.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
if str(Path(__file__).resolve().parent) not in sys.path:
    sys.path.insert(0, str(Path(__file__).resolve().parent))

import multi_rig
from mctl_core import briefs as briefs_module
from mctl_core import city as city_module
from mctl_core.beads import bd_timeout_within
from mctl_core.briefs import BriefFilters, list_briefs_report
from mctl_core.mcp_server import MctlMcpServer

MCTL = SCRIPTS_ROOT / "mctl.py"

#: The rig whose bead store this file breaks. It is one of the two READABLE
#: rigs, so its documents are present and its beads would otherwise read --
#: which is what makes "the documents survived" a real observation rather
#: than a rig that never had any.
STALLED = "gascity_packs"
HEALTHY = "mathcity"

DOCUMENT_SOURCES = {"manifest", "stack_file"}


# --- fixture -----------------------------------------------------------------


def stall_bead_store(fixture: multi_rig.MultiRigCity, rig: str = STALLED) -> None:
    """Make one rig's bead store unreadable while leaving its documents alone.

    The file has to exist -- an absent path fails context resolution, which is
    the `sick` rig's separate case and degrades before any read is attempted.
    What is wanted here is a store that resolves and then will not answer,
    which is what a wedged Dolt query looks like from `bd`'s side.
    """
    Path(fixture.env[f"MCTL_BEADS_FIXTURE_{rig}"]).write_text(
        "{ this is not a bead\n", encoding="utf-8"
    )


def server(fixture: multi_rig.MultiRigCity, deadline: float | None = None) -> MctlMcpServer:
    instance = MctlMcpServer(
        default_city=fixture.city_root,
        default_rig=None,
        client_class="internal",
        env=dict(fixture.env),
        cwd=fixture.city_root,
        **({} if deadline is None else {"all_rigs_deadline": deadline}),
    )
    instance.handle({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
    return instance


_CALL_ID = [500]


def payload(instance: MctlMcpServer, name: str, arguments: dict | None = None) -> dict:
    _CALL_ID[0] += 1
    response = instance.handle(
        {
            "jsonrpc": "2.0",
            "id": _CALL_ID[0],
            "method": "tools/call",
            "params": {"name": name, "arguments": dict(arguments or {})},
        }
    )
    result = response["result"]
    assert not result["isError"], json.dumps(result["structuredContent"], indent=2)
    return result["structuredContent"]


def rig_entry(body: dict, rig_id: str) -> dict:
    return next(entry for entry in body["rigs"] if entry["rig_id"] == rig_id)


def rows_for(body: dict, rig_id: str) -> list[dict]:
    return [row for row in body["briefs"] if row["rig_id"] == rig_id]


# --- the defect: a dead bead store must not hide the documents ---------------


def test_a_rig_whose_bead_store_will_not_read_still_emits_its_documents(tmp_path: Path):
    """The 245 records that never touched Dolt.

    Scaled down to the fixture: one decisions-track row and one stack file.
    Both are read off disk; neither has anything to do with the bead store
    that just failed.
    """
    fixture = multi_rig.build(tmp_path)
    healthy = payload(server(fixture), "briefs_list", {"all_rigs": True})
    documents_when_healthy = {
        row["brief_id"] for row in rows_for(healthy, STALLED) if row["source"] in DOCUMENT_SOURCES
    }
    stall_bead_store(fixture)

    city = payload(server(fixture), "briefs_list", {"all_rigs": True})

    rows = rows_for(city, STALLED)
    assert rows, "the bead store failing took the documents with it"
    assert {row["source"] for row in rows} <= DOCUMENT_SOURCES
    assert documents_when_healthy <= {row["brief_id"] for row in rows}


def test_the_documents_keep_their_source_and_their_fields(tmp_path: Path):
    """Not merely present -- still whole, and still saying where they came from."""
    fixture = multi_rig.build(tmp_path)
    stall_bead_store(fixture)

    city = payload(server(fixture), "briefs_list", {"all_rigs": True})

    rows = rows_for(city, STALLED)
    assert {row["source"] for row in rows} == DOCUMENT_SOURCES, (
        "both document lanes must survive, not just the manifest"
    )
    for row in rows:
        assert row["rig_id"] == STALLED
        assert row["bead_id"] is None, "a document has no bead, and must not claim one"
        assert row["brief_id"]
        assert row["decision_state"]
        assert row["canonical_source"]


def test_a_stack_file_a_dead_bead_would_have_claimed_is_emitted_not_suppressed(
    tmp_path: Path,
):
    """Suppression is a fact about a *pair*, and one half of the pair is gone.

    A stack file named `<bead-id>-….md` is normally folded into that bead's
    record rather than listed twice. With the bead store unreadable there is
    no bead record for it to be a duplicate of, so suppressing it would hide
    the file completely -- the same defect one level down.
    """
    fixture = multi_rig.build(tmp_path)
    stall_bead_store(fixture)

    city = payload(server(fixture), "briefs_list", {"all_rigs": True})

    stack_rows = [row for row in rows_for(city, STALLED) if row["source"] == "stack_file"]
    assert stack_rows, "the stack file was suppressed against a bead that could not be read"


# --- and it must not look like success ---------------------------------------


def test_the_partially_read_rig_is_not_reported_as_a_clean_success(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)
    stall_bead_store(fixture)

    city = payload(server(fixture), "briefs_list", {"all_rigs": True})

    entry = rig_entry(city, STALLED)
    assert entry["ok"] is False, "a rig missing one of its two stores is not ok"
    assert entry["partial"] is True
    assert entry["counts"]["briefs"] == len(rows_for(city, STALLED))


def test_the_reason_names_which_store_answered_and_which_did_not(tmp_path: Path):
    """'Degraded' is not enough. An operator has to know what is missing."""
    fixture = multi_rig.build(tmp_path)
    stall_bead_store(fixture)

    city = payload(server(fixture), "briefs_list", {"all_rigs": True})

    entry = rig_entry(city, STALLED)
    assert "bead store" in entry["reason"]
    assert "manifest" in entry["reason"] and "stack" in entry["reason"]
    lanes = entry["degraded_sources"]
    assert [lane["lane"] for lane in lanes] == [briefs_module.LANE_BEADS]
    assert lanes[0]["ok"] is False
    assert lanes[0]["sources"] == ["bead"], "the lane must name the rows it costs"
    assert any(item["code"] == "MBRF012" for item in lanes[0]["diagnostics"]), (
        "the lane must carry the typed reason, not just a sentence"
    )


def test_the_partial_read_is_a_typed_diagnostic_on_the_rig_and_on_the_city(
    tmp_path: Path,
):
    fixture = multi_rig.build(tmp_path)
    stall_bead_store(fixture)

    city = payload(server(fixture), "briefs_list", {"all_rigs": True})

    entry = rig_entry(city, STALLED)
    assert "MCTL_CITY_RIG_PARTIAL" in {item["code"] for item in entry["diagnostics"]}
    partial = [item for item in city["diagnostics"] if item["code"] == "MCTL_CITY_RIG_PARTIAL"]
    assert partial, "a partially read rig must reach the top-level diagnostics"
    assert partial[0]["facts"]["rig_name"] == STALLED
    bead_failure = [item for item in city["diagnostics"] if item["code"] == "MBRF012"]
    assert bead_failure and bead_failure[0]["facts"]["rig_name"] == STALLED


def test_a_partially_read_city_is_not_valid(tmp_path: Path):
    """You cannot call a city consistent over a store you could not open."""
    fixture = multi_rig.build(tmp_path)
    stall_bead_store(fixture)

    city = payload(server(fixture), "briefs_validate", {"all": True, "all_rigs": True})

    assert city["valid"] is False
    assert rig_entry(city, STALLED)["ok"] is False


def test_a_healthy_rig_declares_no_degraded_sources(tmp_path: Path):
    """Partial has to be distinguishable from 'this payload forgot to say'."""
    fixture = multi_rig.build(tmp_path)
    stall_bead_store(fixture)

    city = payload(server(fixture), "briefs_list", {"all_rigs": True})

    entry = rig_entry(city, HEALTHY)
    assert entry["ok"] is True
    assert entry["partial"] is False
    assert "degraded_sources" not in entry
    assert any(row["source"] == "bead" for row in rows_for(city, HEALTHY)), (
        "one rig's dead bead store must not cost another rig its beads"
    )


def test_a_rig_that_cannot_be_resolved_at_all_stays_fully_degraded(tmp_path: Path):
    """Partial is for a rig that answered from *something*.

    `sick`'s bead-store path does not exist, so its context never resolves and
    no lane is reachable -- not even the document lane, whose layout is
    derived from that same context. Reporting it as partial would claim a
    read that did not happen.
    """
    fixture = multi_rig.build(tmp_path)
    stall_bead_store(fixture)

    city = payload(server(fixture), "briefs_list", {"all_rigs": True})

    entry = rig_entry(city, multi_rig.SICK_RIG)
    assert entry["ok"] is False
    assert entry["partial"] is False
    assert entry["counts"]["briefs"] == 0
    assert not rows_for(city, multi_rig.SICK_RIG)


# --- the incident's own shape: the bead read outlives the deadline -----------


def slow_bead_store(monkeypatch, rig: str, seconds: float) -> None:
    """Make one rig's `bd` read take longer than the caller's whole budget."""
    real = briefs_module.read_beads

    def read(rig_root, **kwargs):
        if Path(rig_root).name == rig:
            time.sleep(seconds)
        return real(rig_root, **kwargs)

    monkeypatch.setattr(briefs_module, "read_beads", read)


def test_a_bead_read_that_outlives_the_deadline_still_yields_that_rigs_documents(
    tmp_path: Path, monkeypatch
):
    """The incident, reproduced end to end through the MCP cross-rig surface.

    Before the fix the rig came back with an empty payload and one
    `MCTL_CITY_RIG_TIMEOUT`, and its documents -- already read, sitting in a
    local -- died with the thread. The publish has to be eager for this to
    work: a partial answer drained only after the read returns is published
    on every path except the one that needs it.
    """
    fixture = multi_rig.build(tmp_path)
    slow_bead_store(monkeypatch, STALLED, seconds=10)

    started = time.monotonic()
    city = payload(server(fixture, deadline=0.75), "briefs_list", {"all_rigs": True})
    elapsed = time.monotonic() - started

    assert elapsed < 8, f"a wedged rig held the whole read for {elapsed:.1f}s"
    entry = rig_entry(city, STALLED)
    assert entry["partial"] is True, "the documents were dropped with the rig"
    rows = rows_for(city, STALLED)
    assert rows, "the merge dropped the rows the fan-out had rescued"
    assert {row["source"] for row in rows} == DOCUMENT_SOURCES


def test_the_timed_out_rig_reports_both_the_timeout_and_which_store_went_quiet(
    tmp_path: Path, monkeypatch
):
    fixture = multi_rig.build(tmp_path)
    slow_bead_store(monkeypatch, STALLED, seconds=10)

    city = payload(server(fixture, deadline=0.75), "briefs_list", {"all_rigs": True})

    entry = rig_entry(city, STALLED)
    codes = {item["code"] for item in entry["diagnostics"]}
    assert "MCTL_CITY_RIG_TIMEOUT" in codes, "why the read stopped"
    assert "MCTL_CITY_RIG_PARTIAL" in codes, "what is consequently missing"
    assert entry["ok"] is False
    assert "bead store" in entry["reason"]
    assert "MCTL_CITY_RIG_TIMEOUT" in {item["code"] for item in city["diagnostics"]}


def test_a_timed_out_rigs_partial_answer_is_still_a_finished_payload(
    tmp_path: Path, monkeypatch
):
    """A harvested payload must have been through the adapter's own passes.

    It travels on the same surface as a whole one, so it carries the same
    contract -- here, the per-rig artifact-trust verdict that must never
    accompany artifact state silently.
    """
    fixture = multi_rig.build(tmp_path)
    slow_bead_store(monkeypatch, STALLED, seconds=10)

    city = payload(server(fixture, deadline=0.75), "briefs_list", {"all_rigs": True})

    entry = rig_entry(city, STALLED)
    assert entry["partial"] is True
    assert entry["artifact_trust"]["reason"], "a harvested payload skipped the trust pass"


def test_a_rig_that_publishes_no_partial_answer_is_degraded_exactly_as_before(
    tmp_path: Path,
):
    """The harvest must not turn an empty timeout into a false partial."""
    fixture = multi_rig.build(tmp_path)

    def run(ctx, progress):
        if ctx.rig_id == STALLED:
            time.sleep(5)
        return {"briefs": [], "diagnostics": []}

    _, outcomes = city_module.for_each_rig(
        Path(fixture.city_root),
        city=fixture.city_root,
        env=fixture.env,
        run=run,
        deadline=0.4,
    )

    outcome = next(item for item in outcomes if item.rig_id == STALLED)
    assert outcome.ok is False
    assert outcome.partial is False
    assert outcome.readable is False
    assert [str(item["code"]) for item in outcome.diagnostics] == ["MCTL_CITY_RIG_TIMEOUT"]


# --- the bead lane is bounded below the fan-out's own deadline ---------------


def test_the_bead_subprocess_is_bounded_by_the_remaining_city_budget(tmp_path: Path):
    """`bd`'s 30s default sits ABOVE the 25s fan-out deadline.

    Left alone, the fan-out always gave up first and the operator was told
    "the rig did not answer" when the truth available one layer down was "the
    bead store did not answer". The adapter sizes the subprocess timeout off
    the budget that is actually left.
    """
    fixture = multi_rig.build(tmp_path)
    seen: list[int | None] = []

    def run(ctx, progress):
        seen.append(bd_timeout_within(progress.remaining_seconds()))
        return {"briefs": [], "diagnostics": []}

    city_module.for_each_rig(
        Path(fixture.city_root), city=fixture.city_root, env=fixture.env, run=run, deadline=9.0
    )

    assert seen, "nothing ran"
    for budget in seen:
        assert budget is not None
        assert 1 <= budget <= 7, f"{budget}s is not inside a 9s deadline with margin"


def test_bounding_the_bead_read_never_raises_an_operators_own_ceiling(monkeypatch):
    """It is a bound, not an override. `MCTL_BD_TIMEOUT_SECONDS` still wins low."""
    monkeypatch.setenv("MCTL_BD_TIMEOUT_SECONDS", "3")

    assert bd_timeout_within(None) == 3
    assert bd_timeout_within(60.0) == 3, "a long deadline must not raise the ceiling"
    assert bd_timeout_within(2.5) == 1, "a short deadline must still lower it"


# --- the CLI says so, and a pipeline can see it ------------------------------


def run_cli(fixture: multi_rig.MultiRigCity, *args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(fixture.env)
    return subprocess.run(
        [sys.executable, str(MCTL), *args, "--city", str(fixture.city_root)],
        capture_output=True,
        text=True,
        cwd=str(fixture.city_root),
        env=env,
    )


def test_the_cli_marks_the_partial_rig_and_still_shows_its_count(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)
    stall_bead_store(fixture)

    result = run_cli(fixture, "briefs", "list", "--all-rigs")

    assert result.returncode == 1, result.stdout
    assert f"PARTIAL {STALLED}: briefs=" in result.stdout, result.stdout
    assert "answered from only part of their stores" in result.stdout
    assert f"ok  {HEALTHY}: briefs=" in result.stdout
    assert f"DEGRADED {multi_rig.SICK_RIG}" in result.stdout


def test_a_single_rig_list_emits_the_documents_and_refuses_to_look_complete(
    tmp_path: Path,
):
    """The same honesty one scope down: `--rig` is where most callers live."""
    fixture = multi_rig.build(tmp_path)
    stall_bead_store(fixture)

    result = run_cli(fixture, "briefs", "list", "--rig", STALLED, "--json")

    assert result.returncode == 1, result.stderr
    body = json.loads(result.stdout)
    assert body["briefs"], "the documents were dropped on the single-rig path too"
    assert {row["source"] for row in body["briefs"]} == DOCUMENT_SOURCES
    lanes = body["degraded_sources"]
    assert [lane["lane"] for lane in lanes] == [briefs_module.LANE_BEADS]
    assert "MBRF012" in {item["code"] for item in body["diagnostics"]}


def test_a_healthy_single_rig_list_is_unchanged(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)

    result = run_cli(fixture, "briefs", "list", "--rig", HEALTHY, "--json")

    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    assert "degraded_sources" not in body
    assert any(row["source"] == "bead" for row in body["briefs"])


def test_the_human_single_rig_output_qualifies_the_count_it_prints(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)
    stall_bead_store(fixture)

    stdout = run_cli(fixture, "briefs", "list", "--rig", STALLED).stdout

    assert "INCOMPLETE:" in stdout
    assert "bead store" in stdout


# --- the healthy path did not change -----------------------------------------


def test_a_healthy_listing_is_identical_to_the_claim_aware_read(tmp_path: Path):
    """Reading the documents first must not change what a good read returns.

    The document lane runs once with an empty claim map (to publish early)
    and again with the real one; if the second pass were skipped, the stack
    file its bead already carries would be listed twice.
    """
    fixture = multi_rig.build(tmp_path)
    from mctl_core.context import resolve_context

    ctx = resolve_context(
        Path(fixture.city_root),
        city=fixture.city_root,
        rig=HEALTHY,
        require_runtime_city=True,
        require_explicit_runtime=True,
        env=fixture.env,
    )
    listing = list_briefs_report(ctx, BriefFilters())

    assert listing.complete
    assert listing.degraded_sources == ()
    ids = [record.brief_id for record in listing.records]
    assert len(ids) == len(set(ids)), "the same document was emitted twice"
    assert any(record.source == "bead" for record in listing.records)


# --- the dashboard says the same thing -------------------------------------


def city_view(body: dict):
    from mctl_dashboard.aggregate import CityView

    return CityView.from_payload(body)


def test_the_dashboard_view_separates_partial_from_unreadable(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)
    stall_bead_store(fixture)

    view = city_view(payload(server(fixture), "briefs_list", {"all_rigs": True}))

    assert [rig.rig_id for rig in view.partial] == [STALLED]
    assert [rig.rig_id for rig in view.unreadable] == [multi_rig.SICK_RIG]
    assert {rig.rig_id for rig in view.degraded} == {STALLED, multi_rig.SICK_RIG}
    assert view.complete is False, "a partial rig still means the total is short"
    assert [row["rig_id"] for row in view.rows_for(STALLED)], (
        "the partial rig's rows must be on the page it is reported degraded on"
    )


def test_the_rig_health_panel_does_not_tell_the_operator_to_look_for_rows_it_shows(
    tmp_path: Path,
):
    """"Counted nowhere" is false for a partial rig, and actively misleading."""
    from mctl_dashboard import render

    fixture = multi_rig.build(tmp_path)
    stall_bead_store(fixture)
    view = city_view(payload(server(fixture), "briefs_list", {"all_rigs": True}))

    html = render.degraded_rigs_panel(view.degraded, len(view.rigs))

    assert 'data-partial-count="1"' in html
    assert "partial" in html
    assert STALLED in html and multi_rig.SICK_RIG in html
    assert "totals on this page are incomplete" in html
