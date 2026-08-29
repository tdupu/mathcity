"""mc-mbf3a: the tracker read one pairing key while the city wrote another.

`index_beads_by_issue` paired on `external_ref` == `gh-<number>`.
`create_issue_bead` writes `metadata["gh.issue"]` == `owner/repo#<number>` and
sets no `external_ref`. Different key, different format; they never joined, so
the `/tracker` screen reported beads that exist as absent.

MEASURED 2026-08-29 against the live instance: the screen said `109 issues · 5
with a bead · 104 without`, while the store held mirror beads for 56 of them.
The decisive case is `#204`, whose mirror `mc-8ncv` had carried
`metadata["gh.issue"] = "tdupu/mathcity#204"` since 2026-08-23 -- six days --
in the same rig store the screen reads.

WHY THIS IS NOT A COSMETIC BUG, and why the tests below check `needs_bead`.
`_handle_tracker_rows` withholds `needs_bead` when the store is UNREADABLE,
precisely so #180 cannot mint duplicates over beads it could not see. Here the
store is readable and the join merely misses, so rows come back `unpaired` -- a
positive claim that the store was read and holds nothing -- and the guard never
fires. A mint sweep on that field would have duplicated 51 existing beads.

THE DISCIPLINE THAT MUST SURVIVE THE FIX. tracker.py refuses to pair on a bare
number: "a numeric match is not a pairing". `metadata["gh.issue"]` is
repo-qualified, so honouring that means the repo half has to MATCH -- otherwise
`other/repo#204` would answer for our `#204`. Relaxing it to gain rows would
trade a visible undercount for an invisible mispairing, which is strictly worse.
The cross-repo and no-repo tests below exist to pin that.
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.tracker import (
    PAIRED,
    UNKNOWN,
    UNPAIRED,
    build_rows,
    index_beads_by_issue,
    issue_ref_from_metadata,
)

REPO = "tdupu/mathcity"


def _bead(bead_id: str, *, gh_issue: str | None = None, external_ref: str | None = None):
    bead: dict = {"id": bead_id, "metadata": {}}
    if gh_issue is not None:
        bead["metadata"]["gh.issue"] = gh_issue
    if external_ref is not None:
        bead["external_ref"] = external_ref
    return bead


def _issue(number: int):
    return {"number": number, "title": f"issue {number}", "url": "", "state": "open", "labels": []}


# --- the defect ------------------------------------------------------------


def test_bead_carrying_only_gh_issue_metadata_pairs() -> None:
    """The mc-8ncv shape: metadata pairing, no external_ref."""
    index = index_beads_by_issue([_bead("mc-8ncv", gh_issue=f"{REPO}#204")], repo=REPO)
    assert [b["id"] for b in index.get(204, ())] == ["mc-8ncv"]


def test_row_for_a_metadata_paired_issue_is_PAIRED_not_UNPAIRED() -> None:
    """The screen said `no bead` for exactly this input."""
    rows = build_rows([_issue(204)], [_bead("mc-8ncv", gh_issue=f"{REPO}#204")], repo=REPO)
    assert rows[0].pairing == PAIRED
    assert [b["id"] for b in rows[0].beads] == ["mc-8ncv"]


# --- the discipline that must survive --------------------------------------


def test_a_bead_from_another_repo_does_not_pair() -> None:
    """`other/repo#204` is not our #204. Pairing on the bare number is the
    failure this module refuses everywhere else."""
    rows = build_rows([_issue(204)], [_bead("x-1", gh_issue="other/repo#204")], repo=REPO)
    assert rows[0].pairing == UNPAIRED
    assert rows[0].beads == ()


def test_without_a_repo_the_metadata_key_is_skipped_entirely() -> None:
    """No repo means no safe repo comparison, so do not pair on the number."""
    index = index_beads_by_issue([_bead("mc-8ncv", gh_issue=f"{REPO}#204")], repo=None)
    assert index == {}


def test_unanchored_metadata_values_do_not_pair() -> None:
    """Same anchoring rule as `gh-56-followup`: containing a number is not being it."""
    for bad in (f"{REPO}#204-followup", f"see {REPO}#204", "204", "#204", f"{REPO}#", ""):
        assert issue_ref_from_metadata({"gh.issue": bad}) is None, bad


def test_missing_or_malformed_metadata_is_tolerated() -> None:
    assert issue_ref_from_metadata(None) is None
    assert issue_ref_from_metadata({}) is None
    assert issue_ref_from_metadata({"gh.issue": 204}) is None
    assert issue_ref_from_metadata("not-a-mapping") is None


# --- regressions: the legacy key must keep working -------------------------


def test_legacy_external_ref_still_pairs() -> None:
    index = index_beads_by_issue([_bead("mc-old", external_ref="gh-56")], repo=REPO)
    assert [b["id"] for b in index.get(56, ())] == ["mc-old"]


def test_legacy_external_ref_pairs_even_with_no_repo() -> None:
    """external_ref is not repo-qualified, so the repo gate must not affect it."""
    index = index_beads_by_issue([_bead("mc-old", external_ref="gh-56")], repo=None)
    assert [b["id"] for b in index.get(56, ())] == ["mc-old"]


def test_a_bead_carrying_both_keys_is_listed_once() -> None:
    """Reading two keys must not double-count one bead into the same issue."""
    both = _bead("mc-both", gh_issue=f"{REPO}#204", external_ref="gh-204")
    assert [b["id"] for b in index_beads_by_issue([both], repo=REPO).get(204, ())] == ["mc-both"]


def test_duplicate_mirrors_are_still_surfaced_as_a_list() -> None:
    """mc-vwkn7: two beads on one issue is the condition worth seeing, not hiding."""
    beads = [_bead("mc-a", gh_issue=f"{REPO}#204"), _bead("mc-b", gh_issue=f"{REPO}#204")]
    assert len(index_beads_by_issue(beads, repo=REPO)[204]) == 2


# --- the three-state contract ----------------------------------------------


def test_unreadable_store_is_UNKNOWN_not_UNPAIRED() -> None:
    """`unknown` is not a flavour of `unpaired`, and the fix must not blur them."""
    rows = build_rows([_issue(204)], None, store_unreadable="boom", repo=REPO)
    assert rows[0].pairing == UNKNOWN
    assert rows[0].unknown_reason == "boom"


def test_readable_store_with_no_match_is_UNPAIRED() -> None:
    rows = build_rows([_issue(999)], [_bead("mc-8ncv", gh_issue=f"{REPO}#204")], repo=REPO)
    assert rows[0].pairing == UNPAIRED
