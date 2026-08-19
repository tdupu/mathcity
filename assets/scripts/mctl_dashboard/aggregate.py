"""Reading a city-wide payload. No aggregation happens here.

The cross-rig read lives in `mctl_core/city.py` behind the plan's declared
`all_rigs` option, and the CLI and the MCP surface are both adapters over it.
This module is the dashboard's third adapter and nothing more: it takes the
payload one `briefs_list(all_rigs=true)` call returns and gives the renderer
names for the parts.

That split is deliberate. Cross-rig assembly written here would be a second
implementation of the semantics, drifting from the CLI's -- and there is
already a third in the wild (the `check-briefs` skill loops `mctl briefs list
--rig X` in shell). One read path, three consumers, is the same argument Q2
settled for the stack index.

What this module does hold is the presentation invariant: a brief row is only
ever addressed through the rig it came from. `CityView.briefs` are the rows the
core already tagged with `rig_id`; nothing here invents a rig for a row that
lacks one, and nothing sums a per-rig fact into a city-wide claim.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class RigView:
    """One entry of the payload's per-rig breakdown."""

    rig_id: str
    rig_root: str = ""
    rig_db: str = ""
    ok: bool = True
    reason: str = ""
    counts: Mapping[str, int] = field(default_factory=dict)
    elapsed_ms: int = 0
    diagnostics: tuple[Mapping[str, Any], ...] = ()
    artifact_trust: Mapping[str, Any] | None = None

    @classmethod
    def from_payload(cls, entry: Mapping[str, Any]) -> "RigView":
        trust = entry.get("artifact_trust")
        return cls(
            rig_id=str(entry.get("rig_id") or ""),
            rig_root=str(entry.get("rig_root") or ""),
            rig_db=str(entry.get("rig_db") or ""),
            ok=bool(entry.get("ok")),
            reason=str(entry.get("reason") or ""),
            counts={str(k): int(v) for k, v in (entry.get("counts") or {}).items()},
            elapsed_ms=int(entry.get("elapsed_ms") or 0),
            diagnostics=tuple(entry.get("diagnostics") or ()),
            artifact_trust=dict(trust) if isinstance(trust, Mapping) else None,
        )

    def count(self, name: str) -> int:
        return int(self.counts.get(name, 0))


@dataclass(frozen=True)
class CityView:
    """A city-wide payload, named."""

    city_root: str
    rigs: tuple[RigView, ...] = ()
    rows: tuple[Mapping[str, Any], ...] = ()
    diagnostics: tuple[Mapping[str, Any], ...] = ()
    untrusted_diagnostics: tuple[Mapping[str, Any], ...] = ()
    artifact_trust: Mapping[str, Any] | None = None
    severity_counts: Mapping[str, int] = field(default_factory=dict)
    valid: bool | None = None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any], *, rows: str = "briefs") -> "CityView":
        trust = payload.get("artifact_trust")
        return cls(
            city_root=str(payload.get("city_root") or ""),
            rigs=tuple(RigView.from_payload(entry) for entry in payload.get("rigs") or ()),
            rows=tuple(payload.get(rows) or ()),
            diagnostics=tuple(payload.get("diagnostics") or ()),
            untrusted_diagnostics=tuple(payload.get("untrusted_diagnostics") or ()),
            artifact_trust=dict(trust) if isinstance(trust, Mapping) else None,
            severity_counts={
                str(k): int(v) for k, v in (payload.get("severity_counts") or {}).items()
            },
            valid=payload.get("valid") if isinstance(payload.get("valid"), bool) else None,
        )

    @property
    def healthy(self) -> tuple[RigView, ...]:
        return tuple(rig for rig in self.rigs if rig.ok)

    @property
    def degraded(self) -> tuple[RigView, ...]:
        return tuple(rig for rig in self.rigs if not rig.ok)

    @property
    def complete(self) -> bool:
        """Whether every registered rig answered.

        Exposed rather than inferred at each call site: "is this total the
        whole city" is the question a reader most needs answered and least
        likely to think to ask.
        """
        return not self.degraded

    def rows_for(self, rig_id: str | None) -> tuple[Mapping[str, Any], ...]:
        if not rig_id:
            return self.rows
        return tuple(row for row in self.rows if str(row.get("rig_id") or "") == rig_id)

    def state_counts(self, rig_id: str | None = None) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in self.rows_for(rig_id):
            state = str(row.get("decision_state"))
            counts[state] = counts.get(state, 0) + 1
        return counts

    def rig_ids(self) -> tuple[str, ...]:
        return tuple(rig.rig_id for rig in self.rigs)


def state_columns(view: CityView) -> tuple[str, ...]:
    """Every decision state present anywhere in the city, in a stable order."""
    return tuple(sorted(view.state_counts()))


def rig_of(rows: Sequence[Mapping[str, Any]], brief_id: str) -> str | None:
    """Which rig a listed brief came from, or None if the list does not say."""
    for row in rows:
        if str(row.get("brief_id")) == brief_id:
            return str(row.get("rig_id") or "") or None
    return None
