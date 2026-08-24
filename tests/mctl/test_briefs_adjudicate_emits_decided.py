"""A typed verdict rings the `brief.decided` doorbell (Plan C, #202, Task 3).

`briefs_adjudicate`'s LIVE apply path emits `brief.decided` exactly once, with
the brief id as the event subject, so `brief-decision-dispatch` and
`post-decision-file-or-sendback` (both trigger = event: brief.decided) fire
within seconds -- the mc-f045 adjudication (2026-08-23) rang nothing, the live
demonstration of the missing doorbell this task installs.

THE PAYLOAD CARRIES THE VERDICT AND THE ADJUDICATOR. `brief-decision-dispatch`
branches on approve/reject/revise/defer, so the verdict must ride in the
payload; and post-#152 the adjudicator is recorded so a decision can be
attributed. Both go in the payload under the same `decision`/`adjudicated_by`
names the bead records them under.

DRY RUN EMITS NOTHING (#188). BEST-EFFORT: a failed doorbell is a WARN advisory,
never a FATAL (the verdict already landed on the bead; the condition backstop
recovers a lost event).
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest  # noqa: E402

from mctl_core import gc_events  # noqa: E402
from mctl_core.diagnostics import Diagnostic, Severity  # noqa: E402

from test_mcp_server import call, runtime_fixture, server  # noqa: E402

#: mc-open is the fixture's one adjudicatable OPEN decision brief.
BRIEF = "mc-open"


class EmitRecorder:
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


def _adjudicate(city_root, rig_root, *, dry_run, verdict="approve", adjudicated_by="taylor"):
    args = {
        "brief_id": BRIEF,
        "verdict": verdict,
        "reason": "ready to ship",
        "option": "A",
        "adjudicated_by": adjudicated_by,
    }
    if dry_run is not None:
        args["dry_run"] = dry_run
    return call(server(city_root, rig_root), "briefs_adjudicate", args)["result"]


class TestLiveVerdictRingsTheBell:
    def test_it_emits_exactly_once(self, tmp_path: Path, monkeypatch):
        rec = _install(monkeypatch)
        city_root, rig_root = runtime_fixture(tmp_path)

        _adjudicate(city_root, rig_root, dry_run=False)

        assert len(rec.calls) == 1

    def test_the_event_is_brief_decided(self, tmp_path: Path, monkeypatch):
        rec = _install(monkeypatch)
        city_root, rig_root = runtime_fixture(tmp_path)

        _adjudicate(city_root, rig_root, dry_run=False)

        assert rec.calls[0]["event"] == "brief.decided"

    def test_the_subject_is_the_brief_id(self, tmp_path: Path, monkeypatch):
        rec = _install(monkeypatch)
        city_root, rig_root = runtime_fixture(tmp_path)

        _adjudicate(city_root, rig_root, dry_run=False)

        assert rec.calls[0]["subject"] == BRIEF


class TestThePayloadCarriesTheVerdictAndAdjudicator:
    def test_the_verdict_is_in_the_payload(self, tmp_path: Path, monkeypatch):
        rec = _install(monkeypatch)
        city_root, rig_root = runtime_fixture(tmp_path)

        _adjudicate(city_root, rig_root, dry_run=False, verdict="approve")

        assert rec.calls[0]["payload"].get("decision") == "approve"

    def test_the_adjudicator_is_in_the_payload(self, tmp_path: Path, monkeypatch):
        rec = _install(monkeypatch)
        city_root, rig_root = runtime_fixture(tmp_path)

        _adjudicate(city_root, rig_root, dry_run=False, adjudicated_by="taylor")

        assert rec.calls[0]["payload"].get("adjudicated_by") == "taylor"

    def test_the_subject_is_also_carried_as_brief_slug(self, tmp_path: Path, monkeypatch):
        """Same key the skill path uses, so the event is shape-indistinguishable."""
        rec = _install(monkeypatch)
        city_root, rig_root = runtime_fixture(tmp_path)

        _adjudicate(city_root, rig_root, dry_run=False)

        assert rec.calls[0]["payload"].get("brief_slug") == BRIEF


class TestDryRunRingsNothing:
    def test_explicit_dry_run_emits_zero_events(self, tmp_path: Path, monkeypatch):
        rec = _install(monkeypatch)
        city_root, rig_root = runtime_fixture(tmp_path)

        _adjudicate(city_root, rig_root, dry_run=True)

        assert rec.calls == [], "a preview must have NO side effects, events included (#188)"

    def test_absent_dry_run_defaults_to_no_emit(self, tmp_path: Path, monkeypatch):
        rec = _install(monkeypatch)
        city_root, rig_root = runtime_fixture(tmp_path)

        _adjudicate(city_root, rig_root, dry_run=None)

        assert rec.calls == []


class TestEmissionIsBestEffort:
    def test_a_failed_doorbell_does_not_fail_the_verdict(self, tmp_path: Path, monkeypatch):
        advisory = Diagnostic(Severity.WARN, gc_events.EMIT_FAILED, "doorbell failed")
        _install(monkeypatch, advisory=advisory)
        city_root, rig_root = runtime_fixture(tmp_path)

        result = _adjudicate(city_root, rig_root, dry_run=False)

        assert result.get("isError") in (None, False), "an emit failure must not fail the apply"
        assert result["structuredContent"]["applied"] is True

    def test_the_advisory_surfaces_in_the_response_diagnostics(self, tmp_path: Path, monkeypatch):
        advisory = Diagnostic(Severity.WARN, gc_events.EMIT_FAILED, "doorbell failed")
        _install(monkeypatch, advisory=advisory)
        city_root, rig_root = runtime_fixture(tmp_path)

        structured = _adjudicate(city_root, rig_root, dry_run=False)["structuredContent"]

        codes = {d.get("code") for d in structured.get("diagnostics", [])}
        assert gc_events.EMIT_FAILED in codes
