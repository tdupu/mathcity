"""The brief pipeline outage of 2026-10-08: `--readonly` on a proxied store.

Gas City 1.5 moves every city and rig onto bd's `proxied-server` Dolt backend.
bd REFUSES `--readonly` there -- deliberately, not as a gap:

    strict readonly is unavailable for dolt proxied-server backend; refusing to
    open a store that cannot guarantee mutation-free access

There is no non-strict variant of the flag to fall back to. `BD_LIST_ARGS` has
always passed `--readonly`, so the moment `gc beads city migrate-proxied` ran
(2026-10-08 ~16:53) EVERY mctl bead read began raising `BeadReadError`, and the
brief pipeline stayed down for two days.

The fix gates the flag rather than dropping it. Dropping it everywhere would
surrender the mutation guard on the stores where bd CAN still honour it -- which
is most of them. So: omit it on a proxied store, keep it everywhere else.

Two details this pins, both of which broke a first attempt at the fix:

1. **bd reports the refusal on STDOUT, not stderr.** Exit is 1, stderr is
   EMPTY, and the error arrives as a JSON object on stdout carrying the stable
   code `proxy.readonly.unsupported`. A retry that inspected stderr -- the
   obvious place -- never fired. Measured against
   ~/gt/gascity-packs-briefpath, 2026-10-10.

2. **metadata.json can be wrong.** That same store declared
   `dolt_mode=server` while its database was already migrated, because it is a
   second path onto a store another scope had migrated. The file is a hint; bd's
   refusal is authoritative. So the gate reads the file, and the retry recovers
   when the file turns out to have lied.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
import mctl_core.beads as beads  # noqa: E402


REFUSAL_STDOUT = json.dumps(
    {
        "code": "proxy.readonly.unsupported",
        "error": (
            "strict readonly is unavailable for dolt proxied-server backend; "
            "refusing to open a store that cannot guarantee mutation-free access"
        ),
        "mutates": False,
    }
)


def _store(tmp_path: Path, dolt_mode: str | None) -> Path:
    root = tmp_path / "rig"
    (root / ".beads").mkdir(parents=True)
    if dolt_mode is not None:
        (root / ".beads" / "metadata.json").write_text(
            json.dumps({"dolt_mode": dolt_mode}), encoding="utf-8"
        )
    beads._readonly_args_cache.clear()
    return root


def _completed(returncode: int, stdout: str, stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=[], returncode=returncode, stdout=stdout, stderr=stderr)


def test_proxied_store_omits_readonly(tmp_path: Path) -> None:
    assert beads.bd_readonly_args(_store(tmp_path, "proxied-server")) == ()


def test_non_proxied_store_keeps_the_guard(tmp_path: Path) -> None:
    assert beads.bd_readonly_args(_store(tmp_path, "server")) == ("--readonly",)


def test_unclassifiable_store_keeps_the_guard(tmp_path: Path) -> None:
    """No metadata must not mean no guard -- fail toward the stricter read."""
    assert beads.bd_readonly_args(_store(tmp_path, None)) == ("--readonly",)
    root = _store(tmp_path / "bad", "server")
    (root / ".beads" / "metadata.json").write_text("{not json", encoding="utf-8")
    beads._readonly_args_cache.clear()
    assert beads.bd_readonly_args(root) == ("--readonly",)


def test_refusal_on_stdout_triggers_one_retry_without_readonly(tmp_path: Path, monkeypatch) -> None:
    """The regression that matters: empty stderr, JSON refusal on stdout."""
    root = _store(tmp_path, "server")  # the file LIES; the store is really proxied
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(list(args))
        if "--readonly" in args:
            return _completed(1, REFUSAL_STDOUT, "")
        return _completed(0, json.dumps([{"id": "gsp-1", "issue_type": "decision"}]))

    monkeypatch.setattr(beads.subprocess, "run", fake_run)
    rows = list(beads._read_bd(root, timeout=5))

    assert len(calls) == 2, "expected exactly one retry"
    assert "--readonly" in calls[0]
    assert "--readonly" not in calls[1]
    assert [r["id"] for r in rows] == ["gsp-1"]
    assert beads._readonly_args_cache[str(root)] == (), "retry result should stick for the run"


def test_unrelated_failure_is_not_retried(tmp_path: Path, monkeypatch) -> None:
    """Only the proxied refusal earns a second attempt."""
    root = _store(tmp_path, "server")
    calls: list[list[str]] = []

    def fake_run(args, **kwargs):
        calls.append(list(args))
        return _completed(1, "", "database is locked")

    monkeypatch.setattr(beads.subprocess, "run", fake_run)
    try:
        beads._read_bd(root, timeout=5)
    except beads.BeadReadError as error:
        assert "database is locked" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected BeadReadError")
    assert len(calls) == 1, "a non-readonly failure must not be retried"


def test_error_text_prefers_bd_json_payload_over_a_bare_failed(tmp_path: Path, monkeypatch) -> None:
    """With stderr empty, say what bd said instead of '<argv> failed'."""
    root = _store(tmp_path, "proxied-server")
    payload = json.dumps({"code": "dolt.unreachable", "error": "could not reach the dolt server"})
    monkeypatch.setattr(beads.subprocess, "run", lambda args, **kw: _completed(1, payload, ""))
    try:
        beads._read_bd(root, timeout=5)
    except beads.BeadReadError as error:
        assert "could not reach the dolt server" in str(error)
        assert "dolt.unreachable" in str(error)
    else:  # pragma: no cover
        raise AssertionError("expected BeadReadError")
