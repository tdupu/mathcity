"""Slice 2: read the verdict a closed brief already carries.

`_verdict()` read `metadata.verdict`, `decision`, and `recorded_verdict`. Two
of those three are not bd columns at all, so they could never hit; measured
against the live city they resolved **10 of 139** closed decision beads.
Meanwhile `close_reason` -- the field `bd close` actually writes -- is
non-empty on **138 of 139** and was never read.

The whole difficulty is that `close_reason` means five different things, and
only one of them is a verdict:

* a verdict            -- ``approve: YES, this is a no-brainer...``
* an execution record  -- ``All five decisions implemented: memory governor...``
* a supersession       -- ``superseded by he-saeno4 (B4 decision recorded there)``
* a withdrawal         -- ``Brief he-tqze KILLED -- jumbled; replaced by he-t0c9``
* free narrative       -- ``Closed``

Reading the last four as verdicts would be a mass false positive of exactly
the shape `MBRF021` already caused, so every one of them returns `None` with a
diagnostic naming *why*, never a guess.

`source` is always recorded. It has to be: of the 10 typed values, 7 sit
beside the `legacy verdict backfill:` `close_reason` they were copied from,
and 5 of the 10 disagree with the `close_reason` next to them. A front end
that showed all verdicts alike would be asserting a uniformity the corpus does
not have.
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import verdicts as verdict_module
from mctl_core.beads import _bead_from_mapping
from mctl_core.briefs import _approved_for_dispatch, _decision_state, _verdict
from mctl_core.verdicts import (
    SOURCE_CLOSE_REASON,
    SOURCE_DECISIONS_TRACK,
    SOURCE_NOTES,
    SOURCE_TYPED_FIELD,
    DecisionsTrack,
    brief_population,
    is_brief_bead,
    read_verdict,
    read_verdict_reading,
)


def bead(**overrides):
    row = {
        "id": "mc-1",
        "title": "A closed brief",
        "status": "closed",
        "issue_type": "decision",
    }
    row.update(overrides)
    return _bead_from_mapping(row)


# --------------------------------------------------------------------------
# close_reason is a verdict
# --------------------------------------------------------------------------


def test_a_close_reason_verdict_reads_as_adjudicated_and_names_its_source():
    """The headline case: 41 live beads carry their verdict only here."""
    subject = bead(close_reason="approve: YES, this is a no-brainer. he-m7iuh is sufficient authorization.")

    verdict = read_verdict(subject)

    assert verdict is not None, "a close_reason verdict must resolve"
    assert verdict.source == SOURCE_CLOSE_REASON
    assert verdict.text.lower().startswith("approve")
    assert _decision_state(subject) == "adjudicated"


def test_the_legacy_backfill_marker_yields_the_verdict_not_the_provenance_sentence():
    subject = bead(
        close_reason="legacy verdict backfill: A-CLOSE-DONE per decisions.jsonl 2026-06-25T14:14-1000"
    )

    verdict = read_verdict(subject)

    assert verdict is not None
    assert verdict.text == "A-CLOSE-DONE"
    assert "decisions.jsonl" not in verdict.text


def test_an_uppercase_approved_resolves():
    """`approve\\b` does not match `APPROVED`; 4 live beads are written that way."""
    subject = bead(close_reason="APPROVED -- see comment for full rationale.")

    verdict = read_verdict(subject)

    assert verdict is not None and verdict.source == SOURCE_CLOSE_REASON


def test_a_ratification_keeps_the_actor_in_the_recorded_text():
    """`ratified 2026-07-03 as-is` without `Taylor` is a fragment, not a record."""
    subject = bead(close_reason="Taylor ratified 2026-07-03 as-is. Standing guard against skew.")

    assert read_verdict(subject).text.startswith("Taylor ratified")


def test_a_taylor_verdict_line_resolves_even_with_the_option_letter_before_the_colon():
    subject = bead(close_reason="Taylor verdict A (2026-07-12): close as partially done; file follow-on.")

    verdict = read_verdict(subject)

    assert verdict is not None
    assert verdict.source == SOURCE_CLOSE_REASON


# --------------------------------------------------------------------------
# close_reason is NOT a verdict -- the four false-positive shapes
# --------------------------------------------------------------------------


def test_a_supersession_pointer_is_not_a_verdict():
    """The decision is on the successor bead. Claiming one here invents it."""
    subject = bead(close_reason="superseded by he-saeno4 (B4 decision recorded there)")

    reading = read_verdict_reading(subject)

    assert reading.verdict is None
    assert reading.code == "MBRF050"
    assert _decision_state(subject) == "malformed"


def test_a_duplicate_pointer_is_not_a_verdict():
    subject = bead(close_reason="Duplicate/superseded by gt-rqaqu")

    assert read_verdict(subject) is None
    assert read_verdict_reading(subject).code == "MBRF050"


def test_an_execution_record_is_not_a_verdict():
    """The verdict happened earlier and elsewhere; this only reports the work."""
    subject = bead(
        close_reason=(
            "All five decisions implemented: memory governor (gate/reaper/instrumentation) "
            "was done in he-6g3f.5; OOM-immune launcher implemented here."
        )
    )

    reading = read_verdict_reading(subject)

    assert reading.verdict is None
    assert reading.code == "MBRF051"
    assert _decision_state(subject) == "malformed"


def test_a_push_receipt_is_not_a_verdict():
    subject = bead(close_reason="Push/sync authorization receipt — action completed; closing in bulk triage")

    assert read_verdict(subject) is None
    assert read_verdict_reading(subject).code == "MBRF051"


def test_a_withdrawal_is_not_a_verdict():
    subject = bead(
        close_reason="Brief he-tqze KILLED (cozy 2026-06-23) — jumbled; replaced by he-t0c9."
    )

    reading = read_verdict_reading(subject)

    assert reading.verdict is None
    assert reading.code == "MBRF052"


def test_a_moot_closure_is_a_withdrawal_not_a_verdict():
    subject = bead(close_reason="moot: hecke tip-cleanup (option A) was already executed yesterday.")

    assert read_verdict(subject) is None
    assert read_verdict_reading(subject).code == "MBRF052"


def test_a_bead_with_nothing_readable_stays_malformed_with_a_diagnostic():
    subject = bead(close_reason="Closed")

    reading = read_verdict_reading(subject)

    assert reading.verdict is None
    assert reading.code == "MBRF053"
    assert reading.message
    assert _decision_state(subject) == "malformed"


def test_an_empty_close_reason_stays_malformed():
    subject = bead()

    assert read_verdict(subject) is None
    assert read_verdict_reading(subject).code == "MBRF053"
    assert _decision_state(subject) == "malformed"


def test_a_pointer_to_a_verdict_recorded_elsewhere_is_not_a_verdict():
    """`Decision recorded; verdicts in ...decisions.jsonl 310-313` names a file."""
    subject = bead(close_reason="Decision recorded; verdicts in hecke/.beads/briefs/decisions.jsonl 310-313")

    assert read_verdict(subject) is None


# --------------------------------------------------------------------------
# the other lanes
# --------------------------------------------------------------------------


def test_a_typed_field_wins_over_close_reason_and_is_labelled_typed_field():
    subject = bead(
        metadata={"verdict": "A-RESUBMIT-WITH-TARGET-MASTER"},
        close_reason="legacy verdict backfill: A-RESUBMIT-WITH-CORRECT-TARGET-NAME per decisions.jsonl",
    )

    verdict = read_verdict(subject)

    assert verdict is not None
    assert verdict.source == SOURCE_TYPED_FIELD
    assert verdict.text == "A-RESUBMIT-WITH-TARGET-MASTER"


def test_a_typed_field_that_disagrees_with_the_close_reason_it_cites_is_low_confidence():
    """5 of the 10 live typed values disagree with the close_reason beside them."""
    subject = bead(
        metadata={"verdict": "A-RESUBMIT-WITH-TARGET-MASTER"},
        close_reason="legacy verdict backfill: A-RESUBMIT-WITH-CORRECT-TARGET-NAME per decisions.jsonl",
    )

    assert read_verdict(subject).confidence == "low"


def test_a_typed_field_agreeing_with_its_close_reason_keeps_high_confidence():
    subject = bead(
        metadata={"verdict": "A-CLOSE-DONE"},
        close_reason="legacy verdict backfill: A-CLOSE-DONE per decisions.jsonl 2026-06-25T14:14-1000",
    )

    assert read_verdict(subject).confidence == "high"


def test_a_typed_field_that_prefixes_its_close_reason_is_not_a_disagreement():
    """`approve` beside `approve: <subject>` is one verdict, not two."""
    subject = bead(metadata={"verdict": "approve"}, close_reason="approve: gate-fix re-verification test")

    assert read_verdict(subject).confidence == "high"


def test_the_top_level_verdict_column_still_reads_as_a_typed_field():
    subject = bead(verdict="approve")

    verdict = read_verdict(subject)

    assert verdict is not None and verdict.source == SOURCE_TYPED_FIELD


def test_the_canonical_verdict_block_in_notes_resolves_and_is_labelled_notes():
    """7 live briefs carry `VERDICT: x | AUTHORIZER: y` in notes and nowhere else."""
    subject = bead(
        close_reason="Closed",
        notes="VERDICT: revise | AUTHORIZER: Taylor | RATIONALE: wrong order, server repair first.",
    )

    verdict = read_verdict(subject)

    assert verdict is not None
    assert verdict.source == SOURCE_NOTES
    assert verdict.text == "revise"
    assert _decision_state(subject) == "adjudicated"


def test_prose_in_notes_without_the_canonical_block_is_not_a_verdict():
    subject = bead(close_reason="Closed", notes="Some background on how this came up.")

    assert read_verdict(subject) is None


# --------------------------------------------------------------------------
# decisions-track manifest
# --------------------------------------------------------------------------


def test_a_manifest_sourced_verdict_resolves_and_is_labelled_decisions_track():
    track = DecisionsTrack.from_rows(
        [
            {"n": 8, "slug": "sigma18-done-vs-residual", "source_bead": "he-0rk2",
             "status": "adjudicated", "verdict": "residual"},
        ]
    )
    subject = bead(
        close_reason="Closed",
        dependencies=[{"issue_id": "mc-1", "depends_on_id": "he-0rk2", "type": "related"}],
    )

    verdict = read_verdict(subject, track=track)

    assert verdict is not None
    assert verdict.source == SOURCE_DECISIONS_TRACK
    assert verdict.text == "residual"


def test_a_manifest_row_with_no_verdict_does_not_resolve():
    track = DecisionsTrack.from_rows(
        [{"n": 1, "slug": "gh-auth-login", "source_bead": "he-0rk2", "status": "present-it-pending"}]
    )
    subject = bead(
        close_reason="Closed",
        dependencies=[{"issue_id": "mc-1", "depends_on_id": "he-0rk2", "type": "related"}],
    )

    assert read_verdict(subject, track=track) is None


def test_the_manifest_never_outranks_a_field_on_the_bead_itself():
    track = DecisionsTrack.from_rows(
        [{"n": 8, "slug": "s", "source_bead": "he-0rk2", "verdict": "residual"}]
    )
    subject = bead(
        close_reason="approve: ship it",
        dependencies=[{"issue_id": "mc-1", "depends_on_id": "he-0rk2", "type": "related"}],
    )

    assert read_verdict(subject, track=track).source == SOURCE_CLOSE_REASON


def test_an_unjoinable_manifest_row_resolves_nothing():
    """Measured live: 0 of 126 verdict-bearing rows join to any decision bead."""
    track = DecisionsTrack.from_rows(
        [{"n": 8, "slug": "s", "source_bead": None, "verdict": "approve"}]
    )

    assert read_verdict(bead(close_reason="Closed"), track=track) is None


# --------------------------------------------------------------------------
# beads that were never briefs
# --------------------------------------------------------------------------


def test_an_authorize_git_operation_bead_leaves_the_brief_population():
    """B2.1: push authorizations stay standalone decision beads, not briefs."""
    receipt = bead(
        id="gt-xwq3qz",
        title="Taylor authorized git PUSH: tdupu/gascity-packs main",
        description="Authorization gate invoked via authorize-git-operation skill.",
        notes="Operation: PUSH. Verdict: AUTHORIZED.",
        close_reason="Decision recorded.",
    )

    assert is_brief_bead(receipt) is False
    assert receipt not in brief_population([receipt, bead()])


def test_an_authorize_git_operation_bead_gains_no_verdict():
    """It must not be repaired into the population by the back door either."""
    receipt = bead(
        description="Authorization gate invoked via authorize-git-operation skill.",
        notes="Operation: PUSH. Verdict: AUTHORIZED.",
        close_reason="Decision recorded.",
    )

    reading = read_verdict_reading(receipt)

    assert reading.verdict is None
    assert reading.code == "MBRF054"


def test_an_ordinary_brief_stays_in_the_brief_population():
    subject = bead(description="## §1 — What is being decided\n\nWhether to ship.")

    assert is_brief_bead(subject) is True


def test_a_non_decision_bead_is_not_a_brief():
    assert is_brief_bead(bead(issue_type="task")) is False


# --------------------------------------------------------------------------
# invariants the front end depends on
# --------------------------------------------------------------------------


def test_every_resolved_verdict_records_a_source_and_a_confidence():
    subjects = [
        bead(metadata={"verdict": "approve"}),
        bead(close_reason="approve: ship it"),
        bead(close_reason="Closed", notes="VERDICT: reject | AUTHORIZER: Taylor"),
    ]

    for subject in subjects:
        verdict = read_verdict(subject)
        assert verdict is not None
        assert verdict.source in verdict_module.SOURCES
        assert verdict.confidence in verdict_module.CONFIDENCES
        assert verdict.to_dict()["source"] == verdict.source


def test_an_open_bead_is_not_adjudicated_however_its_close_reason_reads():
    subject = bead(status="open", close_reason="approve: ship it")

    assert _decision_state(subject) == "pending"


def test_a_prose_approval_does_not_become_a_dispatch_authorization():
    """Reading a verdict must not silently widen who may dispatch work.

    `_approved_for_dispatch` compares the verdict to an exact token set. A
    `close_reason` verdict is a sentence, so it stays outside that set --
    deliberately: `approve: promote X into a standing filter rule` authorises
    a decision, and inferring a dispatch grant from it would be the adapter
    making a call nobody asked it to make. Measured against the live city,
    only the two briefs carrying a canonical `VERDICT: approve | AUTHORIZER:`
    block newly qualify, which is the intended effect.
    """
    prose = bead(close_reason="approve: promote the filter rule into a standing rule, per §4")

    assert _approved_for_dispatch(prose) is False
    assert _approved_for_dispatch(bead(notes="VERDICT: approve | AUTHORIZER: Taylor")) is True


def test_the_legacy_verdict_helper_still_answers_a_plain_string():
    """`_verdict()` has callers that compare it to a cached string."""
    subject = bead(close_reason="approve: ship it")

    assert isinstance(_verdict(subject), str)
    assert _verdict(bead(close_reason="superseded by gt-1")) is None
