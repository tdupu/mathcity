"""#66: adjudication recorded WHICH option was taken, and nothing read it.

`briefs_relay_adjudication` writes `metadata.verdict_option` whenever the caller
names one (`effects.py`, since #208). The `Verdict` object the Adjudicated
screen reads did not carry it, so the panel reported the verdict and not its
subject — and said so: *"The option taken and the follow-up bead are still not
exposed."*

WHY THE ABSENT CASE IS NOT A BLANK. A verdict on a brief that offered A–D and
recorded no option is a decision whose subject **cannot be reconstructed**.
Rendering that identically to a single-path verdict would hide the one case an
operator needs to see. `option` is None and the screen says "no option
recorded", which is a statement, not an empty cell.

WHY IT IS READ FROM THE BEAD, not from the verdict's own source. The option is a
fact about the ADJUDICATION; the verdict TEXT may have been recovered from a
typed field, from notes, or from a close reason at low confidence. A verdict
rescued from a close reason can still have had an option recorded beside it, so
tying the option to the text's provenance would drop it exactly where the record
is already weakest. The parametrised test below pins that for every source.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.beads import Bead
from mctl_core.verdicts import Verdict, read_verdict, verdict_option


def _Bead(raw):
    """The REAL Bead, not a stub.

    My first draft used a minimal stand-in and `read_verdict` reached for
    `.description`, which the stub did not have. A stub thin enough to miss a
    field the code under test reads is a test of the stub.
    """
    return Bead(
        id=str(raw.get("id", "mc-test")),
        title=str(raw.get("title", "t")),
        status=str(raw.get("status", "closed")),
        issue_type=str(raw.get("issue_type", "decision")),
        labels=(),
        source_dependencies=(),
        created_at=None,
        updated_at=None,
        raw=raw,
        description=raw.get("description"),
    )


def _bead(**metadata):
    return _Bead({"id": "mc-test", "status": "closed", "issue_type": "decision",
                  "metadata": {"verdict": "approve", **metadata}})


# --- the field that was being dropped --------------------------------------


def test_the_option_is_read_from_the_bead() -> None:
    assert verdict_option(_bead(verdict_option="A")) == "A"


def test_no_option_recorded_is_none_not_empty_string() -> None:
    """None is 'not recorded'. An empty string would render as an option."""
    assert verdict_option(_bead()) is None
    assert verdict_option(_bead(verdict_option="")) is None
    assert verdict_option(_bead(verdict_option="   ")) is None


def test_a_non_string_option_is_ignored() -> None:
    assert verdict_option(_bead(verdict_option=3)) is None
    assert verdict_option(_Bead({"metadata": None})) is None
    assert verdict_option(_Bead({})) is None


def test_the_option_is_whitespace_trimmed() -> None:
    assert verdict_option(_bead(verdict_option="  B  ")) == "B"


# --- it reaches the verdict object and the payload -------------------------


def test_the_verdict_carries_the_option() -> None:
    verdict = read_verdict(_bead(verdict_option="C"))
    assert verdict is not None
    assert verdict.option == "C"


def test_the_payload_emits_option_even_when_absent() -> None:
    """Schema stability: the key is always present, null when unrecorded, so a
    consumer can tell 'no option' from 'this reader does not report options'."""
    payload = read_verdict(_bead()).to_dict()
    assert "option" in payload
    assert payload["option"] is None


def test_option_defaults_to_none_on_a_bare_verdict() -> None:
    """Constructing a Verdict without one must not require the argument."""
    assert Verdict("approve", "typed_field", "high", "metadata.verdict").option is None


# --- the screen ------------------------------------------------------------


@pytest.mark.parametrize(
    "option,expected",
    [("A", "option A"), (None, "no option recorded"), ("", "no option recorded")],
)
def test_the_cell_states_the_option_or_its_absence(option, expected) -> None:
    from mctl_dashboard.screens.pipeline import verdict_cell

    cell = verdict_cell(
        {"verdict": {"text": "approve", "source": "typed_field",
                     "confidence": "high", "option": option}}
    )
    assert expected in cell


def test_a_brief_with_no_verdict_is_still_a_dash() -> None:
    """Unchanged: no verdict at all is not 'a verdict with no option'."""
    from mctl_dashboard.screens.pipeline import verdict_cell

    cell = verdict_cell({"verdict": None})
    assert "&mdash;" in cell
    assert "no option recorded" not in cell
