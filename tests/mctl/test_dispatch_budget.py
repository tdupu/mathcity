"""#181 — work_dispatch's subprocess budget must clear the measured sling cost.

`apply_dispatch_plan` shells out to `gc sling` with a fixed subprocess budget.
That budget shipped at 120s. S48 measured a live sling at 162.7s (exit 0 -- slow,
not hung), and #181 measured a live dispatch KILLED at the 120s bound: the budget
was smaller than the cost of the command it wraps, so no molecule ever reached
the typed surface.

These pin the same relationship `test_orders_catalog_timeout.py` pins for the
dashboard: a subprocess bound must accommodate the worst MEASURED cost of the
call it wraps. A bound below that measurement is a path that cannot succeed, and
it fails here rather than on a live sling.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core.work import (  # noqa: E402
    DISPATCH_BUDGET_WARN_FRACTION,
    DISPATCH_TIMEOUT_CODE,
    DISPATCH_TIMEOUT_LANDED_CODE,
    DISPATCH_TIMEOUT_SECONDS,
    MEASURED_SLING_WORST_SECONDS,
    dispatch_budget_drift_warning,
    dispatch_timeout_is_failure,
    resolve_dispatch_timeout,
)


def test_the_dispatch_budget_accommodates_the_measured_sling_cost():
    """The budget must clear the worst measured cost of the sling it wraps.

    120s could not: #181 measured a live dispatch killed at that bound. A budget
    below the measured cost fails every live sling the same way.
    """
    assert DISPATCH_TIMEOUT_SECONDS >= MEASURED_SLING_WORST_SECONDS, (
        f"dispatch budget {DISPATCH_TIMEOUT_SECONDS}s cannot accommodate the "
        f"measured worst sling cost {MEASURED_SLING_WORST_SECONDS}s -- it would "
        "time out before it dispatches, which is exactly #181"
    )


def test_the_measured_sling_worst_case_is_pinned_to_the_s48_measurement():
    """The measurement is evidence, not a knob: it may only rise on new evidence.

    Guards the S48 datum (162.7s) so a future edit cannot quietly lower the
    budget by lowering the number it is checked against.
    """
    assert MEASURED_SLING_WORST_SECONDS >= 162.7, (
        "the S48 live sling measured 162.7s; the recorded worst case must not "
        "drop below its own evidence"
    )


# --- mc-u9eun: the third recurrence, and the drift guard that would have caught it ---
#
# 2026-08-28 measured a live sling at 243.51s, exit 0, molecule mc-mgejq minted.
# The budget was 200s, so `subprocess.run` killed a call that HAD succeeded and
# the caller was told the outcome was UNKNOWN. That is the same defect as #181,
# for the third time: 120s -> killed -> 200s (on S48's 162.7s) -> killed at 243.51s.
#
# The two tests above cannot catch this. They pin the budget against a RECORDED
# measurement, so they only stop someone LOWERING the constant -- they are blind
# to the real cost drifting past it. Both stayed green through every recurrence.


def test_the_budget_clears_the_2026_08_28_measured_cost():
    """The 243.51s live measurement must fit inside the budget.

    Direct regression on mc-u9eun: at DISPATCH_TIMEOUT_SECONDS = 200 this fails,
    which is exactly the production failure (trace 46184eb8).
    """
    assert DISPATCH_TIMEOUT_SECONDS >= 243.51, (
        f"dispatch budget {DISPATCH_TIMEOUT_SECONDS}s is below the 243.51s live "
        "sling measured 2026-08-28 (exit 0, molecule mc-mgejq) -- it kills a "
        "dispatch that succeeds and reports UNKNOWN, which is #181 a third time"
    )


def test_the_recorded_worst_case_reflects_the_newest_larger_measurement():
    """The measurement may only RISE, and 243.51 > 162.7, so it must have risen."""
    assert MEASURED_SLING_WORST_SECONDS >= 243.51, (
        "a larger sling cost (243.51s) was measured on 2026-08-28; the recorded "
        "worst case must rise to its own newest evidence"
    )


def test_a_dispatch_near_the_budget_ceiling_warns_before_it_fails():
    """The guard the previous two tests could not provide.

    A cost that has drifted to within the headroom band is the ONLY early signal
    that the next raise is coming. Without it the constant fails silently and is
    discovered in production, which is how 120 -> 200 -> 243 happened unobserved.
    """
    near = DISPATCH_TIMEOUT_SECONDS * 0.95
    warning = dispatch_budget_drift_warning(near)
    assert warning is not None, (
        f"a dispatch costing {near:.1f}s of a {DISPATCH_TIMEOUT_SECONDS}s budget "
        "must warn -- it is one busier city away from the #181 failure"
    )
    assert str(DISPATCH_TIMEOUT_SECONDS) in warning
    assert f"{near:.1f}s" in warning, "the warning must name the ELAPSED cost (P6.3a)"


def test_a_fast_dispatch_does_not_warn():
    """Negative control: the check must be capable of NOT firing.

    Without this, a drift warning that fired unconditionally would pass the test
    above while telling the operator nothing (P6.2: a check that could not have
    failed must not render as a check that passed).
    """
    assert dispatch_budget_drift_warning(1.0) is None
    assert dispatch_budget_drift_warning(DISPATCH_TIMEOUT_SECONDS * 0.1) is None


def test_the_drift_threshold_sits_below_the_budget():
    """The warn band must leave room to act, not fire as the call is being killed."""
    assert 0.0 < DISPATCH_BUDGET_WARN_FRACTION < 1.0
    just_under = DISPATCH_TIMEOUT_SECONDS * DISPATCH_BUDGET_WARN_FRACTION - 0.01
    just_over = DISPATCH_TIMEOUT_SECONDS * DISPATCH_BUDGET_WARN_FRACTION + 0.01
    assert dispatch_budget_drift_warning(just_under) is None
    assert dispatch_budget_drift_warning(just_over) is not None


# --- mc-u9eun: UNKNOWN-on-timeout is the behaviour that actually caused harm ---
#
# The 2026-08-28 dispatch COMPLETED (exit 0, 243.51s, molecule mc-mgejq) and was
# then killed by the 200s budget and reported UNKNOWN. UNKNOWN is strictly worse
# than a refusal: it invites the retry that double-dispatches, and that is exactly
# what happened -- mc-5wdje ended up with two work streams.
#
# The timeout cannot know what happened, but it does not have to GUESS: the same
# claim observation the success path already runs can be run after a timeout too,
# turning "unknown" into an answer whenever the dispatch is observable.


def test_a_timeout_whose_dispatch_is_observable_reports_it_landed():
    """The whole point: stop saying UNKNOWN when we can just look."""
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


# --- P6.3 "a deadline is not a verdict" (subdomains/dev/POLICY.md:554) ---
#
# P6.3(b): on expiry a deadline path must report a distinctly-named NON-FAILURE
# state carrying elapsed, and "must never render as `failed`". A dispatch that
# LANDED is the least-failed outcome there is. Caught by clark reviewing cfd4878:
# the first cut resolved the verdict correctly and then raised it FATAL anyway,
# which is the exact violation P6.3 exists to stop.


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


def test_the_drift_warning_names_the_elapsed_time():
    """P6.3(a): the sub-deadline warn signal must name ELAPSED, not just a bound."""
    elapsed = DISPATCH_TIMEOUT_SECONDS * 0.9
    warning = dispatch_budget_drift_warning(elapsed)
    assert warning is not None
    assert f"{elapsed:.1f}s" in warning
