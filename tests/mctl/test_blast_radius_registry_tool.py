"""`#110`'s classification, made reachable — plus the one bit it does not carry.

`mctl_core/blast_radius.py` shipped with `#110` and closed. Measured on
`8120a24`, its only references are its own module, a comment, and tests: no MCP
tool, no consumer, not on `EffectPlan` despite the issue's title. `#153`'s
deeper shape.

**The bit the core deliberately does not carry, and a reporting surface must.**
`load_registry()` returns `{}` for an absent file, and says why:

    "Absent file is an empty registry, not a crash. An empty registry is SAFE,
     not permissive: every lookup then misses and resolves to UNCLASSIFIED."

That is right for **classification** — failing safe is the whole point. It is
wrong for a **page**, because "this city classifies no operations" and "the
registry file is missing" would render identically as `0`, and an operator
reading `0 classified` would conclude the city has nothing dangerous rather
than that we failed to look.

So the tool reports `registry_present` alongside the entries. Same shape as
`gates_readable`, for the same reason, and the core is left exactly as it is —
its collapse is correct for its own caller.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))


def _server():
    from mctl_core.mcp_server import MctlMcpServer

    return MctlMcpServer(default_city=Path("/Users/tdupuy/gt"), client_class="internal")


def test_the_tool_is_exposed():
    assert "blast_radius_registry" in {s.name for s in _server().visible_tools()}


def test_the_dashboard_is_allowed_to_call_it():
    """Registration is not reachability -- the allowlist is a second gate, and
    forgetting it is how `#111` nearly shipped unreachable."""
    from mctl_dashboard.client import ALLOWED_TOOLS

    assert "blast_radius_registry" in ALLOWED_TOOLS


# ---------------------------------------------------------------------------
# the bit the core does not carry
# ---------------------------------------------------------------------------


def test_a_missing_registry_is_not_reported_as_zero_classified(tmp_path):
    from mctl_core.blast_radius import registry_report

    report = registry_report(path=tmp_path / "absent.toml")
    assert report["registry_present"] is False
    assert report["operations"] == []


def test_a_present_registry_says_so(tmp_path):
    registry = tmp_path / "blast_radius.toml"
    # Quoted, as the real registry writes them: an unquoted [briefs.create]
    # is a NESTED table in TOML, so the key would be "briefs". My first draft
    # of this fixture made exactly that mistake and the test caught it.
    registry.write_text('["briefs.create"]\nfloor = "medium"\n', encoding="utf-8")

    from mctl_core.blast_radius import registry_report

    report = registry_report(path=registry)
    assert report["registry_present"] is True
    assert [op["operation"] for op in report["operations"]] == ["briefs.create"]


def test_awaiting_emitter_is_reported_as_a_fact_not_a_warning(tmp_path):
    """`awaiting_emitter`'s own docstring: "Reporting 'N entries await an
    emitter' is a fact; reporting 'N orphans' is a warning about the wrong
    thing." The report must not relabel them."""
    registry = tmp_path / "blast_radius.toml"
    registry.write_text(
        '["rig.suspend"]\nfloor = "high"\naspirational = true\n'
        '["briefs.create"]\nfloor = "medium"\n',
        encoding="utf-8",
    )

    from mctl_core.blast_radius import registry_report

    report = registry_report(path=registry)
    assert report["awaiting_emitter"] == ["rig.suspend"]
    assert "orphan" not in str(report).lower()
