"""Decision options must resolve from wherever the brief actually wrote them.

`decision_options()` read the bead description and nothing else, and it scoped
the search to `§4`. Measured against the live city on 2026-08-19, that reads
the wrong population with the wrong rule:

* **1 of 280** decision beads city-wide carries labeled options in its
  `description` (one hecke brief). The bead lane is nearly empty.
* **17 of 89** stack files under `<city-root>/.beads/briefs/stack/` enumerate
  labeled `- **(A) …**` options, and **every one of them is `form: full`**.
  The `form: compact` briefs carry none, by design.
* Of those 17, only **5** sit under a heading numbered `§4`. The rest head
  their options `§5 — Options`, `§6 — Options`, `§3 — Options`. The parser
  matched the *number* and so missed twelve briefs whose heading says
  "Options" in as many words.

So there are two defects, one per source: the reader looked in the lane that
has no options, and inside that lane it keyed on a section number that real
briefs do not hold fixed. Both are the shape of issue #65 — brief state lives
in more than one place and readers disagree about which.

## What must NOT become an option

The pressure here is to widen the parser until the count looks good, and the
corpus punishes that immediately:

* **`form: compact` briefs have no options by design.** They are
  DECISION / CONTEXT / RECOMMEND / CONFIRM with a y/n. `()` is the correct
  answer for all 19 of them, not a gap to be closed.
* **Prose alternatives are not labeled options.** hecke writes §4 as prose:
  "Algebraic quotient without explicit cusp cells" is a genuine alternative a
  human can weigh, and it is not `B`. Labeling it would make `MOPT001` block
  adjudication on a brief that never offered a choice.
* **A bolded `(B)` in a Risks section is not an option.** Live brief
  `243-worktree-isolation-shares-git-config` writes
  "**(B) is only as good as its placement.**" under `§7 — Risks`; its own
  `§5 — Options` is a table with no list items. The honest answer for that
  brief is `()`, and this file asserts it.

## Provenance

Every option records the `source` it was parsed from — `bead_description`,
`stack_file`, `pile_file` — the way Slice 2's `Verdict` does, so the front end
can show where a brief's options came from rather than implying all options
are equally canonical. When both the bead and the cache offer options, the
bead wins (B2.4/B2.8) and the disagreement is reported as `MOPT003` rather
than silently resolved.
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

MCTL = SCRIPTS_ROOT / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"

BRIEF = "mc-sources"
SOURCE = "source-sources"


# The live shape this slice exists for: options under a heading that says
# "Options" while carrying a number that is not 4. Copied in structure from
# `232-brief-operator-redispatch-loop-brief.md`.
STACK_OPTIONS_BODY = """---
artifact: none
status: ready-for-adjudication
form: full
---

## §1 — What is being decided (INVARIANT)

Whether the redispatch loop is stopped at the issuer or at the consumer.

## §5 — What it is blocking

Eight beads.

## §6 — Options

- **(A) Stop it at the issuer.** *(recommended)* Cheapest, one call site.
- **(B) Add consumer-side backoff.** Correct but touches every consumer.
- **(C) Leave it.** Rejected: the status quo produced this brief.

## §7 — Risks

- **(B) alone rots.** An override that is not re-checked drifts.
"""

# Options where the parser always looked: an explicitly numbered §4.
BEAD_OPTIONS_BODY = """# Brief

## §1 — What is being decided (INVARIANT)

Whether to do the thing.

## §4 — Options

- **(A) Do it now.** *(recommended)* Cheapest path.
- **(B) Defer it.** Costs a cycle.
"""

# A different option set in the cache, to make the precedence rule observable.
CACHE_OPTIONS_BODY = """# Brief

## §5 — Options

- **(A) Do it now.**
- **(B) Defer it.**
- **(C) Drop it.**
"""

# `form: compact` — DECISION / CONTEXT / RECOMMEND / CONFIRM, y/n. No options
# by design; `()` is the right answer, not a gap.
COMPACT_BODY = """---
form: compact
---

## 1. What is being decided

Close and re-sling three router beads that can never be claimed.

## 2. Context (one paragraph)

The targets are dead.

## 3. Recommended verdict

Approve. Confirm y/n.

## 4. Risks

Low.
"""

# hecke's real §4 shape: alternatives written as prose, with no labels. A
# reader that manufactures `(A)`/`(B)` here invents a choice nobody offered.
PROSE_ALTERNATIVES_BODY = """# Brief

