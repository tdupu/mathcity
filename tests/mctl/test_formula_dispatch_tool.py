"""#256 -- the typed surface lists every formula the city knows and can run none of them.

`formulas_catalog` reports 96 formulas. No tool on the surface dispatches one.
An agent restricted to the MCP can enumerate the entire catalogue and invoke
none of it, so the only way to actually run a formula is to leave the surface
for `gc sling` -- which is the gap `CT13.1` names.

THE PROPERTY THAT MATTERS MOST HERE is what the tool REFUSES. A dispatch tool
that accepted a caller-supplied command string, or a formula name it never
checked against the catalogue, would faithfully run whatever it was handed with
the full authority of the typed surface -- which is worse than the shell, not
better, because the answer would be believed harder. Same shape as
`artifact_locate` refusing to take a path.

    caller passes a FORMULA NAME  ->  resolved against the catalogue  ->  typo is caught
    caller passes a COMMAND       ->  the tool is a slower, more trusted `gc sling`

So `test_the_tool_refuses_an_unknown_formula` and
`test_the_tool_takes_no_command_string` are the load-bearing tests in this file.

The second property, inherited from `work_dispatch` and asserted again here
because a new mutating tool is exactly where it gets dropped: dispatch is a
WRITE, so it must be dry-run by default and must report an effect plan. A tool
that slung on the first call, before the caller had seen what it would run,
would be the one mistake this surface cannot take back.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))


def _server():
    from mctl_core.mcp_server import MctlMcpServer

    return MctlMcpServer(default_city=Path("<city-root>"), client_class="internal")


def _spec(name: str):
    from mctl_core.mcp_server import TOOLS

    for spec in TOOLS:
        if spec.name == name:
            return spec
    return None


def test_the_surface_has_a_formula_dispatch_tool() -> None:
    """The gap itself: 96 formulas listed, none runnable."""
    assert _spec("formula_dispatch") is not None, (
        "formulas_catalog lists the whole catalogue and no tool runs any of it (#256)"
    )


def test_the_tool_takes_no_command_string() -> None:
    """A command parameter would make this a slower shell with more authority."""
    spec = _spec("formula_dispatch")
    assert spec is not None
    props = spec.input_schema.get("properties", {})
    for banned in ("command", "argv", "shell", "cmd"):
        assert banned not in props, (
            f"formula_dispatch must not accept {banned!r}: a caller-supplied command "
            "turns the typed surface into an unaudited shell"
        )


def test_the_tool_names_a_formula_and_carries_vars() -> None:
    """`gc sling` needs a formula and its vars; #256 measured that vars are the
    reason the existing dispatch-shaped tools cannot stand in."""
    spec = _spec("formula_dispatch")
    assert spec is not None
    props = spec.input_schema.get("properties", {})
    assert "formula" in props, "no formula parameter -- the defect in #256"
    assert "vars" in props, (
        "no vars parameter -- work_dispatch already fails this way, which is why "
        "#256 had to shell out to `gc sling --var`"
    )


def test_the_tool_is_mutating_and_dry_run_by_default() -> None:
    """Dispatch is a write. The caller must be able to see the command first."""
    spec = _spec("formula_dispatch")
    assert spec is not None
    assert spec.mutating is True, "dispatch is a write and must be declared mutating"
    assert "dry_run" in spec.input_schema.get("properties", {})


def test_the_tool_refuses_an_unknown_formula() -> None:
    """Resolution against the catalogue is the whole safety property.

    A typo must come back as a refusal naming the unknown formula, not as a
    sling of a name the city has never heard of.
    """
    from mctl_core.formula_dispatch import plan_formula_dispatch

    plan = plan_formula_dispatch(
        formula="definitely-not-a-real-formula",
        catalogue=("do-work", "review", "brief-prep"),
        target="myrig/gc.run-operator",
        bead_id=None,
        variables={},
    )
    assert plan["ok"] is False
    assert plan["code"] == "MFRM_UNKNOWN_FORMULA"
    assert "definitely-not-a-real-formula" in plan["message"]


def test_a_known_formula_plans_a_sling_with_its_vars() -> None:
    """The command is built, not typed: every var becomes its own `--var` pair."""
    from mctl_core.formula_dispatch import plan_formula_dispatch

    plan = plan_formula_dispatch(
        formula="brief-prep",
        catalogue=("do-work", "brief-prep"),
        target="myrig/gc.run-operator",
        bead_id=None,
        variables={"brief_slug": "s", "source": "SUBJECT.md"},
    )
    assert plan["ok"] is True
    command = plan["command"]
    assert command[:2] == ["gc", "sling"]
    assert "myrig/gc.run-operator" in command
    assert "--formula" in command
    assert "brief-prep" in command
    # Vars are passed as separate argv entries, never joined into one string.
    for key, value in (("brief_slug", "s"), ("source", "SUBJECT.md")):
        assert f"{key}={value}" in command
        assert command[command.index(f"{key}={value}") - 1] == "--var"


def test_a_bead_id_selects_the_targeted_on_form() -> None:
    """#256 measured both shapes. A convoy-targeted formula needs `--on <bead>`;
    passing a bead must not silently produce the untargeted `--formula` form,
    which is the error `convoy_id requires a targeted formulas v2 invocation`.
    """
    from mctl_core.formula_dispatch import plan_formula_dispatch

    plan = plan_formula_dispatch(
        formula="do-work",
        catalogue=("do-work",),
        target="myrig/gc.run-operator",
        bead_id="mc-123",
        variables={},
    )
    assert plan["ok"] is True
    command = plan["command"]
    assert "--on" in command
    assert command[command.index("--on") + 1] == "do-work"
    assert "mc-123" in command
    assert "--formula" not in command


def test_variable_values_are_never_shell_joined() -> None:
    """A value containing a space or a quote must survive as ONE argv entry.

    This is the injection guard. If the command were ever assembled by joining
    on spaces, a value like `a b` would split into two arguments and a value
    containing `;` would end the command.
    """
    from mctl_core.formula_dispatch import plan_formula_dispatch

    plan = plan_formula_dispatch(
        formula="review",
        catalogue=("review",),
        target="myrig/gc.run-operator",
        bead_id=None,
        variables={"report_path": "a b; rm -rf /"},
    )
    assert plan["ok"] is True
    assert "report_path=a b; rm -rf /" in plan["command"]
