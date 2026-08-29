"""#226: the rejection artifacts existed and no typed tool could read them.

Panel v2 re-grounded the error-briefs and HELD views on real failure artifacts
(ADR 0004 D4). `.pile/.rejected/<slug>/rejection.json` was on disk with the
shape the views needed, and nothing served it, so the dashboard rendered a
"not readable" banner over data that was sitting there.

WHAT THE GAP COST, measured on `mc-x338k`: the three briefs the S63 charge told
four consecutive Mayors to present FIRST -- `mc-s0a4j`, `mc-vmcc5`, `mc-7a98s`
-- were all in `.rejected/`. Nothing reads that directory: not `briefs_list`,
not `/queue`, not `check-briefs`. Four sessions recorded "not presented" and
none could record "cannot be presented", because no instrument told them apart.
Run against the live pile, this reader returns all three as REJECTED with the
identical reason in one call.

THE INVARIANT THIS FILE EXISTS TO PIN, and it is the one a "helpful" version
would break: **PENDING must never imply promotable.** Gate evaluation lives in
`brief-check.sh` and the shuffler, outside the typed surface (#66). Deriving
PROMOTABLE from "in the pile and not rejected" would be a guess wearing a
measurement's clothes, and it would read to an operator as an assurance the
brief is ready. `gate_state` stays None and `gate_state_known` stays False.

Second invariant: `failures: []` beside a non-empty `reason` is the LIVE shape
on every one of the 24 rejections measured. A reader that smoothed `[]` into
"no failures" would invert it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.pile_state import (
    STATE_PENDING,
    STATE_REJECTED,
    briefs_pile_state,
    city_reader,
)

#: The live shape, copied verbatim from mc-s0a4j's artifact 2026-08-29.
LIVE_REJECTION = {
    "failures": [],
    "gate_profile": "standard",
    "reason": "standard brief missing provenance metadata",
    "rejected_at": "2026-08-28T10:36:29Z",
    "slug": "mc-s0a4j",
    "source_path": ".pile/mc-s0a4j.md",
}


def _pile(tmp_path: Path, *, pending=(), rejected=()) -> Path:
    pile = tmp_path / ".pile"
    pile.mkdir(parents=True, exist_ok=True)
    for slug in pending:
        (pile / f"{slug}.md").write_text("body", encoding="utf-8")
    for slug, payload in rejected:
        d = pile / ".rejected" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "brief.md").write_text("body", encoding="utf-8")
        if payload is not None:
            (d / "rejection.json").write_text(json.dumps(payload), encoding="utf-8")
    return pile


def _by_slug(result):
    return {b["slug"]: b for b in result["briefs"]}


# --- the gap: rejections must be readable ----------------------------------


def test_a_rejection_is_reported_with_its_payload_verbatim(tmp_path: Path) -> None:
    pile = _pile(tmp_path, rejected=[("mc-s0a4j", LIVE_REJECTION)])
    row = _by_slug(briefs_pile_state(city_reader(pile)))["mc-s0a4j"]
    assert row["state"] == STATE_REJECTED
    assert row["reason"] == LIVE_REJECTION["reason"]
    assert row["gate_profile"] == "standard"
    assert row["rejected_at"] == LIVE_REJECTION["rejected_at"]
    assert row["source_path"] == ".pile/mc-s0a4j.md"


def test_empty_failures_is_surfaced_not_smoothed(tmp_path: Path) -> None:
    """`[]` beside a non-empty reason is the live shape on all 24. Reading it
    as 'no failures' inverts what the gate said."""
    pile = _pile(tmp_path, rejected=[("mc-s0a4j", LIVE_REJECTION)])
    row = _by_slug(briefs_pile_state(city_reader(pile)))["mc-s0a4j"]
    assert row["failures"] == []
    assert row["reason"], "an empty failures list must not imply an empty reason"


def test_rejected_briefs_are_not_hidden_among_pending(tmp_path: Path) -> None:
    """The whole defect: a rejected brief leaving the queue with no trace."""
    pile = _pile(tmp_path, pending=["mc-live"], rejected=[("mc-s0a4j", LIVE_REJECTION)])
    result = briefs_pile_state(city_reader(pile))
    assert result["pending_count"] == 1
    assert result["rejected_count"] == 1
    assert _by_slug(result)["mc-s0a4j"]["state"] == STATE_REJECTED


# --- the invariant a "helpful" version would break --------------------------


def test_pending_never_claims_to_be_promotable(tmp_path: Path) -> None:
    """#66: gate evaluation is outside this surface. Do not guess."""
    pile = _pile(tmp_path, pending=["mc-live"])
    result = briefs_pile_state(city_reader(pile))
    row = _by_slug(result)["mc-live"]
    assert row["state"] == STATE_PENDING
    assert row["gate_state"] is None
    assert result["gate_state_known"] is False


