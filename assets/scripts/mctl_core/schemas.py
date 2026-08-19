"""Request and response schemas shared by mctl's CLI JSON and MCP responses.

Plan Slice 6 says to pick one modelling style and use it consistently. The
repository's stated tech stack is the Python standard library, and the core
already models every domain object as a frozen dataclass with a `to_dict`.
So the schemas here are *descriptions of those dicts* -- plain JSON Schema
documents plus a small validator -- rather than a second parallel object
model in Pydantic. That keeps one shape per concept: the dataclass is the
producer, the JSON Schema is the contract, and `schema_errors` is the gate.

Only the JSON Schema subset the tool surface actually uses is implemented:
`type`, `properties`, `required`, `additionalProperties`, `items`, `enum`,
and `const`. Unsupported keywords are ignored rather than silently treated
as satisfied-by-default, and `_UNSUPPORTED` fails loudly in the snapshot
tests if a schema starts using something the validator cannot check -- an
unenforced keyword in a contract is worse than no keyword.

Strictness policy, deliberately not uniform:

* Objects the MCP layer itself constructs (the response envelope, artifact
  trust, artifact entries) are closed -- `additionalProperties: false`. They
  are this slice's contract, so an unexpected key is a bug here.
* Objects produced by other slices' dataclasses (brief records, work items,
  effect plans, traces) declare and type their key fields but stay open. A
  later slice adding a field to `BriefRecord` is a compatible change, and
  making it fail here would couple every slice to this file.
"""
from __future__ import annotations

from typing import Any, Mapping, Sequence


Schema = dict[str, Any]

_SUPPORTED = frozenset(
    {
        "additionalProperties",
        "const",
        "default",
        "description",
        "enum",
        "items",
        "properties",
        "required",
        "title",
        "type",
    }
)


# --- validation -------------------------------------------------------------


def _json_type(value: object) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, tuple)):
        return "array"
    if isinstance(value, Mapping):
        return "object"
    return type(value).__name__


def _type_matches(value: object, expected: str) -> bool:
    if expected == "number":
        return _json_type(value) in {"integer", "number"}
    return _json_type(value) == expected


def _failure(path: str, keyword: str, expected: object, actual: object, message: str) -> dict:
    return {
        "path": path,
        "keyword": keyword,
        "expected": expected,
        "actual": actual,
        "message": message,
    }


def _join(path: str, key: str) -> str:
    return f"{path}.{key}" if path else key


def schema_errors(instance: object, schema: Schema, path: str = "") -> list[dict]:
    """Return every way `instance` violates `schema`, as typed failures.

    Returns a list rather than raising: a caller reporting "your arguments
    were wrong" is far more useful naming all three wrong fields than the
    first one.
    """
    failures: list[dict] = []
    declared_type = schema.get("type")
    if declared_type is not None:
        allowed = [declared_type] if isinstance(declared_type, str) else list(declared_type)
        if not any(_type_matches(instance, candidate) for candidate in allowed):
            expected = allowed[0] if len(allowed) == 1 else allowed
            return [
                _failure(
                    path or "(root)",
                    "type",
                    expected,
                    _json_type(instance),
                    f"expected {expected}, got {_json_type(instance)}",
                )
            ]

    if "const" in schema and instance != schema["const"]:
        failures.append(
            _failure(path or "(root)", "const", schema["const"], instance, "value is not the constant")
        )
    if "enum" in schema and instance not in schema["enum"]:
        failures.append(
            _failure(
                path or "(root)",
                "enum",
                list(schema["enum"]),
                instance,
                f"{instance!r} is not one of {list(schema['enum'])}",
            )
        )

    if isinstance(instance, Mapping):
        failures.extend(_object_errors(instance, schema, path))
    elif isinstance(instance, (list, tuple)) and "items" in schema:
        for index, item in enumerate(instance):
            failures.extend(schema_errors(item, schema["items"], f"{path}[{index}]"))
    return failures


