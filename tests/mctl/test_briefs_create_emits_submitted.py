"""A typed deposit rings the `brief.submitted` doorbell (Plan C, #202, Task 2).

`briefs_create`'s LIVE apply path emits `brief.submitted` exactly once, with the
minted brief id as the event subject, so `brief-shuffle-on-submit` (trigger =
event: brief.submitted) fires within seconds instead of at the next condition
tick.

DRY RUN EMITS NOTHING. #188 is the cautionary precedent: a preview that
mkdir'd on dry_run had a side effect it should not have. An event is a side
effect. A preview must have NONE -- events included -- so a dry_run apply rings
no bell.

BEST-EFFORT. The emit is wired through `gc_events.emit`, which is best-effort
by design: a failed doorbell is a WARN advisory on the response, never a FATAL,
and never perturbs the served output schema (the advisory is a diagnostic
object, which the schema already allows).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from mctl_core import gc_events  # noqa: E402
from mctl_core.diagnostics import Diagnostic, Severity  # noqa: E402

from test_mcp_server import call, server, work_fixture  # noqa: E402

#: A brief body with the `## Gate Evidence` section MBRF036 requires.
BODY = (
    "## What is being decided\n\nShip it?\n\n"
    "## Gate Evidence\n\nG5: n/a -- no server surface touched.\n"
)

#: An OPEN task in the work fixture with a CLOSED brief, usable as a B2.1 source
#: dependency so the create is not refused for reasons unrelated to emission.
#: work_fixture is used (not runtime_fixture) because the latter carries legacy
#: decisions-track state that blocks every create with the #38 migration gate.
SOURCE = "source-revise"


class EmitRecorder:
    """Records every emit() call and returns a scripted advisory (None =
    success). Substituted for gc_events.emit so no subprocess is spawned."""

    def __init__(self, advisory: Diagnostic | None = None):
        self.calls: list[dict] = []
        self._advisory = advisory

    def __call__(self, event, subject, payload, **kwargs):
        self.calls.append({"event": event, "subject": subject, "payload": payload})
        return self._advisory


def _install(monkeypatch, advisory: Diagnostic | None = None) -> EmitRecorder:
    recorder = EmitRecorder(advisory)
    monkeypatch.setattr(gc_events, "emit", recorder)
    return recorder


def _create(city_root, rig_root, *, dry_run):
    args = {
        "title": "Decide dispatch policy",
        "body": BODY,
        "sources": [SOURCE],
    }
    if dry_run is not None:
        args["dry_run"] = dry_run
    return call(server(city_root, rig_root), "briefs_create", args)["result"]


def _minted_brief_id(structured) -> str | None:
    for entry in structured.get("actual_effects") or ():
        if isinstance(entry, dict) and entry.get("kind") == "bead_create":
            target = entry.get("target")
            if isinstance(target, str):
                return target
    return None


class TestLiveDepositRingsTheBell:
    def test_it_emits_exactly_once(self, tmp_path: Path, monkeypatch):
        rec = _install(monkeypatch)
        city_root, rig_root = work_fixture(tmp_path)

        _create(city_root, rig_root, dry_run=False)

        assert len(rec.calls) == 1

    def test_the_event_is_brief_submitted(self, tmp_path: Path, monkeypatch):
        rec = _install(monkeypatch)
        city_root, rig_root = work_fixture(tmp_path)

        _create(city_root, rig_root, dry_run=False)

        assert rec.calls[0]["event"] == "brief.submitted"

    def test_the_subject_is_the_minted_brief_id(self, tmp_path: Path, monkeypatch):
        rec = _install(monkeypatch)
        city_root, rig_root = work_fixture(tmp_path)

        structured = _create(city_root, rig_root, dry_run=False)["structuredContent"]
        brief_id = _minted_brief_id(structured)

        assert brief_id, "the live apply must mint a brief bead"
        assert rec.calls[0]["subject"] == brief_id


class TestDryRunRingsNothing:
    def test_explicit_dry_run_emits_zero_events(self, tmp_path: Path, monkeypatch):
        rec = _install(monkeypatch)
        city_root, rig_root = work_fixture(tmp_path)

        _create(city_root, rig_root, dry_run=True)

        assert rec.calls == [], "a preview must have NO side effects, events included (#188)"

    def test_absent_dry_run_defaults_to_no_emit(self, tmp_path: Path, monkeypatch):
        """Mutation is opt-in: absent dry_run means dry run, so no bell rings."""
        rec = _install(monkeypatch)
        city_root, rig_root = work_fixture(tmp_path)

        _create(city_root, rig_root, dry_run=None)

        assert rec.calls == []


class TestEmissionIsBestEffort:
    def test_a_failed_doorbell_does_not_fail_the_deposit(self, tmp_path: Path, monkeypatch):
        advisory = Diagnostic(Severity.WARN, gc_events.EMIT_FAILED, "doorbell failed")
        _install(monkeypatch, advisory=advisory)
        city_root, rig_root = work_fixture(tmp_path)

        result = _create(city_root, rig_root, dry_run=False)

        assert result.get("isError") in (None, False), "an emit failure must not fail the apply"
        structured = result["structuredContent"]
        assert structured["applied"] is True

    def test_the_advisory_surfaces_in_the_response_diagnostics(self, tmp_path: Path, monkeypatch):
        advisory = Diagnostic(Severity.WARN, gc_events.EMIT_FAILED, "doorbell failed")
        _install(monkeypatch, advisory=advisory)
        city_root, rig_root = work_fixture(tmp_path)

        structured = _create(city_root, rig_root, dry_run=False)["structuredContent"]

        codes = {d.get("code") for d in structured.get("diagnostics", [])}
        assert gc_events.EMIT_FAILED in codes
