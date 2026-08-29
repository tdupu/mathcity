"""mc-8q0g4 -- no typed way to ask "where does this artifact live, and is it there?"

THE DEFECT
----------
mctl exposes 48 tools and not one answers that question. The machinery to answer
it exists and is sound: `artifact_layout()` resolves the brief root rig-relative,
and `_pile_artifact()` already handles exact-vs-slug filenames and refuses to pick
between two candidates. It is simply unreachable as a tool.

So an agent holding the question shells out to `find` against a hand-typed path.

WHY THAT IS A TRAP AND NOT CARELESSNESS
---------------------------------------
Measured 2026-08-28, and this is the number the whole design turns on:

    <city-root>/mathcity/.beads/briefs/decisions/*.toml    118 files
    <city-root>/.beads/briefs/decisions/*.toml              11 files

The wrong root is NOT empty. A probe there returns clean, populated, entirely
plausible output that is simply about a different rig. Nothing local to the
caller distinguishes it from the right answer. That is how brief mc-tbucy was
reported as having no recorded verdict -- published to a peer as a correction,
and written into a bead comment -- while both its artifacts sat in the rig root
the whole time. Had it stood, it would have sent QUIMBY to RE-ADJUDICATE a
decision Taylor had already made (mc-tbucy, approve, C+D). Re-asking a human a
settled question is the expensive failure here, not the wrong log line.

"Be more careful" cannot fix a trap whose failure mode is indistinguishable from
success. Two structural properties can:

  1. The caller passes a BEAD ID, never a path. The tool resolves the root
     itself, through the one existing resolver. Looking in the wrong tree stops
     being an available move.
  2. Every answer carries its own provenance -- resolved root, whether that root
     exists, and the corpus size. The corpus size IS the control, executed by
     the tool rather than remembered by the agent: "no artifact here, out of 118"
     and "no artifact here, out of 0" are different claims and must not render
     identically.

And the verdict must have THREE values, not two. When the root does not exist,
the tool cannot distinguish "this rig has piled nothing yet" from "I resolved the
wrong root" -- so it must say `unknown`, never `absent`. That is POLICY P6.2's
mirror: a check that could not have failed must not render as a check that
passed, and a diagnostic that could not have succeeded must not render as one
that found nothing.

HOW THESE TESTS COULD FAIL (P6.2)
---------------------------------
The vacuous version asserts `present` for a file that exists and stops -- which
passes against an implementation returning `present` unconditionally, i.e. this
defect inverted and strictly worse. So absence, ambiguity, and the unknown/absent
distinction are each asserted here, and each is paired with the reading it must
NOT collapse into.

  * test_exact_name_resolves_present            -- control. Must pass.
  * test_absent_artifact_in_an_existing_root_is_absent  -- the inverse control.
  * test_missing_root_is_unknown_not_absent     -- the core new behaviour.
  * test_corpus_size_distinguishes_the_two_absences -- makes absence auditable.
  * test_ambiguity_is_not_flattened_to_present  -- preserves existing discipline.
  * test_every_answer_names_the_root_it_searched -- pins the provenance.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core.redundant_state import ArtifactLayout, locate_artifact  # noqa: E402


def _layout(tmp_path: Path, *, make_dirs: bool = True) -> ArtifactLayout:
    root = tmp_path / "briefs"
    if make_dirs:
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


def _write(layout: ArtifactLayout, relative: str, body: str = "x") -> Path:
    path = layout.root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")
    return path


# -- controls --------------------------------------------------------------


def test_exact_name_resolves_present(tmp_path: Path) -> None:
    """Without this, every assertion below could pass on a probe that finds nothing."""
    layout = _layout(tmp_path)
    _write(layout, ".pile/mc-tbucy.md")

    found = locate_artifact(layout, "mc-tbucy")

    pile = found.artifact("pile")
    assert pile.verdict == "present"
    assert pile.path is not None and pile.path.name == "mc-tbucy.md"


def test_absent_artifact_in_an_existing_root_is_absent(tmp_path: Path) -> None:
    """The inverse control: a real absence must still read as absent, not unknown.

    Without this, an implementation answering `unknown` for everything would pass
    the unknown test below while destroying the tool's usefulness.
    """
    layout = _layout(tmp_path)
    _write(layout, ".pile/mc-other.md")  # corpus non-empty, our id is not in it

    found = locate_artifact(layout, "mc-tbucy")

    assert found.artifact("pile").verdict == "absent"


# -- the defect ------------------------------------------------------------


def test_missing_root_is_unknown_not_absent(tmp_path: Path) -> None:
    """A root that does not exist cannot tell empty-rig from wrong-root.

    This is the reading that, as `absent`, produced the mc-tbucy false report.
    """
    layout = _layout(tmp_path, make_dirs=False)

    found = locate_artifact(layout, "mc-tbucy")

    assert found.root_exists is False
    assert found.artifact("pile").verdict == "unknown"
    assert found.artifact("decisions").verdict == "unknown"


def test_corpus_size_distinguishes_the_two_absences(tmp_path: Path) -> None:
    """"Absent out of 3" and "absent out of 0" must not render identically.

    The corpus count is the "probe a case that must be present" control, run by
    the tool. An absence from an empty corpus is the shape a wrong root takes.
    """
    populated = _layout(tmp_path / "a")
    for name in ("mc-one.md", "mc-two.md", "mc-three.md"):
        _write(populated, f".pile/{name}")
    empty = _layout(tmp_path / "b")

    from_populated = locate_artifact(populated, "mc-tbucy").artifact("pile")
    from_empty = locate_artifact(empty, "mc-tbucy").artifact("pile")

    assert from_populated.verdict == "absent"
    assert from_empty.verdict == "absent"
    assert from_populated.corpus_size == 3
    assert from_empty.corpus_size == 0


def test_ambiguity_is_not_flattened_to_present(tmp_path: Path) -> None:
    """Two slug candidates must stay `ambiguous`, never resolve by sort order.

    `_pile_artifact()` already refuses to guess here. This pins that the new
    layer does not launder that refusal into a confident answer.
    """
    layout = _layout(tmp_path)
    _write(layout, ".pile/mc-tbucy-first.md")
    _write(layout, ".pile/mc-tbucy-second.md")

    assert locate_artifact(layout, "mc-tbucy").artifact("pile").verdict == "ambiguous"


def test_slugged_deposit_resolves_present(tmp_path: Path) -> None:
    """The single-candidate slug form still resolves, per #128."""
    layout = _layout(tmp_path)
    _write(layout, ".pile/mc-tbucy-the-brief-gate.md")

    assert locate_artifact(layout, "mc-tbucy").artifact("pile").verdict == "present"


