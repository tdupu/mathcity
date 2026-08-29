"""mc-vtru8 — a caller may watch a subprocess without bounding it (P6.3).

Taylor's verdict on mc-vtru8: *"We shouldn't have a dispatch timeout. So yes, if
we raise the dispatch timeout to infinity and replace it with a warning."* plus
*"There should also be a surface for adjusting the timeout size."*

This is not "raise the number". A client-side deadline manufactures a fact about
the CALLER and then reports it as a fact about the WORK; P6.3 says that fact must
never render as failure. Reporting it more honestly keeps the false fact and
labels it. Removing the bound removes it at the source: with no deadline there is
no elapsed-deadline event to misreport, and the only thing the tool can say about
time is how much has passed, which is true by construction.

`mctl_core/deadlines.py` is the reusable form of that. It is the FIRST such helper
in this codebase (measured 2026-08-28: zero hits for `warn_after`/`warn_threshold`
in `mctl_core/*.py`), and it exists so the three sites POLICY P6.3 named as
violators at adoption -- `fleet.py MCTL_FLEET_STATUS_PROBE_FAILED`,
`health.py MCTL_HEALTH_FD_PROBE_FAILED`, `city.py MCTL_CITY_RIG_TIMEOUT` -- can
adopt one implementation instead of writing a fourth.

P6.2 governs the shape of these tests. The warning REPLACES a check, so a warn
path that never emits is indistinguishable from a call that was never slow. Every
firing assertion below drives a deliberately slow subprocess and reads the elapsed
value out of the warning it actually produced, and every one is paired with a
negative control that proves the same check is capable of NOT firing.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.deadlines import (  # noqa: E402
    ElapsedNotice,
    ElapsedPolicy,
    bounded_policy,
    parse_optional_seconds,
    run_supervised,
    unbounded_policy,
)


def _sleep_command(seconds: float) -> list[str]:
    return [sys.executable, "-c", f"import time; time.sleep({seconds})"]


# --- the policy object refuses the shapes P6.3 forbids -------------------------


def test_the_default_policy_carries_no_deadline():
    """Part 1 of the verdict: the subprocess is not bounded by a client-side timer."""
    policy = unbounded_policy("gc sling", warn_after_seconds=1.0)
    assert policy.deadline_seconds is None
    assert policy.warn_after_seconds == 1.0


def test_a_deadline_with_no_warn_threshold_beneath_it_is_refused():
    """P6.3: "any deadline with no warn threshold beneath it -> fail"."""
    with pytest.raises(ValueError, match="warn"):
        ElapsedPolicy(label="probe", warn_after_seconds=None, deadline_seconds=10.0)


def test_a_warn_threshold_at_or_above_the_deadline_is_refused():
    """A warn that fires as the call is killed leaves no room to act."""
    with pytest.raises(ValueError, match="strictly below"):
        ElapsedPolicy(label="probe", warn_after_seconds=10.0, deadline_seconds=10.0)


def test_an_unbounded_policy_may_still_carry_no_warning():
    """Negative control: the validator must be capable of accepting, not just refusing."""
    policy = ElapsedPolicy(label="probe", warn_after_seconds=None, deadline_seconds=None)
    assert policy.deadline_seconds is None


def test_bounded_policy_derives_a_warn_threshold_strictly_below_the_bound():
    """The one-call constructor the three named sites adopt."""
    policy = bounded_policy("gc status", deadline_seconds=30.0, warn_fraction=0.75)
    assert policy.deadline_seconds == 30.0
    assert policy.warn_after_seconds == 22.5
    assert policy.warn_after_seconds < policy.deadline_seconds


# --- the warning is OBSERVED to fire, mid-flight, carrying elapsed (P6.2) -----


def test_a_slow_subprocess_warns_while_it_is_still_running():
    """The load-bearing test. Drives a real slow subprocess, reads the real warning.

    Three separate claims, each asserted from the produced object rather than from
    a constant: the warning fired at all; it fired BEFORE the process ended
    (`notice.elapsed_seconds < result.elapsed_seconds`, which a post-hoc report
    could not satisfy); and it named the elapsed value.
    """
    seen: list[ElapsedNotice] = []
    policy = unbounded_policy("slow probe", warn_after_seconds=0.15)
    result = run_supervised(_sleep_command(0.75), policy=policy, on_notice=seen.append)

    assert result.completed is not None and result.completed.returncode == 0
    assert not result.deadline_exceeded
    assert seen, "a 0.75s call under a 0.15s warn threshold produced no warning"

    first = seen[0]
    assert first.still_running is True
    assert first.elapsed_seconds < result.elapsed_seconds, (
        f"the warning reported {first.elapsed_seconds:.2f}s but the call took "
        f"{result.elapsed_seconds:.2f}s -- it must fire DURING the call, not after"
    )
    assert f"{first.elapsed_seconds:.1f}s" in first.message()
    assert "slow probe" in first.message()
    assert "no deadline" in first.message()
    assert result.notices[0] == first


def test_a_fast_subprocess_produces_no_warning():
    """Negative control for the test above (P6.2).

    Without it, a notice emitted unconditionally would satisfy every assertion
    above while telling an operator nothing.
    """
    seen: list[ElapsedNotice] = []
    policy = unbounded_policy("fast probe", warn_after_seconds=5.0)
    result = run_supervised(_sleep_command(0.05), policy=policy, on_notice=seen.append)

    assert result.completed is not None and result.completed.returncode == 0
    assert seen == []
    assert result.notices == ()


def test_the_warning_repeats_while_the_call_keeps_running():
    """One warning at 0.15s says nothing about a call still going at 10 minutes."""
    seen: list[ElapsedNotice] = []
    policy = unbounded_policy("slow probe", warn_after_seconds=0.15)
    run_supervised(_sleep_command(0.75), policy=policy, on_notice=seen.append)

    assert len(seen) >= 2, f"expected repeated notices, got {len(seen)}"
    assert [n.elapsed_seconds for n in seen] == sorted(n.elapsed_seconds for n in seen)


def test_an_unbounded_run_is_never_killed():
    """Part 1, end to end: the call outlives every threshold and still exits 0."""
    policy = unbounded_policy("slow probe", warn_after_seconds=0.05)
    result = run_supervised(_sleep_command(0.4), policy=policy)
    assert result.deadline_exceeded is False
    assert result.timeout_error is None
    assert result.completed is not None and result.completed.returncode == 0
    assert result.elapsed_seconds >= 0.4


# --- part 3: the operator surface, and what expiry is allowed to claim --------


def test_an_operator_bound_expires_as_deadline_exceeded_not_as_failure():
    """P6.3 exception (a): a hard safety deadline may abort, but reports elapsed.

    The result carries `deadline_exceeded` and the elapsed time. It does NOT carry
    a non-zero return code presented as the command's own failure -- `completed`
    is None precisely because the command never reported an outcome.
    """
    policy = bounded_policy("slow probe", deadline_seconds=0.4, warn_fraction=0.5)
    started = time.monotonic()
    result = run_supervised(_sleep_command(30.0), policy=policy)
    wall = time.monotonic() - started

    assert result.deadline_exceeded is True
    assert result.completed is None
    assert isinstance(result.timeout_error, subprocess.TimeoutExpired)
    assert result.elapsed_seconds >= 0.4
    assert wall < 10.0, "the deadline did not actually kill the subprocess"
    assert result.notices, "an expiring deadline must have warned beneath itself"
    assert result.notices[0].still_running is True


def test_a_bounded_run_that_finishes_in_time_is_not_deadline_exceeded():
    """Negative control: `deadline_exceeded` must be capable of staying False."""
    policy = bounded_policy("fast probe", deadline_seconds=10.0, warn_fraction=0.75)
    result = run_supervised(_sleep_command(0.05), policy=policy)
    assert result.deadline_exceeded is False
    assert result.timeout_error is None
    assert result.completed is not None and result.completed.returncode == 0


def test_the_notice_names_the_operator_bound_when_there_is_one():
    """An operator who set a bound must see it in the warning that precedes it."""
    notice = ElapsedNotice(
        label="gc sling", elapsed_seconds=12.0, still_running=True, deadline_seconds=20.0
    )
    assert "12.0s" in notice.message()
    assert "20.0s" in notice.message()
    assert "no deadline" not in notice.message()


def test_output_survives_an_unbounded_run():
    """The polling loop must not eat stdout/stderr -- callers read both."""
    command = [
        sys.executable,
        "-c",
        "import sys, time; time.sleep(0.25); sys.stdout.write('out'); sys.stderr.write('err')",
    ]
    result = run_supervised(command, policy=unbounded_policy("echo", warn_after_seconds=0.1))
    assert result.completed is not None
    assert result.completed.stdout == "out"
    assert result.completed.stderr == "err"


def test_a_command_that_cannot_start_still_raises_oserror():
    """Unchanged contract: a spawn failure is a spawn failure, not a deadline."""
    with pytest.raises(OSError):
        run_supervised(
            ["/nonexistent/mctl-elapsed-supervision-probe"],
            policy=unbounded_policy("missing", warn_after_seconds=1.0),
        )


# --- the operator surface's parser --------------------------------------------


@pytest.mark.parametrize("raw", ["", "   ", "none", "None", "off", "never", "infinity"])
def test_the_operator_can_ask_for_no_bound_at_all(raw: str):
    assert parse_optional_seconds(raw) == (None, None)


def test_the_operator_can_set_a_bound():
    assert parse_optional_seconds("45.5") == (45.5, None)


@pytest.mark.parametrize("raw", ["banana", "-3", "0"])
def test_an_unusable_bound_is_reported_rather_than_silently_applied(raw: str):
    seconds, complaint = parse_optional_seconds(raw)
    assert seconds is None
    assert complaint is not None and raw in complaint
