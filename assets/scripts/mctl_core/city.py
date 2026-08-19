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

Cross-rig *mutation* stays forbidden (plan Global Constraints). Nothing in this
module writes, and `for_each_rig` is only ever handed read functions.
"""
from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
import time
from typing import Any, Callable, Mapping, Sequence

from .context import CityScope, ContextError, MctlContext, resolve_city, resolve_context
from .diagnostics import Diagnostic, Severity
from .liveness import city_not_active_diagnostic


#: Wall-clock budget for one cross-rig read. A rig still unanswered when it
#: expires is reported degraded rather than allowed to hold the whole answer:
#: an operator who cannot see fifteen rigs because the sixteenth is wedged has
#: been given nothing.
ALL_RIGS_DEADLINE_SECONDS = 25.0

#: Concurrency for the fan-out. Eight was the measured knee on the live city:
#: four left the two large rigs queued behind small ones, sixteen bought
#: nothing over eight and multiplied the concurrent `bd` subprocesses.
ALL_RIGS_WORKERS = 8

ALL_RIGS_SCOPE = "all-rigs"


@dataclass(frozen=True)
class RigOutcome:
    """What one rig answered, or the typed reason it could not."""

    rig_id: str
    rig_root: str
    rig_db: str
    payload: dict[str, Any] = field(default_factory=dict)
    failure: tuple[Mapping[str, Any], ...] = ()
    elapsed_ms: int = 0

    @property
    def ok(self) -> bool:
        return not self.failure

    @property
    def reason(self) -> str:
        """One line naming why this rig could not be read."""
        for item in self.failure:
            message = str(item.get("message") or "").strip()
            if message:
                return message
        return "the rig did not answer"

    def to_dict(self, arrays: Sequence[str] = ()) -> dict[str, Any]:
        entry: dict[str, Any] = {
            "counts": {name: len(self.payload.get(name) or ()) for name in arrays},
            "diagnostics": [dict(item) for item in self.failure],
            "elapsed_ms": self.elapsed_ms,
            "ok": self.ok,
            "reason": "" if self.ok else self.reason,
            "rig_db": self.rig_db,
            "rig_id": self.rig_id,
            "rig_root": self.rig_root,
        }
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


def rig_unreadable_diagnostic(rig_id: str, rig_root: str, error: BaseException) -> dict[str, Any]:
    return _diagnostic(
        "MCTL_CITY_RIG_UNREADABLE",
        f"Rig {rig_id!r} could not be read: {type(error).__name__}.",
        f"Read it on its own with --rig {rig_id} to reproduce the failure directly.",
        implementation_provenance="mctl cross-rig read",
        rig_name=rig_id,
        rig_path=rig_root,
    )


def for_each_rig(
    cwd: Path,
    *,
    city: Path | None,
    env: Mapping[str, str],
    run: Callable[[MctlContext], dict[str, Any]],
    workers: int = ALL_RIGS_WORKERS,
    deadline: float = ALL_RIGS_DEADLINE_SECONDS,
) -> tuple[CityScope, tuple[RigOutcome, ...]]:
    """Run one read against every registered rig, concurrently and fail-soft.

    `run` receives a fully resolved `MctlContext` for one rig and returns that
    rig's payload. It is called off the calling thread, so it must not mutate
    shared state -- which is automatic for the read functions this is for.

    Results come back in registry order, not completion order: a page whose
    rows reshuffle between refreshes because one rig got faster is a page
    nobody can scan.
    """
    scope = resolve_city(cwd, city=city, require_runtime_city=True, env=env)

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
            payload = run(ctx)
        except Exception as error:  # noqa: BLE001 - one rig may not kill the answer
            diagnostic = getattr(error, "diagnostic", None)
            failure = (
                diagnostic.to_dict()
                if diagnostic is not None and hasattr(diagnostic, "to_dict")
                else rig_unreadable_diagnostic(rig.name, rig_root, error)
            )
            return RigOutcome(rig.name, rig_root, rig.db, failure=(failure,), elapsed_ms=elapsed())
        return RigOutcome(rig.name, rig_root, rig.db, payload=dict(payload), elapsed_ms=elapsed())

    pool = ThreadPoolExecutor(max_workers=max(1, workers), thread_name_prefix="mctl-rig")
    try:
        futures: list[tuple[Any, Future]] = [(rig, pool.submit(one, rig)) for rig in scope.rigs]
        expires_at = time.monotonic() + deadline
        outcomes: list[RigOutcome] = []
        for rig, future in futures:
            remaining = max(0.0, expires_at - time.monotonic())
            try:
                outcomes.append(future.result(timeout=remaining))
            except Exception:  # noqa: BLE001 - TimeoutError included, deliberately
                outcomes.append(
                    RigOutcome(
                        rig.name,
                        str(rig.root),
                        rig.db,
                        failure=(rig_timeout_diagnostic(rig.name, str(rig.root), deadline),),
                    )
                )
    finally:
        # Not waited on: a straggler finishes into a result nobody reads, but
        # the answer already went out. Waiting here would reintroduce exactly
        # the "one wedged rig holds the page" failure the deadline removes.
        pool.shutdown(wait=False)
    return scope, tuple(outcomes)


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


def merge_outcomes(
    scope: CityScope,
    outcomes: Sequence[RigOutcome],
    *,
    arrays: Sequence[str],
    trace_id: str,
    artifact_state: bool = False,
    validity: bool = False,
) -> dict[str, Any]:
    """Assemble one city-wide payload out of the per-rig payloads.

    Every row in every merged array carries `rig_id`, because a brief id with
    no rig is an address with no store behind it -- and the caller that opens
    or adjudicates it has to know which bead store it belongs to. Aggregation
    is a read-side convenience; addressing stays per rig.
    """
    merged: dict[str, list[Any]] = {name: [] for name in arrays}
    diagnostics: list[dict[str, Any]] = []
    untrusted: list[dict[str, Any]] = []
    severity_counts: dict[str, int] = {}
    valid = True
    trusted_rigs: list[str] = []
    untrusted_rigs: list[str] = []
    withheld: set[str] = set()

    for outcome in outcomes:
        if not outcome.ok:
            valid = False  # a rig that could not be read cannot be called consistent
            diagnostics.extend(_tagged(outcome.failure, outcome.rig_id))
            continue
        for name in arrays:
            for row in outcome.payload.get(name) or ():
                merged[name].append(
                    {**dict(row), "rig_id": outcome.rig_id} if isinstance(row, Mapping) else row
                )
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
        "rigs": [outcome.to_dict(arrays) for outcome in outcomes],
        "scope": ALL_RIGS_SCOPE,
        "trace_id": trace_id,
    }
    payload.update(merged)
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