def _object_errors(instance: Mapping[str, object], schema: Schema, path: str) -> list[dict]:
    failures: list[dict] = []
    properties: Mapping[str, Schema] = schema.get("properties", {})
    for key in schema.get("required", []):
        if key not in instance:
            failures.append(
                _failure(_join(path, key), "required", key, "absent", f"required property {key!r} is missing")
            )
    if schema.get("additionalProperties") is False:
        for key in sorted(set(instance) - set(properties)):
            failures.append(
                _failure(
                    _join(path, key),
                    "additionalProperties",
                    sorted(properties),
                    key,
                    f"property {key!r} is not declared by this schema",
                )
            )
    for key in sorted(set(instance) & set(properties)):
        failures.extend(schema_errors(instance[key], properties[key], _join(path, key)))
    return failures


def unsupported_keywords(schema: Schema) -> set[str]:
    """Keywords present in a schema that `schema_errors` does not enforce."""
    found: set[str] = set(schema) - _SUPPORTED
    for child in schema.get("properties", {}).values():
        found |= unsupported_keywords(child)
    if isinstance(schema.get("items"), dict):
        found |= unsupported_keywords(schema["items"])
    return found


# --- shared building blocks -------------------------------------------------


def nullable_string(description: str) -> Schema:
    return {"type": ["string", "null"], "description": description}


STRING_ARRAY: Schema = {"type": "array", "items": {"type": "string"}}

#: Mirrors `mctl_core.diagnostics.Diagnostic.to_dict`. The typed fields are
#: always emitted (null when unset) precisely so this schema can require them.
DIAGNOSTIC_SCHEMA: Schema = {
    "type": "object",
    "title": "Diagnostic",
    "description": "A structured mctl diagnostic: severity, stable code, and provenance.",
    "required": [
        "bead_id",
        "brief_slug",
        "city_path",
        "code",
        "data_location",
        "facts",
        "message",
        "policy_ref",
        "provenance_ref",
        "rig_name",
        "rig_path",
        "severity",
        "suggested_next_command",
    ],
    "properties": {
        "bead_id": nullable_string("Canonical bead this diagnostic is about."),
        "brief_slug": nullable_string("Brief slug this diagnostic is about."),
        "city_path": nullable_string("Resolved Gas City root."),
        "code": {"type": "string", "description": "Stable code from assets/mctl/diagnostics.toml."},
        "data_location": nullable_string("File or store the finding was read from."),
        "facts": {"type": "object", "description": "Untyped supporting facts."},
        "hint": nullable_string("Suggested operator action."),
        "message": {"type": "string", "description": "Human-readable finding."},
        "policy_ref": nullable_string("Policy clause the finding is grounded in."),
        "provenance_ref": nullable_string("Implementation surface that raised it."),
        "rig_name": nullable_string("Resolved rig identifier."),
        "rig_path": nullable_string("Resolved rig root."),
        "severity": {"type": "string", "enum": ["INFO", "WARN", "ERROR", "FATAL"]},
        "suggested_next_command": nullable_string("Command that would advance the situation."),
        "trace_id": nullable_string("Trace this diagnostic belongs to."),
    },
    "additionalProperties": False,
}

DIAGNOSTIC_ARRAY: Schema = {
    "type": "array",
    "description": "Structured diagnostics for this call.",
    "items": DIAGNOSTIC_SCHEMA,
}

#: Q5 (subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md) is unresolved: mctl's
#: redundant-artifact model resolves rig-root-relative while the live stack is
#: city-root-level, and looks up `<root>/.pile/<bead_id>.md` while real pile
#: files carry the bead id in an `artifact:` frontmatter key. Every response
#: that reports artifact state carries this verdict so no client can mistake
#: an unverifiable "missing" for an established one.
ARTIFACT_TRUST_SCHEMA: Schema = {
    "type": "object",
    "title": "ArtifactTrust",
    "description": "Whether redundant-artifact state in this response can be acted on.",
    "required": [
        "open_question",
        "reason",
        "reference",
        "resolved_brief_root",
        "resolved_pile",
        "trusted",
        "withheld_codes",
    ],
    "properties": {
        "open_question": nullable_string("Open design question that makes the state untrustworthy."),
        "reason": {"type": "string", "description": "Why artifact state is or is not trustworthy."},
        "reference": nullable_string("Document recording the open question."),
        "resolved_brief_root": {"type": "string", "description": "Brief root artifact_layout() resolved."},
        "resolved_pile": {"type": "string", "description": "Pile directory artifact_layout() resolved."},
        "trusted": {"type": "boolean", "description": "False when artifact state must not be acted on."},
        "withheld_codes": dict(
            STRING_ARRAY,
            description="Diagnostic codes moved to untrusted_diagnostics.",
        ),
    },
    "additionalProperties": False,
}

