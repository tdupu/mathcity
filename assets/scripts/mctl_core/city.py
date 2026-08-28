"""Cross-rig reads: the one `--all-rigs` / `all_rigs` implementation.

The plan has specified this since Slice 2 -- *"Cross-rig reads require an
explicit option such as `--all-rigs`"*, with `all_rigs` on `briefs_list` -- and
it was never built. In its absence three separate workarounds grew: the
`check-briefs` skill loops `mctl briefs list --rig <X>` in shell, the dashboard
was about to assemble its own, and anything else that wanted a city-wide answer
would have written a fourth. This module is the one read path all of them call,
for the same reason Q2 settled on a single stack-index writer: one
implementation of the semantics, not one per consumer.

Two properties are load-bearing.

**A rig that fails is a named degraded entry, never an exception that kills the
call.** A city-wide answer that silently drops a rig is worse than no city-wide
answer, because it looks complete. Every failure -- an unresolvable context, a
dead data plane, a store that will not read, a rig that never came back -- is
converted into a `RigOutcome` with `ok=False` carrying the typed diagnostics
that explain it, and the healthy rigs are returned beside it.

**The cost is the slowest rig, not the sum of the rigs.** `work ready` once
took 217s by re-reading a store per item; reading N rigs in series is the same
mistake one layer up. Rigs are read concurrently and the whole fan-out is
bounded by a deadline. Measured on the live 16-rig city, 200 briefs: 3.94s in
series, ~1.4s here.

**A rig that runs out of deadline still reports what it had already read.**
The deadline above is what keeps one wedged rig from costing the other
fifteen, and for a while it also threw away everything the wedged rig had
managed to read. That is only harmless when a rig has one store. A brief
roster has two -- a bead store behind Dolt, and manifest rows and stack files
on disk -- and when `hq`'s bead query became a full partition scan the
deadline dropped 245 file-sourced records that had never touched Dolt at all,
taking the city total from 442 to 8. A read that can produce a usable answer
without its slowest store now publishes that answer into a `RigProgress`
slot as soon as it exists, and an expired deadline returns it as a
*partially* degraded rig rather than as nothing. Partial is not success:
`ok` is False, `reason` names which store answered and which did not, and the
CLI exit code is still non-zero.

**"Every rig" includes the city's own store.** The fan-out iterates
`CityScope.rigs`, which `context.city_rig_entries` builds from `city.toml`
*plus* the reserved `hq` entry for `<city-root>/.beads`. That store held 80 of
the live city's 280 decision beads and was invisible here for as long as
"registered" meant "listed in `city.toml`" -- so a city-wide read reported 200
and looked complete, which is the exact failure the degraded-entry rule above
exists to prevent, arriving through enumeration instead of through error.
Membership stays configuration-driven for a reason stated in full there: the
city root holds several `.beads` directories that are not stores and read HQ's
beads when walked, so a directory-driven fan-out would have reported the same
80 beads six times.

Cross-rig *mutation* stays forbidden (plan Global Constraints). Nothing in this
module writes, and `for_each_rig` is only ever handed read functions. The HQ
store changes nothing there: it is addressed by the same per-rig
`resolve_context`, so a brief in it is mutable only through `--rig hq`, whose
`rig_root` is the city root and whose writes therefore land in that store and
no other.
"""
from __future__ import annotations

import os

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from threading import Lock
import time
from typing import Any, Callable, Mapping, Sequence

from .context import CityScope, ContextError, MctlContext, resolve_city, resolve_context
from .diagnostics import Diagnostic, Severity
from .liveness import city_not_active_diagnostic


