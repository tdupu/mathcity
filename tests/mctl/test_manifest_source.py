"""The decisions-track manifest as a third read-side source.

Two of a brief's three representations -- bead, stack file, manifest row --
had readers. The manifest did not, and on the live city 158 of its 204 rows
are represented by neither of the others: nothing could read them, count them,
or say they existed. This slice makes them reachable without minting anything,
because minting is what would make the measured state worse (105 of the 158
name no source bead, so 105 new beads would fail POLICY B2.1 on creation and
raise `MBRF004` apiece).

Every number asserted below comes from a fixture built in the test, not from
the live city. The live counts are checked separately and loosely at the end:
the brief commissioning this work quoted 45/159, a stack file appeared, and
the true split became 46/158 -- a frozen live number is a test that fails for
being right.
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
    CODE_MANIFEST_ROW_MALFORMED,
    CODE_MANIFEST_ROW_NO_SLUG,
    CODE_MANIFEST_UNREADABLE,
    SOURCE_MANIFEST,
    STATE_ADJUDICATED,
    STATE_UNREADABLE,
    manifest_records,
    normalize_stem,
    read_manifest,
)
from mctl_core.verdicts import CONFIDENCE_HIGH, SOURCE_DECISIONS_TRACK  # noqa: E402

MCTL = SCRIPTS_ROOT / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"

LIVE_MANIFEST = Path.home() / "gt" / ".beads" / "decisions-track" / "manifest.jsonl"
LIVE_STACK = Path.home() / "gt" / ".beads" / "briefs" / "stack"


# --- helpers -----------------------------------------------------------------


def write_manifest(path: Path, rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{json.dumps(row, sort_keys=True)}\n" for row in rows), encoding="utf-8"
    )
    return path


def stack_with(directory: Path, names: list[str]) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for name in names:
        (directory / name).write_text("# a brief\n", encoding="utf-8")
    return directory


def adjudicated(slug: str, **extra: object) -> dict[str, object]:
    return {"slug": slug, "status": "adjudicated", "verdict": "approve", **extra}


def unreadable(slug: str, **extra: object) -> dict[str, object]:
    return {"slug": slug, "status": "adjudicated", **extra}


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


# --- the two lanes -----------------------------------------------------------


def test_rows_split_into_adjudicated_and_unreadable_by_whether_a_verdict_is_there(
    tmp_path: Path,
):
    """The split the live corpus shows, at fixture scale: 122 vs 36 there."""
    path = write_manifest(
        tmp_path / "manifest.jsonl",
        [adjudicated(f"decided-{n}") for n in range(5)]
        + [unreadable(f"silent-{n}") for n in range(3)]
        + [{"slug": "blank-verdict", "status": "adjudicated", "verdict": "   "}]
        + [{"slug": "null-verdict", "status": "adjudicated", "verdict": None}],
    )

    reading = read_manifest(path)

    assert reading.rows_read == 10
    assert reading.state_counts == {STATE_ADJUDICATED: 5, STATE_UNREADABLE: 5}


def test_a_row_with_no_verdict_is_never_pending(tmp_path: Path):
    """`unreadable`, not `pending`: there is nothing here to decide on.

    A row with no verdict has no bead, no file, and no body. Putting it in the
    pending queue would present an un-decidable item to a human as decidable,
    which is worse than leaving it unreachable.
    """
    path = write_manifest(tmp_path / "manifest.jsonl", [unreadable("silent")])

    (record,) = read_manifest(path).records

    assert record.decision_state == STATE_UNREADABLE
    assert record.decision_state != "pending"
    assert record.verdict is None


def test_a_status_string_never_stands_in_for_a_verdict(tmp_path: Path):
    """`status: adjudicated:defer-c(7d)` is not a readable verdict.

    114 live rows carry a status that begins `adjudicated`, and 36 of those
    carry no verdict. Reading the status as the decision would manufacture 36
    adjudications nobody recorded.
    """
    path = write_manifest(
        tmp_path / "manifest.jsonl", [{"slug": "deferred", "status": "adjudicated:defer-c(7d)"}]
    )

    (record,) = read_manifest(path).records

    assert record.status == "adjudicated:defer-c(7d)"
    assert record.decision_state == STATE_UNREADABLE


# --- provenance --------------------------------------------------------------


def test_a_manifest_verdict_carries_its_own_provenance(tmp_path: Path):
    path = write_manifest(tmp_path / "manifest.jsonl", [adjudicated("decided")])

    (record,) = read_manifest(path).records

    assert record.source == SOURCE_MANIFEST
    assert record.verdict is not None
    assert record.verdict.text == "approve"
    assert record.verdict.source == SOURCE_DECISIONS_TRACK
    assert record.verdict.confidence == CONFIDENCE_HIGH
    assert "manifest.jsonl" in record.verdict.field


def test_both_populations_declare_which_store_they_came_from(tmp_path: Path):
    """The single most important field: no row may look attested when it is not."""
    city_root, rig_root = runtime_fixture(tmp_path)
    write_manifest(
        rig_root / ".beads" / "decisions-track" / "manifest.jsonl",
        [adjudicated("manifest-only")],
    )

    payload = run_mctl(city_root, rig_root, "briefs", "list", "--json")

    by_id = {brief["brief_id"]: brief for brief in payload["briefs"]}
    assert by_id["mc-open"]["source"] == "bead"
    assert by_id["mc-open"]["canonical_source"] == "bead_store"
    assert by_id["mc-open"]["bead_id"] == "mc-open"

    row = by_id["manifest-only"]
    assert row["source"] == "manifest"
    assert row["canonical_source"] == "decisions_track_manifest"
    assert row["bead_id"] is None
    assert row["title"] is None
    assert row["verdict"]["source"] == SOURCE_DECISIONS_TRACK


def test_a_manifest_record_claims_no_body_and_no_cache_artifacts(tmp_path: Path):
    """There is no file and no bead behind these rows, so there is nothing to show.

    An artifact scan would report four `missing` caches for a brief that never
    had any, which reads as damage rather than as absence.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    write_manifest(
        rig_root / ".beads" / "decisions-track" / "manifest.jsonl", [adjudicated("manifest-only")]
    )

    payload = run_mctl(city_root, rig_root, "briefs", "list", "--json")

    row = next(item for item in payload["briefs"] if item["brief_id"] == "manifest-only")
    assert row["redundant_artifacts"] == []
    assert row["labels"] == []
    assert "body" not in row
    assert "sections" not in row


