"""#234: a stack index row can state the brief's OWN decision bead, typed.

THE DEFECT
----------
`stack/.index.jsonl` rows carried no reference to the brief's canonical
decision bead. `brief-stack-index.py::new_row` emitted `path`, `slug`,
`gate_profile`, `source` and `created_at` -- and `source` is fed from
`("source_bead", "artifact")`, the brief's *subject* bead, never `brief_bead`,
the brief's *own* decision bead. So "does this stack brief have a bead, and
which one?" was unanswerable from the index. The absence was silent, so a
reader could not tell "declares no bead" from "the schema has no such field",
and both rendered as nothing -- the misread that produced the phantom "62
beadless briefs, MBRF010 blocks adjudication" claim.

THE FIX (issue candidate A, three-valued)
------------------------------------------
`new_row` now reads `brief_bead` and emits it typed:

    present in frontmatter          -> "brief_bead": "<id>"
    file DECLARES no bead subject   -> "brief_bead": null   (B2.1a, explicit)
    file is silent                  -> the key is omitted

and the two consumers that join a bead to its stack row -- the adjudication
write path (`effects._update_stack_index`/`_row_targets_brief`) and the read
path (`redundant_state.scan_artifacts`) -- consult `brief_bead`, so a
bead-backed brief whose `slug`/`source`/`path` all name something else still
finds its own row. That join failure is what returned
`MCTL_STACK_INDEX_ROW_ABSENT` on a live revise batch.

HOW THESE TESTS COULD FAIL (P6.2)
---------------------------------
Every assertion below was OBSERVED failing against the pre-fix tree:

  * producer, present  -- new_row never read `brief_bead`; the key was absent.
  * producer, null     -- no declaration path existed; the key was absent.
  * producer, silent   -- control; passes before and after (guards against a
                          fix that invents `brief_bead` unconditionally).
  * producer, subject  -- control; `source_bead` still lands in `source`, NOT
                          in `brief_bead` (the two answer different questions;
                          a fix that conflated them would fail this).
  * write-join         -- `_row_targets_brief` did not consult `brief_bead`, so
                          a row named by slug/source alone raised
                          StackIndexRowUnwritable for its own bead.
  * read-join          -- `_row_id` did not consult `brief_bead`, so the
                          stack_index artifact read `missing` for a present row.

The read path is a READ surface (POLICY P7.1): nothing here writes a bead, and
`new_row` writes only the index cache it already owned.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

INDEX_TOOL = SCRIPTS_ROOT / "brief-stack-index.py"

from mctl_core import effects  # noqa: E402
from mctl_core.redundant_state import ArtifactLayout, scan_artifacts  # noqa: E402


# --- the producer: new_row emits a typed, three-valued brief_bead ------------


def _brief_root(tmp_path: Path) -> Path:
    root = tmp_path / ".beads" / "briefs"
    (root / "stack").mkdir(parents=True)
    (root / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    return root


def _write(stack: Path, name: str, text: str) -> Path:
    path = stack / name
    path.write_text(text, encoding="utf-8")
    return path


def _add_missing_rows(brief_root: Path) -> list[dict]:
    result = subprocess.run(
        [sys.executable, str(INDEX_TOOL), "add-missing-rows",
         "--brief-root", str(brief_root), "--apply"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stderr
    index = brief_root / "stack" / ".index.jsonl"
    return [json.loads(line) for line in index.read_text().splitlines() if line.strip()]


def _row_for(rows: list[dict], slug: str) -> dict:
    return next(row for row in rows if row["slug"] == slug)


def test_a_declared_brief_bead_is_carried_onto_the_row(tmp_path: Path) -> None:
    """The whole point: the row can name the brief's own decision bead."""
    stack = _brief_root(tmp_path) / "stack"
    _write(stack, "62-typed-brief.md",
           "---\nbrief_bead: mc-dec42\nsource_bead: mc-subject\n---\nbody\n")

    row = _row_for(_add_missing_rows(stack.parent), "62-typed-brief")

    assert row["brief_bead"] == "mc-dec42"


def test_a_declared_absence_is_null_and_distinguishable_from_silence(tmp_path: Path) -> None:
    """B2.1a: an EXPLICIT no-subject declaration reports `null`, not nothing.

    `null` says "the brief declared it has no bead"; an ABSENT key says "the
    brief did not declare one". Collapsing the two is the misread this fix
    exists to end, so the two files below must produce different rows.
    """
    stack = _brief_root(tmp_path) / "stack"
    _write(stack, "01-standing-rule-brief.md",
           "---\ntitle: Should we do X at all\n---\n"
           "## What is being decided\n\nSource: none\n")
    _write(stack, "02-silent-brief.md", "---\nstatus: ready\n---\nbody\n")

    rows = _add_missing_rows(stack.parent)

    declared = _row_for(rows, "01-standing-rule-brief")
    silent = _row_for(rows, "02-silent-brief")
    assert "brief_bead" in declared and declared["brief_bead"] is None
    assert "brief_bead" not in silent


