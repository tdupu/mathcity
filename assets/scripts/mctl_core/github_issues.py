"""Read-only GitHub issue snapshots, for turning a tracker issue into a bead.

`#170`: no typed surface mints a bead from an existing GitHub issue, so a
brief whose provenance is a tracker issue has nothing legal to depend on
(`MWRK011`). This module is the read half -- fetching and normalising the
issue -- kept separate from `effects.py`'s planning so the network call is
one obvious seam, not folded into a mutation planner.

Server-side `gh` invocation only. The MCP-only handicap in `mayor-math-prime`
constrains AGENTS routing around the control surface; it says nothing about
what a typed tool does inside its own implementation, and a tool that reads
an issue is exactly the kind of thing a typed tool exists to encapsulate.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import subprocess


class GithubIssueError(Exception):
    """`gh` could not answer, or answered with something unusable."""


@dataclass(frozen=True)
class IssueSnapshot:
    repo: str
    number: int
    title: str
    body: str
    labels: tuple[str, ...]
    state: str
    url: str

    @property
    def is_open(self) -> bool:
        return self.state.upper() == "OPEN"

    @property
    def reference(self) -> str:
        """`owner/repo#N` -- the provenance string, and the AUTHORIZER value."""
        return f"{self.repo}#{self.number}"


def fetch_issue(repo: str, number: int, *, timeout: int = 30) -> IssueSnapshot:
    """Read one issue's current state. Never mutates GitHub.

    Raises `GithubIssueError` on anything that is not a clean read -- `gh`
    absent, not authenticated, the issue not found, or a malformed response --
    so a caller building on this never mistakes a failed read for an issue
    that legitimately has an empty body.
    """
    try:
        result = subprocess.run(
            [
                "gh",
                "issue",
                "view",
                str(number),
                "--repo",
                repo,
                "--json",
                "title,body,labels,state,url,number",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as error:
        raise GithubIssueError("gh is not installed") from error
    except subprocess.TimeoutExpired as error:
        raise GithubIssueError(f"gh issue view timed out after {timeout}s") from error

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise GithubIssueError(
            f"gh issue view {repo}#{number} failed: {stderr or 'no stderr'}"
        )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise GithubIssueError(
            f"gh issue view {repo}#{number} returned unparseable JSON"
        ) from error

    labels = tuple(
        str(label.get("name", "")) for label in payload.get("labels", []) if label.get("name")
    )
    return IssueSnapshot(
        repo=repo,
        number=int(payload.get("number", number)),
        title=str(payload.get("title") or ""),
        body=str(payload.get("body") or ""),
        labels=labels,
        state=str(payload.get("state") or ""),
        url=str(payload.get("url") or ""),
    )
