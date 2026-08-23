"""Every server tool is reachable from the dashboard, or deliberately is not.

WHY THIS TEST EXISTS. #153: five city-dashboard slices were merged, each
correct against its own acceptance criteria, and not one put a pixel on a page.
The investigation into that found `fleet_sessions` and `city_health` present in
the dashboard's `ALLOWED_TOOLS` and called by nothing -- a permission with no
consumer.

Then the author of that investigation added `molecules_list` and
`molecules_show` to the server (#111) and did not allowlist them at all, which
is one worse: not even permitted. bob caught it in review. Nothing in the suite
did, because nothing compared the two lists.

WHAT THIS CATCHES AND WHAT IT DOES NOT. This asserts *reachability* -- that a
tool the server offers is one the dashboard is allowed to call. It does NOT
assert that anything calls it; a permission is not a consumer, and asserting
otherwise here would be the same mistake in the other direction. Rendering is a
slice's own business (#121) and its own acceptance criterion.

So: this test would have caught the #111 miss. It would NOT have caught the
#153 shape, and it must not be cited as if it had.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.mcp_server import TOOLS  # noqa: E402
from mctl_dashboard.client import ALLOWED_TOOLS  # noqa: E402

#: Server tools the dashboard deliberately may not call, with the reason.
#: An entry here is a decision; absence from both lists is an oversight.
DELIBERATELY_UNREACHABLE: dict[str, str] = {
    "work_dispatch": "mutating dispatch is not driven from the dashboard",
    "work_dispatch_event": "provenance events are written by the dispatcher, not the page",
    "briefs_create": "briefs are produced by the pipeline, not authored in the dashboard",
    "mayor_boot": "a lifecycle action, not a read the page performs",
    "mayor_conservation": "not yet surfaced; no screen consumes it",
    "mayor_city_state": "not yet surfaced; no screen consumes it",
    "work_claim": "not yet surfaced; no screen consumes it (pre-existing, found by this test)",
    "create_issue_bead": "mints a bead from an external GitHub issue; not a read the dashboard performs (#170)",
}

#: `gates_status` is deliberately NOT listed here -- by the time this branch
#: rebased it was allowlisted AND consumed by `screens/city.py`, which is the
#: outcome this test wants.
#:
#: The history is the point. When this test was written, `#119` had merged
#: `mctl_core/gates.py` and registered NO MCP tool at all, so the dashboard
#: could not reach a gate even with permission -- `#153`'s deeper shape, and
#: this test's first run is what surfaced it. It has since been exposed and
#: wired. Recorded so nobody re-derives the finding from an empty list.


def test_every_server_tool_is_allowlisted_or_deliberately_excluded():
    """The gap that let #111 ship unreachable.

    A tool in neither list is not a decision -- it is a tool somebody added to
    the server and forgot the dashboard existed.
    """
    server = {tool.name for tool in TOOLS}
    unaccounted = sorted(server - set(ALLOWED_TOOLS) - set(DELIBERATELY_UNREACHABLE))
    assert not unaccounted, (
        f"server tools neither allowlisted nor deliberately excluded: {unaccounted}. "
        f"Add each to mctl_dashboard.client.ALLOWED_TOOLS, or to "
        f"DELIBERATELY_UNREACHABLE here with the reason."
    )


def test_the_exclusion_list_names_only_tools_that_exist():
    """A stale exclusion is a claim about a tool nobody offers."""
    server = {tool.name for tool in TOOLS}
    ghosts = sorted(set(DELIBERATELY_UNREACHABLE) - server)
    assert not ghosts, f"exclusions naming tools the server does not register: {ghosts}"


def test_the_allowlist_names_only_tools_that_exist():
    server = {tool.name for tool in TOOLS}
    ghosts = sorted(set(ALLOWED_TOOLS) - server)
    assert not ghosts, f"allowlisted tools the server does not register: {ghosts}"


def test_every_exclusion_states_a_reason():
    """`DELIBERATELY` is the whole point: an entry with no reason is a silent
    opt-out wearing the costume of a decision."""
    empty = sorted(name for name, why in DELIBERATELY_UNREACHABLE.items() if not why.strip())
    assert not empty, f"exclusions with no stated reason: {empty}"


def test_the_molecules_tools_are_reachable():
    """The specific regression. Named so a future failure explains itself."""
    assert "molecules_list" in ALLOWED_TOOLS
    assert "molecules_show" in ALLOWED_TOOLS
