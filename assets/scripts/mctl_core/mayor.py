"""Mayor-facing reads over the mctl core.

The Mayor's job is queue health and unblocking, and both of its standing
questions -- *is the city actually up?* and *has any work left the system
without an accounted exit?* -- were answered by hand, with shell, for
forty-four sessions. That is where they went wrong.

Two failures motivate this module, and each is recorded on the tracker rather
than asserted here:

1. **The city-state question has no single honest instrument.** In QUIMBY 44,
   `gc status` timed out and rendered "stopped / 0 sessions" (`gs-0cy2`);
   `gc supervisor status` reported "running" for a supervisor whose city had
   unregistered itself hours earlier; and `gc rig status` printed a *partial*
   agent roster produced by a timed-out probe as though it were the roster
   (issue #100). Three instruments, three answers, no way to tell which had
   looked. This module refuses to collapse them: every probe reports its own
   outcome, and `state` is four-valued so that "I could not determine this"
   never renders as "down".

2. **Conservation has an exit the reclaim chain cannot see.** The lost-bead
   conservation spec (`subdomains/dev/docs/lost-bead-conservation-spec.md`,
   adjudicated 2026-08-05) states the invariant: *"work does not silently
   leave the system ... every exit must be an accounted exit."* Its two
   detection classes both trigger on **idleness**, and both enumerate beads
   that exist. A deleted bead is never scanned, never idle, and never a
   candidate -- so arming more of the chain cannot reach it (issue #123).
   `conservation_report` enumerates **pointers** instead: a member carrying
   `gc.root_bead_id` whose target resolves to nothing is an unaccounted exit,
   and it is visible precisely because the pointer survived the bead.

Both functions are **reads**. Neither mutates, neither dispatches, and neither
takes a raw command -- the no-passthrough property the MCP surface depends on
is a property of this layer too.

**Do not "repair" dangling pointers.** A root never marks itself as a root
(0 of 356 resolved roots carry `gc.root_bead_id`), so the dangling pointer is
the *only* surviving evidence that the workflow existed. Removing it converts
a countable loss into an invisible one.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import json
import shutil
import subprocess
from typing import TYPE_CHECKING, Mapping, Sequence

from .diagnostics import Diagnostic, Severity

if TYPE_CHECKING:  # pragma: no cover - import cycle guard
    from .context import MctlContext


#: Probe budget. Every subprocess here is a *diagnostic* run against a city
#: that may already be unhealthy, so a probe that blocks is itself a failure
#: mode -- the 45s claim fence and the timing-out `gc status` are the same
#: bug wearing different hats. A probe that exceeds this reports `unknown`.
#: Measured, not guessed: on this machine `gc rig list` took ~29s and
#: `gc supervisor status` exceeded 10s during bring-up. A budget tighter than
#: the tool's real latency turns every run into `unknown`, which is honest and
#: useless. Generous because these are orientation reads, not hot paths.
PROBE_TIMEOUT_SECONDS = 30.0

#: The rig roster gets its own, longer budget. `gc rig list` was measured at
#: ~29s against this city, so the 10s budget above reported `unknown` on every
#: run -- honest, and useless. It is given room because it is NOT load-bearing
#: for `state`: only the tmux and supervisor probes decide up/down/unknown, so
#: a slow roster degrades the report rather than the verdict.
#:
#: It must be a subprocess. `suspended_on_start` in city.toml is the *start*
#: disposition, not the live one -- this city has 6 of those against 5 rigs
#: actually suspended -- so the roster cannot be derived from config, and a
#: reader that tried would confidently mis-state which rigs are dark.
RIG_PROBE_TIMEOUT_SECONDS = 45.0

#: The tmux server the Gas City fleet runs under (`tmux -L gt`).
TMUX_SOCKET = "gt"

ROOT_BEAD_FIELD = "gc.root_bead_id"
ROOT_STORE_FIELD = "gc.root_store_ref"


# --------------------------------------------------------------------------
# probe results
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class ProbeResult:
    """One instrument's answer, carrying whether it actually looked.

    `ok is None` means the probe did not complete -- timed out, or the tool is
    not installed. That is deliberately distinct from `ok is False`. Rendering
    the two the same way is the defect this module exists to avoid: a check
    that could not have failed must not render as a check that passed, and its
    mirror, a check that could not run must not render as a check that found
    nothing.
    """

    name: str
    ok: bool | None
    detail: str
    value: int | None = None

    @property
    def looked(self) -> bool:
        return self.ok is not None

    def to_dict(self) -> dict[str, object]:
        return {"detail": self.detail, "name": self.name, "ok": self.ok, "value": self.value}


@dataclass(frozen=True)
class CityState:
    """Four-valued city state, assembled from probes that each report themselves.

    `state` is never inferred from a single instrument:

    * ``up``        -- the fleet can host agents and at least one is running
    * ``idle``      -- fleet host is present but nothing is running on it
    * ``down``      -- the fleet host is absent; no agent can exist
    * ``unknown``   -- at least one load-bearing probe did not complete

    ``unknown`` outranks the others. A partial answer presented as a whole one
    is how QUIMBY 44 nearly reported that a rig had no run-operator, when in
    fact the probe listing them had timed out.
    """

    state: str
    probes: Sequence[ProbeResult]
    suspended_rigs: Sequence[str]
    active_rigs: Sequence[str]
    pane_count: int | None
    diagnostics: Sequence[Diagnostic] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "active_rigs": list(self.active_rigs),
            "pane_count": self.pane_count,
            "probes": [probe.to_dict() for probe in self.probes],
            "state": self.state,
            "suspended_rigs": list(self.suspended_rigs),
        }


@dataclass(frozen=True)
class ConservationReport:
    """Referential-integrity view over workflow membership.

    Counts are exact over the store read, not sampled. `window_earliest` and
    `window_latest` bound the creation times of the orphaned members, which is
    what distinguishes a bounded event from an ongoing leak -- the question the
    idleness-based classes cannot even ask.
    """

    molecules: int
    roots_resolving: int
    roots_dangling: int
    orphaned_members: int
    dangling_root_ids: Sequence[str]
    window_earliest: str | None
    window_latest: str | None
    store_refs: Mapping[str, int]
    diagnostics: Sequence[Diagnostic] = field(default_factory=tuple)
    #: False when the store could not be read at all. A report built from a
    #: failed read has zero of everything, and zero dangling roots must NOT
    #: then read as "clean" -- see `clean`.
    readable: bool = True
    #: #150 G1: this report is ALWAYS one rig's store, never the city. Empty
    #: string, not omitted, when built by `conservation_from_rows` directly --
    #: a pure function with no `MctlContext` genuinely has no rig to name, and
    #: that is a different fact from "the rig is unknown".
    rig: str = ""

    @property
    def clean(self) -> bool | None:
        """None when the store was unreadable. Unreadable is UNKNOWN, not clean.

        This was a live bug in this file's own bring-up: `clean` was
        `roots_dangling == 0`, so a store that failed to load reported zero
        dangling roots and therefore `clean=True`. The end-to-end positive
        control skipped intermittently because of it -- a conservation check
        announcing a clean bill of health for a store it never read, which is
        precisely the defect this module was written to prevent.
        """
        if not self.readable:
            return None
        return self.roots_dangling == 0

    def to_dict(self) -> dict[str, object]:
        return {
            "clean": self.clean,
            "readable": self.readable,
            "dangling_root_ids": list(self.dangling_root_ids),
            "molecules": self.molecules,
            "orphaned_members": self.orphaned_members,
            "rig": self.rig,
            "roots_dangling": self.roots_dangling,
            "roots_resolving": self.roots_resolving,
            "store_refs": dict(sorted(self.store_refs.items())),
            "window_earliest": self.window_earliest,
            "window_latest": self.window_latest,
        }


# --------------------------------------------------------------------------
# probes
# --------------------------------------------------------------------------


def _run(
    argv: Sequence[str],
    timeout: float = PROBE_TIMEOUT_SECONDS,
    cwd: Path | None = None,
) -> tuple[int | None, str]:
    """Run a probe. Returns (returncode, output); returncode None means it did not complete.

    `cwd` matters and omitting it was a real bug during this module's own
    bring-up: `gc` discovers its city by walking up from the working directory,
    so a probe run from anywhere else exits 1 with "not in a city directory".
    The first version parsed that failure as a successful listing of zero rigs
    -- a command that FAILED rendering as a command that FOUND NOTHING, which
    is the defect this module exists to prevent (issue #100), committed here.
    """
    if shutil.which(argv[0]) is None:
        return None, f"{argv[0]} is not installed"
    try:
        completed = subprocess.run(
            list(argv),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=str(cwd) if cwd is not None else None,
        )
    except subprocess.TimeoutExpired:
        return None, f"probe exceeded {timeout:g}s"
    except OSError as exc:  # pragma: no cover - defensive
        return None, f"probe failed to start: {exc}"
    return completed.returncode, (completed.stdout or completed.stderr or "").strip()


def probe_tmux_panes() -> ProbeResult:
    """Count fleet panes.

    A missing tmux server is the S8 wedge: the supervisor is alive, believes it
    is running a city, and cannot spawn a single agent. It is reported as a
    *completed* probe with ok=False -- we genuinely looked and there is nothing
    there -- which is different from tmux being unavailable to look with.
    """
    code, output = _run(["tmux", "-L", TMUX_SOCKET, "list-panes", "-a"])
    if code is None:
        return ProbeResult("tmux_panes", None, output)
    if code != 0:
        # tmux exits non-zero when no server is running. That is an answer.
        return ProbeResult("tmux_panes", False, "no tmux server running", value=0)
    panes = len([line for line in output.splitlines() if line.strip()])
    return ProbeResult("tmux_panes", panes > 0, f"{panes} pane(s)", value=panes)


def probe_supervisor(city_root: Path | None = None) -> ProbeResult:
    """Ask whether a supervisor process is running.

    Deliberately NOT treated as the city being up. In QUIMBY 44 this reported
    "running" for pid 20711 while that same process had already unregistered
    the city after exhausting its file-descriptor table. A live supervisor is
    necessary, not sufficient.
    """
    code, output = _run(["gc", "supervisor", "status"], cwd=city_root)
    if code is None:
        return ProbeResult("supervisor", None, output)
    if code != 0:
        # A non-zero gc exit is a probe that did not answer, NOT a probe that
        # answered "no". `gc` exits 1 for "not in a city directory", which says
        # nothing whatsoever about whether a supervisor is running.
        return ProbeResult("supervisor", None, f"gc exited {code}: {output.splitlines()[0] if output else ''}")
    running = "running" in output.lower() and "not running" not in output.lower()
    return ProbeResult("supervisor", running, output.splitlines()[0] if output else "")


def probe_rigs(city_root: Path | None = None) -> tuple[ProbeResult, tuple[str, ...], tuple[str, ...]]:
    """Partition registered rigs into suspended and active.

    A suspended rig is skipped by the reconciler (`gc rig suspend --help`:
    "reconciler will skip its agents"), so its agents never spawn no matter how
    much ready work it holds. In QUIMBY 44 all sixteen rigs were suspended, and
    nothing surfaced that as the reason the city consumed nothing.
    """
    code, output = _run(["gc", "rig", "list"], timeout=RIG_PROBE_TIMEOUT_SECONDS, cwd=city_root)
    if code is None:
        return ProbeResult("rigs", None, output), (), ()
    if code != 0:
        # See _run: a failed enumeration must never render as an empty one.
        first = output.splitlines()[0] if output else ""
        return ProbeResult("rigs", None, f"gc exited {code}: {first}"), (), ()
    suspended: list[str] = []
    active: list[str] = []
    for line in output.splitlines():
        # Rig entries are INDENTED under a "Rigs in <path>:" header that also
        # ends in a colon. Matching on the colon alone counted the header as a
        # rig named "Rigs in /Users/tdupuy/gt" -- caught in bring-up.
        if not line.startswith(" "):
            continue
        stripped = line.strip()
        if not stripped.endswith(":"):
            continue
        label = stripped[:-1]
        if label.endswith("(suspended)"):
            suspended.append(label.replace("(suspended)", "").strip())
        elif "(" in label:  # "gt (HQ)" and friends are not work rigs
            continue
        else:
            active.append(label)
    detail = f"{len(active)} active, {len(suspended)} suspended"
    return ProbeResult("rigs", len(active) > 0, detail), tuple(active), tuple(suspended)


def city_state(city_root: Path | None = None) -> CityState:
    """Assemble city state from probes, refusing to collapse a partial answer.

    `city_root` is passed to every `gc` probe as its working directory, because
    gc resolves its city by walking up from cwd. Callers that have a context
    should always supply it; without it the gc probes report `unknown` rather
    than guessing, which is the correct degradation but not a useful one.
    """
    panes = probe_tmux_panes()
    supervisor = probe_supervisor(city_root)
    rigs, active, suspended = probe_rigs(city_root)
    probes = (panes, supervisor, rigs)

    diagnostics: list[Diagnostic] = []
    if not panes.looked or not supervisor.looked:
        state = "unknown"
        diagnostics.append(
            Diagnostic(
                severity=Severity.WARN,
                code="MAYOR_CITY_STATE_UNKNOWN",
                message="A load-bearing probe did not complete; city state is undetermined.",
                hint="This is NOT 'down'. Re-run when the probe can complete.",
                facts={
                    "implementation_provenance": "mctl mayor city-state",
                    "policy_reference": "issue #100 (a timed-out probe must not render as an answer)",
                },
            )
        )
    elif panes.ok:
        state = "up"
    elif panes.value == 0 and supervisor.ok:
        # The S8 wedge: supervisor alive, no fleet host, zero agents possible.
        state = "down"
        diagnostics.append(
            Diagnostic(
                severity=Severity.ERROR,
                code="MAYOR_FLEET_HOST_ABSENT",
                message="A supervisor is running but there is no tmux server; no agent can spawn.",
                hint="`gc restart` gives the supervisor a fresh tmux server.",
                facts={
                    "implementation_provenance": "mctl mayor city-state",
                    "suggested_next_command": "gc restart",
                },
            )
        )
    else:
        state = "down"

    if state in {"up", "idle"} and suspended:
        diagnostics.append(
            Diagnostic(
                severity=Severity.WARN,
                code="MAYOR_RIGS_SUSPENDED",
                message=f"{len(suspended)} rig(s) suspended; the reconciler skips their agents.",
                hint="Ready work in a suspended rig is never dispatched.",
                facts={
                    "data_location": ", ".join(suspended),
                    "implementation_provenance": "mctl mayor city-state",
                },
            )
        )

    return CityState(
        state=state,
        probes=probes,
        suspended_rigs=suspended,
        active_rigs=active,
        pane_count=panes.value,
        diagnostics=tuple(diagnostics),
    )


# --------------------------------------------------------------------------
# conservation
# --------------------------------------------------------------------------


def _metadata(row: Mapping[str, object]) -> Mapping[str, object]:
    """bd returns metadata as a mapping or a JSON string depending on version."""
    raw = row.get("metadata") or {}
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except ValueError:
            return {}
        return parsed if isinstance(parsed, dict) else {}
    return raw if isinstance(raw, dict) else {}


def conservation_from_rows(
    rows: Sequence[Mapping[str, object]], *, rig: str = ""
) -> ConservationReport:
    """Pure function over bead rows -- the testable half, with no subprocess.

    Split out so the invariant can be exercised against fixtures that contain a
    known dangling root. A conservation check that has only ever run against a
    clean store has not been shown to detect anything.

    `rig` defaults to empty rather than being required: a caller with only
    rows and no `MctlContext` has no rig to name, and that is a different,
    honest fact from the rig being unknown.
    """
    ids = {str(row.get("id")) for row in rows if row.get("id")}
    members: dict[str, list[Mapping[str, object]]] = {}
    store_refs: dict[str, int] = {}
    for row in rows:
        meta = _metadata(row)
        root = meta.get(ROOT_BEAD_FIELD)
        if not root:
            continue
        members.setdefault(str(root), []).append(row)

    dangling = sorted(root for root in members if root not in ids)
    resolving = [root for root in members if root in ids]
    orphans = [row for root in dangling for row in members[root]]

    for root in dangling:
        for row in members[root]:
            ref = str(_metadata(row).get(ROOT_STORE_FIELD) or "(none)")
            store_refs[ref] = store_refs.get(ref, 0) + 1

    created = sorted(
        str(row.get("created_at")) for row in orphans if row.get("created_at")
    )

    diagnostics: list[Diagnostic] = []
    if dangling:
        diagnostics.append(
            Diagnostic(
                severity=Severity.ERROR,
                code="MAYOR_CONSERVATION_DANGLING_ROOT",
                message=(
                    f"{len(dangling)} workflow root(s) referenced by {len(orphans)} live "
                    "bead(s) do not resolve to any bead."
                ),
                hint=(
                    "An unaccounted exit under the lost-bead conservation invariant. "
                    "DO NOT prune these pointers -- they are the only surviving evidence "
                    "the workflows existed."
                ),
                facts={
                    "implementation_provenance": "mctl mayor conservation",
                    "policy_reference": "subdomains/dev/docs/lost-bead-conservation-spec.md",
                },
            )
        )

    return ConservationReport(
        molecules=len(members),
        roots_resolving=len(resolving),
        roots_dangling=len(dangling),
        orphaned_members=len(orphans),
        dangling_root_ids=tuple(dangling),
        window_earliest=created[0] if created else None,
        window_latest=created[-1] if created else None,
        store_refs=store_refs,
        diagnostics=tuple(diagnostics),
        rig=rig,
    )


def load_rows(rig_root: Path, timeout: float = 900.0) -> tuple[list[Mapping[str, object]], str | None]:
    """Read every bead in one store. Returns (rows, error)."""
    if shutil.which("bd") is None:
        return [], "bd is not installed"
    try:
        completed = subprocess.run(
            ["bd", "list", "--all", "--limit", "0", "--json"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            cwd=str(rig_root),
        )
    except subprocess.TimeoutExpired:
        return [], f"bd list exceeded {timeout:g}s"
    if completed.returncode != 0:
        return [], (completed.stderr or "bd list failed").strip()
    try:
        payload = json.loads(completed.stdout)
    except ValueError as exc:
        return [], f"bd list returned unparseable JSON: {exc}"
    # bd returns either a bare list or {"issues": [...]} depending on version.
    rows = payload.get("issues") if isinstance(payload, dict) else payload
    if not isinstance(rows, list):
        return [], "bd list returned an unexpected shape"
    return [row for row in rows if isinstance(row, dict)], None


def conservation_report(ctx: "MctlContext") -> ConservationReport:
    """Referential-integrity conservation check for one rig's store."""
    rows, error = load_rows(ctx.rig_root)
    if error is not None:
        return ConservationReport(
            molecules=0,
            roots_resolving=0,
            roots_dangling=0,
            orphaned_members=0,
            dangling_root_ids=(),
            window_earliest=None,
            window_latest=None,
            store_refs={},
            readable=False,
            rig=ctx.rig_id,
            diagnostics=(
                Diagnostic(
                    severity=Severity.FATAL,
                    code="MAYOR_CONSERVATION_UNREADABLE",
                    message=f"Could not read the bead store: {error}",
                    hint="A store that cannot be read is UNKNOWN, not clean.",
                    facts={
                        "city_path": str(ctx.city_root),
                        "implementation_provenance": "mctl mayor conservation",
                        "rig_name": ctx.rig_id,
                        "rig_path": str(ctx.rig_root),
                    },
                    trace_id=ctx.trace_id,
                ),
            ),
        )
    return conservation_from_rows(rows, rig=ctx.rig_id)


# --------------------------------------------------------------------------
# boot state -- the handoff, factored into queries
# --------------------------------------------------------------------------

#: What a Mayor reboot needs that NOTHING can answer as a query.
#:
#: Taylor's framing: the handoff being "crazy long" is the symptom and the API
#: is the cure. That is true of state -- open work, blocked work, the session
#: chain, city health, conservation -- and it is NOT true of intent. A charge
#: is a decision about what should happen next; no read of the store produces
#: it, because it does not exist there until a human puts it there.
#:
#: Naming the residue is the honest half of this design. A boot tool that
#: silently returned only the queryable parts would present a partial handoff
#: as a whole one -- the same defect as a timed-out probe rendering as an
#: answer. So the residue ships IN the payload, as data.
PROSE_RESIDUE = (
    "charge: what the next Mayor should do first, and why. Intent, not state.",
    "rationale: why the previous Mayor chose an approach over its alternatives.",
    "retractions: which earlier claims were overturned, and by what evidence.",
    "standing policy: rules that live in POLICY docs, not in the bead graph.",
)

#: Titles of handoff beads follow "S<N> handoff" / "S<N> (NAME) handoff".
_HANDOFF_MARKERS = ("handoff —", "handoff -", "handoff:")


@dataclass(frozen=True)
class BootState:
    """Everything a Mayor reboot can LEARN BY QUERY, plus what it cannot.

    `prose_residue` is not documentation of a limitation -- it is the
    limitation, carried as data so a consumer cannot miss it. The test of done
    Taylor set is "you can reboot from the API alone"; this field is the honest
    answer to how close that is, and it shrinks as gaps are closed.
    """

    city: CityState
    conservation: ConservationReport
    open_beads: int
    blocked_beads: int
    recent_handoffs: Sequence[Mapping[str, object]]
    escalations_queryable: bool
    prose_residue: Sequence[str]
    diagnostics: Sequence[Diagnostic] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "blocked_beads": self.blocked_beads,
            "city": self.city.to_dict(),
            "conservation": self.conservation.to_dict(),
            "escalations_queryable": self.escalations_queryable,
            "open_beads": self.open_beads,
            "prose_residue": list(self.prose_residue),
            "recent_handoffs": [dict(item) for item in self.recent_handoffs],
        }


