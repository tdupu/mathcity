"""`brief-stack-index.py check` -- a divergence check that CAN fail.

The gap this closes: `add-missing-rows` reports index/disk divergence but
always returns 0, so nothing could gate on it. mathcity POLICY P6.2 -- a check
that could not have failed must not render as a check that passed.

The measurement error this encodes against: the live index holds the SAME file
spelled three ways (`.beads/briefs/stack/x.md`, absolute, and bare
`stack/x.md`). Comparing raw `path` strings against one base makes rows in the
other two forms read as phantom. That is how a live 1-file gap (93 files, 92
rows) was once reported as "40 phantom rows, 41 orphan files, ~44% divergence".
So `check` matches on BASENAME and reports serialization counts separately --
heterogeneity is a writer-consistency defect, never counted as a missing brief.

Every fixture is built here in tmp_path. The live pile is never touched.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_TOOL = REPO_ROOT / "assets" / "scripts" / "brief-stack-index.py"


def run_check(brief_root: Path) -> tuple[int, dict]:
    proc = subprocess.run(
        [sys.executable, str(INDEX_TOOL), "check", "--brief-root", str(brief_root)],
        capture_output=True,
        text=True,
        check=False,
    )
    payload = json.loads(proc.stdout) if proc.stdout.strip() else {}
    return proc.returncode, payload


@pytest.fixture
def brief_root(tmp_path: Path) -> Path:
    # Mirrors the live layout <root>/.beads/briefs/stack/ so serialization
    # classification sees the same shapes the real index holds.
    root = tmp_path / ".beads" / "briefs"
    (root / "stack").mkdir(parents=True)
    return root


def write_brief(brief_root: Path, name: str) -> None:
    (brief_root / "stack" / name).write_text(
        "---\nstatus: present-it-pending\n---\nbody\n"
    )


def write_index(brief_root: Path, paths: list[str]) -> None:
    (brief_root / "stack" / ".index.jsonl").write_text(
        "".join(
            json.dumps({"slug": Path(p).name[:-3], "path": p}) + "\n" for p in paths
        )
    )


def test_clean_stack_passes(brief_root: Path) -> None:
    write_brief(brief_root, "a-brief.md")
    write_brief(brief_root, "b-brief.md")
    write_index(brief_root, [".beads/briefs/stack/a-brief.md", "stack/b-brief.md"])

    code, report = run_check(brief_root)

    assert code == 0
    assert report["ok"] is True
    assert report["divergence_count"] == 0


def test_orphan_file_fails(brief_root: Path) -> None:
    """The live shape: a file on disk that no row mentions. Must be nonzero."""
    write_brief(brief_root, "a-brief.md")
    write_brief(brief_root, "orphan-brief.md")
    write_index(brief_root, [".beads/briefs/stack/a-brief.md"])

    code, report = run_check(brief_root)

    assert code == 1
    assert report["ok"] is False
    assert report["orphan_files"] == ["orphan-brief.md"]
    assert report["phantom_row_count"] == 0


def test_phantom_row_fails(brief_root: Path) -> None:
    write_brief(brief_root, "a-brief.md")
    write_index(
        brief_root,
        [".beads/briefs/stack/a-brief.md", ".beads/briefs/stack/gone-brief.md"],
    )

    code, report = run_check(brief_root)

    assert code == 1
    assert report["phantom_rows"] == ["gone-brief.md"]


def test_duplicate_row_fails(brief_root: Path) -> None:
    """Two rows for one file -- what a naive repair tool produces first."""
    write_brief(brief_root, "a-brief.md")
    write_index(
        brief_root, [".beads/briefs/stack/a-brief.md", "stack/a-brief.md"]
    )

    code, report = run_check(brief_root)

    assert code == 1
    assert report["duplicate_basenames"] == ["a-brief.md"]


def test_malformed_index_is_exit_2_not_divergence(brief_root: Path) -> None:
    """A broken index is a different failure from a diverged one."""
    write_brief(brief_root, "a-brief.md")
    (brief_root / "stack" / ".index.jsonl").write_text(
        json.dumps({"slug": "a-brief", "path": "stack/a-brief.md"}) + "\n{ not json\n"
    )

    code, report = run_check(brief_root)

    assert code == 2
    assert report["malformed_row_numbers"]


def test_three_serializations_of_existing_files_is_not_divergence(
    brief_root: Path,
) -> None:
    """THE REGRESSION GUARD for the false 44% figure.

    Three spellings, three real files, zero missing briefs. A checker that
    resolved `path` against one base would score two of these three as phantom
    AND their files as orphans -- inflating one clean stack into 4 findings.
    """
    for name in ("a-brief.md", "b-brief.md", "c-brief.md"):
        write_brief(brief_root, name)
    write_index(
        brief_root,
        [
            ".beads/briefs/stack/a-brief.md",
            str(brief_root / "stack" / "b-brief.md"),  # absolute
            "stack/c-brief.md",
        ],
    )

    code, report = run_check(brief_root)

    assert code == 0, report
    assert report["divergence_count"] == 0
    assert report["serialization_form_count"] == 3
    assert report["path_serializations"] == {
        "city-relative": 1,
        "absolute": 1,
        "briefs-relative": 1,
    }


def test_missing_stack_dir_is_exit_2(tmp_path: Path) -> None:
    code, report = run_check(tmp_path / "nope")

    assert code == 2
    assert report["error"] == "stack-dir-missing"


def test_check_is_single_root_and_ignores_a_sibling_root(tmp_path: Path) -> None:
    """Cross-root scanning is the failure mode that manufactures divergence.

    Q5 (RESOLVED 2026-08-19) makes storage per-rig, so two populated brief roots
    coexist: a city root and a rig root. A scan that took the index from one and
    the files from the other would report a large, plausible, entirely fictional
    divergence. `check` globs `<brief-root>/stack/*.md` against
    `<brief-root>/stack/.index.jsonl` and never leaves the root it was given.
    """
    city = tmp_path / "city" / ".beads" / "briefs"
    rig = tmp_path / "city" / "rig" / ".beads" / "briefs"
    for root in (city, rig):
        (root / "stack").mkdir(parents=True)

    # Each root is internally consistent, with disjoint contents.
    write_brief(city, "city-brief.md")
    write_index(city, [".beads/briefs/stack/city-brief.md"])
    for name in ("rig-a-brief.md", "rig-b-brief.md"):
        write_brief(rig, name)
    write_index(rig, ["stack/rig-a-brief.md", "stack/rig-b-brief.md"])

    # Both pass on their own terms; neither sees the other's files or rows.
    city_code, city_report = run_check(city)
    rig_code, rig_report = run_check(rig)

    assert (city_code, rig_code) == (0, 0)
    assert city_report["stack_file_count"] == 1
    assert city_report["index_row_count"] == 1
    assert rig_report["stack_file_count"] == 2
    assert rig_report["index_row_count"] == 2
