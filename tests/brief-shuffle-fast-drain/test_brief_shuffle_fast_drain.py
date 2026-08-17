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


if __name__ == "__main__":
    unittest.main()
