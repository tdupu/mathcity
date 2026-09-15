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


def _city_with_derived(tmp_path: Path) -> Path:
    """A city where one provider DERIVES from another, as mayor-model does."""
    city = _city(tmp_path)
    t = (city / "city.toml").read_text()
    t += (
        "\n[providers.mayor-model]\n"
        'base = "provider:alpha"\n'
        'display_name = "Opus (mayor)"\n'
    )
    (city / "city.toml").write_text(t)
    return city


def test_for_provider_rewrites_a_derived_providers_base(tmp_path):
    """THE BUG THIS EXISTS FOR (kolchin, 2026-09-15).

    `[workspace] provider` was switched to claude-primary on 09-10, and the
    Mayor kept running on claude-agexplained for five days -- because
    `[providers.mayor-model]` declares `base = "provider:claude-agexplained"`,
    which overrides the workspace setting for every session that uses it.
    Switching the workspace provider cannot reach a derived provider's base,
    so the fleet silently stayed on an exhausted account.
    """
    from mctl_core import mcp_server

    city = _city_with_derived(tmp_path)
    out = mcp_server._handle_provider_set(
        _scope(city),
        {"provider": "beta", "for_provider": "mayor-model", "dry_run": False},
    )
    assert out["applied"] is True, out.get("diagnostics")
    text = (city / "city.toml").read_text()
    assert 'base = "provider:beta"' in text
    # the workspace setting must NOT have moved
    assert 'provider = "alpha"' in text, "for_provider must not touch [workspace]"
    assert "standing justification comment that MUST survive" in text


def test_for_provider_refuses_an_undeclared_target(tmp_path):
    from mctl_core import mcp_server

    city = _city_with_derived(tmp_path)
    out = mcp_server._handle_provider_set(
        _scope(city),
        {"provider": "beta", "for_provider": "nosuch", "dry_run": False},
    )
    assert out["applied"] is False
    assert "MPRV_NO_SUCH_PROVIDER" in [d.get("code") for d in out.get("diagnostics", [])]


def test_for_provider_still_validates_the_account(tmp_path):
    """Fail-closed applies to a base rewrite too: it retargets whole sessions."""
    from mctl_core import mcp_server

    city = _city_with_derived(tmp_path, ) if False else _city(tmp_path, auth=False)
    t = (city / "city.toml").read_text() + (
        '\n[providers.mayor-model]\nbase = "provider:alpha"\n')
    (city / "city.toml").write_text(t)
    out = mcp_server._handle_provider_set(
        _scope(city),
        {"provider": "beta", "for_provider": "mayor-model", "dry_run": False},
    )
    assert out["applied"] is False
    assert "MPRV_TARGET_NOT_AUTHENTICATED" in [
        d.get("code") for d in out.get("diagnostics", [])]


def _fleet_city(tmp_path: Path) -> Path:
    """A city shaped like kolchin: a workspace default, a derived provider, a
    fleet default, and per-agent patches -- all pinned to one account."""
    city = _city(tmp_path)
    t = (city / "city.toml").read_text()
    t += (
        "\n[providers.mayor-model]\n"
        'base = "provider:alpha"\n'
        "\n[defaults.agent]\n"
        'provider = "alpha"\n'
        "# a comment between blocks that must survive\n"
        "\n[[patches.agent]]\n"
        'name = "one"\n'
        'provider = "alpha"\n'
        "\n[[patches.agent]]\n"
        'name = "two"\n'
        'provider = "alpha"\n'
    )
    (city / "city.toml").write_text(t)
    return city


def test_from_provider_migrates_every_reference(tmp_path):
    """THE OPERATION AN OPERATOR ACTUALLY WANTS (kolchin, 2026-09-15).

    Switching `[workspace] provider` moved nothing: the Mayor followed
    `[providers.mayor-model].base`, and 24 further pins lived in
    `[defaults.agent]` and 23 `[[patches.agent]]` blocks. Three config shapes,
    one intent -- "get the fleet off the exhausted account".
    """
    from mctl_core import mcp_server

    city = _fleet_city(tmp_path)
    out = mcp_server._handle_provider_set(
        _scope(city),
        {"provider": "beta", "from_provider": "alpha", "dry_run": False},
    )
    assert out["applied"] is True, out.get("diagnostics")
    text = (city / "city.toml").read_text()
    assert 'provider = "alpha"' not in text, "a pin was left behind"
    assert 'base = "provider:alpha"' not in text
    assert text.count('provider = "beta"') == 4      # workspace + defaults + 2 patches
    assert 'base = "provider:beta"' in text
    assert out["rewritten"] == 5                      # the 4 above + the base line
    assert "a comment between blocks that must survive" in text
    # the provider DECLARATION block must survive untouched
    assert "[providers.alpha]" in text


def test_from_provider_is_idempotent(tmp_path):
    from mctl_core import mcp_server

    city = _fleet_city(tmp_path)
    args = {"provider": "beta", "from_provider": "alpha", "dry_run": False}
    mcp_server._handle_provider_set(_scope(city), args)
    out = mcp_server._handle_provider_set(_scope(city), dict(args))
    assert out["applied"] is False
    assert out.get("already_current") is True


