"""The decisions-track manifest as a third read-side source, bodies included.

Two of a brief's three representations -- bead, stack file, manifest row --
had readers. The manifest did not, and on the live city 158 of its 204 rows
are represented by neither of the others: nothing could read them, count them,
or say they existed. Slice 6 made them reachable without minting anything,
because minting is what would make the measured state worse (105 of the 158
name no source bead, so 105 new beads would fail POLICY B2.1 on creation and
raise `MBRF004` apiece).

**Slice 6 then read the manifest without listing the directory it sits in.**
That directory holds 204 markdown bodies. 35 of the 36 rows Slice 6 filed as
`unreadable` have one, so 35 undecided briefs with real text were kept out of
the pending queue on the grounds that they could not be shown. The tests below
now pin the corrected reading: `unreadable` means **no body file exists** --
one live row -- and a row with a body and no verdict is `pending`.

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
    CODE_BODY_AMBIGUOUS,
    CODE_BODY_NO_FRONTMATTER,
    CODE_MANIFEST_ROW_MALFORMED,
    CODE_MANIFEST_ROW_NO_SLUG,
    CODE_MANIFEST_UNREADABLE,
    CODE_ROW_HAS_NO_BODY,
    SOURCE_MANIFEST,
    STATE_ADJUDICATED,
    STATE_PENDING,
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


def stack_with(directory: Path, names: list[str], *, body: str = "# a brief\n") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    for name in names:
        (directory / name).write_text(body, encoding="utf-8")
    return directory


def adjudicated(slug: str, **extra: object) -> dict[str, object]:
    return {"slug": slug, "status": "adjudicated", "verdict": "approve", **extra}


def unreadable(slug: str, **extra: object) -> dict[str, object]:
    """A row with no `verdict` key. Whether it is *unreadable* now depends on
    whether a body file exists beside the manifest, which is the point."""
    return {"slug": slug, "status": "adjudicated", **extra}


BODY = """---
status: ready
form: full
track: brief-system
---

## §1 What is being decided

