"""Cross-rig reads: the `--all-rigs` / `all_rigs` option the plan has always specified.

Plan Global Constraints, Slice 2: *"Cross-rig reads require an explicit option
such as `--all-rigs`"*, with `all_rigs` on `briefs_list`. This file pins the
behavior of the one implementation behind that option -- `mctl_core/city.py` --
through both adapters, so the CLI and the MCP surface cannot answer the same
question differently and no consumer has a reason to assemble its own.

The properties that matter are not "it returns more rows":

* the city total IS the sum of the per-rig totals, checked against the per-rig
  reads rather than against a hard-coded number;
* a rig that cannot be read becomes a NAMED degraded entry and the other rigs
  still report -- a city-wide answer that silently drops a rig is worse than
  no city-wide answer, because it looks complete;
* withheld diagnostics stay withheld after aggregation;
* artifact trust stays per rig, because the resolved brief root is per rig;
* cross-rig MUTATION remains unreachable.
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
from mctl_core import city as city_module
from mctl_core import mcp_server
from mctl_core.mcp_server import MctlMcpServer

MCTL = SCRIPTS_ROOT / "mctl.py"


def server(fixture: multi_rig.MultiRigCity) -> MctlMcpServer:
    instance = MctlMcpServer(
        default_city=fixture.city_root,
        default_rig=None,
        client_class="internal",
        env=dict(fixture.env),
        # Runs as if invoked from the city, not from the MathCity source
        # checkout -- the checkout guard is a separate contract with its own
        # tests, and tripping it here would mask what this file is pinning.
        cwd=fixture.city_root,
    )
    instance.handle({"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}})
    return instance


_CALL_ID = [100]


def call(instance: MctlMcpServer, name: str, arguments: dict | None = None) -> dict:
    _CALL_ID[0] += 1
    response = instance.handle(
        {
            "jsonrpc": "2.0",
            "id": _CALL_ID[0],
            "method": "tools/call",
            "params": {"name": name, "arguments": dict(arguments or {})},
        }
    )
    assert "result" in response, response
    return response["result"]


def payload(instance: MctlMcpServer, name: str, arguments: dict | None = None) -> dict:
    result = call(instance, name, arguments)
    assert not result["isError"], json.dumps(result["structuredContent"], indent=2)
    return result["structuredContent"]


def rig_entry(body: dict, rig_id: str) -> dict:
    return next(entry for entry in body["rigs"] if entry["rig_id"] == rig_id)


# --- totals ------------------------------------------------------------------


def test_city_wide_totals_equal_the_sum_of_per_rig_totals(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    per_rig = {
        rig: len(payload(instance, "briefs_list", {"rig": rig})["briefs"])
        for rig in multi_rig.READABLE_RIGS
    }
    city = payload(instance, "briefs_list", {"all_rigs": True})

    assert sum(per_rig.values()) > 0, "the fixture must have briefs to aggregate"
    assert len(city["briefs"]) == sum(per_rig.values())
    for rig, count in per_rig.items():
        assert rig_entry(city, rig)["counts"]["briefs"] == count


def test_every_row_carries_the_rig_whose_store_it_came_from(tmp_path: Path):
    """A brief id with no rig is an address with no store behind it."""
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    city = payload(instance, "briefs_list", {"all_rigs": True})

    assert city["briefs"], "nothing to check"
    bead_rows = [brief for brief in city["briefs"] if brief["source"] == "bead"]
    assert bead_rows, "nothing to check"
    for brief in city["briefs"]:
        rig = brief["rig_id"]
        assert rig in multi_rig.READABLE_RIGS
    for brief in bead_rows:
        rig = brief["rig_id"]
        assert brief["bead_id"].startswith(multi_rig.PREFIXES[rig]), (
            "a row was tagged with a rig that does not own it"
        )
    # A manifest-sourced row has no bead to carry a prefix, so the rig tag is
    # the only thing saying which store it came from -- and it is exactly the
    # rig whose manifest was read, never a shared or defaulted one.
    for brief in city["briefs"]:
        if brief["source"] == "manifest":
            assert brief["bead_id"] is None
            assert brief["rig_id"] in multi_rig.READABLE_RIGS


def test_the_explicit_option_is_required_for_a_cross_rig_read(tmp_path: Path):
    """Without `all_rigs` a multi-rig city refuses rather than picking one."""
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    result = call(instance, "briefs_list", {})

    assert result["isError"]
    codes = [item["code"] for item in result["structuredContent"]["diagnostics"]]
    assert "MCTL_CONTEXT_RIG_REQUIRED" in codes


def test_the_rig_selector_errors_name_the_registered_rigs(tmp_path: Path):
    """A caller that guessed a rig is told which ones exist, not just 'no'."""
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    required = call(instance, "briefs_list", {})["structuredContent"]["diagnostics"][0]
    unknown = call(instance, "briefs_list", {"rig": "nope"})["structuredContent"]["diagnostics"][0]

    for diagnostic in (required, unknown):
        listed = diagnostic["facts"]["registered_rigs"]
        for rig in multi_rig.ALL_RIGS:
            assert rig in listed
    assert unknown["code"] == "MCTL_CONTEXT_UNKNOWN_RIG"


def test_the_registry_is_readable_without_selecting_a_rig(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    body = payload(instance, "context_rigs", {})

    assert [entry["rig_id"] for entry in body["rigs"]] == list(multi_rig.ALL_RIGS)
    assert body["city_root"] == str(fixture.city_root)


# --- a failing rig degrades, it does not black out the answer ----------------


def test_a_rig_that_cannot_be_read_is_degraded_while_the_others_still_report(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    city = payload(instance, "briefs_list", {"all_rigs": True})

    sick = rig_entry(city, multi_rig.SICK_RIG)
    assert sick["ok"] is False
    assert sick["reason"], "a degraded rig must say why"
    assert sick["diagnostics"], "a degraded rig must carry its typed diagnostics"
    assert sick["diagnostics"][0]["code"].startswith("MCTL_")
    for rig in multi_rig.READABLE_RIGS:
        assert rig_entry(city, rig)["ok"] is True
    assert len(city["briefs"]) > 0, "healthy rigs must still report"
    assert any(
        item["code"] == sick["diagnostics"][0]["code"] for item in city["diagnostics"]
    ), "the failure must also reach the top-level diagnostics"


def test_the_degraded_rig_is_named_so_a_partial_answer_cannot_look_complete(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    city = payload(instance, "briefs_list", {"all_rigs": True})

    degraded = [entry["rig_id"] for entry in city["rigs"] if not entry["ok"]]
    assert degraded == [multi_rig.SICK_RIG]
    # Every registered rig appears, readable or not: the caller can always
    # compare the roster it got against the roster it expected.
    assert [entry["rig_id"] for entry in city["rigs"]] == list(multi_rig.ALL_RIGS)


def test_a_rig_that_does_not_answer_in_time_is_degraded_rather_than_holding_the_answer(
    tmp_path: Path,
):
    """The deadline is the guard against one wedged rig costing every rig."""
    fixture = multi_rig.build(tmp_path)

    def run(ctx):
        if ctx.rig_id == "gascity_packs":
            time.sleep(5)
        return {"briefs": [], "diagnostics": []}

    started = time.monotonic()
    scope, outcomes = city_module.for_each_rig(
        Path(fixture.city_root),
        city=fixture.city_root,
        env=fixture.env,
        run=run,
        deadline=0.4,
    )
    elapsed = time.monotonic() - started

    assert elapsed < 4, f"a slow rig held the whole read for {elapsed:.1f}s"
    by_rig = {outcome.rig_id: outcome for outcome in outcomes}
    assert by_rig["gascity_packs"].ok is False
    assert by_rig["gascity_packs"].failure[0]["code"] == "MCTL_CITY_RIG_TIMEOUT"
    assert by_rig["mathcity"].ok is True, "a healthy rig must still answer"


def test_validate_across_rigs_is_inconsistent_when_a_rig_cannot_be_read(tmp_path: Path):
    """You cannot call a city consistent over a store you could not open."""
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    city = payload(instance, "briefs_validate", {"all": True, "all_rigs": True})

    assert city["valid"] is False
    assert city["scope"] == "all-rigs"
    assert set(city["severity_counts"]) == {"INFO", "WARN", "ERROR", "FATAL"}


# --- honesty properties survive aggregation ---------------------------------


def test_untrusted_diagnostics_stay_withheld_in_the_aggregate(tmp_path: Path):
    """`MBRF021` must never be summed into an actionable city-wide total."""
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    city = payload(instance, "briefs_validate", {"all": True, "all_rigs": True})

    withheld = [item["code"] for item in city["untrusted_diagnostics"]]
    assert "MBRF021" in withheld, "the fixture's untrusted rig must produce one"
    for item in city["untrusted_diagnostics"]:
        assert item["facts"]["rig_name"] == "gascity_packs", (
            "a withheld diagnostic must still say which rig it came from"
        )
    # Nothing withheld for a rig may reappear as actionable for that same rig.
    # (A rig whose artifact state IS trustworthy keeps its own MBRF021 as a
    # real finding -- that is the per-rig verdict doing its job, and the
    # dashboard applies the further `review.py` exclusion on top.)
    leaked = [
        item
        for item in city["diagnostics"]
        if item["code"] == "MBRF021" and item["facts"].get("rig_name") == "gascity_packs"
    ]
    assert not leaked, "a withheld diagnostic was promoted back into the actionable array"


def test_artifact_trust_is_reported_per_rig_not_collapsed(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    city = payload(instance, "briefs_list", {"all_rigs": True})

    assert rig_entry(city, "mathcity")["artifact_trust"]["trusted"] is True
    assert rig_entry(city, "gascity_packs")["artifact_trust"]["trusted"] is False
    # The city roll-up exists because the response contract requires one, and
    # it is trustworthy only if every rig is -- never a silent average.
    assert city["artifact_trust"]["trusted"] is False
    assert "gascity_packs" in city["artifact_trust"]["reason"]


def test_a_rig_whose_artifact_state_is_trusted_still_says_so(tmp_path: Path):
    """Trusted has to be distinguishable from 'this payload forgot to say'."""
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    city = payload(instance, "briefs_list", {"all_rigs": True})

    trust = rig_entry(city, "mathcity")["artifact_trust"]
    assert trust["trusted"] is True
    assert trust["reason"]
    assert trust["resolved_brief_root"].endswith("mathcity/.beads/briefs")


def test_every_aggregated_diagnostic_names_its_rig(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    city = payload(instance, "briefs_validate", {"all": True, "all_rigs": True})

    assert city["diagnostics"], "nothing to check"
    for item in city["diagnostics"]:
        assert item["facts"].get("rig_name") in multi_rig.ALL_RIGS


# --- cross-rig mutation stays forbidden -------------------------------------


def test_no_mutating_tool_accepts_the_cross_rig_option(tmp_path: Path):
    """Plan Global Constraints: cross-rig mutations are forbidden."""
    for tool in mcp_server.TOOLS:
        if not tool.mutating:
            continue
        assert "all_rigs" not in tool.input_schema["properties"], tool.name
        assert not tool.cross_rig, tool.name
    assert set(mcp_server.CROSS_RIG_ARRAYS) == {"briefs_list", "briefs_validate", "work_ready"}


def test_all_rigs_on_a_mutating_tool_is_a_schema_violation(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    response = instance.handle(
        {
            "jsonrpc": "2.0",
            "id": 900,
            "method": "tools/call",
            "params": {
                "name": "briefs_adjudicate",
                "arguments": {"brief_id": "mc-open", "all_rigs": True},
            },
        }
    )

    assert response["error"]["code"] == -32602
    assert response["error"]["data"]["diagnostic"]["code"] == "MCTL_MCP_INVALID_ARGUMENTS"


# --- the CLI adapter answers identically ------------------------------------


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


def test_the_cli_option_is_the_plans_declared_name(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)

    helptext = run_cli(fixture, "briefs", "list", "--help").stdout

    assert "--all-rigs" in helptext


def test_the_cli_and_the_mcp_tool_report_the_same_city(tmp_path: Path):
    """One read path, two adapters. They may not drift."""
    fixture = multi_rig.build(tmp_path)
    instance = server(fixture)

    result = run_cli(fixture, "briefs", "list", "--all-rigs", "--json")
    from_cli = json.loads(result.stdout)
    from_mcp = payload(instance, "briefs_list", {"all_rigs": True})

    assert {b["bead_id"] for b in from_cli["briefs"]} == {
        b["bead_id"] for b in from_mcp["briefs"]
    }
    assert {(b["bead_id"], b["rig_id"]) for b in from_cli["briefs"]} == {
        (b["bead_id"], b["rig_id"]) for b in from_mcp["briefs"]
    }
    assert [e["rig_id"] for e in from_cli["rigs"]] == [e["rig_id"] for e in from_mcp["rigs"]]


def test_the_cli_exits_nonzero_when_a_rig_could_not_be_read(tmp_path: Path):
    """A pipeline must not read a partial city-wide answer as a complete one."""
    fixture = multi_rig.build(tmp_path)

    result = run_cli(fixture, "briefs", "list", "--all-rigs")

    assert result.returncode == 1, result.stdout
    assert "DEGRADED sick" in result.stdout
    assert "totals below are incomplete" in result.stdout
    assert "2 of 3 rigs readable" in result.stdout


def test_the_cli_human_output_shows_the_per_rig_breakdown(tmp_path: Path):
    fixture = multi_rig.build(tmp_path)

    stdout = run_cli(fixture, "briefs", "list", "--all-rigs").stdout

    for rig in multi_rig.READABLE_RIGS:
        assert f"ok  {rig}: briefs=" in stdout
