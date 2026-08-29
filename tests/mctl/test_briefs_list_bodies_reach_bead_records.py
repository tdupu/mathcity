"""#229: `bodies=true` never reached bead-backed records, and said nothing.

`list_briefs_report` threaded `bodies` into `_document_records` only. A
bead-backed brief therefore came back from the roster with **no `body` key at
all** and `body_elided: null` -- carrying nothing while positively claiming
nothing was withheld.

MEASURED 2026-08-29, rig hq, `briefs_list(status=open, bodies=true)`: all nine
records `source: "bead"`, none with a `body` key, all `body_elided: null`, and
two (`gt-6x491h`, `gt-pnq9im`) naming a real `body_path` on disk -- so it was
never "there is no body to show".

WHY THIS WAS NOT COSMETIC, and why the option tests below are the point.
`BriefRecord.to_dict` emits `decision_options` and `recommendation` ONLY when
`body is not None` (#76 Field 8). No body on the roster therefore meant no
caller could discover that a brief requires an `option` argument -- while
`briefs_relay_adjudication` refuses without one (MOPT001). Batch adjudication
through the typed surface was impossible, and the roster gave no hint why.

THE TWO HALVES ARE TESTED SEPARATELY BECAUSE THEY FAIL SEPARATELY:

  bodies=True  -> the body must arrive, and options/recommendation with it
  bodies=False -> the record must SAY so, via BODY_ELIDED_ON_ROSTER, not null

A fix that only did the first would leave the silent-omission half intact, and
that half is the one that misleads a caller who never passes `bodies`.
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.briefs import (
    BODY_ELIDED_ON_ROSTER,
    BriefRecord,
    SOURCE_BEAD,
    _bead_records_with_body_state,
)


class _FakeBead:
    def __init__(self, bead_id: str, description: str) -> None:
        self.id = bead_id
        self.description = description


BODY_WITH_OPTIONS = """## §1 — What is being decided

Whether to do the thing.

## §4 — Options

- **(A) Do it** *(recommended)* the cheap path
- **(B) Do not** the other path
"""


def _record(brief_id: str = "mc-x1", bead_id: str = "mc-x1") -> BriefRecord:
    return BriefRecord(
        brief_id=brief_id,
        bead_id=bead_id,
        title="a decision",
        status="open",
        decision_state="pending",
        labels=(),
        created_at=None,
        updated_at=None,
        redundant_artifacts=(),
        policy_references=(),
        source=SOURCE_BEAD,
    )


def _enrich(ctx, *, bodies: bool):
    beads = (_FakeBead("mc-x1", BODY_WITH_OPTIONS),)
    return _bead_records_with_body_state(ctx, (_record(),), beads, bodies=bodies)


# --- bodies=False: the silent half -----------------------------------------


def test_without_bodies_the_record_says_the_body_was_withheld(monkeypatch) -> None:
    """`null` there asserted nothing was withheld. That was false."""
    (record,) = _enrich(None, bodies=False)
    assert record.body is None
    assert record.body_elided == BODY_ELIDED_ON_ROSTER


def test_the_elision_label_names_how_to_get_the_body() -> None:
    """A caller holding one record must be able to act on it, not just notice."""
    assert "bodies=true" in BODY_ELIDED_ON_ROSTER
    assert "briefs show" in BODY_ELIDED_ON_ROSTER


# --- bodies=True: the missing half -----------------------------------------


def test_with_bodies_the_body_arrives(monkeypatch) -> None:
    import mctl_core.briefs as briefs

    monkeypatch.setattr(briefs, "brief_body", lambda ctx, bid, bead: BODY_WITH_OPTIONS)
    monkeypatch.setattr(briefs, "brief_body_report", lambda ctx, bid, body: ((), ()))
    (record,) = _enrich(None, bodies=True)
    assert record.body == BODY_WITH_OPTIONS
    assert record.body_elided is None, "nothing was withheld, so do not label it"


def test_with_bodies_the_payload_carries_options_and_recommendation(monkeypatch) -> None:
    """The consequence that made this P-worthy: MOPT001 is undiscoverable
    from a roster whose records carry no body."""
    import mctl_core.briefs as briefs

    monkeypatch.setattr(briefs, "brief_body", lambda ctx, bid, bead: BODY_WITH_OPTIONS)
    monkeypatch.setattr(briefs, "brief_body_report", lambda ctx, bid, body: ((), ()))
    (record,) = _enrich(None, bodies=True)
    payload = record.to_dict()
    assert "body" in payload
    assert payload["decision_options"], "a brief offering options must say so"
    # `label` is the option id the verdict names (A/B/...); `title` is its prose.
    # Checked against the live parser rather than assumed -- my first draft
    # guessed `id` and was wrong, which is the same class of error as the bug.
    assert {o["label"] for o in payload["decision_options"]} == {"A", "B"}
    assert payload["recommendation"] == "A"
    assert [o["recommended"] for o in payload["decision_options"]] == [True, False]


def test_without_bodies_the_payload_omits_options_rather_than_faking_them() -> None:
    """The default stays a cheap metadata read; absence must not be forged."""
    (record,) = _enrich(None, bodies=False)
    payload = record.to_dict()
    assert "body" not in payload
    assert "decision_options" not in payload
    assert payload["body_elided"] == BODY_ELIDED_ON_ROSTER


# --- a bead the snapshot does not cover ------------------------------------


def test_a_record_whose_bead_is_missing_still_returns_a_record(monkeypatch) -> None:
    """A snapshot gap must not drop the row -- an unreadable body is still a
    brief the operator needs to see listed."""
    import mctl_core.briefs as briefs

    monkeypatch.setattr(briefs, "brief_body", lambda ctx, bid, bead: "")
    monkeypatch.setattr(briefs, "brief_body_report", lambda ctx, bid, body: ((), ()))
    out = _bead_records_with_body_state(None, (_record(bead_id="absent"),), (), bodies=True)
    assert len(out) == 1
    assert out[0].brief_id == "mc-x1"


def test_every_record_is_returned_exactly_once() -> None:
    """Guard against the enrichment dropping or duplicating rows."""
    records = tuple(_record(brief_id=f"mc-{n}", bead_id=f"mc-{n}") for n in range(5))
    out = _bead_records_with_body_state(None, records, (), bodies=False)
    assert [r.brief_id for r in out] == [r.brief_id for r in records]
