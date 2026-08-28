"""The CLI verdict path rings the `brief.decided` doorbell (mc-d6lp).

THE DEFECT. `briefs_relay_adjudication` (the MCP path) emits `brief.decided` on
a live apply; `mctl briefs adjudicate` (the CLI path) recorded the identical
verdict and rang nothing. `mc-d6lp` filed it and it was closed "QA-only, not
code-fixed by design", so the bell stayed silent on the surface the
`adjudicate-brief` skill actually prescribes. Measured consequence:
`gc events --since 72h | grep revise-return` showed ZERO firings, and the 13
hecke briefs adjudicated `revise` on 2026-08-25 were closed by that verdict and
can never come back on their own -- `revise-return` is built and unreachable.

WHAT THIS TEST ASSERTS. Not a flag, not a return value: the CONSEQUENCE. A fake
`gc` executable is placed on PATH and records every argv it is called with, so
each test observes the same thing a city consumer observes -- `gc event emit
brief.decided ...` actually being invoked by the real CLI subprocess, through
the real `gc_events._default_runner` seam. No monkeypatching of the emitter.

BLAST RADIUS (master plan section 11). THREE orders trigger on `brief.decided`:
`brief-decision-dispatch`, `post-decision-file-or-sendback`, and
`revise-return`. All three will now fire on CLI verdicts that previously fired
none, so `TestAllThreeConsumersCanFire` pins that the emitted event type and
payload keys are the ones all three read, and that the event is emitted ONCE --
a second bell would drive three consumers twice, not one.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MCTL = REPO_ROOT / "assets" / "scripts" / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"

#: The fixture's one adjudicatable OPEN decision brief.
BRIEF = "mc-open"

#: Every order under orders/ whose trigger is `on = "brief.decided"`.
BRIEF_DECIDED_ORDERS = (
    "brief-decision-dispatch",
    "post-decision-file-or-sendback",
    "revise-return",
)


def runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track")
    (rig_root / ".beads" / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return city_root, rig_root


def fake_gc(tmp_path: Path, *, exit_code: int = 0, stderr: str = "") -> tuple[Path, Path]:
    """A `gc` on PATH that records its argv. The consumer's-eye view of the bell.

    Returns (bin_dir, log_path). The log is JSON lines, one argv list per call.
    """
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir()
    log = tmp_path / "gc-calls.jsonl"
    script = bin_dir / "gc"
    script.write_text(
        "#!" + sys.executable + "\n"
        "import json, sys\n"
        "with open(" + repr(str(log)) + ", 'a') as fh:\n"
        "    fh.write(json.dumps(sys.argv[1:]) + '\\n')\n"
        "sys.stderr.write(" + repr(stderr) + ")\n"
        "raise SystemExit(" + str(exit_code) + ")\n",
        encoding="utf-8",
    )
    script.chmod(0o755)
    return bin_dir, log


def run_adjudicate(
    city_root: Path,
    rig_root: Path,
    bin_dir: Path,
    *extra: str,
    verdict: str = "approve",
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    # Opt back in to the real emitter (conftest switches it off suite-wide so no
    # test rings Taylor's actual city). The `gc` this reaches is the fake above.
    env["MCTL_CITY_EVENTS"] = "1"
    return subprocess.run(
        [
            sys.executable,
            str(MCTL),
            "briefs",
            "adjudicate",
            BRIEF,
            "--verdict",
            verdict,
            "--reason",
            "ready to ship",
            "--adjudicated-by",
            "taylor",
            "--city",
            str(city_root),
            "--rig",
            "mathcity",
            "--json",
            *extra,
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def emitted(log: Path) -> list[list[str]]:
    if not log.exists():
        return []
    return [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines() if line]


def decided_calls(log: Path) -> list[list[str]]:
    return [c for c in emitted(log) if c[:3] == ["event", "emit", "brief.decided"]]


def payload_of(call: list[str]) -> dict:
    return json.loads(call[call.index("--payload") + 1])


@pytest.fixture()
def city(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    bin_dir, log = fake_gc(tmp_path)
    return city_root, rig_root, bin_dir, log


class TestALiveCliVerdictRingsTheBell:
    def test_the_cli_emits_brief_decided(self, city):
        city_root, rig_root, bin_dir, log = city

        result = run_adjudicate(city_root, rig_root, bin_dir)

        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["applied"] is True
        assert decided_calls(log), (
            "the CLI recorded the verdict but rang no bell -- `gc event emit "
            "brief.decided` never reached the city, so all three consumers "
            "(brief-decision-dispatch, post-decision-file-or-sendback, "
            "revise-return) stayed asleep (mc-d6lp)"
        )

    def test_it_rings_exactly_once(self, city):
        city_root, rig_root, bin_dir, log = city

        run_adjudicate(city_root, rig_root, bin_dir)

        assert len(decided_calls(log)) == 1

    def test_the_subject_is_the_brief_id(self, city):
        city_root, rig_root, bin_dir, log = city

        run_adjudicate(city_root, rig_root, bin_dir)

        call = decided_calls(log)[0]
        assert call[call.index("--subject") + 1] == BRIEF

    def test_a_revise_verdict_rings_the_bell_that_revise_return_waits_on(self, city):
        """The 13 stranded hecke briefs were `revise`. That is the load-bearing case."""
        city_root, rig_root, bin_dir, log = city

        result = run_adjudicate(city_root, rig_root, bin_dir, verdict="revise")

        assert result.returncode == 0, result.stderr
        assert decided_calls(log), "a revise verdict must wake revise-return"
        assert payload_of(decided_calls(log)[0])["decision"] == "revise"


class TestThePayloadIsShapeIndistinguishableFromTheOtherProducers:
    """A consumer must not be able to tell a CLI verdict from an MCP or skill one."""

    def test_the_payload_carries_the_brief_slug(self, city):
        city_root, rig_root, bin_dir, log = city

        run_adjudicate(city_root, rig_root, bin_dir)

        assert payload_of(decided_calls(log)[0])["brief_slug"] == BRIEF

    def test_the_payload_carries_the_verdict_under_decision(self, city):
        city_root, rig_root, bin_dir, log = city

        run_adjudicate(city_root, rig_root, bin_dir, verdict="approve")

        assert payload_of(decided_calls(log)[0])["decision"] == "approve"

    def test_the_payload_carries_the_adjudicator(self, city):
        city_root, rig_root, bin_dir, log = city

        run_adjudicate(city_root, rig_root, bin_dir)

        assert payload_of(decided_calls(log)[0])["adjudicated_by"] == "taylor"


class TestAllThreeConsumersCanFire:
    """Blast radius: emitting from the CLI wakes THREE orders, not one."""

    def test_orders_on_disk_still_number_three_and_all_key_on_brief_decided(self):
        found = set()
        for path in sorted((REPO_ROOT / "orders").glob("*.toml")):
            text = path.read_text(encoding="utf-8")
            if 'trigger = "event"' in text and 'on = "brief.decided"' in text:
                found.add(path.stem)
        assert found == set(BRIEF_DECIDED_ORDERS), (
            "the brief.decided consumer set changed; re-assess the blast radius "
            "of emitting from the CLI path before shipping"
        )

    def test_the_emitted_event_type_is_the_one_all_three_orders_subscribe_to(self, city):
        city_root, rig_root, bin_dir, log = city

        run_adjudicate(city_root, rig_root, bin_dir)

        call = decided_calls(log)[0]
        assert call[:3] == ["event", "emit", "brief.decided"]

    def test_the_payload_carries_every_key_the_three_consumers_branch_on(self, city):
        """dispatch branches on `decision`; all three resolve the brief by `brief_slug`."""
        city_root, rig_root, bin_dir, log = city

        run_adjudicate(city_root, rig_root, bin_dir)

        payload = payload_of(decided_calls(log)[0])
        assert {"brief_slug", "decision", "adjudicated_by"} <= set(payload)


class TestADryRunRingsNothing:
    def test_dry_run_emits_zero_events(self, city):
        city_root, rig_root, bin_dir, log = city

        result = run_adjudicate(city_root, rig_root, bin_dir, "--dry-run")

        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["applied"] is False
        assert emitted(log) == [], "a preview must have NO side effects, events included (#188)"


class TestEmissionIsBestEffort:
    def test_a_failed_doorbell_does_not_fail_the_verdict(self, tmp_path: Path):
        city_root, rig_root = runtime_fixture(tmp_path)
        bin_dir, log = fake_gc(tmp_path, exit_code=1, stderr="city is down")

        result = run_adjudicate(city_root, rig_root, bin_dir)

        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["applied"] is True, "the verdict already landed on the bead"

    def test_the_advisory_surfaces_in_the_response_diagnostics(self, tmp_path: Path):
        city_root, rig_root = runtime_fixture(tmp_path)
        bin_dir, log = fake_gc(tmp_path, exit_code=1, stderr="city is down")

        result = run_adjudicate(city_root, rig_root, bin_dir)

        codes = {d.get("code") for d in json.loads(result.stdout).get("diagnostics", [])}
        assert "MEVT_EMIT_FAILED" in codes

    def test_an_absent_gc_does_not_fail_the_verdict(self, tmp_path: Path):
        """No `gc` on PATH at all -- the subprocess cannot even launch."""
        city_root, rig_root = runtime_fixture(tmp_path)
        empty_bin = tmp_path / "emptybin"
        empty_bin.mkdir()
        env_free = tmp_path / "nogc"
        env_free.mkdir()

        result = subprocess.run(
            [
                sys.executable,
                str(MCTL),
                "briefs",
                "adjudicate",
                BRIEF,
                "--verdict",
                "approve",
                "--reason",
                "ready to ship",
                "--city",
                str(city_root),
                "--rig",
                "mathcity",
                "--json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env={
                "PATH": str(empty_bin),
                "PYTHONDONTWRITEBYTECODE": "1",
                "MCTL_BEADS_FIXTURE": str(rig_root / ".beads" / "issues.jsonl"),
                "MCTL_CITY_EVENTS": "1",
                "HOME": str(env_free),
            },
        )

        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["applied"] is True


class TestTheSuiteCannotRingTheRealCity:
    """The switch that keeps fixture verdicts off the live bus (see conftest.py).

    Without it, every live-apply test published `brief.decided` for `mc-open` to
    the real city and woke all three consumers on a brief that does not exist --
    329 such events were measured on the bus in 24h on 2026-08-28.
    """

    def test_switching_city_events_off_suppresses_the_real_doorbell(self, city):
        city_root, rig_root, bin_dir, log = city

        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
        env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
        env["MCTL_CITY_EVENTS"] = "0"
        result = subprocess.run(
            [
                sys.executable,
                str(MCTL),
                "briefs",
                "adjudicate",
                BRIEF,
                "--verdict",
                "approve",
                "--reason",
                "ready to ship",
                "--city",
                str(city_root),
                "--rig",
                "mathcity",
                "--json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["applied"] is True, "the verdict still lands"
        assert emitted(log) == [], "a suppressed doorbell must not shell out at all"

    def test_a_suppressed_doorbell_is_not_reported_as_a_failed_one(self, city):
        """Silence asked for is not silence to recover -- no MEVT_EMIT_FAILED."""
        city_root, rig_root, bin_dir, log = city

        env = os.environ.copy()
        env["PYTHONDONTWRITEBYTECODE"] = "1"
        env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
        env["MCTL_CITY_EVENTS"] = "0"
        result = subprocess.run(
            [
                sys.executable,
                str(MCTL),
                "briefs",
                "adjudicate",
                BRIEF,
                "--verdict",
                "approve",
                "--reason",
                "ready to ship",
                "--city",
                str(city_root),
                "--rig",
                "mathcity",
                "--json",
            ],
            cwd=REPO_ROOT,
            text=True,
            capture_output=True,
            check=False,
            env=env,
        )

        codes = {d.get("code") for d in json.loads(result.stdout).get("diagnostics", [])}
        assert "MEVT_EMIT_FAILED" not in codes

    def test_the_switch_does_not_gag_an_injected_runner(self, monkeypatch):
        """A caller supplying a runner is asking to observe the call."""
        sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
        from mctl_core import gc_events

        monkeypatch.setenv(gc_events.CITY_EVENTS_ENV, "0")
        seen: list[list[str]] = []

        class _Ok:
            returncode = 0
            stderr = ""

        def runner(argv):
            seen.append(argv)
            return _Ok()

        assert gc_events.emit("brief.decided", BRIEF, {}, runner=runner) is None
        assert seen, "an injected runner is the caller's own seam, never suppressed"
