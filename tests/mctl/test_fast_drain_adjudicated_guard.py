"""A decided brief must survive the fast-drain's gates (mc-8ehd0).

`evaluate()` returns a non-empty `error` for a standard-profile brief with no
provenance metadata, and its caller `process_item()` then reaches
`reject_staged()`, which moves the file into `.pile/.rejected/`. Measured
2026-08-28 against the live city: 24 rejected briefs, **8** carrying a verdict
(7 approve + 1 reject, all `status: adjudicated`), 22 of the 24 rejected for
"standard brief missing provenance metadata". Those 8 are human decisions the
machine discarded.

The two CONTROLS below are load-bearing. The failure mode of this guard is that
it becomes always-true and the gate stops rejecting anything, at which point the
guard's own tests would still pass while the gate had been destroyed. P6.2 -- a
check that could not have failed must not render as a check that passed.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

# Loaded by path, not imported: the module's filename has hyphens in it, so it
# is not a legal module name. This is the same file the scheduled order runs
# (orders/brief-shuffle-fast-drain-city.toml) -- not a copy of it.
_SPEC = importlib.util.spec_from_file_location(
    "fast_drain", REPO_ROOT / "assets" / "scripts" / "brief-shuffle-fast-drain.py"
)
fast_drain = importlib.util.module_from_spec(_SPEC)
# Registered BEFORE exec: the module defines a @dataclass, and dataclasses
# resolves annotations via `sys.modules[cls.__module__]`, which is None for a
# module still being built. Same order as `load_drain_module()` in
# tests/brief-shuffle-fast-drain/.
sys.modules[_SPEC.name] = fast_drain
_SPEC.loader.exec_module(fast_drain)

GATE_CONFIG = {
    "registry": {"default_profile": "standard"},
    "profiles": {"standard": {"gates": []}},
}


def _brief(tmp_path: Path, front: str) -> Path:
    path = tmp_path / "brief.md"
    path.write_text(f"---\n{front}---\n\n## Gate Evidence\n\nnone\n", encoding="utf-8")
    return path


def test_an_undecided_brief_without_provenance_is_still_rejected(tmp_path: Path) -> None:
    """CONTROL. The gate must keep working -- this is not a licence to pass."""
    path = _brief(tmp_path, "slug: x\ngate_profile: standard\n")
    _profile, error, _meta, _fail = fast_drain.evaluate(path, GATE_CONFIG)
    assert error == "standard brief missing provenance metadata"


def test_an_adjudicated_brief_without_provenance_is_NOT_rejected(tmp_path: Path) -> None:
    """The defect: a human said approve and the gate threw it away."""
    path = _brief(tmp_path, "slug: x\ngate_profile: standard\nverdict: approve\n")
    _profile, error, _meta, _fail = fast_drain.evaluate(path, GATE_CONFIG)
    assert not error


def test_a_status_adjudicated_brief_is_NOT_rejected(tmp_path: Path) -> None:
    """All 8 stranded briefs carry `status: adjudicated`."""
    path = _brief(tmp_path, "slug: x\ngate_profile: standard\nstatus: adjudicated\n")
    _profile, error, _meta, _fail = fast_drain.evaluate(path, GATE_CONFIG)
    assert not error


def test_an_empty_verdict_does_not_buy_a_pass(tmp_path: Path) -> None:
    """CONTROL. `verdict:` with nothing after it is an ABSENT verdict."""
    path = _brief(tmp_path, "slug: x\ngate_profile: standard\nverdict:   \n")
    _profile, error, _meta, _fail = fast_drain.evaluate(path, GATE_CONFIG)
    assert error == "standard brief missing provenance metadata"


def test_the_guard_makes_the_caller_promote_rather_than_reject(tmp_path: Path) -> None:
    """The invariant, at the layer that performs the move.

    `evaluate()` returning a falsy error is only half the claim; what matters is
    that `process_item()` -- the function that calls `reject_staged()` -- takes
    the promote branch. Asserting on `evaluate()`'s return alone would still
    pass if the caller treated the sentinel as a rejection.
    """
    decided = _brief(tmp_path, "slug: decided\ngate_profile: standard\nverdict: approve\n")
    outcome = fast_drain.process_item(decided, tmp_path, GATE_CONFIG, apply=False)
    assert outcome.action == "promote"


def test_the_caller_still_rejects_an_undecided_brief(tmp_path: Path) -> None:
    """CONTROL, at the same layer. The reject path must remain reachable."""
    undecided = _brief(tmp_path, "slug: undecided\ngate_profile: standard\n")
    outcome = fast_drain.process_item(undecided, tmp_path, GATE_CONFIG, apply=False)
    assert outcome.action == "reject"
    assert outcome.reason == "standard brief missing provenance metadata"


def test_fast_drain_guard_matches_mctl_core() -> None:
    """Two copies of one rule must not drift (the script cannot import mctl_core)."""
    from mctl_core.verdicts import is_adjudicated

    for front in (
        {"verdict": "approve"},
        {"status": "adjudicated"},
        {"verdict": "   "},
        {"status": "ready"},
        {},
    ):
        assert fast_drain._is_adjudicated(front) == is_adjudicated(front), front


@pytest.mark.xfail(
    strict=True,
    reason="mc-8ehd0 residual hole: the duplicate-stack-slug path still rejects a "
    "decided brief. Measured, not inferred -- see the docstring below.",
)
def test_an_adjudicated_brief_with_a_duplicate_slug_is_still_not_rejected(
    tmp_path: Path,
) -> None:
    """The plan's invariant is NOT yet fully established, and this records it.

    The plan states the invariant as "no code path moves a brief carrying a
    verdict into `.pile/.rejected/`", and its Task 4 interface claims the
    caller "never reaches reject_staged". That is true for the gate-failure
    path this fix closes, and FALSE for one other: `process_item()` overrides
    a promote with

        action = "reject"; reason = "duplicate stack slug"

    when `stack/<slug>.md` already exists -- after `evaluate()` has already
    approved the item. A decided brief re-entering `.pile/` while a copy sits
    in the stack is therefore still moved into `.pile/.rejected/`.

    Measured 2026-08-28 with exactly this fixture: `evaluate()` returns `''`
    (no error) and `process_item()` returns `reject / duplicate stack slug`.

    Left xfail(strict) rather than fixed here on purpose. The remedy is a
    judgement call the guard's author should not make alone: "skip and leave
    it in `.pile/`" risks the item being re-processed on every scheduled run
    forever, and the plan's own rule -- leave it where it is and ESCALATE --
    has no escalation sink in this script today. strict=True means this test
    FAILS the moment someone closes the hole, forcing the marker to be removed
    rather than silently outliving the defect.
    """
    (tmp_path / "stack").mkdir()
    (tmp_path / "stack" / "dupe.md").write_text("already here\n", encoding="utf-8")
    decided = _brief(tmp_path, "slug: dupe\ngate_profile: standard\nverdict: approve\n")
    decided = decided.rename(tmp_path / "dupe.md")
    outcome = fast_drain.process_item(decided, tmp_path, GATE_CONFIG, apply=False)
    assert outcome.action != "reject"