## §1 — What is being decided (INVARIANT)

Whether to compute the fundamental domain by explicit cusp cells.

## §4 — Alternatives considered

Algebraic quotient without explicit cusp cells. Rejected because the
side-pairing data is not recoverable afterwards. A polytope wrapper was also
considered and is a fallback only.
"""


def bead_rows(description: str | None) -> list[dict[str, object]]:
    brief: dict[str, object] = {
        "id": BRIEF,
        "title": "Options live in more than one place",
        "status": "open",
        "issue_type": "decision",
        "labels": ["brief-open"],
        "dependencies": [{"issue_id": BRIEF, "depends_on_id": SOURCE, "type": "related"}],
        "created_at": "2026-08-10T12:00:00Z",
        "updated_at": "2026-08-11T12:00:00Z",
    }
    if description is not None:
        brief["description"] = description
    return [
        brief,
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


def runtime(
    tmp_path: Path,
    description: str | None = None,
    *,
    stack_body: str | None = None,
    pile_body: str | None = None,
) -> tuple[Path, Path]:
    """A one-brief rig whose body can be planted in any of the three sources."""
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
        (beads / "briefs" / "stack" / f"{BRIEF}.md").write_text(stack_body, encoding="utf-8")
    if pile_body is not None:
        (beads / "briefs" / ".pile" / f"{BRIEF}.md").write_text(pile_body, encoding="utf-8")
    fixture = beads / "issues.jsonl"
    fixture.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in bead_rows(description)),
        encoding="utf-8",
    )
    return city_root, fixture


def context_for(city_root: Path, fixture: Path):
    from mctl_core.context import resolve_context

    return resolve_context(
        REPO_ROOT,
        city=city_root,
        rig="mathcity",
        require_runtime_city=True,
        require_explicit_runtime=True,
        env={"MCTL_BEADS_FIXTURE": str(fixture)},
    )


def options_for(city_root: Path, fixture: Path):
    from mctl_core.briefs import decision_options

    return decision_options(context_for(city_root, fixture), BRIEF)


def report_for(city_root: Path, fixture: Path):
    from mctl_core.briefs import decision_options_report

    return decision_options_report(context_for(city_root, fixture), BRIEF)


def adjudicate(city_root: Path, fixture: Path, *extra: str):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(fixture)
    return subprocess.run(
        [
            sys.executable, str(MCTL), "briefs", "adjudicate", BRIEF,
            "--verdict", "approve", "--reason", "source test", *extra,
            "--city", str(city_root), "--rig", "mathcity", "--json",
        ],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )


# --- the stack file is a source ----------------------------------------------


def test_options_written_to_the_stack_file_resolve(tmp_path: Path):
    """The measured gap: options live in stack files, the parser read beads."""
    city_root, fixture = runtime(tmp_path, "A description with no options at all.",
                                 stack_body=STACK_OPTIONS_BODY)

    options = options_for(city_root, fixture)

    assert [option.label for option in options] == ["A", "B", "C"]


def test_the_stack_file_is_recorded_as_the_source(tmp_path: Path):
    """Provenance, not just content: the front end must be able to show it."""
    city_root, fixture = runtime(tmp_path, "A description with no options at all.",
                                 stack_body=STACK_OPTIONS_BODY)

    options = options_for(city_root, fixture)

    assert {option.source for option in options} == {"stack_file"}


def test_the_pile_file_is_recorded_as_its_own_source(tmp_path: Path):
    """`.pile` and `stack` are different lanes and must not be conflated."""
    city_root, fixture = runtime(tmp_path, None, pile_body=BEAD_OPTIONS_BODY)

    options = options_for(city_root, fixture)

    assert [option.label for option in options] == ["A", "B"]
    assert {option.source for option in options} == {"pile_file"}


def test_options_under_a_section_numbered_other_than_four_resolve(tmp_path: Path):
    """12 of the 17 live option-bearing briefs head their options §5/§6/§3."""
    city_root, fixture = runtime(tmp_path, None, stack_body=STACK_OPTIONS_BODY)

    options = options_for(city_root, fixture)

    assert [option.label for option in options] == ["A", "B", "C"]
    assert options[0].heading == "Stop it at the issuer."


# --- the bead description is still a source, and still wins ------------------


def test_options_on_the_bead_description_still_resolve(tmp_path: Path):
    city_root, fixture = runtime(tmp_path, BEAD_OPTIONS_BODY)

    options = options_for(city_root, fixture)

    assert [option.label for option in options] == ["A", "B"]
    assert {option.source for option in options} == {"bead_description"}


def test_the_bead_wins_when_both_sources_offer_options(tmp_path: Path):
    """B2.4/B2.8: the bead is canonical and the file is a regenerable cache."""
    city_root, fixture = runtime(tmp_path, BEAD_OPTIONS_BODY, stack_body=CACHE_OPTIONS_BODY)

    options = options_for(city_root, fixture)

    assert [option.label for option in options] == ["A", "B"]
    assert {option.source for option in options} == {"bead_description"}


def test_a_disagreement_between_the_sources_is_reported_not_swallowed(tmp_path: Path):
    """Preferring the bead silently would hide that the cache says otherwise."""
    city_root, fixture = runtime(tmp_path, BEAD_OPTIONS_BODY, stack_body=CACHE_OPTIONS_BODY)

    _, diagnostics = report_for(city_root, fixture)

    assert "MOPT003" in {diagnostic.code for diagnostic in diagnostics}


def test_agreeing_sources_raise_no_diagnostic(tmp_path: Path):
    """Redundant-but-consistent state is not a defect and must not read as one."""
    city_root, fixture = runtime(tmp_path, BEAD_OPTIONS_BODY, stack_body=BEAD_OPTIONS_BODY)

    options, diagnostics = report_for(city_root, fixture)

    assert [option.label for option in options] == ["A", "B"]
    assert "MOPT003" not in {diagnostic.code for diagnostic in diagnostics}


# --- what must not become an option ------------------------------------------


def test_a_compact_brief_returns_no_options_and_that_is_correct(tmp_path: Path):
    """19 live stack briefs are `form: compact`. `()` is the answer, not a gap."""
    city_root, fixture = runtime(tmp_path, None, stack_body=COMPACT_BODY)

    assert options_for(city_root, fixture) == ()


def test_prose_alternatives_are_not_extracted_as_labeled_options(tmp_path: Path):
    """hecke writes §4 as prose. Inventing `(B)` would fire MOPT001 falsely."""
    city_root, fixture = runtime(tmp_path, PROSE_ALTERNATIVES_BODY)

    assert options_for(city_root, fixture) == ()


def test_a_bolded_label_in_a_risks_section_is_not_an_option(tmp_path: Path):
    """Live `243-worktree-isolation…` writes `**(B) is only as good as…**` in §7."""
    city_root, fixture = runtime(tmp_path, None, stack_body=STACK_OPTIONS_BODY)

    options = options_for(city_root, fixture)

    assert [option.label for option in options] == ["A", "B", "C"]
    assert not any("rots" in option.raw_text for option in options)


def test_a_brief_with_no_body_anywhere_returns_no_options(tmp_path: Path):
    """Failing open is right here: a missing cache must not block a verdict."""
    city_root, fixture = runtime(tmp_path, None)

    assert options_for(city_root, fixture) == ()


# --- the gate this feeds -----------------------------------------------------


def test_mopt001_fires_on_a_brief_whose_options_are_in_its_stack_file(tmp_path: Path):
    """The acceptance: the gate must reach briefs it could not previously see."""
    city_root, fixture = runtime(tmp_path, None, stack_body=STACK_OPTIONS_BODY)

    result = adjudicate(city_root, fixture)

    assert result.returncode != 0
    assert "MOPT001" in result.stderr, result.stderr


def test_naming_a_stack_file_option_unblocks_adjudication(tmp_path: Path):
    city_root, fixture = runtime(tmp_path, None, stack_body=STACK_OPTIONS_BODY)

    result = adjudicate(city_root, fixture, "--option", "B")

    assert result.returncode == 0, result.stderr


def test_mopt002_still_rejects_a_label_the_stack_file_does_not_offer(tmp_path: Path):
    city_root, fixture = runtime(tmp_path, None, stack_body=STACK_OPTIONS_BODY)

    result = adjudicate(city_root, fixture, "--option", "Z")

    assert result.returncode != 0
    assert "MOPT002" in result.stderr, result.stderr


def test_a_compact_brief_adjudicates_without_an_option(tmp_path: Path):
    """The y/n lane must stay adjudicable; MOPT001 must not reach it."""
    city_root, fixture = runtime(tmp_path, None, stack_body=COMPACT_BODY)

    result = adjudicate(city_root, fixture)

    assert result.returncode == 0, result.stderr
