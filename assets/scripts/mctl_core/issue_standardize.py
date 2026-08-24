"""#185/#52: make an existing GitHub issue hygienic in place, ADDITIVELY.

`update-issue` consolidates an issue body into one canonical statement and folds
the prior versions away. That is destructive on an agent-maintained tracker,
where the history of an issue is evidence -- so this tool is built on the OPPOSITE
contract: it appends a `## Standardized restatement` section and leaves every
existing byte of the body in place. A transform, not a gate.

`fetch_issue` and the `edit_issue` write live in `github_issues.py`; the write is
carried on the shared `GithubWrite` effect so a dry run previews the composed
body and shells nothing.
"""
from __future__ import annotations

from dataclasses import dataclass

from .context import MctlContext
from .diagnostics import Diagnostic, Severity
from .effects import EffectPlan, GithubWrite
from .github_issues import GithubIssueError, IssueSnapshot, fetch_issue


#: The heading that marks a body as already standardized. Idempotence keys on
#: its presence: a second run must not append a second restatement.
STANDARDIZED_MARKER = "## Standardized restatement"


@dataclass(frozen=True)
class StandardizeIssueInput:
    repo: str
    issue_number: int


def plan_standardize_github_issue(
    ctx: MctlContext, request: StandardizeIssueInput
) -> EffectPlan:
    """Plan an additive standardization edit of one open issue.

    Idempotent by construction: if the body already carries the marker, the plan
    holds NO github write and an INFO advisory, and the handler serves it as a
    no-op (`applied: false`) whether or not a dry run was asked for -- re-editing
    an already-standardized issue would append a second restatement, which is the
    consolidation-adjacent damage #52 forbids.
    """
    try:
        issue = fetch_issue(request.repo, request.issue_number)
    except GithubIssueError as error:
        raise _fetch_failed(ctx, request, error) from error

    if STANDARDIZED_MARKER in issue.body:
        return EffectPlan(
            trace_id=ctx.trace_id,
            operation="standardize_github_issue",
            target_brief_id=issue.reference,
            preconditions=(),
            bead_updates=(),
            cache_updates=(),
            event_writes=(),
            trace_writes=(),
            github_writes=(),
            advisories=(
                Diagnostic(
                    Severity.INFO,
                    "MGHW_ALREADY_STANDARDIZED",
                    f"{issue.reference} already carries a standardized restatement; nothing to do.",
                    facts={
                        "city_path": str(ctx.city_root),
                        "rig_name": ctx.rig_id,
                    },
                    trace_id=ctx.trace_id,
                ),
            ),
        )

    composed = issue.body + "\n\n" + _restatement(issue)
    write = GithubWrite(
        kind="edit",
        repo=request.repo,
        number=request.issue_number,
        body=composed,
    )
    return EffectPlan(
        trace_id=ctx.trace_id,
        operation="standardize_github_issue",
        target_brief_id=issue.reference,
        preconditions=(),
        bead_updates=(),
        cache_updates=(),
        event_writes=(),
        trace_writes=(),
        github_writes=(write,),
    )


def _restatement(issue: IssueSnapshot) -> str:
    """The appended, template-shaped section. Never rewrites the body above it."""
    labels = ", ".join(issue.labels) if issue.labels else "(none)"
    return (
        f"{STANDARDIZED_MARKER}\n"
        "\n"
        "_Appended by mctl `standardize_github_issue` (#52): additive only. The "
        "original body above is preserved unchanged._\n"
        "\n"
        "### Title\n"
        f"{issue.title}\n"
        "\n"
        "### Labels\n"
        f"{labels}\n"
        "\n"
        "### Original report\n"
        "See the full original body above this section.\n"
    )


def _fetch_failed(
    ctx: MctlContext, request: StandardizeIssueInput, error: GithubIssueError
):
    from .effects import MutationError

    return MutationError(
        Diagnostic(
            Severity.FATAL,
            "MGHW_GH_UNAVAILABLE",
            f"Could not read {request.repo}#{request.issue_number}: {error}",
            facts={"city_path": str(ctx.city_root), "rig_name": ctx.rig_id},
            trace_id=ctx.trace_id,
        )
    )
