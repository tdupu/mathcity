"""mc-vtru8 — the dispatch bound is reachable from an agent, not only a shell.

Taylor's verdict removed the client-side dispatch deadline and replaced it with
a live elapsed warning, and asked for *"a surface for adjusting the timeout
size."* That surface shipped as `--deadline-seconds` / `--warn-after-seconds`
and the two `MCTL_DISPATCH_*` env keys -- both of which require a human at a
shell. Asked whether the surface must also be agent-reachable, Taylor: **"Yes
MCP reachable."** `work_dispatch_bound` is that tool.

THE ONE THING THIS TOOL MUST NOT DO is become a second answer to "what is the
bound". A tool that parsed its own arguments into its own policy would let the
MCP surface and the CLI/env surface disagree, and two surfaces that disagree
about a kill bound are worse than one surface that is merely inconvenient. So
the tool writes the SAME two env keys the CLI layers its flags onto, and reads
them back through the SAME `resolve_dispatch_elapsed_policy`. Asserted below
structurally (the resolver is the only thing that resolves) and behaviourally
(every precedence rule the env surface has, this tool inherits unchanged).

POLICY P6.3 names `MWRK_DISPATCH_TIMEOUT_UNKNOWN` as the in-house compliant
reference for an expiring bound, and #184's fix is that
`DispatchFailureVerdict.applied` stays `None` -- *cannot tell* -- rather than
collapsing to `False`, which would tell a caller a retry is safe when it is not.
A bound set through THIS tool reaches that same classifier, and the end-to-end
test below drives a real slow `gc` shim through the real MCP server to prove it.
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from mctl_core import mcp_server, work  # noqa: E402
from mctl_core.schemas import schema_errors  # noqa: E402
from mctl_core.work import (  # noqa: E402
    DISPATCH_DEADLINE_ENV,
    DISPATCH_OPERATOR_BOUND_CODE,
    DISPATCH_WARN_AFTER_ENV,
    DISPATCH_WARN_AFTER_SECONDS,
    MEASURED_SLING_WORST_SECONDS,
    plan_dispatch_bound,
    resolve_dispatch_elapsed_policy,
)

from test_dispatch_kill_switch import APPROVED_BRIEF, runtime  # noqa: E402

TOOL = "work_dispatch_bound"


@pytest.fixture(autouse=True)
def _no_inherited_bound():
    """Every test starts from the shipped default, and leaves nothing behind.

    The tool writes into the process environment on purpose -- that is the one
    store the resolver reads -- which makes this module the only one in the suite
    that can arm a kill bound for every test that runs after it, in this process
    and in every subprocess those tests spawn.

    Deliberately NOT `monkeypatch.delenv(..., raising=False)`: pytest records an
    undo entry only when the key was already present, so on a clean environment
    -- the normal case -- it records nothing and a value the TEST later writes is
    never rolled back. Saving and restoring by hand is unconditional.
    """
    keys = (DISPATCH_DEADLINE_ENV, DISPATCH_WARN_AFTER_ENV)
    saved = {key: os.environ.get(key) for key in keys}
    for key in keys:
        os.environ.pop(key, None)
    try:
        yield
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value


def server(city_root: Path, rig_root: Path, *, client_class: str = "internal"):
    return mcp_server.MctlMcpServer(
        default_city=city_root,
        default_rig="mathcity",
        client_class=client_class,
        env={"MCTL_BEADS_FIXTURE": str(rig_root / ".beads" / "issues.jsonl")},
        cwd=REPO_ROOT,
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


def body(response: dict) -> dict:
    return response["result"]["structuredContent"]


def codes(payload: dict) -> list[str]:
    return [str(row.get("code")) for row in payload.get("diagnostics", [])]


def details(payload: dict) -> str:
    return " ".join(
        str(row.get("facts", {}).get("detail", "")) for row in payload.get("diagnostics", [])
    )


def spec():
    return mcp_server.TOOLS_BY_NAME[TOOL]


# --- registration: a WRITE, on the same footing as the other writes ----------


def test_the_tool_is_registered_as_a_mutating_write():
    """It SETS a bound, so it is a mutation, and mutations are dry-run-first."""
    tool = spec()

    assert tool.mutating is True
    assert tool.external_ready is False, "mutating tools stay off the external surface"
    dry_run = tool.input_schema["properties"]["dry_run"]
    assert dry_run["type"] == "boolean" and dry_run["default"] is True


def test_the_response_satisfies_the_schema_the_tool_advertises(tmp_path: Path):
    """The registration trap, made a test.

    A ToolSpec that declares `artifact_state` in only one of the two places it
    must appear returns `MCTL_MCP_OUTPUT_SCHEMA_VIOLATION` on every call, and the
    failure reads like a broken handler. This asserts the served payload against
    the served schema, which is the check that tells those two apart.
    """
    city_root, rig_root, _, _ = runtime(tmp_path)

    response = call(server(city_root, rig_root), TOOL, {"deadline_seconds": "400"})
    payload = body(response)

    assert response["result"]["isError"] is False, payload
    assert "MCTL_MCP_OUTPUT_SCHEMA_VIOLATION" not in codes(payload)
    assert schema_errors(payload, spec().output_schema) == []


# --- one resolver, never two -------------------------------------------------


def test_the_plan_resolves_only_through_the_shared_resolver(monkeypatch: pytest.MonkeyPatch):
    """Structural proof that the MCP surface cannot disagree with the CLI one.

    The tool parses no seconds of its own: it layers the caller's raw strings
    onto the environment and hands the whole mapping to
    `resolve_dispatch_elapsed_policy` -- the same function `apply_dispatch_plan`
    and the CLI flags resolve through. Stubbing that one function is therefore
    enough to control everything the tool believes about the bound; if it were
    not, this test could not see the sentinel.
    """
    seen: list[dict[str, str]] = []
    sentinel_before = work.unbounded_policy("before", warn_after_seconds=11.0)
    sentinel_after = work.unbounded_policy("after", warn_after_seconds=22.0)

    def fake(env=None):
        seen.append(dict(env or {}))
        return (sentinel_before if len(seen) == 1 else sentinel_after), ("a note",)

    monkeypatch.setattr(work, "resolve_dispatch_elapsed_policy", fake)
    plan = plan_dispatch_bound(
        "trace-1", deadline_seconds="900", warn_after_seconds="30", env={"PATH": "/nowhere"}
    )

    assert plan.in_force is sentinel_before
    assert plan.resolved is sentinel_after
    assert plan.notes == ("a note",)
    # The second resolution saw the caller's request layered onto the environment
    # -- raw, unparsed, exactly as the CLI layers its flags.
    assert seen[0] == {"PATH": "/nowhere"}
    assert seen[1] == {
        "PATH": "/nowhere",
        DISPATCH_DEADLINE_ENV: "900",
        DISPATCH_WARN_AFTER_ENV: "30",
    }


def test_an_omitted_field_writes_nothing(monkeypatch: pytest.MonkeyPatch):
    """Absent means *leave it alone*, not *reset it to the default*."""
    monkeypatch.setenv(DISPATCH_WARN_AFTER_ENV, "45")
    plan = plan_dispatch_bound("trace-2", deadline_seconds="900")

    assert plan.requested == {DISPATCH_DEADLINE_ENV: "900"}
    assert plan.resolved.warn_after_seconds == 45.0


# --- the dry run is the read, and it writes nothing --------------------------


def test_a_dry_run_reports_the_bound_and_installs_nothing(tmp_path: Path):
    city_root, rig_root, _, _ = runtime(tmp_path)

    payload = body(call(server(city_root, rig_root), TOOL, {"deadline_seconds": "900"}))

    assert payload["applied"] is False
    bound = payload["dispatch_bound"]
    assert bound["before"]["deadline_seconds"] is None, "the default is NO deadline"
    assert bound["before"]["warn_after_seconds"] == DISPATCH_WARN_AFTER_SECONDS
    assert bound["after"]["deadline_seconds"] == 900.0, "a preview still shows the bound"
    assert bound["env_writes"] == {DISPATCH_DEADLINE_ENV: "900"}
    # Nothing was written, so the resolver still answers with the default.
    assert DISPATCH_DEADLINE_ENV not in os.environ
    assert resolve_dispatch_elapsed_policy()[0].deadline_seconds is None


def test_applying_writes_the_bound_where_the_resolver_reads_it(tmp_path: Path):
    """One store: the env key the CLI and the docs already name."""
    city_root, rig_root, _, _ = runtime(tmp_path)

    payload = body(
        call(server(city_root, rig_root), TOOL, {"deadline_seconds": "900", "dry_run": False})
    )

    assert payload["applied"] is True
    assert payload["dispatch_bound"]["after"]["deadline_seconds"] == 900.0
    assert os.environ[DISPATCH_DEADLINE_ENV] == "900"
    assert resolve_dispatch_elapsed_policy()[0].deadline_seconds == 900.0


def test_the_agent_can_take_the_bound_back_off(tmp_path: Path):
    """`none` restores the default, which is unbounded (part 1 of the verdict)."""
    city_root, rig_root, _, _ = runtime(tmp_path)
    instance = server(city_root, rig_root)
    call(instance, TOOL, {"deadline_seconds": "900", "dry_run": False})

    payload = body(call(instance, TOOL, {"deadline_seconds": "none", "dry_run": False}))

    assert payload["dispatch_bound"]["after"]["deadline_seconds"] is None
    assert payload["dispatch_bound"]["after"]["bounded"] is False
    assert resolve_dispatch_elapsed_policy()[0].deadline_seconds is None


# --- everything the env surface refuses to do, this tool refuses too ---------


def test_an_unreadable_bound_is_reported_and_never_coerced(tmp_path: Path):
    """A typo must not become a kill bound nobody chose."""
    city_root, rig_root, _, _ = runtime(tmp_path)

    payload = body(
        call(server(city_root, rig_root), TOOL, {"deadline_seconds": "5 minutes", "dry_run": False})
    )

    assert payload["dispatch_bound"]["after"]["deadline_seconds"] is None
    assert DISPATCH_OPERATOR_BOUND_CODE in codes(payload)
    assert "is not a number of seconds" in details(payload)


def test_a_bound_below_the_measured_sling_cost_is_reported_back(tmp_path: Path):
    """#181's subject, inherited whole: 200s killed a 243.51s dispatch that landed."""
    city_root, rig_root, _, _ = runtime(tmp_path)

    payload = body(call(server(city_root, rig_root), TOOL, {"deadline_seconds": "200"}))

    assert DISPATCH_OPERATOR_BOUND_CODE in codes(payload)
    assert "cannot succeed" in details(payload)
    assert str(MEASURED_SLING_WORST_SECONDS) in details(payload)
    # Still applied, because it is the operator's bound and this is a report.
    assert payload["dispatch_bound"]["after"]["deadline_seconds"] == 200.0


