"""`remove-archived-row` must verify the archive it names.

The defect: the subcommand computed `archive_hit` and never tested it. The row
was removed unconditionally and the report recorded
`reason: "explicit_slug_archived_row"` with `archived_at: ""` -- a name and a
reason that both assert an archive nothing looked for.

Why it is on the dogfood path: `formulas/brief-record-decision.toml:206-213`
runs this as the LAST step of adjudication, after prose that says "after the
archive move succeeds". That ordering is an instruction to an agent, not an
enforced sequence. If the archive move is skipped or fails, the row is removed
anyway, the brief stays in `stack/` as a stray, and Taylor's verdict leaves the
four representations disagreeing -- which is exactly what dogfood must not do.

Live evidence at the time of the fix: the 35 rows drained from the city index
were 35/35 archived, so this is latent, not observed corruption.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_TOOL = REPO_ROOT / "assets" / "scripts" / "brief-stack-index.py"


def run_index_tool(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(INDEX_TOOL), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def read_rows(index: Path) -> list[dict]:
    return [json.loads(l) for l in index.read_text().splitlines() if l.strip()]


@pytest.fixture
def brief_root(tmp_path: Path) -> Path:
    root = tmp_path / ".beads" / "briefs"
    (root / "stack").mkdir(parents=True)
    return root


def seed(root: Path, slug: str, *, archived: bool) -> Path:
    stack = root / "stack"
    (stack / f"{slug}.md").write_text("---\nstatus: adjudicated\n---\nbody\n")
    (stack / ".index.jsonl").write_text(
        json.dumps({"slug": slug, "path": f"stack/{slug}.md", "status": "ready"}) + "\n"
    )
    if archived:
        archive = root / ".adjudicated-archive"
        archive.mkdir(parents=True, exist_ok=True)
        (archive / f"{slug}.md").write_text("---\nstatus: adjudicated\n---\nbody\n")
    return stack / ".index.jsonl"


def test_row_is_kept_when_no_archive_exists(brief_root: Path) -> None:
    index = seed(brief_root, "not-archived", archived=False)

    result = run_index_tool(
        "remove-archived-row", "--brief-root", str(brief_root),
        "--slug", "not-archived", "--apply",
    )

    assert result.returncode != 0, "removing an unarchived row must fail loudly"
    assert [r["slug"] for r in read_rows(index)] == ["not-archived"]


def test_refusal_is_reported_and_names_the_slug(brief_root: Path) -> None:
    seed(brief_root, "not-archived", archived=False)

    result = run_index_tool(
        "remove-archived-row", "--brief-root", str(brief_root),
        "--slug", "not-archived", "--apply",
    )
    report = json.loads(result.stdout)

    assert report["removed"] == []
    assert [r["slug"] for r in report["refused"]] == ["not-archived"]
    assert "archive" in report["refused"][0]["reason"]


def test_an_archived_row_is_still_removed(brief_root: Path) -> None:
    # The guard must not break the path the formula actually depends on.
    index = seed(brief_root, "properly-archived", archived=True)

    result = run_index_tool(
        "remove-archived-row", "--brief-root", str(brief_root),
        "--slug", "properly-archived", "--apply",
    )

    assert result.returncode == 0, result.stderr
    assert read_rows(index) == []
    report = json.loads(result.stdout)
    assert report["removed"][0]["slug"] == "properly-archived"
    assert report["removed"][0]["archived_at"], "archived_at must name the file it verified"


def test_dry_run_refuses_without_writing(brief_root: Path) -> None:
    index = seed(brief_root, "not-archived", archived=False)

    result = run_index_tool(
        "remove-archived-row", "--brief-root", str(brief_root), "--slug", "not-archived",
    )

    assert result.returncode != 0
    assert [r["slug"] for r in read_rows(index)] == ["not-archived"]
