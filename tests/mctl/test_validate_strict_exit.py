"""`briefs validate --strict` exits non-zero when it reports the city invalid.

Without it, `mctl briefs validate --all` exits **0** while reporting 159 ERRORs
and a FATAL, with `valid: false` in its own payload. Any consumer reading `$?` --
a CI gate, a shell `&&` chain -- is told the city is clean.

The default is deliberately unchanged. `cli.py` documents the rule: "Read commands
still exit 0 with diagnostics -- reporting drift is what they are for." That rule
is right for `list` and `doctor`. `--strict` is opt-in for callers that want the
verdict in the exit status, and it reuses `ValidationReport.valid` rather than
re-deriving the severity test, so the flag and the payload cannot disagree.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

SCRIPTS_ROOT = Path(__file__).resolve().parents[2] / "assets" / "scripts"
sys.path.insert(0, str(SCRIPTS_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import multi_rig
from mctl_core import cli


def _validate(fixture, *extra: str) -> int:
    argv = [
        "briefs", "validate", "--all",
        "--city", str(fixture.city_root),
        "--rig", multi_rig.READABLE_RIGS[0],
        "--json",
        *extra,
    ]
    old = dict(__import__("os").environ)
    __import__("os").environ.update(fixture.env)
    try:
        return cli.main(argv)
    finally:
        __import__("os").environ.clear()
        __import__("os").environ.update(old)


def test_strict_is_accepted_by_the_parser(tmp_path: Path, capsys):
    """The flag has to exist before its behaviour can be asserted."""
    fixture = multi_rig.build(tmp_path)
    code = _validate(fixture, "--strict")
    capsys.readouterr()

    assert code in (0, 1), f"--strict was rejected by the parser (exit {code})"


def test_strict_exit_agrees_with_the_payloads_own_verdict(tmp_path: Path, capsys):
    """The flag must never disagree with the `valid` field it is reporting.

    This is the discriminating assertion: it fails both if `--strict` ignores an
    invalid city and if it fails a valid one.
    """
    fixture = multi_rig.build(tmp_path)

    code = _validate(fixture, "--strict")
    payload = json.loads(capsys.readouterr().out)

    assert code == (0 if payload["valid"] else 1), (
        f"valid={payload['valid']} but --strict exited {code}"
    )


def test_the_default_still_exits_zero_and_reports(tmp_path: Path, capsys):
    """The documented read-command rule must survive this change."""
    fixture = multi_rig.build(tmp_path)

    code = _validate(fixture)
    payload = json.loads(capsys.readouterr().out)

    assert code == 0, "the default must stay a reporting read, not a gate"
    assert "valid" in payload, "the verdict must still be in the payload"


def test_strict_exits_zero_when_the_report_is_valid(tmp_path: Path, capsys, monkeypatch):
    """Guards the other direction: `--strict` must not simply always fail.

    The multi-rig fixture is invalid (5 ERROR, 1 FATAL), so every assertion above
    exercises only the invalid branch. An implementation that returned 1
    unconditionally would satisfy all of them.
    """
    fixture = multi_rig.build(tmp_path)

    real = cli.validate_brief

    def _clean(ctx, scope):
        report = real(ctx, scope)
        return type(report)(scope=report.scope, records=report.records, diagnostics=())

    monkeypatch.setattr(cli, "validate_brief", _clean)

    code = _validate(fixture, "--strict")
    payload = json.loads(capsys.readouterr().out)

    assert payload["valid"] is True, "the monkeypatch must produce a clean report"
    assert code == 0, "--strict must exit 0 on a valid report"
