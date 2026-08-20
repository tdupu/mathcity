"""Stack files as the fourth read-side source, and a dedup that never subtracts.

Slices 6 and 7 suppressed a decisions-track row whenever a file in
`.beads/briefs/stack/` normalised to the same slug, on the stated ground that
"a stack file already represents them". Nothing read stack files. Measured on
the live city 2026-08-19: 46 rows suppressed, **0** of the 46 reachable
anywhere in the roster, and of the 89 stack files exactly **2** reachable --
and those only as some bead's cached body. So the dedup subtracted 46 briefs
and added none, and 87 documents with real frontmatter reached no surface.

`gh-38-decisions-track-classifier-verify-close-brief.md` is the case this
slice is measured against: deposited 2026-08-19, awaiting a verdict, and
invisible to `briefs list --all-rigs` before this. It has no manifest row at
all, so it was never even a dedup casualty -- it was simply never read.

Every number asserted below comes from a fixture built in the test. The live
city is checked separately and by *shape* rather than by frozen count, at the
end: a stack file appearing overnight is not a regression, and a test that
fails for being right is worse than no test.
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

from mctl_core.documents import (  # noqa: E402
    CANONICAL_SOURCE_STACK_FILE,
    SOURCE_STACK_FILE,
    read_documents,
    read_stack,
)
from mctl_core.manifest import (  # noqa: E402
    CODE_BODY_NO_FRONTMATTER,
    CODE_MANIFEST_ROW_NO_SLUG,
    SOURCE_MANIFEST,
    STATE_ADJUDICATED,
    STATE_PENDING,
    normalize_stem,
)
from mctl_core.verdicts import CONFIDENCE_HIGH, SOURCE_BRIEF_FRONTMATTER  # noqa: E402

MCTL = SCRIPTS_ROOT / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"

LIVE_ROOT = Path.home() / "gt" / ".beads"
LIVE_MANIFEST = LIVE_ROOT / "decisions-track" / "manifest.jsonl"
LIVE_STACK = LIVE_ROOT / "briefs" / "stack"

#: The acceptance case, by name. Named as a constant so a failure says which
#: document went missing rather than which glob returned nothing.
GH_38 = "gh-38-decisions-track-classifier-verify-close-brief.md"


# --- helpers -----------------------------------------------------------------


STACK_BODY = """---
artifact: gh-issue-38
status: present-it-pending
form: compact
track: decisions-to-briefs
unlock_count: 4
priority: P1
deposited_at: 2026-08-19T10:40:00-04:00
---

## §1 What is being decided

Whether to close the issue.
"""


def stack_with(directory: Path, files: dict[str, str]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (directory / name).write_text(text, encoding="utf-8")
    return directory


def manifest_with(path: Path, rows: list[dict[str, object]]) -> Path:
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


# --- the acceptance case -----------------------------------------------------


def test_a_deposited_stack_file_with_no_row_and_no_bead_is_listed(tmp_path: Path):
    """The gh-38 shape: a stack file nothing else records, at fixture scale.

    87 of the 89 live files are in this position. Before this slice the only
    stack files any reader touched were the 2 named `<bead-id>-…-brief.md`,
    and those only as that bead's cached body.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    stack_with(rig_root / ".beads" / "briefs" / "stack", {GH_38: STACK_BODY})

    payload = run_mctl(city_root, rig_root, "briefs", "list", "--json")

    record = next(
        item
        for item in payload["briefs"]
        if item["brief_id"] == normalize_stem(Path(GH_38).stem)
    )
    assert record["source"] == SOURCE_STACK_FILE
    assert record["canonical_source"] == CANONICAL_SOURCE_STACK_FILE
    assert record["bead_id"] is None
    assert record["status"] == "present-it-pending"
    assert record["decision_state"] == STATE_PENDING
    # Read from the frontmatter key the file actually carries, never derived
    # from an mtime: a deposited-at date is a fact about the brief.
    assert record["timestamp"] == "2026-08-19T10:40:00-04:00"
    assert record["timestamp_field"] == "deposited_at"
    assert record["body_path"].endswith(GH_38)


