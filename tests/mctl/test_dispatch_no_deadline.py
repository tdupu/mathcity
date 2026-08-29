"""mc-vtru8 — the dispatch has no deadline, and says how long it is taking.

End-to-end, through the real CLI, against a real (deliberately slow) `gc` shim.
The unit tests in `test_elapsed_supervision.py` pin the helper; these pin the
behaviour an operator actually gets from `mctl work dispatch`.

Taylor's verdict, recorded on mc-vtru8: *"We shouldn't have a dispatch timeout.
So yes, if we raise the dispatch timeout to infinity and replace it with a
warning. This would be A'+C', D'"* and *"There should also be a surface for
adjusting the timeout size."*

P6.2 is the reason these drive a slow subprocess rather than assert on constants.
The warning REPLACES a check, so a warn path that never emits is indistinguishable
from a dispatch that was never slow -- and an unfirable check is worse than an
absent one. Every assertion below reads the elapsed value out of output the city
actually produced.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_dispatch_kill_switch import (  # noqa: E402
    APPROVED_BRIEF,
    MCTL,
    REPO_ROOT,
    gc_calls,
    provenance_files,
    runtime,
)


def dispatch(
    city_root: Path,
    rig_root: Path,
    bin_dir: Path,
    *,
    warn_after: str | None = None,
    deadline: str | None = None,
    use_flags: bool = False,
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
    env["MCTL_ENABLE_LIVE_DISPATCH"] = "1"
    env.pop("MCTL_DISPATCH_DEADLINE_SECONDS", None)
    env.pop("MCTL_DISPATCH_WARN_AFTER_SECONDS", None)
    argv = [
        sys.executable, str(MCTL), "work", "dispatch", APPROVED_BRIEF,
        "--city", str(city_root), "--rig", "mathcity", "--json",
    ]
    if use_flags:
        if warn_after is not None:
            argv += ["--warn-after-seconds", warn_after]
        if deadline is not None:
            argv += ["--deadline-seconds", deadline]
    else:
        if warn_after is not None:
            env["MCTL_DISPATCH_WARN_AFTER_SECONDS"] = warn_after
        if deadline is not None:
            env["MCTL_DISPATCH_DEADLINE_SECONDS"] = deadline
    return subprocess.run(
        argv, cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env
    )


def still_running_lines(stderr: str) -> list[str]:
    return [line for line in stderr.splitlines() if "has not returned yet" in line]


def diagnostics(payload: str) -> list[dict[str, object]]:
    return list(json.loads(payload).get("diagnostics", []))


def codes(payload: str) -> list[str]:
    return [str(row.get("code")) for row in diagnostics(payload)]


# --- part 2: the warning is OBSERVED to fire, with its elapsed value ----------


def test_a_slow_dispatch_reports_elapsed_while_it_is_still_running(tmp_path: Path):
    """The P6.2 test the verdict requires: a real slow sling, a real warning.

    The sling sleeps 1.2s; the warn threshold is 0.2s. Nothing is bounded, so the
    dispatch completes normally -- and while it was running, the city said how
    long it had been running, repeatedly, on stderr where a human waiting on it
    can see it.
    """
    city_root, rig_root, bin_dir, gc_log = runtime(tmp_path, sling_delay=1.2)
    started = time.monotonic()
    result = dispatch(city_root, rig_root, bin_dir, warn_after="0.2")
    wall = time.monotonic() - started

    assert result.returncode == 0, result.stderr
    live = still_running_lines(result.stderr)
    assert live, (
        "a 1.2s dispatch under a 0.2s warn threshold emitted no live warning; the "
        f"signal that replaced the deadline is unfirable (P6.2). stderr:\n{result.stderr}"
    )
    assert len(live) >= 2, f"the report must repeat while the call runs: {live}"

    # Each named an ELAPSED time, and every one of them lands inside the call --
    # which is what makes them reports from DURING the dispatch rather than after.
    elapsed_values = [
        float(line.split("has been running ")[1].split("s and")[0]) for line in live
    ]
    assert all(0.0 < value < wall for value in elapsed_values), (elapsed_values, wall)
    assert elapsed_values == sorted(elapsed_values)
    assert all("no deadline is set" in line for line in live)
    assert all("not a failure" in line for line in live)

    # The sling really ran, really landed, and was never killed.
    assert [call for call in gc_calls(gc_log) if call[:1] == ["sling"]]
    assert provenance_files(rig_root)
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    assert "MWRK_DISPATCH_STILL_RUNNING" in codes(result.stdout)


def test_a_fast_dispatch_reports_nothing(tmp_path: Path):
    """Negative control (P6.2): the same check must be capable of NOT firing.

    Without this, a warning emitted on every dispatch would satisfy the test above
    while telling an operator nothing about whether this one was slow.
    """
    city_root, rig_root, bin_dir, _ = runtime(tmp_path, sling_delay=0.0)
    result = dispatch(city_root, rig_root, bin_dir, warn_after="30")

    assert result.returncode == 0, result.stderr
    assert still_running_lines(result.stderr) == []
    assert "MWRK_DISPATCH_STILL_RUNNING" not in codes(result.stdout)
    assert "MWRK_DISPATCH_SLOW" not in codes(result.stdout)


def test_a_dispatch_that_outlives_every_default_threshold_is_not_killed(tmp_path: Path):
    """Part 1: with no deadline the sling runs to completion, however long it takes.

    The old code would have killed this at its budget; the whole verdict is that
    it must not. 1.2s of sling against a 0.2s warn threshold is, proportionally, a
    dispatch running 6x past the point where the old bound would have fired.
    """
    city_root, rig_root, bin_dir, gc_log = runtime(tmp_path, sling_delay=1.2)
    started = time.monotonic()
    result = dispatch(city_root, rig_root, bin_dir, warn_after="0.2")
    elapsed = time.monotonic() - started

    assert result.returncode == 0, result.stderr
    assert elapsed >= 1.2, "the dispatch returned before its own subprocess finished"
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    assert payload["claim"] == "observed"
    assert "MWRK_DISPATCH_TIMEOUT_UNKNOWN" not in codes(result.stdout)
    assert [call for call in gc_calls(gc_log) if call[:1] == ["sling"]]


# --- part 3: the operator surface, and what it is NOT allowed to claim --------


def test_an_operator_set_bound_expires_as_UNKNOWN_never_as_applied_false(tmp_path: Path):
    """The #184 contract, verified through the surface that can still reach it.

    POLICY P6.3 cites `MWRK_DISPATCH_TIMEOUT_UNKNOWN` as the in-house compliant
    reference, and `DispatchFailureVerdict.applied=None` -- "cannot tell" -- is
    the #184 fix. Collapsing it to False tells a caller a retry is safe when it
    may not be. An operator-set bound expiring must land on exactly that path.
    """
    city_root, rig_root, bin_dir, gc_log = runtime(tmp_path, sling_delay=30.0)
    started = time.monotonic()
    result = dispatch(city_root, rig_root, bin_dir, deadline="0.6")
    elapsed = time.monotonic() - started

    assert elapsed < 25.0, "the operator's bound did not actually abandon the sling"
    assert result.returncode == 1
    combined = result.stdout + result.stderr
    assert "MWRK_DISPATCH_TIMEOUT_UNKNOWN" in combined
    assert "UNKNOWN" in combined

    # `applied` is never asserted False here, and the payload must not say so.
    if result.stdout.strip():
        payload = json.loads(result.stdout)
        assert payload.get("applied") is not True
    assert "no dispatch was recorded" not in combined, (
        "an expired bound claimed the dispatch did not happen -- that is a claim "
        "about the world derived from how long we waited (#184)"
    )
    # It ran. That is exactly why the outcome is unknown rather than false.
    assert [call for call in gc_calls(gc_log) if call[:1] == ["sling"]]
    assert "ran " in combined and "s against an operator-set" in combined, (
        "P6.3(b): expiry must report ELAPSED"
    )


def test_the_expiring_bound_warned_beneath_itself_first(tmp_path: Path):
    """P6.3(a): no deadline without a warn threshold strictly below it.

    The operator sets only the bound; the warn threshold is derived beneath it, so
    a bound cannot be configured into existence without its early signal.
    """
    city_root, rig_root, bin_dir, _ = runtime(tmp_path, sling_delay=30.0)
    result = dispatch(city_root, rig_root, bin_dir, deadline="0.8")

    live = still_running_lines(result.stderr)
    assert live, f"a bound expired with no warning beneath it. stderr:\n{result.stderr}"
    assert "an operator-set deadline of 0.8s applies" in live[0]


def test_the_cli_flag_sets_the_bound_too(tmp_path: Path):
    """`--deadline-seconds` is the per-call half of the surface Taylor asked for."""
    city_root, rig_root, bin_dir, _ = runtime(tmp_path, sling_delay=30.0)
    result = dispatch(city_root, rig_root, bin_dir, deadline="0.6", use_flags=True)

    assert result.returncode == 1
    assert "MWRK_DISPATCH_TIMEOUT_UNKNOWN" in result.stdout + result.stderr


def test_a_bound_below_the_measured_sling_cost_is_reported_back(tmp_path: Path):
    """#181's subject, on the surface that inherited it.

    200s was a shipped budget that killed a 243.51s dispatch. An operator who sets
    it today is told what that number does -- and the bound is still applied,
    because it is theirs.
    """
    city_root, rig_root, bin_dir, _ = runtime(tmp_path, sling_delay=0.0)
    result = dispatch(city_root, rig_root, bin_dir, deadline="200")

    assert result.returncode == 0, result.stderr
    assert "MWRK_DISPATCH_OPERATOR_BOUND" in codes(result.stdout)
    detail = " ".join(
        str(row.get("facts", {}).get("detail", "")) for row in diagnostics(result.stdout)
    )
    assert "cannot succeed" in detail and "243.51" in detail


def test_a_generous_bound_is_not_reported_back(tmp_path: Path):
    """Negative control: the operator-bound report must be capable of NOT firing."""
    city_root, rig_root, bin_dir, _ = runtime(tmp_path, sling_delay=0.0)
    result = dispatch(city_root, rig_root, bin_dir, deadline="600")

    assert result.returncode == 0, result.stderr
    assert "MWRK_DISPATCH_OPERATOR_BOUND" not in codes(result.stdout)
