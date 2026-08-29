"""#181 / mc-u9eun / mc-vtru8 — a bound below the measured cost cannot succeed.

**Original subject, unchanged.** `apply_dispatch_plan` shells out to `gc sling`.
The budget shipped at 120s; S48 measured a live sling at 162.7s (exit 0 -- slow,
not hung) and #181 measured a live dispatch KILLED at 120s. The budget was smaller
than the cost of the command it wrapped, so no molecule reached the typed surface.
The relationship these tests pin is: **a bound below the measurement is a path
that cannot succeed.**

**What changed (mc-vtru8, Taylor, 2026-08-28).** The budget was raised twice more
on exactly that reasoning -- 120 -> 200 -> 300 -- and killed a successful dispatch
before each raise. A proposal to raise it again with a warn threshold beneath it
was REJECTED. Taylor: *"We shouldn't have a dispatch timeout. So yes, if we raise
the dispatch timeout to infinity and replace it with a warning."* The default now
carries NO deadline, so there is no default bound left to sit below a measurement.

**Why this file was migrated rather than deleted.** Its subject did not go away;
it moved. An operator may still set a bound (`MCTL_DISPATCH_DEADLINE_SECONDS`,
`--deadline-seconds`), and a bound an operator sets below the measured cost fails
in precisely the way #181 failed. So the assertions that compared two constants
now interrogate the operator surface, and the evidence pins -- which may only rise
-- are untouched, because the measurements are evidence and evidence does not
change when a policy does.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.work import (  # noqa: E402
    DISPATCH_BUDGET_WARN_FRACTION,
    DISPATCH_DEADLINE_ENV,
    DISPATCH_TIMEOUT_CODE,
    DISPATCH_TIMEOUT_LANDED_CODE,
    DISPATCH_WARN_AFTER_ENV,
    DISPATCH_WARN_AFTER_SECONDS,
    MEASURED_SLING_WORST_SECONDS,
    classify_dispatch_subprocess_error,
    dispatch_elapsed_warning,
    dispatch_timeout_is_failure,
    operator_bound_below_measurement_warning,
    resolve_dispatch_elapsed_policy,
    resolve_dispatch_timeout,
)


# --- the default: nothing to be below the measurement -------------------------


def test_the_default_dispatch_carries_no_deadline():
    """Part 1 of the verdict, at the site it was ruled about.

    This is the migrated form of `test_the_dispatch_budget_accommodates_the_
    measured_sling_cost`. That test asked whether the bound cleared the
    measurement; the strongest possible answer is that there is no bound, so the
    comparison has no left-hand side.
    """
    policy, notes = resolve_dispatch_elapsed_policy({})
    assert policy.deadline_seconds is None, (
        "a client-side deadline reappeared by default -- mc-vtru8 removed it, and "
        "raising it was explicitly rejected as the wrong fix"
    )
    assert policy.bounded is False
    assert notes == ()


def test_the_default_still_warns_so_the_cost_stays_observable():
    """Removing the bound must not remove the signal (P6.2).

    The reason 120 -> 200 -> 243.51 was discovered three times in production is
    that nothing reported the ACTUAL cost while it still fit. Without a warn
    threshold, an unbounded dispatch is silent no matter how long it runs, which
    is a worse blindness than the one the bound caused.
    """
    policy, _ = resolve_dispatch_elapsed_policy({})
    assert policy.warn_after_seconds == DISPATCH_WARN_AFTER_SECONDS
    assert DISPATCH_WARN_AFTER_SECONDS >= MEASURED_SLING_WORST_SECONDS, (
        f"warning at {DISPATCH_WARN_AFTER_SECONDS}s about a sling MEASURED at "
        f"{MEASURED_SLING_WORST_SECONDS}s would warn on every healthy dispatch, "
        "and a signal that fires always carries nothing"
    )


# --- the evidence pins, untouched: measurements may only rise -----------------


def test_the_measured_sling_worst_case_is_pinned_to_the_s48_measurement():
    """The measurement is evidence, not a knob: it may only rise on new evidence."""
    assert MEASURED_SLING_WORST_SECONDS >= 162.7, (
        "the S48 live sling measured 162.7s; the recorded worst case must not "
        "drop below its own evidence"
    )


def test_the_recorded_worst_case_reflects_the_newest_larger_measurement():
    """The measurement may only RISE, and 243.51 > 162.7, so it must have risen."""
    assert MEASURED_SLING_WORST_SECONDS >= 243.51, (
        "a larger sling cost (243.51s) was measured on 2026-08-28; the recorded "
        "worst case must rise to its own newest evidence"
    )


# --- the migrated subject: an OPERATOR-set bound below the measurement ---------


def test_an_operator_bound_below_the_measured_cost_is_reported():
    """The #181 relationship, retargeted at the surface that can still produce it.

    200s was a real shipped budget that killed a real 243.51s dispatch. An operator
    who sets 200s today gets told what that number does before it does it.
    """
    warning = operator_bound_below_measurement_warning(200.0)
    assert warning is not None
    assert str(MEASURED_SLING_WORST_SECONDS) in warning
    assert "cannot succeed" in warning
    assert DISPATCH_DEADLINE_ENV in warning


def test_a_bound_that_clears_the_measurement_is_not_reported():
    """Negative control (P6.2): the check must be capable of NOT firing."""
    assert operator_bound_below_measurement_warning(MEASURED_SLING_WORST_SECONDS) is None
    assert operator_bound_below_measurement_warning(600.0) is None


def test_no_bound_at_all_cannot_be_below_the_measurement():
    """The structural reason the default retires this failure class."""
    assert operator_bound_below_measurement_warning(None) is None


def test_the_operator_surface_reports_the_undersized_bound_it_accepted():
    """The report reaches the caller, not just the helper that computed it.

    The bound is still APPLIED -- it is the operator's -- but it is never applied
    silently. Silently is how 120s shipped.
    """
    policy, notes = resolve_dispatch_elapsed_policy({DISPATCH_DEADLINE_ENV: "120"})
    assert policy.deadline_seconds == 120.0
    assert any("cannot succeed" in note for note in notes)


def test_an_operator_bound_keeps_a_warn_threshold_strictly_beneath_it():
    """P6.3(a): every deadline carries a warn below it, including operator ones."""
    policy, _ = resolve_dispatch_elapsed_policy({DISPATCH_DEADLINE_ENV: "400"})
    assert policy.deadline_seconds == 400.0
    assert policy.warn_after_seconds is not None
    assert policy.warn_after_seconds < policy.deadline_seconds
    assert 0.0 < DISPATCH_BUDGET_WARN_FRACTION < 1.0


def test_an_unreadable_bound_leaves_the_dispatch_unbounded_and_says_so():
    """A config typo must not become a kill bound nobody chose."""
    policy, notes = resolve_dispatch_elapsed_policy({DISPATCH_DEADLINE_ENV: "5 minutes"})
    assert policy.deadline_seconds is None
    assert any("not a number of seconds" in note for note in notes)


def test_the_operator_can_also_move_the_warn_threshold():
    """The surface adjusts what is REPORTED, not only what is enforced."""
    policy, notes = resolve_dispatch_elapsed_policy({DISPATCH_WARN_AFTER_ENV: "30"})
    assert policy.warn_after_seconds == 30.0
    assert policy.deadline_seconds is None
    assert notes == ()


# --- the completed-dispatch report, retargeted to the warn threshold ----------


def test_a_dispatch_that_ran_past_the_warn_threshold_is_reported():
    """The drift signal survives the removal of the bound it used to precede."""
    elapsed = DISPATCH_WARN_AFTER_SECONDS * 1.2
    warning = dispatch_elapsed_warning(elapsed, policy=resolve_dispatch_elapsed_policy({})[0])
    assert warning is not None
    assert f"{elapsed:.1f}s" in warning, "the report must name the ELAPSED cost (P6.3a)"
    assert "not a failure" in warning


def test_a_fast_dispatch_is_not_reported():
    """Negative control: a report that fired unconditionally would say nothing."""
    policy, _ = resolve_dispatch_elapsed_policy({})
    assert dispatch_elapsed_warning(1.0, policy=policy) is None
    assert dispatch_elapsed_warning(DISPATCH_WARN_AFTER_SECONDS * 0.1, policy=policy) is None


def test_the_report_bands_around_the_warn_threshold():
    just_under = DISPATCH_WARN_AFTER_SECONDS - 0.01
    just_over = DISPATCH_WARN_AFTER_SECONDS + 0.01
    policy, _ = resolve_dispatch_elapsed_policy({})
    assert dispatch_elapsed_warning(just_under, policy=policy) is None
    assert dispatch_elapsed_warning(just_over, policy=policy) is not None


# --- mc-u9eun: the three-valued verdict, which mc-vtru8 must not regress ------
#
# POLICY P6.3 cites DISPATCH_TIMEOUT_CODE / MWRK_DISPATCH_TIMEOUT_UNKNOWN as the
# in-house COMPLIANT REFERENCE, and `applied=None` is the #184 fix. Removing the
# default deadline does not remove this path -- an operator-set bound still
# reaches it -- so every assertion below is load-bearing for the new default too.


def test_a_timeout_whose_dispatch_is_observable_reports_it_landed():
    """Stop saying UNKNOWN when we can just look."""
    verdict = resolve_dispatch_timeout(claim_observed=True)
    assert verdict.applied is True
    assert verdict.may_have_dispatched is True
    assert verdict.code == DISPATCH_TIMEOUT_LANDED_CODE
    assert "retry" not in (verdict.suggested_next_command or "").lower() or "do not" in (
        verdict.suggested_next_command or ""
    ).lower()


def test_a_timeout_with_no_observable_dispatch_stays_unknown():
    """Negative control. Absence of a claim is NOT proof nothing landed.

    The claim may simply not be observable yet (#212/MWRK003), so this must stay
    three-valued `None` -- never collapse to False, which would tell a caller a
    retry is safe when it may not be.
    """
    verdict = resolve_dispatch_timeout(claim_observed=False)
    assert verdict.applied is None
    assert verdict.may_have_dispatched is True
    assert verdict.code == DISPATCH_TIMEOUT_CODE


def test_the_unknown_timeout_still_warns_against_a_blind_retry():
    verdict = resolve_dispatch_timeout(claim_observed=False)
    assert "retry" in (verdict.suggested_next_command or "").lower()


def test_a_landed_timeout_is_not_a_failure():
    """P6.3(b): applied=True must never be rendered as a failure."""
    verdict = resolve_dispatch_timeout(claim_observed=True)
    assert verdict.applied is True
    assert not dispatch_timeout_is_failure(verdict), (
        "a dispatch that demonstrably LANDED was rendered as a failure -- P6.3: "
        "a deadline is a fact about the caller, not the probed system"
    )


def test_an_unresolved_timeout_is_still_reported_as_a_problem():
    """Negative control: the predicate must be able to return True.

    Without this it could return False unconditionally and still pass the test
    above (P6.2 -- a guard that could not have failed is worse than none).
    """
    verdict = resolve_dispatch_timeout(claim_observed=False)
    assert verdict.applied is None
    assert dispatch_timeout_is_failure(verdict)


def test_a_timeout_expiring_is_still_never_collapsed_to_applied_false():
    """The #184 fix, asserted against the CLASSIFIER an operator bound reaches.

    `subprocess.TimeoutExpired` is what an operator-set deadline produces, and it
    must classify as `applied=None` -- cannot tell -- rather than `False`, which
    would be a claim about the world derived from how long we waited.
    """
    verdict = classify_dispatch_subprocess_error(
        subprocess.TimeoutExpired(cmd=["gc", "sling"], timeout=120.0)
    )
    assert verdict.applied is None
    assert verdict.applied is not False
    assert verdict.code == DISPATCH_TIMEOUT_CODE
    assert verdict.may_have_dispatched is True


def test_a_command_that_never_ran_is_still_applied_false():
    """Negative control: `applied` must be capable of False, or None means nothing."""
    verdict = classify_dispatch_subprocess_error(OSError("no such file"))
    assert verdict.applied is False
    assert verdict.may_have_dispatched is False
