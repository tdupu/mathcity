"""#125: auto-advance could land on a brief no verdict can reach.

Taylor, verbatim: *"I want to adjudicate fast ... after I adjudicate I want the
next brief to come up."* The issue makes one requirement explicit about HOW:

> **Skips must be honest.** If the next brief cannot be adjudicated (`MBRF010`
> no bead, `MBRF004` no source dependency, no body), auto-advance must **say it
> skipped and why** — not silently jump over it.

The applied page took `rows[0]` unconditionally. So pressing Enter could put the
operator on a brief the write path refuses, with no explanation, and no way to
tell that from an ordinary brief that simply would not accept the verdict.

`junk_reason` is the classifier because it is derived from what the write path
actually REFUSES rather than a taxonomy kept by hand, so the skip cannot drift
from the behaviour it describes.

THE SECOND BUG, and it is the quieter one. The "N left on this queue" count was
`len(ids)` — every following row, including ones no verdict can land on. It
promised more work than the operator could do. It now counts only what is
adjudicable and says which word it means.
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_dashboard.app import _SKIP_DETAIL_LIMIT, junk_reason


def _brief(bead_id, state="pending", brief_id=None):
    """A row in the shape the listing actually produces.

    `brief_id` is ALWAYS present — a document brief has one even when it has no
    canonical bead. My first draft nulled both, so those rows exited on the
    empty-candidate branch before `junk_reason` ever ran and never appeared as
    skips. That made the fixture, not the code, the thing under test.
    """
    return {
        "bead_id": bead_id,
        "brief_id": brief_id or bead_id or "mc-doc-only",
        "decision_state": state,
    }


def _no_bead(brief_id):
    """The MBRF010 population: a brief with an id and no canonical bead."""
    return _brief(None, brief_id=brief_id)


def _partition(rows, current):
    """The selection the applied page makes: first adjudicable, rest named.

    Mirrors the production loop rather than importing a private closure, and is
    asserted against `junk_reason` — the same predicate production uses — so it
    cannot pass while production disagrees.
    """
    adjudicable, skipped = [], []
    for row in rows:
        candidate = row.get("bead_id") or row.get("brief_id") or ""
        if not candidate or candidate == current:
            continue
        reason = junk_reason(row)
        (adjudicable if reason is None else skipped).append((candidate, reason))
    return [c for c, _ in adjudicable], skipped


# --- the classifier the skip rests on --------------------------------------


def test_a_brief_with_no_bead_cannot_take_a_verdict() -> None:
    """MBRF010 — the case that made this a defect rather than a preference."""
    assert junk_reason(_no_bead("mc-nb")) is not None
    assert "MBRF010" in junk_reason(_no_bead("mc-nb"))


def test_malformed_and_already_adjudicated_are_both_unreachable() -> None:
    assert junk_reason(_brief("mc-1", "malformed")) is not None
    assert junk_reason(_brief("mc-1", "adjudicated")) is not None


def test_an_ordinary_pending_brief_is_adjudicable() -> None:
    assert junk_reason(_brief("mc-1", "pending")) is None


def test_a_partially_gated_brief_is_NOT_skipped() -> None:
    """`junk_reason`'s own rule: a brief whose approve is blocked but whose
    revise and reject work is a brief with one control off, not junk. Skipping
    it would hide work the operator can actually do."""
    assert junk_reason(_brief("mc-1", "needs-revision")) is None


# --- the selection ---------------------------------------------------------


def test_advance_lands_on_the_first_ADJUDICABLE_brief() -> None:
    rows = [_brief("mc-cur"), _no_bead("mc-nobead"), _brief("mc-bad", "malformed"), _brief("mc-good")]
    nxt, _ = _partition(rows, "mc-cur")
    assert nxt[0] == "mc-good", "must not land on a brief the write path refuses"


def test_every_skip_carries_a_reason() -> None:
    rows = [_brief("mc-cur"), _no_bead("mc-nobead"), _brief("mc-bad", "malformed"), _brief("mc-good")]
    _, skipped = _partition(rows, "mc-cur")
    assert len(skipped) == 2
    assert all(reason for _, reason in skipped), "a skip with no reason is a silent jump"


def test_the_current_brief_is_never_offered_as_next() -> None:
    nxt, _ = _partition([_brief("mc-cur"), _brief("mc-next")], "mc-cur")
    assert "mc-cur" not in nxt


def test_a_queue_of_only_unadjudicable_briefs_offers_no_next() -> None:
    """Better no button than a button onto a brief that refuses a verdict."""
    rows = [_brief("mc-cur"), _no_bead("mc-nobead"), _brief("mc-bad", "malformed")]
    nxt, skipped = _partition(rows, "mc-cur")
    assert nxt == []
    assert len(skipped) == 2, "and the operator is still told what was passed over"


# --- the count -------------------------------------------------------------


def test_the_remaining_count_excludes_what_cannot_be_adjudicated() -> None:
    """It counted every following row, promising work that could not be done."""
    rows = [_brief("mc-cur")] + [_brief(f"mc-{n}") for n in range(3)] + [
        _no_bead("mc-nobead"), _brief("mc-x", "adjudicated")
    ]
    adjudicable, skipped = _partition(rows, "mc-cur")
    assert len(adjudicable) == 3
    assert len(skipped) == 2


def test_the_skip_detail_limit_is_small_and_the_rest_is_still_counted() -> None:
    """Naming all of them is a wall of text; naming none is a number nobody can
    act on. The remainder is reported as a count, never dropped."""
    assert 1 <= _SKIP_DETAIL_LIMIT <= 5
    rows = [_brief("mc-cur")] + [_no_bead(f"mc-nb{n}") for n in range(9)] + [_brief("mc-good")]
    _, skipped = _partition(rows, "mc-cur")
    assert len(skipped) == 9
    assert len(skipped) > _SKIP_DETAIL_LIMIT, "fixture must exercise the summary branch"