@pytest.mark.skipif(not (LIVE_STACK / GH_38).is_file(), reason="gh-38 brief not deposited here")
def test_the_live_gh_38_brief_is_reachable():
    """Named, not globbed. This exact file was the acceptance criterion."""
    reading = read_documents(LIVE_MANIFEST, LIVE_STACK)

    slug = normalize_stem(Path(GH_38).stem)
    record = next((item for item in reading.records if item.brief_id == slug), None)

    assert record is not None, f"{GH_38} reached no surface"
    assert record.source == SOURCE_STACK_FILE
    assert record.status == "present-it-pending"
    assert record.decision_state == STATE_PENDING
    assert record.body is not None and record.body.strip()


# --- the invariant -----------------------------------------------------------


def test_no_document_is_suppressed_without_a_record_that_represents_it(tmp_path: Path):
    """`emitted + duplicate + unusable == read`, and every duplicate names a record.

    The arithmetic is the whole point: the dedup it replaces removed 46 rows
    and emitted nothing in their place, so `emitted + duplicate` came to 158
    against 293 documents read.
    """
    stack = stack_with(
        tmp_path / "stack",
        {"01-paired-brief.md": STACK_BODY, "02-stack-only-brief.md": STACK_BODY},
    )
    manifest = manifest_with(
        tmp_path / "decisions-track" / "manifest.jsonl",
        [
            {"slug": "paired", "status": "briefed"},
            {"slug": "row-only", "status": "briefed", "verdict": "approve"},
        ],
    )

    reading = read_documents(manifest, stack)

    assert reading.documents_read == 4
    assert len(reading.records) == 3
    assert len(reading.duplicates) == 1
    assert reading.unusable == ()
    assert reading.balanced
    emitted = {record.brief_id for record in reading.records}
    for duplicate in reading.duplicates:
        assert duplicate.represented_by in emitted, "a document was suppressed into nothing"


def test_a_row_with_no_identity_is_counted_unusable_rather_than_absorbed(tmp_path: Path):
    """A slugless row cannot be merged onto anything, so it is not a duplicate.

    Counting it as one would claim some record represents it. It gets its own
    lane, its own MBRF062, and keeps the arithmetic exact.
    """
    stack = stack_with(tmp_path / "stack", {"01-only-brief.md": STACK_BODY})
    manifest = manifest_with(
        tmp_path / "decisions-track" / "manifest.jsonl",
        [{"status": "briefed"}, {"slug": "fine", "status": "briefed"}],
    )

    reading = read_documents(manifest, stack)

    assert reading.documents_read == 3
    assert len(reading.records) == 2
    assert reading.duplicates == ()
    assert [item.code for item in reading.unusable] == [CODE_MANIFEST_ROW_NO_SLUG]
    assert reading.balanced


def test_a_bead_that_already_carries_a_stack_file_is_not_duplicated(tmp_path: Path):
    """The mirror image of the defect: two records for one document.

    The fixture bead `mc-open` has copies in both the pile and the stack. The
    bead's own lookup prefers the pile, so claiming only the path it reports
    would leave `stack/mc-open.md` to be emitted as a brief of its own -- under
    the bead's id.
    """
    city_root, rig_root = runtime_fixture(tmp_path)

    payload = run_mctl(city_root, rig_root, "briefs", "list", "--json")

    matching = [item for item in payload["briefs"] if item["brief_id"] == "mc-open"]
    assert len(matching) == 1
    assert matching[0]["source"] == "bead"


# --- one record for a pair, with both readings kept --------------------------


def test_a_row_and_a_stack_file_for_one_brief_produce_exactly_one_record(tmp_path: Path):
    """46 live pairs. Not two records, and -- the defect -- not zero."""
    stack = stack_with(tmp_path / "stack", {"07-paired-brief.md": STACK_BODY})
    manifest = manifest_with(
        tmp_path / "decisions-track" / "manifest.jsonl",
        [{"slug": "paired", "status": "briefed", "form": "full"}],
    )

    reading = read_documents(manifest, stack)

    assert [record.brief_id for record in reading.records] == ["paired"]
    (record,) = reading.records
    assert record.merged
    # The file is the brief; the row is an index entry about it.
    assert record.source == SOURCE_STACK_FILE
    assert record.canonical_source == CANONICAL_SOURCE_STACK_FILE
    assert record.status == "present-it-pending"
    # And the row it folded in is named, not merely gone.
    assert record.also_recorded_in
    assert any("manifest.jsonl:1" in location for location in record.also_recorded_in)


