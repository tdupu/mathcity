"""The beadless-brief materialisation planner.

The planner exists to be read before anything is written, so the tests that
matter most are the ones asserting it *cannot* write: no subprocess import, no
mutating `bd` verb reachable from either file. The rest pin the readings that a
previous pass got wrong -- `ready-for-adjudication` is not a disposition, and a
prefix absent from `rigs.json` is not an unknown rig.
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import materialize_plan as plan  # noqa: E402
from mctl_core.beads import _bead_from_mapping  # noqa: E402
from mctl_core.verdicts import (  # noqa: E402
    CONFIDENCE_HIGH,
    SOURCE_NOTES,
    read_verdict_reading,
)

PLANNER_SOURCE = (SCRIPTS_ROOT / "mctl_core" / "materialize_plan.py").read_text(encoding="utf-8")
CLI_SOURCE = (SCRIPTS_ROOT / "plan_beadless_briefs.py").read_text(encoding="utf-8")

INDEX = {
    "he-xkm7u": {"id": "he-xkm7u", "issue_type": "task", "status": "open"},
    "gsp-0bf29": {"id": "gsp-0bf29", "issue_type": "feature", "status": "open"},
    "gsp-99s6": {"id": "gsp-99s6", "issue_type": "task", "status": "closed"},
    "gt-1fne2g": {"id": "gt-1fne2g", "issue_type": "bug", "status": "open"},
    "tgi-d1k": {"id": "tgi-d1k", "issue_type": "task", "status": "open"},
    "gs-0hd8": {"id": "gs-0hd8", "issue_type": "decision", "status": "open"},
}


def row_for(text: str, name: str = "demo-brief.md") -> plan.PlanRow:
    return plan.build_row(plan.parse_stack_file(name, text), INDEX)


def frontmatter(**fields: str) -> str:
    body = "\n".join(f"{key.replace('__', '.')}: {value}" for key, value in fields.items())
    return f"---\n{body}\n---\n\n## §1 What is being decided\n\nsomething\n"


# --------------------------------------------------------------------------
# read-only by construction
# --------------------------------------------------------------------------


def _imported_modules(source: str) -> set[str]:
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            names.add(node.module or "")
    return names


def _called_names(source: str) -> set[str]:
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name):
            names.add(func.id)
        elif isinstance(func, ast.Attribute):
            names.add(func.attr)
    return names


def _string_constants(source: str) -> set[str]:
    return {
        node.value
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_planner_imports_no_subprocess_or_shell():
    """Parsed imports, not a grep: the module cannot reach a shell at all."""
    assert _imported_modules(PLANNER_SOURCE) & {"subprocess", "os", "sys", "pty", "shutil"} == set()


def test_planner_never_imports_the_bead_write_path():
    """`mctl_core.beads` carries create/update; the planner must not reach it."""
    assert not any(
        module.endswith("beads") for module in _imported_modules(PLANNER_SOURCE)
    )


def test_planner_calls_nothing_that_writes():
    banned = {"open", "write", "write_text", "write_bytes", "mkdir", "run", "system", "popen"}
    assert _called_names(PLANNER_SOURCE) & banned == set()


def test_cli_only_ever_asks_bd_to_list():
    """The CLI's single subprocess argv is the frozen read-only constant."""
    import plan_beadless_briefs as cli

    assert cli.BD_READ_ARGV[:2] == ("bd", "list")
    mutating = {"create", "close", "update", "delete", "dep", "import", "compact", "sync"}
    assert _string_constants(CLI_SOURCE) & mutating == set()


# --------------------------------------------------------------------------
# artifact parsing
# --------------------------------------------------------------------------


def test_none_and_decorated_none_yield_no_source():
    assert plan.artifact_ids("none") == ()
    assert plan.artifact_ids("none (blocks gt-g2e + brief 04)") == ()


def test_non_bead_artifacts_yield_no_source():
    assert plan.artifact_ids("gh-issue-335") == ()
    assert plan.artifact_ids("f4f72ed") == ()
    assert plan.artifact_ids("72-skill-invocation-contract-policy-skills-brief.md") == ()


def test_multiple_ids_are_kept_in_order_and_deduplicated():
    assert plan.artifact_ids("gsp-0s20, gsp-99s6, gsp-0s20") == ("gsp-0s20", "gsp-99s6")


