"""Command-line rendering for mctl Slice 1."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

from .briefs import (
    BriefError,
    BriefFilters,
    brief_command_diagnostics,
    brief_options_report,
    doctor_briefs,
    list_briefs,
    show_brief,
    validate_brief,
)
from .context import ContextError, MctlContext, resolve_context
from .diagnostics import Diagnostic, Severity, render_diagnostic
from .trace import fold, read_rows
from .effects import (
    BriefCreateInput,
    MutationError,
    apply_effect_plan,
    dry_run_payload,
    plan_adjudication,
    plan_create_brief,
    plan_deferral,
)
from .work import (
    WorkError,
    apply_dispatch_plan,
    dispatch_dry_run_payload,
    plan_dispatch,
    ready_work,
    work_provenance,
    work_status,
)


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        context = resolve_context(
            Path.cwd(),
            city=Path(args.city) if args.city else None,
            rig=args.rig,
            require_runtime_city=True,
            require_explicit_runtime=args.command in {"briefs", "work"},
            env=os.environ,
        )
    except ContextError as error:
        print(render_diagnostic(error.diagnostic), file=sys.stderr)
        return 1

    if args.command == "context":
        if args.json:
            print(json.dumps(context.to_dict(), indent=2, sort_keys=True))
        else:
            print(_render_explain(context))
        return 0
    if context.city_active is False and args.command != "trace":
        print(render_diagnostic(_city_not_active_diagnostic(context)), file=sys.stderr)
        return 1
    if args.command == "briefs":
        return _briefs_command(args, context)
    if args.command == "trace":
        return _trace_command(args, context)
    return _work_command(args, context)


def _trace_command(args: argparse.Namespace, context: MctlContext) -> int:
    record = fold(read_rows(context.rig_root), args.trace_id)
    if record is None:
        print(
            render_diagnostic(
                Diagnostic(
                    severity=Severity.FATAL,
                    code="MCTL_TRACE_NOT_FOUND",
                    message=f"No trace rows recorded for {args.trace_id!r}.",
                    hint="List recent traces under .beads/mctl/traces/.",
                    facts={
                        "city_path": str(context.city_root),
                        "rig_name": context.rig_id,
                        "rig_path": str(context.rig_root),
                        "implementation_provenance": "mctl trace show",
                    },
                    trace_id=context.trace_id,
                )
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps({"trace": record, "trace_id": context.trace_id}, indent=2, sort_keys=True))
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mctl")
    commands = parser.add_subparsers(dest="command", required=True)
    context = commands.add_parser("context", help="resolve a MathCity city and rig context")
    context.add_argument("--city", help="registered Gas City root")
    context.add_argument("--rig", help="registered rig identifier")
    output = context.add_mutually_exclusive_group()
    output.add_argument("--json", action="store_true", help="render deterministic JSON")
    output.add_argument("--explain", action="store_true", help="render context discovery details")
    briefs = commands.add_parser("briefs", help="inspect canonical brief state without repairs")
    brief_commands = briefs.add_subparsers(dest="brief_command", required=True)
    _add_brief_list_parser(brief_commands)
    _add_brief_show_parser(brief_commands)
    _add_brief_options_parser(brief_commands)
    _add_brief_doctor_parser(brief_commands)
    _add_brief_adjudicate_parser(brief_commands)
    _add_brief_defer_parser(brief_commands)
    _add_brief_create_parser(brief_commands)
    _add_brief_validate_parser(brief_commands)
    trace = commands.add_parser("trace", help="inspect mctl operation traces")
    trace_commands = trace.add_subparsers(dest="trace_command", required=True)
    trace_show = trace_commands.add_parser("show", help="fold every phase row for one trace id")
    trace_show.add_argument("trace_id")
    _add_runtime_arguments(trace_show)
    work = commands.add_parser("work", help="inspect and dispatch brief-backed work")
    work_commands = work.add_subparsers(dest="work_command", required=True)
    _add_work_ready_parser(work_commands)
    _add_work_status_parser(work_commands)
    _add_work_provenance_parser(work_commands)
    _add_work_dispatch_parser(work_commands)
    return parser


def _add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--city", help="registered Gas City root")
    parser.add_argument("--rig", help="registered rig identifier")
    parser.add_argument("--json", action="store_true", help="render deterministic JSON")


def _add_brief_list_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("list", help="list canonical decision brief beads")
    parser.add_argument("--status", help="filter by raw bead or decision status")
    parser.add_argument("--label", help="filter by brief label")
    _add_runtime_arguments(parser)


def _add_brief_show_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("show", help="show canonical and redundant brief state")
    parser.add_argument("brief_id")
    _add_runtime_arguments(parser)


def _add_brief_options_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("options", help="show available actions without applying them")
    parser.add_argument("brief_id")
    _add_runtime_arguments(parser)


def _add_brief_doctor_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("doctor", help="report canonical/cache invariant violations")
    parser.add_argument("--brief", dest="brief_id", help="inspect one canonical brief")
    _add_runtime_arguments(parser)


def _add_brief_adjudicate_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("adjudicate", help="record a brief verdict through an effect plan")
    parser.add_argument("brief_id")
    parser.add_argument("--verdict", "--decision", dest="verdict")
    parser.add_argument("--reason")
    parser.add_argument("--option")
    parser.add_argument("--dry-run", action="store_true")
    _add_runtime_arguments(parser)


def _add_brief_defer_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("defer", help="defer a brief through an effect plan")
    parser.add_argument("brief_id")
    parser.add_argument("--reason")
    parser.add_argument("--until")
    parser.add_argument("--days", type=int)
    parser.add_argument("--dry-run", action="store_true")
    _add_runtime_arguments(parser)


def _add_brief_create_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("create", help="create a canonical decision brief bead")
    parser.add_argument("--title", help="what is being decided")
    body = parser.add_mutually_exclusive_group()
    body.add_argument("--body-file", dest="body_file", help="read the brief body from a file")
    body.add_argument("--body", help="brief body text")
    parser.add_argument("--label", action="append", default=[], help="brief label (repeatable)")
    parser.add_argument(
        "--source", action="append", default=[], help="source bead id (repeatable)"
    )
    parser.add_argument("--requested-by", dest="requested_by")
    parser.add_argument("--dry-run", action="store_true")
    _add_runtime_arguments(parser)


def _add_brief_validate_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("validate", help="prove canonical and redundant state agree")
    parser.add_argument("brief_id", nargs="?")
    parser.add_argument("--all", action="store_true", help="validate every canonical brief")
    _add_runtime_arguments(parser)


def _add_work_ready_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("ready", help="list ready brief-backed work")
    _add_runtime_arguments(parser)


def _add_work_status_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("status", help="show work readiness and blockers")
    parser.add_argument("brief_id")
    _add_runtime_arguments(parser)


def _add_work_provenance_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("provenance", help="show validated dispatch provenance")
    parser.add_argument("brief_id")
    _add_runtime_arguments(parser)


def _add_work_dispatch_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("dispatch", help="dispatch brief-backed work through an effect plan")
    parser.add_argument("brief_id")
    parser.add_argument("--dry-run", action="store_true")
    _add_runtime_arguments(parser)


def _briefs_command(args: argparse.Namespace, context: MctlContext) -> int:
    try:
        if args.brief_command == "list":
            records = list_briefs(context, BriefFilters(args.status, args.label))
            payload = _brief_payload(
                context,
                briefs=[brief.to_dict() for brief in records],
                diagnostics=brief_command_diagnostics(context, records),
            )
        elif args.brief_command == "show":
            record = show_brief(context, args.brief_id)
            payload = _brief_payload(
                context,
                brief=record.to_dict(),
                diagnostics=brief_command_diagnostics(context, (record,)),
            )
        elif args.brief_command == "options":
            options, diagnostics = brief_options_report(context, args.brief_id)
            payload = {
                "brief_id": args.brief_id,
                "diagnostics": _diagnostics_payload(context, diagnostics),
                "options": [option.to_dict() for option in options],
                "trace_id": context.trace_id,
            }
        elif args.brief_command == "validate":
            report = validate_brief(context, _validation_scope(context, args))
            payload = report.to_dict()
            payload["trace_id"] = context.trace_id
            payload["diagnostics"] = _diagnostics_payload(context, report.diagnostics)
        else:
            if args.brief_command == "doctor":
                report = doctor_briefs(context, args.brief_id)
                payload = report.to_dict()
                payload["trace_id"] = context.trace_id
                payload["diagnostics"] = _diagnostics_payload(context, report.diagnostics)
            elif args.brief_command == "create":
                plan = plan_create_brief(
                    context,
                    BriefCreateInput(
                        title=args.title or "",
                        body=_brief_body(context, args),
                        labels=tuple(args.label),
                        requested_by=args.requested_by,
                        sources=tuple(args.source),
                    ),
                )
                payload = dry_run_payload(plan) if args.dry_run else apply_effect_plan(context, plan).to_dict()
            elif args.brief_command == "adjudicate":
                plan = plan_adjudication(
                    context,
                    args.brief_id,
                    verdict=args.verdict,
                    reason=args.reason,
                    option=args.option,
                )
                payload = dry_run_payload(plan) if args.dry_run else apply_effect_plan(context, plan).to_dict()
            else:
                plan = plan_deferral(
                    context,
                    args.brief_id,
                    reason=args.reason,
                    until=args.until,
                    days=args.days,
                )
                payload = dry_run_payload(plan) if args.dry_run else apply_effect_plan(context, plan).to_dict()
    except (BriefError, MutationError) as error:
        print(render_diagnostic(error.diagnostic), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_render_brief_payload(payload))
    # A mutation that reports ERROR or FATAL has not fully succeeded, even
    # when the canonical write landed. Read commands still exit 0 with
    # diagnostics -- reporting drift is what they are for.
    if "applied" in payload and _has_blocking_diagnostic(payload):
        return 1
    return 0


def _has_blocking_diagnostic(payload: dict[str, object]) -> bool:
    diagnostics = payload.get("diagnostics")
    if not isinstance(diagnostics, list):
        return False
    return any(
        isinstance(item, dict) and item.get("severity") in {"ERROR", "FATAL"}
        for item in diagnostics
    )


def _validation_scope(context: MctlContext, args: argparse.Namespace) -> str | None:
    if args.all and args.brief_id:
        raise BriefError(_validation_scope_diagnostic(context, both=True))
    if args.all:
        return None
    if args.brief_id:
        return args.brief_id
    raise BriefError(_validation_scope_diagnostic(context, both=False))


def _validation_scope_diagnostic(context: MctlContext, *, both: bool) -> Diagnostic:
    message = (
        "briefs validate takes a brief id or --all, not both."
        if both
        else "briefs validate requires a brief id or --all."
    )
    return Diagnostic(
        severity=Severity.FATAL,
        code="MBRF014",
        message=message,
        hint="Run `mctl briefs validate <brief-id>` or `mctl briefs validate --all`.",
        facts={
            "city_path": str(context.city_root),
            "implementation_provenance": "mctl Slice 5 brief validation",
            "rig_name": context.rig_id,
            "rig_path": str(context.rig_root),
        },
        trace_id=context.trace_id,
    )


def _brief_body(context: MctlContext, args: argparse.Namespace) -> str:
    """Read the brief body from --body-file or --body.

    An unreadable body file is an empty body as far as policy is concerned,
    so it fails the same B1.5 check rather than crashing.
    """
    if args.body_file:
        path = Path(args.body_file)
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""
    return args.body or ""


def _work_command(args: argparse.Namespace, context: MctlContext) -> int:
    try:
        if args.work_command == "ready":
            payload = {
                "diagnostics": _diagnostics_payload(context, ()),
                "trace_id": context.trace_id,
                "work": [item.to_dict() for item in ready_work(context)],
            }
        elif args.work_command == "status":
            payload = {
                "diagnostics": _diagnostics_payload(context, ()),
                "trace_id": context.trace_id,
                "work": work_status(context, args.brief_id).to_dict(),
            }
        elif args.work_command == "provenance":
            payload = {
                "diagnostics": _diagnostics_payload(context, ()),
                "provenance": work_provenance(context, args.brief_id).to_dict(),
                "trace_id": context.trace_id,
            }
        else:
            plan = plan_dispatch(context, args.brief_id)
            payload = (
                dispatch_dry_run_payload(plan)
                if args.dry_run
                else apply_dispatch_plan(context, plan)
            )
    except WorkError as error:
        print(render_diagnostic(error.diagnostic), file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_render_brief_payload(payload))
    return 0


def _brief_payload(
    context: MctlContext, *, diagnostics: tuple[Diagnostic, ...], **payload: object
) -> dict[str, object]:
    payload["diagnostics"] = _diagnostics_payload(context, diagnostics)
    payload["trace_id"] = context.trace_id
    return payload


def _diagnostics_payload(
    context: MctlContext, diagnostics: tuple[Diagnostic, ...]
) -> list[dict[str, object]]:
    return [warning.to_dict() for warning in context.warnings] + [
        diagnostic.to_dict() for diagnostic in diagnostics
    ]


def _render_brief_payload(payload: dict[str, object]) -> str:
    """Render a payload for a human.

    Plan §1 promises concise human output OR structured JSON; this is the
    former. Every shape keeps its diagnostics and trace id, since those are
    what an operator acts on.
    """
    lines: list[str] = []

    briefs = payload.get("briefs")
    if isinstance(briefs, list):
        lines.append(f"briefs: {len(briefs)}")
        for brief in briefs:
            lines.append(f"  {_brief_line(brief)}")

    brief = payload.get("brief")
    if isinstance(brief, dict):
        lines.append(_brief_line(brief))
        for key in ("title", "created_at", "canonical_source"):
            if brief.get(key):
                lines.append(f"  {key}: {brief[key]}")

    options = payload.get("options")
    if isinstance(options, list):
        lines.append(f"options for {payload.get('brief_id', '?')}:")
        for option in options:
            mark = "+" if option.get("enabled") else "-"
            detail = "" if option.get("enabled") else f"  ({option.get('disabled_reason') or 'disabled'})"
            lines.append(f"  {mark} {option.get('id')}: {option.get('description', '')}{detail}")

    work = payload.get("work")
    if isinstance(work, list):
        lines.append(f"ready work: {len(work)}")
        for item in work:
            lines.append(f"  {_work_line(item)}")
    elif isinstance(work, dict):
        lines.append(_work_line(work))
        for blocker in work.get("blockers", []):
            lines.append(f"  {_diagnostic_line(blocker)}")

    if "valid" in payload:
        counts = payload.get("severity_counts") or {}
        verdict = "consistent" if payload.get("valid") else "DIVERGENT"
        lines.append(f"validate {payload.get('scope', '?')}: {verdict}")
        if isinstance(counts, dict):
            lines.append("  " + "  ".join(f"{key}={value}" for key, value in sorted(counts.items())))

    per_brief = payload.get("brief_diagnostics")
    if isinstance(per_brief, list):
        total = sum(len(entry.get("diagnostics", [])) for entry in per_brief)
        label = "validate" if "valid" in payload else "doctor"
        lines.append(f"{label}: {len(per_brief)} brief(s), {total} diagnostic(s)")
        for entry in per_brief:
            for diagnostic in entry.get("diagnostics", []):
                lines.append(f"  {entry.get('brief_id')}: {_diagnostic_line(diagnostic)}")
        if total == 0:
            lines.append("  no diagnostics")

    if "applied" in payload:
        lines.append(f"applied: {payload['applied']}")
        plan = payload.get("effect_plan")
        if isinstance(plan, dict):
            lines.append(f"  operation: {plan.get('operation', '?')}")
            for create in plan.get("bead_creates", []):
                lines.append(
                    f"  bead create: type={create.get('issue_type')} "
                    f"title={str(create.get('title', ''))[:60]!r}"
                )
            for update in plan.get("bead_updates", []):
                lines.append(f"  bead update: {update.get('id')} -> status={update.get('status')}")
            for create in plan.get("file_creates", []):
                lines.append(f"  cache create: {create.get('path')}")
            for write in plan.get("cache_updates", []):
                lines.append(f"  cache update: {write.get('path')}")

    for diagnostic in payload.get("diagnostics", []) or []:
        lines.append(_diagnostic_line(diagnostic))

    if payload.get("trace_id"):
        lines.append(f"trace_id: {payload['trace_id']}")

    return "\n".join(lines) if lines else "(no output)"


def _brief_line(brief: dict[str, object]) -> str:
    state = brief.get("decision_state") or brief.get("status") or "?"
    return f"{brief.get('brief_id', '?')}  [{state}]  {str(brief.get('title', ''))[:70]}"


def _work_line(item: dict[str, object]) -> str:
    return (
        f"{item.get('brief_id', '?')} -> {item.get('bead_id', '?')}  "
        f"[{item.get('readiness', '?')}]  {str(item.get('title', ''))[:60]}"
    )


def _diagnostic_line(diagnostic: dict[str, object]) -> str:
    return (
        f"[{diagnostic.get('severity', '?')}] {diagnostic.get('code', '?')}: "
        f"{diagnostic.get('message', '')}"
    )


def _city_not_active_diagnostic(context: MctlContext) -> Diagnostic:
    facts = {
        "city_path": str(context.city_root),
        "implementation_provenance": "mctl city liveness gate",
        "rig_name": context.rig_id,
        "rig_path": str(context.rig_root),
    }
    if context.city_endpoint is not None:
        facts["data_location"] = context.city_endpoint
    return Diagnostic(
        severity=Severity.FATAL,
        code="MCTL_CITY_NOT_ACTIVE",
        message=(
            "The Gas City data plane for this rig is not reachable, so canonical "
            "bead state cannot be read."
        ),
        hint="Start the city with `gc supervisor run`, then re-run this command.",
        facts=facts,
        trace_id=context.trace_id,
    )


def _render_liveness(context: MctlContext) -> str:
    """One line on the data plane.

    This is the field an operator wants during an outage, so it belongs in the
    human view -- not only under --json, which is the shape they are least
    likely to be using while something is broken.
    """
    if context.city_active is None:
        return "embedded Dolt (rig does not use a Dolt server)"
    if context.city_active:
        return f"reachable at {context.city_endpoint}"
    endpoint = context.city_endpoint or "the configured endpoint"
    return f"NOT REACHABLE at {endpoint} — bead commands will fail closed"


def _render_explain(context: MctlContext) -> str:
    lines = [
        f"Trace ID: {context.trace_id}",
        f"City discovery: {context.discovery_path}",
        f"City root: {context.city_root}",
        f"Rig: {context.rig_id}",
        f"Rig database: {context.rig_db}",
        f"Source checkout: {context.source_checkout}",
        f"paths.toml: {context.paths_toml}",
        f"gates.toml: {context.gates_toml}",
        f"Data plane: {_render_liveness(context)}",
    ]
    for warning in context.warnings:
        lines.append(render_diagnostic(warning))
    return "\n".join(lines)