REDUNDANT_ARTIFACT_SCHEMA: Schema = {
    "type": "object",
    "title": "RedundantArtifact",
    "description": "One non-canonical cache artifact cross-checked against the bead store.",
    "required": ["detail", "kind", "path", "state", "state_reported_by_core"],
    "properties": {
        "detail": {"type": "string"},
        "kind": {"type": "string"},
        "path": {"type": "string"},
        "state": {
            "type": "string",
            "enum": ["present", "missing", "stale", "inconsistent", "unverified"],
            "description": "`unverified` when Q5 makes the core's reading unusable.",
        },
        "state_reported_by_core": {
            "type": "string",
            "enum": ["present", "missing", "stale", "inconsistent"],
            "description": "Raw state from mctl_core, preserved even when overridden.",
        },
    },
    "additionalProperties": False,
}

BRIEF_RECORD_SCHEMA: Schema = {
    "type": "object",
    "title": "BriefRecord",
    "description": "A canonical decision brief bead plus its redundant cache artifacts.",
    "required": [
        "bead_id",
        "brief_id",
        "canonical_source",
        "decision_state",
        "labels",
        "policy_references",
        "redundant_artifacts",
        "status",
        "title",
    ],
    "properties": {
        "bead_id": {"type": "string"},
        "brief_id": {"type": "string"},
        "canonical_source": {"type": "string", "const": "bead_store"},
        "created_at": nullable_string("Bead creation timestamp."),
        "decision_state": {"type": "string"},
        "labels": STRING_ARRAY,
        "policy_references": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["description", "reference"],
                "properties": {"description": {"type": "string"}, "reference": {"type": "string"}},
                "additionalProperties": False,
            },
        },
        "redundant_artifacts": {"type": "array", "items": REDUNDANT_ARTIFACT_SCHEMA},
        "status": {"type": "string"},
        "title": {"type": "string"},
        "updated_at": nullable_string("Bead update timestamp."),
    },
}

BRIEF_OPTION_SCHEMA: Schema = {
    "type": "object",
    "title": "BriefOption",
    "description": "An action this brief's current bead state does or does not permit.",
    "required": ["description", "enabled", "id", "label"],
    "properties": {
        "description": {"type": "string"},
        "disabled_reason": {"type": ["object", "null"]},
        "enabled": {"type": "boolean"},
        "id": {"type": "string"},
        "label": {"type": "string"},
    },
}

BRIEF_DIAGNOSTICS_SCHEMA: Schema = {
    "type": "array",
    "description": "Diagnostics grouped by the brief they were raised against.",
    "items": {
        "type": "object",
        "required": ["brief_id", "diagnostics"],
        "properties": {"brief_id": {"type": "string"}, "diagnostics": DIAGNOSTIC_ARRAY},
    },
}

SEVERITY_COUNTS_SCHEMA: Schema = {
    "type": "object",
    "description": "Diagnostic counts by severity.",
    "required": ["INFO", "WARN", "ERROR", "FATAL"],
    "properties": {
        "INFO": {"type": "integer"},
        "WARN": {"type": "integer"},
        "ERROR": {"type": "integer"},
        "FATAL": {"type": "integer"},
    },
    "additionalProperties": False,
}

