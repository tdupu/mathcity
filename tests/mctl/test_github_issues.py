"""`github_issues.fetch_issue` -- the read half of #170.

subprocess is monkeypatched via `subprocess.run`; these tests exercise the
parsing and error-shaping, not `gh` itself.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.github_issues import GithubIssueError, fetch_issue


def fake_run(returncode: int, stdout: str = "", stderr: str = ""):
    def _fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(args, returncode, stdout=stdout, stderr=stderr)

    return _fake_run


def test_a_clean_read_returns_a_populated_snapshot(monkeypatch):
    payload = json.dumps(
        {
            "title": "bug: thing is broken",
            "body": "steps to reproduce",
            "labels": [{"name": "kind/bug"}, {"name": "priority/p1"}],
            "state": "OPEN",
            "url": "https://github.com/tdupu/mathcity/issues/1",
            "number": 1,
        }
    )
    monkeypatch.setattr(subprocess, "run", fake_run(0, stdout=payload))

    issue = fetch_issue("tdupu/mathcity", 1)

    assert issue.title == "bug: thing is broken"
    assert issue.labels == ("kind/bug", "priority/p1")
    assert issue.is_open is True
    assert issue.reference == "tdupu/mathcity#1"


def test_a_closed_issue_is_reported_not_open(monkeypatch):
    payload = json.dumps(
        {"title": "t", "body": "b", "labels": [], "state": "CLOSED", "url": "u", "number": 2}
    )
    monkeypatch.setattr(subprocess, "run", fake_run(0, stdout=payload))

    issue = fetch_issue("tdupu/mathcity", 2)

    assert issue.is_open is False


def test_gh_failure_raises_rather_than_returning_a_blank_snapshot(monkeypatch):
    monkeypatch.setattr(subprocess, "run", fake_run(1, stderr="issue not found"))

    with pytest.raises(GithubIssueError, match="not found"):
        fetch_issue("tdupu/mathcity", 999)


def test_gh_missing_raises_a_clear_error(monkeypatch):
    def _missing(*args, **kwargs):
        raise FileNotFoundError("gh")

    monkeypatch.setattr(subprocess, "run", _missing)

    with pytest.raises(GithubIssueError, match="not installed"):
        fetch_issue("tdupu/mathcity", 1)


def test_malformed_json_raises_rather_than_crashing(monkeypatch):
    monkeypatch.setattr(subprocess, "run", fake_run(0, stdout="not json"))

    with pytest.raises(GithubIssueError, match="unparseable"):
        fetch_issue("tdupu/mathcity", 1)
