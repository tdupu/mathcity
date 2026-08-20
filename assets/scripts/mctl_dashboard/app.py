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
    GET  /diagnostics      grouped by severity and code
    GET  /work             brief-backed work readiness
    GET  /validate         canonical-versus-cache consistency
    GET  /trace            one trace, plus a replay preview that replays nothing
    POST /preview          dry-run an operation. Writes nothing.
    POST /apply            confirm a preview that is still true.

There is no route that takes a command, and `MUTATION_ROUTES` is the whole
set of paths that can write anything.

**Two scopes, one route table.** Started with `--rig`, the dashboard serves
that rig and behaves exactly as it always has. Started without one it serves
the whole city: queue counts become city-wide with a per-rig breakdown, and
the brief list spans rigs. The aggregation itself is not here -- it is
`mctl_core/city.py`, behind the plan's declared `all_rigs` option, and this
module is one of its consumers alongside the CLI. A dashboard that assembled
its own city-wide answer would be a second implementation of the semantics,
drifting from the one the CLI reports.

**Reads aggregate; writes never do.** A brief lives in exactly one rig's bead
store, so `rig` travels with every link, every form, and every preview, and a
mutation's tool arguments always name it. `?rig=` on a city-wide list is a
filter over what was read; on a brief page and on `/preview` it is the store
being addressed. The apply path refuses when the rig it is handed is not the
rig the preview was taken against.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qs, unquote

from . import render
from . import state as view_state
from .screens import brief as brief_screen
from .screens import panel as panel_screen
from .screens import pipeline as pipeline_screen
from .screens import priority as priority_screen
from .screens import stack
from .aggregate import CityView
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
    #: The `briefs_options` id whose `disabled_reason` answers "can this bead
    #: be operated on at all" -- an answer that does not depend on how the
    #: form was filled in.
    option_id: str = ""


