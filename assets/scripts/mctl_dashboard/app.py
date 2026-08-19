"""Routes for the operator dashboard.

`Dashboard.handle` is a pure function from a `Request` to a `Response`: no
socket, no global state beyond the preview store. `server.py` adapts
`http.server` onto it. That split is what lets the view and mutation-safety
tests drive every path directly while `test_dashboard_transport.py` proves the
real HTTP and stdio wiring.

Route inventory, deliberately small:

    GET  /                 context + decision queue
    GET  /briefs           the queue, filterable
    GET  /briefs/<id>      one brief: canonical fields, options, diagnostics
    GET  /diagnostics      rig-wide, grouped by severity and code
    GET  /work             brief-backed work readiness
    GET  /validate         canonical-versus-cache consistency
    GET  /trace            one trace, plus a replay preview that replays nothing
    POST /preview          dry-run an operation. Writes nothing.
    POST /apply            confirm a preview that is still true.

There is no route that takes a command, and `MUTATION_ROUTES` is the whole
set of paths that can write anything.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qs, unquote

from . import render
from .client import McpClient, ToolFailure, ToolResponse
from .preview import Preview, PreviewStore, context_fingerprint, stable_digest, target_fingerprint


@dataclass(frozen=True)
class Request:
    method: str
    path: str
    query: dict[str, str] = field(default_factory=dict)
    form: dict[str, str] = field(default_factory=dict)

    @classmethod
    def get(cls, path: str, **query: str) -> "Request":
        return cls("GET", path, {key: str(value) for key, value in query.items()}, {})

    @classmethod
    def post(cls, path: str, **form: str) -> "Request":
        return cls("POST", path, {}, {key: str(value) for key, value in form.items()})

    @classmethod
    def from_wire(cls, method: str, raw_path: str, body: str = "") -> "Request":
        path, _, query = raw_path.partition("?")
        return cls(
            method=method.upper(),
            path=unquote(path) or "/",
            query={key: values[0] for key, values in parse_qs(query).items()},
            form={key: values[0] for key, values in parse_qs(body).items()},
        )


@dataclass(frozen=True)
class Response:
    status: int
    body: str
    content_type: str = "text/html; charset=utf-8"


@dataclass(frozen=True)
class Operation:
    """One mutation the dashboard can drive, and the typed tool behind it."""

    name: str
    tool: str
    title: str
    needs_brief: bool = True


OPERATIONS: dict[str, Operation] = {
    "adjudicate": Operation("adjudicate", "briefs_adjudicate", "adjudication"),
    "defer": Operation("defer", "briefs_defer", "deferral"),
    "dispatch": Operation("dispatch", "work_dispatch", "work dispatch"),
    "create": Operation("create", "briefs_create", "brief creation", needs_brief=False),
}


def _dashboard_diagnostic(
    severity: str, code: str, message: str, hint: str, **facts: object
) -> dict[str, Any]:
    return {
        "severity": severity,
        "code": code,
        "message": message,
        "hint": hint,
        "facts": {key: str(value) for key, value in facts.items()},
    }


class Dashboard:
    """The operator surface. A client of the typed MCP tools, nothing more."""

    #: Every path that can write. Asserted by the tests so a future route
    #: cannot quietly become a third mutation path.
    MUTATION_ROUTES = ("/preview", "/apply")

    def __init__(self, client: McpClient):
        self.client = client
        self.previews = PreviewStore()

    # -- dispatch --

    def handle(self, request: Request) -> Response:
        if request.method == "POST":
            if request.path == "/preview":
                return self._preview(request)
            if request.path == "/apply":
                return self._apply(request)
            return self._not_found(request)
        if request.path == "/":
            return self._overview()
        if request.path == "/briefs":
            return self._briefs(request)
        if request.path.startswith("/briefs/"):
            return self._brief(request.path[len("/briefs/") :])
        if request.path == "/diagnostics":
            return self._diagnostics()
        if request.path == "/work":
            return self._work()
        if request.path == "/validate":
            return self._validate()
        if request.path == "/trace":
            return self._trace(request)
        return self._not_found(request)

    # -- MCP helpers --

    def _context(self) -> Mapping[str, Any]:
        return self.client.call("context_resolve").payload

    def _context_bar(self, context: Mapping[str, Any], *, compact: bool = True) -> str:
        return render.context_panel(context, compact=compact)

    def _page(
        self,
        title: str,
        current: str,
        context: Mapping[str, Any],
        sections: Sequence[str],
        *,
        status: int = 200,
        compact_context: bool = True,
    ) -> Response:
        return Response(
            status,
            render.page(
                title,
                current,
                sections,
                context_bar=self._context_bar(context, compact=compact_context),
            ),
        )

    # -- read views --

    def _overview(self) -> Response:
        context = self._context()
        listing = self.client.call("briefs_list")
        briefs = list(listing.payload.get("briefs") or ())
        sections = [
            render.queue_panel(briefs),
            render.diagnostics_sections(
                listing.diagnostics,
                listing.untrusted_diagnostics,
                listing.artifact_trust,
                heading="Queue diagnostics",
            ),
        ]
        return self._page("Overview", "/", context, sections, compact_context=False)

    def _briefs(self, request: Request) -> Response:
        context = self._context()
        arguments = {
            key: value
            for key, value in (
                ("status", request.query.get("status")),
                ("label", request.query.get("label")),
            )
            if value
        }
        listing = self.client.call("briefs_list", arguments)
        briefs = list(listing.payload.get("briefs") or ())
        filters = (
            '<section class="panel" data-region="filters"><h2>Filter</h2>'
            '<form class="operation" method="get" action="/briefs">'
            f'<label>Bead or decision status<input type="text" name="status" value="{render.esc(request.query.get("status") or "")}"></label>'
            f'<label>Label<input type="text" name="label" value="{render.esc(request.query.get("label") or "")}"></label>'
            '<div><button type="submit" class="secondary">Apply filter</button></div>'
            "</form></section>"
        )
        sections = [
            filters,
            '<section class="panel" data-region="brief-list">'
            f"<h2>Briefs ({len(briefs)})</h2>"
            '<p class="lede">Canonical source <span class="mono">bead_store</span>, '
            'read through <span class="mono">briefs_list</span>.</p>'
            + render.brief_rows(briefs)
            + "</section>",
            render.artifact_trust_panel(listing.artifact_trust),
        ]
        return self._page("Briefs", "/briefs", context, sections)

    def _brief(self, brief_id: str) -> Response:
        context = self._context()
        try:
            shown = self.client.call("briefs_show", {"brief_id": brief_id})
        except ToolFailure as failure:
            return self._page(
                "Brief not found",
                "/briefs",
                context,
                [
                    render.notice_panel(
                        "No such brief",
                        f"The canonical bead store has no brief named {brief_id!r}.",
                        failure.diagnostics,
                        region="brief-missing",
                    )
                ],
                status=404,
            )
        brief = dict(shown.payload.get("brief") or {})
        options = self._options(brief_id)
        doctor = self._doctor(brief_id)
        sections = [
            render.brief_detail_panel(brief),
            render.artifact_trust_panel(shown.artifact_trust),
            render.options_panel(options.payload.get("options") or ()) if options else "",
            render.operation_forms(brief_id, (options.payload.get("options") or ()) if options else ()),
            render.diagnostics_sections(
                doctor.diagnostics if doctor else [],
                doctor.untrusted_diagnostics if doctor else [],
                None,
                heading="Brief diagnostics",
            ),
        ]
        return self._page(str(brief.get("title") or brief_id), "/briefs", context, sections)

    def _options(self, brief_id: str) -> ToolResponse | None:
        try:
            return self.client.call("briefs_options", {"brief_id": brief_id})
        except ToolFailure:
            return None

    def _doctor(self, brief_id: str) -> ToolResponse | None:
        try:
            return self.client.call("briefs_doctor", {"brief_id": brief_id})
        except ToolFailure:
            return None

    def _diagnostics(self) -> Response:
        context = self._context()
        report = self.client.call("briefs_validate", {"all": True})
        counts = report.payload.get("severity_counts") or {}
        summary = (
            '<section class="panel" data-region="severity-summary"><h2>By severity</h2>'
            '<p class="lede">Rig-wide, from <span class="mono">briefs_validate</span> - the strict '
            "superset of the doctor invariants. Severity is styled; the code is always shown.</p>"
            '<div class="scroll-x"><table><thead><tr><th>Severity</th><th>Count</th></tr></thead><tbody>'
            + "".join(
                f'<tr><td><span class="severity severity-{severity}">{severity}</span></td>'
                f'<td class="mono">{int(counts.get(severity, 0))}</td></tr>'
                for severity in render.SEVERITY_ORDER
            )
            + "</tbody></table></div></section>"
        )
        sections = [
            summary,
            render.diagnostics_sections(
                report.diagnostics,
                report.untrusted_diagnostics,
                report.artifact_trust,
                heading="Rig diagnostics",
            ),
        ]
        return self._page("Diagnostics", "/diagnostics", context, sections)

    def _validate(self) -> Response:
        context = self._context()
        report = self.client.call("briefs_validate", {"all": True})
        verdict = "consistent" if report.payload.get("valid") else "inconsistent"
        sections = [
            '<section class="panel" data-region="validation">'
            f"<h2>Canonical versus cache: {render.esc(verdict)}</h2>"
            '<p class="lede">Scope <span class="mono">'
            f'{render.esc(report.payload.get("scope"))}</span>. This view reads only; it never '
            "repairs, and no view in this dashboard does.</p>"
            + render.brief_rows(list(report.payload.get("briefs") or ()))
            + "</section>",
            render.artifact_trust_panel(report.artifact_trust),
        ]
        return self._page("Validate", "/validate", context, sections)

    def _work(self) -> Response:
        context = self._context()
        ready = self.client.call("work_ready")
        items = list(ready.payload.get("work") or ())
        rows = "".join(
            "<tr>"
            f'<td><a href="/briefs/{render.esc(item.get("brief_id"))}">'
            f'<span class="mono">{render.esc(item.get("brief_id"))}</span></a></td>'
            f'<td><span class="mono">{render.esc(item.get("bead_id"))}</span></td>'
            f'<td>{render.esc(item.get("title"))}</td>'
            f'<td><span class="badge">{render.esc(item.get("readiness"))}</span></td>'
            f'<td class="mono">{len(item.get("blockers") or ())}</td>'
            "</tr>"
            for item in items
        )
        blockers: list[Mapping[str, Any]] = []
        for item in items:
            blockers.extend(item.get("blockers") or ())
        sections = [
            '<section class="panel" data-region="work">'
            f"<h2>Ready work ({len(items)})</h2>"
            '<p class="lede">Brief-backed work whose canonical state permits dispatch, from '
            '<span class="mono">work_ready</span>. Dispatch itself is preview-first, from the '
            "brief page.</p>"
            + (
                '<div class="scroll-x"><table><thead><tr><th>Brief</th><th>Work bead</th>'
                "<th>Title</th><th>Readiness</th><th>Blockers</th></tr></thead>"
                f"<tbody>{rows}</tbody></table></div>"
                if rows
                else '<p class="lede">No brief-backed work is ready in this rig.</p>'
            )
            + "</section>",
            render.diagnostics_sections(
                list(ready.diagnostics) + blockers, [], None, heading="Work diagnostics"
            ),
        ]
        return self._page("Work", "/work", context, sections)

    def _trace(self, request: Request) -> Response:
        context = self._context()
        trace_id = request.query.get("trace_id", "").strip()
        search = (
            '<section class="panel" data-region="trace-search"><h2>Find a trace</h2>'
            '<form class="operation" method="get" action="/trace">'
            f'<label>Trace id<input type="text" name="trace_id" value="{render.esc(trace_id)}"></label>'
            '<div><button type="submit" class="secondary">Show trace</button></div>'
            "</form></section>"
        )
        if not trace_id:
            return self._page("Traces", "/", context, [search])
        try:
            shown = self.client.call("trace_show", {"trace_id": trace_id})
        except ToolFailure as failure:
            return self._page(
                "Traces",
                "/",
                context,
                [
                    search,
                    render.notice_panel(
                        "No such trace",
                        f"No recorded trace matches {trace_id!r}.",
                        failure.diagnostics,
                        region="trace-missing",
                    ),
                ],
            )
        record = dict(shown.payload.get("trace") or {})
        replay = self.client.call("trace_replay_preview", {"trace_id": trace_id})
        sections = [
            search,
            '<section class="panel" data-region="trace">'
            f'<h2>Trace {render.esc(record.get("trace_id"))}</h2>'
            f'<dl class="facts"><dt>Outcome</dt><dd><span class="badge">{render.esc(record.get("outcome"))}</span></dd>'
            f'<dt>Phases</dt><dd class="mono">{render.esc(", ".join(record.get("phases") or ()))}</dd></dl>'
            "</section>",
            '<section class="panel" data-region="replay-preview">'
            "<h2>Replay preview</h2>"
            '<p class="lede">A read of what this trace planned. It reapplies nothing, and there '
            "is no control here that could.</p>"
            + render.diagnostic_list(
                list(replay.payload.get("replay_blockers") or ()),
                empty="No replay blockers recorded.",
            )
            + f'<pre class="plan">{render.esc(_pretty(replay.payload.get("planned_effects") or []))}</pre>'
            "</section>",
        ]
        return self._page("Traces", "/", context, sections)

    def _not_found(self, request: Request) -> Response:
        try:
            context = self._context()
        except ToolFailure:  # pragma: no cover - defensive
            context = {}
        return self._page(
            "Not found",
            "/",
            context,
            [
                render.notice_panel(
                    "No such page",
                    f"{request.method} {request.path} is not a dashboard route.",
                    [
                        _dashboard_diagnostic(
                            "WARN",
                            "MCTL_DASH_NO_ROUTE",
                            f"{request.method} {request.path} is not a route this dashboard serves.",
                            "Use the navigation above; the dashboard exposes read views plus "
                            "/preview and /apply.",
                            requested_path=request.path,
                        )
                    ],
                    region="not-found",
                )
            ],
            status=404,
        )

    # -- mutations --

    def _preview(self, request: Request) -> Response:
        operation = OPERATIONS.get(request.form.get("operation", "").strip())
        if operation is None:
            return self._mutation_notice(
                "Unknown operation",
                400,
                [
                    _dashboard_diagnostic(
                        "ERROR",
                        "MCTL_DASH_UNKNOWN_OPERATION",
                        "That operation is not one the dashboard can drive.",
                        "The dashboard drives adjudicate, defer, dispatch, and create - each "
                        "through its own typed MCP tool. It has no generic command surface.",
                        requested_operation=request.form.get("operation", ""),
                    )
                ],
            )
        brief_id = request.form.get("brief_id", "").strip() or None
        if operation.needs_brief and not brief_id:
            return self._mutation_notice(
                "No target brief",
                400,
                [
                    _dashboard_diagnostic(
                        "ERROR",
                        "MCTL_DASH_TARGET_REQUIRED",
                        f"{operation.name} needs a target brief bead.",
                        "Start from a brief page so the target is unambiguous.",
                        requested_operation=operation.name,
                    )
                ],
            )
        arguments = _arguments_for(operation, brief_id, request.form)
        return self._render_preview(operation, brief_id, arguments, heading="Dry-run preview")

    def _render_preview(
        self,
        operation: Operation,
        brief_id: str | None,
        arguments: Mapping[str, Any],
        *,
        heading: str,
        prefix: Sequence[str] = (),
        status: int = 200,
    ) -> Response:
        context = self._context()
        try:
            planned = self.client.call(operation.tool, {**arguments, "dry_run": True})
        except ToolFailure as failure:
            # The refusal names its blocking code in `facts`, but the operator
            # needs the whole set: the brief's own diagnostics follow, each
            # with its code, so "blocked" is a diagnosis rather than a wall.
            doctor = self._doctor(brief_id) if brief_id else None
            return self._page(
                "Blocked",
                "/briefs",
                context,
                [
                    *prefix,
                    render.notice_panel(
                        f"{operation.title.capitalize()} is blocked",
                        "Nothing was written. The typed tool refused to plan this mutation, and "
                        "the diagnostic code behind the refusal is below.",
                        failure.diagnostics,
                        region="blocked",
                    ),
                    render.diagnostics_sections(
                        doctor.diagnostics if doctor else [],
                        doctor.untrusted_diagnostics if doctor else [],
                        None,
                        heading="Diagnostics on this brief",
                    )
                    if doctor
                    else "",
                ],
                status=409,
            )
        target = self._target(brief_id)
        preview = self.previews.create(
            operation=operation.name,
            tool=operation.tool,
            arguments=arguments,
            brief_id=brief_id,
            context=context,
            target=target,
            payload=planned.payload,
        )
        sections = [
            *prefix,
            # The brief as it reads *now*. On a fresh preview replacing a stale
            # one this is the whole point: the operator has to be able to see
            # what moved before confirming against the new state.
            render.brief_detail_panel(target) if target else "",
            render.effect_plan_panel(preview.effect_plan, title=heading),
            render.confirm_panel(preview.token, operation.title, brief_id),
            render.artifact_trust_panel(planned.artifact_trust),
            render.diagnostics_sections(
                planned.diagnostics, planned.untrusted_diagnostics, None, heading="Preview diagnostics"
            ),
        ]
        return self._page(f"Preview {operation.title}", "/briefs", context, sections, status=status)

    def _apply(self, request: Request) -> Response:
        preview = self.previews.pop(request.form.get("token"))
        if preview is None:
            return self._mutation_notice(
                "No preview to apply",
                400,
                [
                    _dashboard_diagnostic(
                        "ERROR",
                        "MCTL_DASH_PREVIEW_REQUIRED",
                        "There is no live preview for this confirmation.",
                        "Previews are single use and are consumed by the first confirm attempt. "
                        "Take a fresh preview and confirm that one.",
                    )
                ],
            )
        operation = OPERATIONS[preview.operation]
        context = self._context()
        target = self._target(preview.brief_id)
        try:
            replanned = self.client.call(operation.tool, {**preview.arguments, "dry_run": True})
        except ToolFailure as failure:
            return self._page(
                "Blocked",
                "/briefs",
                context,
                [
                    render.notice_panel(
                        "The operation is no longer plannable",
                        "Nothing was written. Re-planning at confirm time failed, so the preview "
                        "you were holding no longer describes anything that can be applied.",
                        failure.diagnostics,
                        region="blocked",
                    )
                ],
                status=409,
            )
        changed = preview.matches(
            context=context_fingerprint(context),
            target=target_fingerprint(target),
            plan=stable_digest(replanned.payload.get("effect_plan")),
        )
        if changed:
            return self._stale(preview, operation, changed, replanned)
        applied = self.client.call(operation.tool, {**preview.arguments, "dry_run": False})
        return self._page(
            f"Applied {operation.title}",
            "/briefs",
            context,
            [
                render.applied_panel(applied.payload, operation.title),
                render.effect_plan_panel(
                    dict(applied.payload.get("effect_plan") or {}), title="What was applied"
                ),
                render.artifact_trust_panel(applied.artifact_trust),
                render.diagnostics_sections(
                    applied.diagnostics,
                    applied.untrusted_diagnostics,
                    None,
                    heading="Apply diagnostics",
                ),
            ],
        )

    def _stale(
        self,
        preview: Preview,
        operation: Operation,
        changed: Sequence[str],
        replanned: ToolResponse,
    ) -> Response:
        """Refuse, then replace: a refusal with no way forward is a dead end.

        The stale token was already popped, so it cannot be retried; what the
        operator gets back is a *new* preview of the current world, which they
        must read and confirm on its own terms.
        """
        described = ", ".join(changed)
        notice = render.notice_panel(
            "This preview is stale - nothing was applied",
            f"The {described} changed after the preview was taken, so the plan you confirmed is "
            "no longer the plan that would run. A fresh preview of the current state is below; "
            "read it and confirm that one. The stale preview has been discarded.",
            [
                _dashboard_diagnostic(
                    "ERROR",
                    "MCTL_DASH_PREVIEW_STALE",
                    f"Preview for {operation.name} is stale: {described} changed since it was taken.",
                    "Confirm the fresh preview below, or navigate away and take a new one.",
                    changed=described,
                    operation=operation.name,
                    target_brief_id=str(preview.brief_id or ""),
                )
            ],
            region="stale-preview",
        )
        return self._render_preview(
            operation,
            preview.brief_id,
            preview.arguments,
            heading="Fresh dry-run preview",
            prefix=[notice],
            status=409,
        )

    def _target(self, brief_id: str | None) -> Mapping[str, Any] | None:
        """The canonical bead record a preview was computed against."""
        if not brief_id:
            return None
        try:
            return dict(self.client.call("briefs_show", {"brief_id": brief_id}).payload.get("brief") or {})
        except ToolFailure:
            # A target that can no longer be read is itself a change; the
            # fingerprint of None will not match the one recorded at preview.
            return None

    def _mutation_notice(self, title: str, status: int, diagnostics: Sequence[Mapping[str, Any]]) -> Response:
        try:
            context = self._context()
        except ToolFailure:  # pragma: no cover - defensive
            context = {}
        return self._page(
            title,
            "/briefs",
            context,
            [
                render.notice_panel(
                    title,
                    "Nothing was written.",
                    diagnostics,
                    region="mutation-refused",
                )
            ],
            status=status,
        )


def _arguments_for(
    operation: Operation, brief_id: str | None, form: Mapping[str, str]
) -> dict[str, Any]:
    """Build typed tool arguments from form fields. No passthrough, ever.

    Every field is named here and mapped to a declared schema property, so a
    surprise form field cannot become a tool argument.
    """
    if operation.name == "adjudicate":
        arguments: dict[str, Any] = {"brief_id": brief_id}
        for key in ("verdict", "reason", "option"):
            value = (form.get(key) or "").strip()
            if value:
                arguments[key] = value
        arguments.setdefault("reason", "")
        return arguments
    if operation.name == "defer":
        arguments = {"brief_id": brief_id, "reason": (form.get("reason") or "").strip()}
        until = (form.get("until") or "").strip()
        days = (form.get("days") or "").strip()
        if until:
            arguments["until"] = until
        elif days.isdigit():
            arguments["days"] = int(days)
        return arguments
    if operation.name == "dispatch":
        return {"brief_id": brief_id}
    labels = [item.strip() for item in (form.get("labels") or "").split(",") if item.strip()]
    sources = [item.strip() for item in (form.get("sources") or "").split(",") if item.strip()]
    arguments = {
        "title": (form.get("title") or "").strip(),
        "body": (form.get("body") or "").strip(),
    }
    if labels:
        arguments["labels"] = labels
    if sources:
        arguments["sources"] = sources
    requested_by = (form.get("requested_by") or "").strip()
    if requested_by:
        arguments["requested_by"] = requested_by
    return arguments


def _pretty(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str)
