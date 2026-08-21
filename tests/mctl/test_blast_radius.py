"""D2 / #110: `blast_radius` is a gate enforced at apply time, not a rendering hint.

Design by stripes (`<city-root>/docs/D2-blast-radius-proposal.md`), amended to a
TWO-FIELD shape after I asked whether `gated` is a tier or a destination. It is a
destination:

    blast_radius : low | medium | high   -- how much confirmation the page demands
    gate         : None | <gate name>    -- or: not here at all, go to the gate

One four-value enum carried both meanings, and the concrete failure is that any
code treating the tier as ordered (`tier >= HIGH`, a sort, a `max()` during
escalation) reads `gated` as merely-more-severe. Splitting it makes stripes' own
constraint -- `gate` is never escalated into -- true by construction rather than a
rule people must remember.

The load-bearing line, in stripes' words: the default is `gate="unclassified"`,
NOT `blast_radius="low"`. An operation nobody classified must be the HARDEST to
perform, not the easiest.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core import blast_radius as br  # noqa: E402


# --- the field vocabulary ----------------------------------------------------

def test_the_tier_axis_has_exactly_three_values_and_gated_is_not_one():
    assert br.TIERS == ("low", "medium", "high")
    assert "gated" not in br.TIERS


# --- fail closed: the single most important line in the proposal -------------

def test_an_unregistered_operation_is_GATED_not_low():
    verdict = br.classify("some.operation.nobody.classified", plan_contents={})
    assert verdict["gate"] == "unclassified"
    assert verdict["blast_radius"] != "low"
    # Gated by the same rule as any other gate: no tier, because there is none.
    assert verdict["blast_radius"] is None


def test_an_unregistered_operation_refuses_at_apply():
    verdict = br.classify("some.operation.nobody.classified", plan_contents={})
    assert br.refuses(verdict) is True


# --- gate is a destination, and the tier is not consulted --------------------

def test_a_gated_operation_refuses_and_names_its_gate():
    verdict = br.classify("worktree.remove", plan_contents={})
    assert verdict["gate"] == "artifact-harvest"
    assert br.refuses(verdict) is True
    assert "artifact-harvest" in verdict["blast_radius_reason"]


def test_a_gated_operation_reports_blast_radius_None_not_a_tier():
    """stripes' ruling, and the reasoning is theirs.

    A consumer that reads only `blast_radius` and sees "high" renders a
    typed-confirmation form -- for an operation that must be REFUSED outright.
    A value that looks meaningful and is not is the same family as a plausible
    empty result. `null` is still uniform: the key is present, the value absent,
    exactly as city_health does with `bytes_used: null` plus a reason.

    Object-model principle 5 picks WHICH null: None = "there is none",
    Unknown = "we did not look". A gated operation genuinely HAS no tier.
    """
    verdict = br.classify("worktree.remove", plan_contents={})
    assert verdict["blast_radius"] is None
    assert verdict["blast_radius"] != "unknown"
    assert verdict["blast_radius_floor"] is None
    assert verdict["blast_radius_reason"].strip()      # the reason carries the why


def test_escalation_can_never_produce_a_gated_plan():
    """stripes' constraint, made structural rather than remembered."""
    verdict = br.classify("capacity.set_target", plan_contents={"stops_work": True})
    assert verdict["blast_radius"] == "high"
    assert verdict["gate"] is None          # escalation touched the tier only


# --- escalation raises, never lowers (CT9.2's shape) -------------------------

def test_plan_contents_escalate_above_the_floor():
    # capacity.set_target(5) and set_target(0) share a floor; only contents differ.
    quiet = br.classify("capacity.set_target", plan_contents={})
    stops = br.classify("capacity.set_target", plan_contents={"stops_work": True})
    assert quiet["blast_radius"] == "medium"
    assert stops["blast_radius"] == "high"
    assert stops["blast_radius_floor"] == "medium"   # the raw reading is preserved


