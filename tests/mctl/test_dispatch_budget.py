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
    DISPATCH_TIMEOUT_SECONDS,
    MEASURED_SLING_WORST_SECONDS,
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
