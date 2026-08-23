"""commission_brief as a typed MCP tool (#190, registration half).

The core landed at ebd80cd as pure functions. This wires it to the MCP surface.

WHY THIS IS A SEPARATE BRANCH FROM THE CORE. Adding a tool touches six
declarations that must agree -- mcp_server, DECLARED_TOOLS, the harness
EXPECTED_TOOLS, the schema snapshot, the dashboard allowlist, and the
diagnostics registry -- two of which are ORDERED tuples that conflict on
insertion. Three agents were queued to add tools; the agreed order was
#168 -> #170 -> this, so the tax is paid once per branch instead of three times
concurrently.

THE DESIGN POINT THESE TESTS EXIST TO PIN. `CommissionRefused` is an EXCEPTION
in the core, which is right for a library: a caller that ignores it gets a
traceback rather than a silent half-commission. At the TOOL boundary an
exception is wrong -- it escapes the response envelope, so the caller gets a
crash instead of a diagnostic with a code they can branch on. The refusal must
become a FATAL diagnostic, and the plan must not be applied.

That conversion is the whole substance of this branch. Everything else is
declarations.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

TOOL = "commission_brief"


class TestTheToolIsRegistered:
    def test_it_exists_on_the_mcp_surface(self):
        from mctl_core.mcp_server import TOOLS_BY_NAME

        assert TOOL in TOOLS_BY_NAME

    def test_it_is_mutating_and_therefore_dry_run_by_default(self):
        from mctl_core.mcp_server import TOOLS_BY_NAME

        schema = TOOLS_BY_NAME[TOOL].input_schema
        assert schema["properties"]["dry_run"]["default"] is True, (
            "a tool that creates a bead must preview by default"
        )

    def test_it_requires_a_source_bead(self):
        """The constraint that cost a bricked brief. Required at the SCHEMA
        level, so the refusal happens before a caller can omit it."""
        from mctl_core.mcp_server import TOOLS_BY_NAME

        schema = TOOLS_BY_NAME[TOOL].input_schema
        assert "bead_id" in schema.get("required", [])


class TestRefusalBecomesADiagnostic:
    """The design point. An exception at a tool boundary escapes the envelope."""

    def test_the_handler_catches_CommissionRefused(self):
        source = (SCRIPTS_ROOT / "mctl_core" / "mcp_server.py").read_text(encoding="utf-8")
        handler = source.split("def _handle_commission_brief", 1)
        assert len(handler) == 2, "the handler is missing"
        # Bounded by the NEXT function, not a character count. Two earlier
        # versions of this pattern (600 and 1200 chars) passed or failed on
        # docstring length rather than on behaviour. Third time; structure now.
        body = handler[1].split("\ndef ", 1)[0]
        assert "CommissionRefused" in body, (
            "an uncaught CommissionRefused escapes the response envelope: the caller "
            "gets a traceback instead of a diagnostic code it can branch on"
        )

    def test_the_refusal_carries_the_core_s_own_code(self):
        """`MCMS_SOURCES_REQUIRED` / `MCMS_CROSS_STORE_SOURCE` are set by the
        core. The handler must surface them, not invent a generic one."""
        source = (SCRIPTS_ROOT / "mctl_core" / "mcp_server.py").read_text(encoding="utf-8")
        body = source.split("def _handle_commission_brief", 1)[1].split("\ndef ", 1)[0]
        assert ".code" in body, "the diagnostic must carry the refusal's own code"

    def test_a_refusal_does_not_apply_the_plan(self):
        source = (SCRIPTS_ROOT / "mctl_core" / "mcp_server.py").read_text(encoding="utf-8")
        body = source.split("def _handle_commission_brief", 1)[1].split("\ndef ", 1)[0]
        refusal = body.split("except CommissionRefused", 1)[1]
        assert "return" in refusal, "the handler must return on refusal, not fall through"


class TestTheDiagnosticCodesAreRegistered:
    """The guard that caught me on #111 and that brad's orders.py bypassed by
    using bare strings. These codes come from the core, so they must be
    declared even though the core does not import the registry."""

    def _registry(self):
        import tomllib

        return tomllib.loads(
            (REPO_ROOT / "assets" / "mctl" / "diagnostics.toml").read_text(encoding="utf-8")
        )

    def test_sources_required_is_registered(self):
        assert "MCMS_SOURCES_REQUIRED" in self._registry()

    def test_cross_store_is_registered(self):
        assert "MCMS_CROSS_STORE_SOURCE" in self._registry()

    def test_both_are_FATAL_because_both_refuse_before_writing(self):
        registry = self._registry()
        for code in ("MCMS_SOURCES_REQUIRED", "MCMS_CROSS_STORE_SOURCE"):
            assert registry[code]["severity"] == "FATAL", (
                f"{code} stops the operation; WARN would imply it proceeded"
            )


class TestTheSixDeclarationsAgree:
    """Adding a tool means six lists must agree. Each of these failed on #111."""

    def test_declared_tools_names_it(self):
        from tests.mctl import test_mcp_server as t  # noqa: F401

        source = (REPO_ROOT / "tests" / "mctl" / "test_mcp_server.py").read_text(encoding="utf-8")
        assert f'"{TOOL}"' in source

    def test_the_harness_expects_it(self):
        source = (SCRIPTS_ROOT / "mctl_mcp_harness.py").read_text(encoding="utf-8")
        assert f'"{TOOL}"' in source

    def test_the_dashboard_may_call_it(self):
        from mctl_dashboard.client import ALLOWED_TOOLS

        assert TOOL in ALLOWED_TOOLS

    def test_the_reachability_guard_is_satisfied(self):
        """My own #111 guard: every registered tool is allowlisted or
        deliberately excluded. This tool must not be the one that trips it."""
        from mctl_core.mcp_server import TOOLS
        from mctl_dashboard.client import ALLOWED_TOOLS

        from tests.mctl.test_dashboard_tool_reachability import DELIBERATELY_UNREACHABLE

        server = {tool.name for tool in TOOLS}
        unaccounted = sorted(server - set(ALLOWED_TOOLS) - set(DELIBERATELY_UNREACHABLE))
        assert not unaccounted, f"unaccounted tools: {unaccounted}"
