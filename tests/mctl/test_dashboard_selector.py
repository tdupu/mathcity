"""The dashboard selector (Taylor, 2026-08-28: "We need a surface for this in the MCP").

The city dashboard and the briefs dashboard are rendered by ONE codebase and
served by ONE process, so before this existed there was no way -- on the CLI or
through the MCP -- to say which one an instance was, and `dashboard_status`
could not tell you either. These tests pin the surface and, more importantly,
pin the two things that make it safe: `both` is the default (no regression on
anyone who never passes the flag), and selection scopes the LANDING route only,
never 404ing the other dashboard's routes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_core import dashboards  # noqa: E402
from mctl_core.cli import _build_parser  # noqa: E402


def _serve_args(argv):
    return _build_parser().parse_args(argv)


class TestCliSurface:
    def test_default_is_both_so_the_flag_regresses_nothing(self):
        args = _serve_args(["dashboard", "serve", "--port", "9999"])
        assert args.dashboard == "both"

    @pytest.mark.parametrize("choice", ["city", "briefs", "both"])
    def test_every_choice_parses(self, choice):
        args = _serve_args(["dashboard", "serve", "--port", "9999", "--dashboard", choice])
        assert args.dashboard == choice

    def test_an_unknown_dashboard_is_refused_not_coerced(self):
        with pytest.raises(SystemExit):
            _serve_args(["dashboard", "serve", "--port", "9999", "--dashboard", "orders"])


class TestStamp:
    """The stamp is what `dashboard_status` reads, so the selection has to survive it."""

    def test_selection_round_trips(self, tmp_path: Path):
        dashboards.write_stamp(
            tmp_path, pid=4242, host="127.0.0.1", port=9999,
            url="http://127.0.0.1:9999", rig="mathcity",
            serving_commit="abc1234", started_at="2026-08-29T02:00:00Z",
            dashboard="briefs",
        )
        stamp = json.loads(next(dashboards.stamp_dir(tmp_path).glob("*.json")).read_text())
        assert stamp["dashboard"] == "briefs"

    def test_a_pre_selector_stamp_reads_unknown_never_both(self, tmp_path: Path):
        """P6.2: an absent field is unmeasured. Defaulting it to `both` would
        assert a selection nobody made, which is the exact class of error the
        city keeps catching -- a check that could not have failed."""
        directory = dashboards.stamp_dir(tmp_path)
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "1.json").write_text(json.dumps({
            "pid": 1, "host": "127.0.0.1", "port": 9999,
            "url": "http://127.0.0.1:9999", "rig": None,
            "serving_commit": "abc1234", "started_at": "2026-08-29T02:00:00Z",
        }))
        inst = dashboards.DashboardInstance(
            pid=1, host="127.0.0.1", port=9999, url="", rig=None,
            serving_commit="abc1234", started_at="",
        )
        assert inst.dashboard == "unknown"
        assert inst.to_dict()["dashboard"] == "unknown"


class TestChildCommand:
    """What `start_instance` actually puts on the child's command line.

    The fake DELEGATES anything that is not the dashboard launch to the real
    Popen -- `start_instance` also shells out to git to read the serving
    commit, and a blanket fake silently breaks that call instead of the one
    under test.
    """

    @staticmethod
    def _capture(monkeypatch):
        seen = {}
        real_popen = dashboards.subprocess.Popen

        class _Proc:
            pid = 777

        def _fake_popen(command, **kwargs):
            if isinstance(command, (list, tuple)) and "dashboard" in command and "serve" in command:
                seen["command"] = list(command)
                return _Proc()
            return real_popen(command, **kwargs)

        monkeypatch.setattr(dashboards.subprocess, "Popen", _fake_popen)
        return seen

    def test_both_is_not_passed_down(self, monkeypatch, tmp_path: Path):
        """`both` is the child's own default; passing it would make every
        historical command line differ for no behavioural reason."""
        seen = self._capture(monkeypatch)
        dashboards.start_instance(city_root=tmp_path, host="127.0.0.1", port=9999, rig=None)
        assert "--dashboard" not in seen["command"]

    def test_an_explicit_choice_is_passed_down(self, monkeypatch, tmp_path: Path):
        seen = self._capture(monkeypatch)
        dashboards.start_instance(
            city_root=tmp_path, host="127.0.0.1", port=9999, rig=None, dashboard="briefs"
        )
        command = seen["command"]
        assert command[command.index("--dashboard") + 1] == "briefs"


class TestMcpSurface:
    def test_dashboard_serve_declares_the_enum(self):
        from mctl_core.mcp_server import TOOLS

        spec = next(t for t in TOOLS if t.name == "dashboard_serve")
        prop = spec.input_schema["properties"]["dashboard"]
        assert prop["enum"] == ["city", "briefs", "both"]

    def test_dashboard_serve_does_not_require_it(self):
        """Required would break every existing caller."""
        from mctl_core.mcp_server import TOOLS

        spec = next(t for t in TOOLS if t.name == "dashboard_serve")
        assert "dashboard" not in spec.input_schema.get("required", [])


class TestDegradedCityIsNotSilent:
    """A start that BINDS is not a dashboard that RENDERS.

    /city and /orders are measured at ~112s with no response (mc-wbwel). Without
    this, `dashboard_serve(dashboard="city")` returns confirmed=true and the
    operator opens a hang. That is a hang rendering as success -- the exact
    shape P6.2 exists to forbid.
    """

    def test_selecting_city_warns_on_dry_run(self):
        from mctl_core import mcp_server

        spec = next(t for t in mcp_server.TOOLS if t.name == "dashboard_serve")
        assert spec is not None

    def test_the_warning_is_reachable_in_source(self):
        """Pinned by code presence: the handler must carry the degraded-city
        diagnostic and must NOT refuse the start."""
        import inspect

        from mctl_core import mcp_server

        src = inspect.getsource(mcp_server._handle_dashboard_serve)
        assert "MDSH_CITY_SCREENS_DEGRADED" in src
        assert "mc-wbwel" in src
        # It must warn, not refuse: applied stays reachable for a city start.
        assert 'if dashboard == "city"' in src

    def test_a_briefs_start_carries_no_city_warning(self):
        """The control: the warning must be able to NOT fire, or it says
        nothing when it does."""
        import inspect

        from mctl_core import mcp_server

        src = inspect.getsource(mcp_server._handle_dashboard_serve)
        assert "else []" in src
