"""Dispatch a named formula from the typed surface (#256).

`formulas_catalog` has always been able to report every formula the city knows.
Nothing could run one. The only dispatch-shaped tools were `work_dispatch`
(brief-backed, no formula parameter, no vars), `commission_brief` (produces a
brief, not a molecule) and `work_dispatch_event` (records a sling that already
happened) -- so an agent restricted to the MCP could enumerate the whole
catalogue and invoke none of it, and every real dispatch left the surface for a
hand-typed `gc sling`. That is the gap `CT13.1` names.

WHAT THIS MODULE DELIBERATELY DOES NOT DO
-----------------------------------------
It does not accept a command. `work.py::_formula_invocation` builds the
`work-briefed` sling argv by hand for exactly one formula; the fix for #256 is
NOT to let a caller hand in the argv for any other one. A caller-supplied
command string would run with the authority of the typed surface while being
audited less than a shell, which is strictly worse than the shell it replaced.

So the caller names a formula and supplies variables as data, and the argv is
composed here. Two consequences fall out of that and both are load-bearing:

  * a formula the city does not have is refused by name, not slung and left to
    fail somewhere downstream where the caller cannot see it;
  * a variable value is one argv entry, always. Nothing is joined on spaces, so
    a value containing a space, a quote or a `;` cannot become two arguments or
    end the command.

THE TWO INVOCATION SHAPES ARE NOT INTERCHANGEABLE
-------------------------------------------------
Measured in #256 and again during the kolchin formula sweep: a formula that
references `{{convoy_id}}` or carries a drain step requires a TARGETED
invocation and fails instantiation with

    convoy_id requires a targeted formulas v2 invocation

if slung untargeted. The two shapes are

    gc sling <target> <bead> --on <formula> [--var k=v ...]     targeted
    gc sling <target> <formula> --formula   [--var k=v ...]     untargeted

Passing a bead selects the first; omitting one selects the second. They are
chosen by the caller's data rather than guessed, because guessing wrong
produces an instantiation error that reads like a defect in the formula.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

__all__ = ["plan_formula_dispatch"]

UNKNOWN_FORMULA = "MFRM_UNKNOWN_FORMULA"
NO_TARGET = "MFRM_NO_TARGET"
BAD_VARIABLE = "MFRM_BAD_VARIABLE"


def _refusal(code: str, message: str, **extra: Any) -> dict[str, Any]:
    return {"ok": False, "code": code, "message": message, **extra}


def plan_formula_dispatch(
    *,
    formula: str,
    catalogue: Iterable[str],
    target: str,
    bead_id: str | None,
    variables: Mapping[str, str] | None,
) -> dict[str, Any]:
    """Compose the `gc sling` argv for `formula`, or refuse and say why.

    Pure: builds a plan and runs nothing. The caller applies it, which is what
    keeps this dry-runnable and lets the tool show the command before it runs.
    """
    known = tuple(catalogue)
    if formula not in known:
        # Named, not just rejected: a typo is the common case and the caller
        # cannot fix it from a bare "unknown formula".
        suggestions = [name for name in known if formula and name.startswith(formula[:4])]
        return _refusal(
            UNKNOWN_FORMULA,
            f"no formula named {formula!r} in this city's catalogue "
            f"({len(known)} known)",
            formula=formula,
            did_you_mean=sorted(suggestions)[:5],
        )

    if not target:
        return _refusal(
            NO_TARGET,
            "a dispatch needs a target agent, e.g. '<rig>/gc.run-operator'",
            formula=formula,
        )

    items = dict(variables or {})
    for key, value in items.items():
        if not isinstance(key, str) or not key or "=" in key:
            return _refusal(
                BAD_VARIABLE,
                f"variable name {key!r} is unusable: names must be non-empty and "
                "must not contain '='",
                formula=formula,
            )
        if not isinstance(value, str):
            return _refusal(
                BAD_VARIABLE,
                f"variable {key!r} must be a string; got {type(value).__name__}. "
                "Formula variables are substituted as text.",
                formula=formula,
            )

    command: list[str] = ["gc", "sling", target]
    if bead_id:
        command += [bead_id, "--on", formula]
    else:
        command += [formula, "--formula"]

    # One argv entry per var. Never joined -- see the module docstring.
    for key in sorted(items):
        command += ["--var", f"{key}={items[key]}"]

    return {
        "ok": True,
        "formula": formula,
        "target": target,
        "bead_id": bead_id,
        "invocation": "targeted" if bead_id else "untargeted",
        "variables": items,
        "command": command,
    }


def apply_formula_dispatch(plan: Mapping[str, Any], *, timeout: float | None = None) -> dict[str, Any]:
    """Run a planned sling, reusing work.py's timeout vocabulary.

    Deliberately NOT a second dispatch engine. `work.py` owns the bounded
    dispatch loop for brief-backed work -- its deadline policy, its elapsed
    notices, its claim-observation on timeout. Re-implementing that here would
    create exactly the second resolution rule this module's docstring warns
    about, and the two would drift.

    What this does instead is run the composed argv and hand any failure to
    `classify_dispatch_subprocess_error`, the SAME classifier, so a timeout
    here means what a timeout there means: the command RAN and we stopped
    waiting. `applied: null` is that verdict, and it is not `applied: false`
    -- reporting our own impatience as the city's failure is what invites a
    caller to double-dispatch (#184).
    """
    import subprocess

    from .work import classify_dispatch_subprocess_error

    command = list(plan["command"])
    try:
        completed = subprocess.run(  # noqa: S603
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except BaseException as error:  # noqa: BLE001
        verdict = classify_dispatch_subprocess_error(error)
        return {
            "applied": verdict.applied,
            "command": command,
            "formula": plan["formula"],
            "outcome": "unknown",
            "detail": str(error),
        }

    ok = completed.returncode == 0
    return {
        "applied": ok,
        "command": command,
        "formula": plan["formula"],
        "outcome": "dispatched" if ok else "refused-by-gc",
        "exit_code": completed.returncode,
        "stdout": (completed.stdout or "").strip()[-2000:],
        "stderr": (completed.stderr or "").strip()[-2000:],
    }