def test_a_pair_that_disagrees_keeps_both_readings_in_authority_order(tmp_path: Path):
    """`status` disagrees 28 times live, `form` 4 times, `gates` once.

    Resolving either away would destroy the only record that the file and the
    row describe the same brief differently.
    """
    stack = stack_with(tmp_path / "stack", {"07-paired-brief.md": STACK_BODY})
    manifest = manifest_with(
        tmp_path / "decisions-track" / "manifest.jsonl",
        [{"slug": "paired", "status": "briefed", "form": "full"}],
    )

    (record,) = read_documents(manifest, stack).records

    form = next(item for item in record.fields if item.name == "form")
    assert form.conflict is True
    assert [(item.value, item.source) for item in form.readings] == [
        ("compact", "frontmatter"),
        ("full", "manifest_row"),
    ]
    assert form.value == "compact", "the stack file leads on a merged pair"
    status = next(item for item in record.fields if item.name == "status")
    assert status.conflict is True
    assert {item.value for item in status.readings} == {"present-it-pending", "briefed"}


def test_a_verdict_on_either_side_of_a_pair_resolves_the_record(tmp_path: Path):
    """4 live pairs carry a verdict on the row only and 1 on the file only.

    A merged record that read only its leading store would file 4 adjudicated
    briefs as pending.
    """
    stack = stack_with(tmp_path / "stack", {"07-paired-brief.md": STACK_BODY})
    manifest = manifest_with(
        tmp_path / "decisions-track" / "manifest.jsonl",
        [{"slug": "paired", "status": "adjudicated", "verdict": "approve"}],
    )

    (record,) = read_documents(manifest, stack).records

    assert record.decision_state == STATE_ADJUDICATED
    assert record.verdict is not None
    assert record.verdict.text == "approve"
    # It says which document attested it. The stack file did not.
    assert "manifest.jsonl" in record.verdict.field


# --- frontmatter, with provenance and nothing invented -----------------------


def test_stack_frontmatter_is_exposed_with_the_document_it_came_from(tmp_path: Path):
    stack = stack_with(tmp_path / "stack", {"01-counted-brief.md": STACK_BODY})

    records, duplicates, read, issues = read_stack(stack)

    (record,) = records
    assert (duplicates, read, issues) == ((), 1, ())
    by_name = {item.name: item for item in record.fields}
    assert by_name["unlock_count"].value == "4"
    assert by_name["unlock_count"].source == "frontmatter"
    # Named so a merged record's two frontmatter readings are distinguishable:
    # a stack file and a decisions-track snapshot are different documents.
    assert by_name["unlock_count"].readings[0].field.startswith("briefs/stack:")
    assert by_name["priority"].value == "P1"
    assert by_name["track"].value == "decisions-to-briefs"
    assert by_name["form"].value == "compact"
    # Nothing invented: the file declares no gates and no verdict.
    assert "gates" not in by_name
    assert "verdict" not in by_name
    assert record.verdict is None


def test_a_stack_verdict_is_typed_and_says_it_came_from_the_document(tmp_path: Path):
    """22 live files carry a frontmatter verdict. It is not a bead's verdict."""
    stack = stack_with(
        tmp_path / "stack",
        {"01-decided-brief.md": "---\nstatus: adjudicated\nverdict: approve\n---\n\n# text\n"},
    )

    (record,), _, _, _ = read_stack(stack)

    assert record.decision_state == STATE_ADJUDICATED
    assert record.verdict.text == "approve"
    assert record.verdict.source == SOURCE_BRIEF_FRONTMATTER
    assert record.verdict.confidence == CONFIDENCE_HIGH


