"""A numbered `Gate Evidence` heading is present, and the matcher must see it.

Measured 2026-08-29 (mc-ntxi0). `briefs_create` refused two stranded
gate-approved briefs with MBRF036 -- "missing a required section: Gate
Evidence" -- for a section they contain. `gsp-2bowrk-work.md` carries
`## 12. Gate Evidence` at line 534; `gsp-pdbyqa-work.md` carries it at 617.

The rule in `required-sections.toml` is `^##*[[:space:]]+Gate Evidence\b`,
which requires the literal IMMEDIATELY after the hashes. A section number
between them is unmatched, so the heading reads as absent.

Two things make this worse than a near-miss. The refusal's own
`suggested_next_command` says "add a '## Gate Evidence' section" -- following
it appends a SECOND gate-evidence section to a brief that already has one. And
the numbered form is what the `commission-work-briefed` producer emits, so the
refused briefs are conformant to the contract that produced them; producer and
validator disagree, and the validator states the disagreement as a claim about
CONTENT.

Surveyed across every pile in the city (313 headings): 248 `## Gate Evidence`,
60 `### Gate Evidence`, 2 `## 12. Gate Evidence`, and one each of
`## §9 — Gate Evidence` / `## §10 — Gate Evidence`. So FOUR briefs are refused,
in two prefix families, not the two first observed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core.structure import missing_sections  # noqa: E402

BODY = "## {heading}\n\nG1 Test-evidence: PASSED\n"


def _absent(heading: str) -> bool:
    return bool(missing_sections(BODY.format(heading=heading)))


# -- controls: without these, the assertions below prove nothing -------------


def test_bare_heading_is_found() -> None:
    """The 248-brief majority form. If this ever fails, the fix went too far."""
    assert not _absent("Gate Evidence")


def test_a_body_with_no_gate_evidence_is_still_refused() -> None:
    """The matcher must still be able to FAIL -- P6.2."""
    assert missing_sections("## Something Else\n\nnothing here\n")


def test_prose_mentioning_the_phrase_is_not_a_heading() -> None:
    """Guard against relaxing into a substring search."""
    assert missing_sections("## Discussion\n\nwe owe Gate Evidence here\n")


def test_a_heading_that_merely_contains_the_words_is_not_a_match() -> None:
    assert _absent("Notes On Gate Evidence Practice") is True


# -- the defect --------------------------------------------------------------


@pytest.mark.parametrize(
    "heading",
    [
        "12. Gate Evidence",       # gsp-2bowrk:534, gsp-pdbyqa:617
        "§9 — Gate Evidence",
        "§10 — Gate Evidence",
        "7. Gate Evidence",
    ],
)
def test_numbered_gate_evidence_heading_is_found(heading: str) -> None:
    assert not _absent(heading), (
        f"{heading!r} contains a Gate Evidence section but the matcher "
        "reports it missing"
    )
