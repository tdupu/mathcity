"""Watch a subprocess by elapsed time instead of bounding it (POLICY P6.3).

**The problem this replaces.** A client-side deadline invents a fact about the
CALLER -- *we stopped waiting* -- and then reports it as a fact about the WORK:
`failed`, `unknown`, absent, zero. P6.3 forbids that rendering, and the record
here says reporting it more honestly is not enough. `work.py`'s dispatch budget
was raised three times on measurement (120s -> 200s -> 300s) and killed a live,
successful dispatch each time before the raise; every one of those kills was a
correct measurement of our patience and a false statement about the sling.

**Taylor's verdict (mc-vtru8, 2026-08-28):** *"We shouldn't have a dispatch
timeout. So yes, if we raise the dispatch timeout to infinity and replace it with
a warning."* and *"There should also be a surface for adjusting the timeout
size."* With no deadline there is no elapsed-deadline event to misreport, and the
only claim the caller can make about time is how much has passed -- true by
construction.

**Three parts, and why parts 1 and 3 are not in tension.** The default is
unbounded (part 1) with a repeating elapsed warning while the call is still
running (part 2). An operator may still set a bound (part 3), and that bound is
load-bearing rather than a hedge: mc-znfnm measured every MCP call serializing on
a single RLock -- `/queue` alone 1.6s / 1.8s, `/queue` during `/city` 64.9s, same
pid, same route, 36x. An unbounded dispatch behind that lock can wedge the
dashboard for as long as the sling runs. P6.3 exception (a) explicitly permits a
hard safety deadline for deadlock and resource exhaustion **provided expiry still
reports `deadline_exceeded` with elapsed and never `failed`**. Part 3 is that
valve, made operator-set instead of hardcoded, and `SupervisedRun` reports its
expiry as exactly the state P6.3 names.

**Why a module and not a branch inside `apply_dispatch_plan`.** P6.3 named four
sites in violation at adoption; three are still violating today --
`fleet.py MCTL_FLEET_STATUS_PROBE_FAILED`, `health.py MCTL_HEALTH_FD_PROBE_FAILED`,
`city.py MCTL_CITY_RIG_TIMEOUT`. Each wraps `subprocess.run(..., timeout=X)` and
turns expiry into a probe failure. They adopt this by replacing that call with
`run_supervised(cmd, policy=bounded_policy(label, deadline_seconds=X))` and
branching on `result.deadline_exceeded` instead of on a `None` payload -- keeping
their bound if they want one, and gaining the warn threshold beneath it that P6.3
requires and none of them has.

**What this module deliberately does NOT do.** It does not classify outcomes. A
timeout still hands back its `TimeoutExpired` so the caller's own verdict logic --
in `work.py`, the three-valued `DispatchFailureVerdict.applied` that #184 fixed --
runs unchanged and keeps saying `None` (cannot tell) rather than `False`.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Mapping, Sequence

#: Values an operator may write to mean "do not bound this at all". The default
#: is already unbounded; these exist so an operator can spell the default back
#: out explicitly, and so a config that once carried a number can be neutralised
#: without deleting the key.
NO_BOUND_WORDS = frozenset({"none", "off", "never", "infinity", "inf", "unbounded", "0s"})

#: Longest the supervisor will sleep between wakeups when it has nothing
#: scheduled. Only reached when a policy has neither a warn threshold nor a
#: deadline, where the wait is on the process itself and this never applies.
_MIN_WAIT_SECONDS = 0.001


@dataclass(frozen=True)
class ElapsedNotice:
    """One honest statement about how long a call has been running.

    Every field is measured. `elapsed_seconds` is wall time since spawn;
    `still_running` distinguishes *"this is taking a while"* (emitted mid-flight,
    which is the signal that replaces the deadline) from *"this took a while"*
    (emitted after the fact, which is a record). Nothing here claims anything
    about whether the work succeeded, because at emission time nobody knows.
    """

    label: str
    elapsed_seconds: float
    still_running: bool
    deadline_seconds: float | None = None

    def message(self) -> str:
        """Text naming the elapsed time and what is being waited on (P6.3(a))."""
        tense = (
            f"has been running {self.elapsed_seconds:.1f}s and has not returned yet"
            if self.still_running
            else f"took {self.elapsed_seconds:.1f}s"
        )
        if self.deadline_seconds is None:
            bound = (
                "no deadline is set, so it will NOT be killed -- this is a report, "
                "not a failure"
            )
        else:
            bound = (
                f"an operator-set deadline of {self.deadline_seconds:.1f}s applies; "
                "on expiry the call is abandoned and the outcome becomes UNKNOWN, "
                "never `failed`"
            )
        return f"{self.label} {tense} ({bound})."


@dataclass(frozen=True)
class ElapsedPolicy:
    """How a caller watches a call it is NOT, by default, bounding.

    `deadline_seconds is None` -- the default everywhere -- means the call runs to
    completion however long it takes. The validation below is P6.3(a) made
    structural: a deadline with no warn threshold strictly beneath it cannot be
    constructed, so no adopter can ship the shape the policy names as a failure.
    """

    label: str
    warn_after_seconds: float | None
    deadline_seconds: float | None = None
    #: Whether the mid-flight warning repeats every `warn_after_seconds`. One
    #: notice at 30s says nothing about a call still running at ten minutes.
    repeat: bool = True

    def __post_init__(self) -> None:
        if self.warn_after_seconds is not None and self.warn_after_seconds <= 0:
            raise ValueError("warn_after_seconds must be positive when set")
        if self.deadline_seconds is None:
            return
        if self.deadline_seconds <= 0:
            raise ValueError("deadline_seconds must be positive when set")
        if self.warn_after_seconds is None:
            raise ValueError(
                "P6.3: a deadline must carry a warn threshold strictly below it; "
                f"{self.label!r} set a {self.deadline_seconds}s deadline with no warn"
            )
        if self.warn_after_seconds >= self.deadline_seconds:
            raise ValueError(
                "P6.3: the warn threshold must sit strictly below the deadline so "
                f"there is room to act; {self.label!r} warns at "
                f"{self.warn_after_seconds}s against a {self.deadline_seconds}s deadline"
            )

    @property
    def bounded(self) -> bool:
        return self.deadline_seconds is not None

    def exceeds_warn(self, elapsed_seconds: float) -> bool:
        if self.warn_after_seconds is None:
            return False
        return elapsed_seconds > self.warn_after_seconds

    def notice(self, elapsed_seconds: float, *, still_running: bool) -> ElapsedNotice:
        return ElapsedNotice(
            label=self.label,
            elapsed_seconds=elapsed_seconds,
            still_running=still_running,
            deadline_seconds=self.deadline_seconds,
        )


def unbounded_policy(label: str, *, warn_after_seconds: float | None) -> ElapsedPolicy:
    """The default shape: watch, report elapsed, never kill."""
    return ElapsedPolicy(label=label, warn_after_seconds=warn_after_seconds)


def bounded_policy(
    label: str, *, deadline_seconds: float, warn_fraction: float = 0.75
) -> ElapsedPolicy:
    """An operator-set bound with a compliant warn threshold derived beneath it.

    One call, so adopting a P6.3-compliant deadline is cheaper than writing a
    non-compliant one by hand. This is the entry point the three named violator
    sites use.
    """
    if not 0.0 < warn_fraction < 1.0:
        raise ValueError("warn_fraction must lie strictly between 0 and 1")
    return ElapsedPolicy(
        label=label,
        warn_after_seconds=deadline_seconds * warn_fraction,
        deadline_seconds=deadline_seconds,
    )


def parse_optional_seconds(raw: str | None) -> tuple[float | None, str | None]:
    """Read an operator's bound: `(seconds, complaint)`, either of which may be None.

    Returns `(None, None)` for absent, blank, or an explicit no-bound word -- the
    default is unbounded, and asking for the default is not an error. Returns
    `(None, complaint)` for anything unusable: an unreadable bound must be
    REPORTED, never silently coerced to a number the operator did not choose,
    which is how a config typo becomes a kill bound nobody set.
    """
    if raw is None:
        return None, None
    text = raw.strip()
    if not text or text.lower() in NO_BOUND_WORDS:
        return None, None
    try:
        seconds = float(text)
    except ValueError:
        return None, (
            f"{text!r} is not a number of seconds, so no deadline was applied; "
            "use a positive number, or one of: " + ", ".join(sorted(NO_BOUND_WORDS))
        )
    if seconds <= 0:
        return None, (
            f"{text!r} is not a positive number of seconds, so no deadline was "
            "applied; use `none` if you meant to remove the bound"
        )
    return seconds, None


@dataclass(frozen=True)
class SupervisedRun:
    """What a supervised call yields: an outcome, an elapsed time, and its notices.

    `completed is None` and `deadline_exceeded is True` together are P6.3's
    `deadline_exceeded` state: the call was abandoned, and this object refuses to
    say more than that. It is NOT a `CompletedProcess` with a synthesised non-zero
    return code, because inventing an exit status the command never produced is
    the collapse P6.3 exists to prevent.
    """

    elapsed_seconds: float
    completed: subprocess.CompletedProcess[str] | None = None
    deadline_exceeded: bool = False
    timeout_error: subprocess.TimeoutExpired | None = None
    notices: tuple[ElapsedNotice, ...] = field(default_factory=tuple)

    @property
    def final_notice(self) -> ElapsedNotice | None:
        """The after-the-fact record, for a call that finished but ran long."""
        if not self.notices:
            return None
        last = self.notices[-1]
        return ElapsedNotice(
            label=last.label,
            elapsed_seconds=self.elapsed_seconds,
            still_running=False,
            deadline_seconds=last.deadline_seconds,
        )


def run_supervised(
    command: Sequence[str],
    *,
    policy: ElapsedPolicy,
    cwd: Path | str | None = None,
    env: Mapping[str, str] | None = None,
    on_notice: Callable[[ElapsedNotice], None] | None = None,
) -> SupervisedRun:
    """Run `command`, reporting elapsed time while it runs; kill only if bounded.

    The child is drained on a worker thread rather than polled, so a chatty
    command cannot fill a pipe buffer and deadlock the supervisor -- the failure
    mode of the obvious `Popen` + `poll()` loop, and one that would look exactly
    like the hang this module is here to stop mislabelling.

    `on_notice` is called AS each notice is produced, which is what makes the
    warning visible while the call is still running; the same notices are also
    returned, so a caller that renders a payload afterwards keeps them. A caller
    that passes no sink still gets the record.

    Raises `OSError` if the command cannot be started -- unchanged from
    `subprocess.run`, and deliberately distinct from expiry: nothing ran.
    """
    argv = [str(part) for part in command]
    started = time.monotonic()
    process = subprocess.Popen(  # noqa: S603 -- argv is caller-controlled, no shell
        argv,
        cwd=None if cwd is None else str(cwd),
        env=None if env is None else dict(env),
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    drained = threading.Event()
    captured: dict[str, object] = {}

    def _drain() -> None:
        try:
            captured["streams"] = process.communicate()
        except BaseException as error:  # pragma: no cover -- defensive
            captured["error"] = error
        finally:
            drained.set()

    worker = threading.Thread(target=_drain, name="mctl-elapsed-drain", daemon=True)
    worker.start()

    notices: list[ElapsedNotice] = []
    next_warn = policy.warn_after_seconds
    deadline = policy.deadline_seconds
    deadline_exceeded = False

    while True:
        elapsed = time.monotonic() - started
        waits = [value - elapsed for value in (next_warn, deadline) if value is not None]
        timeout = max(_MIN_WAIT_SECONDS, min(waits)) if waits else None
        if drained.wait(timeout):
            break
        elapsed = time.monotonic() - started
        if deadline is not None and elapsed >= deadline:
            deadline_exceeded = True
            process.kill()
            drained.wait()
            break
        if next_warn is not None and elapsed >= next_warn:
            notice = policy.notice(elapsed, still_running=True)
            notices.append(notice)
            if on_notice is not None:
                on_notice(notice)
            next_warn = (
                elapsed + policy.warn_after_seconds
                if policy.repeat and policy.warn_after_seconds is not None
                else None
            )

    worker.join()
    elapsed = time.monotonic() - started
    error = captured.get("error")
    if isinstance(error, BaseException):  # pragma: no cover -- defensive
        raise error
    stdout, stderr = captured.get("streams", ("", ""))  # type: ignore[misc]

    if deadline_exceeded:
        return SupervisedRun(
            elapsed_seconds=elapsed,
            completed=None,
            deadline_exceeded=True,
            timeout_error=subprocess.TimeoutExpired(
                cmd=argv, timeout=float(deadline or elapsed), output=stdout, stderr=stderr
            ),
            notices=tuple(notices),
        )
    return SupervisedRun(
        elapsed_seconds=elapsed,
        completed=subprocess.CompletedProcess(
            args=argv, returncode=process.returncode, stdout=stdout, stderr=stderr
        ),
        notices=tuple(notices),
    )