#: Wall-clock budget for one cross-rig read. A rig still unanswered when it
#: expires is reported degraded rather than allowed to hold the whole answer:
#: an operator who cannot see fifteen rigs because the sixteenth is wedged has
#: been given nothing.
#:
#: Overridable via MCTL_ALL_RIGS_DEADLINE_SECONDS. The default is deliberate and
#: should usually stand -- but on 2026-08-20 a degraded Dolt made every `bd list`
#: exceed 25s, so EVERY rig reported degraded and the bead lane collapsed from 197
#: rows to 8. The documented remedy, MCTL_BD_TIMEOUT_SECONDS, could not help:
#: `bd_timeout_within` bounds the subprocess DOWN to `remaining - 2` and never up,
#: so the fan-out deadline always won. An operator diagnosing a slow store had no
#: way to read the full population at all.
#:
#: This is the third deadline in this codebase to convert a slow truth into a
#: wrong answer (the others: the control-plane probe, and bd's own 30s default
#: sitting above this 25s ceiling). Where a deadline is genuinely load-bearing,
#: as here, it must at least be adjustable by the person watching it fail.
ALL_RIGS_DEADLINE_SECONDS = float(
    os.environ.get("MCTL_ALL_RIGS_DEADLINE_SECONDS", "") or 25.0
)

#: Concurrency for the fan-out. Eight was the measured knee on the live city:
#: four left the two large rigs queued behind small ones, sixteen bought
#: nothing over eight and multiplied the concurrent `bd` subprocesses.
ALL_RIGS_WORKERS = 8

ALL_RIGS_SCOPE = "all-rigs"


#: Key a per-rig read may set on its payload to declare that some of its own
#: stores did not answer while others did. Each entry is one lane, shaped by
#: `briefs.SourceOutcome`: `{lane, ok, reason, sources, diagnostics}`.
#:
#: `city.py` stays out of the question of what a lane *is* -- that is the
#: core read's own vocabulary, and briefs, validate and work do not share
#: one. All this module does is refuse to call a payload carrying a
#: not-ok lane a clean success.
DEGRADED_SOURCES = "degraded_sources"


