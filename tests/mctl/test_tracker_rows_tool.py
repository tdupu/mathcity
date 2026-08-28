"""The `tracker_rows` MCP tool (#186) -- the read seam.

Two independent reads sit behind this tool, and the whole point of the tests
below is that **their failures stay separate**:

* GitHub not answering -> `issues_unreadable` set, no rows. Returning `[]` for
  a failed read would claim the repo has no issues.
* The bead store not answering -> issues still render, but every row is
  `pairing: "unknown"` with a reason, and `summary.needs_bead` is withheld.

That second one is not fussiness. #180 mints a bead for every issue that
appears to lack one, so a silently-swallowed store failure would mint
duplicates on top of the beads it could not see. `needs_bead` under `unknown`
is therefore false by construction, and the summary refuses a count rather than
reporting one over a partial denominator.

Both reads are stubbed. These tests never touch GitHub or a bead store, so they
cannot pass or fail on either being reachable.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core import mcp_server  # noqa: E402
from mctl_core.beads import Bead, BeadReadError  # noqa: E402
from mctl_core.context import MctlContext  # noqa: E402
from mctl_core.github_issues import GithubIssueError, IssueSnapshot  # noqa: E402


def _ctx(tmp_path: Path) -> MctlContext:
    return MctlContext(
        city_root=tmp_path,
        rig_id="mathcity",
        rig_root=tmp_path / "rig",
        beads_fixture=tmp_path / "issues.jsonl",
        rig_db=".beads",
        source_checkout=tmp_path,
        paths_toml=tmp_path / "paths.toml",
        gates_toml=tmp_path / "gates.toml",
        invocation_cwd=tmp_path,
        trace_id="trace-tracker-1",
        warnings=(),
        discovery_path="test",
        city_active=None,
        city_endpoint=None,
    )


def _snap(number: int, *, state: str = "OPEN") -> IssueSnapshot:
    return IssueSnapshot(
        repo="tdupu/mathcity",
        number=number,
        title=f"issue {number}",
        body="",
        labels=(),
        state=state,
        url=f"https://github.com/tdupu/mathcity/issues/{number}",
    )


def _bead(bead_id: str, ref: str | None, status: str = "open") -> Bead:
    raw = {"id": bead_id, "status": status, "title": "t"}
    if ref is not None:
        raw["external_ref"] = ref
    return Bead(
        id=bead_id,
        title="t",
        status=status,
        issue_type="task",
        labels=(),
        source_dependencies=(),
        created_at=None,
        updated_at=None,
        raw=raw,
    )


@pytest.fixture
def stubs(monkeypatch):
    """Stub both reads; each test sets what it needs."""
    state: dict = {"issues": [], "beads": [], "issue_error": None, "bead_error": None}

    def fake_list_issues(repo, **kwargs):
        if state["issue_error"]:
            raise state["issue_error"]
        return tuple(state["issues"])

    def fake_read_beads(rig_root, **kwargs):
        if state["bead_error"]:
            raise state["bead_error"]
        return tuple(state["beads"])

    monkeypatch.setattr("mctl_core.github_issues.list_issues", fake_list_issues)
    monkeypatch.setattr("mctl_core.beads.read_beads", fake_read_beads)
    return state


def _call(tmp_path, repo="tdupu/mathcity"):
    return mcp_server._handle_tracker_rows(_ctx(tmp_path), {"repo": repo})


# -- registration ----------------------------------------------------------


def test_the_tool_is_registered() -> None:
    assert "tracker_rows" in mcp_server.TOOLS_BY_NAME


def test_repo_is_required_not_guessed() -> None:
    """Nothing infers which repo; the caller names it."""
    spec = mcp_server.TOOLS_BY_NAME["tracker_rows"]
    assert "repo" in spec.input_schema.get("required", [])


# -- the happy path (controls) ---------------------------------------------


def test_pairs_an_issue_to_its_bead(tmp_path, stubs) -> None:
    stubs["issues"] = [_snap(56)]
    stubs["beads"] = [_bead("mc-2kf", "gh-56")]
    out = _call(tmp_path)
    assert out["issues_unreadable"] is None
    assert out["rows"][0]["pairing"] == "paired"
    assert out["rows"][0]["bead_ids"] == ["mc-2kf"]


def test_an_issue_with_no_bead_is_unpaired_and_needs_one(tmp_path, stubs) -> None:
    stubs["issues"] = [_snap(56)]
    stubs["beads"] = []
    out = _call(tmp_path)
    assert out["rows"][0]["pairing"] == "unpaired"
    assert out["rows"][0]["needs_bead"] is True
    assert out["summary"]["needs_bead"] == 1


# -- GitHub failing --------------------------------------------------------


def test_github_failure_is_reported_not_rendered_as_no_issues(tmp_path, stubs) -> None:
    stubs["issue_error"] = GithubIssueError("gh is not installed")
    out = _call(tmp_path)
    assert out["issues_unreadable"] == "gh is not installed"
    assert out["rows"] == []


def test_an_empty_repo_is_not_an_error(tmp_path, stubs) -> None:
    """Control: [] with issues_unreadable None means READ, and none."""
    stubs["issues"] = []
    out = _call(tmp_path)
    assert out["issues_unreadable"] is None
    assert out["rows"] == []


# -- the bead store failing ------------------------------------------------


def test_a_store_failure_still_renders_issues_but_marks_them_unknown(tmp_path, stubs) -> None:
    stubs["issues"] = [_snap(56), _snap(57)]
    stubs["bead_error"] = BeadReadError("dolt refused the connection")
    out = _call(tmp_path)
    assert out["issues_unreadable"] is None
    assert [r["pairing"] for r in out["rows"]] == ["unknown", "unknown"]
    assert out["rows"][0]["unknown_reason"] == "dolt refused the connection"


def test_a_store_failure_never_reports_needing_a_bead(tmp_path, stubs) -> None:
    """Minting off an unread store is how duplicates get made."""
    stubs["issues"] = [_snap(56)]
    stubs["bead_error"] = BeadReadError("timeout")
    out = _call(tmp_path)
    assert out["rows"][0]["needs_bead"] is False
    assert out["summary"]["needs_bead"] is None


def test_an_empty_store_and_an_unreadable_store_differ(tmp_path, stubs) -> None:
    """The control proving the two are not collapsed."""
    stubs["issues"] = [_snap(56)]
    stubs["beads"] = []
    answered = _call(tmp_path)
    stubs["bead_error"] = BeadReadError("x")
    refused = _call(tmp_path)
    assert answered["summary"]["needs_bead"] == 1
    assert refused["summary"]["needs_bead"] is None
    assert answered["rows"][0]["pairing"] != refused["rows"][0]["pairing"]


# -- the pairing rules survive the tool boundary ---------------------------


def test_a_near_miss_ref_does_not_pair_through_the_tool(tmp_path, stubs) -> None:
    """mc-vwkn7's shape must not reappear at the seam."""
    stubs["issues"] = [_snap(56)]
    stubs["beads"] = [_bead("mc-x", "gh-56-followup")]
    out = _call(tmp_path)
    assert out["rows"][0]["pairing"] == "unpaired"


def test_two_beads_on_one_issue_are_flagged(tmp_path, stubs) -> None:
    stubs["issues"] = [_snap(53)]
    stubs["beads"] = [_bead("mc-a", "gh-53"), _bead("mc-b", "gh-53")]
    out = _call(tmp_path)
    assert out["rows"][0]["is_duplicated"] is True


def test_an_open_issue_with_only_a_closed_bead_is_flagged(tmp_path, stubs) -> None:
    """Live case #55 / mc-6jk."""
    stubs["issues"] = [_snap(55)]
    stubs["beads"] = [_bead("mc-6jk", "gh-55", status="closed")]
    out = _call(tmp_path)
    assert out["rows"][0]["is_orphaned_by_bead"] is True


def test_a_bead_without_a_ref_pairs_with_nothing(tmp_path, stubs) -> None:
    stubs["issues"] = [_snap(56)]
    stubs["beads"] = [_bead("mc-plain", None)]
    out = _call(tmp_path)
    assert out["rows"][0]["pairing"] == "unpaired"
