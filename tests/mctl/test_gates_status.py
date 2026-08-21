"""#119a — `gates_status` static surface, with statistics explicitly Unknown.

HOW THIS TEST COULD HAVE FAILED (required by handoff §6):

The whole point of this slice is the handoff's own sentence — an itemized
evaluation list "is the only way to distinguish a gate that never fails from one
that never runs."  This city records **no gate outcome anywhere** (measured
2026-08-20: no `gate_id` in mctl_core; bead metadata carries `gc.check_path` /
`gc.check_mode` / `gc.check_timeout`, which is *what to run*, never a result; the
mctl event and trace sinks hold 0 files).

So the failure this test exists to catch is the tempting one: computing
`evaluated`/`passed` from an absent source and emitting `0`.  That renders a gate
that never ran identically to a gate that never failed, and would fire
`suspect: true` on all five gates at once — the exact defect the slice was
commissioned to expose, committed by the slice.

`test_statistics_are_unknown_never_zero` fails if any statistic is `0` rather than
`None`, and `test_suspect_is_unknown_not_true` fails if `suspect` is asserted from
no data.  Both fail against a naive implementation; both would pass vacuously if
the module simply returned no gates at all, which is why
`test_static_fields_are_populated` asserts a non-empty gate set first — that is the
control.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

# NOT `pytest.importorskip`. The first draft of this file used it, and a missing
# `mctl_core.gates` reported "1 skipped" — a green suite for a module that does
# not exist. importorskip is for optional dependencies; this is the module under
# test, and its absence must be a failure. Caught on the first red-first run,
# which is the only reason it is not still here.
from mctl_core import gates  # noqa: E402


def _rows(tmp_gates_dir):
    return gates.gates_status(gates_dir=tmp_gates_dir).gates


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def gates_dir(tmp_path):
    """Copied from REAL gate definitions, never hand-written.

    The first draft invented a `[gate] id/rule_id` + `[[checks]]` schema. The
    parser was written to match the invention, both were green, and all five
    real gates returned `checks=0, rule_id=None`. A fixture that does not come
    from the artifact tests the author's belief about the artifact.

    `test-evidence` has 1 check, `test-execution` has 2 — measured from the real
    files, which is what makes the count assertions below meaningful.
    """
    d = tmp_path / "gates"
    d.mkdir()
    for name in ("test-evidence.toml", "test-execution.toml"):
        source = REPO_ROOT / "gates" / name
        if not source.is_file():  # pragma: no cover - guards fixture rot
            pytest.fail(f"fixture source missing: {source}")
        shutil.copy(source, d / name)
    return d


# --- CONTROL -----------------------------------------------------------------
# If this fails the fixture is not exercising anything and every assertion below
# would pass vacuously over an empty list.
def test_static_fields_are_populated(gates_dir):
    rows = _rows(gates_dir)
    assert len(rows) == 2, "control: the fixture's gates must be discovered"
    by_id = {r.gate_id: r for r in rows}
    assert set(by_id) == {"test-evidence", "test-execution"}
    assert by_id["test-execution"].checks == 2
    assert by_id["test-evidence"].checks == 1
    assert by_id["test-evidence"].registered_at is not None


# --- THE HONESTY INVARIANT ---------------------------------------------------
def test_statistics_are_unknown_never_zero(gates_dir):
    """§5: a failed probe never renders as a value — not zero, not blank."""
    for row in _rows(gates_dir):
        for field in ("evaluated", "passed", "beads_failing_now"):
            value = getattr(row, field)
            assert value is None, (
                f"{row.gate_id}.{field} is {value!r}; with no evaluation record in "
                "the city it must be None (Unknown), never 0 — 0 would render a "
                "gate that never ran as a gate that never failed"
            )


def test_suspect_is_unknown_not_true(gates_dir):
    """`suspect` means 'zero failures over a long window'. No window, no claim."""
    for row in _rows(gates_dir):
        assert row.suspect is None, (
            f"{row.gate_id}.suspect is {row.suspect!r}; asserting suspicion from an "
            "absent evaluation record is the defect this slice exposes"
        )


def test_unknown_statistics_carry_a_registered_diagnostic(gates_dir):
    """Unknown must be explained, loudly, with a next command (§6)."""
    report = gates.gates_status(gates_dir=gates_dir)
    codes = [d.code for d in report.diagnostics]
    assert "MGATE001" in codes, f"expected MGATE001 explaining Unknown, got {codes}"
    diag = next(d for d in report.diagnostics if d.code == "MGATE001")
    assert diag.suggested_next_command, "an Unknown must tell the operator what to run"


def test_absent_gates_dir_is_unknown_not_empty(tmp_path):
    """§5: `None` = there is none. `Unknown` = we did not look. Never collapse them.

    An unreadable gates directory must NOT render as 'this city has no gates'.
    """
    report = gates.gates_status(gates_dir=tmp_path / "does-not-exist")
    codes = [d.code for d in report.diagnostics]
    assert "MGATE002" in codes, (
        f"an unresolvable gates dir must emit MGATE002, got {codes}; returning an "
        "empty list would be indistinguishable from a city with no gates"
    )
    assert report.gates_readable is False
