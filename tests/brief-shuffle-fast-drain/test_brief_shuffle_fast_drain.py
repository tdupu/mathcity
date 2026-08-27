import json
import importlib.util
import subprocess
import sys
import tempfile
import tomllib
import unittest
from pathlib import Path
from unittest import mock


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "assets/scripts/brief-shuffle-fast-drain.py"
GATES = REPO_ROOT / "assets/brief-pipeline/gates.toml"


def load_drain_module():
    spec = importlib.util.spec_from_file_location("brief_shuffle_fast_drain", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class BriefShuffleFastDrainTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.brief_root = Path(self.temp_dir.name) / ".beads/briefs"
        (self.brief_root / ".pile").mkdir(parents=True)
        # Canonical pile membership is the bead query (POLICY B2.4), so every
        # run needs a bead source. These fixtures have no bd store, so they
        # inject one through the same seam `mctl_core.beads.read_beads` uses.
        # Empty by default: a slug with no brief bead is UNRESOLVED, not
        # closed, and unresolved briefs are still drained.
        self.bead_fixture = Path(self.temp_dir.name) / "beads.jsonl"
        self.bead_fixture.write_text("", encoding="utf-8")

    def write_beads(self, *rows):
        self.bead_fixture.write_text(
            "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
        )
        return self.bead_fixture

    def tearDown(self):
        self.temp_dir.cleanup()

    def run_drain(self, *args):
        return subprocess.run(
            [
                "python3",
                str(SCRIPT),
                "--brief-root",
                str(self.brief_root),
                "--gate-config",
                str(GATES),
                "--bead-fixture",
                str(self.bead_fixture),
                "--json",
                "--no-external",
                *args,
            ],
            text=True,
            capture_output=True,
            check=False,
        )

    def write_brief(self, slug, profile="standard", extra_frontmatter="", evidence=None):
        profile_gates = {
            "standard": ["G1", "G2", "G3", "G4", "G5", "G5b", "G6", "G7", "G8", "G9", "G10", "G11", "G12", "G13", "G14", "G15", "G16"],
            "decision": ["G5", "G5b", "G8", "G9", "G11", "G12", "G13"],
            "lost_bead_filter": ["G5", "G5b", "G8", "G9", "G11", "G12", "G13"],
            "producer_repair": ["G5", "G5b", "G8", "G9", "G11", "G12", "G13"],
            "no_brainer": ["G1", "G5", "G5b", "G7", "G8", "G9", "G12", "G13", "G14", "G16"],
        }.get(profile, [])
        gate_names = {
            "G1": "Test-evidence", "G2": "Good-test", "G3": "Shell-scripts-testable",
            "G4": "Critical-review", "G5": "Server-touching", "G5b": "User-skill-touching",
            "G6": "LaTeX-gate", "G7": "Artifacts-staging", "G8": "Brief-record",
            "G9": "No-brainer-filter", "G10": "Improve-README", "G11": "Breadcrumb",
            "G12": "Auto-merge-kill-switch", "G13": "Stale-claim",
            "G14": "Test-execution-silent", "G15": "Improve-README-silent", "G16": "Master-current",
        }
        lines = evidence if evidence is not None else [
            f"{gate} {gate_names[gate]}: "
            + ("PASS classifier_state=known_non_no_brainer reason=fixture classified_at=2026-08-16T00:00:00Z" if gate == "G9" else "PASS")
            for gate in profile_gates
        ]
        frontmatter = f"""---
brief_slug: {slug}
gate_profile: {profile}
source_bead: source-{slug}
feedback_sink: brief_quality_failure
{extra_frontmatter}---
"""
        path = self.brief_root / ".pile" / f"{slug}.md"
        path.write_text(frontmatter + "\n# Fixture brief\n\n## Gate Evidence\n" + "\n".join(lines) + "\n")
        return path

    def json_output(self, result):
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def gate_config(self):
        with GATES.open("rb") as handle:
            return tomllib.load(handle)

    def write_pile_manifest(self, *rows):
        """Write pile rows in the live city's convention.

        Measured against <city-root>/.beads/briefs/.pile/manifest.jsonl on
        2026-08-20: all 22 rows round-trip byte-identically under a plain
        `json.dumps(row)` -- default separators, insertion key order, no
        sorting. The stack index uses a different convention.
        """
        path = self.brief_root / ".pile/manifest.jsonl"
        path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
        return path

    def read_pile_manifest_rows(self):
        path = self.brief_root / ".pile/manifest.jsonl"
        return [json.loads(l) for l in path.read_text().splitlines() if l.strip()]

    def reject_brief(self, slug, **kwargs):
        brief = self.write_brief(slug, **kwargs)
        brief.write_text(brief.read_text().replace("G4 Critical-review: PASS", "G4 Critical-review: FAIL"))
        return brief

    def test_valid_standard_brief_promotes_to_stack(self):
        self.write_brief("standard-ok")
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["promoted"], ["standard-ok"])
        self.assertTrue((self.brief_root / "stack/standard-ok.md").is_file())

    def test_valid_decision_brief_promotes_to_stack(self):
        self.write_brief(
            "decision-ok",
            profile="decision",
            extra_frontmatter="brief_kind: decision\nlegacy_source: decisions-track/decision-ok.md\n",
        )
        decision = self.brief_root / ".pile/decision-ok.md"
        decision.write_text(decision.read_text().replace("\n# Fixture brief", "\naction_block:\n  on_approve: []\n  on_reject: []\n  on_defer: []\n\n# Fixture brief"))
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["promoted"], ["decision-ok"])

    def test_missing_g4_rejects(self):
        brief = self.write_brief("missing-g4")
        brief.write_text(brief.read_text().replace("G4 Critical-review: PASS\n", ""))
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["rejected"], ["missing-g4"])
        self.assertTrue((self.brief_root / ".pile/.rejected/missing-g4/brief.md").is_file())
        rejection = json.loads((self.brief_root / ".pile/.rejected/missing-g4/rejection.json").read_text())
        self.assertIn("missing required gate G4 Critical-review", rejection["reason"])

    def test_failed_g4_rejects_and_records_failure(self):
        brief = self.write_brief("failed-g4")
        brief.write_text(brief.read_text().replace("G4 Critical-review: PASS", "G4 Critical-review: FAIL - controlled fixture"))
        self.json_output(self.run_drain("--apply"))
        rejection = json.loads((self.brief_root / ".pile/.rejected/failed-g4/rejection.json").read_text())
        self.assertIn("G4 Critical-review: FAIL", rejection["reason"])

    def test_headingless_pass_evidence_rejects(self):
        brief = self.write_brief("headingless-pass")
        brief.write_text(brief.read_text().replace("## Gate Evidence\n", ""))
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["rejected"], ["headingless-pass"])
        self.assertEqual(report["reasons"]["headingless-pass"], "missing Gate Evidence section")

    def test_pass_evidence_outside_gate_evidence_section_rejects(self):
        brief = self.write_brief("sectionless-pass")
        brief.write_text(brief.read_text().replace("## Gate Evidence", "## Other Evidence"))
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["rejected"], ["sectionless-pass"])
        self.assertEqual(report["reasons"]["sectionless-pass"], "missing Gate Evidence section")

    def test_max_items_one_leaves_other_pile_items(self):
        self.write_brief("one")
        self.write_brief("two")
        report = self.json_output(self.run_drain("--max-items", "1", "--apply"))
        self.assertEqual(len(report["promoted"] + report["rejected"]), 1)
        self.assertEqual(len(list((self.brief_root / ".pile").glob("*.md"))), 1)

    def test_dry_run_does_not_change_files_and_reports_planned_action(self):
        brief = self.write_brief("dry-run")
        before = brief.read_text()
        report = self.json_output(self.run_drain())
        self.assertEqual(brief.read_text(), before)
        self.assertFalse((self.brief_root / "stack").exists())
        self.assertEqual(report["planned_promoted"], ["dry-run"])

    def test_index_gets_one_row_per_promoted_slug_and_rerun_does_not_duplicate(self):
        self.write_brief("indexed")
        self.json_output(self.run_drain("--apply"))
        self.json_output(self.run_drain("--apply"))
        rows = [json.loads(line) for line in (self.brief_root / "stack/.index.jsonl").read_text().splitlines()]
        self.assertEqual([row["slug"] for row in rows], ["indexed"])

    def test_unknown_gate_profile_rejects(self):
        self.write_brief("unknown", profile="unknown")
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["rejected"], ["unknown"])
        rejection = json.loads((self.brief_root / ".pile/.rejected/unknown/rejection.json").read_text())
        self.assertIn("unknown gate profile", rejection["reason"])

    def test_unclaimed_staging_directory_is_not_removed(self):
        self.write_brief("claimed")
        foreign = self.brief_root / ".staging/other-worker"
        foreign.mkdir(parents=True)
        (foreign / "brief.md").write_text("foreign")
        (foreign / ".claimed_by").write_text("other-worker\n")
        self.json_output(self.run_drain("--apply"))
        self.assertTrue((foreign / "brief.md").exists())
        self.assertTrue((foreign / ".claimed_by").exists())

    def test_foreign_fast_drain_staging_is_ignored(self):
        self.write_brief("claimed")
        foreign = self.brief_root / ".staging/fast-drain-foreign"
        foreign.mkdir(parents=True)
        (foreign / "brief.md").write_text("foreign")
        (foreign / ".claimed_by").write_text('{"owner":"another-worker","source_path":".pile/foreign.md"}\n')
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["recovered"], [])
        self.assertTrue((foreign / "brief.md").exists())
        self.assertTrue((foreign / ".claimed_by").exists())

    def test_profile_rejects_wrong_feedback_sink(self):
        fixtures = {
            "decision": "brief_kind: decision\nlegacy_source: decisions-track/decision.md\n",
            "lost_bead_filter": "brief_kind: lost_bead_filter\nfingerprint: fixture\nthreshold_count: 1\ndistinct_bead_count: 1\nreplay_command: bd show source\nfalse_positive_risk: low\n",
            "producer_repair": "brief_kind: producer_repair\nproducer_contract: brief-producer-repair.v1\nrepair_source_formula: fixture\nrepair_failed_gate: G9\nrepair_failure_fingerprint: fixture\nreplay_command: true\n",
        }
        for profile, metadata in fixtures.items():
            brief = self.write_brief(f"wrong-sink-{profile}", profile=profile, extra_frontmatter=metadata)
            if profile == "decision":
                brief.write_text(brief.read_text().replace("\n# Fixture brief", "\naction_block:\n  on_approve: []\n  on_reject: []\n  on_defer: []\n\n# Fixture brief"))
            brief.write_text(brief.read_text().replace("feedback_sink: brief_quality_failure", "feedback_sink: another_sink"))
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["rejected"], sorted(f"wrong-sink-{profile}" for profile in fixtures))
        for profile in fixtures:
            reason = report["reasons"][f"wrong-sink-{profile}"]
            self.assertIn("feedback_sink", reason)

    def test_no_brainer_rejects_malformed_classifier_evidence(self):
        self.write_brief(
            "bad-classifier",
            profile="no_brainer",
            evidence=[
                "G1 Test-evidence: PASS",
                "G5 Server-touching: PASS",
                "G5b User-skill-touching: PASS",
                "G7 Artifacts-staging: PASS",
                "G8 Brief-record: PASS",
                "G9 No-brainer-filter: PASS classifier_state=candidate classified_at=2026-08-16T00:00:00Z",
                "G12 Auto-merge-kill-switch: PASS",
                "G13 Stale-claim: PASS",
                "G14 Test-execution-silent: PASS",
                "G16 Master-current: PASS",
            ],
        )
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["rejected"], ["bad-classifier"])
        self.assertIn("proposed_registry_extension", report["reasons"]["bad-classifier"])

    def test_existing_stack_slug_is_rejected_without_overwrite(self):
        self.write_brief("duplicate")
        stack = self.brief_root / "stack"
        stack.mkdir()
        existing = stack / "duplicate.md"
        existing.write_text("existing stack content\n")
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["rejected"], ["duplicate"])
        self.assertEqual(existing.read_text(), "existing stack content\n")
        self.assertTrue((self.brief_root / ".pile/.rejected/duplicate/brief.md").is_file())
        self.assertIn("duplicate stack slug", report["reasons"]["duplicate"])

    def test_rejection_collision_keeps_claimed_brief_and_reports_skip(self):
        brief = self.write_brief("reject-collision")
        brief.write_text(brief.read_text().replace("G4 Critical-review: PASS", "G4 Critical-review: FAIL"))
        (self.brief_root / ".pile/.rejected/reject-collision").mkdir(parents=True)
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["skipped"], ["reject-collision"])
        staged = list((self.brief_root / ".staging").glob("fast-drain-*-reject-collision/brief.md"))
        self.assertEqual(len(staged), 1)
        self.assertFalse(brief.exists())

    def test_source_disappearing_during_claim_is_skipped(self):
        module = load_drain_module()
        brief = self.write_brief("gone")
        with mock.patch.object(module, "claim", side_effect=FileNotFoundError):
            outcome = module.process_item(brief, self.brief_root, self.gate_config(), True)
        self.assertEqual(outcome.action, "skipped")
        self.assertIn("source disappeared", outcome.reason)

    def test_contended_fast_drain_staging_directory_is_skipped(self):
        module = load_drain_module()
        brief = self.write_brief("contended")
        with mock.patch.object(module.os, "getpid", return_value=4242):
            foreign = self.brief_root / ".staging/fast-drain-4242-contended"
            foreign.mkdir(parents=True)
            (foreign / ".claimed_by").write_text('{"owner":"brief-shuffle-fast-drain"}\n')
            outcome = module.process_item(brief, self.brief_root, self.gate_config(), True)
        self.assertEqual(outcome.action, "skipped")
        self.assertTrue(brief.exists())
        self.assertTrue((foreign / ".claimed_by").exists())

    def test_index_failure_rolls_back_to_staging_and_reports_skip(self):
        module = load_drain_module()
        brief = self.write_brief("index-failure")
        with mock.patch.object(module, "append_index", side_effect=OSError("index unavailable")):
            outcome = module.process_item(brief, self.brief_root, self.gate_config(), True)
        self.assertEqual(outcome.action, "skipped")
        self.assertFalse((self.brief_root / "stack/index-failure.md").exists())
        staged = list((self.brief_root / ".staging").glob("fast-drain-*-index-failure/brief.md"))
        self.assertEqual(len(staged), 1)

    def test_claim_marker_failure_rolls_back_to_pile(self):
        module = load_drain_module()
        brief = self.write_brief("marker-failure")
        original_write_text = Path.write_text

        def fail_marker(path, *args, **kwargs):
            if path.name == ".claimed_by":
                raise OSError("marker unavailable")
            return original_write_text(path, *args, **kwargs)

        with mock.patch.object(Path, "write_text", new=fail_marker):
            outcome = module.process_item(brief, self.brief_root, self.gate_config(), True)
        self.assertEqual(outcome.action, "skipped")
        self.assertTrue(brief.exists())
        self.assertEqual(list((self.brief_root / ".staging").iterdir()), [])

    def test_post_claim_staging_recovers_and_promotes(self):
        module = load_drain_module()
        brief = self.write_brief("post-claim")
        module.claim(brief, self.brief_root, "post-claim")
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["recovered"], ["post-claim"])
        self.assertEqual(report["promoted"], ["post-claim"])
        self.assertEqual(list((self.brief_root / ".staging").iterdir()), [])

    def test_recovery_collision_uses_durable_rejected_disposition(self):
        source = self.write_brief("recovery-collision")
        staging_dir = self.brief_root / ".staging/fast-drain-recovery-collision"
        staging_dir.mkdir(parents=True)
        staged = staging_dir / "brief.md"
        staged.write_text(source.read_text().replace("source-recovery-collision", "staged-recovery-collision"))
        (staging_dir / ".claimed_by").write_text(
            '{"owner":"brief-shuffle-fast-drain","source_path":".pile/recovery-collision.md"}\n'
        )
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["recovered"], ["recovery-collision"])
        self.assertTrue((self.brief_root / ".pile/.rejected/recovery-collision-recovery/brief.md").is_file())
        rejection = json.loads(
            (self.brief_root / ".pile/.rejected/recovery-collision-recovery/rejection.json").read_text()
        )
        self.assertEqual(rejection["rejection_kind"], "operational_recovery_collision")
        self.assertFalse(rejection["feedback_required"])
        self.assertFalse((staging_dir / "brief.md").exists())
        self.assertEqual(list((self.brief_root / ".staging").iterdir()), [])

    def test_rejection_sidecar_failure_rolls_back_to_owned_staging(self):
        module = load_drain_module()
        brief = self.write_brief("sidecar-failure")
        brief.write_text(brief.read_text().replace("G4 Critical-review: PASS", "G4 Critical-review: FAIL"))
        original_write_text = Path.write_text

        def fail_sidecar(path, *args, **kwargs):
            if path.name == "rejection.json":
                raise OSError("sidecar unavailable")
            return original_write_text(path, *args, **kwargs)

        with mock.patch.object(Path, "write_text", new=fail_sidecar):
            outcome = module.process_item(brief, self.brief_root, self.gate_config(), True)
        self.assertEqual(outcome.action, "skipped")
        staged = list((self.brief_root / ".staging").glob("fast-drain-*-sidecar-failure/brief.md"))
        self.assertEqual(len(staged), 1)
        self.assertTrue(staged[0].with_name(".claimed_by").exists())
        self.assertFalse((self.brief_root / ".pile/.rejected/sidecar-failure/brief.md").exists())

    def test_index_failure_staging_recovers_and_promotes(self):
        module = load_drain_module()
        brief = self.write_brief("index-recovery")
        with mock.patch.object(module, "append_index", side_effect=OSError("index unavailable")):
            outcome = module.process_item(brief, self.brief_root, self.gate_config(), True)
        self.assertEqual(outcome.action, "skipped")
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["recovered"], ["index-recovery"])
        self.assertEqual(report["promoted"], ["index-recovery"])

    def test_rejection_sidecar_failure_staging_recovers_and_rejects(self):
        module = load_drain_module()
        brief = self.write_brief("sidecar-recovery")
        brief.write_text(brief.read_text().replace("G4 Critical-review: PASS", "G4 Critical-review: FAIL"))
        original_write_text = Path.write_text

        def fail_sidecar(path, *args, **kwargs):
            if path.name == "rejection.json":
                raise OSError("sidecar unavailable")
            return original_write_text(path, *args, **kwargs)

        with mock.patch.object(Path, "write_text", new=fail_sidecar):
            outcome = module.process_item(brief, self.brief_root, self.gate_config(), True)
        self.assertEqual(outcome.action, "skipped")
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["recovered"], ["sidecar-recovery"])
        self.assertEqual(report["rejected"], ["sidecar-recovery"])
        self.assertTrue((self.brief_root / ".pile/.rejected/sidecar-recovery/rejection.json").is_file())

    # --- all failing gates, not just the first ------------------------------
    #
    # evaluate() returned on the FIRST failing gate, so rejection.json recorded
    # exactly one reason. A repair track built on that data gets one repair item
    # per round trip: fix G4, resubmit, fail G3, resubmit. The drain must report
    # every quality gate that failed so one repair pass can clear them all.
    #
    # Stop gates (G5 server-touching, G5b user-skill-touching, G12 kill-switch)
    # are the deliberate exception: they are `kind = "stop"` in gates.toml and a
    # brief that trips one must NOT be auto-repaired. A stop failure short-
    # circuits, is reported alone, and is marked non-repairable.

    def test_every_failing_quality_gate_is_reported_not_just_the_first(self):
        brief = self.write_brief("many-failures")
        brief.write_text(brief.read_text()
                         .replace("G3 Shell-scripts-testable: PASS", "G3 Shell-scripts-testable: FAIL")
                         .replace("G4 Critical-review: PASS", "G4 Critical-review: FAIL")
                         .replace("G10 Improve-README: PASS", "G10 Improve-README: FAIL"))
        self.json_output(self.run_drain("--apply"))
        rejection = json.loads((self.brief_root / ".pile/.rejected/many-failures/rejection.json").read_text())
        failed = [f["gate"] for f in rejection["failures"]]
        self.assertEqual(failed, ["G3", "G4", "G10"])
        self.assertTrue(all(f["repairable"] for f in rejection["failures"]))

    def test_reason_still_names_the_first_failure_so_fingerprints_are_stable(self):
        # brief-quality-failure-record.py:109 reads `reason` to build
        # failed_gate and failure_fingerprint. Track 1 groups on that
        # fingerprint, so `reason` must keep its exact meaning.
        brief = self.write_brief("stable-fingerprint")
        brief.write_text(brief.read_text()
                         .replace("G3 Shell-scripts-testable: PASS", "G3 Shell-scripts-testable: FAIL")
                         .replace("G4 Critical-review: PASS", "G4 Critical-review: FAIL"))
        report = self.json_output(self.run_drain("--apply"))
        rejection = json.loads((self.brief_root / ".pile/.rejected/stable-fingerprint/rejection.json").read_text())
        self.assertEqual(rejection["reason"], "G3 Shell-scripts-testable: FAIL")
        self.assertEqual(report["reasons"]["stable-fingerprint"], "G3 Shell-scripts-testable: FAIL")

    def test_a_stop_gate_short_circuits_and_is_marked_non_repairable(self):
        brief = self.write_brief("stop-gate")
        brief.write_text(brief.read_text()
                         .replace("G4 Critical-review: PASS", "G4 Critical-review: FAIL")
                         .replace("G5 Server-touching: PASS", "G5 Server-touching: FAIL"))
        self.json_output(self.run_drain("--apply"))
        rejection = json.loads((self.brief_root / ".pile/.rejected/stop-gate/rejection.json").read_text())
        self.assertEqual([f["gate"] for f in rejection["failures"]], ["G5"])
        self.assertFalse(rejection["failures"][0]["repairable"])
        self.assertEqual(rejection["reason"], "G5 Server-touching: FAIL")

    def test_a_passing_brief_records_no_failures(self):
        self.write_brief("clean")
        self.json_output(self.run_drain("--apply"))
        self.assertTrue((self.brief_root / "stack/clean.md").is_file())

    def test_a_frontmatter_error_is_not_reported_as_a_gate_failure(self):
        # Absent means absent: a malformed profile is not a gate that failed.
        self.write_brief("bad-profile", profile="unknown")
        self.json_output(self.run_drain("--apply"))
        rejection = json.loads((self.brief_root / ".pile/.rejected/bad-profile/rejection.json").read_text())
        self.assertEqual(rejection["failures"], [])
        self.assertIn("unknown gate profile", rejection["reason"])

    def test_missing_and_failed_gates_both_appear_in_the_failure_list(self):
        brief = self.write_brief("mixed-failures")
        brief.write_text(brief.read_text()
                         .replace("G3 Shell-scripts-testable: PASS\n", "")
                         .replace("G4 Critical-review: PASS", "G4 Critical-review: BLOCKED"))
        self.json_output(self.run_drain("--apply"))
        rejection = json.loads((self.brief_root / ".pile/.rejected/mixed-failures/rejection.json").read_text())
        by_gate = {f["gate"]: f for f in rejection["failures"]}
        self.assertEqual(by_gate["G3"]["status"], "missing")
        self.assertEqual(by_gate["G4"]["status"], "BLOCKED")

    # --- pile manifest: the fourth representation of a pile brief -------------
    #
    # The disposition moved the file to .pile/.rejected/<slug>/ and wrote
    # rejection.json but left <pile>/manifest.jsonl untouched. On the live city
    # that stranded 22 of 22 rows reading "status": "ready".

    def test_gate_failure_marks_the_pile_manifest_row_rejected(self):
        self.write_pile_manifest(
            {"n": 1, "slug": "gate-fail", "form": "full", "status": "ready",
             "requires_taylor_adjudication": True})
        self.reject_brief("gate-fail")
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["manifest_updated"], ["gate-fail"])
        row = self.read_pile_manifest_rows()[0]
        self.assertEqual(row["status"], "rejected")
        self.assertIn("G4 Critical-review: FAIL", row["rejection_reason"])

    def test_manifest_rejected_at_matches_the_sidecar(self):
        self.write_pile_manifest({"n": 1, "slug": "stamped", "status": "ready"})
        self.reject_brief("stamped")
        self.json_output(self.run_drain("--apply"))
        sidecar = json.loads((self.brief_root / ".pile/.rejected/stamped/rejection.json").read_text())
        self.assertEqual(self.read_pile_manifest_rows()[0]["rejected_at"], sidecar["rejected_at"])

    def test_numbered_brief_filename_resolves_to_its_manifest_row(self):
        self.write_pile_manifest(
            {"n": 18, "slug": "unrelated", "status": "ready"},
            {"n": 19, "slug": "mc-x6a-dead-target-router-beads", "status": "ready"})
        self.reject_brief("19-mc-x6a-dead-target-router-beads-brief")
        self.json_output(self.run_drain("--apply"))
        rows = self.read_pile_manifest_rows()
        self.assertEqual(rows[0]["status"], "ready")
        self.assertEqual(rows[1]["status"], "rejected")

    def test_a_slug_that_itself_ends_in_brief_is_not_over_stripped(self):
        self.write_pile_manifest(
            {"n": 14, "slug": "gt-1f2781-downstream-filter-rule-brief", "status": "ready"},
            {"n": 15, "slug": "gt-1f2781-downstream-filter-rule", "status": "ready"})
        self.reject_brief("14-gt-1f2781-downstream-filter-rule-brief")
        self.json_output(self.run_drain("--apply"))
        rows = self.read_pile_manifest_rows()
        self.assertEqual(rows[0]["status"], "rejected")
        self.assertEqual(rows[1]["status"], "ready")

    def test_only_the_changed_row_is_reserialized(self):
        manifest = self.write_pile_manifest(
            {"n": 1, "slug": "keep-me", "status": "ready", "no_brainer_verdict": "candidate"},
            {"n": 2, "slug": "reject-me", "status": "ready"},
            {"n": 3, "slug": "keep-me-too", "status": "ready", "requires_taylor_adjudication": True})
        before = manifest.read_text().splitlines()
        self.reject_brief("reject-me")
        self.json_output(self.run_drain("--apply"))
        after = manifest.read_text().splitlines()
        self.assertEqual(len(before), len(after))
        self.assertEqual(before[0], after[0])
        self.assertEqual(before[2], after[2])
        self.assertNotEqual(before[1], after[1])

    def test_no_matching_manifest_row_reports_rather_than_invents(self):
        self.write_pile_manifest({"n": 1, "slug": "someone-else", "status": "ready"})
        self.reject_brief("no-row-here")
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["manifest_updated"], [])
        self.assertIn("no manifest row", report["manifest_aborted"]["no-row-here"])
        self.assertEqual(self.read_pile_manifest_rows(),
                         [{"n": 1, "slug": "someone-else", "status": "ready"}])

    def test_ambiguous_manifest_match_writes_nothing(self):
        self.write_pile_manifest({"n": 1, "slug": "twin", "status": "ready"},
                                 {"n": 1, "slug": "twin", "status": "ready"})
        self.reject_brief("twin")
        report = self.json_output(self.run_drain("--apply"))
        self.assertIn("ambiguous", report["manifest_aborted"]["twin"])
        self.assertTrue(all(r["status"] == "ready" for r in self.read_pile_manifest_rows()))

    def test_absent_pile_manifest_does_not_block_the_disposition(self):
        self.reject_brief("no-manifest")
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["rejected"], ["no-manifest"])
        self.assertTrue((self.brief_root / ".pile/.rejected/no-manifest/brief.md").is_file())
        self.assertIn("no pile manifest", report["manifest_aborted"]["no-manifest"])

    def test_manifest_write_failure_leaves_the_disposition_applied(self):
        module = load_drain_module()
        self.write_pile_manifest({"n": 1, "slug": "cache-down", "status": "ready"})
        brief = self.reject_brief("cache-down")
        with mock.patch.object(module, "mark_manifest_rejected", side_effect=OSError("manifest unavailable")):
            outcome = module.process_item(brief, self.brief_root, self.gate_config(), True)
        self.assertEqual(outcome.action, "reject")
        self.assertTrue((self.brief_root / ".pile/.rejected/cache-down/brief.md").is_file())
        self.assertIn("manifest unavailable", outcome.manifest_detail)
        self.assertEqual(self.read_pile_manifest_rows()[0]["status"], "ready")
        self.assertEqual(list((self.brief_root / ".staging").iterdir()), [])

    def test_rerunning_against_an_already_rejected_row_is_idempotent(self):
        self.write_pile_manifest({"n": 1, "slug": "twice", "status": "ready"})
        self.reject_brief("twice")
        self.json_output(self.run_drain("--apply"))
        first = (self.brief_root / ".pile/manifest.jsonl").read_text()
        module = load_drain_module()
        outcome, _ = module.mark_manifest_rejected(self.brief_root, "twice", "other", "2099-01-01T00:00:00Z")
        self.assertEqual(outcome, "unchanged")
        self.assertEqual((self.brief_root / ".pile/manifest.jsonl").read_text(), first)

    def test_promotion_does_not_write_the_pile_manifest(self):
        # Scope boundary, asserted so it is visible rather than assumed: the
        # promotion path leaves the same rows stale and is a separate defect.
        manifest = self.write_pile_manifest({"n": 1, "slug": "promoted-ok", "status": "ready"})
        before = manifest.read_text()
        self.write_brief("promoted-ok")
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["promoted"], ["promoted-ok"])
        self.assertEqual(manifest.read_text(), before)

    def test_failures_carry_the_gates_repair_routing(self):
        # The trinity keys were dead metadata: nothing in the pack read
        # improve_skill or gate_skill. A failure now carries its gate's routing
        # so a repair pass knows what each failure needs.
        brief = self.write_brief("routing")
        brief.write_text(brief.read_text()
                         .replace("G4 Critical-review: PASS", "G4 Critical-review: FAIL")
                         .replace("G14 Test-execution-silent: PASS", "G14 Test-execution-silent: FAIL"))
        self.json_output(self.run_drain("--apply"))
        rejection = json.loads((self.brief_root / ".pile/.rejected/routing/rejection.json").read_text())
        by_gate = {f["gate"]: f for f in rejection["failures"]}
        self.assertEqual(by_gate["G14"]["repair_kind"], "skill")
        self.assertEqual(by_gate["G14"]["repair_skill"], "improve-test-execution-silent")
        # G4 has no repair yet; absent means absent, not a guessed skill name.
        self.assertEqual(by_gate["G4"]["repair_kind"], "unassigned")
        self.assertNotIn("repair_skill", by_gate["G4"])

    def test_a_stop_gate_failure_routes_to_discard(self):
        brief = self.write_brief("discard-route")
        brief.write_text(brief.read_text().replace("G5 Server-touching: PASS", "G5 Server-touching: FAIL"))
        self.json_output(self.run_drain("--apply"))
        rejection = json.loads((self.brief_root / ".pile/.rejected/discard-route/rejection.json").read_text())
        self.assertEqual(rejection["failures"][0]["repair_kind"], "discard")
        self.assertFalse(rejection["failures"][0]["repairable"])

    # --- Canonical pile membership (POLICY B2.3/B2.4/B2.8) --------------
    #
    # The pile DIRECTORY is redundant cache; the pile is the bead query.
    # A file left behind for a brief bead that is already closed is not a
    # pile member and must never be handed to the intake gate.

    def test_closed_brief_bead_is_not_a_pile_member_and_is_left_alone(self):
        self.write_brief("adjudicated-approve")
        self.write_beads({
            "id": "adjudicated-approve",
            "status": "closed",
            "issue_type": "decision",
            "title": "already adjudicated",
        })
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["promoted"], [])
        self.assertEqual(report["rejected"], [])
        self.assertTrue((self.brief_root / ".pile/adjudicated-approve.md").is_file())
        self.assertFalse((self.brief_root / ".pile/.rejected/adjudicated-approve").exists())
        self.assertEqual(
            report["not_pile_members"],
            [{"slug": "adjudicated-approve", "bead": "adjudicated-approve", "status": "closed"}],
        )
        self.assertEqual(report["remaining_pile"], 0)

    def test_open_brief_bead_is_a_pile_member_and_still_drains(self):
        self.write_brief("live-brief")
        self.write_beads({"id": "live-brief", "status": "open", "issue_type": "decision"})
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["promoted"], ["live-brief"])
        self.assertEqual(report["not_pile_members"], [])

    def test_closed_beads_do_not_consume_the_max_items_budget(self):
        # The live symptom: three closed-bead cache files per 8h cycle filled
        # the whole batch, so a real pile member was never reached.
        for slug in ("aaa-closed", "bbb-closed", "ccc-closed"):
            self.write_brief(slug)
        self.write_brief("ddd-live")
        self.write_beads(
            {"id": "aaa-closed", "status": "closed", "issue_type": "decision"},
            {"id": "bbb-closed", "status": "closed", "issue_type": "decision"},
            {"id": "ccc-closed", "status": "closed", "issue_type": "decision"},
            {"id": "ddd-live", "status": "open", "issue_type": "decision"},
        )
        report = self.json_output(self.run_drain("--max-items", "3", "--apply"))
        self.assertEqual(report["promoted"], ["ddd-live"])
        self.assertEqual([row["slug"] for row in report["not_pile_members"]],
                         ["aaa-closed", "bbb-closed", "ccc-closed"])

    def test_slug_suffixed_filename_resolves_to_its_brief_bead(self):
        self.write_brief("mc-abc-some-slug-brief")
        self.write_beads({"id": "mc-abc", "status": "closed", "issue_type": "decision"})
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["rejected"], [])
        self.assertEqual([row["bead"] for row in report["not_pile_members"]], ["mc-abc"])

    def test_ambiguous_prefix_match_is_unresolved_not_closed(self):
        # `mc-ab` must not claim `mc-abc-x.md`; two candidates resolve to
        # neither. Unknown is reported as unknown and the brief still drains.
        self.write_brief("mc-ab-c-x")
        self.write_beads(
            {"id": "mc-ab", "status": "closed", "issue_type": "decision"},
            {"id": "mc-ab-c", "status": "closed", "issue_type": "decision"},
        )
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["not_pile_members"], [])
        self.assertEqual(report["membership_unresolved"], ["mc-ab-c-x"])
        self.assertEqual(report["promoted"], ["mc-ab-c-x"])

    def test_non_decision_bead_never_supplies_membership(self):
        self.write_brief("task-shaped")
        self.write_beads({"id": "task-shaped", "status": "closed", "issue_type": "task"})
        report = self.json_output(self.run_drain("--apply"))
        self.assertEqual(report["not_pile_members"], [])
        self.assertEqual(report["membership_unresolved"], ["task-shaped"])

    def test_unreadable_bead_source_fails_loud_and_drains_nothing(self):
        # P6.1: an unreadable canonical store must not silently degrade to the
        # directory listing -- that IS the defect this filter exists to kill.
        self.write_brief("never-touched")
        self.bead_fixture.write_text("{not json}\n", encoding="utf-8")
        result = self.run_drain("--apply")
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertIn("membership_error", report)
        self.assertEqual(report["promoted"], [])
        self.assertEqual(report["rejected"], [])
        self.assertTrue((self.brief_root / ".pile/never-touched.md").is_file())


if __name__ == "__main__":
    unittest.main()
