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
)
from .context import ContextError, MctlContext, resolve_context
from .diagnostics import Diagnostic, Severity, render_diagnostic
from .trace import fold, read_rows
from .effects import (
    MutationError,
    apply_effect_plan,
    dry_run_payload,
    plan_adjudication,
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
        else:
            if args.brief_command == "doctor":
                report = doctor_briefs(context, args.brief_id)
                payload = report.to_dict()
                payload["trace_id"] = context.trace_id
                payload["diagnostics"] = _diagnostics_payload(context, report.diagnostics)
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
    return 0


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
    return json.dumps(payload, indent=2, sort_keys=True)


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
    ]
    for warning in context.warnings:
        lines.append(render_diagnostic(warning))
    return "\n".join(lines)
