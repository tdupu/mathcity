"""`check_silent_accumulators.py` had no test, which is the defect it detects.

THE FINDING THAT PRODUCED THIS FILE (2026-09-17 QC audit). The script was
shipped verified by hand against fixture cities and referenced in **zero** test
files. It is a DETECTOR: if it silently stops working, nothing reports that,
and its output is exactly the kind a reader trusts. An untested detector is the
same shape as the defects it exists to find.

WHAT IT DETECTS. A workflow dispatched to a pool that cannot staff it produces
no diagnostic at any layer -- not an order failure, not a stuck-bead hit, not a
`gc doctor` failure. It accumulates silently. kolchin carried 49 such workflows
holding 441 step beads, 67 of them completed before stopping.

THE TEST THAT MATTERS MOST is `test_empty_sweep_is_cannot_verify_not_pass`.
The script's first version scanned only `<city>/**/orders/` and reported OK on
the very city the incident happened in -- kolchin's orders resolve from the
source checkout and the import cache, not `~/HQ/orders`. It read zero files and
rendered that as a pass: P6.2, in the tool written to enforce P6.2 thinking. An
empty sweep must be CANNOT_VERIFY forever.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "assets" / "scripts" / "check_silent_accumulators.py"

OK, FOUND, CANNOT_VERIFY = 0, 1, 2


def _run(city: Path, *extra: str):
    r = subprocess.run(
        [sys.executable, str(SCRIPT), str(city), *extra],
        capture_output=True, text=True, timeout=60,
    )
    return r.returncode, r.stdout + r.stderr


def _city(tmp_path: Path, *, caps: str, orders: dict[str, str]) -> Path:
    city = tmp_path / "city"
    (city / "orders").mkdir(parents=True)
    (city / "city.toml").write_text(caps)
    for name, body in orders.items():
        (city / "orders" / name).write_text(body)
    return city


KOLCHIN_CAPS = """
[[pool]]
name = "mathcity.brief-operator"
max_active_sessions = 0

[[pool]]
dir = "mathcity"
name = "mathcity.brief-operator"
max_active_sessions = 0

[[pool]]
name = "healthy.pool"
max_active_sessions = 3
"""


def test_script_exists_and_is_executable():
    """P6.2: a check that could not fail must not render as passed."""
    assert SCRIPT.is_file(), f"{SCRIPT} is missing; every test below would skip vacuously"


def test_fires_on_the_kolchin_shape(tmp_path):
    """A capped pool that an enabled order targets is the live incident."""
    city = _city(tmp_path, caps=KOLCHIN_CAPS, orders={
        "brief-shuffle-on-submit.toml": '[order]\npool = "mathcity.brief-operator"\n',
        "fine.toml": '[order]\npool = "healthy.pool"\n',
    })
    rc, out = _run(city)
    assert rc == FOUND, out
    assert "FOUND" in out
    assert "mathcity.brief-operator" in out


def test_reads_both_cap_blocks_not_just_the_first(tmp_path):
    """kolchin carried TWO blocks named mathcity.brief-operator -- one city-level,
    one rig-scoped (`dir = "mathcity"`) -- with different justifications. Reading
    only the first sent an earlier repair at the wrong entry."""
    city = _city(tmp_path, caps=KOLCHIN_CAPS, orders={
        "o.toml": '[order]\npool = "mathcity.brief-operator"\n'})
    rc, out = _run(city)
    assert rc == FOUND
    assert "(city)" in out and "mathcity" in out, (
        "both the city-level and the rig-scoped cap block must be reported")


def test_empty_sweep_is_cannot_verify_not_pass(tmp_path):
    """THE REGRESSION GUARD. A sweep that read nothing cannot clear anything."""
    city = tmp_path / "city"
    city.mkdir()
    (city / "city.toml").write_text(KOLCHIN_CAPS)
    rc, out = _run(city, "--root", str(tmp_path / "nonexistent"))
    assert rc == CANNOT_VERIFY, out
    assert "CANNOT VERIFY" in out
    assert "NOT a pass" in out


def test_healthy_city_stays_quiet(tmp_path):
    """A detector that always fires is worth nothing."""
    city = _city(tmp_path, caps='[[pool]]\nname = "a"\nmax_active_sessions = 3\n',
                 orders={"x.toml": '[order]\npool = "a"\n'})
    rc, out = _run(city)
    assert rc == OK, out
    assert "OK" in out


def test_capped_pool_nobody_targets_is_not_a_finding(tmp_path):
    """A cap with no order aimed at it strands nothing."""
    city = _city(tmp_path, caps=KOLCHIN_CAPS, orders={
        "x.toml": '[order]\npool = "healthy.pool"\n'})
    rc, out = _run(city)
    assert rc == OK, out


def test_disabled_order_does_not_count(tmp_path):
    """An order that cannot fire cannot strand work."""
    city = _city(tmp_path, caps=KOLCHIN_CAPS, orders={
        "off.toml": '[order]\nenabled = false\npool = "mathcity.brief-operator"\n'})
    rc, out = _run(city)
    assert rc == OK, out


def test_missing_city_toml_is_cannot_verify(tmp_path):
    """Absence of a city is not a healthy city."""
    empty = tmp_path / "nocity"
    empty.mkdir()
    rc, out = _run(empty)
    assert rc == CANNOT_VERIFY, out
