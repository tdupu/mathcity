"""The move mctl could not do (#95, brief mc-up5vd).

`EffectPlan` had creates, updates and writes and NO move, rename or delete, and
`apply_file_create` refuses to overwrite. So nothing in mctl could relocate a
file, and 28 briefs carrying a TERMINAL status sat on the PENDING stack -- a
count that went 8 -> 27 -> 28 while the gap stayed open.

The de-index half already existed and was already CORRECT:
`brief-stack-index.py::should_reconcile_remove` refuses to de-index a brief with
no archive copy, because "saying adjudicated is a claim, and a claim is not an
archive". It was refusing because nothing performed the move.

These tests pin the safety properties, not the happy path. The happy path is one
assertion; the ordering guarantees are the reason this code is careful.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core.effects import _archive_brief  # noqa: E402


def _tree(tmp_path: Path, *, body: str = "---\nstatus: adjudicated\n---\n\nbody\n"):
    stack = tmp_path / "stack"
    stack.mkdir()
    archive = tmp_path / ".adjudicated-archive"
    brief = stack / "mc-x1.md"
    brief.write_text(body, encoding="utf-8")
    index = stack / ".index.jsonl"
    index.write_text(
        json.dumps({"slug": "mc-x1", "path": "stack/mc-x1.md"}) + "\n"
        + json.dumps({"slug": "mc-other", "path": "stack/mc-other.md"}) + "\n",
        encoding="utf-8",
    )
    fields = {"archive_path": str(archive / "mc-x1.md"), "index_path": str(index)}
    return brief, archive / "mc-x1.md", index, fields


def test_archives_and_deindexes_in_one_act(tmp_path):
    brief, archived, index, fields = _tree(tmp_path)
    _archive_brief(brief, "mc-x1", fields)

    assert not brief.exists(), "the stack copy must be gone"
    assert archived.is_file(), "the archive copy must exist"
    rows = [json.loads(l) for l in index.read_text().splitlines() if l.strip()]
    assert [r["slug"] for r in rows] == ["mc-other"], "only this brief's row is dropped"


def test_the_copy_is_verified_before_the_original_is_destroyed(tmp_path):
    """The ordering IS the safety property.

    If the read-back fails, the stack file must still be there -- nothing lost.
    Simulated by making the archive PARENT an existing regular file, so the
    `mkdir` for it must fail: the original must survive.
    """
    brief, archived, index, fields = _tree(tmp_path)
    blocker = tmp_path / "blocked"
    blocker.write_text("I am a file, not a directory\n", encoding="utf-8")
    fields["archive_path"] = str(blocker / "mc-x1.md")

    with pytest.raises(OSError):
        _archive_brief(brief, "mc-x1", fields)

    assert brief.is_file(), "the stack file must survive a failed archive"
    rows = [json.loads(l) for l in index.read_text().splitlines() if l.strip()]
    assert len(rows) == 2, "nothing is de-indexed when the move did not happen"


def test_refuses_to_overwrite_a_DIFFERENT_archived_decision(tmp_path):
    """#95's third defect: a slug present in BOTH lanes.

    Overwriting would silently destroy one of two adjudications. Refusing
    surfaces it, which is the only outcome that cannot lose a decision.
    """
    brief, archived, index, fields = _tree(tmp_path)
    archived.parent.mkdir(parents=True)
    archived.write_text("a DIFFERENT decision\n", encoding="utf-8")

    with pytest.raises(OSError, match="DIFFERENT content"):
        _archive_brief(brief, "mc-x1", fields)

    assert brief.is_file()
    assert archived.read_text() == "a DIFFERENT decision\n"


def test_an_identical_archive_copy_is_idempotent(tmp_path):
    """Re-running after a crash between move and de-index must converge.

    The step order leaves exactly this state on a crash, so it must be safe to
    repeat rather than requiring manual repair.
    """
    body = "---\nstatus: adjudicated\n---\n\nbody\n"
    brief, archived, index, fields = _tree(tmp_path, body=body)
    archived.parent.mkdir(parents=True)
    archived.write_text(body, encoding="utf-8")

    _archive_brief(brief, "mc-x1", fields)

    assert not brief.exists()
    rows = [json.loads(l) for l in index.read_text().splitlines() if l.strip()]
    assert [r["slug"] for r in rows] == ["mc-other"]


def test_refuses_when_the_brief_is_not_on_the_stack(tmp_path):
    """A missing source is NOT "already archived".

    It may be a slug collision or a concurrent writer, and guessing between
    those is how a brief gets lost.
    """
    brief, archived, index, fields = _tree(tmp_path)
    brief.unlink()
    with pytest.raises(OSError, match="not a file"):
        _archive_brief(brief, "mc-x1", fields)


def test_a_malformed_index_row_is_preserved_not_normalised(tmp_path):
    """Same discipline as add-missing-rows: a malformed row stays as malformed.

    Rewriting it would be a silent repair of a record nobody audited.
    """
    brief, archived, index, fields = _tree(tmp_path)
    index.write_text(
        '{"slug": "mc-x1", "path": "stack/mc-x1.md"}\n{ this is not json\n',
        encoding="utf-8",
    )
    _archive_brief(brief, "mc-x1", fields)
    text = index.read_text()
    assert "{ this is not json" in text, "the malformed row must survive untouched"
    assert "mc-x1" not in text, "the target row must still be dropped"
