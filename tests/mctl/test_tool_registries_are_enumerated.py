"""Adding a tool means updating FIVE registries, and nothing said so.

THE PROBLEM, and it is not detection
------------------------------------
Every one of the five registries below already has its own test that fails when
it drifts from `TOOLS`. Those tests work -- they caught two tool additions on
2026-08-28, correctly, twice each.

What no test did was tell you HOW MANY there were. So the failure mode is not
"a drift goes unnoticed", it is:

    fix registry 1, 2, 3, 4  ->  run  ->  green  ->  believe you are done
    (the fifth only fires for MUTATING tools, so a read-only tool never meets it
     and its author learns four; the next author, adding a write, learns five)

That happened. `artifact_locate` (read-only) taught its author FOUR registries.
He wrote that four-item list into a bead and relayed it to a peer who was adding
a tool. `bead_close` (mutating) then hit the fifth, after the other four were
green -- so the relayed list was wrong, and the peer would have gone red
believing they were finished.

A sixth test asserting "count matches declared ToolSpecs" would add nothing:
these five already compare NAMES, which is strictly stronger than a count. The
gap is that the first red tells you about one registry when there are five.

WHAT THIS TEST DOES
-------------------
Checks all five in one pass and reports EVERY out-of-sync registry in a single
failure, naming the file to edit for each. One red, complete list.

HOW IT WAS PROVEN TO WORK
-------------------------
Red-first by deliberate mutation: `DECLARED_TOOLS` was desynced and this test
was confirmed to fail while naming all five registries and their state, then the
mutation was reverted. A test for a "you missed one" defect that was never made
to see a missing one would be asserting its own premise.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mctl_core.mcp_server import TOOLS  # noqa: E402

#: Every place a tool name must be listed, and the file to edit. Keep this in
#: step with reality: a registry added and not listed here recreates the exact
#: defect this file exists for.
REGISTRIES = (
    ("DECLARED_TOOLS", "tests/mctl/test_mcp_server.py", "all tools"),
    ("DELIBERATELY_UNREACHABLE / ALLOWED_TOOLS",
     "tests/mctl/test_dashboard_tool_reachability.py", "all tools"),
    ("EXPECTED_TOOLS (+ two hardcoded counts)",
     "assets/scripts/mctl_mcp_harness.py + tests/mctl/test_mcp_client_harness.py",
     "all tools"),
    ("mutating-tools list", "tests/mctl/test_mcp_schema_snapshots.py", "MUTATING tools only"),
    ("schema snapshot (MCTL_UPDATE_MCP_SNAPSHOT=1)",
     "tests/mctl/fixtures/mcp_tool_schemas.json", "all tools"),
)


def _declared() -> set[str]:
    return {spec.name for spec in TOOLS}


def _mutating() -> set[str]:
    return {spec.name for spec in TOOLS if getattr(spec, "mutating", False)}


def _registry_contents() -> dict[str, set[str]]:
    """Read each registry's actual contents, by import, never by re-listing here."""
    import json

    from test_mcp_server import DECLARED_TOOLS
    from test_dashboard_tool_reachability import DELIBERATELY_UNREACHABLE
    from mctl_dashboard.client import ALLOWED_TOOLS
    from mctl_mcp_harness import EXPECTED_TOOLS

    snapshot_path = REPO_ROOT / "tests" / "mctl" / "fixtures" / "mcp_tool_schemas.json"
    snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))

    return {
        "DECLARED_TOOLS": set(DECLARED_TOOLS),
        "DELIBERATELY_UNREACHABLE / ALLOWED_TOOLS": set(DELIBERATELY_UNREACHABLE) | set(ALLOWED_TOOLS),
        "EXPECTED_TOOLS (+ two hardcoded counts)": set(EXPECTED_TOOLS),
        "mutating-tools list": {n for n, e in snapshot.items() if e.get("mutating")},
        "schema snapshot (MCTL_UPDATE_MCP_SNAPSHOT=1)": set(snapshot),
    }


def test_every_registry_lists_every_tool_and_the_failure_names_all_of_them() -> None:
    """One red, five answers.

    The value is entirely in the failure message: a developer who has just added
    a tool should learn the COMPLETE set of places to edit from the first run,
    not discover the fifth after the other four have gone green.
    """
    declared = _declared()
    mutating = _mutating()
    contents = _registry_contents()

    problems: list[str] = []
    for name, where, scope in REGISTRIES:
        expected = mutating if scope == "MUTATING tools only" else declared
        actual = contents[name]
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        if missing or extra:
            detail = []
            if missing:
                detail.append(f"MISSING {missing}")
            if extra:
                detail.append(f"UNEXPECTED {extra}")
            problems.append(f"  [{name}] {'; '.join(detail)}\n      edit: {where}  ({scope})")

    assert not problems, (
        "Tool registries are out of sync. ALL FIVE places a tool must be listed "
        f"are checked here; {len(problems)} of {len(REGISTRIES)} need editing:\n"
        + "\n".join(problems)
        + "\n\n  The other registries are in sync. The complete set is:\n"
        + "\n".join(f"      {n}  ->  {w}  ({s})" for n, w, s in REGISTRIES)
        + "\n\n  Note the mutating-tools list fires ONLY for mutating tools, which is why "
        "a read-only tool's author learns four registries and a write's author learns five."
    )


def test_the_enumeration_covers_every_registry_this_repo_actually_has() -> None:
    """A guard on the list above: five entries, and each names a real file.

    If someone adds a sixth registry without listing it here, this file becomes
    the thing it was written to prevent -- an authoritative-looking list that is
    quietly incomplete.
    """
    assert len(REGISTRIES) == 5
    for name, where, _ in REGISTRIES:
        for path in where.split(" + "):
            assert (REPO_ROOT / path.strip()).exists(), f"{name} names a missing path: {path}"
