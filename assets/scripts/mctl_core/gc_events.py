"""Best-effort city-event emission for mctl (Plan C, #202).

mctl rings the city's doorbells: when the typed surface deposits a brief or
records a verdict, it emits a `gc event` so the event-triggered orders
(`brief-shuffle-on-submit` on `brief.submitted`; `brief-decision-dispatch` and
`post-decision-file-or-sendback` on `brief.decided`) fire within seconds
instead of waiting for the next condition tick.

EMISSION SHAPE. The plan's Task 1 Step 1 says to copy brief-prep.toml's
submit-to-pile emit command verbatim -- but that step emits nothing; it only
moves the staged brief into `.pile/`. The only real in-tree `gc event`
producer is `formulas/brief-record-decision.toml`'s emit-decided-event step:

    gc event emit brief.decided \\
      --subject "<slug>" \\
      --message "brief <slug> decided: <decision>" \\
      --payload '{"brief_slug":"<slug>","decision":"<decision>"}'

so `emit()` reproduces that shape -- `gc event emit <type> --subject <s>
--message <m> --payload <json>` -- and a consumer cannot tell mctl's event
apart from the skill path's.

BEST-EFFORT BY DESIGN (the human adjudicator 2026-06-30, "ring the bell, no
polling"). The event is a wake-up, never the source of truth: the typed
mutation already wrote the canonical bead. `gc event emit` is documented to
always exit 0, but the subprocess can still fail to launch (gc absent, city
down, timeout). On ANY failure emit() returns a WARN advisory Diagnostic
(MEVT_EMIT_FAILED) and NEVER raises -- the condition backstop recovers a lost
event.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Callable, Mapping

from .diagnostics import Diagnostic, Severity

#: Stable diagnostic code for a failed doorbell. Registered in
#: assets/mctl/diagnostics.toml; the MEVT family is in test_diagnostics_registry
#: CODE_PATTERN so this string is scanned like every other emitted code.
EMIT_FAILED = "MEVT_EMIT_FAILED"

#: Seconds to allow the `gc event emit` subprocess. A slow or hung `gc` is a
#: failed doorbell, not a failed deposit -- it must not hold the typed
#: mutation's response open.
#:
#: SIZED TO A MEASUREMENT (#217), not to a round number. Measured on the live
#: kolchin city 2026-09-09, six consecutive `gc event emit` calls against an
#: event type no order listens for (so the probe rang nothing):
#:
#:     0.62  0.72  0.77  0.72  0.61  0.58   seconds, rc=0
#:     p100 = 0.77s, mean = 0.67s
#:
#: So the real cost is sub-second and this budget carries ~13x headroom over the
#: worst observed call. That margin is deliberate and is NOT slack to be tuned
#: away:
#:
#:   * #216 measured gc startup alone at ~9.5s before the fast path landed
#:     (fixed in tdupu/gascity#32). A budget tightened to today's sub-second
#:     numbers would turn any regression of that fast path -- or a loaded city --
#:     straight back into the dropped-doorbell class this constant exists for.
#:   * The failure mode is asymmetric. Too generous costs a slow WARN on a
#:     already-broken path; too tight silently drops the bell that fires
#:     brief-shuffle-on-submit and brief-decision-dispatch.
#:
#: Re-measure with `gc event emit <unlistened-type> --subject probe` before
#: changing this; the number should follow the measurement, not the reverse.
EMIT_TIMEOUT_SECONDS = 10

Runner = Callable[[list[str]], Any]

#: Kill-switch for the real doorbell. Set to `0`/`false`/`no`/`off` to make
#: `emit` a no-op instead of shelling to `gc event emit`.
#:
#: WHY IT EXISTS (measured 2026-08-28). `gc` is on PATH on a developer box, so
#: any test that drives a LIVE mctl apply rang the REAL city: 329 `brief.decided`
#: events with the fixture subject `mc-open`, plus 60 for `gs-open`, were on the
#: bus in 24h, the oldest from 2026-08-27T18:38 -- and `brief.decided` has THREE
#: consumers, so each one woke brief-decision-dispatch,
#: post-decision-file-or-sendback and revise-return on a brief that does not
#: exist. A fixture run is not a city and must not ring its bells.
#:
#: The switch is honoured ONLY for the default subprocess runner. An INJECTED
#: runner is the caller's own seam -- a test that supplies one is asking to
#: observe the call, and suppressing it there would make the seam lie.
CITY_EVENTS_ENV = "MCTL_CITY_EVENTS"

_SUPPRESSED_VALUES = frozenset({"0", "false", "no", "off"})


def suppressed() -> bool:
    """True when the environment has switched the real doorbell off."""
    return os.environ.get(CITY_EVENTS_ENV, "").strip().lower() in _SUPPRESSED_VALUES


def _default_runner(argv: list[str]) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        argv,
        text=True,
        capture_output=True,
        check=False,
        timeout=EMIT_TIMEOUT_SECONDS,
    )


def emit_argv(event: str, subject: str, payload: Mapping[str, object]) -> list[str]:
    """The exact `gc event emit` command line for one doorbell.

    Factored out so a test can pin the shape without spawning a subprocess. The
    payload is serialised with sorted keys so the command is deterministic.
    """
    return [
        "gc",
        "event",
        "emit",
        event,
        "--subject",
        subject,
        "--message",
        f"{event} {subject}",
        "--payload",
        json.dumps(dict(payload), sort_keys=True),
    ]


def emit(
    event: str,
    subject: str,
    payload: Mapping[str, object],
    *,
    runner: Runner | None = None,
) -> Diagnostic | None:
    """Ring one city doorbell. Returns None on success, or a WARN advisory
    Diagnostic on failure. NEVER raises.

    `runner` is an injectable subprocess seam (a recording fake in tests);
    absent, it shells to `gc event emit` with a bounded timeout.
    """
    if runner is None and suppressed():
        # Deliberate suppression is not a failed doorbell: the caller asked for
        # silence, so there is nothing for a backstop to recover and no advisory
        # to raise.
        return None
    argv = emit_argv(event, subject, payload)
    run = runner or _default_runner
    try:
        result = run(argv)
    except Exception as error:  # OSError, TimeoutExpired, or anything the runner raises
        return _failed(event, subject, f"gc event emit could not run: {error}")
    returncode = getattr(result, "returncode", 0)
    if returncode not in (0, None):
        stderr = (getattr(result, "stderr", "") or "").strip()
        return _failed(event, subject, stderr or f"gc event emit exited {returncode}")
    return None


def _failed(event: str, subject: str, detail: str) -> Diagnostic:
    return Diagnostic(
        Severity.WARN,
        EMIT_FAILED,
        f"Best-effort city event {event!r} for {subject!r} was not emitted; "
        "the condition backstop will recover it.",
        hint="events are lossy by design; the typed mutation already succeeded",
        facts={"event_type": event, "subject": subject, "detail": detail},
    )


#: The city event one recorded verdict rings. THREE orders subscribe to it --
#: `brief-decision-dispatch` (acts on the verdict), `post-decision-file-or-
#: sendback` (routes follow-up briefing), and `revise-return` (re-deposits a
#: revised brief). Named once here so the producers cannot disagree about it.
BRIEF_DECIDED = "brief.decided"


def emit_brief_decided(
    brief_id: str,
    *,
    verdict: object,
    adjudicated_by: object,
    runner: Runner | None = None,
) -> Diagnostic | None:
    """Ring `brief.decided` for a just-recorded verdict, from ANY write path.

    WHY THIS IS SHARED (mc-d6lp). The MCP path (`briefs_relay_adjudication`)
    rang this bell; the CLI path (`mctl briefs adjudicate`) recorded the same
    verdict and rang nothing -- so `gc events | grep revise-return` showed zero
    firings and 13 hecke briefs adjudicated `revise` were closed by a verdict
    that could never come back. Two producers of one event with two separate
    payload literals is how they drifted; there is now one.

    The payload keys are the ones the skill path (brief-record-decision.toml)
    uses, so a consumer cannot tell the three producers apart: `brief_slug`
    resolves the brief for all three orders, and `decision` is what
    brief-decision-dispatch branches on (approve/reject/revise/defer).
    Best-effort like every doorbell: returns a WARN advisory, never raises.
    """
    return emit(
        BRIEF_DECIDED,
        brief_id,
        {
            "brief_slug": brief_id,
            "decision": verdict,
            "adjudicated_by": adjudicated_by,
        },
        runner=runner,
    )