WORK_ITEM_SCHEMA: Schema = {
    "type": "object",
    "title": "WorkItem",
    "description": "Brief-backed work with its readiness and blockers.",
    "required": ["bead_id", "blockers", "brief_id", "readiness", "title"],
    "properties": {
        "bead_id": {"type": "string"},
        "blockers": DIAGNOSTIC_ARRAY,
        "brief_id": {"type": "string"},
        "provenance": {"type": ["object", "null"]},
        "readiness": {"type": "string"},
        "title": {"type": "string"},
    },
}

EFFECT_PLAN_SCHEMA: Schema = {
    "type": "object",
    "title": "EffectPlan",
    "description": "Everything a mutation intends to do, before it does any of it.",
    "required": ["operation", "trace_id"],
    "properties": {
        "advisories": DIAGNOSTIC_ARRAY,
        "bead_creates": {"type": "array"},
        "bead_updates": {"type": "array"},
        "cache_updates": {"type": "array"},
        "event_writes": {"type": "array"},
        "file_creates": {"type": "array"},
        "formula_invocation": {"type": "object"},
        "operation": {"type": "string"},
        "preconditions": DIAGNOSTIC_ARRAY,
        "provenance": {"type": "object"},
        "target_brief_id": {"type": "string"},
        "trace_id": {"type": "string"},
        "trace_writes": {"type": "array"},
        "bead_id": {"type": "string"},
    },
}

TRACE_RECORD_SCHEMA: Schema = {
    "type": "object",
    "title": "TraceRecord",
    "description": "Every recorded phase row for one trace id, folded together.",
    "required": ["actual_effects", "blocking_diagnostics", "outcome", "phases", "trace_id"],
    "properties": {
        "actual_effects": {"type": "array"},
        "blocking_diagnostics": {"type": "array"},
        "outcome": {"type": "string", "enum": ["planned", "applied", "aborted"]},
        "phases": STRING_ARRAY,
        "trace_id": {"type": "string"},
    },
}


# --- envelope ---------------------------------------------------------------

#: Runtime-context selectors every tool accepts. A tool that could not name a
#: city and rig would have to infer one, which is the failure mode
#: `MCTL_CONTEXT_SOURCE_CHECKOUT` exists to prevent.
RUNTIME_PROPERTIES: dict[str, Schema] = {
    "city": nullable_string("Registered Gas City root; defaults to the server's --city."),
    "rig": nullable_string("Registered rig identifier; defaults to the server's --rig."),
}

DRY_RUN_PROPERTY: Schema = {
    "type": "boolean",
    "default": True,
    "description": "Preview the effect plan without applying it. Defaults to true.",
}


def request_schema(
    properties: Mapping[str, Schema] | None = None, required: Sequence[str] = ()
) -> Schema:
    """A closed request object with the runtime selectors already attached."""
    return {
        "type": "object",
        "properties": {**RUNTIME_PROPERTIES, **dict(properties or {})},
        "required": list(required),
        "additionalProperties": False,
    }


def response_schema(
    properties: Mapping[str, Schema],
    required: Sequence[str],
    *,
    artifact_state: bool = False,
) -> Schema:
    """A response object carrying the mandatory diagnostics/trace envelope.

    `artifact_state=True` additionally makes the Q5 trust verdict and the
    withheld-diagnostic array part of the *required* contract, so a client
    cannot read artifact state without also receiving the reason it may not
    be trustworthy.
    """
    declared: dict[str, Schema] = {
        "diagnostics": DIAGNOSTIC_ARRAY,
        "trace_id": {"type": "string", "description": "Trace id for this tool call."},
        **dict(properties),
    }
    mandatory = ["diagnostics", "trace_id", *required]
    if artifact_state:
        declared["artifact_trust"] = ARTIFACT_TRUST_SCHEMA
        declared["untrusted_diagnostics"] = dict(
            DIAGNOSTIC_ARRAY,
            description="Diagnostics withheld because Q5 makes them unactionable.",
        )
        mandatory = [*mandatory, "artifact_trust", "untrusted_diagnostics"]
    return {
        "type": "object",
        "properties": declared,
        "required": sorted(set(mandatory)),
        "additionalProperties": True,
    }
