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
from .diagnostics import Diagnostic, render_diagnostic


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        context = resolve_context(
            Path.cwd(),
            city=Path(args.city) if args.city else None,
            rig=args.rig,
            require_runtime_city=True,
            require_explicit_runtime=args.command == "briefs",
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
    return _briefs_command(args, context)


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
            report = doctor_briefs(context, args.brief_id)
            payload = report.to_dict()
            payload["trace_id"] = context.trace_id
            payload["diagnostics"] = _diagnostics_payload(context, report.diagnostics)
    except BriefError as error:
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
