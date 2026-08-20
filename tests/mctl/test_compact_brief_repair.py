"""B1.3 shape repair: ungated compact briefs become full form, and say so.

The defect (GitHub #74, bead `mc-0ka`): POLICY B1.3 allows compact form ONLY
for a brief the no-brainer classifier cleared. Measured 2026-08-19 and
re-measured 2026-08-20 against the live stack, 19 of 89 briefs are `form:
compact` and 18 of those carry no `no_brainer_classification` at all.

The constraint that shapes the tool, and every test below:

    Rejection -- a verdict on the brief's content -- belongs to the owner and
    may NOT be automated.  Repair -- a shape change that leaves the decision
    intact -- belongs to the contract and may be.

So the repair never writes a verdict, never closes a brief, and never removes
one. It changes `form:` and appends the sections the compact shape had no slot
for, marked NOT SUPPLIED rather than filled in.

And a *silent* repair would destroy the producer signal exactly as an
auto-reject would: nothing would afterwards record that a producer keeps filing
ungated compact briefs. That is why the recording tests here are not
bookkeeping tests -- they are the tests that make the automation permissible.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
REPAIR_TOOL = REPO_ROOT / "assets" / "scripts" / "brief-compact-repair.py"

COMPACT_BODY = """
## §1 What is being decided

DECISION:  Will the pool be raised?
CONTEXT:   It is low.
RECOMMEND: APPROVE.
CONFIRM:   y / n / grill-me-further
"""


def run_repair(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REPAIR_TOOL), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def report_of(result: subprocess.CompletedProcess[str]) -> dict:
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def write_brief(stack: Path, name: str, frontmatter: str, body: str = COMPACT_BODY) -> Path:
    path = stack / name
    path.write_text("---\n" + frontmatter.strip() + "\n---\n" + body)
    return path


def frontmatter_of(path: Path) -> dict[str, str]:
    text = path.read_text()
    block = text.split("\n---", 1)[0][4:]
    out: dict[str, str] = {}
    for line in block.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip()
    return out


@pytest.fixture
def brief_root(tmp_path: Path) -> Path:
    root = tmp_path / ".beads" / "briefs"
    (root / "stack").mkdir(parents=True)
    return root


@pytest.fixture
def stack(brief_root: Path) -> Path:
    return brief_root / "stack"


UNGATED = "artifact: none\nstatus: ready-for-adjudication\nform: compact\ntrack: pack-hygiene"


# --- selection ------------------------------------------------------------


def test_an_ungated_compact_brief_is_selected(brief_root, stack):
    write_brief(stack, "01-ungated-brief.md", UNGATED)
    report = report_of(run_repair("--brief-root", str(brief_root)))
    assert [r["file"] for r in report["repaired"]] == ["01-ungated-brief.md"]


def test_a_compliant_compact_brief_is_left_alone(brief_root, stack):
    """gh-38's live shape: compact, but classified. B1.3 permits it."""
    path = write_brief(
        stack,
        "gh-38-brief.md",
        "artifact: gh-issue-38\nstatus: present-it-pending\nform: compact\n"
        "no_brainer_classification: close-done-cited-commit\nno_brainer_confidence: 0.95",
    )
    before = path.read_bytes()
    report = report_of(run_repair("--brief-root", str(brief_root), "--apply"))
    assert report["repaired"] == []
    assert [s["reason"] for s in report["skipped"]] == ["classified"]
    assert path.read_bytes() == before


@pytest.mark.parametrize(
    "status",
    ["approved", "approved-slung", "adjudicated", "mixed-partial", "needs-revision(x:y)", "deferred"],
)
def test_an_already_disposed_brief_is_skipped(brief_root, stack, status):
    """The owner's instruction is "repair unless they are already closed"."""
    path = write_brief(stack, "02-done-brief.md", f"status: {status}\nform: compact\ntrack: t")
    before = path.read_bytes()
    report = report_of(run_repair("--brief-root", str(brief_root), "--apply"))
    assert report["repaired"] == []
    assert [s["reason"] for s in report["skipped"]] == ["already-disposed"]
    assert path.read_bytes() == before


def test_ready_for_adjudication_is_not_read_as_disposed(brief_root, stack):
    """`ready-for-adjudication` is the opposite of adjudicated.

    Reading it as a disposition is how an earlier count reached 58 instead of
    35, and here it would silently skip 7 of the 13 repairable briefs.
    """
    write_brief(stack, "100-ready-brief.md", UNGATED)
    report = report_of(run_repair("--brief-root", str(brief_root)))
    assert len(report["repaired"]) == 1


def test_a_full_form_brief_is_untouched(brief_root, stack):
    path = write_brief(stack, "03-full-brief.md", "status: ready\nform: full\ntrack: t")
    before = path.read_bytes()
    report = report_of(run_repair("--brief-root", str(brief_root), "--apply"))
    assert report["repaired"] == []
    assert path.read_bytes() == before


