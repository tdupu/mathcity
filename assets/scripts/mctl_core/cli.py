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
    present_it_label,
    show_brief,
    validate_brief,
    validation_scope,
)
from .city import for_each_rig, merge_outcomes
from .context import ContextError, MctlContext, resolve_context
from .diagnostics import Diagnostic, render_diagnostic
from .liveness import city_not_active_diagnostic
from .trace import fold, new_trace_id, read_rows, trace_not_found_diagnostic
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
    if args.command == "mcp":
        # The MCP server resolves a fresh context per tool call, so resolving
        # one here would only produce a stale trace id nothing uses. Imported
        # lazily: mcp_server imports this module's siblings, and starting a
        # server is not a cost every `mctl briefs list` should pay.
        from .mcp_server import serve_from_args

        return serve_from_args(args)
    if args.command == "dashboard":
        # Same reasoning as `mcp`: the dashboard resolves a fresh context per
        # request through its own MCP client, so a context resolved here would
        # be stale before the first page render. Imported lazily so no ordinary
        # CLI invocation pays for http.server.
        from mctl_dashboard.server import serve_from_args as serve_dashboard

        return serve_dashboard(args)
    if getattr(args, "all_rigs", False):
        # Cross-rig reads never resolve a single rig: on a multi-rig city that
        # resolution is exactly the MCTL_CONTEXT_RIG_REQUIRED error this flag
        # exists to answer. `city.py` resolves one context per rig instead.
        return _all_rigs_command(args)
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
        print(render_diagnostic(city_not_active_diagnostic(context)), file=sys.stderr)
        return 1
    if args.command == "briefs":
        return _briefs_command(args, context)
    if args.command == "trace":
        return _trace_command(args, context)
    return _work_command(args, context)


#: Which arrays each cross-rig read contributes, mirroring the MCP server's
#: `CROSS_RIG_ARRAYS`. Both adapters run the same `city.for_each_rig` over the
#: same per-rig core call, so the CLI and the MCP tool cannot disagree about
#: what a city-wide answer contains.
_ALL_RIGS_ARRAYS: dict[tuple[str, str], tuple[str, ...]] = {
    ("briefs", "list"): ("briefs",),
    ("briefs", "validate"): ("briefs", "brief_diagnostics"),
    ("work", "ready"): ("work",),
}


def _all_rigs_command(args: argparse.Namespace) -> int:
    """Run one read against every registered rig.

    Exits non-zero when any rig could not be read. A shell caller that treats
    a partial city-wide answer as complete is the failure this whole path
    exists to prevent, and an exit code is the only signal a pipeline sees.
    """
    key = (args.command, getattr(args, "brief_command", None) or getattr(args, "work_command", None))
    arrays = _ALL_RIGS_ARRAYS[key]

    def run(context: MctlContext) -> dict[str, object]:
        if key == ("briefs", "list"):
            records = list_briefs(
                context, BriefFilters(args.status, args.label), bodies=args.bodies
            )
            return _brief_payload(
                context,
                briefs=[brief.to_dict() for brief in records],
                diagnostics=brief_command_diagnostics(context, records),
            )
        if key == ("briefs", "validate"):
            report = validate_brief(context, _validation_scope(context, args))
            payload = report.to_dict()
            payload["diagnostics"] = _diagnostics_payload(context, report.diagnostics)
            return payload
        return {
            "diagnostics": _diagnostics_payload(context, ()),
            "work": [item.to_dict() for item in ready_work(context)],
        }

    try:
        scope, outcomes = for_each_rig(
            Path.cwd(), city=Path(args.city) if args.city else None, env=os.environ, run=run
        )
    except ContextError as error:
        print(render_diagnostic(error.diagnostic), file=sys.stderr)
        return 1
    payload = merge_outcomes(
        scope,
        outcomes,
        arrays=arrays,
        trace_id=new_trace_id(),
        validity=key == ("briefs", "validate"),
    )
    if args.json:
        print(json.dumps(payload, indent=2, sort_keys=True))
    else:
        print(_render_all_rigs_payload(payload))
    return 1 if any(not outcome.ok for outcome in outcomes) else 0


