"""Diagnostic codes the dashboard must not present as actionable.

This module exists because the most damaging thing this dashboard could do is
be *confidently wrong*. It renders authoritative-looking findings over a queue
the repo owner has not been able to read; a badge saying "74 malformed --
repair" would send someone to fix 150+ beads that are fine.

Three codes are currently instrumentation artifacts, not findings:

`MBRF021` -- "no redundant cache artifact". A mass false positive: 66 of 70 in
one rig. Open question Q5 (`subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md`)
records why -- the artifact root resolves rig-relative while the live stack is
city-root-level, and the lookup expects `<bead_id>.md` while real pile files
carry the bead id in `artifact:` frontmatter. Slice 6 already partitions this
one server-side into `untrusted_diagnostics`; the dashboard's job is to honor
that split instead of flattening it back together.

`MBRF004` / `MBRF005` -- under review per
`subdomains/dev/docs/MALFORMED-BRIEF-TRIAGE-2026-08-19.md`. `malformed` does
not mean malformed: it means *closed with no verdict field*, and the verdicts
are not missing -- 50 of 50 closed hecke decision beads carry a non-empty
`close_reason`, and `_verdict()` does not read it. Roughly 39 of the 74 are
not briefs at all but git-operation receipts that `Bead.is_brief` sweeps in
because it only tests `issue_type == "decision"`.

The rule this module enforces, everywhere these codes appear:

1. show the code -- hiding it would be its own dishonesty;
2. label it under review and name the document;
3. keep it out of every actionable count;
4. never render a repair affordance for it.

Removing a code from here is a claim that its instrumentation was fixed. That
claim belongs in the referenced document first.
"""
from __future__ import annotations

from dataclasses import dataclass


Q5_DOC = "subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md#q5"
TRIAGE_DOC = "subdomains/dev/docs/MALFORMED-BRIEF-TRIAGE-2026-08-19.md"


@dataclass(frozen=True)
class ReviewNote:
    code: str
    headline: str
    detail: str
    reference: str


UNDER_REVIEW: dict[str, ReviewNote] = {
    "MBRF021": ReviewNote(
        code="MBRF021",
        headline="Under review - known mass false positive (open question Q5).",
        detail=(
            "The artifact root resolves rig-relative while the live brief stack is "
            "city-root-level, and the lookup expects <bead_id>.md while real pile files "
            "carry the bead id in `artifact:` frontmatter. 66 of 70 briefs in one rig "
            "report this against artifacts that exist. Repairing from it would create "
            "duplicate artifacts, so it is not actionable until Q5 is answered."
        ),
        reference=Q5_DOC,
    ),
    "MBRF004": ReviewNote(
        code="MBRF004",
        headline="Under review - instrumentation, not a finding.",
        detail=(
            "`no source dependency` fires on 146 beads across both malformed and pending "
            "briefs and is independent of why any brief is malformed. Many of the beads it "
            "fires on are not briefs at all -- roughly 39 of the 74 are git-operation "
            "receipts that are counted as briefs only because they are type=decision."
        ),
        reference=TRIAGE_DOC,
    ),
    "MBRF005": ReviewNote(
        code="MBRF005",
        headline="Under review - instrumentation, not a finding.",
        detail=(
            "`malformed` means closed with no verdict *field*. The verdicts are mostly not "
            "missing: they sit in `close_reason` (non-empty on 50 of 50 closed hecke "
            "decision beads) and in `notes`, which the verdict reader does not consult. "
            "At most 35 of the 74 are malformed briefs, and 27 of those carry a legible "
            "human verdict written to the wrong field."
        ),
        reference=TRIAGE_DOC,
    ),
}

UNDER_REVIEW_CODES = frozenset(UNDER_REVIEW)

#: What `decision_state == "malformed"` actually means, for the queue badge.
#: A bare count with no caveat is a defect, so the caveat travels with it.
MALFORMED_CAVEAT = (
    "`malformed` means closed with no verdict field -- not damaged. The verdicts are "
    "mostly present in `close_reason` and `notes`, which the verdict reader does not "
    "consult, and about half of these beads are git-operation receipts that were never "
    "briefs. Counts here are instrumentation under review."
)


def is_under_review(code: str | None) -> bool:
    return str(code or "") in UNDER_REVIEW


def note_for(code: str | None) -> ReviewNote | None:
    return UNDER_REVIEW.get(str(code or ""))


def partition(diagnostics: list[dict]) -> tuple[list[dict], list[dict]]:
    """Split diagnostics into (actionable, under review), preserving order."""
    actionable = [item for item in diagnostics if not is_under_review(item.get("code"))]
    reviewed = [item for item in diagnostics if is_under_review(item.get("code"))]
    return actionable, reviewed
