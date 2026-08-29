"""mc-dhsgo: `stale` is blind to a checkout that is itself behind the remote.

`DashboardInstance.stale` compares the PROCESS against ITS CHECKOUT. It answers
"is this server running the code that is checked out" -- not "is this server
running current code". A dashboard faithfully serving a checkout nobody pulled
reports `stale: false` while rendering old code.

MEASURED 2026-08-29: a live instance reported `stale: false, staleness_known:
true` while its checkout sat 1 commit behind `origin/main`; a second checkout
was 40 behind at the same moment. The operator noticed before the instrument
did -- "that was an old dashboard" -- which is the definition of a blind probe.

WHY A SECOND FIELD RATHER THAN A BETTER `stale`. Re-basing `stale` on the remote
would change the meaning of a field callers already branch on, and would make
`stale: true` unfixable by `dashboard_restart` -- the remedy would become a pull,
which mctl does not own. So the missing fact is published beside it.

THE INVARIANT THESE TESTS EXIST TO PIN. `None` and `0` mean different things and
must never collapse:

    None -> the ref did not resolve; we do not know      (checkout_freshness_known False)
    0    -> level with the ref ON DISK                   (NOT proof of freshness -- nothing fetches)

A `0` returned from a failed lookup is the plausible-looking wrong answer P6.2
forbids, and is the specific bug this fix must not introduce while fixing the
other one.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import serving
from mctl_core.dashboards import DashboardInstance


def _instance(**overrides) -> DashboardInstance:
    base = dict(
        pid=1234,
        host="127.0.0.1",
        port=8471,
        url="http://127.0.0.1:8471",
        rig="mathcity",
        serving_commit="abc1234",
        started_at="2026-08-29T00:00:00Z",
    )
    base.update(overrides)
    return DashboardInstance(**base)


# --- the defect itself ------------------------------------------------------


def test_stale_is_false_while_the_checkout_is_behind_the_remote() -> None:
    """The exact live reading that motivated mc-dhsgo, reproduced as a unit.

    Process matches its checkout, so `stale` is correctly False -- and the
    dashboard is nevertheless serving code 40 commits old. Both statements are
    true at once, which is why one boolean could never carry them.
    """
    inst = _instance(
        serving_commit="778509c",
        current_commit="778509c",
        remote_commit="f66b5d8",
        checkout_behind_remote=40,
    )
    assert inst.stale is False
    assert inst.staleness_known is True
    assert inst.checkout_behind_remote == 40
    assert inst.checkout_freshness_known is True


def test_the_two_axes_are_independent() -> None:
    """A process can be stale AND its checkout current, or neither, or both."""
    stale_but_current_checkout = _instance(
        serving_commit="old1111", current_commit="new2222",
        remote_commit="new2222", checkout_behind_remote=0,
    )
    assert stale_but_current_checkout.stale is True
    assert stale_but_current_checkout.checkout_behind_remote == 0


# --- the invariant a naive fix breaks --------------------------------------


def test_unknown_freshness_is_none_never_zero() -> None:
    """An unresolvable ref must NOT read as 'up to date'."""
    inst = _instance(current_commit="abc1234", remote_commit=None, checkout_behind_remote=None)
    assert inst.checkout_behind_remote is None
    assert inst.checkout_freshness_known is False
    assert inst.to_dict()["checkout_behind_remote"] is None


def test_zero_is_a_real_measurement_and_reports_as_known() -> None:
    """Level-with-the-ref is a fact we established, not a lookup we skipped."""
    inst = _instance(current_commit="f66b5d8", remote_commit="f66b5d8", checkout_behind_remote=0)
    assert inst.checkout_behind_remote == 0
    assert inst.checkout_freshness_known is True


def test_payload_carries_all_three_new_keys() -> None:
    """Schema stability: the keys are always present, null when unset."""
    payload = _instance().to_dict()
    for key in ("remote_commit", "checkout_behind_remote", "checkout_freshness_known"):
        assert key in payload, key
    assert payload["checkout_behind_remote"] is None
    assert payload["checkout_freshness_known"] is False


def test_stale_semantics_are_unchanged() -> None:
    """Regression guard: existing callers branch on `stale`; do not move it."""
    assert _instance(serving_commit="a", current_commit="b").stale is True
    assert _instance(serving_commit="a", current_commit="a").stale is False
    assert _instance(serving_commit=None, current_commit="a").stale is False
    assert _instance(serving_commit="a", current_commit=None).stale is False


# --- the readers, against a real git repo -----------------------------------


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_readers_measure_a_real_behind_count(tmp_path: Path) -> None:
    """Drive the git reads against an actual repository, not a mock.

    A mock would prove the plumbing and not that the git invocation is right,
    and the invocation is the part that can be wrong.
    """
    origin = tmp_path / "origin"
    origin.mkdir()
    _git(origin, "init", "--initial-branch=main")
    _git(origin, "config", "user.email", "t@example.com")
    _git(origin, "config", "user.name", "t")
    (origin / "f.txt").write_text("one", encoding="utf-8")
    _git(origin, "add", "f.txt")
    _git(origin, "commit", "-m", "one")

    clone = tmp_path / "clone"
    subprocess.run(["git", "clone", str(origin), str(clone)], check=True, capture_output=True)

    # Level with the ref: a real zero.
    assert serving.read_behind_remote(clone) == 0
    assert serving.read_remote_commit(clone) is not None

    # Two commits land upstream and the clone fetches them, but does not merge.
    for text in ("two", "three"):
        (origin / "f.txt").write_text(text, encoding="utf-8")
        _git(origin, "commit", "-am", text)
    _git(clone, "fetch", "origin")

    assert serving.read_behind_remote(clone) == 2


def test_readers_return_none_when_the_ref_is_absent(tmp_path: Path) -> None:
    """A repo with no `origin/main` yields None, not 0."""
    solo = tmp_path / "solo"
    solo.mkdir()
    _git(solo, "init", "--initial-branch=main")
    _git(solo, "config", "user.email", "t@example.com")
    _git(solo, "config", "user.name", "t")
    (solo / "f.txt").write_text("x", encoding="utf-8")
    _git(solo, "add", "f.txt")
    _git(solo, "commit", "-m", "x")

    assert serving.read_remote_commit(solo) is None
    assert serving.read_behind_remote(solo) is None


def test_readers_return_none_for_a_non_repository(tmp_path: Path) -> None:
    """Not a git repo is unknowable, not zero."""
    plain = tmp_path / "plain"
    plain.mkdir()
    assert serving.read_remote_commit(plain) is None
    assert serving.read_behind_remote(plain) is None


def test_the_diagnostic_code_is_registered() -> None:
    """#199: a code emitted but absent from the registry is unexplainable."""
    registry = (REPO_ROOT / "assets" / "mctl" / "diagnostics.toml").read_text(encoding="utf-8")
    assert "[MDSH_CHECKOUT_BEHIND_REMOTE]" in registry