def test_every_live_store_prefix_is_known():
    """`tgi`, `lm`, `ja`, `ho`, `gt`, `gsp`, `gs` are real rigs, not junk."""
    for prefix in ("tgi", "lm", "ja", "ho", "gt", "gsp", "gs", "mc", "cp2"):
        assert prefix in plan.STORE_BY_PREFIX


# --------------------------------------------------------------------------
# target store: the cross-rig question
# --------------------------------------------------------------------------


def test_brief_bead_targets_the_store_its_artifact_lives_in():
    row = row_for(frontmatter(artifact="he-xkm7u", status="ready-for-adjudication"))
    assert row.target_store == "hecke"
    assert plan.CLASS_CROSS_RIG not in row.problem_classes


def test_unresolved_artifact_falls_back_to_hq_with_no_source_link():
    row = row_for(frontmatter(artifact="none", status="ready"))
    assert row.target_store == plan.TARGET_STORE_FALLBACK == "gt"
    assert row.resolved_ids == ()
    assert plan.CLASS_UNRESOLVED in row.problem_classes
    assert plan.UNRESOLVED_KEY in plan.metadata_for(row)


def test_a_source_link_is_never_invented_for_an_unresolved_artifact():
    row = row_for(frontmatter(artifact="gh-issue-335", status="ready"))
    assert all("--deps" not in line for line in plan.commands_for(row))


# --------------------------------------------------------------------------
# verdict tiers
# --------------------------------------------------------------------------


def test_ready_for_adjudication_is_not_a_disposition():
    row = row_for(frontmatter(artifact="he-xkm7u", status="ready-for-adjudication"))
    assert row.tier == plan.TIER_OPEN
    assert row.status == "open"


def test_complete_b22_fields_plan_a_closed_bead():
    row = row_for(
        frontmatter(
            artifact="tgi-d1k",
            status="adjudicated",
            verdict="APPROVE",
            adjudicated_by='"Taylor (Q18)"',
            adjudicated_at="2026-07-18",
        )
    )
    assert row.tier == plan.TIER_ADJUDICATED
    assert row.status == "closed"
    assert row.verdict_authorizer == "Taylor (Q18)"


def test_claimed_disposition_without_authorizer_stays_open():
    row = row_for(frontmatter(artifact="he-xkm7u", status="adjudicated"))
    assert row.tier == plan.TIER_CLAIMED
    assert row.status == "open"


def test_tier_a_notes_round_trip_through_the_existing_verdict_adapter():
    """The plan reuses `verdicts.py`'s reader rather than inventing a format."""
    row = row_for(
        frontmatter(
            artifact="tgi-d1k",
            status="adjudicated",
            verdict="APPROVE",
            adjudicated_by="Taylor",
            adjudicated_at="2026-07-18",
            verdict_note="ship it",
        )
    )
    bead = _bead_from_mapping(
        {
            "id": "tgi-new",
            "title": row.title,
            "issue_type": "decision",
            "status": "closed",
            "notes": plan.notes_for(row),
        }
    )
    reading = read_verdict_reading(bead)
    assert reading.resolved
    assert reading.verdict.text == "APPROVE"
    assert reading.verdict.source == SOURCE_NOTES
    assert reading.verdict.confidence == CONFIDENCE_HIGH


def test_tier_b_notes_are_not_readable_as_a_verdict():
    """A claimed disposition must not become an asserted adjudication."""
    row = row_for(frontmatter(artifact="he-xkm7u", status="adjudicated", verdict="APPROVE"))
    bead = _bead_from_mapping(
        {
            "id": "he-new",
            "title": row.title,
            "issue_type": "decision",
            "status": "open",
            "notes": plan.notes_for(row),
        }
    )
    assert read_verdict_reading(bead).verdict is None


# --------------------------------------------------------------------------
# idempotency, duplicates, reversal
# --------------------------------------------------------------------------


def test_idempotency_key_is_not_the_formula_owned_slug_key():
    """`gc.brief.slug` is already on 826 live beads; reusing it would
    make a re-run skip files that were never materialised."""
    assert plan.STACK_FILE_KEY != "gc.brief.slug"
    assert "gc.brief.slug" not in plan.metadata_for(row_for(frontmatter(artifact="none")))


def test_every_planned_bead_carries_the_stack_filename_and_batch_marker():
    row = row_for(frontmatter(artifact="he-xkm7u"), name="he-xkm7u-335-repair.md")
    metadata = plan.metadata_for(row)
    assert metadata[plan.STACK_FILE_KEY] == "he-xkm7u-335-repair.md"
    assert metadata[plan.MATERIALIZED_KEY] == plan.MATERIALIZED_VALUE


