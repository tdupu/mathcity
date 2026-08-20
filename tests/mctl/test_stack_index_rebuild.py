"""`.index.jsonl` gets a rebuild path, and it emits exactly one serialization.

The defect (clerk sweep B2): `stack/` held 89 markdown files against 88 index
rows, and both existing subcommands -- `reconcile-archive` and
`remove-archived-row` -- only REMOVE. A file that never got a row could never
acquire one. `gh-38-decisions-track-classifier-verify-close-brief.md` was the
live orphan.

The constraint that shapes the fix: the live index already holds three
incompatible path serializations across those 88 rows -- 45
`.beads/briefs/stack/x.md`, 40 absolute, 3 bare `stack/x.md`. Three producers
disagree; `add-missing-rows` must not become the fourth. It emits the 45-row
plurality form and nothing else, and appends rather than re-serializing, so it
cannot repeat the whole-file rewrite that mangled 38 rows (pile brief 22).

Fixture numbers are built in the test. The live index is checked by shape, not
by frozen count, because other agents write to it.
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
    return [
        json.loads(line)
        for line in index.read_text().splitlines()
        if line.strip()
    ]


def write_brief(stack: Path, name: str, frontmatter: str = "status: present-it-pending") -> Path:
    path = stack / name
    path.write_text(f"---\n{frontmatter}\n---\nbody\n")
    return path


@pytest.fixture
def brief_root(tmp_path: Path) -> Path:
    # Mirrors the live layout: <root>/.beads/briefs/stack/, so the emitted path
    # is the `.beads/...` form rather than the fixture-only fallback.
    root = tmp_path / ".beads" / "briefs"
    (root / "stack").mkdir(parents=True)
    (root / "stack" / ".index.jsonl").write_text("")
    return root


def test_a_stack_file_with_no_index_row_can_be_repaired(brief_root: Path) -> None:
    write_brief(brief_root / "stack", "01-orphan-brief.md")

    result = run_index_tool("add-missing-rows", "--brief-root", str(brief_root), "--apply")

    assert result.returncode == 0, result.stderr
    rows = read_rows(brief_root / "stack" / ".index.jsonl")
    assert len(rows) == 1
    assert Path(rows[0]["path"]).name == "01-orphan-brief.md"


def test_dry_run_is_the_default_and_writes_nothing(brief_root: Path) -> None:
    """The index is the human presentation queue; --apply is opt-in."""
    write_brief(brief_root / "stack", "01-orphan-brief.md")
    index = brief_root / "stack" / ".index.jsonl"

    result = run_index_tool("add-missing-rows", "--brief-root", str(brief_root))

    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report["apply"] is False
    assert report["added_count"] == 1
    assert index.read_text() == ""


def test_added_rows_use_one_serialization(brief_root: Path) -> None:
    """Brief 22: `.index.jsonl` already has three producers. Not a fourth.

    Every row this command emits uses the `.beads/...` root-relative form --
    never absolute, never bare `stack/...` -- regardless of what the rows
    already in the file look like.
    """
    stack = brief_root / "stack"
    # Seed the file with the two rival serializations, so a naive "match the
    # neighbours" implementation would be caught rather than rewarded.
    (stack / ".index.jsonl").write_text(
        json.dumps({"path": str(stack / "already-absolute.md"), "slug": "already-absolute"})
        + "\n"
        + json.dumps({"path": "stack/already-bare.md", "slug": "already-bare"})
        + "\n"
    )
    write_brief(stack, "already-absolute.md")
    write_brief(stack, "already-bare.md")
    for name in ("new-a-brief.md", "new-b-brief.md", "new-c-brief.md"):
        write_brief(stack, name)

    result = run_index_tool("add-missing-rows", "--brief-root", str(brief_root), "--apply")
    assert result.returncode == 0, result.stderr

    rows = read_rows(stack / ".index.jsonl")
    added = [row for row in rows if row["slug"].startswith("new-")]
    assert len(added) == 3
    for row in added:
        assert row["path"].startswith(".beads/briefs/stack/"), row
        assert not Path(row["path"]).is_absolute()

    # The two pre-existing rows keep their own serializations byte-for-byte.
    raw = (stack / ".index.jsonl").read_text().splitlines()
    assert raw[0] == json.dumps(
        {"path": str(stack / "already-absolute.md"), "slug": "already-absolute"}
    )
    assert raw[1] == json.dumps({"path": "stack/already-bare.md", "slug": "already-bare"})


def test_existing_rows_are_never_reserialized(brief_root: Path) -> None:
    """Splice, don't re-serialize -- the rule pile brief 22 recommends.

    A whole-file rewrite is the operation that split the index in the first
    place. An indented, unsorted, non-compact row must survive untouched.
    """
    stack = brief_root / "stack"
    ugly = '{"slug": "ugly", "path": ".beads/briefs/stack/ugly.md",  "unlock_count": 7}'
    (stack / ".index.jsonl").write_text(ugly + "\n")
    write_brief(stack, "ugly.md")
    write_brief(stack, "fresh-brief.md")

    run_index_tool("add-missing-rows", "--brief-root", str(brief_root), "--apply")

    assert (stack / ".index.jsonl").read_text().splitlines()[0] == ugly


def test_malformed_rows_survive_and_are_reported(brief_root: Path) -> None:
    """A line that will not parse is kept, not dropped. It is somebody's data."""
    stack = brief_root / "stack"
    (stack / ".index.jsonl").write_text("{not json at all\n")
    write_brief(stack, "fresh-brief.md")

    result = run_index_tool("add-missing-rows", "--brief-root", str(brief_root), "--apply")

    report = json.loads(result.stdout)
    assert report["malformed_kept_count"] == 1
    lines = (stack / ".index.jsonl").read_text().splitlines()
    assert lines[0] == "{not json at all"
    assert len(lines) == 2