def test_the_unreadable_gate_state_is_stated_not_omitted(tmp_path: Path) -> None:
    """A consumer must be able to tell 'not promotable' from 'we cannot say'."""
    result = briefs_pile_state(city_reader(_pile(tmp_path, pending=["mc-live"])))
    codes = [d["code"] for d in result["diagnostics"]]
    assert "MPIL_GATE_STATE_UNREADABLE" in codes


# --- absence vs failure to look --------------------------------------------


def test_a_missing_pile_is_unreachable_not_empty(tmp_path: Path) -> None:
    """An empty pile and an unreadable one are different answers."""
    result = briefs_pile_state(city_reader(tmp_path / "nope" / ".pile"))
    assert result["state"] == "unreachable"
    assert result["briefs"] is None, "None, never [] -- [] asserts a drained queue"
    assert result["pending_count"] is None
    assert any(d["code"] == "MPIL_PILE_UNREACHABLE" for d in result["diagnostics"])


def test_a_pile_with_no_rejections_is_a_real_empty_answer(tmp_path: Path) -> None:
    """No `.rejected/` directory means none, and that is measurable."""
    result = briefs_pile_state(city_reader(_pile(tmp_path, pending=["mc-live"])))
    assert result["state"] == "healthy"
    assert result["rejected_count"] == 0


def test_an_unparseable_rejection_is_reported_not_dropped(tmp_path: Path) -> None:
    """A brief whose artifact is corrupt is still a brief that left the queue."""
    pile = _pile(tmp_path, rejected=[("mc-broken", None)])
    result = briefs_pile_state(city_reader(pile))
    row = _by_slug(result)["mc-broken"]
    assert row["state"] == STATE_REJECTED, "must not vanish for want of a payload"
    assert row["artifact_readable"] is False
    assert row["reason"] is None
    assert any(d["code"] == "MPIL_REJECTION_UNPARSEABLE" for d in result["diagnostics"])


# --- counting ---------------------------------------------------------------


def test_a_redeposited_brief_is_counted_once(tmp_path: Path) -> None:
    """Present in both places after a re-deposit. Two rows would imply two briefs."""
    pile = _pile(tmp_path, pending=["mc-s0a4j"], rejected=[("mc-s0a4j", LIVE_REJECTION)])
    result = briefs_pile_state(city_reader(pile))
    assert [b["slug"] for b in result["briefs"]].count("mc-s0a4j") == 1
    assert result["rejected_count"] == 1
    assert result["pending_count"] == 0


def test_dotfiles_and_subdirectories_are_not_counted_as_pending(tmp_path: Path) -> None:
    """`.rejected/`, `.no-brainer/` and partials must not read as waiting briefs."""
    pile = _pile(tmp_path, pending=["mc-live"], rejected=[("mc-gone", LIVE_REJECTION)])
    (pile / ".partial.md").write_text("x", encoding="utf-8")
    (pile / ".no-brainer").mkdir(exist_ok=True)
    result = briefs_pile_state(city_reader(pile))
    assert result["pending_count"] == 1
    assert [b["slug"] for b in result["briefs"] if b["state"] == STATE_PENDING] == ["mc-live"]
