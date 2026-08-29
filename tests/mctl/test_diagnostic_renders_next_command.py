"""#183: a diagnostic's remedy must reach the operator who was just refused.

`suggested_next_command` is a first-class field on `Diagnostic` (`diagnostics.py`)
and is in `_FACT_TO_TYPED_FIELD`, so it is populated and serialised. But
`render_diagnostic` enumerated severity, code, message, hint, facts and trace_id
-- and not the remedy. Seventeen call sites across `effects.py`, `work.py`,
`briefs.py` and `gates.py` write it; the CLI showed none of them.

WHY THIS IS THE TEST THAT WOULD HAVE FAILED. The value reaches the renderer by
TWO different routes and only one of them was visible, which is why the gap
survived casual inspection:

  * set as a TYPED FIELD (briefs.py:788, :829, :1640, :2186, :2268) -- dropped
    entirely; the operator saw a code and had to grep the registry.
  * passed through FACTS (briefs.py:2302, effects.py:2636) -- printed, but only
    as a raw `suggested_next_command:` line sorted alphabetically among the
    machine facts, i.e. present but not where anyone looks for what to do next.

A test that exercised only the facts route would have PASSED against the broken
renderer. Both routes are covered below for exactly that reason.

The de-duplication case is the one a naive fix breaks: `__post_init__` promotes
a `facts` entry onto the typed field, so appending the typed field without
skipping the fact prints the remedy twice.
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.diagnostics import Diagnostic, Severity, render_diagnostic


REMEDY = "mctl briefs doctor mc-example --json"


def _lines(diagnostic: Diagnostic) -> list[str]:
    return render_diagnostic(diagnostic).split("\n")


def test_typed_field_remedy_is_rendered() -> None:
    """The route that was silently dropped: set directly, not via facts."""
    rendered = render_diagnostic(
        Diagnostic(
            severity=Severity.ERROR,
            code="MBRF034",
            message="Brief has no source dependency.",
            suggested_next_command=REMEDY,
        )
    )
    assert f"next: {REMEDY}" in rendered


def test_facts_route_remedy_is_rendered() -> None:
    """The route that 'worked' -- it must still work, and now reads as a remedy."""
    rendered = render_diagnostic(
        Diagnostic(
            severity=Severity.ERROR,
            code="MBRF034",
            message="Brief has no source dependency.",
            facts={"suggested_next_command": REMEDY},
        )
    )
    assert f"next: {REMEDY}" in rendered


def test_remedy_is_emitted_exactly_once_when_supplied_via_facts() -> None:
    """`__post_init__` promotes facts onto the typed field; do not print twice."""
    diagnostic = Diagnostic(
        severity=Severity.ERROR,
        code="MBRF034",
        message="Brief has no source dependency.",
        facts={"suggested_next_command": REMEDY},
    )
    assert sum(REMEDY in line for line in _lines(diagnostic)) == 1


def test_remedy_is_placed_with_the_hint_not_buried_in_facts() -> None:
    """Position is the point of #183: a remedy sorted among machine facts is
    technically present and operationally invisible."""
    lines = _lines(
        Diagnostic(
            severity=Severity.ERROR,
            code="MBRF034",
            message="Brief has no source dependency.",
            hint="Supply at least one source bead.",
            facts={"aaa_sorts_first": "x", "zzz_sorts_last": "y"},
            suggested_next_command=REMEDY,
        )
    )
    next_index = next(i for i, line in enumerate(lines) if line.startswith("next: "))
    hint_index = next(i for i, line in enumerate(lines) if line.startswith("hint: "))
    first_fact_index = next(i for i, line in enumerate(lines) if line.startswith("aaa_sorts_first: "))
    assert hint_index < next_index < first_fact_index


def test_absent_remedy_emits_no_next_line() -> None:
    """No remedy must render as nothing -- never an empty `next:` line, which
    would read as a remedy that exists and is blank."""
    rendered = render_diagnostic(
        Diagnostic(
            severity=Severity.WARN,
            code="MBRF063",
            message="Row has no brief body file.",
        )
    )
    assert "next:" not in rendered


def test_other_facts_are_untouched() -> None:
    """Skipping the duplicate must not drop neighbouring facts."""
    lines = _lines(
        Diagnostic(
            severity=Severity.ERROR,
            code="MBRF034",
            message="Brief has no source dependency.",
            facts={"suggested_next_command": REMEDY, "rig_name": "mathcity"},
        )
    )
    assert "rig_name: mathcity" in lines
    assert "suggested_next_command: " + REMEDY not in lines


def test_facts_payload_still_carries_the_key_for_json_consumers() -> None:
    """The renderer skips the fact; it must not remove it from the payload.
    `facts` is part of the serialisation contract read by JSON consumers."""
    diagnostic = Diagnostic(
        severity=Severity.ERROR,
        code="MBRF034",
        message="Brief has no source dependency.",
        facts={"suggested_next_command": REMEDY},
    )
    payload = diagnostic.to_dict()
    assert payload["facts"]["suggested_next_command"] == REMEDY
    assert payload["suggested_next_command"] == REMEDY