class RigProgress:
    """A slot one rig's read publishes a usable partial answer into.

    Handed to `run` so that a read with more than one store can say "this
    half is done" before the slow half finishes. The collector reads it only
    when that rig's future misses the deadline: on the ordinary path the
    published value is discarded and the completed payload is used instead.

    Single writer (the worker thread), single reader (the collector, after
    that thread has stopped mattering), but the two are different threads and
    the deadline fires while the writer is still running -- so the handoff
    takes a lock rather than relying on the GIL making a dict assignment
    look atomic.
    """

    __slots__ = ("_lock", "_payload", "_expires_at", "_sink")

    def __init__(
        self,
        expires_at: float | None = None,
        sink: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self._lock = Lock()
        self._payload: dict[str, Any] | None = None
        self._expires_at = expires_at
        self._sink = sink

    def publish(self, payload: Mapping[str, Any]) -> None:
        """Record what is readable so far. Later calls replace earlier ones."""
        snapshot = dict(payload)
        with self._lock:
            self._payload = snapshot
        if self._sink is not None:
            # Outside the lock: the sink is another slot's `publish`, which
            # takes its own, and holding both would order two locks.
            self._sink(snapshot)

    def snapshot(self) -> dict[str, Any] | None:
        """The last published partial answer, or None if the read published none."""
        with self._lock:
            return dict(self._payload) if self._payload is not None else None

    def relaying(self, transform: Callable[[dict[str, Any]], Mapping[str, Any]]) -> "RigProgress":
        """A slot that forwards every publish into this one through `transform`.

        For an adapter that has to finish a partial answer before it is
        published -- add the artifact-trust verdict, say -- without waiting
        for the read to return. Forwarding has to be eager: the whole point
        of the slot is to hold a value at the moment the read is still
        running, and a relay that only drained afterwards would publish
        exactly nothing on the one path that needs it.

        The deadline is shared, because the inner read sizes its own timeouts
        off it.
        """
        return RigProgress(self._expires_at, sink=lambda payload: self.publish(transform(payload)))

    def remaining_seconds(self) -> float | None:
        """Wall-clock budget left before the fan-out gives up on this rig.

        A read whose slowest store has a timeout of its own should bound it by
        this rather than by its own default, so the store reports why it
        failed instead of the fan-out reporting that the rig went quiet. None
        when the caller set no deadline.
        """
        if self._expires_at is None:
            return None
        return max(0.0, self._expires_at - time.monotonic())


@dataclass(frozen=True)
class RigOutcome:
    """What one rig answered, or the typed reason it could not.

    Three states, not two. `failure` means nothing was read and there is no
    payload; `partial_failure` means some of the rig's stores answered and
    others did not, and `payload` holds what did. Both are `ok is False`,
    because a partial answer that renders as a clean success is the exact
    dishonesty the degraded-rig rule exists to prevent -- but only the first
    has nothing worth merging.
    """

    rig_id: str
    rig_root: str
    rig_db: str
    payload: dict[str, Any] = field(default_factory=dict)
    failure: tuple[Mapping[str, Any], ...] = ()
    partial_failure: tuple[Mapping[str, Any], ...] = ()
    elapsed_ms: int = 0

    @property
    def ok(self) -> bool:
        """Whether every store this rig reads answered."""
        return not self.failure and not self.partial_failure

    @property
    def readable(self) -> bool:
        """Whether there is a payload to merge -- true for a partial answer."""
        return not self.failure

    @property
    def partial(self) -> bool:
        """Whether this rig answered from some of its stores but not all."""
        return bool(self.partial_failure) and not self.failure

    @property
    def diagnostics(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(self.failure) + tuple(self.partial_failure)

    @property
    def reason(self) -> str:
        """One line naming why this rig is not a clean read."""
        for item in self.diagnostics:
            message = str(item.get("message") or "").strip()
            if message:
                return message
        return "the rig did not answer"

    @property
    def degraded_sources(self) -> tuple[Mapping[str, Any], ...]:
        return tuple(
            dict(entry)
            for entry in self.payload.get(DEGRADED_SOURCES) or ()
            if isinstance(entry, Mapping)
        )

    def to_dict(self, arrays: Sequence[str] = (), scopes: Sequence[str] = ()) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "counts": {name: len(self.payload.get(name) or ()) for name in arrays},
            "diagnostics": [dict(item) for item in self.diagnostics],
            "elapsed_ms": self.elapsed_ms,
            "ok": self.ok,
            "partial": self.partial,
            "reason": "" if self.ok else self.reason,
            "rig_db": self.rig_db,
            "rig_id": self.rig_id,
            "rig_root": self.rig_root,
        }
        sources = self.degraded_sources
        if sources:
            # Per lane, beside the counts, so "247 briefs" and "the bead store
            # did not answer" are read together. A count with no lane report
            # beside it is the number that looked complete.
            entry[DEGRADED_SOURCES] = list(sources)
        for name in scopes:
            block = self.payload.get(name)
            if isinstance(block, Mapping):
                # Per rig as well as summed, because "1 of 40 briefs" is a
                # different report per rig and a city-wide sum alone would
                # hide which rig the rows came out of. Absent, not zeroed, for
                # a rig that did not answer: a scope block invented for a rig
                # nobody could read would be a denominator with no store
                # behind it.
                entry[name] = dict(block)
        trust = self.payload.get("artifact_trust")
        if isinstance(trust, Mapping):
            # Per rig, never collapsed into one city-wide claim: the resolved
            # brief root and pile differ per rig, so trust genuinely differs
            # per rig and a single verdict would be a guess about most of them.
            entry["artifact_trust"] = dict(trust)
        return entry


def _diagnostic(
    code: str, message: str, hint: str, severity: Severity = Severity.ERROR, **facts: object
) -> dict[str, Any]:
    return Diagnostic(
        severity=severity,
        code=code,
        message=message,
        hint=hint,
        facts={key: str(value) for key, value in facts.items()},
    ).to_dict()


def rig_timeout_diagnostic(rig_id: str, rig_root: str, seconds: float) -> dict[str, Any]:
    return _diagnostic(
        "MCTL_CITY_RIG_TIMEOUT",
        f"Rig {rig_id!r} did not answer within {seconds:.0f}s and is reported as degraded.",
        f"Read it on its own with --rig {rig_id} to see the underlying failure.",
        implementation_provenance="mctl cross-rig read",
        rig_name=rig_id,
        rig_path=rig_root,
        timeout_seconds=f"{seconds:.1f}",
    )


def rig_partial_diagnostic(rig_id: str, rig_root: str, reason: str) -> dict[str, Any]:
    """A rig that answered from some of its stores and not others.

    Separate from `MCTL_CITY_RIG_UNREADABLE` on purpose. "Could not be read"
    and "was read from one of its two stores" call for different actions, and
    a reader given the first sentence for the second situation either
    discards rows that are perfectly good or trusts a total that is short.
    The message carries the whole answer -- which store answered, which did
    not, and why -- because the rig entry is where an operator looks.
    """
    return _diagnostic(
        "MCTL_CITY_RIG_PARTIAL",
        f"Rig {rig_id!r} answered from only part of its stores: {reason}.",
        f"The rows for {rig_id} are that partial read; re-run once the named store answers.",
        implementation_provenance="mctl cross-rig read",
        rig_name=rig_id,
        rig_path=rig_root,
    )


def rig_unreadable_diagnostic(rig_id: str, rig_root: str, error: BaseException) -> dict[str, Any]:
    return _diagnostic(
        "MCTL_CITY_RIG_UNREADABLE",
        f"Rig {rig_id!r} could not be read: {type(error).__name__}.",
        f"Read it on its own with --rig {rig_id} to reproduce the failure directly.",
        implementation_provenance="mctl cross-rig read",
        rig_name=rig_id,
        rig_path=rig_root,
    )


def _partial_failure(payload: Mapping[str, Any], rig_id: str, rig_root: str) -> tuple[dict[str, Any], ...]:
    """Promote a payload's self-declared lane failures to the rig entry.

    The read knows which of *its* stores failed; this module knows only that
    a rig whose payload says so is not a clean success. Keeping the knowledge
    on that side is what lets briefs, validate and work each name their own
    stores without `city.py` learning three vocabularies.

    The lane's own diagnostics are deliberately not copied up: they are
    already in the payload's `diagnostics`, which `merge_outcomes` tags and
    concatenates, and a diagnostic reported twice reads as two findings.
    """
    reasons = [
        str(entry.get("reason") or "").strip()
        for entry in payload.get(DEGRADED_SOURCES) or ()
        if isinstance(entry, Mapping) and not entry.get("ok")
    ]
    reasons = [reason for reason in reasons if reason]
    if not reasons:
        return ()
    return (rig_partial_diagnostic(rig_id, rig_root, "; ".join(reasons)),)


def for_each_rig(
    cwd: Path,
    *,
    city: Path | None,
    env: Mapping[str, str],
    run: Callable[[MctlContext, RigProgress], dict[str, Any]],
    workers: int = ALL_RIGS_WORKERS,
    deadline: float = ALL_RIGS_DEADLINE_SECONDS,
) -> tuple[CityScope, tuple[RigOutcome, ...]]:
    """Run one read against every registered rig, concurrently and fail-soft.

    `run` receives a fully resolved `MctlContext` for one rig and a
    `RigProgress` slot, and returns that rig's payload. It is called off the
    calling thread, so it must not mutate shared state -- which is automatic
    for the read functions this is for.

    A `run` with more than one store should publish the fast stores into the
    progress slot before starting the slow one, and may bound the slow one by
    `progress.remaining_seconds()`. Doing neither is still correct; it just
    means a deadline that expires on this rig returns nothing for it instead
    of the half that was ready.

    Results come back in registry order, not completion order: a page whose
    rows reshuffle between refreshes because one rig got faster is a page
    nobody can scan.
    """
    scope = resolve_city(cwd, city=city, require_runtime_city=True, env=env)
    expires_at = time.monotonic() + deadline
    progress = {rig.name: RigProgress(expires_at) for rig in scope.rigs}

    def one(rig) -> RigOutcome:
        started = time.monotonic()
        rig_root = str(rig.root)

        def elapsed() -> int:
            return int((time.monotonic() - started) * 1000)

        try:
            ctx = resolve_context(
                cwd,
                city=scope.city_root,
                rig=rig.name,
                require_runtime_city=True,
                require_explicit_runtime=True,
                env=env,
            )
        except ContextError as error:
            return RigOutcome(
                rig.name, rig_root, rig.db, failure=(error.diagnostic.to_dict(),), elapsed_ms=elapsed()
            )
        if ctx.city_active is False:
            # The same fail-closed gate a single-rig read applies, applied per
            # rig: one rig's dead data plane degrades that rig, not the city.
            return RigOutcome(
                rig.name,
                rig_root,
                rig.db,
                failure=(city_not_active_diagnostic(ctx).to_dict(),),
                elapsed_ms=elapsed(),
            )
        try:
            payload = run(ctx, progress[rig.name])
        except Exception as error:  # noqa: BLE001 - one rig may not kill the answer
            diagnostic = getattr(error, "diagnostic", None)
            failure = (
                diagnostic.to_dict()
                if diagnostic is not None and hasattr(diagnostic, "to_dict")
                else rig_unreadable_diagnostic(rig.name, rig_root, error)
            )
            return RigOutcome(rig.name, rig_root, rig.db, failure=(failure,), elapsed_ms=elapsed())
        return RigOutcome(
            rig.name,
            rig_root,
            rig.db,
            payload=dict(payload),
            partial_failure=_partial_failure(payload, rig.name, rig_root),
            elapsed_ms=elapsed(),
        )

    pool = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="mctl-rig")
    try:
        futures: list[tuple[Any, Future]] = [(rig, pool.submit(one, rig)) for rig in scope.rigs]
        outcomes: list[RigOutcome] = []
        for rig, future in futures:
            remaining = max(0.0, expires_at - time.monotonic())
            try:
                outcomes.append(future.result(timeout=remaining))
            except Exception:  # noqa: BLE001 - TimeoutError included, deliberately
                outcomes.append(_timed_out(rig, deadline, progress[rig.name].snapshot()))
    finally:
        # Not waited on: a straggler finishes into a result nobody reads, but
        # the answer already went out. Waiting here would reintroduce exactly
        # the "one wedged rig holds the page" failure the deadline removes.
        pool.shutdown(wait=False)
    return scope, tuple(outcomes)