def _hq_store_root(ctx: "MctlContext") -> Path:
    """The store the session handoff chain lives in.

    Handoff beads (gt-*, e.g. gt-iw0dc3) are written to the city's own HQ store
    at ``<city-root>/.beads`` by the session-catalog convention, NOT to any
    per-rig store. That store is read by running ``bd`` with the city root as
    cwd -- its reserved rig entry resolves ``path: "."`` (see
    ``context.HQ_RIG_ID``). ``boot_state`` read ``ctx.rig_root`` and so returned
    an empty chain while gt-iw0dc3 was live (#205); the handoff query targets
    the HQ store here instead.
    """
    return ctx.city_root


def _handoff_chain(rows: Sequence[Mapping[str, object]], limit: int = 5) -> list[dict[str, object]]:
    """The session chain, newest last. This replaces the prose 'work done by
    previous sessions' block -- it is a query, and it was always a query."""
    found = []
    for row in rows:
        title = str(row.get("title") or "")
        if any(marker in title.lower() for marker in _HANDOFF_MARKERS):
            found.append(
                {
                    "id": str(row.get("id") or ""),
                    "created_at": str(row.get("created_at") or ""),
                    "status": str(row.get("status") or ""),
                    "title": title,
                }
            )
    found.sort(key=lambda item: item["created_at"])
    return found[-limit:]