def test_a_file_naming_an_existing_bead_is_planned_as_skip():
    row = row_for(frontmatter(artifact="none", brief_bead="gs-0hd8"))
    assert row.existing_bead == "gs-0hd8"
    assert row.action == "SKIP"
    assert plan.CLASS_DUPLICATE in row.problem_classes
    assert plan.commands_for(row)[0].startswith("# SKIP")


def test_an_existing_decision_bead_naming_the_artifact_puts_the_row_on_hold():
    """`sandbox-shell-commands-in-steps.md` and `he-tbmq0` are this shape live."""
    index = dict(INDEX)
    index["he-tbmq0"] = {
        "id": "he-tbmq0",
        "issue_type": "decision",
        "status": "open",
        "title": "gsp-0bf29: omit scope-audit step; follow bmad patterns",
    }
    row = plan.build_row(
        plan.parse_stack_file("sandbox.md", frontmatter(artifact="gsp-0bf29")), index
    )
    assert row.collisions == ("he-tbmq0",)
    assert row.action == "HOLD"
    assert plan.CLASS_COLLISION in row.problem_classes
    assert plan.commands_for(row)[0].startswith("# HOLD")


def test_a_non_decision_bead_with_the_same_title_text_is_not_a_collision():
    index = dict(INDEX)
    index["he-zzzz"] = {
        "id": "he-zzzz",
        "issue_type": "task",
        "status": "open",
        "title": "gsp-0bf29: implement the thing",
    }
    row = plan.build_row(
        plan.parse_stack_file("x.md", frontmatter(artifact="gsp-0bf29")), index
    )
    assert row.collisions == ()
    assert row.action == "CREATE"


def test_a_stale_existing_bead_pointer_does_not_suppress_creation():
    row = row_for(frontmatter(artifact="none", brief_bead="zz-nosuchbead"))
    assert row.existing_bead is None
    assert row.action == "CREATE"


def test_rollback_names_the_single_batch_marker():
    rows = [row_for(frontmatter(artifact="he-xkm7u")), row_for(frontmatter(artifact="none"))]
    lines = plan.rollback_commands(rows)
    assert lines
    assert all(plan.MATERIALIZED_VALUE in line for line in lines)
    assert all("delete --force" in line for line in lines)


# --------------------------------------------------------------------------
# emitted commands
# --------------------------------------------------------------------------


def test_source_links_use_create_deps_never_dep_add():
    """`bd dep add <local> <foreign>` exits 0 and stores an invisible edge."""
    row = row_for(frontmatter(artifact="gsp-0bf29"))
    lines = plan.commands_for(row)
    assert any("--deps gsp-0bf29" in line for line in lines)
    assert all("dep add" not in line for line in lines)


def test_closed_rows_emit_a_close_line_and_open_rows_do_not():
    closed = row_for(
        frontmatter(
            artifact="tgi-d1k", status="adjudicated", verdict="APPROVE",
            adjudicated_by="Taylor", adjudicated_at="2026-07-18",
        )
    )
    assert any(" close " in line for line in plan.commands_for(closed))
    open_row = row_for(frontmatter(artifact="tgi-d1k", status="ready"))
    assert all(" close " not in line for line in plan.commands_for(open_row))


def test_commands_are_shell_quoted():
    row = row_for(frontmatter(artifact="he-xkm7u"), name="a b's brief.md")
    assert "'" in plan.commands_for(row)[0]


def test_summary_recomputes_from_rows():
    rows = [
        row_for(frontmatter(artifact="he-xkm7u")),
        row_for(frontmatter(artifact="none")),
        row_for(frontmatter(artifact="none", brief_bead="gs-0hd8")),
    ]
    summary = plan.summarise(rows)
    assert summary["files"] == 3
    assert summary["skip"] == 1
    assert summary["create"] == 2
    assert summary["hold"] == 0
    assert summary["cross_rig"] == 0


def test_titles_come_from_the_slug_not_the_body():
    """81 of 89 live files open with the same `§1 What is being decided`."""
    row = row_for(frontmatter(artifact="he-xkm7u"), name="he-xkm7u-335-repair-brief.md")
    assert row.title == "[brief] he xkm7u 335 repair"
