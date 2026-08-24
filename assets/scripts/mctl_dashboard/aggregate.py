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

from .reading import attr


def is_deferred(row: Mapping[str, Any]) -> bool:
    """Whether a brief has been held out of the pending queue.

    THE canonical rule, single-sourced here so the overview census
    (`CityView.state_counts`) and the queue's lane filter (`app.is_deferred`,
    which re-exports this) cannot drift and disagree on one brief -- the `#198`
    off-by-one. Deferral is written to the bead's `status`
    (`effects.py::plan_deferral` sets `status="deferred"`) while `decision_state`
    is computed separately and never takes that value; both are consulted until
    the core reconciles them.
    """
    return (
        str(attr(row, "decision_state") or "") == "deferred"
        or str(attr(row, "status") or "") == "deferred"
    )


@dataclass(frozen=True)
class RigView:
    """One entry of the payload's per-rig breakdown."""

    rig_id: str
    rig_root: str = ""
    rig_db: str = ""
    ok: bool = True
    #: The rig answered from some of its stores and not others. Its rows ARE
    #: in `CityView.rows`; the ones its unread stores hold are not. Carried
    #: separately from `ok` because the page has to say two different things:
    #: "this rig contributed nothing" and "this rig contributed part of what
    #: it has" are different instructions to whoever is reading a total.
    partial: bool = False
    reason: str = ""
    counts: Mapping[str, int] = field(default_factory=dict)
    elapsed_ms: int = 0
    diagnostics: tuple[Mapping[str, Any], ...] = ()
    degraded_sources: tuple[Mapping[str, Any], ...] = ()
    artifact_trust: Mapping[str, Any] | None = None

    @classmethod
    def from_payload(cls, entry: Mapping[str, Any]) -> "RigView":
        trust = entry.get("artifact_trust")
        return cls(
            rig_id=str(entry.get("rig_id") or ""),
            rig_root=str(entry.get("rig_root") or ""),
            rig_db=str(entry.get("rig_db") or ""),
            ok=bool(entry.get("ok")),
            partial=bool(entry.get("partial")),
            reason=str(entry.get("reason") or ""),
            counts={str(k): int(v) for k, v in (entry.get("counts") or {}).items()},
            elapsed_ms=int(entry.get("elapsed_ms") or 0),
            diagnostics=tuple(entry.get("diagnostics") or ()),
            degraded_sources=tuple(entry.get("degraded_sources") or ()),
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
        """Every rig that is not a clean read -- partial ones included.

        Deliberately not narrowed to "contributed nothing". This is what the
        rig-health panel is built from, and a rig whose bead store went quiet
        while its documents were read belongs on that panel: its rows are on
        the page and the rows behind the unread store are not. `RigView.partial`
        is how the panel tells the two cases apart in its wording.
        """
        return tuple(rig for rig in self.rigs if not rig.ok)

    @property
    def unreadable(self) -> tuple[RigView, ...]:
        """Rigs that contributed no rows at all."""
        return tuple(rig for rig in self.rigs if not rig.ok and not rig.partial)

    @property
    def partial(self) -> tuple[RigView, ...]:
        """Rigs that contributed the rows their readable stores hold."""
        return tuple(rig for rig in self.rigs if rig.partial)

    @property
    def complete(self) -> bool:
        """Whether every registered rig answered from every one of its stores.

        Exposed rather than inferred at each call site: "is this total the
        whole city" is the question a reader most needs answered and least
        likely to think to ask. A partial rig makes it False -- the total is
        short by whatever its unread store holds, even though the rig is on
        the page with a count beside it.
        """
        return not self.degraded

    def rows_for(self, rig_id: str | None) -> tuple[Mapping[str, Any], ...]:
        if not rig_id:
            return self.rows
        return tuple(row for row in self.rows if str(row.get("rig_id") or "") == rig_id)

    def state_counts(self, rig_id: str | None = None) -> dict[str, int]:
        counts: dict[str, int] = {}
        for row in self.rows_for(rig_id):
            # `#198`: a deferred brief's `decision_state` is still `"pending"`
            # (deferral is written to `status`, never to `decision_state`), so
            # counting the raw field put it under `pending` -- and the overview
            # then reported one more "pending, needs a human" than `/queue`,
            # which drops deferred briefs from its in-scope count. A deferred
            # brief has been excused from the queue; it belongs under `deferred`.
            # Reclassifying here (not dropping) keeps the census total equal to
            # the number of briefs, and makes the two paths agree.
            state = "deferred" if is_deferred(row) else str(row.get("decision_state"))
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
