"""`registry_report` dropped `gate`, so the page had to invent a tier.

stick-dog's two CONCERNS on `#110`, both reproduced at the merged SHA before
writing this. The surface they describe is mine, and so is the cause.

`registry_report()` emitted `operation / floor / reason / aspirational` and
**dropped `gate`**. `branch.delete` carries `gate = "authorize-git-operation"`
and no `floor`, so it reached the screen as `floor: None` with no gate field --
and the screen filled the hole with the literal string `"gated"`.

Two consequences, and the second is the defect:

1. `branch.delete — gated` on the live page is CORRECT, and correct by accident.
   It is the display default for a missing floor that happens to coincide with
   the truth.

2. An entry with NO floor AND NO gate classifies as **medium** and renders as
   **gated** -- opposite ends of the ladder, and the reassuring end is the one a
   human reads. Reproduced:

       classifier says : medium
       page renders    : gated

   No shipped entry triggers it today (every floorless entry has an explicit
   gate), so this is latent rather than live. It is still wrong, and "latent"
   is what every defect this week was until it was not.

The fix is not a better default. **A reporting surface that drops a field and
lets its consumer guess is the same defect `registry_report` was written to
prevent** -- it exists because `load_registry` collapses "absent" into "empty",
and I then collapsed "gated" into "no floor".
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_core.blast_radius import registry_report
from mctl_dashboard.screens import city


def _registry(tmp_path, body: str) -> Path:
    p = tmp_path / "blast_radius.toml"
    p.write_text(body, encoding="utf-8")
    return p


def test_a_gated_operation_reports_its_gate(tmp_path):
    """The dropped field. Without it the consumer cannot tell a gated
    operation from one whose floor is simply missing."""
    path = _registry(tmp_path, '["branch.delete"]\ngate = "authorize-git-operation"\n')
    row = registry_report(path=path)["operations"][0]
    assert row["gate"] == "authorize-git-operation"


def test_an_operation_with_a_floor_reports_no_gate(tmp_path):
    path = _registry(tmp_path, '["briefs.create"]\nfloor = "medium"\n')
    row = registry_report(path=path)["operations"][0]
    assert row["floor"] == "medium"
    assert row["gate"] is None


def test_a_floorless_gateless_entry_is_not_rendered_as_gated(tmp_path):
    """CONCERN 1. The classifier says `medium`; the page must not say `gated`,
    which is the OPPOSITE end of the ladder and the more reassuring one."""
    html = city.blast_radius(
        {
            "registry_present": True,
            "operations": [
                {"operation": "listed.no_floor", "floor": None, "gate": None,
                 "reason": "x", "aspirational": False}
            ],
            "awaiting_emitter": [],
        }
    )
    assert "gated" not in html.lower()


def test_a_genuinely_gated_operation_still_says_gated(tmp_path):
    """The true case must survive the fix -- and now it is rendered because the
    payload SAYS so, not because a field was missing."""
    html = city.blast_radius(
        {
            "registry_present": True,
            "operations": [
                {"operation": "branch.delete", "floor": None,
                 "gate": "authorize-git-operation", "reason": "x", "aspirational": True}
            ],
            "awaiting_emitter": [],
        }
    )
    low = html.lower()
    assert "gated" in low or "authorize-git-operation" in low


def test_a_gated_floor_does_not_crash_the_classifier():
    """CONCERN 2. `TIERS` is ("low","medium","high") -- `gated` is not among
    them, so an entry written `floor = "gated"` raised KeyError inside the
    escalation ladder.

    No shipped entry does that today (gated operations use `gate =`, not
    `floor =`), so this is latent. But `gated` is a word the PAGE prints, and
    the next person to write it in the registry gets a crash rather than a
    diagnostic. A registry is edited by humans; a KeyError is not an answer.
    """
    from mctl_core.blast_radius import classify

    result = classify("x", plan_contents={"deletes": True}, registry={"x": {"floor": "gated"}})
    assert result is not None
    # It must not silently become a tier either -- `gated` means a human gate
    # owns it, which is exactly what `gate =` expresses.
    assert result.get("blast_radius") != "gated"
