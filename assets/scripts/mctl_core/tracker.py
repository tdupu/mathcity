"""Pair every GitHub issue with its bead and brief -- the #186 read model.

Taylor, verbatim on #186: *"I would love to have links to issues on the github
issue tracker ... It should also list the associated beads and briefs if
available."* This module answers only the pairing question. Rendering is
`mctl_dashboard/screens/tracker.py`; the GitHub read is
`github_issues.list_issues`.

**The pairing key is `external_ref`, and it is almost always absent.** Measured
on the live mathcity store 2026-08-28: **7 of 1142 beads carry one** (0.6%),
against ~100 open issues. So the overwhelmingly common row is an issue with no
bead, and that is not a defect in this module -- it is the finding the screen
exists to show. #180's whole pipeline is minting those missing beads, and a
tracker that could not show the gap would be useless for it.

Two consequences drive the design:

**UNPAIRED IS A FIRST-CLASS STATE, never an empty cell.** `TrackerRow.pairing`
is one of `paired` / `unpaired` / `unknown`, and the three mean different
things. `unpaired` asserts the bead store was read and contains no bead for
this issue. `unknown` asserts the store could not be read at all. A blank cell
would collapse both into "fine", which is the failure P6.2 keeps naming: a
report that cannot say "I could not tell" will eventually say something false.

**A NUMERIC MATCH IS NOT A PAIRING.** `external_ref` is matched exactly against
`gh-<number>`, never by scanning titles or bodies for an issue number. Title
matching is what produced the duplicate beads in mc-vwkn7 -- five pairs, two of
which escaped title-match dedup entirely. A cheap predicate standing in for a
semantic question is how that happened, and this module refuses to repeat it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Iterable, Mapping, Sequence

#: `external_ref` values that name a GitHub issue. Anchored on purpose: a bead
#: whose ref is `gh-56-followup` is NOT issue 56, and a substring match would
#: claim it is.
_GH_REF = re.compile(r"^gh-(\d+)$")

#: The three pairing states. `unknown` is not a flavour of `unpaired`.
PAIRED = "paired"
UNPAIRED = "unpaired"
UNKNOWN = "unknown"


def issue_number_from_ref(external_ref: Any) -> int | None:
    """The issue number an `external_ref` names, or None if it names none.

    Returns None for a ref that merely CONTAINS a number (`gh-56-followup`,
    `see-gh-56`). Those are not issue 56 and must not be rendered as it.
    """
    if not isinstance(external_ref, str):
        return None
    match = _GH_REF.match(external_ref.strip())
    return int(match.group(1)) if match else None


#: `metadata["gh.issue"]` values, which is where `create_issue_bead` actually
#: records the pairing: `owner/repo#123`. Anchored for the same reason as
#: `_GH_REF` -- a ref that merely CONTAINS a number is not that issue.
_GH_ISSUE_META = re.compile(r"^([\w.\-]+/[\w.\-]+)#(\d+)$")


def issue_ref_from_metadata(metadata: Any) -> tuple[str, int] | None:
    """The `(repo, number)` a bead's `metadata["gh.issue"]` names, or None.

    THE SECOND PLACE A PAIRING LIVES, and the one that carries almost all of
    them (mc-mbf3a). `create_issue_bead` writes `metadata["gh.issue"]` as
    `owner/repo#N` and sets no `external_ref`, so a reader consulting only
    `external_ref` reports beads that exist as absent -- measured 2026-08-29:
    5 issues paired on the rendered screen against 56 in the store.

    The repo half is returned rather than discarded because it is load-bearing:
    pairing on the number alone would let `other/repo#204` answer for this
    repo's `#204`. That is precisely the "a numeric match is not a pairing"
    failure this module refuses elsewhere, and it must not sneak in here.
    """
    if not isinstance(metadata, Mapping):
        return None
    raw = metadata.get("gh.issue")
    if not isinstance(raw, str):
        return None
    match = _GH_ISSUE_META.match(raw.strip())
    if match is None:
        return None
    return match.group(1), int(match.group(2))


def index_beads_by_issue(
    beads: Iterable[Mapping[str, Any]], *, repo: str | None = None
) -> dict[int, list[Mapping[str, Any]]]:
    """Group beads by the issue they name, reading BOTH pairing keys.

    A list per issue, not a single bead: mc-vwkn7 measured five issues carrying
    TWO beads each after a duplicating drain. Modelling this as one-to-one would
    silently drop the duplicate and hide exactly the condition worth surfacing.

    Two keys, because the city writes one and this module used to read only the
    other (mc-mbf3a):

    * `external_ref` == `gh-<number>` -- the legacy form, still present on a
      small set of beads.
    * `metadata["gh.issue"]` == `owner/repo#<number>` -- what `create_issue_bead`
      writes today, and where the great majority of pairings actually are.

    `repo` GATES THE SECOND KEY AND NOTHING ELSE. Given, only beads whose repo
    half matches are paired. NOT given, `metadata["gh.issue"]` is skipped
    entirely rather than paired on the number alone -- an unqualified numeric
    match across unknown repositories is the exact predicate this module exists
    to refuse, and silently relaxing it here to gain a few rows would trade a
    visible undercount for an invisible wrong pairing.

    A bead carrying both keys is added once, not twice.
    """
    index: dict[int, list[Mapping[str, Any]]] = {}
    for bead in beads:
        numbers: set[int] = set()
        legacy = issue_number_from_ref(bead.get("external_ref"))
        if legacy is not None:
            numbers.add(legacy)
        meta_ref = issue_ref_from_metadata(bead.get("metadata"))
        if meta_ref is not None and repo is not None and meta_ref[0] == repo:
            numbers.add(meta_ref[1])
        for number in numbers:
            index.setdefault(number, []).append(bead)
    return index


@dataclass(frozen=True)
class TrackerRow:
    """One GitHub issue, with whatever the city knows about it."""

    number: int
    title: str
    url: str
    state: str
    labels: tuple[str, ...] = ()
    beads: tuple[Mapping[str, Any], ...] = ()
    briefs: tuple[Mapping[str, Any], ...] = ()
    pairing: str = UNPAIRED
    #: Set when `pairing == UNKNOWN`: why the store could not be read.
    unknown_reason: str | None = None

    @property
    def is_duplicated(self) -> bool:
        """More than one bead claims this issue -- the mc-vwkn7 signature."""
        return len(self.beads) > 1

    @property
    def bead_ids(self) -> tuple[str, ...]:
        return tuple(str(b.get("id") or "") for b in self.beads if b.get("id"))

    @property
    def is_orphaned_by_bead(self) -> bool:
        """Issue still OPEN, but every bead claiming it is CLOSED.

        Found in live data on the first run of this model: issue #55 is open
        while its only bead, `mc-6jk`, is closed. That is either work finished
        without closing the issue, or a bead closed on the wrong grounds -- and
        both are worth an operator's eye. It renders distinctly from `unpaired`
        because the two call for opposite actions: mint a bead, versus go look
        at why the existing one is closed.

        False when there are no beads at all; absence is `unpaired`'s job.
        """
        if not self.beads or self.state.upper() != "OPEN":
            return False
        return all(str(b.get("status") or "").lower() == "closed" for b in self.beads)

    @property
    def needs_bead(self) -> bool:
        """The #180 work item: a live issue with no bead minted for it.

        False when the pairing is UNKNOWN. "The store did not answer" is not
        the same as "this issue needs a bead", and dispatching work off the
        former would mint duplicates.
        """
        return self.pairing == UNPAIRED and self.state.upper() == "OPEN"


def build_rows(
    issues: Sequence[Mapping[str, Any]],
    beads: Sequence[Mapping[str, Any]] | None,
    briefs_by_bead: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    *,
    store_unreadable: str | None = None,
    repo: str | None = None,
) -> list[TrackerRow]:
    """Assemble one row per issue.

    `beads=None` or `store_unreadable` set means the bead store did not answer:
    every row is UNKNOWN, and none is reported as needing a bead. Passing an
    empty list instead means the store answered and holds nothing -- a
    different claim, and the caller must not conflate them.

    `repo` is the repository the issues came from. It gates pairing on
    `metadata["gh.issue"]`, which is repo-qualified (mc-mbf3a); omit it and that
    key is not consulted, so rows will under-report exactly as they did before
    the fix. Callers that know their repo should always pass it.
    """
    unreadable = store_unreadable is not None or beads is None
    index = {} if unreadable else index_beads_by_issue(beads or (), repo=repo)
    briefs_by_bead = briefs_by_bead or {}

    rows: list[TrackerRow] = []
    for issue in issues:
        number = issue.get("number")
        if not isinstance(number, int):
            continue
        matched = tuple(index.get(number, ()))
        briefs: list[Mapping[str, Any]] = []
        for bead in matched:
            briefs.extend(briefs_by_bead.get(str(bead.get("id") or ""), ()))
        if unreadable:
            pairing = UNKNOWN
        elif matched:
            pairing = PAIRED
        else:
            pairing = UNPAIRED
        rows.append(
            TrackerRow(
                number=number,
                title=str(issue.get("title") or ""),
                url=str(issue.get("url") or ""),
                state=str(issue.get("state") or ""),
                labels=tuple(str(x) for x in (issue.get("labels") or ())),
                beads=matched,
                briefs=tuple(briefs),
                pairing=pairing,
                unknown_reason=store_unreadable if unreadable else None,
            )
        )
    return rows


def summarize(rows: Sequence[TrackerRow]) -> dict[str, Any]:
    """Counts for the screen header.

    `needs_bead` is deliberately absent when anything is UNKNOWN: a partial
    denominator rendered as a total is how "3,301 ready beads" became a number
    nobody could act on. If the store did not answer for some rows, the count
    of issues needing beads is not known, and the summary says so.
    """
    unknown = sum(1 for r in rows if r.pairing == UNKNOWN)
    summary: dict[str, Any] = {
        "issues": len(rows),
        "paired": sum(1 for r in rows if r.pairing == PAIRED),
        "unpaired": sum(1 for r in rows if r.pairing == UNPAIRED),
        "unknown": unknown,
        "duplicated": sum(1 for r in rows if r.is_duplicated),
    }
    summary["needs_bead"] = None if unknown else sum(1 for r in rows if r.needs_bead)
    return summary
