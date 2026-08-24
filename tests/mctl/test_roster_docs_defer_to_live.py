"""The tool roster must not be frozen as a hand-maintained count (`#162`).

CT13.3: *"The tool roster cannot go stale silently... A stale roster is not a
cosmetic docs defect: it tells an agent a capability does not exist, and the
agent then builds the workaround CT13.1 forbids."*

Three documents an agent actually reads (`mayor-math-handoff`, `mayor-math-prime`,
`mctl-entry-point`) and one live print statement all froze the tool count at
`16`. The live surface was 23 when `#162` was filed and is larger now -- every
number went stale as tools were added, and two of those documents tell a Mayor
to trust the frozen list *over* its own current tool list, so a real tool reads
as hallucinated.

CT13.3's own pass condition is deferral: *"the document defers to a live
enumeration instead of naming one."* These tests pin that: no frozen roster
count survives, the entry-point fragment points at the canonical live roster,
and the dashboard banner computes its count instead of hard-coding it -- so the
defect class cannot silently reappear the next time a tool is registered.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

ENTRY_POINT = ROOT / "template-fragments" / "mctl-entry-point.md"
HANDOFF = ROOT / "skills" / "mayor-math-handoff" / "SKILL.md"
PRIME = ROOT / "skills" / "mayor-math-prime" / "SKILL.md"
SERVER = ROOT / "assets" / "scripts" / "mctl_dashboard" / "server.py"

#: A frozen roster-size claim: "16 tools", "23 typed tools", "all 16", etc. The
#: bug is naming a number for the whole surface; a count that refers to
#: something else (e.g. "four mutating tools") is fine.
_FROZEN_COUNT = re.compile(r"\b\d+\s+(?:real |typed )?tools\b|\ball\s+\d+\b", re.IGNORECASE)


def _frozen_claims(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if _FROZEN_COUNT.search(line)]


def test_the_entry_point_fragment_names_no_frozen_roster_count():
    claims = _frozen_claims(ENTRY_POINT.read_text(encoding="utf-8"))
    assert not claims, f"mctl-entry-point.md still freezes a roster count: {claims}"


def test_the_entry_point_fragment_points_at_the_canonical_live_roster():
    """Deferral is the fix: the reader must be sent to the live enumeration."""
    text = ENTRY_POINT.read_text(encoding="utf-8")
    assert "tools/list" in text, "the fragment must point at the live tools/list roster"


def test_the_handoff_skill_names_no_frozen_roster_count():
    claims = _frozen_claims(HANDOFF.read_text(encoding="utf-8"))
    assert not claims, f"mayor-math-handoff still freezes a roster count: {claims}"


def test_the_prime_skill_names_no_frozen_roster_count():
    claims = _frozen_claims(PRIME.read_text(encoding="utf-8"))
    assert not claims, f"mayor-math-prime still freezes a roster count: {claims}"


def test_the_dashboard_banner_computes_its_tool_count_instead_of_hardcoding_it():
    """`server.py:138` printed a literal `16` on every dashboard start (#162,
    #154: many starts a night). It must derive the count from the live roster."""
    src = SERVER.read_text(encoding="utf-8")
    assert "all 16 tools" not in src, "the hardcoded '16' literal is still in the banner"
    # The banner must compute its count from the live roster, not name an integer.
    banner = next((l for l in src.splitlines() if "MCP client class" in l), "")
    assert "internal_tool_count()" in banner, f"the banner must compute its count: {banner!r}"


def test_the_computed_count_matches_the_live_roster():
    from mctl_core import mcp_server

    from mctl_dashboard import server

    assert server.internal_tool_count() == len(mcp_server.TOOLS)
