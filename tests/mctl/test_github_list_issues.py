"""`list_issues` -- the batch GitHub read behind the #186 tracker.

`fetch_issue` reads one issue. A tracker row per open issue would be ~107
sequential `gh` calls on this repo: slow, and a different failure surface (one
flaky call in a hundred, versus one call that either worked or did not).

The property that matters most here is **a failed read must never look like an
empty repo.** Every failure path raises `GithubIssueError` rather than
returning `()`. On the tracker those two render differently -- "this repo has
no open issues" versus "GitHub did not answer" -- and collapsing them is the
P6.2 failure this codebase keeps naming. Half these tests exist for that one
distinction.

All subprocess interaction is stubbed. These tests never touch the network, so
they cannot pass or fail on GitHub's availability.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core import github_issues  # noqa: E402


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


def _stub(monkeypatch, *, result=None, raises=None):
    """Replace subprocess.run for the duration of one test."""

    def fake_run(*args, **kwargs):
        if raises is not None:
            raise raises
        return result

    monkeypatch.setattr(github_issues.subprocess, "run", fake_run)


ONE_ISSUE = json.dumps(
    [
        {
            "number": 186,
            "title": "a tracker view",
            "state": "OPEN",
            "url": "https://github.com/tdupu/mathcity/issues/186",
            "labels": [{"name": "feat"}, {"name": "dashboard"}],
        }
    ]
)


# -- the happy path (controls) ---------------------------------------------


def test_reads_issues(monkeypatch) -> None:
    _stub(monkeypatch, result=_Result(stdout=ONE_ISSUE))
    issues = github_issues.list_issues("tdupu/mathcity")
    assert len(issues) == 1
    assert issues[0].number == 186
    assert issues[0].title == "a tracker view"
    assert issues[0].labels == ("feat", "dashboard")


def test_an_empty_repo_returns_an_empty_tuple(monkeypatch) -> None:
    """The control for every failure test below: () means READ, and none."""
    _stub(monkeypatch, result=_Result(stdout="[]"))
    assert github_issues.list_issues("tdupu/mathcity") == ()


def test_bodies_are_not_fetched(monkeypatch) -> None:
    """Deliberate: the tracker renders no bodies, and 200 of them is a big payload."""
    _stub(monkeypatch, result=_Result(stdout=ONE_ISSUE))
    assert github_issues.list_issues("tdupu/mathcity")[0].body == ""


def test_the_command_does_not_request_body(monkeypatch) -> None:
    seen: dict = {}

    def fake_run(cmd, **kwargs):
        seen["cmd"] = cmd
        return _Result(stdout="[]")

    monkeypatch.setattr(github_issues.subprocess, "run", fake_run)
    github_issues.list_issues("tdupu/mathcity")
    joined = " ".join(seen["cmd"])
    assert "body" not in joined
    assert "issue list" in joined.replace("  ", " ")


# -- failures must RAISE, never return () ----------------------------------


def test_a_nonzero_exit_raises(monkeypatch) -> None:
    _stub(monkeypatch, result=_Result(returncode=1, stderr="not authenticated"))
    with pytest.raises(github_issues.GithubIssueError, match="not authenticated"):
        github_issues.list_issues("tdupu/mathcity")


def test_missing_gh_raises(monkeypatch) -> None:
    _stub(monkeypatch, raises=FileNotFoundError())
    with pytest.raises(github_issues.GithubIssueError, match="not installed"):
        github_issues.list_issues("tdupu/mathcity")


def test_a_timeout_raises(monkeypatch) -> None:
    _stub(monkeypatch, raises=subprocess.TimeoutExpired(cmd="gh", timeout=60))
    with pytest.raises(github_issues.GithubIssueError, match="timed out"):
        github_issues.list_issues("tdupu/mathcity")


def test_unparseable_json_raises(monkeypatch) -> None:
    _stub(monkeypatch, result=_Result(stdout="not json"))
    with pytest.raises(github_issues.GithubIssueError, match="unparseable"):
        github_issues.list_issues("tdupu/mathcity")


def test_a_non_list_payload_raises(monkeypatch) -> None:
    """`gh` returning an object where a list was asked for is a broken read."""
    _stub(monkeypatch, result=_Result(stdout='{"number": 1}'))
    with pytest.raises(github_issues.GithubIssueError, match="non-list"):
        github_issues.list_issues("tdupu/mathcity")


# -- malformed rows --------------------------------------------------------


def test_a_row_without_a_number_is_skipped_not_invented(monkeypatch) -> None:
    """Such a row cannot be paired or linked; a made-up number would be worse."""
    payload = json.dumps([{"title": "no number"}, {"number": 7, "title": "ok"}])
    _stub(monkeypatch, result=_Result(stdout=payload))
    assert [i.number for i in github_issues.list_issues("tdupu/mathcity")] == [7]


def test_a_label_without_a_name_is_dropped(monkeypatch) -> None:
    payload = json.dumps(
        [{"number": 1, "title": "t", "labels": [{"name": "keep"}, {"colour": "red"}]}]
    )
    _stub(monkeypatch, result=_Result(stdout=payload))
    assert github_issues.list_issues("tdupu/mathcity")[0].labels == ("keep",)


def test_missing_fields_become_empty_strings_not_none(monkeypatch) -> None:
    _stub(monkeypatch, result=_Result(stdout=json.dumps([{"number": 1}])))
    issue = github_issues.list_issues("tdupu/mathcity")[0]
    assert (issue.title, issue.url, issue.state) == ("", "", "")