OPERATIONS: dict[str, Operation] = {
    "adjudicate": Operation(
        "adjudicate", "briefs_adjudicate", "adjudication", option_id="adjudicate"
    ),
    "defer": Operation("defer", "briefs_defer", "deferral", option_id="defer"),
    "dispatch": Operation("dispatch", "work_dispatch", "work dispatch", option_id="dispatch-work"),
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


#: Which decision states belong to which lane of the pipeline.
#:
#: The stack is what is *ready for a verdict*, which is what the header chip
#: counts. Showing every brief regardless of state under a chip that counts
#: pending ones would make the chip disagree with its own destination -- the
#: exact failure the design's counts rule exists to prevent.
SCOPE_STATES: dict[str, frozenset[str]] = {
    "stack": frozenset({"pending"}),
}


def _scoped(
    briefs: Sequence[Mapping[str, Any]], scope: str
) -> list[Mapping[str, Any]]:
    """The briefs belonging to one lane.

    `errors` and `nobrainer` have no source yet: error briefs are not filed at
    all (CHANGELOG §G1) and the no-brainer classifier writes no bead state, so
    both scopes are genuinely empty rather than unimplemented. Returning an
    empty list makes the screen say so.
    """
    if scope in ("errors", "nobrainer"):
        return []
    states = SCOPE_STATES.get(scope)
    if states is None:
        return list(briefs)
    return [b for b in briefs if str(b.get("decision_state") or "") in states]


def _queued_from(request: "Request") -> list[str]:
    """The operator's ordering, as carried in the URL."""
    raw = request.query.get("order") or ""
    return [part.strip() for part in raw.split(",") if part.strip()]


class Dashboard:
    """The operator surface. A client of the typed MCP tools, nothing more."""

    #: Every path that can write. Asserted by the tests so a future route
    #: cannot quietly become a third mutation path.
    MUTATION_ROUTES = ("/preview", "/apply")

    def __init__(self, client: McpClient, *, city_wide: bool = False, rig: str | None = None):
        self.client = client
        # City-wide is opt-in and comes from how the server was started, not
        # from what a request asks for: a query parameter that could widen the
        # scope would make "which stores did that page read" a property of the
        # URL rather than of the deployment.
        self.city_wide = bool(city_wide)
        self.rig = rig
        self.previews = PreviewStore()

    # -- scope --

    def _rig_for(self, request: Request) -> str | None:
        """Which rig this request addresses.

        In rig scope it is always the pinned rig, whatever the URL says: a
        `?rig=` on a single-rig dashboard must not silently retarget it.
        """
        if not self.city_wide:
            return self.rig
        return (request.query.get("rig") or request.form.get("rig") or "").strip() or None

    def _args(self, rig: str | None = None, **extra: Any) -> dict[str, Any]:
        """Tool arguments, with the rig named whenever there is one to name."""
        arguments = {key: value for key, value in extra.items() if value not in (None, "")}
        if rig:
            arguments["rig"] = rig
        return arguments

    # -- MCP helpers --

    def _context(self, rig: str | None = None) -> Mapping[str, Any]:
        return self.client.call("context_resolve", self._args(rig)).payload

    def _city(self) -> Mapping[str, Any]:
        return self.client.call("context_rigs").payload

    def _rig_ids(self) -> tuple[str, ...]:
        try:
            return tuple(
                str(entry.get("rig_id")) for entry in self._city().get("rigs") or () if entry
            )
        except ToolFailure:  # pragma: no cover - defensive
            return ()

    def _context_bar(self, context: Mapping[str, Any], *, compact: bool = True) -> str:
        return render.context_panel(context, compact=compact)

    def _city_bar(self, degraded: Sequence[str] = ()) -> str:
        try:
            return render.city_context_panel(self._city(), degraded=degraded)
        except ToolFailure as failure:  # pragma: no cover - defensive
            return render.notice_panel(
                "The city registry could not be read",
                "Nothing below can be scoped to a rig until it can.",
                failure.diagnostics,
                region="context",
            )

    def _page(
        self,
        title: str,
        current: str,
        context: Mapping[str, Any] | None,
        sections: Sequence[str],
        *,
        status: int = 200,
        compact_context: bool = True,
        context_bar: str | None = None,
        counts: Mapping[str, int] | None = None,
        queued: Sequence[str] = (),
        weights: Mapping[str, int] | None = None,
    ) -> Response:
        if context_bar is None:
            context_bar = (
                self._context_bar(context, compact=compact_context) if context is not None else ""
            )
        return Response(
            status,
            render.page(
                title,
                current,
                sections,
                context_bar=context_bar,
                counts=counts or {},
                context=context or {},
                queued=queued,
                weights=weights,
            ),
        )

    @staticmethod
    def _counts(briefs: Sequence[Mapping[str, Any]]) -> dict[str, int]:
        """Header and sidebar counts, derived from a listing already read.

        Deliberately a pure function over briefs the caller already has rather
        than a fetch of its own: a city-wide page costs exactly one cross-rig
        read, and `test_dashboard_city_wide.py` asserts that. Counting by
        issuing a second `briefs_list` would double the most expensive call on
        the page to render five numbers.

        Counts with no source yet -- the pile and the no-brainer lane are not
        readable through the typed surface (issue #66) -- are omitted rather
        than zeroed, and the chip renders without a number. A zero would be
        read as "nothing there", which is a claim nobody can currently make.
        """
        states: dict[str, int] = {}
        for brief in briefs:
            state = str(brief.get("decision_state") or "unknown")
            states[state] = states.get(state, 0) + 1
        return {
            "stack": states.get("pending", 0),
            "deferred": states.get("deferred", 0),
            "adjudicated": states.get("adjudicated", 0),
            "malformed": states.get("malformed", 0),
        }

    def _knowls(self, brief: Mapping[str, Any]) -> dict[str, Any]:
        """Reference data the knowls in a brief's prose can resolve against.

        Only what is genuinely available: the brief's own policy references,
        and the diagnostic registry. A full rule-id index with file, line and
        rule text is issue #66 item 3 and does not exist yet, so a rule cited
        in prose but absent from this brief's own references stays plain text
        rather than opening an empty panel.
        """
        rules: dict[str, Any] = {}
        for reference in brief.get("policy_references") or ():
            raw = str(reference.get("reference") or "")
            token = raw.split()[-1] if raw else ""
            if token:
                rules[token] = {
                    "name": reference.get("description") or token,
                    "text": reference.get("description") or "",
                    "file": raw,
                }
        return {"rules": rules}

    def _lane(self, lane: str, request: Request) -> Response:
        """Pile, Deferred, Adjudicated and Malformed.

        One handler because they share a shape: read the listing once, filter
        by decision state, and let the screen say which kind of absence it is
        looking at. The pile is the exception -- it has no source at all, so it
        never touches the listing.
        """
        rig = self._rig_for(request) or self.rig
        context = self._context(rig) if not self.city_wide else None

        if lane == "pile":
            # Nothing to read: no tool reports pile membership.
            return self._page(
                "Pile", "/pile", context, [pipeline_screen.pile()], context_bar=""
            )

        briefs, _city, city_extra = self._read_briefs(rig)
        selected = [
            brief
            for brief in briefs
            if str(brief.get("decision_state") or "") == lane.rstrip("s")
            or str(brief.get("decision_state") or "") == lane
        ]
        renderer = {
            "deferred": pipeline_screen.deferred,
            "adjudicated": pipeline_screen.adjudicated,
            "malformed": pipeline_screen.malformed,
        }[lane]
        return self._page(
            lane.capitalize(),
            f"/{lane}",
            context,
            [renderer(selected), *city_extra],
            counts=self._counts(briefs),
            context_bar="",
        )

    def _priority(self, request: Request) -> Response:
        """The operator's own ordering over the stack.

        The order arrives in the query string rather than from a store: it is
        one clerk's working hypothesis about importance, and persisting it
        server-side would present an experiment as a property of the briefs.
        That also makes move-up and move-down ordinary links, so the list
        reorders with scripting disabled.
        """
        rig = self._rig_for(request) or self.rig
        context = self._context(rig) if not self.city_wide else None
        briefs, _city, city_extra = self._read_briefs(rig)
        by_id = {str(b.get("bead_id")): b for b in briefs}

        # `order` is the saved ordering; `pick` arrives from the stack's
        # bulk-add form. Ticked rows append to the end of the existing order
        # rather than replacing it, so adding never silently discards an
        # ordering the operator built.
        wanted = [
            part
            for part in (request.query.get("order") or "").split(",")
            if part and part in by_id
        ]
        for picked in request.query.get("pick", "").split(","):
            picked = picked.strip()
            if picked and picked in by_id and picked not in wanted:
                wanted.append(picked)
        ordered = [by_id[bead] for bead in wanted]
        return self._page(
            "Priority list",
            "/priority",
            context,
            [priority_screen.screen(ordered), *city_extra],
            counts=self._counts(briefs),
            queued=[str(b.get("bead_id")) for b in ordered],
            context_bar="",
        )

    def _read_briefs(self, rig: str | None) -> tuple[list[Mapping[str, Any]], Any, list[str]]:
        """Read briefs in whichever scope this dashboard is serving.

        Returns (briefs, city_view_or_None, extra_sections).

        City-wide reads need `all_rigs`; a rig-scoped read must not pass it.
        The redesigned screens were written and tested rig-scoped only, so in
        city scope `rig` was None, `briefs_list` was called with neither a rig
        nor `all_rigs`, and every one of them raised.

        The second return value carries the degraded-rig accounting. A rig that
        cannot be read contributes no rows, so a city-wide total is silently
        short while looking complete -- honesty property 4 exists for exactly
        that, and the caller must render the panel rather than quietly
        reporting a smaller number.
        """
        if not self.city_wide:
            listing = self.client.call("briefs_list", self._args(rig))
            return list(listing.payload.get("briefs") or ()), None, []

        view = CityView.from_payload(
            self.client.call("briefs_list", self._args(None, all_rigs=True)).payload
        )
        extra = [
            render.degraded_rigs_panel(view.degraded, len(view.rigs)),
            render.rig_trust_panels(view),
        ]
        return list(view.rows_for(rig)), view, extra

    # -- read views --

    def _queue(self, request: Request) -> Response:
        """The brief stack in the adopted design.

        Reads the same `briefs_list` the older `/briefs` view does; the view
        state -- sort, columns, scope -- comes off the query string so the
        whole screen works with scripting disabled.
        """
        view = view_state.parse(request.query)
        rig = self._rig_for(request) or self.rig
        context = self._context(rig) if not self.city_wide else None
        all_briefs, _city, city_extra = self._read_briefs(rig)
        briefs = _scoped(all_briefs, view.scope)

        titles = {
            "stack": "Brief stack",
            "errors": "Invariant errors",
            "nobrainer": "No-brainers",
        }
        heading = titles.get(view.scope, "Brief stack")
        scope_label = "all rigs" if self.city_wide else f"rig {rig}"
        columns_open = request.query.get("columns_open") == "1"
        base = view.url()
        columns_href = base if columns_open else (
            base + ("&" if "?" in base else "?") + "columns_open=1"
        )

        # The controls sit on the title row, as the design has them: scope,
        # the column picker toggle, and a jump to the top brief. All three are
        # links or forms -- nothing here needs script.
        controls = (
            '<div style="margin-left: auto; display: flex; gap: 10px; '
            'align-items: center;">'
            # The picker is a query flag, so opening it is a link and its
            # state survives a reload -- no toggle handler, no hidden div.
            f'<a class="btn btn-ghost" href="{render.esc(columns_href)}">Columns</a>'
            # Only in city scope: a rig picker on a dashboard pinned to one rig
            # would imply a choice the deployment already made.
            + (render.rig_picker(self._rig_ids(), selected=(rig,) if rig else ()) if self.city_wide else "")
            + (
                f'<a class="btn btn-secondary" href="{render.esc(view.url(view="brief", brief_id=str(briefs[0].get("brief_id"))))}">'
                "Open top brief &rarr;</a>"
                if briefs
                else ""
            )
            + "</div>"
        )

        sections = [
            '<div style="display: flex; align-items: baseline; gap: 12px;">'
            f'<h1 style="font-family: var(--font-heading); font-size: 27px; '
            f'font-weight: 600; margin: 0;">{render.esc(heading)}</h1>'
            f'<span class="mono" style="font-size: 11.5px; color: var(--color-neutral-600);">'
            f"{render.esc(scope_label)} &middot; {len(briefs)} briefs &middot; sorted by "
            f"{render.esc(view_state.COLUMN_LABEL.get(view.sort_key, view.sort_key))}"
            f"{' descending' if view.sort_dir < 0 else ' ascending'}</span>"
            + controls
            + "</div>"
            '<div style="height: 2px; background: var(--color-neutral-900); '
            'margin: 8px 0 0;"></div>',
            stack.column_picker(view) if columns_open else "",
            stack.table(briefs, view, queued=()),
            stack.empty_sort_note(briefs, view),
            stack.key_legend(),
            stack.unfed_note(),
            *city_extra,
        ]
        # Counts come from the whole listing, not the scoped slice: the
        # sidebar has to report every lane, not just the one being viewed.
        return self._page(
            heading,
            "/queue",
            context,
            sections,
            counts=self._counts(all_briefs),
            queued=_queued_from(request),
            weights=view.weights,
            # The masthead already states the resolved city, rig and store.
            # A second Context panel here pushed the table below the fold.
            context_bar="",
        )

    def _overview(self, request: Request) -> Response:
        if self.city_wide:
            return self._city_overview()
        context = self._context(self.rig)
        listing = self.client.call("briefs_list", self._args(self.rig))
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

    def _city_overview(self) -> Response:
        view = CityView.from_payload(
            self.client.call("briefs_list", {"all_rigs": True}).payload
        )
        sections = [
            render.city_queue_panel(view),
            render.degraded_rigs_panel(view.degraded, len(view.rigs)),
            render.rig_trust_panels(view),
            render.city_diagnostics_sections(view, heading="City queue diagnostics"),
        ]
        return self._page(
            "Overview",
            "/",
            None,
            sections,
            context_bar=self._city_bar([rig.rig_id for rig in view.degraded]),
        )

    def _briefs(self, request: Request) -> Response:
        status = request.query.get("status")
        label = request.query.get("label")
        if self.city_wide:
            return self._city_briefs(request, status, label)
        context = self._context(self.rig)
        listing = self.client.call(
            "briefs_list", self._args(self.rig, status=status, label=label)
        )
        briefs = list(listing.payload.get("briefs") or ())
        sections = [
            self._filter_panel(request, rig_ids=()),
            '<section class="panel" data-region="brief-list">'
            f"<h2>Briefs ({len(briefs)})</h2>"
            '<p class="lede">Canonical source <span class="mono">bead_store</span>, '
            'read through <span class="mono">briefs_list</span>.</p>'
            + render.brief_rows(briefs)
            + "</section>",
            render.artifact_trust_panel(listing.artifact_trust, rig=self.rig),
        ]
        return self._page("Briefs", "/briefs", context, sections)

    def _city_briefs(self, request: Request, status: str | None, label: str | None) -> Response:
        selected = self._rig_for(request)
        view = CityView.from_payload(
            self.client.call(
                "briefs_list", self._args(None, status=status, label=label, all_rigs=True)
            ).payload
        )
        rows = view.rows_for(selected)
        scope = f"rig {selected}" if selected else f"{len(view.healthy)} readable rigs"
        sections = [
            self._filter_panel(request, rig_ids=view.rig_ids()),
            '<section class="panel" data-region="brief-list" data-scope="city" '
            f'data-row-count="{len(rows)}">'
            f"<h2>Briefs ({len(rows)} across {render.esc(scope)})</h2>"
            '<p class="lede">Canonical source: each rig\'s own <span class="mono">bead_store</span>, '
            'read through <span class="mono">briefs_list</span> with '
            '<span class="mono">all_rigs</span>. The rig column is the store a brief belongs to, '
            "and it travels with the link.</p>"
            + render.brief_rows(rows, show_rig=True)
            + "</section>",
            render.degraded_rigs_panel(view.degraded, len(view.rigs)),
            render.rig_trust_panels(view),
        ]
        return self._page(
            "Briefs",
            "/briefs",
            None,
            sections,
            context_bar=self._city_bar([rig.rig_id for rig in view.degraded]),
        )

    def _filter_panel(self, request: Request, *, rig_ids: Sequence[str]) -> str:
        rig_field = (
            render.rig_filter_field(rig_ids, self._rig_for(request)) if self.city_wide else ""
        )
        return (
            '<section class="panel" data-region="filters"><h2>Filter</h2>'
            '<form class="operation" method="get" action="/briefs">'
            + rig_field
            + f'<label>Bead or decision status<input type="text" name="status" value="{render.esc(request.query.get("status") or "")}"></label>'
            f'<label>Label<input type="text" name="label" value="{render.esc(request.query.get("label") or "")}"></label>'
            '<div><button type="submit" class="secondary">Apply filter</button></div>'
            "</form></section>"
        )

    def _brief(self, brief_id: str, request: Request) -> Response:
        rig = self._rig_for(request)
        if self.city_wide and not rig:
            return self._rig_required(brief_id)
        try:
            shown = self.client.call("briefs_show", self._args(rig, brief_id=brief_id))
        except ToolFailure as failure:
            # "No such brief" would be the wrong headline when the *rig* is
            # the thing that does not exist -- the operator would go looking
            # for a missing bead instead of a mistyped rig. The code is shown
            # either way; the headline has to match it.
            codes = {str(item.get("code")) for item in failure.diagnostics}
            unknown_rig = "MCTL_CONTEXT_UNKNOWN_RIG" in codes
            return self._page(
                "No such rig" if unknown_rig else "Brief not found",
                "/briefs",
                None if unknown_rig else self._safe_context(rig),
                [
                    render.notice_panel(
                        f"Rig {rig!r} is not registered in this city"
                        if unknown_rig
                        else "No such brief",
                        f"Nothing was read. {brief_id!r} may well exist, but not in a rig by "
                        "that name; the registered rigs are listed in the context above."
                        if unknown_rig
                        else (
                            f"The canonical bead store for rig {rig!r} has no brief named "
                            f"{brief_id!r}."
                            if rig
                            else f"The canonical bead store has no brief named {brief_id!r}."
                        ),
                        failure.diagnostics,
                        region="rig-missing" if unknown_rig else "brief-missing",
                    )
                ],
                status=404,
                context_bar=self._city_bar() if unknown_rig and self.city_wide else None,
            )
        brief = dict(shown.payload.get("brief") or {})
        options = self._options(brief_id, rig)
        doctor = self._doctor(brief_id, rig)
        option_rows = (options.payload.get("options") or ()) if options else ()
        # The redesigned detail leads: it is what the operator reads to decide.
        # The existing panels stay beneath it -- `brief_detail_panel` carries
        # canonical fields the new screen deliberately does not duplicate, and
        # the option forms are still the only mutation path until Slice 3.
        sections = [
            brief_screen.detail(brief, view_state.parse(request.query), knowls=self._knowls(brief)),
            panel_screen.entry(brief, option_rows, view_state.parse(request.query), rig=rig),
            render.artifact_trust_panel(shown.artifact_trust, rig=rig),
            render.brief_detail_panel(brief),
            render.options_panel(option_rows) if options else "",
            render.operation_forms(brief_id, option_rows, rig=rig),
            render.diagnostics_sections(
                doctor.diagnostics if doctor else [],
                doctor.untrusted_diagnostics if doctor else [],
                None,
                heading="Brief diagnostics",
            ),
        ]
        return self._page(
            str(brief.get("title") or brief_id), "/briefs", self._context(rig), sections
        )

    def _rig_required(self, brief_id: str) -> Response:
        """A brief id with no rig is an address with no store behind it.

        The city-wide list always supplies the rig, so this is reached by a
        hand-edited or stale URL. Guessing which of several stores was meant
        is exactly the class of mistake that ends with a verdict recorded on
        the wrong bead, so the page names the rigs and makes the operator pick.
        """
        rigs = self._rig_ids()
        links = "".join(
            f'<li><a href="{render.brief_href(brief_id, rig)}">'
            f'<span class="mono">{render.esc(rig)}</span></a></li>'
            for rig in rigs
        )
        return self._page(
            "Which rig?",
            "/briefs",
            None,
            [
                render.notice_panel(
                    "This brief needs a rig",
                    "Storage is per rig, so a brief id alone does not say which bead store "
                    "owns it. Nothing was read and nothing was written. Pick the rig below.",
                    [
                        _dashboard_diagnostic(
                            "ERROR",
                            "MCTL_DASH_RIG_REQUIRED",
                            f"No rig was supplied for brief {brief_id!r} on a city-wide dashboard.",
                            "Open the brief from the city-wide list, which carries its rig, or "
                            "add ?rig=<rig-id> to this URL.",
                            requested_brief_id=brief_id,
                            registered_rigs=", ".join(rigs),
                        )
                    ],
                    region="rig-required",
                )
                + (f'<section class="panel"><h2>Registered rigs</h2><ul>{links}</ul></section>' if links else ""),
            ],
            status=400,
            context_bar=self._city_bar(),
        )

    def _safe_context(self, rig: str | None) -> Mapping[str, Any] | None:
        try:
            return self._context(rig)
        except ToolFailure:
            return None

    def _options(self, brief_id: str, rig: str | None) -> ToolResponse | None:
        try:
            return self.client.call("briefs_options", self._args(rig, brief_id=brief_id))
        except ToolFailure:
            return None

    def _doctor(self, brief_id: str, rig: str | None) -> ToolResponse | None:
        try:
            return self.client.call("briefs_doctor", self._args(rig, brief_id=brief_id))
        except ToolFailure:
            return None

    def _severity_summary(self, counts: Mapping[str, Any], *, scope: str) -> str:
        return (
            '<section class="panel" data-region="severity-summary"><h2>By severity</h2>'
            f'<p class="lede">{render.esc(scope)}, from <span class="mono">briefs_validate</span> '
            "- the strict superset of the doctor invariants. Severity is styled; the code is "
            "always shown.</p>"
            '<div class="scroll-x"><table><thead><tr><th>Severity</th><th>Count</th></tr></thead><tbody>'
            + "".join(
                f'<tr><td><span class="severity severity-{severity}">{severity}</span></td>'
                f'<td class="mono">{int(counts.get(severity, 0))}</td></tr>'
                for severity in render.SEVERITY_ORDER
            )
            + "</tbody></table></div></section>"
        )

    def _diagnostics(self, request: Request) -> Response:
        if self.city_wide:
            view = CityView.from_payload(
                self.client.call("briefs_validate", {"all": True, "all_rigs": True}).payload
            )
            sections = [
                self._severity_summary(view.severity_counts, scope="Every registered rig"),
                render.degraded_rigs_panel(view.degraded, len(view.rigs)),
                render.rig_trust_panels(view),
                render.city_diagnostics_sections(view, heading="City diagnostics"),
            ]
            return self._page(
                "Diagnostics",
                "/diagnostics",
                None,
                sections,
                context_bar=self._city_bar([rig.rig_id for rig in view.degraded]),
            )
        context = self._context(self.rig)
        report = self.client.call("briefs_validate", self._args(self.rig, all=True))
        sections = [
            self._severity_summary(report.payload.get("severity_counts") or {}, scope="Rig-wide"),
            render.diagnostics_sections(
                report.diagnostics,
                report.untrusted_diagnostics,
                report.artifact_trust,
                heading="Rig diagnostics",
            ),
        ]
        return self._page("Diagnostics", "/diagnostics", context, sections)

    def _validate(self, request: Request) -> Response:
        if self.city_wide:
            view = CityView.from_payload(
                self.client.call("briefs_validate", {"all": True, "all_rigs": True}).payload
            )
            verdict = "consistent" if view.valid else "inconsistent"
            sections = [
                '<section class="panel" data-region="validation" data-scope="city">'
                f"<h2>Canonical versus cache, whole city: {render.esc(verdict)}</h2>"
                '<p class="lede">Every registered rig, read through '
                '<span class="mono">briefs_validate</span> with <span class="mono">all_rigs</span>. '
                "This view reads only; it never repairs, and no view in this dashboard does. A rig "
                "that could not be read makes the city verdict inconsistent by construction.</p>"
                + render.brief_rows(list(view.rows), show_rig=True)
                + "</section>",
                render.degraded_rigs_panel(view.degraded, len(view.rigs)),
                render.rig_trust_panels(view),
            ]
            return self._page(
                "Validate",
                "/validate",
                None,
                sections,
                context_bar=self._city_bar([rig.rig_id for rig in view.degraded]),
            )
        context = self._context(self.rig)
        report = self.client.call("briefs_validate", self._args(self.rig, all=True))
        verdict = "consistent" if report.payload.get("valid") else "inconsistent"
        sections = [
            '<section class="panel" data-region="validation">'
            f"<h2>Canonical versus cache: {render.esc(verdict)}</h2>"
            '<p class="lede">Scope <span class="mono">'
            f'{render.esc(report.payload.get("scope"))}</span>. This view reads only; it never '
            "repairs, and no view in this dashboard does.</p>"
            + render.brief_rows(list(report.payload.get("briefs") or ()))
            + "</section>",
            render.artifact_trust_panel(report.artifact_trust, rig=self.rig),
        ]
        return self._page("Validate", "/validate", context, sections)

    def _work(self, request: Request) -> Response:
        if self.city_wide:
            payload = self.client.call("work_ready", {"all_rigs": True}).payload
            view = CityView.from_payload(payload, rows="work")
            items = list(view.rows)
            sections = [
                self._work_panel(items, show_rig=True, scope="every readable rig"),
                render.degraded_rigs_panel(view.degraded, len(view.rigs)),
                render.diagnostics_sections(
                    list(view.diagnostics) + _blockers(items), [], None, heading="Work diagnostics"
                ),
            ]
            return self._page(
                "Work",
                "/work",
                None,
                sections,
                context_bar=self._city_bar([rig.rig_id for rig in view.degraded]),
            )
        context = self._context(self.rig)
        ready = self.client.call("work_ready", self._args(self.rig))
        items = list(ready.payload.get("work") or ())
        sections = [
            self._work_panel(items, show_rig=False, scope="this rig"),
            render.diagnostics_sections(
                list(ready.diagnostics) + _blockers(items), [], None, heading="Work diagnostics"
            ),
        ]
        return self._page("Work", "/work", context, sections)

    def _work_panel(
        self, items: Sequence[Mapping[str, Any]], *, show_rig: bool, scope: str
    ) -> str:
        rows = "".join(
            "<tr>"
            + (
                f'<td><span class="mono">{render.esc(item.get("rig_id") or "-")}</span></td>'
                if show_rig
                else ""
            )
            + f'<td><a href="{render.brief_href(item.get("brief_id"), item.get("rig_id") if show_rig else None)}">'
            f'<span class="mono">{render.esc(item.get("brief_id"))}</span></a></td>'
            f'<td><span class="mono">{render.esc(item.get("bead_id"))}</span></td>'
            f'<td>{render.esc(item.get("title"))}</td>'
            f'<td><span class="badge">{render.esc(item.get("readiness"))}</span></td>'
            f'<td class="mono">{len(item.get("blockers") or ())}</td>'
            "</tr>"
            for item in items
        )
        return (
            '<section class="panel" data-region="work">'
            f"<h2>Ready work ({len(items)})</h2>"
            '<p class="lede">Brief-backed work whose canonical state permits dispatch, from '
            f'<span class="mono">work_ready</span> across {render.esc(scope)}. Dispatch itself is '
            "preview-first, from the brief page, and stays scoped to the owning rig.</p>"
            + (
                '<div class="scroll-x"><table><thead><tr>'
                + ("<th>Rig</th>" if show_rig else "")
                + "<th>Brief</th><th>Work bead</th>"
                "<th>Title</th><th>Readiness</th><th>Blockers</th></tr></thead>"
                f"<tbody>{rows}</tbody></table></div>"
                if rows
                else '<p class="lede">No brief-backed work is ready.</p>'
            )
            + "</section>"
        )

    def _trace(self, request: Request) -> Response:
        rig = self._rig_for(request)
        trace_id = request.query.get("trace_id", "").strip()
        rig_field = (
            render.rig_filter_field(self._rig_ids(), rig) if self.city_wide else ""
        )
        search = (
            '<section class="panel" data-region="trace-search"><h2>Find a trace</h2>'
            '<p class="lede">Traces are recorded per rig, so a trace id is read against one '
            "rig's log.</p>"
            '<form class="operation" method="get" action="/trace">'
            + rig_field
            + f'<label>Trace id<input type="text" name="trace_id" value="{render.esc(trace_id)}"></label>'
            '<div><button type="submit" class="secondary">Show trace</button></div>'
            "</form></section>"
        )
        context_bar = self._city_bar() if self.city_wide and not rig else None
        context = None if (self.city_wide and not rig) else self._safe_context(rig)
        if not trace_id or (self.city_wide and not rig):
            sections = [search]
            if trace_id and self.city_wide and not rig:
                sections.append(
                    render.notice_panel(
                        "Pick a rig",
                        "Nothing was read. Trace logs live under each rig root, so a trace id "
                        "has to be resolved against one rig.",
                        [
                            _dashboard_diagnostic(
                                "ERROR",
                                "MCTL_DASH_RIG_REQUIRED",
                                f"No rig was supplied for trace {trace_id!r}.",
                                "Choose a rig above and search again.",
                                requested_trace_id=trace_id,
                            )
                        ],
                        region="rig-required",
                    )
                )
            return self._page("Traces", "/", context, sections, context_bar=context_bar)
        try:
            shown = self.client.call("trace_show", self._args(rig, trace_id=trace_id))
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
                context_bar=context_bar,
            )
        record = dict(shown.payload.get("trace") or {})
        replay = self.client.call("trace_replay_preview", self._args(rig, trace_id=trace_id))
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
        return self._page("Traces", "/", context, sections, context_bar=context_bar)

    # -- dispatch --

    def handle(self, request: Request) -> Response:
        if request.method == "POST":
            if request.path == "/preview":
                return self._preview(request)
            if request.path == "/apply":
                return self._apply(request)
            return self._not_found(request)
        if request.path == "/":
            return self._overview(request)
        if request.path == "/queue":
            return self._queue(request)
        if request.path in ("/pile", "/deferred", "/adjudicated", "/malformed"):
            return self._lane(request.path[1:], request)
        if request.path == "/priority":
            return self._priority(request)
        if request.path == "/briefs":
            return self._briefs(request)
        if request.path.startswith("/briefs/"):
            return self._brief(request.path[len("/briefs/") :], request)
        if request.path == "/diagnostics":
            return self._diagnostics(request)
        if request.path == "/work":
            return self._work(request)
        if request.path == "/validate":
            return self._validate(request)
        if request.path == "/trace":
            return self._trace(request)
        return self._not_found(request)

    def _not_found(self, request: Request) -> Response:
        return self._page(
            "Not found",
            "/",
            self._safe_context(self._rig_for(request)),
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
                rig=self._rig_for(request),
            )
        rig = self._rig_for(request)
        if self.city_wide and not rig:
            # A mutation whose target store is ambiguous is refused, never
            # guessed. Aggregation is a read-side convenience; a write always
            # names one bead store.
            return self._mutation_notice(
                "No target rig",
                400,
                [
                    _dashboard_diagnostic(
                        "ERROR",
                        "MCTL_DASH_RIG_REQUIRED",
                        f"{operation.name} needs the rig whose bead store owns the brief.",
                        "Start from a brief page opened out of the city-wide list; it carries "
                        "the rig into the form.",
                        requested_operation=operation.name,
                    )
                ],
                rig=None,
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
                rig=rig,
            )
        arguments = _arguments_for(operation, brief_id, request.form, rig)
        return self._render_preview(
            operation, brief_id, rig, arguments, heading="Dry-run preview"
        )

    def _blocking_option(
        self, brief_id: str | None, rig: str | None, operation: Operation
    ) -> list[Mapping[str, Any]]:
        """The state-level reason this operation is impossible, if there is one.

        A refused preview reports whatever refused first, and a missing form
        field refuses before the bead's state is ever consulted. That buries
        the real answer: a brief blocked by `MBRF004`/`MBRF011` cannot be
        adjudicated however the form is filled in, and telling an operator to
        supply a reason implies that supplying one would work. So the option's
        own `disabled_reason` is surfaced alongside -- and ahead of -- the
        field-validation diagnostic, which also makes the form's promise that
        "a preview will show the blocking diagnostic code" true.
        """
        if not brief_id or not operation.option_id:
            return []
        options = self._options(brief_id, rig)
        if options is None:
            return []
        for option in options.payload.get("options") or ():
            if str(option.get("id")) != operation.option_id or option.get("enabled"):
                continue
            reason = option.get("disabled_reason")
            if isinstance(reason, Mapping):
                return [dict(reason)]
        return []

    def _render_preview(
        self,
        operation: Operation,
        brief_id: str | None,
        rig: str | None,
        arguments: Mapping[str, Any],
        *,
        heading: str,
        prefix: Sequence[str] = (),
        status: int = 200,
    ) -> Response:
        context = self._context(rig)
        try:
            planned = self.client.call(operation.tool, {**arguments, "dry_run": True})
        except ToolFailure as failure:
            # The refusal names its blocking code in `facts`, but the operator
            # needs the whole set: the state-level block comes first, then the
            # refusal itself, then the brief's own diagnostics -- each with its
            # code, so "blocked" is a diagnosis rather than a wall.
            blocking = self._blocking_option(brief_id, rig, operation)
            doctor = self._doctor(brief_id, rig) if brief_id else None
            return self._page(
                "Blocked",
                "/briefs",
                context,
                [
                    *prefix,
                    # Two panels, in this order, rather than one merged list:
                    # the diagnostic list sorts by severity and code, so a
                    # merged list would order the operator's real answer by
                    # alphabetical accident.
                    render.notice_panel(
                        f"This brief's state does not permit {operation.title}",
                        "Nothing was written. No way of filling in the form would change this "
                        "answer -- the bead's own state blocks the operation. The refusal that "
                        "came back from the typed tool is below.",
                        blocking,
                        region="state-blocked",
                    )
                    if blocking
                    else "",
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
        target = self._target(brief_id, rig)
        preview = self.previews.create(
            operation=operation.name,
            tool=operation.tool,
            arguments=arguments,
            brief_id=brief_id,
            rig=rig,
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
            render.confirm_panel(preview.token, operation.title, brief_id, rig=rig),
            render.artifact_trust_panel(planned.artifact_trust, rig=rig),
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
                rig=self._rig_for(request),
            )
        operation = OPERATIONS[preview.operation]
        # The rig the *confirm* arrived with, which is not necessarily the one
        # the preview was taken against. Everything below is recomputed from
        # this one so a rig switch shows up as a change; the mutation itself
        # still runs against `preview.arguments`, which pin the rig recorded at
        # preview time, so an unnoticed switch could never retarget the write.
        requested_rig = self._rig_for(request)
        context = self._context(requested_rig)
        target = self._target(preview.brief_id, requested_rig)
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
            rig=requested_rig,
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
                render.artifact_trust_panel(applied.artifact_trust, rig=preview.rig),
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
        must read and confirm on its own terms. The replacement is taken
        against the preview's own rig -- the store the operator was actually
        looking at -- never against whichever rig the stale confirm named.
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
                    target_rig=str(preview.rig or ""),
                )
            ],
            region="stale-preview",
        )
        return self._render_preview(
            operation,
            preview.brief_id,
            preview.rig,
            preview.arguments,
            heading="Fresh dry-run preview",
            prefix=[notice],
            status=409,
        )

    def _target(self, brief_id: str | None, rig: str | None) -> Mapping[str, Any] | None:
        """The canonical bead record a preview was computed against."""
        if not brief_id:
            return None
        try:
            return dict(
                self.client.call("briefs_show", self._args(rig, brief_id=brief_id)).payload.get(
                    "brief"
                )
                or {}
            )
        except ToolFailure:
            # A target that can no longer be read is itself a change; the
            # fingerprint of None will not match the one recorded at preview.
            # This is also what a rig switch looks like when the brief id does
            # not exist in the newly named store.
            return None

    def _mutation_notice(
        self,
        title: str,
        status: int,
        diagnostics: Sequence[Mapping[str, Any]],
        *,
        rig: str | None = None,
    ) -> Response:
        return self._page(
            title,
            "/briefs",
            self._safe_context(rig),
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


def _blockers(items: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    blockers: list[Mapping[str, Any]] = []
    for item in items:
        blockers.extend(item.get("blockers") or ())
    return blockers


def _arguments_for(
    operation: Operation, brief_id: str | None, form: Mapping[str, str], rig: str | None = None
) -> dict[str, Any]:
    """Build typed tool arguments from form fields. No passthrough, ever.

    Every field is named here and mapped to a declared schema property, so a
    surprise form field cannot become a tool argument. `rig` is one of those
    declared properties (the runtime selectors every tool accepts), and it is
    recorded in the preview so the applied mutation targets the store the
    preview was taken against rather than whatever the page is showing now.
    """
    arguments: dict[str, Any] = {"rig": rig} if rig else {}
    if operation.name == "adjudicate":
        arguments["brief_id"] = brief_id
        for key in ("verdict", "reason", "option"):
            value = (form.get(key) or "").strip()
            if value:
                arguments[key] = value
        arguments.setdefault("reason", "")
        return arguments
    if operation.name == "defer":
        arguments["brief_id"] = brief_id
        arguments["reason"] = (form.get("reason") or "").strip()
        until = (form.get("until") or "").strip()
        days = (form.get("days") or "").strip()
        if until:
            arguments["until"] = until
        elif days.isdigit():
            arguments["days"] = int(days)
        return arguments
    if operation.name == "dispatch":
        arguments["brief_id"] = brief_id
        return arguments
    labels = [item.strip() for item in (form.get("labels") or "").split(",") if item.strip()]
    sources = [item.strip() for item in (form.get("sources") or "").split(",") if item.strip()]
    arguments["title"] = (form.get("title") or "").strip()
    arguments["body"] = (form.get("body") or "").strip()
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
