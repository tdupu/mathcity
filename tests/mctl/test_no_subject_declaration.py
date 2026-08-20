"""B2.1a: a brief may DECLARE that it is about no bead.

B2.1 makes a brief a `type=decision` bead with at least one source dependency,
and a brief without one raises `MBRF004`. Some briefs genuinely have no bead
subject -- a policy question, a standing-rule change, a "should we do X at
all" -- and for those, `MBRF004` is the checker asking a question that does not
apply, the same shape as the push-authorization receipts `test_brief_population`
took out of the population.

The declaration is **explicit and never inferred**, which is the whole design.
A brief that says "no bead subject" is compliant; a brief that merely omits the
field is still `MBRF004`. That asymmetry is what stops B2.1a being a no-op:
the great majority of live sourceless beads are omissions rather than
statements, most of them naming their subject in their own title or body, and
reading their silence as a declaration would relabel every one compliant and
destroy the signal that the subject is recoverable.

So these tests come in two halves. The first fixes the declaration shapes and,
just as importantly, the near-misses that must NOT be read as declarations --
unanchored matching is the defect class this queue exists to close and it has
shipped twice here. The second drives the real `doctor` path end to end.

**A note on `malformed`, because the obvious assertion is the wrong one.**
`decision_state` never consults `source_dependencies`: `_decision_state` reads
`malformed` as "closed, and no verdict could be read", which is B2.2/`MBRF005`.
`MBRF004` is B2.1 and feeds no state at all. So a correct B2.1a change moves the
`MBRF004` count and leaves the `malformed` count *exactly where it was* -- and
a change that moved `malformed` would be evidence of a second, unintended edit.
Both directions are asserted below.
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

from mctl_core.beads import _bead_from_mapping
from mctl_core.verdicts import NO_SUBJECT_LABEL, declares_no_subject

MCTL = SCRIPTS_ROOT / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"

DECLARING_LABEL = "mc-declare-label"
DECLARING_TAG = "mc-declare-tag"
DECLARING_BODY = "mc-declare-body"
OMITTING = "mc-omit"
NEAR_MISS = "mc-near-miss"
LINKED = "mc-linked"
SOURCE = "mc-source"


def bead(**overrides):
    row = {
        "id": "mc-1",
        "title": "A brief",
        "status": "open",
        "issue_type": "decision",
    }
    row.update(overrides)
    return _bead_from_mapping(row)


# --------------------------------------------------------------------------
# what IS a declaration
# --------------------------------------------------------------------------


def test_the_label_declares():
    """The most deliberate shape: it cannot be typed by accident in prose."""
    assert declares_no_subject(bead(labels=[NO_SUBJECT_LABEL])) is True


def test_the_label_declares_regardless_of_case_or_padding():
    assert declares_no_subject(bead(labels=["other", " No-Subject "])) is True


def test_the_title_tag_declares():
    assert declares_no_subject(
        bead(title="[no-subject] Should the fast-drain order stay rig-scoped?")
    ) is True


def test_a_whole_line_source_none_in_the_description_declares():
    assert declares_no_subject(
        bead(description="Should we keep B2.8's repair direction?\n\nSource: none\n")
    ) is True


def test_the_manifest_spelling_of_the_field_declares():
    """The decisions-track manifest spells it `source_bead`."""
    assert declares_no_subject(bead(description="source_bead: none")) is True


def test_the_declaration_is_read_from_notes_and_design_too():
    assert declares_no_subject(bead(notes="Source: none")) is True
    assert declares_no_subject(bead(design="Source bead: none")) is True


def test_markdown_dressing_around_the_declaration_still_declares():
    """Briefs are written by hand, in markdown."""
    for body in ("- source: none", "**Source**: none", "## Source: none", "Source: none."):
        assert declares_no_subject(bead(description=body)) is True, body


# --------------------------------------------------------------------------
# what is NOT a declaration -- the anchoring half
# --------------------------------------------------------------------------


def test_silence_is_not_a_declaration():
    """The load-bearing case. An omission must stay an omission."""
    assert declares_no_subject(bead()) is False


def test_a_sentence_describing_the_omission_is_not_a_declaration():
    """Unanchored matching would read each of these as compliance.

    Every one of them DESCRIBES a missing subject rather than declaring there
    is none -- which is exactly the population B2.1a must keep flagging.
    """
    for body in (
        "The source bead is none of the ones listed above.",
        "No source bead was found for this brief.",
        "Source: none of these apply, see the parent epic.",
        "source: none found -- needs triage",
        "I could not determine a source: none was recorded at prep time.",
    ):
        assert declares_no_subject(bead(description=body)) is False, body


def test_a_real_source_value_is_not_a_declaration():
    assert declares_no_subject(bead(description="Source: mc-3yh")) is False


def test_merely_discussing_having_no_subject_is_not_a_declaration():
    """Same discipline as `is_git_authorization_receipt`: markers, not prose."""
    assert declares_no_subject(
        bead(description="This brief arguably has no bead subject at all.")
    ) is False


def test_a_similarly_named_label_does_not_declare():
    assert declares_no_subject(bead(labels=["no-subject-yet", "subject"])) is False


# --------------------------------------------------------------------------
# end to end, through the real doctor path
# --------------------------------------------------------------------------


def beads_payload():
    stamps = {"created_at": "2026-08-01T00:00:00Z", "updated_at": "2026-08-01T00:00:00Z"}
    return [
        {
            "id": DECLARING_LABEL,
            "title": "Should the brief pipeline keep a city-root pile?",
            "status": "open",
            "issue_type": "decision",
            "labels": [NO_SUBJECT_LABEL],
            **stamps,
        },
        {
            "id": DECLARING_TAG,
            "title": "[no-subject] Retire the polytope fallback?",
            "status": "open",
            "issue_type": "decision",
            **stamps,
        },
        {
            "id": DECLARING_BODY,
            "title": "Should agents escalate on a missing escalation path?",
            "status": "open",
            "issue_type": "decision",
            "description": "A policy question about escalation.\n\nSource: none\n",
            **stamps,
        },
        {
            "id": OMITTING,
            "title": "BRIEF: fix the stack index rebuild for mc-3yh",
            "status": "open",
            "issue_type": "decision",
            "description": "This is about mc-3yh; the link was never recorded.",
            **stamps,
        },
        {
            "id": NEAR_MISS,
            "title": "BRIEF: reconcile the archive rows",
            "status": "open",
            "issue_type": "decision",
            "description": "No source bead was found for this brief.",
            **stamps,
        },
        {
            "id": LINKED,
            "title": "BRIEF: router beads",
            "status": "open",
            "issue_type": "decision",
            "dependencies": [
                {"issue_id": LINKED, "depends_on_id": SOURCE, "type": "related"}
            ],
            **stamps,
        },
        {"id": SOURCE, "title": "Source work", "status": "open", "issue_type": "task", **stamps},
    ]


def runtime(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    beads = city_root / "mathcity" / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "briefs" / ".pile").mkdir(parents=True)
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    fixture = beads / "issues.jsonl"
    fixture.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in beads_payload()),
        encoding="utf-8",
    )
    return city_root, fixture


def run_mctl(city_root: Path, fixture: Path, *args: str):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(fixture)
    return subprocess.run(
        [
            sys.executable, str(MCTL), "briefs", *args,
            "--city", str(city_root), "--rig", "mathcity", "--json",
        ],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )


def doctor_payload(city_root: Path, fixture: Path) -> dict:
    result = run_mctl(city_root, fixture, "doctor")
    assert result.stdout, result.stderr
    return json.loads(result.stdout)


def ids_for(report: dict, code: str) -> set[str]:
    return {
        d["facts"].get("brief_id")
        for d in report["diagnostics"]
        if d["code"] == code
    }


def test_a_declaring_brief_is_compliant(tmp_path: Path):
    report = doctor_payload(*runtime(tmp_path))

    blocked = ids_for(report, "MBRF004")
    assert DECLARING_LABEL not in blocked
    assert DECLARING_TAG not in blocked
    assert DECLARING_BODY not in blocked


def test_a_declaring_brief_is_still_accounted_for(tmp_path: Path):
    """Compliant is not the same as invisible.

    A bead quietly dropped from every listing is indistinguishable, to an
    operator, from a bead that was lost -- the reason the B2.1 exemptions emit
    `MBRF054`/`MBRF055` rather than vanishing. `MBRF056` is that record, INFO
    rather than ERROR so it does not block `adjudicate`.
    """
    report = doctor_payload(*runtime(tmp_path))

    declared = ids_for(report, "MBRF056")
    assert declared == {DECLARING_LABEL, DECLARING_TAG, DECLARING_BODY}

    severities = {
        d["severity"] for d in report["diagnostics"] if d["code"] == "MBRF056"
    }
    assert severities == {"INFO"}


def test_an_omitting_brief_still_raises_mbrf004(tmp_path: Path):
    """Silence must not become compliance."""
    report = doctor_payload(*runtime(tmp_path))

    assert OMITTING in ids_for(report, "MBRF004")


def test_a_brief_that_only_describes_its_omission_still_raises_mbrf004(tmp_path: Path):
    """The anchoring case, end to end rather than as a unit test."""
    report = doctor_payload(*runtime(tmp_path))

    assert NEAR_MISS in ids_for(report, "MBRF004")


def test_the_mbrf004_population_moves_by_exactly_the_declaring_briefs(tmp_path: Path):
    """Three declare, two omit, one is linked. Only the three may move.

    "and no more" is the assertion that matters: a discriminator that is too
    wide takes the omissions with it, and they are the population B2.1a is
    supposed to leave alone.
    """
    report = doctor_payload(*runtime(tmp_path))

    assert ids_for(report, "MBRF004") == {OMITTING, NEAR_MISS}


def test_the_malformed_count_does_not_move(tmp_path: Path):
    """`malformed` is B2.2, not B2.1 -- see this module's docstring.

    `_decision_state` reads `malformed` as "closed, and no verdict could be
    read" and never looks at `source_dependencies`. Every brief in this fixture
    is open, so none is malformed, before the change or after. If this ever
    starts failing, a B2.1a edit has reached B2.2's discriminator.
    """
    city_root, fixture = runtime(tmp_path)
    result = run_mctl(city_root, fixture, "list")
    assert result.stdout, result.stderr
    briefs = json.loads(result.stdout)["briefs"]

    states = {b["brief_id"]: b["decision_state"] for b in briefs}
    assert "malformed" not in states.values(), states
