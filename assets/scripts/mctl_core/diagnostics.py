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


@dataclass(frozen=True)
class Diagnostic:
    severity: Severity
    code: str
    message: str
    hint: str | None = None
    facts: Mapping[str, str] = field(default_factory=dict)
    trace_id: str | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "code": self.code,
            "facts": dict(sorted(self.facts.items())),
            "message": self.message,
            "severity": self.severity.value,
        }
        if self.hint is not None:
            payload["hint"] = self.hint
        if self.trace_id is not None:
            payload["trace_id"] = self.trace_id
        return payload


def render_diagnostic(diagnostic: Diagnostic) -> str:
    lines = [f"[{diagnostic.severity.value}] {diagnostic.code}: {diagnostic.message}"]
    if diagnostic.hint:
        lines.append(f"hint: {diagnostic.hint}")
    for key, value in sorted(diagnostic.facts.items()):
        lines.append(f"{key}: {value}")
    if diagnostic.trace_id:
        lines.append(f"trace_id: {diagnostic.trace_id}")
    return "\n".join(lines)