def test_the_command_is_idempotent(brief_root: Path) -> None:
    write_brief(brief_root / "stack", "01-orphan-brief.md")
    index = brief_root / "stack" / ".index.jsonl"

    run_index_tool("add-missing-rows", "--brief-root", str(brief_root), "--apply")
    first = index.read_text()
    result = run_index_tool("add-missing-rows", "--brief-root", str(brief_root), "--apply")

    assert json.loads(result.stdout)["added_count"] == 0
    assert index.read_text() == first


def test_a_row_matched_by_basename_across_serializations(brief_root: Path) -> None:
    """An absolute-path row already covers its file. Do not add a duplicate."""
    stack = brief_root / "stack"
    write_brief(stack, "covered-brief.md")
    (stack / ".index.jsonl").write_text(
        json.dumps({"path": str(stack / "covered-brief.md"), "slug": "covered-brief"}) + "\n"
    )

    result = run_index_tool("add-missing-rows", "--brief-root", str(brief_root))

    assert json.loads(result.stdout)["added_count"] == 0


def test_absent_fields_are_omitted_not_invented(brief_root: Path) -> None:
    """Absent means absent.

    `unlock_count` is a graph measurement this script cannot take, and
    manifest.py is explicit that it is read, never derived. A row asserting 0
    would be a measurement claim, not a repair. Consumers already tolerate the
    gap: `brief-drain-manifest.sh` reads `(.unlock_count // 0)`.
    """
    write_brief(brief_root / "stack", "bare-brief.md", frontmatter="status: present-it-pending")

    result = run_index_tool("add-missing-rows", "--brief-root", str(brief_root))

    row = json.loads(result.stdout)["added"][0]
    assert "unlock_count" not in row
    assert "gate_profile" not in row
    assert "source" not in row
    assert "created_at" not in row
    assert set(row) == {"path", "slug"}


def test_declared_fields_are_carried_verbatim(brief_root: Path) -> None:
    write_brief(
        brief_root / "stack",
        "declared-brief.md",
        frontmatter=(
            "gate_profile: decision\n"
            "artifact: gh-issue-38\n"
            "deposited_at: 2026-08-19T10:40:00-04:00"
        ),
    )

    result = run_index_tool("add-missing-rows", "--brief-root", str(brief_root))

    row = json.loads(result.stdout)["added"][0]
    assert row["gate_profile"] == "decision"
    assert row["source"] == "gh-issue-38"
    assert row["created_at"] == "2026-08-19T10:40:00-04:00"


def test_source_bead_outranks_artifact(brief_root: Path) -> None:
    write_brief(
        brief_root / "stack",
        "both-brief.md",
        frontmatter="source_bead: mc-x6a\nartifact: gh-issue-38",
    )

    result = run_index_tool("add-missing-rows", "--brief-root", str(brief_root))

    assert json.loads(result.stdout)["added"][0]["source"] == "mc-x6a"


def test_slug_keeps_the_brief_suffix(brief_root: Path) -> None:
    """46 of the 88 live rows keep `-brief` in `slug`. Stripping it unjoins them.

    Pinned to the artefact that exposed the unanchored-strip defect: a
    `.replace('-brief', '')` would maul this name in the middle, not just at
    the end.
    """
    write_brief(brief_root / "stack", "257-decision-brief-gate-profile-brief.md")

    result = run_index_tool("add-missing-rows", "--brief-root", str(brief_root))

    row = json.loads(result.stdout)["added"][0]
    assert row["slug"] == "257-decision-brief-gate-profile-brief"


def test_frontmatter_value_a_yaml_loader_would_reject(brief_root: Path) -> None:
    """Live briefs carry unquoted values a strict parse rejects outright.

    Losing one key is acceptable; dropping the brief is not.
    """
    write_brief(
        brief_root / "stack",
        "gnarly-brief.md",
        frontmatter="status: needs-revision(a:b;c)\ngate_profile: standard",
    )

    result = run_index_tool("add-missing-rows", "--brief-root", str(brief_root))

    row = json.loads(result.stdout)["added"][0]
    assert row["gate_profile"] == "standard"


def test_a_file_with_no_frontmatter_still_gets_a_row(brief_root: Path) -> None:
    (brief_root / "stack" / "plain-brief.md").write_text("no frontmatter here\n")

    result = run_index_tool("add-missing-rows", "--brief-root", str(brief_root), "--apply")

    rows = read_rows(brief_root / "stack" / ".index.jsonl")
    assert len(rows) == 1
    assert rows[0]["slug"] == "plain-brief"


def test_emitted_rows_are_compact_and_key_sorted(brief_root: Path) -> None:
    """86 of the 88 live rows are compact; the sample rows are key-sorted."""
    write_brief(brief_root / "stack", "z-brief.md", frontmatter="gate_profile: standard")

    run_index_tool("add-missing-rows", "--brief-root", str(brief_root), "--apply")

    line = (brief_root / "stack" / ".index.jsonl").read_text().splitlines()[0]
    assert ", " not in line
    assert line == json.dumps(json.loads(line), sort_keys=True, separators=(",", ":"))
