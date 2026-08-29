"""mc-crc4o: the OLD pile lookup still resolves by filename alone.

`locate_artifact` (mc-8q0g4) resolves a bead's artifacts by bead identity --
exact name, then a single `<id>-<slug>` candidate, then the `artifact:`
frontmatter key. `_pile_artifact`/`scan_artifacts` -- the path `briefs_validate`
and the artifact-trust gate actually consult -- stops at the first two. So the
two halves of the same system disagree about whether an artifact exists.

Taylor settled the convention in OPEN-DESIGN-QUESTIONS Q5 (RESOLVED 2026-08-19):
*"the briefs are supposed to be decision beads so it should be however beads are
looked-up."* Bead identity is canonical, so the id in the frontmatter IS the
address. Q5 says the consequence outright -- `scan_artifacts` "would fail to
find these files even if it were pointed at the correct root."

MEASURED on the live mathcity pile, 2026-08-28: 99 files, four addressable ONLY
by frontmatter and findable by no filename at all.

    mc-g4k2   in mc-cbks.md
    mc-99jj   in mc-j6uh.md
    mc-k4t1s  in mc-kjot0.md      <- under active work by another lane that day
    mc-jvqq   in mc-tfp4.md

WHY THIS IS NOT COSMETIC. `MBRF021` ("no redundant cache artifact") is a B2.8
violation code whose documented remedy is to repair the filesystem to match the
bead store. Acting on it for these four would CREATE duplicates of artifacts
that already exist under other names. The withheld-code guard exists precisely
because the lookup is wrong; fixing the lookup is what makes the code safe to
act on. **Fix the lookup, never the files.**

HOW THESE TESTS COULD FAIL (P6.2)
---------------------------------
The vacuous version asserts a frontmatter-addressed file resolves and stops --
which passes against a lookup that returns `present` unconditionally, i.e. this
defect inverted and strictly worse, because a genuinely missing artifact would
then be invisible. So absence and ambiguity are asserted in the same file, and
the exact-name precedence is asserted so the cheap path is not displaced by the
scan.

  * test_exact_name_still_wins                  -- control. Passes before and after.
  * test_absent_still_reports_missing           -- the inverse. Passes before and after.
  * test_frontmatter_addressed_file_is_found    -- the defect. FAILS before.
  * test_two_claimants_are_ambiguous_not_present-- the guess this must not make.
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


def _write(layout: ArtifactLayout, name: str, body: str) -> Path:
    path = layout.pile / name
    path.write_text(body, encoding="utf-8")
    return path


def _pile(layout: ArtifactLayout, brief_id: str):
    artifacts = scan_artifacts(layout, brief_id, decision_state="open")
    return next(a for a in artifacts if a.kind == "pile")


# -- controls --------------------------------------------------------------


def test_exact_name_still_wins(tmp_path: Path) -> None:
    """The cheap path must not be displaced by the frontmatter scan."""
    layout = _layout(tmp_path)
    _write(layout, "mc-tbucy.md", "---\nartifact: mc-tbucy\n---\n")
    _write(layout, "decoy-brief.md", "---\nartifact: mc-tbucy\n---\n")

    found = _pile(layout, "mc-tbucy")

    assert found.state == "present"
    assert found.path.name == "mc-tbucy.md"


def test_absent_still_reports_missing(tmp_path: Path) -> None:
    """The inverse control. Without it, an unconditional `present` passes below."""
    layout = _layout(tmp_path)
    _write(layout, "mc-someone-else.md", "---\nartifact: mc-someone-else\n---\n")

    assert _pile(layout, "mc-tbucy").state == "missing"


# -- the defect ------------------------------------------------------------


def test_frontmatter_addressed_file_is_found(tmp_path: Path) -> None:
    """The four live beads' shape: id in frontmatter, unrelated filename."""
    layout = _layout(tmp_path)
    _write(
        layout,
        "mc-cbks.md",
        "---\nartifact: mc-g4k2\nstatus: adjudicated\n---\n\nbody\n",
    )

    found = _pile(layout, "mc-g4k2")

    assert found.state == "present"
    assert found.path.name == "mc-cbks.md"


def test_two_claimants_are_ambiguous_not_present(tmp_path: Path) -> None:
    """Adding the scan must not reintroduce the guess `_pile_artifact` refuses.

    Resolving two claimants by sort order would replace a false `missing` with a
    false `present` naming a specific file the lookup cannot actually identify --
    worse than the defect, because it is confident.
    """
    layout = _layout(tmp_path)
    _write(layout, "one-brief.md", "---\nartifact: mc-g4k2\n---\n")
    _write(layout, "two-brief.md", "---\nartifact: mc-g4k2\n---\n")

    assert _pile(layout, "mc-g4k2").state == "ambiguous"
