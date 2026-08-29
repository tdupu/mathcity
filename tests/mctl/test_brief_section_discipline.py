"""G17 (`mc-qbs6j`): headings that exist are not headings that work.

`mc-67snh` carried every mandated heading — §1 through §7 plus `### Gate
Evidence` — so `missing_sections` (#169) passed it. It still hid its findings:

    graphroute.go:562-588  ->  filed under `## §1 — What is being decided`
    runtime.go:297         ->  filed under §1
    #2763, twice           ->  filed under §1
    ~35, "24 of 25"        ->  filed under §1
    kindsets.go:113-118    ->  filed under the SECOND `## §4`

It was adjudicated REVISE at 18:16:09Z, reason "We need evidence. We need a
recommendation." Both were present and both were misfiled. Nine minutes later
`mc-wg331` approved one of the directions `mc-67snh` was still deciding; that
approval was refuted at source and rejected, at a cost of about an hour.

P6.2 AT CONSTRUCTION. Every condition here has an OBSERVED failing case and an
OBSERVED passing case, and both are real artifacts checked into
`fixtures/section_discipline/`: `mc-67snh` exactly as filed (6022 chars, the
failing case for all three conditions) and live stack brief 246 (4051 chars,
the passing case). A synthetic body proves the regex compiles; a real brief
proves the gate would have caught the thing it was built for.
"""
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from mctl_core.briefs import parse_brief_sections  # noqa: E402
from mctl_core.decisions import brief_body  # noqa: E402
from mctl_core.structure import (  # noqa: E402
    discipline_rules,
    section_discipline_violations,
)
from test_briefs_create_validate_cli import (  # noqa: E402
    beads_fixture,
    brief_command,
    run_mctl,
    runtime_fixture,
)

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "section_discipline"
AS_FILED = FIXTURES / "mc-67snh-as-filed.md"
LIVE_PASSING = FIXTURES / "246-stale-work-claim-starvation-brief.md"


def violations(body: str):
    return section_discipline_violations(parse_brief_sections(body))


def conditions(body: str) -> set[str]:
    return {v.condition for v in violations(body)}


# --- the negative half: the real brief, exactly as filed ---------------------


def test_mc_67snh_as_filed_fails_all_three_conditions():
    """The whole reason the gate exists. Not a fixture — the artifact."""
    assert conditions(AS_FILED.read_text(encoding="utf-8")) == {"C1", "C2", "C3"}


def test_C1_names_the_evidence_it_found_in_section_one():
    """A refusal the author cannot act on is a wall (CT13.4)."""
    found = [v for v in violations(AS_FILED.read_text(encoding="utf-8")) if v.condition == "C1"]
    detail = " ".join(v.detail for v in found)
    assert "runtime.go:297" in detail
    assert "graphroute.go:562-588" in detail
    assert "#2763" in detail
    assert all("§6" in v.remedy for v in found), "must say where the evidence belongs"


def test_C2_names_both_duplicate_headings():
    found = [v for v in violations(AS_FILED.read_text(encoding="utf-8")) if v.condition == "C2"]
    assert len(found) == 1
    assert "§4 — Alternatives named" in found[0].detail
    assert "§4 — Options" in found[0].detail


def test_C3_catches_a_section_two_that_is_not_empty_but_answers_nothing():
    """Taylor's REVISE said "we need a recommendation" about a NON-EMPTY §2.

    A present-and-non-empty test would have passed this brief, which is why the
    condition is "names a decision verb and does not open with a null answer".
    """
    body = AS_FILED.read_text(encoding="utf-8")
    section_two = [s for s in parse_brief_sections(body) if s.section_index == 2][0]
    assert section_two.body.strip(), "the §2 this test is about is NOT empty"
    found = [v for v in violations(body) if v.condition == "C3"]
    assert len(found) == 1
    assert "None recorded" in found[0].detail


# --- the positive half: a real brief that passes ----------------------------


def test_a_live_stack_brief_passes_clean():
    """P6.2's mirror: a diagnostic that cannot pass is as bad as one that
    cannot fail. This is an unmodified brief off the live stack."""
    assert violations(LIVE_PASSING.read_text(encoding="utf-8")) == []