def _render_all_rigs_payload(payload: dict[str, object]) -> str:
    """Human output that leads with the per-rig breakdown.

    The aggregate answers "how much is there"; the breakdown answers "where is
    it", and a degraded rig has to be visible in the same glance -- a total
    that quietly omits a rig reads as complete.
    """
    rigs = [entry for entry in payload.get("rigs") or () if isinstance(entry, dict)]
    readable = [entry for entry in rigs if entry.get("ok")]
    degraded = [entry for entry in rigs if not entry.get("ok")]
    lines = [
        f"city: {payload.get('city_root', '?')}  "
        f"({len(readable)} of {len(rigs)} rigs readable)"
    ]
    for entry in rigs:
        counts = entry.get("counts") or {}
        detail = (
            "  ".join(f"{name}={value}" for name, value in sorted(counts.items()))
            if entry.get("ok")
            else f"could not read ({entry.get('reason')})"
        )
        lines.append(f"  {'ok ' if entry.get('ok') else 'DEGRADED'} {entry.get('rig_id')}: {detail}")
    if degraded:
        lines.append(
            f"  {len(degraded)} rig(s) could not be read; totals below are incomplete."
        )
    lines.append("")
    lines.append(_render_brief_payload(payload))
    return "\n".join(lines)


def _trace_command(args: argparse.Namespace, context: MctlContext) -> int:
    record = fold(read_rows(context.rig_root), args.trace_id)
    if record is None:
        print(
            render_diagnostic(trace_not_found_diagnostic(context, args.trace_id)),
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
    _add_mcp_parser(commands)
    _add_dashboard_parser(commands)
    work = commands.add_parser("work", help="inspect and dispatch brief-backed work")
    work_commands = work.add_subparsers(dest="work_command", required=True)
    _add_work_ready_parser(work_commands)
    _add_work_status_parser(work_commands)
    _add_work_provenance_parser(work_commands)
    _add_work_dispatch_parser(work_commands)
    return parser


def _add_mcp_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Expose the typed MCP server through the same entry point as the CLI.

    One binary, two adapters. `--client-class` defaults to `external`, the
    closed surface, so an operator who forgets the flag gets no tools rather
    than the whole surface.
    """
    parser = commands.add_parser("mcp", help="serve the typed MCP tool surface")
    subcommands = parser.add_subparsers(dest="mcp_command", required=True)
    serve = subcommands.add_parser("serve", help="serve MCP over stdio (JSON-RPC 2.0)")
    serve.add_argument("--city", help="default registered Gas City root for every tool call")
    serve.add_argument("--rig", help="default registered rig identifier for every tool call")
    serve.add_argument(
        "--client-class",
        dest="client_class",
        choices=["internal", "external"],
        default=None,
        help="internal exposes the full surface; external is gated (default)",
    )


def _add_dashboard_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    """Expose the Slice 8 operator dashboard through the same entry point.

    The dashboard is a client of the MCP surface, not a third adapter over the
    core: it launches its own `mctl mcp serve` subprocess. `--host` defaults to
    loopback and is not given an all-interfaces default, because the client
    class it must run as (`internal`) sees the full mutating surface.
    """
    parser = commands.add_parser("dashboard", help="serve the operator dashboard over HTTP")
    subcommands = parser.add_subparsers(dest="dashboard_command", required=True)
    serve = subcommands.add_parser("serve", help="serve the dashboard on localhost")
    serve.add_argument("--city", help="registered Gas City root the dashboard operates on")
    serve.add_argument("--rig", help="registered rig identifier the dashboard operates on")
    serve.add_argument("--host", default="127.0.0.1", help="bind address (default 127.0.0.1)")
    serve.add_argument("--port", type=int, default=8471, help="bind port (default 8471)")


def _add_runtime_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--city", help="registered Gas City root")
    parser.add_argument("--rig", help="registered rig identifier")
    parser.add_argument("--json", action="store_true", help="render deterministic JSON")


def _add_all_rigs_argument(parser: argparse.ArgumentParser) -> None:
    """The plan's explicit cross-rig opt-in (Global Constraints, Slice 2).

    Explicit because a command that silently spanned rigs would make "which
    store did that read" unanswerable from the command line. The name is the
    plan's own; `mctl_core/city.py` is the single implementation behind it,
    here and on the matching MCP `all_rigs` input.
    """
    parser.add_argument(
        "--all-rigs",
        action="store_true",
        help="read every registered rig; rows carry their rig and unreadable rigs are named",
    )


def _add_brief_list_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("list", help="list canonical decision brief beads")
    parser.add_argument("--status", help="filter by raw bead or decision status")
    parser.add_argument("--label", help="filter by brief label")
    # Off by default: with every document body attached this read measures
    # 5.17 MB city-wide, which makes a roster read a content read for every
    # caller that wanted titles. A record whose body is left out says so in
    # `body_elided`; nothing is ever truncated. `briefs show` always carries
    # the body, for bead-backed and document briefs alike.
    parser.add_argument(
        "--bodies",
        action="store_true",
        help="attach each document brief's body and parsed sections (large)",
    )
    _add_all_rigs_argument(parser)
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
    _add_all_rigs_argument(parser)
    parser.add_argument("brief_id", nargs="?")
    parser.add_argument("--all", action="store_true", help="validate every canonical brief")
    _add_runtime_arguments(parser)


def _add_work_ready_parser(commands: argparse._SubParsersAction[argparse.ArgumentParser]) -> None:
    parser = commands.add_parser("ready", help="list ready brief-backed work")
    _add_all_rigs_argument(parser)
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
            records = list_briefs(
                context, BriefFilters(args.status, args.label), bodies=args.bodies
            )
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
    return validation_scope(context, args.brief_id, args.all)


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
        lines.extend(_brief_body_lines(brief))

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


def _brief_body_lines(brief: dict[str, object]) -> list[str]:
    """Summarize the body for a terminal; never dump it.

    A live brief body runs to ~2,400 characters. Printing it into a command
    whose other output is one line per field would bury every other field,
    so the human shape is a table of contents: how big the body is, which
    sections it has, and where each starts. `--json` is the full text.
    """
    if "body" not in brief:
        return []
    body = str(brief.get("body") or "")
    sections = brief.get("sections")
    sections = sections if isinstance(sections, list) else []
    lines = [
        f"  body: (empty)"
        if not body.strip()
        else f"  body: {len(body)} chars, {len(body.splitlines())} lines"
    ]
    lines.append(f"  sections: {len(sections)}")
    for section in sections:
        # Mapped sections show the canonical present-it name, so the table of
        # contents reads the same across briefs that word their headings
        # differently. Unmapped ones show the brief's own heading, since that
        # is the only name they have. Either way `--json` carries both.
        label = present_it_label(section.get("section_index"), section.get("section_key"))
        lines.append(
            f"    L{section.get('start_line')}  {label or section.get('heading', '')}"
        )
    for diagnostic in brief.get("body_diagnostics") or []:
        lines.append(f"  {_diagnostic_line(diagnostic)}")
    return lines


def _brief_line(brief: dict[str, object]) -> str:
    """One brief per line, with its store named when it is not the bead store.

    A manifest-sourced record has no title and no bead; printing it exactly
    like a bead-backed brief would present a row nothing attests as though a
    decision bead carried it.
    """
    state = brief.get("decision_state") or brief.get("status") or "?"
    # A record's origin is one of three, and "manifest-only" said for all of
    # them would call a deposited stack file a manifest row.
    origin = {"bead": "", "stack_file": "  (stack file)", "manifest": "  (manifest-only)"}.get(
        str(brief.get("source", "bead")), "  (no bead)"
    )
    title = str(brief.get("title") or "")[:70]
    return f"{brief.get('brief_id', '?')}  [{state}]{origin}  {title}"


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