def test_a_brief_with_no_form_key_is_untouched(brief_root, stack):
    """35 of the 39 no-`form` briefs are full-shaped; none is a B1.3 case.

    Absent means absent: the tool does not backfill `form:` on a brief that
    never declared one, because that would assert a producer claim nobody made.
    """
    path = write_brief(stack, "04-noform-brief.md", "status: ready\ntrack: t")
    before = path.read_bytes()
    report = report_of(run_repair("--brief-root", str(brief_root), "--apply"))
    assert report["repaired"] == []
    assert path.read_bytes() == before


def test_a_test_only_canary_is_skipped(brief_root, stack):
    path = write_brief(stack, "0000-canary.md", "status: ready\nform: compact\ntest_only: true")
    before = path.read_bytes()
    report = report_of(run_repair("--brief-root", str(brief_root), "--apply"))
    assert report["repaired"] == []
    assert [s["reason"] for s in report["skipped"]] == ["test-only-canary"]
    assert path.read_bytes() == before


# --- dry run --------------------------------------------------------------


def test_dry_run_is_the_default_and_writes_nothing(brief_root, stack):
    path = write_brief(stack, "01-ungated-brief.md", UNGATED)
    before = path.read_bytes()
    report = report_of(run_repair("--brief-root", str(brief_root)))
    assert report["apply"] is False
    assert len(report["repaired"]) == 1
    assert path.read_bytes() == before


def test_dry_run_reports_the_diff_it_would_make(brief_root, stack):
    write_brief(stack, "01-ungated-brief.md", UNGATED)
    entry = report_of(run_repair("--brief-root", str(brief_root)))["repaired"][0]
    assert entry["form_before"] == "compact"
    assert entry["form_after"] == "full"
    assert entry["sections_present_before"] == [1]
    assert entry["sections_appended"] == [2, 3, 4, 5, 6, 7]


# --- the repair itself ----------------------------------------------------


def test_repair_sets_form_to_full(brief_root, stack):
    path = write_brief(stack, "01-ungated-brief.md", UNGATED)
    run_repair("--brief-root", str(brief_root), "--apply")
    assert frontmatter_of(path)["form"] == "full"


def test_repair_preserves_every_arriving_frontmatter_key_and_its_order(brief_root, stack):
    path = write_brief(
        stack,
        "01-ungated-brief.md",
        "artifact: none (blocks gt-g2e + brief 04)\nstatus: present-it-pending\n"
        "form: compact\ntrack: decisions-to-briefs\nshape: external-reminder\n"
        "gates: test-evidence N/A (decision-shaped, no runnable artifact)\nunlock_count: 1",
    )
    before = frontmatter_of(path)
    run_repair("--brief-root", str(brief_root), "--apply")
    after = frontmatter_of(path)

    # Every arriving key survives with its arriving value -- `form` excepted,
    # which is the one field the repair exists to change.
    for key, value in before.items():
        assert key in after, key
        if key != "form":
            assert after[key] == value, key
    # ...and in the order it arrived in.
    assert list(after)[: len(before)] == list(before)


def test_repair_preserves_the_arriving_body_verbatim(brief_root, stack):
    body = COMPACT_BODY + "\n```yaml\naction_block:\n  on_defer: [{type: snooze}]\n```\n"
    path = write_brief(stack, "01-ungated-brief.md", UNGATED, body)
    run_repair("--brief-root", str(brief_root), "--apply")
    assert body in path.read_text()


def test_repair_never_removes_the_file(brief_root, stack):
    write_brief(stack, "01-ungated-brief.md", UNGATED)
    run_repair("--brief-root", str(brief_root), "--apply")
    assert [p.name for p in stack.glob("*.md")] == ["01-ungated-brief.md"]


def test_repair_records_no_verdict_and_does_not_change_status(brief_root, stack):
    """Repair is not rejection. The brief still needs the owner's verdict."""
    path = write_brief(stack, "01-ungated-brief.md", UNGATED)
    run_repair("--brief-root", str(brief_root), "--apply")
    after = frontmatter_of(path)
    assert after["status"] == "ready-for-adjudication"
    assert "verdict" not in after
    assert "adjudicated_at" not in after
    assert "adjudicated_by" not in after


def test_missing_sections_are_marked_absent_not_filled_in(brief_root, stack):
    path = write_brief(stack, "01-ungated-brief.md", UNGATED)
    run_repair("--brief-root", str(brief_root), "--apply")
    text = path.read_text()
    for heading in ("§3 Assumptions", "§4 Alternatives", "§5 Risks", "§6 Evidence"):
        assert heading in text
    assert text.count("NOT SUPPLIED") >= 6


def test_a_section_the_producer_did_supply_is_not_re_emitted(brief_root, stack):
    """Live brief 47 arrived compact but already carried §1 and §2."""
    body = "\n## §1 What is being decided\n\nq?\n\n## §2 Recommended answer\n\nCONFIGURABLE.\n"
    path = write_brief(stack, "47-sandbox-brief.md", UNGATED, body)
    report = report_of(run_repair("--brief-root", str(brief_root), "--apply"))
    assert report["repaired"][0]["sections_appended"] == [3, 4, 5, 6, 7]
    assert path.read_text().count("§2 Recommended answer") == 1


