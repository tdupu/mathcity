"""Structured diagnostics shared by mctl commands."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Mapping


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    FATAL = "FATAL"


# Plan §2 names these Diagnostic fields explicitly. They were being carried
# inside the untyped `facts` map, which forces every MCP and dashboard consumer
# to string-dig and breaks whenever a fact key is renamed. Deriving the typed
# fields from `facts` here restores the plan shape without changing any of the
# per-module _diagnostic() helpers, and keeps `facts` populated for existing
# consumers.
_FACT_TO_TYPED_FIELD = {
    "city_path": "city_path",
    "rig_name": "rig_name",
    "rig_path": "rig_path",
    "bead_id": "bead_id",
    "brief_id": "brief_slug",
    "data_location": "data_location",
    "policy_reference": "policy_ref",
    "implementation_provenance": "provenance_ref",
    "suggested_next_command": "suggested_next_command",
}

TYPED_FIELDS = tuple(sorted(set(_FACT_TO_TYPED_FIELD.values())))


@dataclass(frozen=True)
class Diagnostic:
    severity: Severity
    code: str
    message: str
    hint: str | None = None
    facts: Mapping[str, str] = field(default_factory=dict)
    trace_id: str | None = None
    city_path: str | None = None
    rig_name: str | None = None
    rig_path: str | None = None
    bead_id: str | None = None
    brief_slug: str | None = None
    data_location: str | None = None
    policy_ref: str | None = None
    provenance_ref: str | None = None
    suggested_next_command: str | None = None

    def __post_init__(self) -> None:
        for fact_key, field_name in _FACT_TO_TYPED_FIELD.items():
            if getattr(self, field_name) is None and fact_key in self.facts:
                object.__setattr__(self, field_name, self.facts[fact_key])

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": self.code,
            "facts": dict(sorted(self.facts.items())),
            "message": self.message,
            "severity": self.severity.value,
        }
        # Always emit every typed field, null when unset, so the schema is
        # stable for consumers rather than shape-shifting per diagnostic.
        for field_name in TYPED_FIELDS:
            payload[field_name] = getattr(self, field_name)
        if self.hint is not None:
            payload["hint"] = self.hint
        if self.trace_id is not None:
            payload["trace_id"] = self.trace_id
        return payload


def render_diagnostic(diagnostic: Diagnostic) -> str:
    """One diagnostic as operator-facing text.

    `suggested_next_command` is rendered beside `hint` rather than left to the
    facts block (#183). It reached the CLI two different ways and neither
    worked: set as a typed field it was dropped entirely, and passed through
    `facts` it surfaced only as a raw `suggested_next_command:` line sorted
    alphabetically among the machine facts -- present, but not where a reader
    looks for what to do next. A remedy matters most at the moment something
    refused, so it goes directly under the message.

    It is emitted ONCE. `__post_init__` promotes a `facts` entry onto the typed
    field, so a naive append would print the value twice for the call sites
    that pass it through facts.
    """
    lines = [f"[{diagnostic.severity.value}] {diagnostic.code}: {diagnostic.message}"]
    if diagnostic.hint:
        lines.append(f"hint: {diagnostic.hint}")
    if diagnostic.suggested_next_command:
        lines.append(f"next: {diagnostic.suggested_next_command}")
    for key, value in sorted(diagnostic.facts.items()):
        # Already rendered as `next:` above -- skip the duplicate rather than
        # dropping the key from `facts` itself, which is part of the payload
        # contract and read by JSON consumers.
        if key == "suggested_next_command":
            continue
        lines.append(f"{key}: {value}")
    if diagnostic.trace_id:
        lines.append(f"trace_id: {diagnostic.trace_id}")
    return "\n".join(lines)
