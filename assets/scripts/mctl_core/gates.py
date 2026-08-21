"""Gate objects for the city dashboard — #119a, the static half.

WHY THE STATISTICS ARE UNKNOWN AND NOT ZERO
-------------------------------------------
The handoff asks a gate row to carry `evaluated`, `passed`, `beads_failing_now`
and `suspect: true` when a gate has had zero failures over a long window, and it
says why that matters:

    "that list is the only way to distinguish a gate that never fails from one
     that never runs."

**This city records no gate outcome anywhere.** Measured 2026-08-20:

  * `mctl_core` has no gate surface at all — `gates_status`, `gates_evaluations`
    and `gate_id` appear in zero files.
  * Bead metadata carries gate *configuration*, never a result: across 161
    distinct keys and 4,462 instances, the gate-shaped keys are
    `gc.check_path` / `gc.check_mode` / `gc.check_timeout` (17 each — *what to
    run*) and `gc.brief.gate_profile` (37 — a profile name).
  * The mctl event and trace sinks hold **0 files**.
  * The only gate-named directories are `gates-candidate-pile` — the pile for
    *proposing* new gates, not a record of evaluations.

So there is no rate to report and no window to judge. Computing these from an
absent source would emit `evaluated: 0, passed: 0` and fire `suspect: true` on
every gate simultaneously — rendering a gate that never ran identically to one
that never failed. That is the precise defect this slice was commissioned to
expose, and honesty invariant §5 forbids it twice over: *"a failed probe never
renders as a value — not zero, not blank"* and *"`None` = there is none,
`Unknown` = we did not look."*

They are therefore `None`, and every response says so out loud via `MGATE001`.
`#119b` fills them in once gate-evaluation recording exists; the working model to
generalize is the no-brainer gate's own sink,
`.beads/briefs/decisions/no-brainer-execution.jsonl`, which already records
timestamp, gate, decision, reason and subject per evaluation.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .diagnostics import Diagnostic, Severity


@dataclass(frozen=True)
class GateRow:
    """One gate. Static fields are read; statistical fields are Unknown (None)."""

    gate_id: str
    rule_id: str | None
    checks: int
    registered_at: str | None
    # --- Unknown until gate-evaluation recording exists (#119b) --------------
    evaluated: int | None = None
    passed: int | None = None
    beads_failing_now: int | None = None
    suspect: bool | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "gate_id": self.gate_id,
            "rule_id": self.rule_id,
            "checks": self.checks,
            "registered_at": self.registered_at,
            "evaluated": self.evaluated,
            "passed": self.passed,
            "beads_failing_now": self.beads_failing_now,
            "suspect": self.suspect,
        }


@dataclass(frozen=True)
class GatesReport:
    gates: tuple[GateRow, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()
    #: False when the gates directory could not be read. Distinguishes
    #: "this city has no gates" from "we could not look" — never collapse them.
    gates_readable: bool = True

    def to_dict(self) -> dict[str, object]:
        return {
            "gates": [row.to_dict() for row in self.gates],
            "gates_readable": self.gates_readable,
            "diagnostics": [d.to_dict() for d in self.diagnostics],
        }


def _registered_at(path: Path) -> str | None:
    try:
        stamp = path.stat().st_mtime
    except OSError:
        return None
    return datetime.fromtimestamp(stamp, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_gate(path: Path) -> GateRow | None:
    """Parse a gate definition.

    Gates are FORMULA-shaped: `description`/`formula`/`version`/`catalog`/`vars`/
    `steps`. There is no `[gate]` table and no `[[checks]]` array. An earlier
    draft of this parser assumed both, matched a fixture that had invented the
    same shape, and returned `checks=0, rule_id=None` for all five real gates
    while its tests were green — the plausible-zero this module exists to refuse.
    The fixture is now copied from real gate files so the two cannot drift apart.

    `catalog.name` is the identifier, not `formula`:
    `server-touching-safety-override.toml` declares `formula = "gate"`, which is
    generic and would collide.
    """
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError):
        return None
    catalog = data.get("catalog")
    catalog = catalog if isinstance(catalog, dict) else {}
    gate_id = catalog.get("name")
    if not isinstance(gate_id, str) or not gate_id:
        formula = data.get("formula")
        gate_id = formula if isinstance(formula, str) and formula != "gate" else path.stem
    steps = data.get("steps")
    steps = steps if isinstance(steps, list) else []
    check_count = sum(1 for step in steps if isinstance(step, dict) and step.get("check"))
    return GateRow(
        gate_id=gate_id,
        # No gate definition carries a rule id today; the field is absent from
        # the schema entirely, so this is "there is none", not "we did not look".
        # MGATE004 says so rather than leaving a bare null to be guessed at.
        rule_id=None,
        checks=check_count,
        registered_at=_registered_at(path),
    )


def gates_status(*, gates_dir: Path) -> GatesReport:
    """Read the gate definitions. Statistics are Unknown and say so.

    `gates_dir` is passed explicitly rather than derived from a context, so this
    function cannot silently compose a path against a working directory that is
    not what the caller meant — the failure mode that made `brief-check.sh`
    report PASS on scans it never ran.
    """
    gates_dir = Path(gates_dir)
    if not gates_dir.is_dir():
        return GatesReport(
            gates=(),
            gates_readable=False,
            diagnostics=(
                Diagnostic(
                    severity=Severity.ERROR,
                    code="MGATE002",
                    message="Gate directory could not be read; the gate set is unknown.",
                    hint=(
                        "An empty gate list here would be indistinguishable from a "
                        "city that defines no gates. It is not a claim that there "
                        "are none."
                    ),
                    data_location=str(gates_dir),
                    suggested_next_command="ls gates/",
                ),
            ),
        )

    rows: list[GateRow] = []
    unreadable: list[str] = []
    for path in sorted(gates_dir.glob("*.toml")):
        row = _read_gate(path)
        if row is None:
            unreadable.append(path.name)
            continue
        rows.append(row)

    diagnostics: list[Diagnostic] = [
        Diagnostic(
            severity=Severity.WARN,
            code="MGATE001",
            message=(
                "Gate statistics are Unknown: this city records no gate evaluation "
                "outcome, so evaluated/passed/beads_failing_now/suspect cannot be "
                "computed."
            ),
            hint=(
                "Reported as null rather than 0. Zero would render a gate that "
                "never ran identically to a gate that never failed, which is the "
                "distinction the gate page exists to make (#119b)."
            ),
            facts={"gates_found": str(len(rows))},
            data_location=str(gates_dir),
            suggested_next_command="mctl briefs doctor --json  # no gate-evaluation surface exists yet; see #119b",
        )
    ]
    if unreadable:
        diagnostics.append(
            Diagnostic(
                severity=Severity.ERROR,
                code="MGATE003",
                message="Gate definition could not be parsed and is missing from the list.",
                hint="The gate set below is short by these files; it is not the whole set.",
                facts={"unreadable": ", ".join(unreadable)},
                data_location=str(gates_dir),
                suggested_next_command="python3 -c 'import tomllib,sys;tomllib.load(open(sys.argv[1],\"rb\"))' gates/<file>.toml",
            )
        )

    return GatesReport(gates=tuple(rows), diagnostics=tuple(diagnostics), gates_readable=True)
