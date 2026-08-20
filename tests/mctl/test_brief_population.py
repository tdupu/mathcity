"""Slice 5: which decision beads are briefs at all.

`MBRF004` ("brief bead has no source dependency", B2.1) is an ERROR, and
`_blocking_diagnostic` turns every ERROR into a refusal, so it blocks
`adjudicate` / `defer` / `dispatch-work` on **120 of the 141 open** decision
beads city-wide (17 rigs, `hq` included). It is the largest single block on
*acting* on briefs.

Most of those 120 are not briefs. POLICY B2.1's own Definitions paragraph says
so in as many words:

    Decision beads created for OTHER purposes (push authorizations,
    kill-switch engagement/release, non-brief adjudications) remain their own
    standalone beads; only the brief/decision-bead pairing is collapsed.

`Bead.is_brief` is `issue_type == "decision"` with no discriminator, so a push
receipt is counted as a brief and then flagged for lacking a source
dependency -- which it cannot have, because it is not deciding about another
bead. `MBRF004` on a push receipt is the checker asking a question that does
not apply.

Measured on the live city (2026-08-19), of those 120:

===================================  ====  ==================================
class                                  n   discriminator
===================================  ====  ==================================
push authorization, skill marker       57  ``authorize-git-operation`` in body
push authorization, receipt template    3  ``Operation: … Verdict: AUTHORIZED``
kill-switch engagement/release          0  (1 live instance, and it is closed)
residue -- reported, not exempted      60  none; needs a human
===================================  ====  ==================================

The residue is deliberately left in the population. B2.1's third exempt class,
"non-brief adjudications", has no discriminator that is not circular -- any
rule wide enough to catch it also catches real briefs -- so inventing one to
make the number smaller is the failure mode this slice exists to avoid. See
`subdomains/dev/docs/MBRF004-TRIAGE-2026-08-19.md`.

Nothing here is exempted silently: `_doctor_briefs` reports every removed bead
as `MBRF054`/`MBRF055` (INFO), so an operator sees "this is a receipt, not a
brief" rather than seeing the bead vanish.
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
from mctl_core.verdicts import (
    CODE_NOT_A_BRIEF,
    CODE_NOT_A_KILL_SWITCH_BRIEF,
    brief_population,
    is_brief_bead,
    is_git_authorization_receipt,
    is_kill_switch_record,
    non_brief_code,
)

MCTL = SCRIPTS_ROOT / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"


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
# push authorizations (B2.1, class 1)
# --------------------------------------------------------------------------


def test_the_skill_marker_takes_a_receipt_out_of_the_population():
    """The shape `authorize-git-operation` writes: 57 of the live 120."""
    receipt = bead(
        id="he-hfa2t",
        title="Taylor authorized git PUSH: 6987010f -> tdupu/hecke master",
        description="Authorization gate invoked via authorize-git-operation skill.",
    )

    assert is_git_authorization_receipt(receipt) is True
    assert is_brief_bead(receipt) is False


def test_the_receipt_template_alone_takes_a_receipt_out_of_the_population():
    """3 live receipts carry the skill's notes template but not its marker.

    `he-0g69g`, `gsp-l5vi`, `gt-d8ztsx` were written by hand to the template in
    the skill's Step 3 (`Operation: … Target: … Verdict: <AUTHORIZED|DENIED>`)
    without the description sentence. They are the same receipt.
    """
    receipt = bead(
        id="he-0g69g",
        title="Taylor authorized git PUSH: 09e5a64+5fecb76 to origin/master (tdupu/hecke)",
        notes=(
            "Operation: PUSH. Target: origin/master tdupu/hecke. Verdict: AUTHORIZED. "
            "Commits: 09e5a64 + 5fecb76. BART cleared, Quimby authorized."
        ),
    )

    assert is_brief_bead(receipt) is False
    assert non_brief_code(receipt) == CODE_NOT_A_BRIEF


def test_the_receipt_template_spans_lines_as_well_as_one_line():
    """`gsp-l5vi` writes the same keys as separate lines with prose between."""
    receipt = bead(
        id="gsp-l5vi",
        title="Taylor authorized git commit a44ec95",
        description=(
            "Retroactive authorization for commit a44ec95.\n\n"
            "Operation: git commit (local, not yet pushed)\n"
            "Target: mathcity/skills/present-briefs/SKILL.md\n"
            "Branch: feature/roles-named-sessions\n\n"
            "Verdict: AUTHORIZED (Taylor in-conversation, 2026-07-12)\n"
        ),
    )

    assert is_brief_bead(receipt) is False


def test_one_receipt_key_on_its_own_is_not_enough():
    """Both keys, in order. A brief that reports an operation is still a brief.

    The template is two keys because one is not distinctive: real briefs
    describe operations, and real briefs record verdicts. Only the pair, in the
    skill's own order, identifies the receipt.
    """
    operation_only = bead(description="Operation: rebuild the tables. Cost: two days.")
    verdict_only = bead(description="Verdict: AUTHORIZED once the gate is green.")

    assert is_brief_bead(operation_only) is True
    assert is_brief_bead(verdict_only) is True


def test_an_explicit_git_auth_title_tag_takes_a_receipt_out_of_the_population():
    """`[decision][git-auth] AUTHORIZED: …` — 3 live receipts are tagged, not sentenced."""
    receipt = bead(
        id="he-d7igo",
        title="[decision][git-auth] AUTHORIZED: merge N5 branch n5-timelimit-he-0xr5b -> hecke master",
        description="## Decision Taylor AUTHORIZED (2026-07-16, via /authorize-git-operation): merge it.",
    )

    assert is_brief_bead(receipt) is False


def test_merely_mentioning_the_skill_in_prose_keeps_a_brief_in_the_population():
    """The regression this slice fixes: 5 real live briefs were being exempted.

    `gt-s4r3a1` is a policy brief that names the skill as an example of an
    approval gate. Matching the bare skill name anywhere in a body swept it,
    and four others, out of the population -- and a brief that leaves the
    population is invisible from then on, which is the one failure mode an
    exemption rule must not have.
    """
    policy_brief = bead(
        id="gt-s4r3a1",
        title="POLICY: fork subagents to execute when the fleet cannot",
        description=(
            "## Decision\n\nWhen the fleet cannot execute work, forking subagents is "
            "authorized, provided the contributing protocol is followed by hand:\n\n"
            "- the human approval gate wherever one applies (e.g. `authorize-git-operation` "
            "for pushes/PRs)\n"
        ),
    )

    assert is_git_authorization_receipt(policy_brief) is False
    assert is_brief_bead(policy_brief) is True


def test_a_manifest_that_lists_beads_needing_authorization_is_still_a_brief():
    """`gt-5fxchl`: a cohort manifest, swept out by the bare-substring rule."""
    manifest = bead(
        id="gt-5fxchl",
        title="bead-manifest-2026-07-18: DECISIONS cohort (11 beads)",
        description="Push decisions (gt-dc1qn, gt-d8ztsx) — these need authorize-git-operation.",
    )

    assert is_brief_bead(manifest) is True


def test_a_receipt_verdict_word_that_is_not_the_skills_enum_is_not_a_receipt():
    """`Verdict: approve` is B2.2's brief enum, not the skill's AUTHORIZED/DENIED."""
    subject = bead(
        description="Operation: merge the branch.\n\nVerdict: approve -- ship it.",
    )

    assert is_brief_bead(subject) is True


# --------------------------------------------------------------------------
# kill-switch engagement/release (B2.1, class 2)
# --------------------------------------------------------------------------


def test_a_kill_switch_record_leaves_the_population():
    """N5: engaging or releasing the switch is recorded as a STANDALONE bead.

    `gt-0i99e` is the live instance, verbatim.
    """
    record = bead(
        id="gt-0i99e",
        status="closed",
        title="DECISION: release no-brainer kill-switch (auto_merge_enabled false->true)",
    )

    assert is_kill_switch_record(record) is True
    assert is_brief_bead(record) is False
    assert non_brief_code(record) == CODE_NOT_A_KILL_SWITCH_BRIEF


def test_merely_mentioning_the_kill_switch_keeps_a_brief_in_the_population():
    """`gsp-pxcu` is a policy-amendment bead whose body discusses the switch.

    A body mention is not a kill-switch record. The record's subject is the
    engagement or release, and that is what the title states.
    """
    amendment = bead(
        id="gsp-pxcu",
        title="Taylor adopted 4 policy amendments: PP1.10 + PP6.3 fix + PP1.8 concision",
        description=(
            "PP6.3 now names the two-level kill-switch hierarchy and the "
            "auto_merge_enabled flag it reads."
        ),
    )

    assert is_kill_switch_record(amendment) is False
    assert is_brief_bead(amendment) is True


def test_a_kill_switch_title_without_an_engagement_verb_is_not_a_record():
    """A brief *about* the switch asks a question; a record states an act.

    The act has to govern the switch. Both halves are present here and this is
    still a brief.
    """
    subject = bead(title="Should the rig-level kill-switch default to engaged?")

    assert is_brief_bead(subject) is True


def test_the_kill_switch_recogniser_stays_narrow_on_purpose():
    """A record phrased noun-first is NOT exempted, and that is the intent.

    One live bead is not enough evidence to generalise a phrasing from. A
    record this misses keeps raising `MBRF004` and a human looks at it; a real
    brief this wrongly caught would silently leave the population. The first
    failure is visible, the second is not, so the recogniser fails toward the
    first.
    """
    noun_first = bead(title="Kill-switch release recorded for the mathcity rig")

    assert is_kill_switch_record(noun_first) is False
    assert is_brief_bead(noun_first) is True


# --------------------------------------------------------------------------
# what stays
# --------------------------------------------------------------------------


def test_an_ordinary_brief_stays_in_the_population():
    subject = bead(
        title="BRIEF #18 -- mc-73k competing graph disposition",
        description="## §1 -- What is being decided\n\nWhether to keep the graph.",
    )

    assert is_brief_bead(subject) is True
    assert non_brief_code(subject) is None


def test_a_non_decision_bead_is_never_in_the_population():
    assert is_brief_bead(bead(issue_type="task")) is False


def test_the_residue_classes_stay_in_the_population():
    """The 60 this slice refuses to exempt. Reported to a human, not removed.

    A handoff record, a memory-migrated policy rule and a server-run
    authorization are all plausibly "non-brief adjudications" under B2.1's
    third class -- and none of them is separable from a real brief by any rule
    that does not also catch real briefs. They stay, and MBRF004 keeps firing.
    """
    residue = [
        bead(id="gt-fbpybd", title="Q28 handoff -- QUIMBY 28 (2026-07-23)"),
        bead(id="he-cjqum", title="Git and push conventions (migrated from memory)"),
        bead(
            id="he-uaarh",
            title="[decision][server-auth] AUTHORIZED: run N0 fresh gamma0 backup on aia-s27",
            description="## Decision Taylor AUTHORIZED (2026-07-16): run N0.",
        ),
        bead(id="gsp-nz99", title="[policy] Mayor works ONLY through the brief system"),
    ]

    assert brief_population(residue) == tuple(residue)


def test_the_population_drops_by_exactly_the_exempt_beads():
    """The count moves by the classification, not by a threshold."""
    exempt = [
        bead(id="a", description="Authorization gate invoked via authorize-git-operation skill."),
        bead(id="b", notes="Operation: PUSH. Target: origin/main. Verdict: AUTHORIZED."),
        bead(id="c", title="DECISION: engage the city-wide kill-switch (auto_merge_enabled)"),
    ]
    kept = [bead(id="d"), bead(id="e", title="Q28 handoff"), bead(id="f", issue_type="task")]

    population = brief_population([*exempt, *kept])

    assert [b.id for b in population] == ["d", "e"]
    assert len(population) == len([*exempt, *kept]) - len(exempt) - 1  # -1: the task


# --------------------------------------------------------------------------
# end to end: MBRF004 stops firing on a receipt and keeps firing on a brief
# --------------------------------------------------------------------------

RECEIPT = "mc-receipt"
SOURCELESS_BRIEF = "mc-sourceless"
LINKED_BRIEF = "mc-linked"
SOURCE = "mc-source"


def beads_payload() -> list[dict[str, object]]:
    stamps = {"created_at": "2026-08-10T12:00:00Z", "updated_at": "2026-08-11T12:00:00Z"}
    return [
        {
            "id": RECEIPT,
            "title": "Taylor authorized git PUSH: origin/main",
            "status": "open",
            "issue_type": "decision",
            "description": "Authorization gate invoked via authorize-git-operation skill.",
            "notes": "Operation: PUSH. Target: origin/main. Verdict: AUTHORIZED.",
            **stamps,
        },
        {
            "id": SOURCELESS_BRIEF,
            "title": "BRIEF #18 -- competing graph disposition",
            "status": "open",
            "issue_type": "decision",
            "description": "## §1 -- What is being decided\n\nWhether to keep the graph.",
            **stamps,
        },
        {
            "id": LINKED_BRIEF,
            "title": "BRIEF #19 -- router beads",
            "status": "open",
            "issue_type": "decision",
            "dependencies": [
                {"issue_id": LINKED_BRIEF, "depends_on_id": SOURCE, "type": "related"}
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


def test_mbrf004_no_longer_fires_on_an_exempted_receipt(tmp_path: Path):
    city_root, fixture = runtime(tmp_path)

    report = doctor_payload(city_root, fixture)

    blocked = {
        d["facts"].get("brief_id")
        for d in report["diagnostics"]
        if d["code"] == "MBRF004"
    }
    assert RECEIPT not in blocked


def test_mbrf004_still_fires_on_a_genuinely_sourceless_brief(tmp_path: Path):
    """The exemption must not become a way to make the check quiet."""
    city_root, fixture = runtime(tmp_path)

    report = doctor_payload(city_root, fixture)

    blocked = {
        d["facts"].get("brief_id")
        for d in report["diagnostics"]
        if d["code"] == "MBRF004"
    }
    assert SOURCELESS_BRIEF in blocked
    assert LINKED_BRIEF not in blocked


def test_the_exempted_receipt_is_reported_not_silently_dropped(tmp_path: Path):
    """Acceptance: no bead is silently exempted."""
    city_root, fixture = runtime(tmp_path)

    report = doctor_payload(city_root, fixture)

    told = [
        d for d in report["diagnostics"]
        if d["code"] == CODE_NOT_A_BRIEF and d["facts"].get("brief_id") == RECEIPT
    ]
    assert told, "an exempted bead must still be named by doctor"
    assert told[0]["severity"] == "INFO"
    assert told[0]["policy_ref"] == "B2.1"


def test_the_receipt_leaves_the_listed_brief_population(tmp_path: Path):
    city_root, fixture = runtime(tmp_path)

    listed = json.loads(run_mctl(city_root, fixture, "list").stdout)

    ids = {row["bead_id"] for row in listed["briefs"]}
    assert ids == {SOURCELESS_BRIEF, LINKED_BRIEF}