def test_a_body_with_no_section_heading_gets_the_decision_at_top_heading(brief_root, stack):
    """B1.1: the first content after the header MUST be the decision.

    Live briefs 100/104/105 arrived with a bare `DECISION:` block and no
    heading at all. The heading goes in above the arriving block, so the
    invariant holds without a word of the prose changing.
    """
    body = "\nDECISION:  Packify the timeouts?\nCONTEXT:   x\nRECOMMEND: yes\n"
    path = write_brief(stack, "104-city-toml-brief.md", UNGATED, body)
    run_repair("--brief-root", str(brief_root), "--apply")
    text = path.read_text()
    assert "## §1 What is being decided" in text
    assert text.index("§1 What is being decided") < text.index("DECISION:")


# --- the repair record ----------------------------------------------------


def test_the_repair_is_recorded_on_the_brief(brief_root, stack):
    path = write_brief(stack, "01-ungated-brief.md", UNGATED)
    run_repair("--brief-root", str(brief_root), "--apply")
    after = frontmatter_of(path)
    assert after["arrived_form"] == "compact"
    assert after["repair_reason"] == "B1.3-compact-without-no-brainer-classification"
    assert after["repaired_by"] == "brief-compact-repair.v1"
    assert after["repaired_at"].endswith("Z")


def test_the_repair_reason_is_a_token_not_free_text(brief_root, stack):
    """Aggregatable, by the same argument as verdict-source provenance."""
    write_brief(stack, "01-ungated-brief.md", UNGATED)
    path = write_brief(stack, "02-ungated-brief.md", UNGATED)
    run_repair("--brief-root", str(brief_root), "--apply")
    reason = frontmatter_of(path)["repair_reason"]
    assert " " not in reason
    assert reason == frontmatter_of(stack / "01-ungated-brief.md")["repair_reason"]


def test_the_recorded_repair_is_countable_afterwards(brief_root, stack):
    for name in ("01-a-brief.md", "02-b-brief.md", "03-c-brief.md"):
        write_brief(stack, name, UNGATED)
    write_brief(stack, "04-clean-brief.md", "status: ready\nform: full\ntrack: pack-hygiene")
    run_repair("--brief-root", str(brief_root), "--apply")
    repaired = [p for p in stack.glob("*.md") if "arrived_form: compact" in p.read_text()]
    assert len(repaired) == 3


def test_producer_attribution_survives_the_repair(brief_root, stack):
    """`track` is the producing lane, and it is what the 18 actually carry.

    None of the live 18 has a `deposited_by`, so the lane is the only producer
    axis there is to preserve -- and "this lane files ungated compact briefs"
    has to stay countable, or the automation destroys the signal it was
    permitted in order to keep.
    """
    write_brief(stack, "01-a-brief.md", UNGATED)
    write_brief(stack, "02-b-brief.md", "status: ready\nform: compact\ntrack: decisions-to-briefs")
    run_repair("--brief-root", str(brief_root), "--apply")
    tracks = sorted(
        frontmatter_of(p)["track"]
        for p in stack.glob("*.md")
        if "arrived_form: compact" in p.read_text()
    )
    assert tracks == ["decisions-to-briefs", "pack-hygiene"]


def test_a_producer_field_that_never_arrived_is_not_invented(brief_root, stack):
    path = write_brief(stack, "01-ungated-brief.md", UNGATED)
    run_repair("--brief-root", str(brief_root), "--apply")
    assert "deposited_by" not in frontmatter_of(path)


def test_the_report_counts_the_repair_by_producer_lane(brief_root, stack):
    write_brief(stack, "01-a-brief.md", UNGATED)
    write_brief(stack, "02-b-brief.md", UNGATED)
    write_brief(stack, "03-c-brief.md", "status: ready\nform: compact\ntrack: decisions-to-briefs")
    report = report_of(run_repair("--brief-root", str(brief_root)))
    assert report["repaired_by_track"] == {"decisions-to-briefs": 1, "pack-hygiene": 2}


# --- idempotence ----------------------------------------------------------


def test_the_repair_is_idempotent(brief_root, stack):
    path = write_brief(stack, "01-ungated-brief.md", UNGATED)
    run_repair("--brief-root", str(brief_root), "--apply")
    once = path.read_bytes()
    second = report_of(run_repair("--brief-root", str(brief_root), "--apply"))
    assert second["repaired"] == []
    assert path.read_bytes() == once


def test_a_brief_already_carrying_a_repair_record_is_never_repaired_twice(brief_root, stack):
    """Belt and braces: `form: full` already de-selects it, but a hand-edit
    that put `compact` back must not stack a second scaffold on the first."""
    path = write_brief(
        stack,
        "01-ungated-brief.md",
        UNGATED + "\narrived_form: compact\nrepaired_by: brief-compact-repair.v1",
    )
    before = path.read_bytes()
    report = report_of(run_repair("--brief-root", str(brief_root), "--apply"))
    assert [s["reason"] for s in report["skipped"]] == ["already-repaired"]
    assert path.read_bytes() == before