def test_compact_form_bodies_are_out_of_scope_rather_than_failed():
    """59 of the 178 live brief files carry no numbered sections at all.

    Reporting three violations on each would make the gate unreadable and would
    be wrong: §-discipline is a rule about the present-it full form.
    """
    assert violations("## What is being decided\n\nWhether to adopt X.\n") == []


def test_each_condition_can_be_repaired_into_a_pass():
    """Every condition is falsifiable in BOTH directions on the same body."""
    bad = (
        "## §1 — What is being decided\n\nShip the fix in runtime.go:297?\n\n"
        "## §2 — Recommended answer\n\nNone recorded.\n\n"
        "## §4 — Alternatives named\n\nA.\n\n"
        "## §4 — Options\n\nB.\n"
    )
    assert conditions(bad) == {"C1", "C2", "C3"}
    good = (
        "## §1 — What is being decided\n\nDo we take the terminal-root interlock?\n\n"
        "## §2 — Recommended answer\n\nAdopt the interlock.\n\n"
        "## §4 — Alternatives named\n\nA.\n\n"
        "## §5 — Options\n\nB.\n"
    )
    assert violations(good) == []


# --- the enforcement point ---------------------------------------------------


def create(tmp_path: Path, body: str):
    city_root, rig_root = runtime_fixture(tmp_path)
    body_file = tmp_path / "body.md"
    body_file.write_text(body, encoding="utf-8")
    return run_mctl(
        *brief_command(
            city_root, "create", "--title", "section discipline probe",
            "--body-file", str(body_file), "--source", "mc-source", "--dry-run", "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )


GATE_EVIDENCE = "\n## Gate Evidence\n\nG5: n/a — no server surface touched.\n"

CLEAN_BODY = (
    "## §1 — What is being decided\n\nWhether to take the terminal-root interlock.\n\n"
    "## §2 — Recommended answer\n\nAdopt the interlock.\n\n"
    "## §6 — Supporting evidence\n\nruntime.go:297 fires on status==closed.\n"
) + GATE_EVIDENCE


def test_creation_REFUSES_the_body_mc_67snh_was_filed_with(tmp_path: Path):
    """Creation is where `mc-67snh` entered: decisions_to_briefs ->
    plan_create_brief -> validate_brief_input. Refusing at the drain instead
    would reach an author already told the write succeeded (#169, CT13.4)."""
    result = create(tmp_path, AS_FILED.read_text(encoding="utf-8") + GATE_EVIDENCE)
    assert result.returncode != 0, "the mc-67snh body must not be creatable"
    assert "MBRF037" in result.stderr, result.stderr


def test_the_SAME_call_SUCCEEDS_on_a_well_filed_body(tmp_path: Path):
    """The positive control. Without it, a gate that refused everything would
    pass the test above — #104 records seven checks that could not have failed."""
    result = create(tmp_path, CLEAN_BODY)
    assert result.returncode == 0, result.stderr
    for code in ("MBRF037", "MBRF038", "MBRF039"):
        assert code not in result.stderr


def test_the_refusal_says_what_to_do(tmp_path: Path):
    result = create(tmp_path, AS_FILED.read_text(encoding="utf-8") + GATE_EVIDENCE)
    # `next:`, not `suggested_next_command:` -- #183 moved the remedy out of the
    # alphabetically-sorted facts block and up beside `hint`, so it reads as a
    # remedy rather than as one more machine fact. The assertion's INTENT is
    # unchanged: the refusal must tell the author what to do.
    assert "next:" in result.stderr
    assert "§6" in result.stderr, "must name where the evidence belongs"
    assert "runtime.go:297" in result.stderr, "must name the offending text"


# --- the producer that emitted the duplicate §4 -----------------------------


def test_decisions_to_briefs_no_longer_composes_two_section_fours():
    """49 of the 178 live brief files carry `§4 — Alternatives named` AND an
    appended `§4 — Options`. All 11 in-scope briefs this composer produced fail
    C2. `parse_decision_options` was taught to de-duplicate around it; the
    writer is now taught not to emit it."""
    with_options = brief_body(
        "Whether to take the interlock.",
        source_bead_id="mc-source",
        checks_passed=("source resolves",),
        options_follow=True,
        recommendation="A",
    ) + "\n## §4 — Options\n\n- **(A) Interlock** *(recommended)* do it.\n"
    fours = [
        s for s in parse_brief_sections(with_options)
        if s.match == "explicit" and s.section_index == 4
    ]
    assert len(fours) == 1, [s.heading for s in fours]
    assert conditions(with_options) == set(), violations(with_options)


def test_decisions_to_briefs_still_emits_a_section_four_when_no_options_follow():
    body = brief_body(
        "Whether to take the interlock.",
        source_bead_id="mc-source",
        checks_passed=("source resolves",),
    )
    assert "## §4 — Alternatives named" in body


def test_a_decision_transported_with_no_recommendation_is_REFUSED_not_silently_filed():
    """The measured conflict, asserted rather than left as a surprise.

    #194 has `decisions_to_briefs` deposit UNDECIDED, and its §2 said "None
    recorded". That is exactly the null answer Taylor sent `mc-67snh` back for.
    The gate refuses it; this test pins that the refusal is C3 and not some
    accident, so the day the policy is changed the test says which one moved.
    """
    body = brief_body(
        "Whether to take the interlock.",
        source_bead_id="mc-source",
        checks_passed=("source resolves",),
    )
    assert "C3" in conditions(body)


# --- registration drift guards ----------------------------------------------


def test_the_gate_is_registered_in_the_machine_join_layer():
    registry = tomllib.loads(
        (REPO_ROOT / "assets" / "brief-pipeline" / "gates.toml").read_text(encoding="utf-8")
    )
    gate = [g for g in registry["gates"] if g["id"] == "G17"]
    assert gate, "G17 missing from gates.toml"
    assert gate[0]["name"] == "section-discipline"
    assert "G17" in registry["profiles"]["standard"]["gates"]


def test_the_policy_table_is_authoritative_and_carries_the_same_row():
    """PP4.1: the gate-inventory table owns the definition; gates.toml must
    match it. This fails the day one moves without the other."""
    policy = (REPO_ROOT / "subdomains" / "brief-system" / "POLICY.md").read_text(
        encoding="utf-8"
    )
    assert "| G17 | section-discipline | mechanical |" in policy
    assert "B1.9 Section discipline (G17)" in policy


@pytest.mark.parametrize(
    "code,severity", [("MBRF037", "FATAL"), ("MBRF038", "FATAL"), ("MBRF039", "WARN")]
)
def test_every_code_the_gate_raises_is_registered(code: str, severity: str):
    """#69/#73 defect class: a reference to something nothing installs.

    MBRF039 is WARN on purpose and the registry says so, so nobody reads the
    severity as an oversight."""
    registry = tomllib.loads(
        (REPO_ROOT / "assets" / "mctl" / "diagnostics.toml").read_text(encoding="utf-8")
    )
    assert code in registry, f"{code} is raised but not registered"
    assert registry[code]["severity"] == severity


def test_C1_and_C2_block_and_C3_only_warns():
    """The declared conflict, asserted rather than left implicit.

    A later reader must be able to see WHY `decisions_to_briefs` still works,
    and this fails the day someone flips a condition without moving the data
    file and its stated reason."""
    found = {v.condition: v.blocking for v in violations(AS_FILED.read_text(encoding="utf-8"))}
    assert found["C1"] is True
    assert found["C2"] is True
    assert found["C3"] is False, (
        "C3 blocks; B1.9(c) vs #194 must be adjudicated (mc-qbs6j) before it can"
    )


def test_an_advisory_C3_is_reported_and_not_silent(tmp_path: Path):
    """D2/G15's rule generalised: a measured finding that does not block must
    still be said out loud. A silent advisory is the same defect as a silent
    N/A."""
    body = brief_body(
        "Whether to take the interlock.",
        source_bead_id="mc-source",
        checks_passed=("source resolves",),
    )
    result = create(tmp_path, body)
    assert result.returncode == 0, result.stderr
    assert "MBRF039" in (result.stdout + result.stderr), (
        "the C3 finding must appear as an advisory on a brief that was accepted"
    )


def test_the_shell_check_does_not_reimplement_the_rule():
    """P7.1/#35 drift guard. Two independently written structural checkers
    drift; the shell layer must call the same function, not a copy of it."""
    script = (
        REPO_ROOT / "assets" / "scripts" / "checks" / "brief-section-discipline.sh"
    ).read_text(encoding="utf-8")
    assert "section_discipline_violations" in script
    for rule in discipline_rules().get("evidence_class") or []:
        assert rule["pattern"] not in script, (
            f"the shell check carries its own copy of the {rule['id']} pattern"
        )
