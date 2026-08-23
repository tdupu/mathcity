"""commission_brief: a source bead becomes a commission brief in the pile (#190).

A COMMISSION AUTHORIZES PLANNING, NOT WORK. `commission-work-briefed`'s own
description is explicit that "actual work dispatch happens only after that brief
is approved". That distinction is what makes the CT4.5 commission exemption safe
and it is one hop deep: the plan this brief commissions returns as its own brief.

WHY A SEPARATE SURFACE. `briefs_create` makes *a* brief from arbitrary
title/body/sources and knows nothing about commissions. `#170` is the inverse
half -- *have a brief, need a bead*. This is *have a bead, need a brief*.

WHY NOT A FORMULA. Formulas cannot create a bead mid-run and reference its id in
a later step: vars are static per-dispatch, not runtime handoffs (pink, while
designing #179). A formula must therefore CALL this, not implement it.

THE FIVE CONSTRAINTS, each of which produced a real failure during the by-hand
proof on 2026-08-23 (`gh#1` -> `mc-7d0` -> `mc-60j` -> readiness "ready"):

  1. sources required and non-empty -- omitting mints a brief that is
     B2.1-incomplete at WARN and FATAL at dispatch (MWRK011)
  2. bead and brief in the SAME STORE -- a city-root bead against a rig-scoped
     brief fails with "no issue found matching <id>"
  3. tracker provenance in METADATA, not labels -- bd rejects `kind/bug`
     (MBRF033), and dropping the namespace is lossy
  4. bd labels carry only what the brief IS
  5. pile only -- B2.10 reserves the stack for brief-shuffle

VALIDATION IS SEPARATE FROM PLANNING ON PURPOSE. `validate_commission` raises
before anything is written, so a caller cannot half-create. Constraints 1 and 2
are both cheap to check and expensive to discover afterwards.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence

#: The brief's own kind. One token, no namespace: `kind/commission` was invented
#: once and MBRF033 correctly refused it, because bd labels cannot hold slashes.
COMMISSION_LABEL = "commission"

#: `https://github.com/<owner>/<repo>/issues/<n>` -- the only shape we parse.
#: Anything else returns None rather than a guess.
_ISSUE_URL = re.compile(
    r"^https?://github\.com/(?P<owner>[^/]+)/(?P<repo>[^/]+)/issues/(?P<number>\d+)/?$"
)


class CommissionRefused(ValueError):
    """A constraint failed BEFORE anything was written.

    Carries the diagnostic `code` so callers can branch on the reason rather
    than on message text, and states the downstream cost in the message --
    a refusal that does not say what it prevents gets argued with.
    """

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def validate_commission(
    *, sources: Sequence[str], bead_rig: str | None, brief_rig: str
) -> None:
    """Refuse the two failures that are cheap here and expensive later.

    `bead_rig` is the rig whose store holds the source bead. None means the
    caller could not determine it, which is not the same as "it matches" -- it
    is not checked rather than checked and passed, and this function says so by
    declining to assert either way.
    """
    if not sources or not any(s and s.strip() for s in sources):
        raise CommissionRefused(
            "MCMS_SOURCES_REQUIRED",
            "A commission brief needs at least one source bead. Without one the "
            "brief is B2.1-incomplete: it warns at creation and is FATAL at "
            "dispatch (MWRK011), so it can never be commissioned.",
        )
    if bead_rig is not None and bead_rig != brief_rig:
        raise CommissionRefused(
            "MCMS_CROSS_STORE_SOURCE",
            f"The source bead lives in rig {bead_rig!r} but the brief targets "
            f"{brief_rig!r}. A rig store cannot see another rig's beads, so "
            f"creation fails with 'no issue found matching <id>'. Create the "
            f"source bead in {brief_rig!r}.",
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
    """
    match = _ISSUE_URL.match(issue_url.strip())
    return match.group("repo") if match else None


def tracker_metadata(
    *, issue_url: str, labels: Sequence[str] = ()
) -> dict[str, str]:
    """Tracker provenance as metadata keys.

    NOT bd labels: GitHub labels are namespaced (`kind/bug`) and bd rejects
    slashes as label tokens (MBRF033). Translating by dropping the namespace is
    lossy -- `kind/bug` and `status/bug` collapse to one token. Metadata values
    have no such restriction, are queryable via `--has-metadata-key`, and match
    how every other structured fact in this city is stored (`gc.routed_to`,
    `gc.kind`, `requested_by`).

    An issue with no labels omits `gh.labels` entirely. Absent means "the issue
    had none"; an empty string is a value that looks like a measurement and is
    not one.
    """
    metadata: dict[str, str] = {}
    match = _ISSUE_URL.match(issue_url.strip())
    if match:
        owner, repo, number = match.group("owner", "repo", "number")
        metadata["gh.repo"] = f"{owner}/{repo}"
        metadata["gh.issue"] = f"{owner}/{repo}#{number}"
    kept = [label.strip() for label in labels if label and label.strip()]
    if kept:
        metadata["gh.labels"] = ",".join(kept)
    return metadata


def brief_labels() -> tuple[str, ...]:
    """The bd labels a commission brief carries: what it IS, nothing more."""
    return (COMMISSION_LABEL,)


@dataclass(frozen=True)
class CommissionRequest:
    """Everything `commission_brief` needs, validated as a unit.

    `metadata` is the tracker provenance from `tracker_metadata`. It is carried
    here rather than folded into the body so it stays queryable.
    """

    source_bead_id: str
    rig: str
    title: str
    body: str
    metadata: Mapping[str, str]

    def labels(self) -> tuple[str, ...]:
        return brief_labels()