# --- timestamps --------------------------------------------------------------


def test_a_row_with_no_date_reports_none_rather_than_a_synthesised_one(tmp_path: Path):
    """60 live rows carry no date. A fabricated one renders as a real Age."""
    path = write_manifest(
        tmp_path / "manifest.jsonl",
        [unreadable("undated"), adjudicated("dated", adjudicated_at="2026-07-18")],
    )

    undated, dated = read_manifest(path).records

    assert undated.timestamp is None
    assert undated.timestamp_field is None
    assert dated.timestamp == "2026-07-18"
    assert dated.timestamp_field == "adjudicated_at"


def test_a_timestampless_row_survives_the_whole_pipeline_as_null(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    write_manifest(
        rig_root / ".beads" / "decisions-track" / "manifest.jsonl", [unreadable("undated")]
    )

    payload = run_mctl(city_root, rig_root, "briefs", "list", "--json")

    row = next(item for item in payload["briefs"] if item["brief_id"] == "undated")
    assert row["timestamp"] is None
    assert row["timestamp_field"] is None
    assert row["created_at"] is None
    assert row["updated_at"] is None


def test_a_bead_record_says_which_field_its_timestamp_came_from(tmp_path: Path):
    """Both populations answer "how old is this" from a field they can name."""
    city_root, rig_root = runtime_fixture(tmp_path)

    payload = run_mctl(city_root, rig_root, "briefs", "list", "--json")

    row = next(item for item in payload["briefs"] if item["brief_id"] == "mc-open")
    assert row["timestamp"] == row["updated_at"]
    assert row["timestamp_field"] == "updated_at"
    assert row["track"] is None


# --- track -------------------------------------------------------------------


def test_track_is_a_first_class_field_on_every_manifest_row(tmp_path: Path):
    path = write_manifest(
        tmp_path / "manifest.jsonl",
        [
            adjudicated("a", track="process-policy"),
            unreadable("b", track="pack-hygiene"),
            adjudicated("c"),
        ],
    )

    records = read_manifest(path).records

    assert [record.track for record in records] == ["process-policy", "pack-hygiene", None]


# --- deduplication -----------------------------------------------------------


def test_normalisation_strips_the_ordering_prefix_and_the_brief_suffix():
    assert normalize_stem("240-dolt-quarantine-retain-222-step2-brief") == (
        "dolt-quarantine-retain-222-step2"
    )
    assert normalize_stem("02-crons-durable-vs-session-brief") == "crons-durable-vs-session"
    assert normalize_stem("he-ckilh-dispatch-gate") == "he-ckilh-dispatch-gate"
    # Only the LEADING run of digits is an ordering prefix. `222-step2` in the
    # middle is part of the slug, and a greedier rule collides real briefs.
    assert normalize_stem("143-diff-alg-1-examples") == "diff-alg-1-examples"


def test_rows_a_stack_file_already_represents_are_not_emitted_again(tmp_path: Path):
    """46 of the live 204 rows are already visible through their stack file."""
    stack = stack_with(
        tmp_path / "stack",
        [
            "12-brief-queue-hygiene-brief.md",
            "he-ckilh-dispatch-gate.md",
            "gone-brief.md.bak",
            ".index.jsonl",
        ],
    )
    path = write_manifest(
        tmp_path / "manifest.jsonl",
        [
            adjudicated("brief-queue-hygiene"),
            adjudicated("he-ckilh-dispatch-gate"),
            adjudicated("gone"),
            unreadable("never-filed"),
        ],
    )

    reading = manifest_records(path, stack)

    assert reading.rows_read == 4
    assert sorted(reading.represented) == ["brief-queue-hygiene", "he-ckilh-dispatch-gate"]
    # `gone` is represented only by a `.bak` copy, which is a backup and not a
    # presentation; suppressing a row because somebody once saved a file would
    # hide it from every reader again.
    assert [record.slug for record in reading.records] == ["gone", "never-filed"]


def test_every_row_is_either_emitted_or_named_as_already_represented(tmp_path: Path):
    """The arithmetic a population count rests on: nothing falls between."""
    stack = stack_with(tmp_path / "stack", ["01-kept-brief.md"])
    path = write_manifest(
        tmp_path / "manifest.jsonl",
        [adjudicated("kept"), adjudicated("one"), unreadable("two")],
    )

    reading = manifest_records(path, stack)

    assert len(reading.records) + len(reading.represented) == reading.rows_read


def test_a_missing_manifest_is_silent_rather_than_an_error(tmp_path: Path):
    """Most rigs have no manifest at all; only the HQ store does."""
    reading = manifest_records(tmp_path / "absent.jsonl", tmp_path / "stack")

    assert reading.records == ()
    assert reading.issues == ()
    assert reading.rows_read == 0


# --- tolerant reads ----------------------------------------------------------


def test_one_bad_line_costs_that_line_and_nothing_else(tmp_path: Path):
    """The strict reader behind the B2.10 gate loses the file; this one loses a row."""
    path = tmp_path / "manifest.jsonl"
    path.write_text(
        json.dumps(adjudicated("good")) + "\n"
        + "{not json at all\n"
        + json.dumps(["a list, not a row"]) + "\n"
        + json.dumps({"status": "adjudicated"}) + "\n"
        + json.dumps(adjudicated("also-good")) + "\n",
        encoding="utf-8",
    )

    reading = read_manifest(path)

    assert [record.slug for record in reading.records] == ["good", "also-good"]
    codes = [issue.code for issue in reading.issues]
    assert codes == [
        CODE_MANIFEST_ROW_MALFORMED,
        CODE_MANIFEST_ROW_MALFORMED,
        CODE_MANIFEST_ROW_NO_SLUG,
    ]
    # An operator has to be able to find the row again in a 204-line file of
    # near-identical JSON, and a row with no slug has no other address.
    assert [issue.line for issue in reading.issues] == [2, 3, 4]


def test_an_unreadable_manifest_reports_it_instead_of_raising(tmp_path: Path):
    path = tmp_path / "manifest.jsonl"
    path.write_bytes(b"\xff\xfe not utf-8 at all\n")

    reading = read_manifest(path)

    assert reading.records == ()
    assert [issue.code for issue in reading.issues] == [CODE_MANIFEST_UNREADABLE]


def test_skipped_rows_surface_as_warnings_on_the_command(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    manifest = rig_root / ".beads" / "decisions-track" / "manifest.jsonl"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(
        json.dumps(adjudicated("good")) + "\n" + "{not json\n", encoding="utf-8"
    )

    payload = run_mctl(city_root, rig_root, "briefs", "list", "--json")

    warning = next(
        item for item in payload["diagnostics"] if item["code"] == CODE_MANIFEST_ROW_MALFORMED
    )
    assert warning["severity"] == "WARN"
    assert warning["facts"]["data_location"].endswith("manifest.jsonl:2")
    assert any(brief["brief_id"] == "good" for brief in payload["briefs"])


# --- nothing is written ------------------------------------------------------


def test_reading_the_manifest_writes_nothing(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    manifest = write_manifest(
        rig_root / ".beads" / "decisions-track" / "manifest.jsonl",
        [adjudicated("one"), unreadable("two")],
    )
    before = manifest.read_bytes()

    run_mctl(city_root, rig_root, "briefs", "list", "--json")

    assert manifest.read_bytes() == before


# --- the live corpus, checked for shape rather than for a frozen number ------


@pytest.mark.skipif(not LIVE_MANIFEST.is_file(), reason="no live decisions-track manifest")
def test_the_live_manifest_reads_consistently():
    """Invariants, not counts.

    This brief's own numbers (45 represented / 159 not) were correct when
    measured and off by one a few days later, because a stack file appeared.
    Asserting them here would make a passing test into a maintenance chore and
    a failing one into a false alarm; asserting that the parts still add up
    catches the reader breaking, which is what a test can actually know.
    """
    reading = manifest_records(LIVE_MANIFEST, LIVE_STACK)

    assert reading.rows_read > 0
    assert len(reading.records) + len(reading.represented) == reading.rows_read
    assert sum(reading.state_counts.values()) == len(reading.records)
    assert all(record.slug for record in reading.records)
    assert all(
        (record.timestamp is None) == (record.timestamp_field is None)
        for record in reading.records
    )
