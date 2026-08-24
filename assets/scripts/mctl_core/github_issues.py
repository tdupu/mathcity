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

try:  # PyYAML ships in this environment; a missing parser must not be a wall.
    import yaml  # type: ignore
except Exception:  # pragma: no cover - defensive
    yaml = None  # type: ignore


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


# --- write half (#185) -------------------------------------------------------
#
# `github_issues.py` was read-only. These are the GitHub WRITES the typed intake
# tools need. They shell out to `gh` exactly as `orders.py` shells to `gc` and
# `fetch_issue` above shells for the read -- one obvious subprocess seam, never
# folded into the effect planner. Nothing here runs on a dry run: the planner
# describes the write, and only `apply_effect_plan` reaches these functions.


def create_issue(
    repo: str, title: str, body: str, labels: tuple[str, ...] = (), *, timeout: int = 30
) -> str:
    """`gh issue create` for `repo`, returning the new issue URL.

    The body is passed on stdin (`--body-file -`) rather than as an argument, so
    a multi-paragraph template-shaped body with shell metacharacters is never
    re-quoted. Raises `GithubIssueError` on anything that is not a clean create,
    so a caller never mistakes a failed post for a filed issue.
    """
    args = ["gh", "issue", "create", "--repo", repo, "--title", title, "--body-file", "-"]
    for label in labels:
        args += ["--label", label]
    try:
        result = subprocess.run(
            args,
            input=body,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as error:
        raise GithubIssueError("gh is not installed") from error
    except subprocess.TimeoutExpired as error:
        raise GithubIssueError(f"gh issue create timed out after {timeout}s") from error

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise GithubIssueError(
            f"gh issue create --repo {repo} failed: {stderr or 'no stderr'}"
        )
    url = (result.stdout or "").strip().splitlines()[-1] if result.stdout.strip() else ""
    if not url:
        raise GithubIssueError("gh issue create returned no issue URL")
    return url


def edit_issue(repo: str, number: int, body: str, *, timeout: int = 30) -> str:
    """`gh issue edit <n> --body-file -`, replacing the body, returning the URL.

    The composed body is the caller's responsibility -- for #52's additive
    standardization it is the ORIGINAL body plus an appended section, so this
    function only transports bytes and never consolidates.
    """
    args = ["gh", "issue", "edit", str(number), "--repo", repo, "--body-file", "-"]
    try:
        result = subprocess.run(
            args,
            input=body,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except FileNotFoundError as error:
        raise GithubIssueError("gh is not installed") from error
    except subprocess.TimeoutExpired as error:
        raise GithubIssueError(f"gh issue edit timed out after {timeout}s") from error

    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        raise GithubIssueError(
            f"gh issue edit {repo}#{number} failed: {stderr or 'no stderr'}"
        )
    url = (result.stdout or "").strip().splitlines()[-1] if result.stdout.strip() else ""
    return url or f"https://github.com/{repo}/issues/{number}"


def required_template_sections(repo: str, *, timeout: int = 30) -> tuple[str, ...]:
    """The REQUIRED field labels of the target repo's live issue-form templates.

    The repo's `.github/ISSUE_TEMPLATE/*.yml` is the enforcement point -- the
    `create-issue` skill's rule -- and it changes without telling you, so this
    reads it LIVE rather than baking a copy in. A GitHub issue FORM renders each
    field's `label` as a `### <label>` heading in the created body, so the set of
    labels whose `validations.required` is true is exactly the set of headings a
    conformant body must carry.

    Best-effort by design: a template that cannot be listed, fetched, or parsed
    returns `()` rather than raising. Refusing to file an issue because the
    template could not be READ would turn a hygiene aid into a wall; the planner
    surfaces that unreadability as an advisory instead.
    """
    if yaml is None:
        return ()
    try:
        listing = subprocess.run(
            ["gh", "api", f"repos/{repo}/contents/.github/ISSUE_TEMPLATE"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired) as error:
        raise GithubIssueError(f"gh api could not list the issue templates: {error}")
    if listing.returncode != 0:
        # No template directory is a legitimate answer, not an error: many repos
        # have none, and such a repo simply imposes no required sections.
        return ()
    try:
        entries = json.loads(listing.stdout)
    except json.JSONDecodeError as error:
        raise GithubIssueError("gh api returned unparseable template listing") from error

    required: list[str] = []
    for entry in entries if isinstance(entries, list) else []:
        name = str(entry.get("name", ""))
        if not name.endswith((".yml", ".yaml")):
            continue
        raw = _fetch_template_file(repo, name, timeout=timeout)
        if raw is None:
            continue
        required.extend(_required_labels(raw))
    # De-duplicate, preserving first-seen order, so a label required by two forms
    # is reported once.
    seen: dict[str, None] = {}
    for label in required:
        seen.setdefault(label, None)
    return tuple(seen)


def _fetch_template_file(repo: str, name: str, *, timeout: int) -> str | None:
    try:
        result = subprocess.run(
            [
                "gh",
                "api",
                f"repos/{repo}/contents/.github/ISSUE_TEMPLATE/{name}",
                "--jq",
                ".content",
            ],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0 or not result.stdout.strip():
        return None
    import base64

    try:
        return base64.b64decode(result.stdout.strip()).decode("utf-8")
    except Exception:  # pragma: no cover - defensive
        return None


def _required_labels(raw_yaml: str) -> list[str]:
    if yaml is None:  # pragma: no cover - guarded by caller
        return []
    try:
        form = yaml.safe_load(raw_yaml)
    except Exception:  # pragma: no cover - a malformed form imposes nothing
        return []
    if not isinstance(form, dict):
        return []
    labels: list[str] = []
    for field in form.get("body", []) or []:
        if not isinstance(field, dict):
            continue
        validations = field.get("validations") or {}
        attributes = field.get("attributes") or {}
        label = attributes.get("label")
        if isinstance(validations, dict) and validations.get("required") and label:
            labels.append(str(label))
    return labels
