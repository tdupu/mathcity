"""`city.toml` edited by hand rather than by a pack update — P1.2.

THE FINDING (2026-09-17 QC audit). kolchin's `~/HQ` holds 22 `city.toml.bak-*`
files. Four came from provider_set's typed write path. **Eighteen predate it**,
dated Sep 6-8, each named for the hand-edit that produced it:

    bak-poolraise  bak-poolraise2  bak-poolcap    bak-poolzero
    bak-agexswitch bak-providerfix bak-fixsession bak-latchlivelock
    bak-srccheckout bak-rigpath    bak-preplin    bak-briefopcap ...

P1.2: "Changes to city behavior go through `gc import add` / `[imports.*]`
entries + `gc import install` -- never a one-off hand-edit to `city.toml`."

So the backup trail is a forensic record of roughly eighteen P1.2 violations,
left by agents doing the responsible thing (backing up) while doing the
forbidden thing (hand-editing). **Nothing enforces P1.2**, which is why they
accumulated visibly over three days without anyone stopping.

TWO SIGNALS, and they answer different questions:

  mtime      city.toml newer than the last `gc import install` -> a write
             happened outside the import path. Catches the CURRENT state.
  backups    city.toml.bak-* count and names -> the HISTORY of hand-edits,
             including ones since overwritten.

The second is what made the eighteen visible at all. A detector reading only
mtime would have reported one violation, not eighteen.

RETENTION. Even the compliant path accumulates: provider_set writes a backup
per apply and nothing ever reaps them. Unbounded growth of a forensic artifact
eventually buries the signal it carries.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "assets" / "scripts" / "check_config_handedits.py"

OK, FOUND, CANNOT_VERIFY = 0, 1, 2


def _run(city: Path, *extra: str):
    r = subprocess.run([sys.executable, str(SCRIPT), str(city), *extra],
                       capture_output=True, text=True, timeout=60)
    return r.returncode, r.stdout + r.stderr


def _city(tmp_path: Path, *, backups=(), install_age=None) -> Path:
    city = tmp_path / "city"
    city.mkdir()
    (city / "city.toml").write_text('[workspace]\nprovider = "a"\n')
    for b in backups:
        (city / f"city.toml.bak-{b}").write_text("old")
    if install_age is not None:
        marker = city / "packs.lock"
        marker.write_text("locked")
        t = time.time() - install_age
        import os
        os.utime(marker, (t, t))
    return city


def test_script_exists():
    assert SCRIPT.is_file(), f"{SCRIPT} missing -- tests below would be vacuous"


def test_backup_trail_is_counted_as_history_not_just_current_state(tmp_path):
    """The eighteen were visible only as a trail; mtime alone shows one."""
    city = _city(tmp_path, backups=("poolraise", "agexswitch", "poolcap"))
    rc, out = _run(city)
    assert rc == FOUND, out
    assert "3" in out, "must report the COUNT of historical hand-edits"


def test_typed_writes_are_distinguished_from_hand_edits(tmp_path):
    """provider_set's backups are named `bak-provider-*` and are the compliant
    path. Counting them as violations would defame the fix."""
    city = _city(tmp_path, backups=("provider-20260915-074516",
                                    "provider-20260915-075305"))
    rc, out = _run(city)
    assert rc == OK, out
    assert "typed" in out.lower() or "compliant" in out.lower()


def test_mixed_trail_reports_only_the_hand_edits(tmp_path):
    city = _city(tmp_path, backups=("poolraise", "provider-20260915-074516",
                                    "agexswitch"))
    rc, out = _run(city)
    assert rc == FOUND, out
    assert "2" in out, "two hand-edits, one typed write"


def test_clean_city_stays_quiet(tmp_path):
    city = _city(tmp_path)
    rc, out = _run(city)
    assert rc == OK, out


def test_missing_city_toml_is_cannot_verify(tmp_path):
    """Absence of a city is not a compliant city."""
    d = tmp_path / "nothing"
    d.mkdir()
    rc, out = _run(d)
    assert rc == CANNOT_VERIFY, out
    assert "NOT a pass" in out


def test_retention_reports_what_it_would_reap_without_reaping(tmp_path):
    """Read-only by default: a detector that deletes is not a detector."""
    city = _city(tmp_path, backups=tuple(f"provider-2026090{i}-000000" for i in range(1, 9)))
    before = len(list(city.glob("city.toml.bak-*")))
    rc, out = _run(city, "--retention", "3")
    after = len(list(city.glob("city.toml.bak-*")))
    assert after == before, "the detector must not delete anything"
    assert "would reap" in out.lower() or "reap" in out.lower()