def test_decisions_toml_resolves_present(tmp_path: Path) -> None:
    """The kind that mc-tbucy was falsely reported missing."""
    layout = _layout(tmp_path)
    _write(layout, "decisions/mc-tbucy.toml", 'brief_id = "mc-tbucy"\n')

    assert locate_artifact(layout, "mc-tbucy").artifact("decisions").verdict == "present"


def test_frontmatter_artifact_id_resolves_present(tmp_path: Path) -> None:
    """A file whose bead id lives ONLY in `artifact:` frontmatter must be found.

    This is the blind spot the first cut of `locate_artifact` shipped with, and
    it is this bead's own defect reproduced inside the fix for it: the tool
    would report `absent` for an artifact that is right there under a different
    filename.

    Measured on the live mathcity pile the day this was written -- 99 files, 4
    of them addressable only by frontmatter, and NONE of the 4 findable by
    filename:

        mc-g4k2   lives in mc-cbks.md
        mc-99jj   lives in mc-j6uh.md
        mc-k4t1s  lives in mc-kjot0.md
        mc-jvqq   lives in mc-tfp4.md

    Taylor settled the convention question in OPEN-DESIGN-QUESTIONS Q5:
    *"the briefs are supposed to be decision beads so it should be however beads
    are looked-up."* Bead identity is canonical, so the id in the frontmatter IS
    the address, and a lookup that consults only filenames is reading the wrong
    key. Q5's own text says so directly: `scan_artifacts` "would fail to find
    these files even if it were pointed at the correct root."
    """
    layout = _layout(tmp_path)
    _write(
        layout,
        ".pile/19-some-slug-brief.md",
        "---\nartifact: mc-tbucy\nstatus: adjudicated\n---\n\nbody\n",
    )

    found = locate_artifact(layout, "mc-tbucy").artifact("pile")

    assert found.verdict == "present"
    assert found.path is not None and found.path.name == "19-some-slug-brief.md"


def test_two_files_claiming_one_id_in_frontmatter_are_ambiguous(tmp_path: Path) -> None:
    """The frontmatter path must not resolve a collision by sort order either.

    Without this, adding the frontmatter lookup would reintroduce exactly the
    guess that `_pile_artifact` was written to refuse -- a false `present`
    naming a specific file the tool cannot actually identify.
    """
    layout = _layout(tmp_path)
    _write(layout, ".pile/a-brief.md", "---\nartifact: mc-tbucy\n---\n")
    _write(layout, ".pile/b-brief.md", "---\nartifact: mc-tbucy\n---\n")

    assert locate_artifact(layout, "mc-tbucy").artifact("pile").verdict == "ambiguous"


def test_filename_still_wins_over_frontmatter(tmp_path: Path) -> None:
    """Control: the cheap exact match must not be displaced by the scan.

    An unambiguous deposit is never reinterpreted, and the frontmatter scan is
    a fallback rather than a competing rule.
    """
    layout = _layout(tmp_path)
    _write(layout, ".pile/mc-tbucy.md", "---\nartifact: mc-tbucy\n---\n")
    _write(layout, ".pile/decoy-brief.md", "---\nartifact: mc-tbucy\n---\n")

    found = locate_artifact(layout, "mc-tbucy").artifact("pile")

    assert found.verdict == "present"
    assert found.path is not None and found.path.name == "mc-tbucy.md"


def test_every_answer_names_the_root_it_searched(tmp_path: Path) -> None:
    """The provenance that makes a wrong-root answer visible on sight."""
    layout = _layout(tmp_path)

    found = locate_artifact(layout, "mc-tbucy")

    assert found.resolved_root == layout.root
    assert str(layout.root) == found.to_dict()["resolved_root"]
