"""MBRF001 -- `_stack_artifact` double-joins every row that is not bare/absolute.

THE DEFECT
----------
`redundant_state._stack_artifact` resolved a stack index row with:

    if not stack_path.is_absolute():
        stack_path = layout.stack / stack_path

That is correct for exactly one relative form: a BARE filename ("x.md").
`brief-stack-index.py` documents four serializations the live index is known to
hold (`path_serialization`, :475), and the writer
`brief-shuffle-fast-drain.py:812` emits the BRIEFS-RELATIVE form `f"stack/{slug}.md"`.
Joining that against `layout.stack` yields `.../stack/stack/x.md`, which does not
exist, so a present brief reports `state="stale"` and blocks approve.

The CITY-RELATIVE form (".beads/briefs/stack/x.md") is broken the same way and
was not in the original report: it resolved to
`.../stack/.beads/briefs/stack/x.md`.

MEASURED BLAST RADIUS (live `.beads/briefs/stack/.index.jsonl`, 7 rigs,
2026-10-02): 68 briefs-relative + 16 city-relative = 84 affected rows;
40 absolute rows were fine. There were ZERO bare rows -- the only relative form
the old code handled is the one nothing writes.

HOW THESE TESTS COULD FAIL (P6.2)
---------------------------------
The controls matter as much as the repros. `test_bare_name_still_resolves` and
`test_absolute_still_resolves` pin the two forms that already worked; a "fix"
that resolved the new forms by loosening the join until everything matched would
break them. `test_genuinely_missing_still_stale` pins that the fix did not turn
the resolver into a search that always finds something -- a row pointing at a
file that truly is not there must still read `stale`, or MBRF001 stops being
able to report real staleness at all.
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core.redundant_state import ArtifactLayout, _stack_artifact  # noqa: E402


def _layout(tmp_path: Path) -> ArtifactLayout:
    """A layout whose briefs root ends in `.beads/briefs`, as the live rigs do.

    The city-relative case is only meaningful against a realistic root: the row
    repeats the briefs-root tail, so a `tmp_path/briefs` root would not exercise
    it.
    """
    root = tmp_path / ".beads" / "briefs"
    for sub in ("", ".pile", "stack", "decisions"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    return ArtifactLayout(
        root=root,
        pile=root / ".pile",
        stack=root / "stack",
        stack_index=root / "stack" / ".index.jsonl",
        decisions=root / "decisions",
        legacy_manifest=root / "manifest.jsonl",
    )


def _artifact(tmp_path: Path, stored_path: str, *, create: bool = True):
    layout = _layout(tmp_path)
    if create:
        (layout.stack / "he-yo7cf2.md").write_text("brief\n", encoding="utf-8")
    return _stack_artifact(layout, {"path": stored_path}, "pending")


def test_briefs_relative_resolves(tmp_path: Path) -> None:
    """THE REPRO. `stack/x.md` is what brief-shuffle-fast-drain.py:812 writes."""
    artifact = _artifact(tmp_path, "stack/he-yo7cf2.md")
    assert artifact.state == "present", f"double-joined to {artifact.path}"


def test_city_relative_resolves(tmp_path: Path) -> None:
    """Same defect, unreported form: 16 live rows."""
    artifact = _artifact(tmp_path, ".beads/briefs/stack/he-yo7cf2.md")
    assert artifact.state == "present", f"double-joined to {artifact.path}"


def test_bare_name_still_resolves(tmp_path: Path) -> None:
    """Control. The one relative form the old code got right."""
    assert _artifact(tmp_path, "he-yo7cf2.md").state == "present"


def test_absolute_still_resolves(tmp_path: Path) -> None:
    """Control. Absolute rows were never broken; 40 live rows depend on this."""
    layout = _layout(tmp_path)
    target = layout.stack / "he-yo7cf2.md"
    target.write_text("brief\n", encoding="utf-8")
    assert _stack_artifact(layout, {"path": str(target)}, "pending").state == "present"


def test_genuinely_missing_still_stale(tmp_path: Path) -> None:
    """Control. The fix must not become a search that always finds something."""
    artifact = _artifact(tmp_path, "stack/he-does-not-exist.md", create=False)
    assert artifact.state == "stale"


def test_adjudicated_still_inconsistent(tmp_path: Path) -> None:
    """Control. Resolving the path must not bypass the decision-state branch."""
    layout = _layout(tmp_path)
    (layout.stack / "he-yo7cf2.md").write_text("brief\n", encoding="utf-8")
    artifact = _stack_artifact(layout, {"path": "stack/he-yo7cf2.md"}, "adjudicated")
    assert artifact.state == "inconsistent"
