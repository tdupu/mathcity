"""The brief stack as a population, and the dedup rule that was aimed backwards.

`manifest.py` used to open the stack directory for exactly one purpose: to
decide which decisions-track rows to throw away. 46 of 204 rows were suppressed
because a stack file "already represents" them.

Measured against the live city 2026-08-20, nothing read stack files as records:

- 0 of the 46 suppressed slugs appeared in `mctl briefs list --all-rigs`.
- 0 stack filename stems appeared as a `brief_id` anywhere.
- 2 of the 89 stack files were reachable at all, both through
  `briefs._cached_brief_document`, which keys on a **bead id**.

So the suppression removed the only record of 46 briefs, and with the 43 stack
files that carry no manifest row, 87 of 89 stack documents reached no surface.

These tests pin the two halves of the fix: the manifest join (in
`test_manifest_source.py`) and this population. Counts here come from fixtures.
The live corpus is checked for invariants only, at the end -- during the
session that wrote this module the stack drained from 89 files to 54, taking
the joined count from 46 to 38, and a frozen live number is a test that fails
for being right.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.manifest import (  # noqa: E402
    STATE_ADJUDICATED,
    STATE_PENDING,
    manifest_records,
)
from mctl_core.stack import (  # noqa: E402
    CANONICAL_SOURCE_STACK,
    SOURCE_STACK,
    stack_records,
)
from mctl_core.verdicts import CONFIDENCE_HIGH, SOURCE_BRIEF_FRONTMATTER  # noqa: E402

MCTL = SCRIPTS_ROOT / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"

LIVE_STACK = Path.home() / "gt" / ".beads" / "briefs" / "stack"
LIVE_MANIFEST = Path.home() / "gt" / ".beads" / "decisions-track" / "manifest.jsonl"

ADJUDICATED = """---
status: adjudicated
verdict: approve
priority: P1
unlock_count: 4
adjudicated_at: 2026-07-02T09:00:00Z
---

## §1 What is being decided

Whether the thing is done.
"""

PENDING = """---
status: ready
form: full
track: brief-system
deposited_at: 2026-07-01T09:00:00Z
---

## §1 What is being decided