def _timed_out(rig, deadline: float, partial: dict[str, Any] | None) -> RigOutcome:
    """The rig ran out of deadline -- with whatever it had already published.

    A rig whose read published nothing is degraded exactly as before: no
    payload, one `MCTL_CITY_RIG_TIMEOUT`. A rig that published a partial
    answer keeps it, and keeps the timeout diagnostic beside the
    `MCTL_CITY_RIG_PARTIAL` that says which store went quiet -- the operator
    needs both, one to know what is missing and one to know why.
    """
    rig_root = str(rig.root)
    timeout = rig_timeout_diagnostic(rig.name, rig_root, deadline)
    if partial is None:
        return RigOutcome(rig.name, rig_root, rig.db, failure=(timeout,))
    declared = _partial_failure(partial, rig.name, rig_root)
    return RigOutcome(
        rig.name,
        rig_root,
        rig.db,
        payload=partial,
        partial_failure=(declared or ()) + (timeout,),
    )


def _tagged(diagnostics: Sequence[Mapping[str, Any]], rig_id: str) -> list[dict[str, Any]]:
    """Every diagnostic names the rig it came from.

    In a city-wide list an untagged diagnostic is unactionable: the operator
    cannot tell which of sixteen stores to go and look at.
    """
    tagged = []
    for item in diagnostics:
        entry = dict(item)
        facts = dict(entry.get("facts") or {})
        facts.setdefault("rig_name", rig_id)
        entry["facts"] = facts
        tagged.append(entry)
    return tagged


