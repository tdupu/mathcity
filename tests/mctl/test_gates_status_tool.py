"""`gates_status` had a core module and no way to reach it.

`#119` shipped `mctl_core/gates.py`: typed, tested, and correct against its own
acceptance criteria. It was then closed. **No page could call it**, because
`mctl_dashboard` reaches data only through the MCP tool surface and no
`gates_status` tool existed. That is `#153`'s deeper shape -- not "the front end
was never staffed" but "there is no route from the core to a front end at all".

This exposes it. The property that must survive the wrapper is the one the core
module already gets right and that an empty list destroys:

    gates_readable=False  ->  "we could not look"
    gates=(), readable     ->  "this city defines no gates"

Those are different facts. A tool that returns `{"gates": []}` for both collapses
them, and the screen above it then cannot tell them apart no matter how carefully
it is written.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))


def _server():
    from mctl_core.mcp_server import MctlMcpServer

    # `client_class="internal"` is what the dashboard uses; the default
    # external surface hides every tool until armed, so asserting against the
    # default would test the arming flag rather than the registration.
    return MctlMcpServer(default_city=Path("<city-root>"), client_class="internal")


def test_the_tool_is_exposed():
    """The whole point: it must be reachable, not merely implemented."""
    names = {spec.name for spec in _server().visible_tools()}
    assert "gates_status" in names


def test_an_unreadable_gate_dir_is_not_reported_as_no_gates(tmp_path):
    """The distinction that the wrapper must not flatten."""
    from mctl_core.gates import gates_status

    report = gates_status(gates_dir=tmp_path / "does-not-exist")
    payload = report.to_dict()
    assert payload["gates_readable"] is False
    assert payload["gates"] == []
    assert payload["diagnostics"], "an unreadable gate dir must say so"


def test_a_readable_empty_gate_dir_reports_zero_gates(tmp_path):
    """The mirror: a diagnostic that cannot pass is as bad as a check that
    cannot fail."""
    from mctl_core.gates import gates_status

    (tmp_path / "gates").mkdir()
    payload = gates_status(gates_dir=tmp_path / "gates").to_dict()
    assert payload["gates_readable"] is True
    assert payload["gates"] == []