Body text, so the file is not unreadable.
"""


def stack_with(directory: Path, files: dict[str, str]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for name, body in files.items():
        (directory / name).write_text(body, encoding="utf-8")
    return directory


def write_manifest(path: Path, rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{json.dumps(row, sort_keys=True)}\n" for row in rows), encoding="utf-8"
    )
    return path


def runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return city_root, rig_root


def run_mctl(city_root: Path, rig_root: Path, *args: str) -> dict[str, object]:
    env = os.environ.copy()
    env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
    result = subprocess.run(
        [sys.executable, str(MCTL), *args, "--city", str(city_root), "--rig", "mathcity"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


# --- the population ----------------------------------------------------------


def test_a_stack_file_nothing_claims_becomes_a_record(tmp_path: Path):
    """41 live files were in this state: deposited, adjudicated, unreadable by anything."""
    stack = stack_with(
        tmp_path / "stack",
        {"31-verdict-in-the-stack-brief.md": ADJUDICATED},
    )

    reading = stack_records(stack)

    assert reading.files_read == 1
    record = reading.records[0]
    assert record.slug == "verdict-in-the-stack"
    assert record.source == SOURCE_STACK
    assert record.decision_state == STATE_ADJUDICATED
    assert record.verdict is not None
    assert record.verdict.text == "approve"
    # The verdict says which document attested it and how far that goes. No
    # bead and no manifest row agrees, because neither has ever seen this file.
    assert record.verdict.source == SOURCE_BRIEF_FRONTMATTER
    assert record.verdict.confidence == CONFIDENCE_HIGH
    assert record.verdict.field == "stack.frontmatter.verdict"


def test_a_stack_file_with_no_verdict_is_pending_not_invisible(tmp_path: Path):
    stack = stack_with(tmp_path / "stack", {"08-still-waiting-brief.md": PENDING})

    record = stack_records(stack).records[0]

    assert record.decision_state == STATE_PENDING
    assert record.body == PENDING
    assert record.status == "ready"
    assert record.track == "brief-system"


def test_fields_declare_the_stack_lane_and_not_the_manifest_one(tmp_path: Path):
    """A stack frontmatter key and a decisions-track one are different claims.

    Rendering both as `frontmatter` would put two answers on screen under one
    label -- the flattening `fields.py` exists to prevent.
    """
    stack = stack_with(tmp_path / "stack", {"31-verdict-in-the-stack-brief.md": ADJUDICATED})

    record = stack_records(stack).records[0]

    by_name = {reading.name: reading for reading in record.fields}
    assert by_name["priority"].source == "stack_frontmatter"
    assert by_name["priority"].readings[0].field == "stack.frontmatter.priority"
    # `unlock_count` is read, never derived -- the number was written by
    # whoever knew what the brief unblocked.
    assert by_name["unlock_count"].value == "4"


def test_a_date_is_read_from_the_document_and_never_from_the_filesystem(tmp_path: Path):
    """A file mtime rendered as an Age is a date the brief never recorded."""
    stack = stack_with(
        tmp_path / "stack",
        {"31-dated-brief.md": ADJUDICATED, "32-undated-brief.md": "# no frontmatter\n"},
    )

    records = {record.slug: record for record in stack_records(stack).records}

    assert records["dated"].timestamp == "2026-07-02T09:00:00Z"
    assert records["dated"].timestamp_field == "adjudicated_at"
    assert records["undated"].timestamp is None
    assert records["undated"].timestamp_field is None


def test_only_md_counts_so_a_backup_never_becomes_a_brief(tmp_path: Path):
    """The stack also holds `.index.jsonl`, `.bak-*` snapshots and `*.md.bak*`."""
    stack = stack_with(
        tmp_path / "stack",
        {
            "08-real-brief.md": PENDING,
            "08-real-brief.md.bak": PENDING,
            ".index.jsonl": "{}\n",
        },
    )

    reading = stack_records(stack)

    assert [record.slug for record in reading.records] == ["real"]


def test_a_missing_stack_directory_is_silent_rather_than_an_error(tmp_path: Path):
    reading = stack_records(tmp_path / "absent")

    assert reading.records == ()
    assert reading.files_read == 0
    assert reading.issues == ()


def test_reading_the_stack_writes_nothing(tmp_path: Path):
    stack = stack_with(tmp_path / "stack", {"08-still-waiting-brief.md": PENDING})
    before = {path: path.read_bytes() for path in sorted(stack.iterdir())}

    stack_records(stack)

    assert {path: path.read_bytes() for path in sorted(stack.iterdir())} == before


# --- dedup, by what the other readers actually opened -------------------------


def test_a_file_a_manifest_row_joined_is_not_emitted_a_second_time(tmp_path: Path):
    """The one double-count that would be real, and the only one this excludes."""
    stack = stack_with(
        tmp_path / "stack",
        {"08-tracked-brief.md": PENDING, "09-untracked-brief.md": PENDING},
    )
    manifest = write_manifest(
        tmp_path / "decisions-track" / "manifest.jsonl", [{"slug": "tracked"}]
    )
    manifest_reading = manifest_records(manifest, stack)

    reading = stack_records(stack, claimed=manifest_reading.stack_paths)

    assert [record.slug for record in reading.records] == ["untracked"]
    assert reading.claimed == (stack / "08-tracked-brief.md",)
    # The arithmetic, stated rather than assumed: every file is either claimed
    # by another reader or emitted here, and none is both or neither.
    assert len(reading.records) + len(reading.claimed) == reading.files_read


def test_dedup_is_by_path_so_the_two_addressing_rules_cannot_drift(tmp_path: Path):
    """The bead lane addresses `<bead-id>-*.md`; the manifest lane a normalised stem.

    A dedup rule that re-guessed either spelling would either double-count a
    brief or hide it. Comparing the paths each reader opened cannot drift.
    """
    stack = stack_with(
        tmp_path / "stack",
        {"he-a9cfa-dispatch-gate-brief.md": PENDING, "09-untracked-brief.md": PENDING},
    )

    reading = stack_records(stack, claimed=[stack / "he-a9cfa-dispatch-gate-brief.md"])

    assert [record.slug for record in reading.records] == ["untracked"]


# --- through the command -----------------------------------------------------


def test_a_stack_only_brief_reaches_the_roster_and_says_what_backs_it(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    stack_with(
        rig_root / ".beads" / "briefs" / "stack",
        {"31-verdict-in-the-stack-brief.md": ADJUDICATED},
    )

    payload = run_mctl(city_root, rig_root, "briefs", "list", "--json")

    row = next(
        item for item in payload["briefs"] if item["brief_id"] == "verdict-in-the-stack"
    )
    assert row["source"] == SOURCE_STACK
    assert row["canonical_source"] == CANONICAL_SOURCE_STACK
    assert row["bead_id"] is None
    assert row["title"] is None
    # No artifact scan: a brief that never had a bead has no caches to be
    # `missing`, and reporting four would read as damage rather than absence.
    assert row["redundant_artifacts"] == []
    # The body reaches the roster, because the roster is the only surface this
    # record ever gets: `show`, `options`, `doctor` and `validate` all act on a
    # bead. A body withheld here is a body withheld everywhere.
    assert row["body"] == ADJUDICATED
    assert [document["lane"] for document in row["documents"]] == ["stack"]
    assert row["documents"][0]["path"].endswith("31-verdict-in-the-stack-brief.md")
    assert any(
        section["section_index"] == 1 for section in row["documents"][0]["sections"]
    )


def test_a_bead_cached_in_both_lanes_does_not_also_appear_as_a_stack_brief(tmp_path: Path):
    """`_cached_brief_document` prefers the pile, which used to orphan the stack copy.

    The fixture's `mc-open` is cached in both. Excluding only the path that
    lookup *returned* would leave the stack copy claimed by nobody and emit it
    as a brief with no bead -- which is false, and is exactly the double-count
    the old dedup was reaching for while pointed at the wrong population.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    stack = rig_root / ".beads" / "briefs" / "stack"
    assert (stack / "mc-open.md").is_file()
    assert (rig_root / ".beads" / "briefs" / ".pile" / "mc-open.md").is_file()

    payload = run_mctl(city_root, rig_root, "briefs", "list", "--json")

    ids = [item["brief_id"] for item in payload["briefs"]]
    assert ids.count("mc-open") == 1
    assert next(item for item in payload["briefs"] if item["brief_id"] == "mc-open")[
        "source"
    ] == "bead"


