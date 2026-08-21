"""The brief read asks for decision beads, not for every bead in the rig.

`bd list --all --limit 0` returns every bead a rig holds. On the live city that
is 30,364 rows for `hq`, of which **80** are decisions -- 0.3%. 83% are agent
session bookkeeping that no brief surface can ever consult, because
`Bead.is_brief` is exactly `issue_type == "decision"`.

Every dashboard view paid for all 30,364. This narrows the *brief* read only.
`work.py` shares `read_beads` and genuinely needs other types -- it resolves
source beads and child workflow beads -- so the shared default must not change.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core import beads as beads_mod


def _fixture(tmp_path: Path) -> Path:
    rows = [
        {"id": "d-1", "issue_type": "decision", "title": "a brief", "status": "open"},
        {"id": "d-2", "issue_type": "decision", "title": "another brief", "status": "closed"},
        {"id": "s-1", "issue_type": "session", "title": "session churn", "status": "open"},
        {"id": "t-1", "issue_type": "task", "title": "a work item", "status": "open"},
        {"id": "e-1", "issue_type": "event", "title": "an event", "status": "open"},
    ]
    path = tmp_path / "beads.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))
    return path


def test_read_beads_can_be_narrowed_to_one_issue_type(tmp_path: Path):
    """The filter is a property of the read, not of the transport.

    It must apply to an injected fixture too -- otherwise every fixture-based
    test is blind to a mistake in the filter.
    """
    got = beads_mod.read_beads(tmp_path, fixture_path=_fixture(tmp_path), issue_type="decision")

    assert sorted(b.id for b in got) == ["d-1", "d-2"], (
        "narrowing must drop session/task/event rows on the fixture path too"
    )


def test_the_unfiltered_read_is_unchanged(tmp_path: Path):
    """`work.py` shares this function and needs tasks and sessions."""
    got = beads_mod.read_beads(tmp_path, fixture_path=_fixture(tmp_path))

    assert sorted(b.id for b in got) == ["d-1", "d-2", "e-1", "s-1", "t-1"], (
        "the default read must still return every type"
    )


def test_the_narrowed_read_keeps_every_brief_bead(tmp_path: Path):
    """Equivalence: nothing a brief surface would have seen is lost.

    `Bead.is_brief` is `issue_type == "decision"`, so the narrowed set and the
    brief-eligible subset of the full set must be identical.
    """
    fixture = _fixture(tmp_path)
    full = beads_mod.read_beads(tmp_path, fixture_path=fixture)
    narrowed = beads_mod.read_beads(tmp_path, fixture_path=fixture, issue_type="decision")

    assert sorted(b.id for b in narrowed) == sorted(b.id for b in full if b.is_brief)


def test_the_subprocess_asks_bd_for_the_narrowed_type(monkeypatch, tmp_path: Path):
    """Narrowing only in Python would still pay the full transfer cost.

    The 380x saving is `bd` not serialising 30,284 irrelevant rows, so the
    filter has to reach the command line.
    """
    seen: list[list[str]] = []

    class _Result:
        returncode = 0
        stdout = "[]"
        stderr = ""

    def _fake_run(args, **kwargs):
        seen.append(list(args))
        return _Result()

    monkeypatch.setattr(beads_mod.subprocess, "run", _fake_run)
    beads_mod.read_beads(tmp_path, issue_type="decision")

    assert seen, "no bd invocation was made"
    assert "--type" in seen[0] and "decision" in seen[0], (
        f"the type filter never reached bd: {seen[0]}"
    )