def test_a_generous_bound_is_not_reported_back(tmp_path: Path):
    """P6.2 negative control: the report must be capable of NOT firing."""
    city_root, rig_root, _, _ = runtime(tmp_path)

    payload = body(call(server(city_root, rig_root), TOOL, {"deadline_seconds": "600"}))

    assert DISPATCH_OPERATOR_BOUND_CODE not in codes(payload)


def test_a_bound_set_here_carries_a_warn_threshold_beneath_it(tmp_path: Path):
    """P6.3(a): no deadline without an early signal strictly below it."""
    city_root, rig_root, _, _ = runtime(tmp_path)

    payload = body(call(server(city_root, rig_root), TOOL, {"deadline_seconds": "0.8"}))

    after = payload["dispatch_bound"]["after"]
    assert after["warn_after_seconds"] < after["deadline_seconds"]


# --- P6.3 / #184: an expiring bound set HERE is still UNKNOWN, never false ----


def test_a_bound_set_through_MCP_expires_as_UNKNOWN_never_as_applied_false(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """The whole point of the review, end to end through the real server.

    An agent sets a 0.6s bound with the new tool and then dispatches through
    `work_dispatch` in the same process, against a `gc` shim that sleeps 30s. The
    bound expires. POLICY P6.3 cites this site by name as the compliant
    reference, so the outcome must be `MWRK_DISPATCH_TIMEOUT_UNKNOWN` with
    `applied` never rendered false -- the #184 fix, reached through a bound the
    MCP surface installed rather than one a shell exported.
    """
    city_root, rig_root, bin_dir, gc_log = runtime(tmp_path, sling_delay=30.0)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("MCTL_ENABLE_LIVE_DISPATCH", "1")
    monkeypatch.setenv("MCTL_BEADS_FIXTURE", str(rig_root / ".beads" / "issues.jsonl"))
    instance = server(city_root, rig_root)

    call(instance, TOOL, {"deadline_seconds": "0.6", "dry_run": False})
    started = time.monotonic()
    response = call(instance, "work_dispatch", {"brief_id": APPROVED_BRIEF, "dry_run": False})
    elapsed = time.monotonic() - started

    assert elapsed < 25.0, "the bound the MCP tool installed never abandoned the sling"
    payload = body(response)
    assert response["result"]["isError"] is True
    assert "MWRK_DISPATCH_TIMEOUT_UNKNOWN" in codes(payload)
    rendered = json.dumps(payload)
    assert "UNKNOWN" in rendered
    # `applied` is never asserted False here -- and the payload must not say it.
    assert payload.get("applied") is not False
    assert "no dispatch was recorded" not in rendered, (
        "an expired bound claimed the dispatch did not happen -- a claim about "
        "the world derived from how long we waited (#184)"
    )
    # P6.3(b): expiry reports elapsed, against the operator's OWN bound.
    assert "s against an operator-set" in rendered
    # It ran. That is exactly why the outcome is unknown rather than false.
    assert gc_log.read_text(encoding="utf-8").strip(), "the sling was never invoked"


def test_the_same_dispatch_is_unbounded_when_no_agent_set_a_bound(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """P6.2 negative control for the test above.

    Same shim, same dispatch, no bound installed -- and the sling is NOT
    abandoned. Without this, the expiry above could be any old failure rather
    than the bound the tool installed.
    """
    city_root, rig_root, bin_dir, _ = runtime(tmp_path, sling_delay=1.0)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    monkeypatch.setenv("MCTL_ENABLE_LIVE_DISPATCH", "1")
    monkeypatch.setenv("MCTL_BEADS_FIXTURE", str(rig_root / ".beads" / "issues.jsonl"))

    response = call(
        server(city_root, rig_root), "work_dispatch", {"brief_id": APPROVED_BRIEF, "dry_run": False}
    )
    payload = body(response)

    assert response["result"]["isError"] is False, payload
    assert payload["applied"] is True
    assert "MWRK_DISPATCH_TIMEOUT_UNKNOWN" not in codes(payload)
