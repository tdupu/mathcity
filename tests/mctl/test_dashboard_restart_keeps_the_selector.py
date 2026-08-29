"""mc-i4d6u: restart discarded the instance's dashboard selection.

`_handle_dashboard_restart` carried `host`, `port` and `rig` across the rebind
and dropped `dashboard`, so `start_instance` applied its `both` default. An
instance started as `city` came back as `both`, with **zero diagnostics**.

REPRODUCED LIVE before this fix, 2026-08-29, on an isolated spare port:

    dashboard_serve(port=53311, dashboard="city")  -> stamp {"dashboard": "city"}
    dashboard_restart(port=53311)                  -> applied true, no diagnostics
    new stamp                                      -> {"dashboard": "both"}

That is the silent contract swap #164/#210 gate restart against, occurring
inside the tool built to prevent it: the operator asks to change one thing (the
code) and silently gets a second change. It also defeats `dashboard_status`'s
care in never reporting `both` unless someone chose it -- after a rebind the
stamp asserts a selection nobody made, indistinguishable from a real one.

THE TRAP A ONE-LINE FIX FALLS INTO, and why `test_unknown_*` below exists.
`start_instance` appends `--dashboard <value>` for anything that is not `both`,
and the child's argparse restricts that flag to city/briefs/both. A stamp
written before the selector existed reports `unknown`. Forwarding it verbatim
would put `--dashboard unknown` on the command line, the child would exit on an
argparse error, and the restart would stop a working dashboard and start
nothing. So the naive fix converts a cosmetic defect into an outage.
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import pytest

from mctl_core import dashboards, mcp_server


class _Scope:
    def __init__(self, city_root: Path) -> None:
        self.city_root = city_root


def _instance(dashboard: str) -> dashboards.DashboardInstance:
    return dashboards.DashboardInstance(
        pid=4242,
        host="127.0.0.1",
        port=8471,
        url="http://127.0.0.1:8471",
        rig="mathcity",
        serving_commit="aaaaaaa",
        started_at="2026-08-29T00:00:00Z",
        dashboard=dashboard,
        current_commit="aaaaaaa",
    )


@pytest.fixture
def restart(monkeypatch, tmp_path):
    """Drive the handler with the process seams replaced.

    Both mutation seams are module-level precisely so a test can do this
    without spawning or killing anything.
    """
    captured: dict[str, object] = {}

    def fake_start(*, city_root, host, port, rig, dashboard="both"):
        captured["dashboard"] = dashboard
        captured["rig"] = rig
        captured["port"] = port
        return {"pid": 5353, "serving_commit": "bbbbbbb", "url": f"http://{host}:{port}"}

    monkeypatch.setattr(dashboards, "start_instance", fake_start)
    monkeypatch.setattr(dashboards, "stop_instance", lambda *a, **k: True)
    monkeypatch.setattr(dashboards, "remove_stamp", lambda *a, **k: None)

    def _run(dashboard: str):
        monkeypatch.setattr(
            dashboards, "discover", lambda *a, **k: [_instance(dashboard)]
        )
        result = mcp_server._handle_dashboard_restart(
            _Scope(tmp_path), {"port": 8471, "dry_run": False}
        )
        return result, captured

    return _run


# --- the defect -------------------------------------------------------------


@pytest.mark.parametrize("selection", ["city", "briefs", "both"])
def test_the_selection_survives_the_rebind(restart, selection) -> None:
    """A restart changes the CODE and nothing else."""
    result, captured = restart(selection)
    assert captured["dashboard"] == selection
    assert result["dashboard"] == selection
    assert result["applied"] is True


def test_a_city_instance_does_not_come_back_as_both(restart) -> None:
    """The exact live reproduction, as a unit."""
    result, captured = restart("city")
    assert captured["dashboard"] != "both"
    assert result["dashboard"] == "city"


def test_the_rest_of_the_binding_still_carries(restart) -> None:
    """Guard: adding the selector must not disturb rig/port threading."""
    _result, captured = restart("briefs")
    assert captured["rig"] == "mathcity"
    assert captured["port"] == 8471


# --- the trap ---------------------------------------------------------------


def test_unknown_is_not_forwarded_as_a_selection(restart) -> None:
    """Forwarding `unknown` would put an invalid flag on the child's command
    line and the replacement would never start."""
    result, captured = restart("unknown")
    assert captured["dashboard"] == "both", "must resolve, never forward"
    assert result["dashboard"] == "both"


def test_unknown_is_reported_rather_than_substituted_quietly(restart) -> None:
    """`both` asserted without a choice is the value dashboard_status refuses
    to invent; if restart writes it, it must say why."""
    result, _captured = restart("unknown")
    codes = [d["code"] for d in result["diagnostics"]]
    assert "MDSH_SELECTOR_UNRECORDED" in codes
    note = next(d for d in result["diagnostics"] if d["code"] == "MDSH_SELECTOR_UNRECORDED")
    assert note["severity"] == "INFO", "a truthful restatement is not a warning"


def test_a_real_selection_emits_no_diagnostic(restart) -> None:
    """The INFO must fire only for the unrecorded case, or it is noise."""
    result, _captured = restart("city")
    assert result["diagnostics"] == []


def test_the_diagnostic_code_is_registered() -> None:
    """#199: a code emitted but absent from the registry is unexplainable."""
    registry = (REPO_ROOT / "assets" / "mctl" / "diagnostics.toml").read_text(encoding="utf-8")
    assert "[MDSH_SELECTOR_UNRECORDED]" in registry
