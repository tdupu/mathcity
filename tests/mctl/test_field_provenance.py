"""Fields carry where they were read, and disagreements are kept.

Slice 6 reported five things off a manifest row and nothing at all off the
brief documents, which turn out to hold the fields the surfaces most need. The
consumer's requirement is not "show me `unlock_count`" but *"I want to render
which is which rather than flatten them"*: a `priority` read off a bd column
and a `priority` typed into a markdown header are different kinds of claim,
and a surface that prints both as `P1` asserts they are the same.

So every value is a reading with a `source`, a `confidence` and the exact
`field` it came from -- the same four-part shape `verdicts.Verdict` already
uses -- and where two stores disagree both are kept with `conflict` set.
Picking a winner would destroy the one fact nobody else records: that the bead
and the document do not agree.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import fields  # noqa: E402

MCTL = SCRIPTS_ROOT / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"

BRIEF = "mc-brief"
SOURCE = "mc-source"

STACK_BODY = """---
artifact: mc-source
status: open
form: full
track: brief-system
unlock_count: 6
priority: P3
gates: test-evidence N/A (decision-shaped, no runnable artifact)
---

## §1 What is being decided

Whether the brief's own document is allowed to say things the bead does not.
"""


def bead_rows(priority: int = 1) -> list[dict[str, object]]:
    return [
        {
            "id": BRIEF,
            "title": "[brief] a decision",
            "status": "open",
            "issue_type": "decision",
            "priority": priority,
            "labels": [],
            "dependencies": [{"id": SOURCE, "type": "blocks"}],
            "created_at": "2026-08-10T12:00:00Z",
            "updated_at": "2026-08-11T12:00:00Z",
        },
        {
            "id": SOURCE,
            "title": "Source work",
            "status": "open",
            "issue_type": "task",
            "labels": [],
            "created_at": "2026-08-10T12:00:00Z",
            "updated_at": "2026-08-11T12:00:00Z",
        },
    ]


def runtime(tmp_path: Path, *, stack_body: str | None = STACK_BODY, priority: int = 1):
    """A one-brief rig whose stack file is named after the bead.

    `_cached_brief_file` resolves `<brief_id>-*.md`, which is the pipeline's
    own convention -- the stack index records `source: he-a9cfa` beside
    `path: .../he-a9cfa-brief.md`.
    """
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    beads = rig_root / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "briefs" / ".pile").mkdir(parents=True)
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    if stack_body is not None:
        (beads / "briefs" / "stack" / f"{BRIEF}-brief.md").write_text(
            stack_body, encoding="utf-8"
        )
    fixture = beads / "issues.jsonl"
    fixture.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in bead_rows(priority)),
        encoding="utf-8",
    )
    return city_root, fixture


def listed(city_root: Path, fixture: Path) -> dict:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(fixture)
    result = subprocess.run(
        [
            sys.executable, str(MCTL), "briefs", "list", "--json",
            "--city", str(city_root), "--rig", "mathcity",
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    return next(item for item in payload["briefs"] if item["brief_id"] == BRIEF)


# --- a bead-backed brief reads its own document ------------------------------


def test_a_bead_record_exposes_its_stack_files_frontmatter(tmp_path: Path):
    city_root, fixture = runtime(tmp_path)

    record = listed(city_root, fixture)

    by_name = record["fields"]
    assert by_name["unlock_count"]["value"] == "6"
    assert by_name["unlock_count"]["source"] == "frontmatter"
    assert by_name["track"]["value"] == "brief-system"
    assert by_name["form"]["value"] == "full"
    assert by_name["gates"]["value"].startswith("test-evidence N/A")
    assert record["body_path"].endswith(f"{BRIEF}-brief.md")


def test_a_bead_with_no_document_reports_only_what_the_bead_holds(tmp_path: Path):
    """Absent means absent: no file, no frontmatter fields, no invented ones."""
    city_root, fixture = runtime(tmp_path, stack_body=None)

    record = listed(city_root, fixture)

    assert record["body_path"] is None
    assert set(record["fields"]) == {"priority"}
    assert record["fields"]["priority"]["source"] == "bead"


def test_a_bead_column_and_its_document_disagreeing_keeps_both(tmp_path: Path):
    """`priority: 1` on the bead against `priority: P3` in the file.

    The bead is this record's canonical store, so it leads -- and the document
    is kept beside it, flagged, because a brief whose own header contradicts
    its bead is a finding rather than a tie to break.
    """
    city_root, fixture = runtime(tmp_path, priority=1)

    priority = listed(city_root, fixture)["fields"]["priority"]

    assert priority["conflict"] is True
    assert priority["value"] == "1"
    assert priority["source"] == "bead"
    assert [(item["value"], item["source"]) for item in priority["readings"]] == [
        ("1", "bead"),
        ("P3", "frontmatter"),
    ]


def test_p_prefixed_and_bare_priorities_are_not_a_disagreement(tmp_path: Path):
    """`P3` and `3` are one claim in two spellings.

    Reporting those as a conflict would bury the real disagreements under one
    false positive per brief that has a document at all.
    """
    city_root, fixture = runtime(tmp_path, priority=3)

    priority = listed(city_root, fixture)["fields"]["priority"]

    assert priority["conflict"] is False
    assert len(priority["readings"]) == 2
    assert priority["readings"][0]["value"] == "3"
    assert priority["readings"][1]["value"] == "P3"


# --- the envelope itself -----------------------------------------------------


def test_a_field_no_store_holds_is_absent_rather_than_null():
    assert fields.reading("unlock_count") is None
    assert fields.readings_map(()) == {}


def test_a_reading_names_its_field_and_confidence():
    reading = fields.reading(
        "unlock_count",
        fields.frontmatter_value({"unlock_count": "6"}, "unlock_count"),
    )

    assert reading is not None
    assert reading.to_dict() == {
        "conflict": False,
        "name": "unlock_count",
        "readings": [
            {
                "confidence": "high",
                "field": "frontmatter.unlock_count",
                "source": "frontmatter",
                "value": "6",
            }
        ],
        "source": "frontmatter",
        "value": "6",
    }


def test_values_are_never_normalised_only_folded_for_comparison():
    reading = fields.reading(
        "form",
        fields.row_value({"form": "Compact"}, "form", field="manifest.jsonl:form"),
        fields.frontmatter_value({"form": "compact"}, "form"),
    )

    assert reading is not None
    assert reading.conflict is False
    # Case folds for the comparison; the values themselves are untouched.
    assert [item.value for item in reading.readings] == ["Compact", "compact"]


def test_an_integer_row_value_is_read_rather_than_dropped():
    """`unlock_count` is an integer on 149 live rows and a string in frontmatter."""
    value = fields.row_value({"unlock_count": 6}, "unlock_count", field="manifest.jsonl:x")

    assert value is not None
    assert value.value == "6"
    assert value.source == "manifest_row"


def test_an_absent_or_null_row_value_produces_no_reading():
    assert fields.row_value({}, "gates", field="x") is None
    assert fields.row_value({"gates": None}, "gates", field="x") is None
    assert fields.row_value({"gates": "  "}, "gates", field="x") is None
    assert fields.frontmatter_value({"gates": ""}, "gates") is None


def test_a_quoted_frontmatter_value_loses_only_its_quotes():
    value = fields.frontmatter_value({"verdict": '"approve-b (push=false)"'}, "verdict")

    assert value is not None
    assert value.value == "approve-b (push=false)"


def test_frontmatter_reading_uses_the_one_existing_parser():
    """Delegated to `materialize_plan.parse_stack_file`, not re-implemented.

    That parser is a line matcher on purpose: live files carry values a YAML
    loader rejects outright, and a strict parse drops the whole brief rather
    than one key.
    """
    parsed = fields.read_frontmatter(
        "---\nstatus: needs-revision(check-zero:partial;option-A)\nrelates: [236]\n---\n\nbody\n"
    )

    assert parsed["status"] == "needs-revision(check-zero:partial;option-A)"
    assert parsed["relates"] == "[236]"


def test_a_document_with_no_frontmatter_yields_no_fields():
    assert fields.read_frontmatter("# just a heading\n") == {}