def test_a_no_subject_title_tag_also_declares_absence(tmp_path: Path) -> None:
    """The `[no-subject]` title tag is a B2.1a marker too, not only the body line."""
    stack = _brief_root(tmp_path) / "stack"
    _write(stack, "03-policy-brief.md",
           "---\ntitle: '[no-subject] Retire the old lane'\n---\nbody\n")

    row = _row_for(_add_missing_rows(stack.parent), "03-policy-brief")

    assert "brief_bead" in row and row["brief_bead"] is None


def test_a_silent_brief_omits_the_key_rather_than_inventing_one(tmp_path: Path) -> None:
    """Control. Absent means absent; a fix that always writes the key fails here."""
    stack = _brief_root(tmp_path) / "stack"
    _write(stack, "04-plain-brief.md", "---\nstatus: ready\ngate_profile: standard\n---\nbody\n")

    row = _row_for(_add_missing_rows(stack.parent), "04-plain-brief")

    assert "brief_bead" not in row


def test_the_subject_bead_still_lands_in_source_not_in_brief_bead(tmp_path: Path) -> None:
    """Control against conflation: `source` and `brief_bead` answer DIFFERENT
    questions -- the subject bead vs the brief's own decision bead. A file that
    names only its subject must NOT get a `brief_bead`, and its subject must
    still reach `source`.
    """
    stack = _brief_root(tmp_path) / "stack"
    _write(stack, "05-subject-only-brief.md", "---\nsource_bead: mc-subject\n---\nbody\n")

    row = _row_for(_add_missing_rows(stack.parent), "05-subject-only-brief")

    assert row["source"] == "mc-subject"
    assert "brief_bead" not in row


# --- the write-path join: adjudication finds the row by brief_bead -----------


def _index(tmp_path: Path, rows: list[dict]) -> Path:
    path = tmp_path / ".index.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return path


def test_adjudication_updates_the_row_matched_only_by_brief_bead(tmp_path: Path) -> None:
    """A bead-backed brief whose slug and source name OTHER things still finds
    its own row. Before the fix `_row_targets_brief` had no `brief_bead` key, so
    this row went unmatched and adjudication raised StackIndexRowUnwritable --
    the `MCTL_STACK_INDEX_ROW_ABSENT` the live revise batch hit.
    """
    path = _index(tmp_path, [{
        "slug": "62-typed-brief",
        "source": "mc-subject",
        "path": ".beads/briefs/stack/62-typed-brief.md",
        "brief_bead": "mc-dec42",
        "status": "ready",
    }])

    effects._update_stack_index(path, "mc-dec42", {"status": "adjudicated"})

    row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    assert row["status"] == "adjudicated"


def test_a_null_brief_bead_row_is_not_matched_by_a_real_bead_id(tmp_path: Path) -> None:
    """A row that DECLARES no bead (`brief_bead: null`) must not be pulled onto
    some other brief's adjudication. Null is inert, not a wildcard.
    """
    path = _index(tmp_path, [{"slug": "01-standing-rule", "brief_bead": None, "status": "ready"}])

    with pytest.raises(effects.StackIndexRowUnwritable):
        effects._update_stack_index(path, "mc-dec42", {"status": "adjudicated"})


# --- the read-path join: the redundant-state scan finds the row --------------


def _layout(tmp_path: Path, rows: list[dict]) -> ArtifactLayout:
    root = tmp_path / "briefs"
    for sub in ("", ".pile", "stack", "decisions"):
        (root / sub).mkdir(parents=True, exist_ok=True)
    (root / "stack" / ".index.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8"
    )
    return ArtifactLayout(
        root=root,
        pile=root / ".pile",
        stack=root / "stack",
        stack_index=root / "stack" / ".index.jsonl",
        decisions=root / "decisions",
        legacy_manifest=root / "manifest.jsonl",
    )


def test_the_stack_artifact_resolves_by_brief_bead_not_only_slug(tmp_path: Path) -> None:
    """`scan_artifacts(brief_id=<bead>)` must find a row whose slug is the
    filename stem and whose `brief_bead` is that bead. Before the fix `_row_id`
    never read `brief_bead`, so the row read `missing` for its own bead.
    """
    layout = _layout(tmp_path, [{
        "slug": "62-typed-brief",
        "source": "mc-subject",
        "path": str(tmp_path / "briefs" / "stack" / "62-typed-brief.md"),
        "brief_bead": "mc-dec42",
    }])
    (layout.stack / "62-typed-brief.md").write_text("---\nstatus: ready\n---\nbody\n", encoding="utf-8")

    artifacts = scan_artifacts(layout, "mc-dec42", "pending")
    stack_artifact = next(a for a in artifacts if a.kind == "stack_index")

    assert stack_artifact.state == "present", (
        f"a row carrying brief_bead=mc-dec42 must resolve for that bead; "
        f"got state={stack_artifact.state!r}"
    )


def test_a_bead_with_no_row_at_all_still_reads_missing(tmp_path: Path) -> None:
    """The inverse. A fix that always says `present` is the defect inverted."""
    layout = _layout(tmp_path, [{"slug": "other", "brief_bead": "mc-other"}])

    artifacts = scan_artifacts(layout, "mc-dec42", "pending")
    stack_artifact = next(a for a in artifacts if a.kind == "stack_index")

    assert stack_artifact.state == "missing"