def _accumulate_scope(total: dict[str, Any], block: Any) -> None:
    """Fold one rig's scope block into the city-wide total (M3, mc-uvl).

    Integers add and string lists union-and-sort, which is the whole rule.
    Rig stores are disjoint, so summing denominators does not double-count a
    bead; a `readiness_excluded` naming `blocked` in two rigs describes one
    city-wide fact, so it unions rather than repeating.

    Keys are folded rather than replaced, and a key the total does not already
    carry is ADDED, so a rig running a newer core that reports one more field
    contributes it instead of having it dropped. A non-numeric, non-list value
    is left as the seeded default: silently coercing one would be inventing a
    number, which is the failure this whole block exists to prevent.
    """
    if not isinstance(block, Mapping):
        return
    for key, value in block.items():
        current = total.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, list)):
            continue
        if isinstance(value, int):
            total[key] = (current if isinstance(current, int) else 0) + value
        else:
            seen = set(current) if isinstance(current, list) else set()
            total[key] = sorted(seen | {str(item) for item in value})


def merge_outcomes(
    scope: CityScope,
    outcomes: Sequence[RigOutcome],
    *,
    arrays: Sequence[str],
    trace_id: str,
    scopes: Mapping[str, Mapping[str, Any]] | None = None,
    artifact_state: bool = False,
    validity: bool = False,
) -> dict[str, Any]:
    """Assemble one city-wide payload out of the per-rig payloads.

    Every row in every merged array carries `rig_id`, because a brief id with
    no rig is an address with no store behind it -- and the caller that opens
    or adjudicates it has to know which bead store it belongs to. Aggregation
    is a read-side convenience; addressing stays per rig.

    A *partially* readable rig contributes its rows and its reason both. The
    rows are real -- they came out of stores that answered -- and the reason
    is what stops the total they are part of from reading as complete: the
    rig entry stays `ok: false`, `valid` goes false, and the lane report
    travels in `rigs[].degraded_sources`.

    `scopes` names the per-rig scope blocks to carry (M3, mc-uvl). They are
    declared alongside `arrays` and initialised the same way -- to an empty
    block, not omitted -- so a city where every rig failed still returns the
    key rather than dropping it and failing the tool's own output schema.
    Summing is sound because rig stores are disjoint, so no bead is counted
    twice; integers add, string lists union, and only rigs that contributed
    rows contribute scope. A rig that could not be read adds nothing to the
    denominator, which is what makes `valid: false` beside it the whole story.
    """
    merged: dict[str, list[Any]] = {name: [] for name in arrays}
    # Seeded from the caller's ZERO block, never from `{}`: the tool that
    # declares a scope also declares what an empty one looks like, so a city
    # where no rig answered returns `matched: 0` out of `total_in_store: 0`
    # rather than a half-block that fails the tool's own output schema.
    scope_totals: dict[str, dict[str, Any]] = {
        name: dict(zero) for name, zero in (scopes or {}).items()
    }
    diagnostics: list[dict[str, Any]] = []
    untrusted: list[dict[str, Any]] = []
    severity_counts: dict[str, int] = {}
    valid = True
    trusted_rigs: list[str] = []
    untrusted_rigs: list[str] = []
    withheld: set[str] = set()

    for outcome in outcomes:
        if not outcome.ok:
            # A rig that could not be fully read cannot be called consistent,
            # whether it answered from none of its stores or from some.
            valid = False
            diagnostics.extend(_tagged(outcome.diagnostics, outcome.rig_id))
        if not outcome.readable:
            continue
        # A partial rig's rows ARE merged. They are rows that were read, from
        # stores that answered; dropping them because a *different* store on
        # the same rig went quiet is the coupling this whole path removes.
        for name in arrays:
            for row in outcome.payload.get(name) or ():
                merged[name].append(
                    {**dict(row), "rig_id": outcome.rig_id} if isinstance(row, Mapping) else row
                )
        for name in scope_totals:
            _accumulate_scope(scope_totals[name], outcome.payload.get(name))
        diagnostics.extend(_tagged(outcome.payload.get("diagnostics") or (), outcome.rig_id))
        # Concatenated, never promoted. An aggregate that summed a withheld
        # code into an actionable city-wide total would be the single most
        # damaging thing this surface could report.
        untrusted.extend(_tagged(outcome.payload.get("untrusted_diagnostics") or (), outcome.rig_id))
        for severity, count in (outcome.payload.get("severity_counts") or {}).items():
            severity_counts[str(severity)] = severity_counts.get(str(severity), 0) + int(count)
        if outcome.payload.get("valid") is False:
            valid = False
        trust = outcome.payload.get("artifact_trust")
        if isinstance(trust, Mapping):
            (trusted_rigs if trust.get("trusted") else untrusted_rigs).append(outcome.rig_id)
            withheld.update(str(code) for code in trust.get("withheld_codes") or ())

    payload: dict[str, Any] = {
        "city_root": str(scope.city_root),
        "diagnostics": diagnostics,
        "rigs": [outcome.to_dict(arrays, tuple(scope_totals)) for outcome in outcomes],
        "scope": ALL_RIGS_SCOPE,
        "trace_id": trace_id,
    }
    payload.update(merged)
    payload.update(scope_totals)
    if validity:
        # Declared unconditionally, not "when a rig reported one": a caller
        # that asked for validation and got a payload with no verdict would
        # read the absence as success.
        payload["severity_counts"] = {
            severity.value: severity_counts.get(severity.value, 0) for severity in Severity
        }
        payload["valid"] = valid
    elif severity_counts:
        payload["severity_counts"] = severity_counts
    if artifact_state:
        # Also unconditional. The contract is that artifact state never
        # travels without the reason it may be untrustworthy, and a city where
        # every rig failed is the case where that matters most.
        payload["artifact_trust"] = _city_trust(trusted_rigs, untrusted_rigs, sorted(withheld))
        payload["untrusted_diagnostics"] = untrusted
    return payload