# --- the live corpus, as invariants ------------------------------------------


@pytest.mark.skipif(not LIVE_STACK.is_dir(), reason="no live brief stack")
def test_every_live_stack_file_is_reachable_through_exactly_one_population():
    """The whole point of the slice, stated as arithmetic rather than as a count.

    87 of 89 live stack documents reached no surface. Each must now be reached
    by exactly one of: a manifest row that joined it, a bead that addresses it,
    or a record of its own. Nothing may be reached twice, and nothing missed.
    """
    files = {path for path in LIVE_STACK.glob("*.md")}
    joined = manifest_records(LIVE_MANIFEST, LIVE_STACK).stack_paths
    emitted = {record.path for record in stack_records(LIVE_STACK, claimed=joined).records}

    assert not (joined & emitted), "a stack file was counted by two populations"
    assert joined | emitted == files, "a stack file is reachable by no population"


@pytest.mark.skipif(not LIVE_STACK.is_dir(), reason="no live brief stack")
def test_the_live_stack_records_carry_the_fields_they_were_measured_to_have():
    reading = stack_records(LIVE_STACK)

    assert reading.files_read > 0
    assert len(reading.records) == reading.files_read
    seen = {reading_.name for record in reading.records for reading_ in record.fields}
    assert seen, "no stack file declared any exposed field -- the frontmatter read broke"
    assert all(record.slug for record in reading.records)
    assert all(
        (record.timestamp is None) == (record.timestamp_field is None)
        for record in reading.records
    )
    assert all(record.body != "" for record in reading.records)
