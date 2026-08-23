"""Behavior tests for the Slice 6 typed MCP server.

The server is a second adapter over the same `mctl_core` functions the CLI
already proved, so these tests assert adapter behavior -- the tool surface,
the typed envelope, the schema gate on arguments, dry-run safety, and the
rollout gate -- rather than re-testing brief or work semantics.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import mcp_server
from mctl_core.schemas import schema_errors

MCTL = SCRIPTS_ROOT / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"
WORK_STATE = FIXTURES / "work_state"

DECLARED_TOOLS = (
    # #110 shipped mctl_core/blast_radius.py with no tool, so no page could
    # reach it. Exposed as a reporting surface that states registry presence.
    "blast_radius_registry",
    "briefs_adjudicate",
    "briefs_create",
    "briefs_defer",
    "briefs_doctor",
    "briefs_list",
    "briefs_options",
    "briefs_present",
    "briefs_show",
    "briefs_validate",
    "city_health",
    "commission_brief",
    "context_resolve",
    "context_rigs",
    "create_issue_bead",
    "decisions_to_briefs",
    "fleet_sessions",
    "formulas_catalog",
    "gates_status",
    "mayor_boot",
    "mayor_city_state",
    "mayor_conservation",
    "molecules_list",
    "molecules_show",
    "orders_status",
    "trace_replay_preview",
    "trace_show",
    "work_claim",
    "work_dispatch",
    "work_dispatch_event",
    "work_provenance",
    "work_ready",
    "work_status",
)

READ_TOOLS = (
    "context_resolve",
    "briefs_list",
    "briefs_doctor",
    "work_ready",
)


def runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track")
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return city_root, rig_root


def empty_rig_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """A rig with a working bead store and zero briefs -- #103's exact shape."""
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    beads = rig_root / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    (beads / "issues.jsonl").write_text("", encoding="utf-8")
    return city_root, rig_root


def work_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """The Slice 4 work fixture: the only one with a dispatchable brief."""
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    schema_dst = source_checkout / "assets" / "bead-filter"
    schema_dst.mkdir(parents=True)
    shutil.copy2(
        REPO_ROOT / "assets" / "bead-filter" / "dispatch-provenance-schema.toml",
        schema_dst / "dispatch-provenance-schema.toml",
    )
    beads = rig_root / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    shutil.copy2(WORK_STATE / "beads.jsonl", beads / "issues.jsonl")
    shutil.copytree(WORK_STATE / "provenance", beads / "mctl" / "provenance")
    return city_root, rig_root


def server(city_root: Path, rig_root: Path, *, client_class: str = "internal", **env: str):
    environment = {"MCTL_BEADS_FIXTURE": str(rig_root / ".beads" / "issues.jsonl"), **env}
    return mcp_server.MctlMcpServer(
        default_city=city_root,
        default_rig="mathcity",
        client_class=client_class,
        env=environment,
    )


def call(instance, name: str, arguments: dict | None = None) -> dict:
    return instance.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        }
    )


def tool_list(instance) -> list[dict]:
    response = instance.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    return response["result"]["tools"]


