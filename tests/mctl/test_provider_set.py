"""`provider_set`: the write half of the city-config surface.

WHY THIS EXISTS. mctl ships 57 tools and every config-adjacent one is
READ-ONLY -- city_health, config_readable, pools_status, mayor_city_state.
`pools_status` records the gap in its own docstring ("zero matches for
pool_size, adjust_pool, scale_pool, seats or capacity anywhere in mctl_core").
Issue #197 filed the VISIBILITY half and pools_status closed it. The WRITE half
was never filed, so switching a city's Claude account had no typed path.

On 2026-09-10 that gap was routed around: a standalone `city_provider.py`
script was written and used to move kolchin from claude-agexplained to
claude-primary. That is a P7.3 violation -- "An interface gap is filed, never
routed around" -- and P7.4 ("repeated skill work earns a surface") was already
triggered: config adjustment recurred three times in 24 hours (pool cap lift,
pool cap revert, provider switch).

This tool is that surface. The script is retired into it.

FAILS CLOSED on an unauthenticated target. The failure mode being prevented is
pointing an entire fleet at an account that cannot log in: silent, fleet-wide,
and discovered only when every agent starts failing at once.

FORMAT-PRESERVING. It rewrites exactly one `provider =` line under [workspace]
and never round-trips the document through a TOML dumper -- kolchin's city.toml
carries comments recording standing justifications for every pool cap, and a
dumper would discard all of them.

DRY RUN BY DEFAULT, matching bead_close and every other mutating tool.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "assets" / "scripts"))


def _scope(city: Path):
    """A CityScope for a fixture city, built through the real dataclass."""
    from mctl_core.context import CityScope

    return CityScope(
        city_root=city,
        discovery_path="fixture",
        invocation_cwd=city,
        trace_id="test",
        rigs=(),
        config={},
    )


def _city(tmp_path: Path, *, provider: str = "alpha", auth: bool = True) -> Path:
    city = tmp_path / "city"
    (city).mkdir()
    good = city / "cfg-alpha"
    good.mkdir()
    (good / ".claude.json").write_text(json.dumps(
        {"oauthAccount": {"emailAddress": "alpha@example.com"}}))
    beta = city / "cfg-beta"
    beta.mkdir()
    if auth:
        (beta / ".claude.json").write_text(json.dumps(
            {"oauthAccount": {"emailAddress": "beta@example.com"}}))
    (city / "city.toml").write_text(
        "# standing justification comment that MUST survive\n"
        "[workspace]\n"
        f'provider = "{provider}"\n'
        "\n"
        "[providers.alpha]\n"
        f'env = {{ CLAUDE_CONFIG_DIR = "{good}" }}\n'
        "\n"
        "[providers.beta]\n"
        f'env = {{ CLAUDE_CONFIG_DIR = "{beta}" }}\n'
    )
    return city


def test_tool_is_registered_and_mutating():
    from mctl_core import mcp_server

    spec = next((t for t in mcp_server.TOOLS if t.name == "provider_set"), None)
    assert spec is not None, "provider_set is not in TOOLS"
    assert spec.mutating is True, "a config write must be declared mutating"
    assert spec.scope == mcp_server.CITY_SCOPE


def test_dry_run_is_the_default_and_writes_nothing(tmp_path):
    from mctl_core import mcp_server

    city = _city(tmp_path)
    before = (city / "city.toml").read_text()
    out = mcp_server._handle_provider_set(
        _scope(city), {"provider": "beta"})
    assert out["applied"] is False, "dry_run defaults to True; mutation is opt-in"
    assert (city / "city.toml").read_text() == before, "dry run wrote to disk"


def test_apply_switches_and_preserves_comments(tmp_path):
    from mctl_core import mcp_server

    city = _city(tmp_path)
    out = mcp_server._handle_provider_set(
        _scope(city), {"provider": "beta", "dry_run": False})
    assert out["applied"] is True
    text = (city / "city.toml").read_text()
    assert 'provider = "beta"' in text
    assert "standing justification comment that MUST survive" in text, (
        "the rewrite destroyed a comment -- this is why it must not use a TOML dumper")
    assert out["previous"] == "alpha"


def test_refuses_unauthenticated_target(tmp_path):
    from mctl_core import mcp_server

    city = _city(tmp_path, auth=False)
    out = mcp_server._handle_provider_set(
        _scope(city), {"provider": "beta", "dry_run": False})
    assert out["applied"] is False
    codes = [d.get("code") for d in out.get("diagnostics", [])]
    assert "MPRV_TARGET_NOT_AUTHENTICATED" in codes, codes
    assert 'provider = "alpha"' in (city / "city.toml").read_text()


def test_refuses_undeclared_provider(tmp_path):
    from mctl_core import mcp_server

    city = _city(tmp_path)
    out = mcp_server._handle_provider_set(
        _scope(city), {"provider": "nosuch", "dry_run": False})
    assert out["applied"] is False
    assert "MPRV_NO_SUCH_PROVIDER" in [d.get("code") for d in out.get("diagnostics", [])]


def test_already_on_target_is_idempotent_not_an_error(tmp_path):
    from mctl_core import mcp_server

    city = _city(tmp_path)
    out = mcp_server._handle_provider_set(
        _scope(city), {"provider": "alpha", "dry_run": False})
    assert out["applied"] is False
    assert out.get("already_current") is True
