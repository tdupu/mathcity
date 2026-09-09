"""Profile-scoped structural rules (#96, #219).

`brief-check.sh` requires an `action_block:` with `on_approve`/`on_reject`/
`on_defer` for the DECISION profile only (`check_decision_profile` is its sole
caller). `required-sections.toml` had one unscoped rule -- `## Gate Evidence` --
so a decision brief could be created, reported as applied, and then bounced at
shuffle time for the action_block nobody checked at creation.

Measured live on the kolchin testrig: brief `mt-yftq`, created through
`briefs_create` and reported `applied: true`, landed in `.pile/.rejected/` with
`reason: "decision brief missing action_block"`. That is the CT13.4 shape #96
quantified as "pile drained 5 -> 0 entirely by auto-reject".

The rule must stay SCOPED: applying action_block to every brief would refuse
`lost_bead_filter` and `producer_repair` briefs, which legitimately have none.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core.structure import missing_sections  # noqa: E402

DECISION_BODY_NO_ACTION_BLOCK = """---
gate_profile: decision
brief_kind: decision
---

## Gate Evidence

G8 brief-record: filed before deposit.
"""

DECISION_BODY_COMPLETE = """---
gate_profile: decision
brief_kind: decision
---

## §1 — What is being decided

n/a for this fixture.

## §2 — Recommended answer

n/a for this fixture.

## §3 — Assumptions surfaced

n/a for this fixture.

## §4 — Alternatives named

n/a for this fixture.

## §5 — Risks foregrounded

n/a for this fixture.

## §6 — Supporting evidence

n/a for this fixture.

## §7 — Plan membership, blocking, and required gates

n/a for this fixture.

## Gate Evidence

G8 brief-record: filed before deposit.

action_block:
  on_approve: do the thing
  on_reject: do nothing
  on_defer: revisit
"""

FILTER_BODY = """---
gate_profile: lost_bead_filter
---

## Gate Evidence

Classifier ran.
"""


def _names(sections):
    return {str(s.get("name")) for s in sections}


def test_a_decision_brief_without_an_action_block_is_refused_at_creation():
    absent = _names(missing_sections(DECISION_BODY_NO_ACTION_BLOCK, profile="decision"))
    assert "action_block" in absent


def test_a_complete_decision_brief_passes():
    assert missing_sections(DECISION_BODY_COMPLETE, profile="decision") == []


def test_the_action_block_rule_does_not_apply_to_other_profiles():
    """lost_bead_filter and producer_repair briefs legitimately carry none."""
    absent = _names(missing_sections(FILTER_BODY, profile="lost_bead_filter"))
    assert "action_block" not in absent


def test_an_unknown_profile_applies_only_unscoped_rules():
    """No profile declared -> only the rules that apply to every brief.

    Strictly more checking than before, never less: an undeclared profile
    behaves exactly as today rather than refusing on a rule it cannot know
    applies.
    """
    absent = _names(missing_sections(DECISION_BODY_NO_ACTION_BLOCK))
    assert "action_block" not in absent
    assert missing_sections("no sections here at all") != []
