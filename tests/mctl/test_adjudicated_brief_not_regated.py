"""An adjudicated brief is terminal; nothing may re-judge it (mc-8ehd0).

Measured 2026-08-28 against the live city: 24 slug directories in
`.beads/briefs/.pile/.rejected/`, **8** of them carrying a verdict (7 approve
+ 1 reject, all `status: adjudicated`), 22 of the 24 rejected for "standard
brief missing provenance metadata" -- metadata an adjudicated brief has no
obligation to carry. Those 8 are human decisions a machine discarded.

Every test below has a stated failing case, and the negative controls are not
decoration: the failure mode of this guard is that it becomes always-true and
the gate stops rejecting anything. P6.2 -- a check that could not have failed
must not render as a check that passed.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core import verdicts  # noqa: E402


def test_a_brief_with_a_verdict_is_adjudicated() -> None:
    assert verdicts.is_adjudicated({"verdict": "approve"}) is True


def test_a_brief_without_a_verdict_is_not_adjudicated() -> None:
    """Control: without this, the guard could return True always and pass."""
    assert verdicts.is_adjudicated({"status": "ready"}) is False


def test_an_empty_verdict_string_is_not_adjudicated() -> None:
    """`verdict:` with nothing after it is an absent verdict, not a decision."""
    assert verdicts.is_adjudicated({"verdict": "   "}) is False


def test_a_status_of_adjudicated_counts_even_without_a_verdict_key() -> None:
    """Legacy briefs recorded the decision in `status` alone."""
    assert verdicts.is_adjudicated({"status": "adjudicated"}) is True


def test_gating_a_decided_brief_emits_the_regate_diagnostic() -> None:
    from mctl_core import briefs

    codes = [d.code for d in briefs.regate_diagnostics({"verdict": "approve"})]
    assert "MBRF_ADJUDICATED_REGATE" in codes


def test_gating_an_undecided_brief_emits_nothing() -> None:
    """Control: the guard must fire only on decided briefs."""
    from mctl_core import briefs

    assert briefs.regate_diagnostics({"status": "ready"}) == ()


def test_the_regate_diagnostic_is_an_error_not_a_warning() -> None:
    """A warning a caller may ignore is not a guard.

    The downstream consequence of ignoring it is a human verdict moved into
    `.pile/.rejected/` -- exactly the 8 measured losses this fix exists for.
    """
    from mctl_core import briefs
    from mctl_core.diagnostics import Severity

    (diagnostic,) = briefs.regate_diagnostics({"status": "adjudicated"})
    assert diagnostic.severity is Severity.ERROR
    assert diagnostic.policy_ref == "B2.2"