def test_a_file_with_no_frontmatter_degrades_that_file_only(tmp_path: Path):
    """WARN per document, like MBRF060-066: one bad header must not sink the read."""
    stack = stack_with(
        tmp_path / "stack",
        {"01-headerless-brief.md": "# just a body\n", "02-fine-brief.md": STACK_BODY},
    )

    records, _, read, issues = read_stack(stack)

    assert read == 2
    assert [record.slug for record in records] == ["fine", "headerless"]
    assert [issue.code for issue in issues] == [CODE_BODY_NO_FRONTMATTER]
    # The issue names the file, not the manifest: an operator sent to the wrong
    # document is an operator who cannot fix anything.
    assert issues[0].location.endswith("01-headerless-brief.md")
    headerless = next(record for record in records if record.slug == "headerless")
    assert headerless.body == "# just a body\n"
    assert headerless.fields == ()


def test_a_file_with_no_date_key_reports_no_timestamp(tmp_path: Path):
    """Never the mtime. A synthesised date renders as a real Age."""
    stack = stack_with(tmp_path / "stack", {"01-undated-brief.md": "---\nstatus: draft\n---\n"})

    (record,), _, _, _ = read_stack(stack)

    assert record.timestamp is None
    assert record.timestamp_field is None


# --- the payload: elided, never truncated ------------------------------------


def test_a_roster_body_is_absent_and_labelled_rather_than_shortened(tmp_path: Path):
    """5.17 MB with every body attached, so the roster leaves them off.

    An elided body says so. A body silently cut to a preview would still read
    as the whole brief, which is the one outcome worth ruling out.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    stack_with(rig_root / ".beads" / "briefs" / "stack", {GH_38: STACK_BODY})
    slug = normalize_stem(Path(GH_38).stem)

    listed = run_mctl(city_root, rig_root, "briefs", "list", "--json")
    record = next(item for item in listed["briefs"] if item["brief_id"] == slug)

    assert "body" not in record
    assert record["body_elided"]
    assert record["body_path"].endswith(GH_38)

    with_bodies = run_mctl(city_root, rig_root, "briefs", "list", "--bodies", "--json")
    asked = next(item for item in with_bodies["briefs"] if item["brief_id"] == slug)

    assert asked["body_elided"] is None
    assert asked["body"] == STACK_BODY, "the body is verbatim or it is absent"
    assert asked["sections"]


def test_briefs_show_carries_a_stack_files_body(tmp_path: Path):
    """What makes the roster's elision safe.

    A document brief reaches no other detail surface: `options`, `doctor` and
    `validate` all act on a bead. If `show` did not serve it, leaving bodies
    off the roster would put it back where Slice 7 found it.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    stack_with(rig_root / ".beads" / "briefs" / "stack", {GH_38: STACK_BODY})
    slug = normalize_stem(Path(GH_38).stem)

    payload = run_mctl(city_root, rig_root, "briefs", "show", slug, "--json")

    brief = payload["brief"]
    assert brief["source"] == SOURCE_STACK_FILE
    assert brief["body"] == STACK_BODY
    assert brief["body_elided"] is None
    assert [section["section_index"] for section in brief["sections"]] == [1]


# --- the live city, by shape ------------------------------------------------


@pytest.mark.skipif(not LIVE_STACK.is_dir(), reason="no live brief stack")
def test_the_live_join_balances_and_adds_rather_than_subtracts():
    reading = read_documents(LIVE_MANIFEST, LIVE_STACK)

    assert reading.balanced, (
        f"{len(reading.records)} + {len(reading.duplicates)} + {len(reading.unusable)} "
        f"!= {reading.documents_read}"
    )
    stack_files = len(list(LIVE_STACK.glob("*.md")))
    emitted_stack = [item for item in reading.records if item.source == SOURCE_STACK_FILE]
    represented = {duplicate.represented_by for duplicate in reading.duplicates}
    # Every stack file is either its own record or represented by one.
    assert len(emitted_stack) + len(
        [item for item in reading.duplicates if item.kind == SOURCE_STACK_FILE]
    ) == stack_files
    assert represented <= {item.brief_id for item in reading.records} | represented
    # And the join emits strictly more than the manifest alone ever did.
    assert len(reading.records) > sum(
        1 for item in reading.records if item.source == SOURCE_MANIFEST
    )