def _city_trust(
    trusted_rigs: Sequence[str], untrusted_rigs: Sequence[str], withheld: Sequence[str]
) -> dict[str, Any]:
    """A city-level roll-up that says which rigs it is a roll-up *of*.

    The per-rig verdicts stay in `rigs[]` and are what a UI should render. This
    exists because the response contract requires one `artifact_trust`, and a
    silent "trusted" computed over a set of rigs that disagree would be the
    dishonest kind of summary. It is trustworthy only if every rig is.
    """
    if not trusted_rigs and not untrusted_rigs:
        return {
            "open_question": "Q5",
            "reason": (
                "no rig reported an artifact-trust verdict, because no rig could be read; "
                "see the per-rig diagnostics in `rigs`"
            ),
            "reference": "subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md#q5",
            "resolved_brief_root": "(per rig - see rigs[].artifact_trust)",
            "resolved_pile": "(per rig - see rigs[].artifact_trust)",
            "trusted": False,
            "withheld_codes": list(withheld),
        }
    if untrusted_rigs:
        return {
            "open_question": "Q5",
            "reason": (
                "artifact readings are not trustworthy in "
                f"{len(untrusted_rigs)} of {len(untrusted_rigs) + len(trusted_rigs)} readable "
                f"rigs ({', '.join(untrusted_rigs)}); see the per-rig verdicts in `rigs`"
            ),
            "reference": "subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md#q5",
            "resolved_brief_root": "(per rig - see rigs[].artifact_trust)",
            "resolved_pile": "(per rig - see rigs[].artifact_trust)",
            "trusted": False,
            "withheld_codes": list(withheld),
        }
    return {
        "open_question": None,
        "reason": (
            f"every readable rig ({', '.join(trusted_rigs)}) resolved a brief root that exists "
            "and a pile using the filename convention the lookup assumes"
        ),
        "reference": None,
        "resolved_brief_root": "(per rig - see rigs[].artifact_trust)",
        "resolved_pile": "(per rig - see rigs[].artifact_trust)",
        "trusted": True,
        "withheld_codes": list(withheld),
    }
