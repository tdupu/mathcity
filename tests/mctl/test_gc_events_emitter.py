"""The `gc_events.emit` best-effort city-event emitter (Plan C, #202, Task 1).

mctl rings the city's doorbells: a typed deposit or a typed verdict emits a
`gc event` so the event-triggered orders (`brief-shuffle-on-submit`,
`brief-decision-dispatch`) fire within seconds instead of waiting for a
condition tick.

SPEC (Task 1 Step 1). The plan says to copy brief-prep.toml's submit-to-pile
emit command verbatim, but that step emits NOTHING -- it only moves the staged
brief into `.pile/`. The only real in-tree `gc event` producer is
`formulas/brief-record-decision.toml`'s emit-decided-event step:

    gc event emit brief.decided \
      --subject "<slug>" \
      --message "brief <slug> decided: <decision>" \
      --payload '{"brief_slug":"<slug>","decision":"<decision>"}'

so the emitter must produce that shape -- `gc event emit <type> --subject <s>
--message <m> --payload <json>` -- and a consumer must not be able to tell
mctl's event apart from the skill path's.

Best-effort by design: on ANY subprocess failure emit() returns a WARN advisory
(MEVT_EMIT_FAILED) and NEVER raises. The typed mutation already succeeded; the
condition backstop recovers a lost event.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import gc_events  # noqa: E402
from mctl_core.diagnostics import Diagnostic, Severity  # noqa: E402

REGISTRY = REPO_ROOT / "assets" / "mctl" / "diagnostics.toml"


class Recorder:
    """A recording fake for the subprocess runner. Captures every argv it is
    handed and returns a scripted result -- it never spawns a process."""

    def __init__(self, returncode: int = 0, stderr: str = "", raises: Exception | None = None):
        self.calls: list[list[str]] = []
        self._returncode = returncode
        self._stderr = stderr
        self._raises = raises

    def __call__(self, argv):
        self.calls.append(list(argv))
        if self._raises is not None:
            raise self._raises
        return subprocess.CompletedProcess(argv, self._returncode, stdout="", stderr=self._stderr)


class TestTheEmittedCommandShape:
    def test_it_shells_to_gc_event_emit_with_the_event_type(self):
        rec = Recorder()
        gc_events.emit("brief.submitted", "mc-abcd", {"brief_slug": "mc-abcd"}, runner=rec)
        assert len(rec.calls) == 1
        argv = rec.calls[0]
        assert argv[:4] == ["gc", "event", "emit", "brief.submitted"]

    def test_the_subject_is_passed_as_a_named_flag(self):
        rec = Recorder()
        gc_events.emit("brief.submitted", "mc-abcd", {"brief_slug": "mc-abcd"}, runner=rec)
        argv = rec.calls[0]
        assert "--subject" in argv
        assert argv[argv.index("--subject") + 1] == "mc-abcd"

    def test_the_payload_is_a_json_object_carrying_the_given_keys(self):
        rec = Recorder()
        gc_events.emit(
            "brief.decided",
            "mc-abcd",
            {"brief_slug": "mc-abcd", "decision": "approve", "adjudicated_by": "taylor"},
            runner=rec,
        )
        argv = rec.calls[0]
        assert "--payload" in argv
        parsed = json.loads(argv[argv.index("--payload") + 1])
        assert parsed == {
            "brief_slug": "mc-abcd",
            "decision": "approve",
            "adjudicated_by": "taylor",
        }

    def test_it_carries_a_message_so_the_shape_matches_the_skill_path(self):
        rec = Recorder()
        gc_events.emit("brief.submitted", "mc-abcd", {"brief_slug": "mc-abcd"}, runner=rec)
        argv = rec.calls[0]
        assert "--message" in argv
        assert argv[argv.index("--message") + 1].strip() != ""


class TestSuccessIsSilent:
    def test_a_clean_emit_returns_no_advisory(self):
        rec = Recorder(returncode=0)
        assert gc_events.emit("brief.submitted", "mc-abcd", {"brief_slug": "mc-abcd"}, runner=rec) is None


class TestFailureIsAdvisoryNotFatal:
    def test_a_nonzero_exit_returns_a_warn_advisory_and_does_not_raise(self):
        rec = Recorder(returncode=1, stderr="gc: city not active")
        diag = gc_events.emit("brief.submitted", "mc-abcd", {"brief_slug": "mc-abcd"}, runner=rec)
        assert isinstance(diag, Diagnostic)
        assert diag.code == "MEVT_EMIT_FAILED"
        assert diag.severity is Severity.WARN

    def test_a_runner_that_raises_is_swallowed_into_the_same_advisory(self):
        rec = Recorder(raises=subprocess.TimeoutExpired(cmd="gc", timeout=10))
        diag = gc_events.emit("brief.decided", "mc-abcd", {"brief_slug": "mc-abcd"}, runner=rec)
        assert isinstance(diag, Diagnostic)
        assert diag.code == "MEVT_EMIT_FAILED"
        assert diag.severity is Severity.WARN

    def test_the_advisory_names_the_event_and_subject_in_its_facts(self):
        rec = Recorder(returncode=1)
        diag = gc_events.emit("brief.decided", "mc-wxyz", {"brief_slug": "mc-wxyz"}, runner=rec)
        assert diag.facts.get("event_type") == "brief.decided"
        assert diag.facts.get("subject") == "mc-wxyz"


class TestTheDiagnosticIsRegistered:
    def _registry(self) -> dict:
        return tomllib.loads(REGISTRY.read_text(encoding="utf-8"))

    def test_the_emit_failed_code_is_in_the_registry(self):
        assert "MEVT_EMIT_FAILED" in self._registry()

    def test_it_is_a_warning(self):
        assert self._registry()["MEVT_EMIT_FAILED"]["severity"] == "WARN"

    def test_it_names_its_module(self):
        assert self._registry()["MEVT_EMIT_FAILED"].get("module") == "gc_events.py"