def tree_digest(root: Path) -> dict[str, str]:
    return {
        str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


# --- tool surface -----------------------------------------------------------


def test_tool_listing_returns_the_declared_surface(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    names = tuple(sorted(tool["name"] for tool in tool_list(server(city_root, rig_root))))

    assert names == DECLARED_TOOLS


def test_no_generic_command_execution_tool_is_registered(tmp_path: Path):
    """Plan constraint: typed domain tools only, no passthrough."""
    city_root, rig_root = runtime_fixture(tmp_path)
    tools = tool_list(server(city_root, rig_root))

    names = {tool["name"] for tool in tools}
    assert not names & {"shell", "gc", "bd", "mctl", "run_command", "exec", "run_shell"}
    for tool in tools:
        properties = tool["inputSchema"].get("properties", {})
        assert "command" not in properties, f"{tool['name']} accepts a raw command"
        assert "argv" not in properties, f"{tool['name']} accepts a raw argv"


def test_every_tool_declares_both_schemas_and_a_rollout_class(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    for tool in tool_list(server(city_root, rig_root)):
        assert tool["inputSchema"]["type"] == "object", tool["name"]
        assert tool["outputSchema"]["type"] == "object", tool["name"]
        rollout = tool["_meta"]["mctl"]
        assert isinstance(rollout["external_ready"], bool), tool["name"]
        assert isinstance(rollout["mutating"], bool), tool["name"]


def test_initialize_advertises_tools_and_says_there_is_no_passthrough(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    response = server(city_root, rig_root).handle(
        {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}
    )

    result = response["result"]
    assert result["capabilities"]["tools"] == {"listChanged": False}
    assert result["serverInfo"]["name"] == "mctl"
    assert "no generic command-execution tool" in result["instructions"]


# --- typed round trips ------------------------------------------------------


def test_each_read_tool_round_trips_its_declared_output_schema(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    instance = server(city_root, rig_root)
    schemas = {tool["name"]: tool["outputSchema"] for tool in tool_list(instance)}

    for name in READ_TOOLS:
        response = call(instance, name, {})
        assert "error" not in response, (name, response)
        structured = response["result"]["structuredContent"]
        assert schema_errors(structured, schemas[name]) == [], (name, structured)
        assert structured["trace_id"]
        assert isinstance(structured["diagnostics"], list)


def test_targeted_read_tools_round_trip_their_declared_output_schema(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    instance = server(city_root, rig_root)
    schemas = {tool["name"]: tool["outputSchema"] for tool in tool_list(instance)}
    targeted = {
        "briefs_show": {"brief_id": "mc-open"},
        "briefs_options": {"brief_id": "mc-open"},
        "briefs_validate": {"brief_id": "mc-open"},
        "work_status": {"brief_id": "mc-open"},
        # Takes a bead id, not a brief id: its call site is the path-B
        # commission flow, which has no brief to name.
        "work_claim": {"bead_id": "mc-work", "window_seconds": 60},
    }

    for name, arguments in targeted.items():
        response = call(instance, name, arguments)
        assert "error" not in response, (name, response)
        structured = response["result"]["structuredContent"]
        assert schema_errors(structured, schemas[name]) == [], (name, structured)


def test_context_resolve_matches_the_cli_context_json(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    env = os.environ.copy()
    env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
    cli = subprocess.run(
        [
            sys.executable, str(MCTL), "context",
            "--city", str(city_root), "--rig", "mathcity", "--json",
        ],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )
    assert cli.returncode == 0, cli.stderr
    cli_payload = json.loads(cli.stdout)

    structured = call(server(city_root, rig_root), "context_resolve", {})["result"][
        "structuredContent"
    ]

    assert set(cli_payload) <= set(structured)
    volatile = {"trace_id", "warnings", "invocation_cwd"}
    for key in set(cli_payload) - volatile:
        assert structured[key] == cli_payload[key], key


def test_briefs_show_returns_canonical_and_redundant_fields(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    structured = call(server(city_root, rig_root), "briefs_show", {"brief_id": "mc-open"})[
        "result"
    ]["structuredContent"]

    assert structured["brief"]["bead_id"] == "mc-open"
    assert structured["brief"]["canonical_source"] == "bead_store"
    assert structured["brief"]["redundant_artifacts"]


def test_tool_result_carries_both_text_and_structured_content(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = call(server(city_root, rig_root), "briefs_list", {})["result"]

    assert result["isError"] is False
    assert result["content"][0]["type"] == "text"
    assert json.loads(result["content"][0]["text"]) == result["structuredContent"]


def test_each_tool_call_receives_a_fresh_trace_id(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    instance = server(city_root, rig_root)

    first = call(instance, "briefs_list", {})["result"]["structuredContent"]["trace_id"]
    second = call(instance, "briefs_list", {})["result"]["structuredContent"]["trace_id"]

    assert first and second and first != second


# --- typed failure ----------------------------------------------------------


def test_wrong_argument_type_is_a_typed_schema_error(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    response = call(server(city_root, rig_root), "briefs_show", {"brief_id": 123})

    assert "result" not in response
    error = response["error"]
    assert error["code"] == -32602
    assert error["data"]["diagnostic"]["code"] == "MCTL_MCP_INVALID_ARGUMENTS"
    assert error["data"]["diagnostic"]["severity"] == "FATAL"
    assert error["data"]["tool"] == "briefs_show"
    failures = error["data"]["schema_errors"]
    assert failures
    for failure in failures:
        assert set(failure) >= {"path", "keyword", "expected", "actual", "message"}
    assert failures[0]["path"] == "brief_id"
    assert failures[0]["keyword"] == "type"
    assert failures[0]["expected"] == "string"


def test_missing_required_argument_is_a_typed_schema_error(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    response = call(server(city_root, rig_root), "briefs_show", {})

    error = response["error"]
    assert error["code"] == -32602
    assert error["data"]["diagnostic"]["code"] == "MCTL_MCP_INVALID_ARGUMENTS"
    assert [failure["keyword"] for failure in error["data"]["schema_errors"]] == ["required"]


def test_unknown_argument_is_rejected_rather_than_ignored(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    response = call(
        server(city_root, rig_root), "briefs_show", {"brief_id": "mc-open", "shell": "rm -rf /"}
    )

    assert response["error"]["data"]["schema_errors"][0]["keyword"] == "additionalProperties"


def test_a_schema_failure_is_never_a_traceback_or_prose(tmp_path: Path):
    """The whole argument for typed tools is that failures stop being advisory."""
    city_root, rig_root = runtime_fixture(tmp_path)

    response = call(server(city_root, rig_root), "briefs_show", {"brief_id": None})

    rendered = json.dumps(response)
    assert "Traceback" not in rendered
    assert 'File "' not in rendered
    assert isinstance(response["error"]["data"]["schema_errors"], list)


def test_unknown_tool_is_a_typed_error(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    response = call(server(city_root, rig_root), "briefs_teleport", {})

    assert response["error"]["code"] == -32601
    assert response["error"]["data"]["diagnostic"]["code"] == "MCTL_MCP_UNKNOWN_TOOL"


def test_a_core_failure_is_a_typed_tool_error_not_a_crash(tmp_path: Path):
    """Core BriefError/WorkError must reach the client as an mctl diagnostic."""
    city_root, rig_root = runtime_fixture(tmp_path)

    result = call(server(city_root, rig_root), "briefs_show", {"brief_id": "mc-nope"})["result"]

    assert result["isError"] is True
    diagnostics = result["structuredContent"]["diagnostics"]
    assert diagnostics[0]["code"].startswith("MBRF")
    assert result["structuredContent"]["trace_id"]


def test_unknown_method_is_a_jsonrpc_method_not_found(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    response = server(city_root, rig_root).handle(
        {"jsonrpc": "2.0", "id": 3, "method": "resources/list", "params": {}}
    )

    assert response["error"]["code"] == -32601


def test_notifications_get_no_response(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    assert (
        server(city_root, rig_root).handle(
            {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        is None
    )


# --- mutation safety --------------------------------------------------------


def test_dry_run_adjudication_produces_a_plan_and_mutates_nothing(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    before = tree_digest(rig_root)

    structured = call(
        server(city_root, rig_root),
        "briefs_adjudicate",
        {
            "brief_id": "mc-open",
            "verdict": "approve",
            "reason": "ready",
            "option": "A",
            "dry_run": True,
        },
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    assert structured["effect_plan"]["operation"]
    assert structured["effect_plan"]["bead_updates"]
    assert tree_digest(rig_root) == before


def test_mutating_tools_default_to_dry_run(tmp_path: Path):
    """Rollout control: mutation is dry-run-first, so omitting the field is safe."""
    city_root, rig_root = runtime_fixture(tmp_path)
    before = tree_digest(rig_root)

    structured = call(
        server(city_root, rig_root),
        "briefs_adjudicate",
        {"brief_id": "mc-open", "verdict": "approve", "reason": "ready", "option": "A"},
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    assert tree_digest(rig_root) == before


def test_work_dispatch_event_defaults_to_dry_run_and_writes_nothing(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    before = tree_digest(rig_root)

    structured = call(
        server(city_root, rig_root),
        "work_dispatch_event",
        {"bead_id": "mc-work", "dispatch_command": "gc sling mathcity/gc.run-operator mc-work"},
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    assert structured["effect_plan"]["bead_relates"][0]["target_id"] == "mc-work"
    assert tree_digest(rig_root) == before


def test_work_dispatch_event_refuses_a_bead_this_rig_cannot_resolve(tmp_path: Path):
    """The cross-store refusal reaches the MCP surface as a typed error."""
    city_root, rig_root = runtime_fixture(tmp_path)

    response = call(
        server(city_root, rig_root),
        "work_dispatch_event",
        {"bead_id": "hq-foreign", "dispatch_command": "gc sling mathcity/gc.run-operator hq"},
    )

    assert response["result"]["isError"] is True
    blocked = next(
        diagnostic
        for diagnostic in response["result"]["structuredContent"]["diagnostics"]
        if diagnostic["code"] == "MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS"
    )
    # The wrapper is the shared precondition gate; the precondition that fired
    # is named, so a client can tell a cross-store id from any other blocker.
    assert blocked["facts"]["blocking_code"] == "MWRK_BEAD_NOT_FOUND"


def test_work_claim_reports_an_unclaimed_bead_rather_than_an_empty_answer(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    structured = call(server(city_root, rig_root), "work_claim", {"bead_id": "mc-work"})[
        "result"
    ]["structuredContent"]

    assert structured["claim"]["verified_assignee"] is False
    assert structured["claim"]["classification_hint"] == "immediate_strand"


def test_work_claim_on_a_missing_bead_is_a_typed_error(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    response = call(server(city_root, rig_root), "work_claim", {"bead_id": "mc-nope"})

    assert response["result"]["isError"] is True
    codes = {
        diagnostic["code"]
        for diagnostic in response["result"]["structuredContent"]["diagnostics"]
    }
    assert "MWRK_BEAD_NOT_FOUND" in codes


def test_work_dispatch_returns_the_same_effect_plan_shape_as_the_cli(tmp_path: Path):
    city_root, rig_root = work_fixture(tmp_path)
    env = os.environ.copy()
    env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
    cli = subprocess.run(
        [
            sys.executable, str(MCTL), "work", "dispatch", "mc-approved", "--dry-run",
            "--city", str(city_root), "--rig", "mathcity", "--json",
        ],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )
    assert cli.returncode == 0, cli.stderr
    cli_plan = json.loads(cli.stdout)["effect_plan"]

    structured = call(
        server(city_root, rig_root), "work_dispatch", {"brief_id": "mc-approved", "dry_run": True}
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    assert set(structured["effect_plan"]) == set(cli_plan)
    assert structured["effect_plan"]["operation"] == cli_plan["operation"]


def test_mutation_fails_closed_on_a_blocking_precondition(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = call(
        server(city_root, rig_root),
        "briefs_adjudicate",
        {"brief_id": "mc-open", "verdict": "approve", "dry_run": True},
    )["result"]

    assert result["isError"] is True
    assert result["structuredContent"]["diagnostics"]


# --- rollout gate -----------------------------------------------------------


def test_external_clients_get_no_tools_until_external_access_is_armed(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    assert tool_list(server(city_root, rig_root, client_class="external")) == []


def test_external_clients_are_blocked_from_calling_a_disabled_tool(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    response = call(server(city_root, rig_root, client_class="external"), "briefs_list", {})

    assert response["error"]["code"] == -32601
    assert response["error"]["data"]["diagnostic"]["code"] == "MCTL_MCP_TOOL_DISABLED"
    assert response["error"]["data"]["client_class"] == "external"


def test_armed_external_clients_still_cannot_reach_mutating_tools(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    armed = server(
        city_root, rig_root, client_class="external", MCTL_MCP_ENABLE_EXTERNAL_TOOLS="1"
    )

    names = {tool["name"] for tool in tool_list(armed)}
    response = call(armed, "briefs_adjudicate", {"brief_id": "mc-open", "verdict": "approve"})

    assert "briefs_list" in names
    assert not names & {
        "briefs_adjudicate",
        "briefs_defer",
        "briefs_create",
        "work_dispatch",
        "work_dispatch_event",
    }
    assert response["error"]["data"]["diagnostic"]["code"] == "MCTL_MCP_TOOL_DISABLED"


def test_internal_clients_reach_the_whole_surface(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    names = {tool["name"] for tool in tool_list(server(city_root, rig_root))}

    assert names == set(DECLARED_TOOLS)


def test_client_class_defaults_to_external(tmp_path: Path):
    """Fail safe: an operator who forgets the flag gets the closed surface."""
    city_root, rig_root = runtime_fixture(tmp_path)

    instance = mcp_server.MctlMcpServer(
        default_city=city_root,
        default_rig="mathcity",
        env={"MCTL_BEADS_FIXTURE": str(rig_root / ".beads" / "issues.jsonl")},
    )

    assert instance.client_class == "external"
    assert tool_list(instance) == []


# --- trace tools ------------------------------------------------------------


def test_trace_show_and_replay_preview_do_not_reapply_effects(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    instance = server(city_root, rig_root)
    applied = call(
        instance,
        "briefs_adjudicate",
        {
            "brief_id": "mc-open",
            "verdict": "approve",
            "reason": "ready",
            "option": "A",
            "dry_run": False,
        },
    )["result"]["structuredContent"]
    trace_id = applied["trace_id"]
    after_mutation = tree_digest(rig_root)

    shown = call(instance, "trace_show", {"trace_id": trace_id})["result"]["structuredContent"]
    preview = call(instance, "trace_replay_preview", {"trace_id": trace_id})["result"][
        "structuredContent"
    ]

    assert shown["trace"]["outcome"] == "applied"
    assert preview["applied"] is False
    assert preview["source_trace_id"] == trace_id
    assert preview["planned_effects"]
    assert preview["replay_blockers"], "replaying an applied trace must be flagged"
    assert tree_digest(rig_root) == after_mutation


def test_trace_show_reports_a_missing_trace_as_a_typed_error(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = call(server(city_root, rig_root), "trace_show", {"trace_id": "not-a-trace"})["result"]

    assert result["isError"] is True
    assert result["structuredContent"]["diagnostics"][0]["code"] == "MCTL_TRACE_NOT_FOUND"


# --- Q5: artifact state honesty --------------------------------------------


def test_artifact_state_is_marked_trusted_when_the_layout_resolves(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    structured = call(server(city_root, rig_root), "briefs_list", {})["result"]["structuredContent"]

    trust = structured["artifact_trust"]
    assert trust["trusted"] is True
    assert structured["untrusted_diagnostics"] == []


def test_a_missing_brief_root_makes_artifact_state_untrusted_not_missing(tmp_path: Path):
    """Q5: against the live city the resolved root does not exist at all."""
    city_root, rig_root = runtime_fixture(tmp_path)
    shutil.rmtree(rig_root / ".beads" / "briefs")

    structured = call(server(city_root, rig_root), "briefs_show", {"brief_id": "mc-open"})[
        "result"
    ]["structuredContent"]

    trust = structured["artifact_trust"]
    assert trust["trusted"] is False
    assert trust["open_question"] == "Q5"
    assert "OPEN-DESIGN-QUESTIONS" in trust["reference"]
    states = {artifact["state"] for artifact in structured["brief"]["redundant_artifacts"]}
    assert states == {"unverified"}
    for artifact in structured["brief"]["redundant_artifacts"]:
        assert artifact["state_reported_by_core"] == "missing"


def test_untrusted_artifact_state_moves_mbrf021_out_of_the_diagnostics_array(tmp_path: Path):
    """MBRF021 is the code Q5 measured firing falsely on 66 of 70 live briefs."""
    city_root, rig_root = runtime_fixture(tmp_path)
    shutil.rmtree(rig_root / ".beads" / "briefs")

    structured = call(server(city_root, rig_root), "briefs_validate", {"all": True})["result"][
        "structuredContent"
    ]

    codes = {diagnostic["code"] for diagnostic in structured["diagnostics"]}
    withheld = {diagnostic["code"] for diagnostic in structured["untrusted_diagnostics"]}
    assert "MBRF021" not in codes
    assert "MBRF021" in withheld
    assert "MCTL_MCP_ARTIFACT_STATE_UNTRUSTED" in codes
    assert structured["artifact_trust"]["withheld_codes"] == ["MBRF021"]


def test_untrusted_state_is_reported_even_when_it_hides_nothing(tmp_path: Path):
    """The warning is about the model, not about how many hits it produced."""
    city_root, rig_root = runtime_fixture(tmp_path)
    shutil.rmtree(rig_root / ".beads" / "briefs")

    structured = call(server(city_root, rig_root), "briefs_list", {})["result"]["structuredContent"]

    warning = next(
        diagnostic
        for diagnostic in structured["diagnostics"]
        if diagnostic["code"] == "MCTL_MCP_ARTIFACT_STATE_UNTRUSTED"
    )
    assert warning["severity"] == "WARN"
    assert "Q5" in warning["message"] or "Q5" in (warning["hint"] or "")


def test_pile_filenames_that_carry_the_bead_id_in_frontmatter_are_untrusted(tmp_path: Path):
    """Q5's second half: the live pile is <NN>-<slug>-brief.md, not <bead_id>.md."""
    city_root, rig_root = runtime_fixture(tmp_path)
    pile = rig_root / ".beads" / "briefs" / ".pile"
    (pile / "12-inspect-open-brief-brief.md").write_text(
        "---\nartifact: mc-open\n---\n\n# Inspect open brief\n", encoding="utf-8"
    )

    structured = call(server(city_root, rig_root), "briefs_list", {})["result"]["structuredContent"]

    trust = structured["artifact_trust"]
    assert trust["trusted"] is False
    assert "frontmatter" in trust["reason"]


def test_an_absent_pile_is_the_empty_state_not_an_untrust_condition(tmp_path: Path):
    """#149: `.pile` is created lazily, so absence is normal, not a defect.

    Every brief-producing formula runs `mkdir -p "{{artifact_root}}/.pile"`
    as it writes its first brief, and nothing provisions the directory before
    then. A rig that has never piled a brief therefore has no pile directory,
    and the artifacts under it genuinely are missing -- the reading is
    accurate, so it may be acted on. Measured when #149 was filed: 6 of 17
    live rigs were untrusted on this branch alone and 4 of them held zero
    brief beads.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    shutil.rmtree(rig_root / ".beads" / "briefs" / ".pile")

    structured = call(server(city_root, rig_root), "briefs_list", {})["result"]["structuredContent"]

    trust = structured["artifact_trust"]
    assert trust["trusted"] is True
    assert trust["open_question"] is None
    codes = {diagnostic["code"] for diagnostic in structured["diagnostics"]}
    assert "MCTL_MCP_ARTIFACT_STATE_UNTRUSTED" not in codes


def test_an_absent_pile_still_untrusts_when_the_root_is_also_absent(tmp_path: Path):
    """Narrowing the pile branch must not narrow the root branch (#2/Q5).

    A missing root also gates the mutation path -- `_require_brief_root`
    refuses with MBRF035 rather than let `mkdir -p` build a shadow tree -- so
    it keeps its own verdict.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    shutil.rmtree(rig_root / ".beads" / "briefs")

    structured = call(server(city_root, rig_root), "briefs_list", {})["result"]["structuredContent"]

    assert structured["artifact_trust"]["trusted"] is False
    assert structured["artifact_trust"]["open_question"] == "Q5"


def test_a_malformed_pile_is_still_untrusted_when_absence_is_not(tmp_path: Path):
    """The distinction #149 draws: absent cannot lie, malformed does."""
    city_root, rig_root = runtime_fixture(tmp_path)
    pile = rig_root / ".beads" / "briefs" / ".pile"
    (pile / "12-inspect-open-brief-brief.md").write_text(
        "---\nartifact: mc-open\n---\n\n# Inspect open brief\n", encoding="utf-8"
    )

    structured = call(server(city_root, rig_root), "briefs_list", {})["result"]["structuredContent"]

    assert structured["artifact_trust"]["trusted"] is False
    assert "frontmatter" in structured["artifact_trust"]["reason"]


def test_mutating_tools_also_declare_artifact_trust(tmp_path: Path):
    """A plan whose cache effects rest on the broken model must say so."""
    city_root, rig_root = runtime_fixture(tmp_path)
    shutil.rmtree(rig_root / ".beads" / "briefs")

    structured = call(
        server(city_root, rig_root),
        "briefs_adjudicate",
        {"brief_id": "mc-open", "verdict": "approve", "reason": "ready", "option": "A"},
    )["result"]["structuredContent"]

    assert structured["artifact_trust"]["trusted"] is False


def test_frontmatter_artifact_id_matches_the_canonical_parser_on_a_leading_whitespace_key(
    tmp_path: Path,
):
    """The hand-rolled parser this replaced stripped the key before comparing
    it; the canonical `read_frontmatter()` key regex is column-anchored and
    never matches a line with leading whitespace, so that key is absent from
    the canonical result. `_frontmatter_artifact_id` must agree with
    canonical, not with the parser it replaced.
    """
    path = tmp_path / "leading-whitespace.md"
    path.write_text("---\n  artifact: gh-issue-99\nstatus: ready\n---\nbody\n", encoding="utf-8")

    assert mcp_server._frontmatter_artifact_id(path) is None


def test_frontmatter_artifact_id_finds_a_key_past_the_old_64_line_cap(tmp_path: Path):
    """The parser this replaced stopped scanning after 64 lines and returned
    None even when a real `artifact:` key existed further down. The canonical
    parser locates the closing fence rather than counting lines, so it always
    finds it.
    """
    lines = ["---"] + [f"filler{i}: x" for i in range(70)] + ["artifact: gh-issue-77", "---", "body"]
    path = tmp_path / "long-frontmatter.md"
    path.write_text("\n".join(lines), encoding="utf-8")

    assert mcp_server._frontmatter_artifact_id(path) == "gh-issue-77"


def test_briefs_list_names_the_empty_scope_rather_than_leaving_it_silent(tmp_path: Path):
    """#103: `briefs: []` for a rig with nothing indistinguishable from `briefs:
    []` for the wrong rig. The finder was three minutes from filing a report
    that mctl was blind before running the discriminator (all_rigs) themselves.
    """
    city_root, rig_root = empty_rig_fixture(tmp_path)
    instance = server(city_root, rig_root)

    response = call(instance, "briefs_list", {})

    result = response["result"]["structuredContent"]
    assert result["briefs"] == []
    codes = [d["code"] for d in result["diagnostics"]]
    assert "MCTL_BRIEFS_SCOPE_EMPTY" in codes
    hint = next(d["hint"] for d in result["diagnostics"] if d["code"] == "MCTL_BRIEFS_SCOPE_EMPTY")
    assert "all_rigs" in hint


def test_briefs_doctor_names_the_empty_scope_for_a_whole_rig_check(tmp_path: Path):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    instance = server(city_root, rig_root)

    response = call(instance, "briefs_doctor", {})

    result = response["result"]["structuredContent"]
    assert result["briefs"] == []
    codes = [d["code"] for d in result["diagnostics"]]
    assert "MCTL_BRIEFS_SCOPE_EMPTY" in codes


def test_briefs_doctor_on_one_missing_id_does_not_claim_the_scope_is_empty(tmp_path: Path):
    """A doctor check on a specific, nonexistent id is a different question
    than "does this rig have any briefs" -- the empty-scope hint would be
    misleading here (all_rigs would not resolve a bad id either).
    """
    city_root, rig_root = empty_rig_fixture(tmp_path)
    instance = server(city_root, rig_root)

    response = call(instance, "briefs_doctor", {"brief_id": "mc-does-not-exist"})

    result = response["result"]["structuredContent"]
    codes = [d["code"] for d in result["diagnostics"]]
    assert "MCTL_BRIEFS_SCOPE_EMPTY" not in codes


def test_briefs_list_with_results_does_not_get_the_empty_scope_hint(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    instance = server(city_root, rig_root)

    response = call(instance, "briefs_list", {})

    result = response["result"]["structuredContent"]
    assert result["briefs"], "fixture must be non-empty for this to be a meaningful check"
    codes = [d["code"] for d in result["diagnostics"]]
    assert "MCTL_BRIEFS_SCOPE_EMPTY" not in codes
