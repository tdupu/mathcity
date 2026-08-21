"""Control-safety classification for an EffectPlan (D2 / #110).

Design by **stripes** (`<city-root>/docs/D2-blast-radius-proposal.md`); reviewer
sally. Implemented here in its amended TWO-FIELD form.

WHY TWO FIELDS AND NOT A FOUR-VALUE ENUM. The original proposal used
`low | medium | high | gated`. `gated` is not "more than high" -- it is a
*destination*: not here at all, go to the approval gate. One field carrying both
meanings has a concrete failure mode: any code treating the tier as ordered
(`tier >= HIGH`, a sort, a `max()` during escalation) reads `gated` as
merely-more-severe and does the wrong thing.

It also undermined the proposal's own constraint. stripes wrote that `gated` is
static-only, never escalated into or out of. **In one enum that is a rule people
must remember; in two fields it is true by construction**, because escalation
operates on `blast_radius` alone and cannot name `gate`.

FAIL CLOSED. An operation absent from the registry resolves to
`gate="unclassified"`, *not* `blast_radius="low"`. An operation nobody classified
must be the hardest thing to perform, not the easiest.
"""
from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Mapping

#: The confirmation axis. `gated` is deliberately NOT among these -- see module docstring.
TIERS: tuple[str, str, str] = ("low", "medium", "high")

#: Ordering used only for "escalation raises, never lowers". Safe because every
#: member is a real tier; this is exactly the comparison a `gated` member would
#: have corrupted.
_RANK = {tier: index for index, tier in enumerate(TIERS)}

#: Returned when an operation is not in the registry.
UNCLASSIFIED = "unclassified"

REGISTRY_PATH = Path(__file__).resolve().parents[2] / "mctl" / "blast_radius.toml"

#: Plan-content signals that RAISE the tier. One direction only, mirroring CT9.2
#: ("the reviewer may escalate the tier, never de-escalate it") rather than
#: inventing a second rule with the same shape.
#:
#: The motivating case: capacity.set_target(5) and capacity.set_target(0) are the
#: same operation with the same floor. One adds a slot; the other stops the rig.
#: Only plan contents tell them apart, so a static table alone would classify
#: them identically.
_ESCALATIONS: tuple[tuple[str, str, str], ...] = (
    ("deletes", "high", "the plan deletes"),
    ("overwrites", "high", "the plan overwrites an existing file"),
    ("stops_work", "high", "the change stops work (target=0, suspend, or disable)"),
    ("multi_rig", "high", "the plan touches more than one rig"),
    ("bulk_bead_updates", "high", "bulk bead updates"),
)


def load_registry(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Read the operation registry. Absent file is an empty registry, not a crash.

    An empty registry is SAFE, not permissive: every lookup then misses and
    resolves to `gate=UNCLASSIFIED`.
    """
    target = path or REGISTRY_PATH
    if not target.is_file():
        return {}
    with target.open("rb") as handle:
        return dict(tomllib.load(handle))


def _escalate(floor: str, plan_contents: Mapping[str, Any]) -> tuple[str, list[str]]:
    tier, causes = floor, []
    for key, raised_to, description in _ESCALATIONS:
        value = plan_contents.get(key)
        if key == "multi_rig":
            value = value or (int(plan_contents.get("rig_count") or 0) > 1)
        if not value:
            continue
        if _RANK[raised_to] > _RANK[tier]:
            tier = raised_to
        causes.append(description)
    return tier, causes


def classify(operation: str, *, plan_contents: Mapping[str, Any] | None = None,
             registry: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Classify one operation plus its plan contents.

    Returns the four fields that ride on the EffectPlan. `blast_radius_floor` is
    kept alongside the final tier so escalation is *visible* rather than silent
    -- the same pattern as `RedundantArtifact.state_reported_by_core`, which
    preserves the raw reading even when overridden.
    """
    contents = plan_contents or {}
    reg = registry if registry is not None else load_registry()
    entry = reg.get(operation)

    if entry is None:
        return {
            "blast_radius": "high",
            "blast_radius_floor": "high",
            "gate": UNCLASSIFIED,
            "blast_radius_reason": (
                f"operation {operation!r} is not in the blast-radius registry, so it is "
                f"refused rather than permitted; classify it in assets/mctl/blast_radius.toml"
            ),
        }

    gate = entry.get("gate")
    if gate:
        # A gated operation's tier is never consulted. The tier fields are still
        # populated so the payload shape is uniform for the renderer, but the
        # reason says plainly that the gate is what decides.
        return {
            "blast_radius": "high",
            "blast_radius_floor": "high",
            "gate": str(gate),
            "blast_radius_reason": (
                f"{entry.get('reason', '').strip()} — the {gate} gate owns this operation, "
                f"so the confirmation tier is not consulted"
            ),
        }

    floor = str(entry.get("floor") or "medium")
    tier, causes = _escalate(floor, contents)
    reason = entry.get("reason", "").strip()
    if causes:
        reason = f"floor {floor}; escalated to {tier} because " + ", ".join(causes) + f". {reason}"
    else:
        reason = f"floor {floor}. {reason}"
    return {
        "blast_radius": tier,
        "blast_radius_floor": floor,
        "gate": None,
        "blast_radius_reason": reason,
    }


def refuses(verdict: Mapping[str, Any]) -> bool:
    """Whether `apply` must refuse. True iff a gate owns the operation."""
    return verdict.get("gate") is not None
