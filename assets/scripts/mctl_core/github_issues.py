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
import re
import subprocess


class GithubIssueError(Exception):
    """`gh` could not answer, or answered with something unusable."""


#: `https://github.com/<owner>/<repo>/issues/<n>` -- the only shape we parse.
#: Anything else returns None rather than a guess.
_ISSUE_URL = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/issues/(?P<number>\d+)/?$"
)


def rig_for_issue(issue_url: str) -> str | None:
    """The rig an issue belongs to, derived from the tracker that holds it.

    Taylor: *"if you are pulling an issue from a github issue tracker, then that
    tracker belongs to the repo of a rig. The obvious spot is that rig."* The
    rig is therefore DETERMINED, not chosen -- an override belongs at the call
    site for the exceptional case, not here.

    Returns None on anything unparseable. A guessed rig writes a brief into the
    wrong store, which fails at creation if you are lucky and succeeds in the
    wrong place if you are not.

    stripes' parser, shared for #190's `commission_brief` and #170's
    `create_issue_bead` so the two tools cannot resolve a rig differently for
    the same issue -- one copy, imported here rather than reimplemented.
    """
    match = _ISSUE_URL.match(issue_url.strip())
    return match.group("repo") if match else None


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
