"""City-wide fleet roster: occupied sessions AND empty slots, in one list.

A table shows presence; only a grid shows absence (dashboard handoff `#112`).
`gc status --json` enumerates every *configured* agent slot for this city,
running or not; `gc session list --json` enumerates every *actual* session.
Joining them on the qualified slot name is what turns "N sessions" into "N of
M slots, M-N empty" -- the thing neither call answers alone.

`limit_state` is a declared gap, not a guess: nothing in this city records
per-agent quota/usage-window state today (dashboard handoff §4.5), so every
row's `limit_state` is `"unknown"` and `MCTL_FLEET_LIMIT_STATE_UNRECORDED`
says why. A rolling-window stall is fixed by a nudge and a weekly stall is
not -- guessing between them would be worse than saying neither is known.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import subprocess
from pathlib import Path
from typing import Mapping, Sequence

from .context import CityScope
from .diagnostics import Diagnostic, Severity

#: `gc` writes a zero-value Go time for "never" rather than null.
_NEVER_ACTIVE_SENTINEL = "0001-01-01T00:00:00Z"

STATUS_PROBE_TIMEOUT_SECONDS = 30.0
SESSION_LIST_TIMEOUT_SECONDS = 30.0


@dataclass(frozen=True)
class FleetSlot:
    """One row: an occupied session, or a configured-but-empty slot.

    `occupied` is the discriminant the page renders on. An empty slot still
    carries `template` and `qualified_name` -- what *would* run there -- so
    the row says what is missing, not just that something is.
    """

    qualified_name: str
    template: str | None
    occupied: bool
    state: str | None
    holds: str | None  # session id / bead this slot currently carries, if any
    model: str | None
    account: str | None
    limit_state: str  # always "unknown" today -- see module docstring
    idle_for_seconds: float | None
    idle_reason: str | None  # populated when idle_for_seconds is None

    def to_dict(self) -> dict[str, object]:
        return {
            "account": self.account,
            "holds": self.holds,
            "idle_for_seconds": self.idle_for_seconds,
            "idle_reason": self.idle_reason,
            "limit_state": self.limit_state,
            "model": self.model,
            "occupied": self.occupied,
            "qualified_name": self.qualified_name,
            "state": self.state,
            "template": self.template,
        }


@dataclass(frozen=True)
class FleetReport:
    slots: tuple[FleetSlot, ...]
    diagnostics: tuple[Diagnostic, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {"slots": [slot.to_dict() for slot in self.slots]}


def _run_json(command: Sequence[str], *, timeout: float) -> tuple[Mapping[str, object] | None, str]:
    try:
        result = subprocess.run(
            list(command), text=True, capture_output=True, check=False, timeout=timeout
        )
    except subprocess.TimeoutExpired:
        return None, f"{command[0]} did not answer within {timeout}s"
    except OSError as error:
        return None, f"{command[0]} could not be run: {error}"
    text = result.stdout
    start = text.find("{")
    if start == -1:
        return None, f"{command[0]} produced no JSON object (exit {result.returncode})"
    try:
        payload = json.loads(text[start:])
    except json.JSONDecodeError as error:
        return None, f"{command[0]} produced unparseable JSON: {error}"
    if not isinstance(payload, dict):
        return None, f"{command[0]} produced a non-object JSON value"
    return payload, ""


def _idle_for_seconds(last_active: object) -> tuple[float | None, str | None]:
    if not isinstance(last_active, str) or last_active == _NEVER_ACTIVE_SENTINEL:
        return None, "never active"
    try:
        stamp = datetime.fromisoformat(last_active.replace("Z", "+00:00"))
    except ValueError:
        return None, f"unparseable last_active: {last_active!r}"
    return (datetime.now(timezone.utc) - stamp).total_seconds(), None


def build_fleet_sessions(scope: CityScope) -> FleetReport:
    """Assemble the full slot list. The only entry point this module exposes."""
    diagnostics: list[Diagnostic] = []

    status_payload, status_detail = _run_json(
        ["gc", "status", "--json", "--city", str(scope.city_root)],
        timeout=STATUS_PROBE_TIMEOUT_SECONDS,
    )
    session_payload, session_detail = _run_json(
        ["gc", "session", "list", "--json", "--state", "all", "--city", str(scope.city_root)],
        timeout=SESSION_LIST_TIMEOUT_SECONDS,
    )

    if status_payload is None:
        diagnostics.append(
            Diagnostic(
                severity=Severity.ERROR,
                code="MCTL_FLEET_STATUS_PROBE_FAILED",
                message="Could not read the configured agent roster.",
                hint=status_detail,
                facts={"city_path": str(scope.city_root), "data_location": status_detail},
                trace_id=scope.trace_id,
            )
        )
    if session_payload is None:
        diagnostics.append(
            Diagnostic(
                severity=Severity.ERROR,
                code="MCTL_FLEET_SESSION_LIST_FAILED",
                message="Could not read the live session list.",
                hint=session_detail,
                facts={"city_path": str(scope.city_root), "data_location": session_detail},
                trace_id=scope.trace_id,
            )
        )

    # Index live sessions by the same qualified-name shape `gc status`
    # publishes: "<rig>/<agent_name>" when the session carries a rig, else
    # bare "<agent_name>". This join key is not documented anywhere as
    # stable -- it is inferred from both commands' live output on
    # 2026-08-20 -- so a mismatch here is a real risk, not a typo; see
    # MCTL_FLEET_JOIN_KEY_UNVERIFIED below.
    sessions_by_key: dict[str, Mapping[str, object]] = {}
    for session in (session_payload or {}).get("sessions") or []:
        if not isinstance(session, dict):
            continue
        agent_name = session.get("agent_name")
        if not isinstance(agent_name, str):
            continue
        rig = session.get("rig")
        key = f"{rig}/{agent_name}" if isinstance(rig, str) and rig else agent_name
        sessions_by_key[key] = session

    diagnostics.append(
        Diagnostic(
            severity=Severity.INFO,
            code="MCTL_FLEET_JOIN_KEY_UNVERIFIED",
            message=(
                "Slots are joined to sessions by '<rig>/<agent_name>' inferred from live "
                "output, not a documented contract between `gc status` and `gc session list`. "
                "A slot reporting occupied=false while a session for it visibly exists is this "
                "join failing, not an empty slot."
            ),
            hint="Verify against a live, running city before trusting occupied=false at scale.",
            facts={"city_path": str(scope.city_root)},
            trace_id=scope.trace_id,
        )
    )

    diagnostics.append(
        Diagnostic(
            severity=Severity.INFO,
            code="MCTL_FLEET_LIMIT_STATE_UNRECORDED",
            message=(
                "limit_state is always 'unknown': no quota/usage-window recording exists yet "
                "(dashboard handoff §4.5 -- agent.account, usage.window_remaining, "
                "weekly_remaining, resets_at are all unrecorded today)."
            ),
            hint="This is a recording gap to file, not something this tool can derive.",
            facts={"city_path": str(scope.city_root)},
            trace_id=scope.trace_id,
        )
    )

    slots: list[FleetSlot] = []
    seen_keys: set[str] = set()
    for agent in (status_payload or {}).get("agents") or []:
        if not isinstance(agent, dict):
            continue
        qualified_name = agent.get("qualified_name")
        if not isinstance(qualified_name, str):
            continue
        seen_keys.add(qualified_name)
        session = sessions_by_key.get(qualified_name)
        if session is None:
            slots.append(
                FleetSlot(
                    qualified_name=qualified_name,
                    template=None,
                    occupied=False,
                    state=None,
                    holds=None,
                    model=None,
                    account=None,
                    limit_state="unknown",
                    idle_for_seconds=None,
                    idle_reason="slot is empty",
                )
            )
            continue
        idle_for, idle_reason = _idle_for_seconds(session.get("last_active"))
        slots.append(
            FleetSlot(
                qualified_name=qualified_name,
                template=session.get("template") if isinstance(session.get("template"), str) else None,
                occupied=True,
                state=session.get("state") if isinstance(session.get("state"), str) else None,
                holds=session.get("id") if isinstance(session.get("id"), str) else None,
                model=session.get("provider") if isinstance(session.get("provider"), str) else None,
                account=None,
                limit_state="unknown",
                idle_for_seconds=idle_for,
                idle_reason=idle_reason,
            )
        )

    # A session that exists but matched no configured slot is not nothing --
    # it is a session `gc status` does not know about. Rendered rather than
    # dropped, so the roster never silently shrinks to fewer rows than exist.
    for key, session in sessions_by_key.items():
        if key in seen_keys:
            continue
        idle_for, idle_reason = _idle_for_seconds(session.get("last_active"))
        slots.append(
            FleetSlot(
                qualified_name=key,
                template=session.get("template") if isinstance(session.get("template"), str) else None,
                occupied=True,
                state=session.get("state") if isinstance(session.get("state"), str) else None,
                holds=session.get("id") if isinstance(session.get("id"), str) else None,
                model=session.get("provider") if isinstance(session.get("provider"), str) else None,
                account=None,
                limit_state="unknown",
                idle_for_seconds=idle_for,
                idle_reason=idle_reason,
            )
        )

    return FleetReport(slots=tuple(slots), diagnostics=tuple(diagnostics))
