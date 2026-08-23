"""#169: `briefs_create` accepted a brief with no structure and called it success.

The body was bound, checked non-empty, and returned verbatim. It was never
parsed. A one-character body produced a valid EffectPlan.

The check ALREADY EXISTS -- `brief-check.sh pile-entry` rejects a pile entry
lacking Gate Evidence -- but it runs at shuffle time, against an author who has
already been told the operation succeeded. That is the CT13.4 shape: the refusal
happens where nobody can act on it. #96 measured the consequence: the pile
drained 5 -> 0 entirely by auto-reject, one casualty being `missing Gate
Evidence section`. Every one of those was a success at creation.

ONE RULE, ONE PLACE. The issue's candidate 2 is right that two independently
written structural checkers will drift -- that is what #35 was about. But the
rule is currently triplicated INSIDE brief-check.sh itself (lines 293, 300, 331),
so "reuse the existing rule" first requires there to be one. It now lives in
assets/brief-pipeline/required-sections.toml and Python reads it from there.

brief-check.sh still carries its three copies. Collapsing them to read the same
file is a follow-up with a wider blast radius (the shell checker gates the live
drain); this change deliberately does NOT touch it, and adds a test that fails
the day the two disagree.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_briefs_create_validate_cli import (  # noqa: E402
    REPO_ROOT, beads_fixture, body_file, brief_command, run_mctl, runtime_fixture,
)

BODY_WITH_EVIDENCE = """## What is being decided

Whether to adopt X.

## Gate Evidence

G5: n/a -- no server surface touched.
"""

BODY_WITHOUT_EVIDENCE = """## What is being decided

Whether to adopt X.
"""


def create(tmp_path: Path, body: str, *extra: str):
    city_root, rig_root = runtime_fixture(tmp_path)
    bf = tmp_path / "body.md"
    bf.write_text(body, encoding="utf-8")
    return run_mctl(
        *brief_command(
            city_root, "create", "--title", "structural probe",
            "--body-file", str(bf), "--source", "mc-source", *extra, "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )


def test_a_body_with_no_gate_evidence_is_REFUSED(tmp_path: Path):
    """The defect. This body was accepted and written before this change."""
    r = create(tmp_path, BODY_WITHOUT_EVIDENCE, "--dry-run")
    assert r.returncode != 0, "a brief with no Gate Evidence must be refused"
    assert "MBRF036" in r.stderr, r.stderr


def test_the_SAME_call_SUCCEEDS_once_the_section_is_supplied(tmp_path: Path):
    """The positive control the issue requires (P6.2).

    Without this, a checker that refused everything would pass the test above.
    #104 records seven instances of a check that could not have failed.
    """
    r = create(tmp_path, BODY_WITH_EVIDENCE, "--dry-run")
    assert r.returncode == 0, r.stderr
    assert "MBRF036" not in r.stderr


def test_a_one_character_body_is_REFUSED(tmp_path: Path):
    """The issue's literal MRE: body="x" returned a valid EffectPlan."""
    r = create(tmp_path, "x", "--dry-run")
    assert r.returncode != 0
    assert "MBRF036" in r.stderr


def test_the_refusal_names_the_missing_section_and_a_remedy(tmp_path: Path):
    """CT13.4: a refusal the author cannot act on is a wall."""
    r = create(tmp_path, BODY_WITHOUT_EVIDENCE, "--dry-run")
    assert "Gate Evidence" in r.stderr, "must name WHAT is missing"
    # `suggested_next_command`, not the `remedy:` label -- that one is the
    # effects.py workaround for #183. briefs.py's own _diagnostic puts the field
    # into facts, so it renders here. TWO helpers, two behaviours, one field:
    # more evidence for #183 rather than a reason to rename anything.
    assert "suggested_next_command:" in r.stderr, "must say what to do"
    assert "add a '## Gate Evidence' section" in r.stderr


def test_the_python_rule_and_the_shell_rule_agree(tmp_path: Path):
    """Drift guard. brief-check.sh still carries its own copies of this rule.

    This fails the day the shell checker and the creation gate disagree about
    what counts as a Gate Evidence heading -- which is exactly the drift #35 was
    filed about and candidate 2 was chosen to prevent.
    """
    import tomllib
    from mctl_core import structure  # noqa: E402

    shell = (REPO_ROOT / "assets" / "scripts" / "checks" / "brief-check.sh").read_text()
    for section in structure.required_sections():
        assert section["match"] in shell, (
            f"brief-check.sh no longer contains the pattern for {section['name']!r}; "
            "the creation gate and the drain gate have drifted"
        )
