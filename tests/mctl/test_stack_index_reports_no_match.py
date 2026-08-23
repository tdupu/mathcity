"""#92: `_update_stack_index` wrote nothing and said nothing when no row matched.

The write not happening is FINE. Not saying so is the defect.

WHY A WARN AND NOT A RAISE-TO-FAILURE. The two cache writers are gated
differently, and that asymmetry decides the fix:

    effects.py  stack_index      planned if stack_index.exists()   <- the FILE
    effects.py  decisions_track  planned if row_key and ...        <- the ROW

cozy's decisions-track writer can treat a no-match as an error because its
planner already established the row should be there. The stack-index planner has
no such precondition -- it plans an update for EVERY brief whenever the index
file exists, including briefs that have no row. Measured on the live corpus: 57
index rows against 79 briefs in `.adjudicated-archive/`, and an archived brief
has no row BY CONSTRUCTION (B2.15: drained means de-indexed AND archived).

So raising to a failed adjudication would turn a correct silent no-op into a
manufactured error on the majority case. The report must reach the operator
without failing the write -- exactly how `DecisionsTrackRowUnwritable` is already
handled at effects.py:634.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core import effects  # noqa: E402


def write_index(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / ".index.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def test_a_matching_row_is_updated_and_reports_no_problem(tmp_path):
    """Control. If this ever fails, the other assertions prove nothing."""
    path = write_index(tmp_path, [{"slug": "b1", "source": "b1", "status": "ready"}])
    effects._update_stack_index(path, "b1", {"status": "adjudicated"})
    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row["status"] == "adjudicated"


def test_no_matching_row_RAISES_a_typed_report_instead_of_writing_nothing(tmp_path):
    """The defect: this call used to return None and touch nothing, silently."""
    path = write_index(tmp_path, [{"slug": "other", "source": "other", "status": "ready"}])
    with pytest.raises(effects.StackIndexRowUnwritable) as caught:
        effects._update_stack_index(path, "absent-brief", {"status": "adjudicated"})
    assert "absent-brief" in str(caught.value)


def test_the_untouched_file_is_left_byte_identical_when_nothing_matched(tmp_path):
    """Reporting must not become a write. A no-match still writes nothing."""
    path = write_index(tmp_path, [{"slug": "other", "source": "other", "status": "ready"}])
    before = path.read_bytes()
    with pytest.raises(effects.StackIndexRowUnwritable):
        effects._update_stack_index(path, "absent-brief", {"status": "adjudicated"})
    assert path.read_bytes() == before


def test_an_idempotent_rewrite_is_NOT_reported_as_a_no_match(tmp_path):
    """A row that already carries the values matched -- it just needed no write.

    Without this, the guard could pass by reporting every write that changed
    nothing, which would fire on every repeat adjudication.
    """
    path = write_index(tmp_path, [{"slug": "b1", "source": "b1", "status": "adjudicated"}])
    effects._update_stack_index(path, "b1", {"status": "adjudicated"})  # must not raise
