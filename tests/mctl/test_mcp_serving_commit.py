"""`#210`/`#172`: a running `mctl mcp serve` must say what commit it is serving.

A merge to main does not reach an already-running server: Python imports
`mctl_core` once per process, so the process keeps answering from the code it
loaded at startup. `create_github_issue` landed at `b7d7a50` and was reachable
from NO running session, and nothing in any response named the stale revision.

The fix here is DETECTABILITY, not hot-reload (`#210` rejects hot-reload: a
silent contract swap mid-session is worse than a visible stale one). The server
reports, in `initialize` and `tools/list`, the commit it imported **at process
start**. A caller compares that to current `origin/main` and DECIDES whether to
deliberately rebind.

The load-bearing property, pinned below: the reported commit is captured ONCE,
at import, so a stale process reports its OWN startup commit. A fresh
`git rev-parse` per request would always look current and hide exactly the drift
this is meant to expose.

`P6.2` governs the read itself (same rule the dashboard's `staleness` obeys):
when the commit cannot be read, the block says so (`known: False`, `commit:
None`) and never substitutes a placeholder that would later be displayed as if
it were a real revision.
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import mcp_server, serving

from test_mcp_server import runtime_fixture, server  # type: ignore


# ---------------------------------------------------------------------------
# sourcing: the commit reflects the PROCESS, captured once at import
# ---------------------------------------------------------------------------


def test_serving_commit_is_captured_once_at_import_not_read_per_call(monkeypatch):
    """The whole point: a stale process reports its OWN startup commit.

    We freeze the module-level value to a commit the checkout is NOT at, and the
    reported info still returns it. A fresh `git rev-parse HEAD` per call would
    return the checkout's real HEAD and mask the drift -- the exact false
    negative `#172` describes.
    """
    monkeypatch.setattr(serving, "SERVING_COMMIT", "deadbee")
    info = serving.serving_info()
    assert info["commit"] == "deadbee"
    assert info["known"] is True


def test_in_a_git_checkout_the_captured_commit_is_a_real_short_sha():
    """Sanity: import-time capture actually read this worktree's HEAD."""
    assert serving.SERVING_COMMIT is not None
    assert serving.SERVING_COMMIT.strip() == serving.SERVING_COMMIT
    assert 6 <= len(serving.SERVING_COMMIT) <= 40


def test_an_unreadable_commit_is_reported_unknown_not_as_a_placeholder(monkeypatch):
    """`P6.2`: if the read failed, say so. Never a sentinel that a caller would
    compare against `origin/main` as though it were a revision."""
    monkeypatch.setattr(serving, "SERVING_COMMIT", None)
    info = serving.serving_info()
    assert info["known"] is False
    assert info["commit"] is None


def test_read_commit_returns_none_off_a_git_tree(tmp_path):
    assert serving.read_commit(tmp_path) is None


# ---------------------------------------------------------------------------
# the wire: initialize and tools/list carry the serving commit
# ---------------------------------------------------------------------------


def test_initialize_reports_the_serving_commit(tmp_path):
    city_root, rig_root = runtime_fixture(tmp_path)
    response = server(city_root, rig_root).handle(
        {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}
    )
    serving_block = response["result"]["_meta"]["mctl"]["serving"]
    assert serving_block["commit"] == serving.SERVING_COMMIT
    assert set(serving_block) >= {"commit", "known", "started_at"}


def test_tools_list_reports_the_serving_commit_alongside_the_tools(tmp_path):
    city_root, rig_root = runtime_fixture(tmp_path)
    response = server(city_root, rig_root).handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )
    result = response["result"]
    # additive: existing consumers still read result["tools"] unchanged.
    assert isinstance(result["tools"], list) and result["tools"]
    assert result["_meta"]["mctl"]["serving"]["commit"] == serving.SERVING_COMMIT


def test_the_serving_commit_is_stable_across_calls_in_one_process(tmp_path):
    """It names the running code, so it does not move under a caller mid-session
    (a re-read per call could, if the tree changed)."""
    city_root, rig_root = runtime_fixture(tmp_path)
    instance = server(city_root, rig_root)
    first = instance.handle({"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}})
    second = instance.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
    assert (
        first["result"]["_meta"]["mctl"]["serving"]
        == second["result"]["_meta"]["mctl"]["serving"]
    )


def test_a_caller_can_detect_staleness_by_comparing_to_current_head(tmp_path):
    """The end-to-end reason this field exists: feed the reported commit and the
    caller's current origin/main into the same `staleness` comparison the
    dashboard uses, and drift is visible."""
    from mctl_dashboard import staleness

    city_root, rig_root = runtime_fixture(tmp_path)
    response = server(city_root, rig_root).handle(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )
    served = response["result"]["_meta"]["mctl"]["serving"]["commit"]
    assert staleness.compare(served=served, current="ffffff0").is_stale is True
    assert staleness.compare(served=served, current=served).is_stale is False