Body text, so the row is not unreadable.
"""


def bodies_for(directory: Path, slugs: list[str], *, body: str = BODY) -> Path:
    """A decisions-track directory holding one `NNN-<slug>-brief.md` per slug.

    Numbered and suffixed exactly as the live directory writes them, because
    the join is a filename normalisation and a test on bare `<slug>.md` files
    would never exercise it.
    """
    directory.mkdir(parents=True, exist_ok=True)
    for number, slug in enumerate(slugs, start=1):
        (directory / f"{number:02d}-{slug}-brief.md").write_text(body, encoding="utf-8")
    return directory


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


def test_rows_split_into_three_lanes_by_body_then_verdict(tmp_path: Path):
    """The live split, at fixture scale: 125 adjudicated / 32 pending / 1 not there.

    Slice 6 read this as two lanes and put every verdictless row in
    `unreadable`. Whether a body exists and whether a verdict exists are
    independent facts, and the second is only askable once the first is yes.
    """
    bodies = bodies_for(tmp_path, ["decided-0", "decided-1", "silent-0", "silent-1"])
    path = write_manifest(
        bodies / "manifest.jsonl",
        [adjudicated(f"decided-{n}") for n in range(2)]
        + [unreadable(f"silent-{n}") for n in range(2)]
        + [{"slug": "blank-verdict", "status": "adjudicated", "verdict": "   "}]
        + [{"slug": "gone", "status": "adjudicated"}],
    )

    reading = read_manifest(path)

    assert reading.rows_read == 6
    assert reading.state_counts == {
        STATE_ADJUDICATED: 2,
        STATE_PENDING: 2,
        STATE_UNREADABLE: 2,
    }


def test_a_row_with_a_body_and_no_verdict_is_pending_not_unreadable(tmp_path: Path):
    """The Slice 6 defect, stated as a test.

    35 of the 36 rows Slice 6 called `unreadable` have a markdown body in the
    manifest's own directory. They are ordinary undecided briefs, and hiding
    them from the pending queue hid the work a human was supposed to see.
    """
    bodies = bodies_for(tmp_path, ["silent"])
    path = write_manifest(bodies / "manifest.jsonl", [unreadable("silent")])

    (record,) = read_manifest(path).records

    assert record.decision_state == STATE_PENDING
    assert record.decision_state != STATE_UNREADABLE
    assert record.verdict is None
    assert record.body is not None


def test_unreadable_means_no_body_file_exists_and_nothing_else(tmp_path: Path):
    """One live row is in this lane. Slice 6 put 36 there.

    `unreadable` is a statement about the corpus -- a brief was tracked and
    nothing anywhere records what it said -- not about a missing verdict.
    """
    bodies = bodies_for(tmp_path, [])
    path = write_manifest(bodies / "manifest.jsonl", [adjudicated("no-file-anywhere")])

    (record,) = read_manifest(path).records

    assert record.decision_state == STATE_UNREADABLE
    assert record.body_path is None
    assert record.body is None
    # Not "" -- an empty string says the brief is empty rather than that it
    # was never stored, which is precisely the conflation being corrected.
    assert record.body != ""
    # A verdict on the row does not rescue it: the verdict is readable and the
    # brief is not, and the lane is about the brief.
    assert record.verdict is not None


def test_a_row_with_no_body_reports_why_per_row(tmp_path: Path):
    bodies = bodies_for(tmp_path, ["here"])
    path = write_manifest(
        bodies / "manifest.jsonl", [adjudicated("here"), adjudicated("gone")]
    )

    reading = read_manifest(path)

    assert [issue.code for issue in reading.issues] == [CODE_ROW_HAS_NO_BODY]
    assert reading.issues[0].line == 2
    assert "gone" in (reading.issues[0].detail or "")


def test_a_status_string_never_stands_in_for_a_verdict(tmp_path: Path):
    """`status: adjudicated:defer-c(7d)` is not a readable verdict.

    114 live rows carry a status that begins `adjudicated`. Reading the status
    as the decision would manufacture adjudications nobody recorded -- so a
    row like this one is pending once its body is found, never adjudicated.
    """
    bodies = bodies_for(tmp_path, ["deferred"])
    path = write_manifest(
        bodies / "manifest.jsonl", [{"slug": "deferred", "status": "adjudicated:defer-c(7d)"}]
    )

    (record,) = read_manifest(path).records

    assert record.status == "adjudicated:defer-c(7d)"
    assert record.verdict is None
    assert record.decision_state == STATE_PENDING


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


def test_a_row_with_a_stack_file_is_joined_to_it_rather_than_suppressed(tmp_path: Path):
    """The defect this replaced: 46 of 204 rows were dropped for having a stack file.

    The stated reason was that such a brief "has always been visible" through
    the file. Nothing reads stack files as records -- 0 of the 46 slugs
    appeared anywhere in `mctl briefs list --all-rigs` -- so suppression was
    not deduplication. It was the only record of 46 briefs, deleted.
    """
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
    # Every row is emitted. Two of them gained a document they did not have
    # before; none of them lost its record for having one.
    assert [record.slug for record in reading.records] == [
        "brief-queue-hygiene",
        "he-ckilh-dispatch-gate",
        "gone",
        "never-filed",
    ]
    assert sorted(reading.joined) == ["brief-queue-hygiene", "he-ckilh-dispatch-gate"]
    joined = next(item for item in reading.records if item.slug == "brief-queue-hygiene")
    assert joined.stack_path == stack / "12-brief-queue-hygiene-brief.md"
    assert joined.stack_body == "# a brief\n"
    # `gone` matches only a `.bak` copy, which is a backup and not a
    # presentation; joining a row to a file somebody once saved would attach a
    # brief to the wrong document.
    assert next(item for item in reading.records if item.slug == "gone").stack_path is None


def test_a_joined_row_keeps_both_copies_of_a_brief_that_disagree(tmp_path: Path):
    """19 of the 46 live pairs differ, and 13 disagree about `form`.

    The stack copies had been rewritten from `compact` to `full` by the
    shape-repair pass while the decisions-track copies still said `compact`.
    Resolving that silently would destroy the only record that the pipeline's
    two copies of a brief have drifted apart.
    """
    bodies = bodies_for(
        tmp_path / "decisions-track",
        ["shape-repaired"],
        body="---\nform: compact\nstatus: present-it-pending\n---\n\n## §1 What is being decided\n\nAs deposited.\n",
    )
    stack = stack_with(
        tmp_path / "stack",
        ["01-shape-repaired-brief.md"],
        body="---\nform: full\nstatus: present-it-pending\n---\n\n## §1 What is being decided\n\nAs repaired.\n",
    )
    path = write_manifest(bodies / "manifest.jsonl", [unreadable("shape-repaired")])

    record = manifest_records(path, stack).records[0]

    form = next(item for item in record.fields if item.name == "form")
    assert form.conflict, "the two documents disagree about `form` and both must be kept"
    assert [(reading.source, reading.value) for reading in form.readings] == [
        ("frontmatter", "compact"),
        ("stack_frontmatter", "full"),
    ]
    # Authority order is unchanged by the new reading: the decisions-track
    # copy still answers "what does this brief say" for a caller that does not
    # ask about provenance, because the manifest lane is canonical here.
    assert form.value == "compact"
    # Both documents are carried, in authority order: the file beside the
    # manifest first, because the manifest is this record's canonical source.
    assert [lane for lane, *_ in record.documents] == ["decisions_track", "stack"]
    assert record.body != record.stack_body
    assert record.body is not None and record.stack_body is not None


def test_a_row_whose_only_document_is_its_stack_file_is_readable(tmp_path: Path):
    """`unreadable` is about the documents, not about which directory holds one.

    Slice 6 called a row unreadable because it never listed the directory
    beside the manifest. Calling one unreadable because its only copy is in
    the stack would be the same error aimed one directory over.
    """
    stack = stack_with(tmp_path / "stack", ["07-only-in-the-stack-brief.md"])
    path = write_manifest(tmp_path / "manifest.jsonl", [unreadable("only-in-the-stack")])

    record = manifest_records(path, stack).records[0]

    assert record.body_path is None
    assert record.stack_path == stack / "07-only-in-the-stack-brief.md"
    assert record.decision_state == STATE_PENDING
    assert [lane for lane, *_ in record.documents] == ["stack"]


def test_every_row_is_emitted_and_the_joined_ones_are_named(tmp_path: Path):
    """The arithmetic a population count rests on: nothing falls between."""
    stack = stack_with(tmp_path / "stack", ["01-kept-brief.md"])
    path = write_manifest(
        tmp_path / "manifest.jsonl",
        [adjudicated("kept"), adjudicated("one"), unreadable("two")],
    )

    reading = manifest_records(path, stack)

    assert len(reading.records) == reading.rows_read
    assert len(reading.joined) == 1
    assert reading.stack_paths == frozenset({stack / "01-kept-brief.md"})


def test_a_missing_manifest_is_silent_rather_than_an_error(tmp_path: Path):
    """Most rigs have no manifest at all; only the HQ store does."""
    reading = manifest_records(tmp_path / "absent.jsonl", tmp_path / "stack")

    assert reading.records == ()
    assert reading.issues == ()
    assert reading.rows_read == 0


# --- tolerant reads ----------------------------------------------------------


def test_one_bad_line_costs_that_line_and_nothing_else(tmp_path: Path):
    """The strict reader behind the B2.10 gate loses the file; this one loses a row."""
    path = bodies_for(tmp_path / "track", ["good", "also-good"]) / "manifest.jsonl"
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
    assert len(reading.records) == reading.rows_read
    assert len(reading.joined) == len(reading.stack_paths)
    assert all(
        (record.stack_path is not None) == (record.slug in set(reading.joined))
        for record in reading.records
    )
    assert sum(reading.state_counts.values()) == len(reading.records)
    assert all(record.slug for record in reading.records)
    assert all(
        (record.timestamp is None) == (record.timestamp_field is None)
        for record in reading.records
    )


# --- the body join -----------------------------------------------------------


def test_a_row_resolves_to_its_numbered_and_suffixed_file(tmp_path: Path):
    """`sigma18-done-vs-residual` -> `08-sigma18-done-vs-residual-brief.md`.

    The whole defect in one assertion: the file was always there, under a name
    the reader never constructed.
    """
    directory = tmp_path / "decisions-track"
    directory.mkdir()
    (directory / "08-sigma18-done-vs-residual-brief.md").write_text(BODY, encoding="utf-8")
    path = write_manifest(directory / "manifest.jsonl", [unreadable("sigma18-done-vs-residual")])

    (record,) = read_manifest(path).records

    assert record.body_path is not None
    assert record.body_path.name == "08-sigma18-done-vs-residual-brief.md"
    assert record.body == BODY
    assert record.decision_state == STATE_PENDING


def test_slug_normalisation_is_anchored_at_both_ends(tmp_path: Path):
    """`257-decision-brief-gate-profile-brief.md` -> `decision-brief-gate-profile`.

    An unanchored `.replace("-brief", "")` yields `decision-gate-profile`,
    matches no row, and drops a 27KB brief into `unreadable` in silence. That
    bug has shipped twice in this codebase -- once in a body-substring
    discriminator and once in a slug matcher -- so the exact live filename is
    pinned here rather than a synthetic stand-in.
    """
    assert normalize_stem("257-decision-brief-gate-profile-brief") == "decision-brief-gate-profile"
    # The trailing digits of an ordering prefix are stripped only at the start,
    # and only whole leading digits: an id inside the slug survives.
    assert normalize_stem("240-dolt-quarantine-222-step2-brief") == "dolt-quarantine-222-step2"
    # A slug that merely contains "brief" keeps it.
    assert normalize_stem("01-brief-system-policy-brief") == "brief-system-policy"


def test_the_anchored_filename_joins_to_its_row(tmp_path: Path):
    """The same regression, end to end rather than on the normaliser alone."""
    directory = tmp_path / "decisions-track"
    directory.mkdir()
    (directory / "257-decision-brief-gate-profile-brief.md").write_text(BODY, encoding="utf-8")
    path = write_manifest(
        directory / "manifest.jsonl", [unreadable("decision-brief-gate-profile")]
    )

    (record,) = read_manifest(path).records

    assert record.body == BODY
    assert record.decision_state == STATE_PENDING
    assert not any(issue.code == CODE_ROW_HAS_NO_BODY for issue in read_manifest(path).issues)


def test_two_files_normalising_to_one_slug_are_reported_not_guessed(tmp_path: Path):
    directory = tmp_path / "decisions-track"
    directory.mkdir()
    (directory / "01-same-slug-brief.md").write_text(BODY, encoding="utf-8")
    (directory / "99-same-slug-brief.md").write_text(BODY, encoding="utf-8")
    path = write_manifest(directory / "manifest.jsonl", [unreadable("same-slug")])

    reading = read_manifest(path)

    (record,) = reading.records
    assert record.body_path is not None
    assert record.body_path.name == "01-same-slug-brief.md"
    assert [issue.code for issue in reading.issues] == [CODE_BODY_AMBIGUOUS]
    assert "99-same-slug-brief.md" in (reading.issues[0].detail or "")


def test_a_body_with_no_frontmatter_degrades_that_row_only(tmp_path: Path):
    """WARN per row, like MBRF060-062: one bad header must not sink the read."""
    directory = tmp_path / "decisions-track"
    directory.mkdir()
    (directory / "01-headerless-brief.md").write_text("# just a body\n", encoding="utf-8")
    (directory / "02-fine-brief.md").write_text(BODY, encoding="utf-8")
    path = write_manifest(
        directory / "manifest.jsonl", [unreadable("headerless"), unreadable("fine")]
    )

    reading = read_manifest(path)

    assert [record.slug for record in reading.records] == ["headerless", "fine"]
    assert [issue.code for issue in reading.issues] == [CODE_BODY_NO_FRONTMATTER]
    assert reading.issues[0].line == 1
    headerless, fine = reading.records
    # The body survives even though its header did not: the text is the
    # evidence, and losing it because a header was malformed is the failure
    # this whole slice is about.
    assert headerless.body == "# just a body\n"
    assert headerless.fields == ()
    assert dict(fine.frontmatter)["form"] == "full"


# --- fields, read and never derived -----------------------------------------


def test_frontmatter_fields_are_exposed_with_their_provenance(tmp_path: Path):
    directory = tmp_path / "decisions-track"
    directory.mkdir()
    (directory / "01-counted-brief.md").write_text(
        "---\nstatus: ready\nunlock_count: 6\npriority: P1\n"
        "form: full\ngates: test-evidence N/A\ntrack: brief-system\n---\n\n## §1 What\n\nBody.\n",
        encoding="utf-8",
    )
    path = write_manifest(directory / "manifest.jsonl", [{"slug": "counted", "status": "ready"}])

    (record,) = read_manifest(path).records

    by_name = {reading.name: reading for reading in record.fields}
    assert by_name["unlock_count"].value == "6"
    assert by_name["unlock_count"].source == "frontmatter"
    assert by_name["unlock_count"].readings[0].field == "frontmatter.unlock_count"
    assert by_name["unlock_count"].readings[0].confidence == "high"
    assert by_name["priority"].value == "P1"
    assert by_name["gates"].value == "test-evidence N/A"
    assert not by_name["unlock_count"].conflict


def test_unlock_count_is_read_and_never_derived(tmp_path: Path):
    """A traversal returns ~0 -- 508 of 528 live edges are `related`.

    The frontmatter number was written at production time by whoever knew what
    the brief unblocked, so a brief that declares none reports none rather
    than a computed zero. Zero and absent are different claims.
    """
    directory = tmp_path / "decisions-track"
    directory.mkdir()
    (directory / "01-silent-brief.md").write_text(
        "---\nstatus: ready\nform: full\n---\n\n## §1 What\n\nBody.\n", encoding="utf-8"
    )
    path = write_manifest(directory / "manifest.jsonl", [{"slug": "silent", "status": "ready"}])

    (record,) = read_manifest(path).records

    assert "unlock_count" not in {reading.name for reading in record.fields}
    assert "unlock_count" not in record.to_dict()["fields"]


def test_a_row_and_its_own_file_disagreeing_keeps_both(tmp_path: Path):
    """17 live rows disagree with their body file. Resolving destroys the finding."""
    directory = tmp_path / "decisions-track"
    directory.mkdir()
    (directory / "01-split-brief.md").write_text(
        "---\nstatus: ready\nunlock_count: 9\nform: full\n---\n\n## §1 What\n\nBody.\n",
        encoding="utf-8",
    )
    path = write_manifest(
        directory / "manifest.jsonl",
        [{"slug": "split", "status": "ready", "unlock_count": 4, "form": "compact"}],
    )

    (record,) = read_manifest(path).records

    unlock = next(reading for reading in record.fields if reading.name == "unlock_count")
    assert unlock.conflict is True
    assert [(item.value, item.source) for item in unlock.readings] == [
        ("4", "manifest_row"),
        ("9", "frontmatter"),
    ]
    # The row is this record's canonical store, so `value` follows it -- but
    # nothing is discarded, and a surface can render both.
    assert unlock.value == "4"
    payload = record.to_dict()["fields"]["unlock_count"]
    assert payload["conflict"] is True
    assert len(payload["readings"]) == 2


def test_a_frontmatter_verdict_is_read_when_the_row_has_none(tmp_path: Path):
    """3 live rows are adjudicated only in their own document."""
    directory = tmp_path / "decisions-track"
    directory.mkdir()
    (directory / "01-filed-brief.md").write_text(
        "---\nstatus: adjudicated\nverdict: approve-b\n---\n\n## §1 What\n\nBody.\n",
        encoding="utf-8",
    )
    path = write_manifest(
        directory / "manifest.jsonl", [{"slug": "filed", "status": "adjudicated"}]
    )

    (record,) = read_manifest(path).records

    assert record.decision_state == STATE_ADJUDICATED
    assert record.verdict is not None
    assert record.verdict.text == "approve-b"
    # Not `decisions_track`: the manifest recorded nothing, the document did.
    assert record.verdict.source == "brief_frontmatter"
    assert record.verdict.field == "frontmatter.verdict"


# --- the live corpus, after the join ----------------------------------------


@pytest.mark.skipif(not LIVE_MANIFEST.is_file(), reason="no live decisions-track manifest")
def test_the_live_corpus_has_almost_no_unreadable_rows():
    """Slice 6 reported 36. The true figure is a small handful.

    Bounded rather than frozen, for the reason the sibling live test gives:
    the corpus moves. What cannot move without a defect is the order of
    magnitude -- `unreadable` is meant to be the rare case where a brief was
    tracked and nothing recorded what it said.
    """
    reading = manifest_records(LIVE_MANIFEST, LIVE_STACK)
    counts = reading.state_counts

    assert counts[STATE_UNREADABLE] <= 5, (
        "unreadable is meant to mean 'no body file exists anywhere'. A jump back "
        "toward 36 means the body join stopped resolving -- check the anchored "
        "slug normalisation first."
    )
    assert counts[STATE_PENDING] + counts[STATE_ADJUDICATED] >= len(reading.records) - 5
    for record in reading.records:
        assert (record.body_path is None) == (record.decision_state == STATE_UNREADABLE)
        assert record.body != ""


@pytest.mark.skipif(not LIVE_MANIFEST.is_file(), reason="no live decisions-track manifest")
def test_the_live_bodies_carry_the_fields_the_dashboard_asked_for():
    reading = manifest_records(LIVE_MANIFEST, LIVE_STACK)
    seen = {name for record in reading.records for name in (r.name for r in record.fields)}

    assert {"unlock_count", "track", "form", "gates"} <= seen
    with_unlock = [
        record for record in reading.records
        if any(item.name == "unlock_count" for item in record.fields)
    ]
    assert len(with_unlock) > 50, "unlock_count came back near zero -- it is being derived, not read"
