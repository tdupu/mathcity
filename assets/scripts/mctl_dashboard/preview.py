"""Dry-run previews and the rule that a stale one cannot be applied.

The plan's rollout controls say to keep apply disabled "until the dashboard can
fetch and display a **fresh** dry-run preview". Freshness, not existence, is
the safety property: an operator who previews an approval, gets interrupted,
and confirms ten minutes later must not apply a verdict against a brief that
moved in between.

So a preview records three fingerprints of the world it was computed against,
and the confirm path recomputes all three:

`rig`      which rig's bead store the mutation targets. On a city-wide
           dashboard this is a real axis: the same page can address sixteen
           stores, and a confirm that arrives naming a different rig than the
           preview was taken against must not be applied to either.
`context`  the resolved city/rig/db. Catches the registry being re-pointed
           underneath a running dashboard, and -- because `rig_id`, `rig_db`
           and `rig_root` are all fingerprinted -- catches the rig changing
           even when the form still claims the old one.
`target`   the canonical bead record from `briefs_show`. Catches the brief
           itself changing -- status, title, labels, timestamps.
`plan`     the effect plan itself, re-planned at confirm time. Catches
           everything the other two cannot see: a redundant cache file
           appearing or vanishing changes the planned effects while every bead
           field stays identical.

The plan digest has to ignore what varies between two identical calls -- the
trace id is fresh per call and `adjudicated_at` is a timestamp -- or every
preview would be stale the instant it was made, and the guard would be noise
an operator learns to click through. `VOLATILE_KEYS` is that redaction, by key
name so it is reviewable. `BeadUpdate.if_status` is deliberately *not*
volatile: it is the observed status the plan was built against, so it is
exactly the field that must invalidate a preview.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
import time
from typing import Any, Mapping
import uuid


#: Keys whose values differ between two identical dry runs. Redacted from the
#: plan digest so freshness means "the same effects", not "the same second".
VOLATILE_KEYS = frozenset(
    {
        "trace_id",
        "mctl_trace_id",
        "adjudicated_at",
        "deferred_at",
    }
)

#: Context fields whose change makes a preview meaningless. Deliberately not
#: the whole context payload: `trace_id` is per call and `invocation_cwd` says
#: nothing about which store the mutation lands in.
CONTEXT_KEYS = (
    "city_active",
    "city_root",
    "rig_db",
    "rig_id",
    "rig_root",
    "source_checkout",
)


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            key: ("<volatile>" if key in VOLATILE_KEYS else _redact(item))
            for key, item in sorted(value.items())
        }
    if isinstance(value, (list, tuple)):
        return [_redact(item) for item in value]
    return value


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()


def stable_digest(value: Any) -> str:
    """Digest of `value` with per-call volatile fields redacted."""
    return _digest(_redact(value))


def context_fingerprint(context: Mapping[str, Any]) -> str:
    return _digest({key: context.get(key) for key in CONTEXT_KEYS})


def target_fingerprint(brief: Mapping[str, Any] | None) -> str:
    """Fingerprint the canonical bead record, not the artifact readings.

    `redundant_artifacts` is excluded on purpose: while Q5 is open those
    readings are unverifiable, and letting an unverifiable field invalidate
    previews would make the guard fire on noise. Real artifact changes still
    land in the plan digest, which is the axis that can see them honestly.
    """
    if brief is None:
        return _digest(None)
    return _digest({key: value for key, value in brief.items() if key != "redundant_artifacts"})


@dataclass(frozen=True)
class Preview:
    token: str
    operation: str
    tool: str
    arguments: dict[str, Any]
    brief_id: str | None
    rig: str | None
    context_fingerprint: str
    target_fingerprint: str
    plan_digest: str
    payload: dict[str, Any]
    created_at: float = field(default_factory=time.time)

    @property
    def effect_plan(self) -> dict[str, Any]:
        plan = self.payload.get("effect_plan")
        return dict(plan) if isinstance(plan, Mapping) else {}

    def matches(
        self, *, context: str, target: str, plan: str, rig: str | None = None
    ) -> tuple[str, ...]:
        """Return the names of the components that have changed since preview."""
        changed = []
        if rig != self.rig:
            # Named separately from `context` even though the context
            # fingerprint would also move: "the rig changed" is the sentence
            # an operator needs, and "the context changed" is not it.
            changed.append("rig")
        if context != self.context_fingerprint:
            changed.append("context")
        if target != self.target_fingerprint:
            changed.append("target")
        if plan != self.plan_digest:
            changed.append("plan")
        return tuple(changed)


class PreviewStore:
    """In-memory previews, keyed by single-use token.

    In-memory on purpose. A preview is a claim about state observed seconds
    ago; persisting one across restarts would preserve a claim whose whole
    value is that it is current.
    """

    def __init__(self) -> None:
        self._previews: dict[str, Preview] = {}

    def create(
        self,
        *,
        operation: str,
        tool: str,
        arguments: Mapping[str, Any],
        brief_id: str | None,
        rig: str | None,
        context: Mapping[str, Any],
        target: Mapping[str, Any] | None,
        payload: Mapping[str, Any],
    ) -> Preview:
        preview = Preview(
            token=uuid.uuid4().hex,
            operation=operation,
            tool=tool,
            arguments=dict(arguments),
            brief_id=brief_id,
            rig=rig,
            context_fingerprint=context_fingerprint(context),
            target_fingerprint=target_fingerprint(target),
            plan_digest=stable_digest(dict(payload).get("effect_plan")),
            payload=dict(payload),
        )
        self._previews[preview.token] = preview
        return preview

    def get(self, token: str | None) -> Preview | None:
        return self._previews.get(str(token or ""))

    def pop(self, token: str | None) -> Preview | None:
        """Take a preview out of the store. Tokens are single use.

        Popped on *every* confirm attempt, including a refused one, so a
        resubmitted form can never reach a second apply and a stale token
        cannot be retried after its replacement has been offered.
        """
        return self._previews.pop(str(token or ""), None)
