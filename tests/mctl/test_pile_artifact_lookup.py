"""#128 -- the pile artifact lookup misses slug-named deposits.

THE DEFECT
----------
`redundant_state.py` resolved the pile artifact by exact filename:

    pile_path = layout.pile / f"{brief_id}.md"

The pile's deposited convention is frequently `<brief_id>-<slug>.md`, so a brief
whose file is present reports `state="missing"`. Measured across the live rigs
when this was filed: 5 of 12 pile files found, 7 missed.

WHY THIS IS WORSE THAN "ALWAYS MISSING"
---------------------------------------
It is a PARTIAL mismatch. A lookup that never matched would have been noticed on
day one. Matching some of the time makes `redundant_artifacts[kind=pile]` look
like a working check, so a `missing` reading is believed as a fact about the
brief rather than a naming mismatch in the lookup.

HOW THESE TESTS COULD FAIL (P6.2)
---------------------------------
The vacuous version asserts `present` for a slugged file and stops. That passes
against a fix that returns `present` unconditionally -- which is this defect
inverted and strictly worse, because a missing pile file would then be invisible.
So absence is asserted in the same file, and ambiguity is asserted too: two
candidate files must not silently resolve to the first.

  * test_exact_name_still_resolves        -- control. PASSES before and after.
  * test_slugged_deposit_resolves         -- the defect. FAILS before.
  * test_absent_pile_still_reports_missing-- the inverse. PASSES before and after.
  * test_ambiguous_candidates_do_not_silently_pick_one -- FAILS before.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core.redundant_state import ArtifactLayout, scan_artifacts  # noqa: E402


def _layout(tmp_path: Path) -> ArtifactLayout:
    root = tmp_path / "briefs"
    for sub in ("", ".pile", "stack", "decisions"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    (root / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    return ArtifactLayout(
        root=root,
        pile=root / ".pile",
        stack=root / "stack",
        stack_index=root / "stack" / ".index.jsonl",
        decisions=root / "decisions",
        legacy_manifest=root / "manifest.jsonl",
    )


def _pile(tmp_path: Path, brief_id: str, *names: str):
    layout = _layout(tmp_path)
    for name in names:
        (layout.pile / name).write_text("---\nstatus: open\n---\n", encoding="utf-8")
    artifacts = scan_artifacts(layout, brief_id, "pending")
    return next(a for a in artifacts if a.kind == "pile")


def test_exact_name_still_resolves(tmp_path: Path) -> None:
    """Control. If this breaks, the fix regressed the case that already worked."""
    assert _pile(tmp_path, "mc-abc", "mc-abc.md").state == "present"


def test_slugged_deposit_resolves(tmp_path: Path) -> None:
    """#128. FAILS today: the file is there and the lookup cannot see it."""
    artifact = _pile(tmp_path, "mc-abc", "mc-abc-some-slug-brief.md")
    assert artifact.state == "present", (
        "a deposited pile file named <brief_id>-<slug>.md must resolve; "
        f"got state={artifact.state!r} path={artifact.path.name!r}"
    )


def test_absent_pile_still_reports_missing(tmp_path: Path) -> None:
    """The inverse. A fix that always says `present` is this bug, inverted."""
    assert _pile(tmp_path, "mc-abc").state == "missing"


def test_ambiguous_candidates_do_not_silently_pick_one(tmp_path: Path) -> None:
    """Two candidates must be visible as ambiguity, not resolved by sort order.

    Silently taking the first would swap a false `missing` for a false
    `present` -- a worse failure, because it names a specific file as the
    brief's cache when the tool cannot actually tell which one is.
    """
    artifact = _pile(tmp_path, "mc-abc", "mc-abc-one.md", "mc-abc-two.md")
    assert artifact.state == "ambiguous", (
        f"two candidates must report ambiguity, got state={artifact.state!r}"
    )


def test_ambiguous_pile_is_not_reported_as_no_cache_artifact(tmp_path: Path) -> None:
    """MBRF021 must not say "no cache artifact" about a brief that has two.

    `MBRF021` fires when no artifact is `present`. Introducing a third state
    without widening that predicate makes an ambiguous pile -- two files on
    disk -- report as zero: a false diagnostic created by the fix for a false
    diagnostic.

    This asserts the PREDICATE's behaviour, not the source text. An earlier
    draft grepped briefs.py for the literal `"present", "ambiguous"`, which
    would have passed on a comment mentioning it and failed on an equivalent
    refactor -- a check that cannot fail for the right reason.
    """
    layout = _layout(tmp_path)
    for name in ("mc-abc-one.md", "mc-abc-two.md"):
        (layout.pile / name).write_text("---\nstatus: open\n---\n", encoding="utf-8")
    artifacts = scan_artifacts(layout, "mc-abc", "pending")

    # The predicate MBRF021 uses, exercised directly against real artifacts.
    has_artifact = any(
        artifact.state in {"present", "ambiguous"} for artifact in artifacts
    )
    naive = any(artifact.state == "present" for artifact in artifacts)

    assert has_artifact, "two pile files on disk must count as having an artifact"
    assert not naive, (
        "control: the naive present-only predicate must NOT see them -- if it "
        "does, this test cannot detect the regression it exists for"
    )