def test_escalation_never_lowers_below_the_floor():
    verdict = br.classify("rig.suspend", plan_contents={})     # floor high
    assert verdict["blast_radius"] == "high"
    assert verdict["blast_radius_floor"] == "high"


def test_multi_rig_escalates():
    assert br.classify("briefs.adjudicate", plan_contents={"rig_count": 2})["blast_radius"] == "high"


def test_a_deletion_escalates():
    assert br.classify("briefs.adjudicate", plan_contents={"deletes": True})["blast_radius"] == "high"


# --- a tier with no stated reason is an assertion ----------------------------

def test_every_verdict_carries_a_non_empty_reason():
    for op, contents in [
        ("briefs.adjudicate", {}),
        ("capacity.set_target", {"stops_work": True}),
        ("worktree.remove", {}),
        ("nobody.classified.this", {}),
    ]:
        assert br.classify(op, plan_contents=contents)["blast_radius_reason"].strip()


def test_an_escalated_reason_names_what_escalated_it():
    r = br.classify("capacity.set_target", plan_contents={"stops_work": True})["blast_radius_reason"]
    assert "medium" in r and "high" in r      # floor and final are both visible


# --- the registry is data, and it is checkable -------------------------------

def test_the_registry_is_loadable_and_every_entry_is_well_formed():
    reg = br.load_registry()
    assert reg, "registry must not be empty"
    for op, entry in reg.items():
        assert entry.get("reason", "").strip(), f"{op} has no reason"
        if "gate" in entry:
            assert "floor" not in entry, f"{op} sets both gate and floor"
        else:
            assert entry.get("floor") in br.TIERS, f"{op} floor not a tier"


def test_every_operation_effects_py_can_emit_is_registered_or_deliberately_not():
    """A mutation added without classification must be LOUD, not permissive.

    This is the lint stripes asked for. It does not require every operation to
    be registered -- it requires an unregistered one to land in the gate lane,
    which `classify` guarantees. What it pins is that the operations we DO ship
    resolve to something a human chose.
    """
    for op in ("briefs.create", "briefs.adjudicate", "briefs.defer"):
        v = br.classify(op, plan_contents={})
        assert v["gate"] != "unclassified", f"{op} is emitted by effects.py but unclassified"


# --- aspirational entries must be marked, or a later lint eats them ----------

def test_entries_with_no_emitter_are_marked_aspirational():
    """stripes' ruling. The proposed lint checks live-operation -> has-entry.
    These are the REVERSE case: entries no live operation emits.

    Unmarked, someone runs that lint later, finds entries matching nothing, and
    either deletes them or -- worse -- reads the registry as evidence those
    operations are classified and safe when nothing emits them yet.
    """
    reg = br.load_registry()
    emitted_today = {"briefs.create", "briefs.adjudicate", "briefs.defer"}
    for op, entry in reg.items():
        if op in emitted_today:
            assert not entry.get("aspirational"), f"{op} IS emitted; drop the marker"
        else:
            assert entry.get("aspirational") is True, (
                f"{op} has no emitter and is not marked aspirational"
            )


def test_the_registry_can_report_what_awaits_an_emitter():
    awaiting = br.awaiting_emitter()
    assert "worktree.remove" in awaiting
    assert "briefs.adjudicate" not in awaiting


# --- the empty `low` category has a consequence, and it is testable ---------

def test_nothing_classifies_as_low_today_which_makes_medium_the_floor():
    """stripes: if nothing is `low`, every mutation requires a confirmation
    token -- there is no one-click mutation. That turns sally's question 3 from
    a preference into a constraint: either adjudication supplies the token
    invisibly, or someone carves a `low` hole in the ladder for UX convenience.

    This test FAILS THE DAY someone adds a `low` entry, which is the point --
    that is a decision that should not pass silently.
    """
    reg = br.load_registry()
    lows = [op for op, e in reg.items() if e.get("floor") == "low"]
    assert lows == [], (
        f"{lows} classify as low; sally's question-3 constraint no longer holds "
        f"and the one-click path needs re-examining"
    )