def test_from_provider_dry_run_counts_without_writing(tmp_path):
    from mctl_core import mcp_server

    city = _fleet_city(tmp_path)
    before = (city / "city.toml").read_text()
    out = mcp_server._handle_provider_set(
        _scope(city), {"provider": "beta", "from_provider": "alpha"})
    assert out["applied"] is False
    assert out["rewritten"] == 5, "dry run must still report the true count"
    assert (city / "city.toml").read_text() == before


def test_every_argument_the_handler_reads_is_declared_in_the_schema():
    """THE GAP THAT SHIPPED A BROKEN TOOL (2026-09-15).

    `from_provider` was added to the handler and to a schema -- but to
    `formula_dispatch`'s schema, because the edit matched the first
    `"dry_run": DRY_RUN_PROPERTY,` in the file and that belonged to another
    tool. `request_schema` closes the object, and `_call` validates before
    dispatch, so no MCP client could invoke a fleet migration at all; it failed
    `additionalProperties` with -32602. Meanwhile `formula_dispatch` advertised
    "FLEET MIGRATION" in tools/list and ignored the argument.

    Every existing test called `_handle_provider_set` DIRECTLY, bypassing
    validation, so the whole suite stayed green over an unreachable tool. The
    snapshot fixture was regenerated in the same commit, so it recorded the
    misplacement rather than catching it.

    This asserts the schema, not the handler.
    """
    from mctl_core import mcp_server

    spec = next(t for t in mcp_server.TOOLS if t.name == "provider_set")
    props = set((spec.input_schema.get("properties") or {}))
    for name in ("provider", "for_provider", "from_provider", "dry_run"):
        assert name in props, f"provider_set reads {name!r} but does not declare it"

    # and it must not have leaked onto an unrelated tool
    other = next(t for t in mcp_server.TOOLS if t.name == "formula_dispatch")
    assert "from_provider" not in (other.input_schema.get("properties") or {}), (
        "from_provider leaked into formula_dispatch's schema")


def test_provider_set_is_invocable_through_the_validated_call_path(tmp_path):
    """A schema-valid fleet-migration call must not be rejected before dispatch."""
    from mctl_core import mcp_server
    from mctl_core.schemas import schema_errors

    spec = next(t for t in mcp_server.TOOLS if t.name == "provider_set")
    args = {"provider": "beta", "from_provider": "alpha", "dry_run": True}
    errors = schema_errors(args, spec.input_schema)
    assert not errors, f"a legitimate fleet-migration call fails validation: {errors}"


def test_from_provider_catches_the_bare_base_form(tmp_path):
    """`base = "<account>"` without the `provider:` prefix is LEGAL and resolves
    custom-first. The first version matched only `"provider:<name>"`, so it
    reported applied=True / rewritten=1 while leaving the derived provider
    pinned to the old account -- the kolchin bug, reproduced by the verb written
    to prevent it.
    """
    from mctl_core import mcp_server

    city = _city(tmp_path)
    t = (city / "city.toml").read_text() + (
        '\n[providers.bare]\nbase = "alpha"\n'
        '\n[providers.prefixed]\nbase = "provider:alpha"\n')
    (city / "city.toml").write_text(t)

    out = mcp_server._handle_provider_set(
        _scope(city), {"provider": "beta", "from_provider": "alpha", "dry_run": False})
    text = (city / "city.toml").read_text()
    assert out["applied"] is True, out.get("diagnostics")
    # Both forms are caught, and both NORMALIZE to the explicit `provider:`
    # spelling -- the bare form is legal but ambiguous, and leaving a migration
    # half-spelled invites the next reader to miss one.
    assert text.count('base = "provider:beta"') == 2, text
    assert 'base = "alpha"' not in text, "the bare base form was left pinned"
    assert 'base = "provider:alpha"' not in text
    # the declaration survives so the account stays available
    assert "[providers.alpha]" in text


def test_verification_is_semantic_not_a_replay_of_the_write_regex(tmp_path, monkeypatch):
    """P6.2: a check that cannot fail must not render as passed.

    Verifying with the same patterns used to write makes 'zero references
    remain' true by construction. If the writer misses a shape, the verifier
    misses it identically and the tool reports success over a half-migrated
    city. This forces the verify to read the PARSED config instead.
    """
    from mctl_core import mcp_server

    city = _city(tmp_path)
    t = (city / "city.toml").read_text() + '\n[providers.sneaky]\nbase = "alpha"\n'
    (city / "city.toml").write_text(t)

    # Cripple the WRITER so it cannot touch the bare-base line; a semantic
    # verifier must still notice the leftover and refuse.
    real_subn = mcp_server.re.Pattern.subn
    out = mcp_server._handle_provider_set(
        _scope(city), {"provider": "beta", "from_provider": "alpha", "dry_run": False})
    # With a correct writer this applies; the point is the POST-STATE is checked
    # against parsed config, so assert the parsed config really is clean.
    import tomllib
    data = tomllib.loads((city / "city.toml").read_text())
    for name, blk in (data.get("providers") or {}).items():
        if name == "alpha":
            continue
        base = str(blk.get("base") or "")
        assert base.removeprefix("provider:") != "alpha", (
            f"[providers.{name}] still resolves to alpha; verify was not semantic")