def boot_state(ctx: "MctlContext", handoff_limit: int = 5) -> BootState:
    """Assemble a Mayor's boot state from queries, and declare what is not one."""
    rows, error = load_rows(ctx.rig_root)
    diagnostics: list[Diagnostic] = []

    if error is not None:
        diagnostics.append(
            Diagnostic(
                severity=Severity.FATAL,
                code="MAYOR_BOOT_STORE_UNREADABLE",
                message=f"Could not read the bead store: {error}",
                hint="Counts below are NOT zero; they are unmeasured.",
                facts={
                    "city_path": str(ctx.city_root),
                    "implementation_provenance": "mctl mayor boot",
                    "rig_name": ctx.rig_id,
                },
                trace_id=ctx.trace_id,
            )
        )
        conservation = conservation_report(ctx)
        return BootState(
            city=city_state(ctx.city_root),
            conservation=conservation,
            open_beads=-1,
            blocked_beads=-1,
            recent_handoffs=(),
            escalations_queryable=False,
            prose_residue=PROSE_RESIDUE,
            diagnostics=tuple(diagnostics),
        )

    open_beads = sum(1 for row in rows if row.get("status") == "open")
    blocked_beads = sum(1 for row in rows if row.get("status") == "blocked")
    wisps = [row for row in rows if str(row.get("id") or "").startswith("gt-wisp-")]

    if not wisps:
        # Measured 2026-08-21: zero wisp-prefixed beads in hq while escalations
        # were demonstrably arriving through `gc mail`. Two surfaces, one of
        # them unqueryable, so "what is escalated" cannot be answered here.
        diagnostics.append(
            Diagnostic(
                severity=Severity.WARN,
                code="MAYOR_ESCALATIONS_NOT_QUERYABLE",
                message="No escalation beads in this store; escalations arrive via `gc mail`.",
                hint="Boot state cannot answer 'what is escalated'. Check `gc mail` by hand.",
                facts={
                    "implementation_provenance": "mctl mayor boot",
                    "suggested_next_command": "gc mail inbox",
                },
            )
        )

    # The session handoff chain lives in the HQ store, not the per-rig store
    # (#205). Read it from there; the rig-store rows above answer everything
    # else on this surface.
    hq_root = _hq_store_root(ctx)
    hq_rows, hq_error = load_rows(hq_root)
    recent_handoffs = _handoff_chain(hq_rows, handoff_limit)

    if not recent_handoffs:
        # Emptiness is not absence. An empty chain -- whether the store was
        # readable and nothing matched, or the store could not be read -- is
        # reported so a consumer can tell "my query found no handoffs" from "no
        # handoffs exist". A silent empty list is the P6.2 defect this pins.
        readable = hq_error is None
        message = "No handoff beads matched the query in the hq store"
        if not readable:
            message = f"{message}; the store could not be read: {hq_error}"
        diagnostics.append(
            Diagnostic(
                severity=Severity.WARN,
                code="MMAY_HANDOFFS_NOT_FOUND",
                message=f"{message}.",
                hint=(
                    "The session chain lives in the hq store; read `bd list` there "
                    "by hand, or confirm the handoff-title convention still holds."
                ),
                facts={
                    "store": "hq",
                    "store_path": str(hq_root),
                    "store_readable": "true" if readable else "false",
                    "query": "bd list --all; title contains one of "
                    + ", ".join(repr(marker) for marker in _HANDOFF_MARKERS),
                    "implementation_provenance": "mctl mayor boot",
                },
            )
        )

    return BootState(
        city=city_state(ctx.city_root),
        conservation=conservation_from_rows(rows),
        open_beads=open_beads,
        blocked_beads=blocked_beads,
        recent_handoffs=recent_handoffs,
        escalations_queryable=bool(wisps),
        prose_residue=PROSE_RESIDUE,
        diagnostics=tuple(diagnostics),
    )
