"""The standalone drain asset's own copies of two fixes made in mctl_core.

`brief-shuffle-fast-drain.py` ships as a standalone pack asset with no
`mctl_core` on its path, so it carries duplicated copies of the bd query and
its `--readonly` gate. 53aaf42 fixed the gate in `mctl_core` only, and the
standalone copy kept passing `--readonly` unconditionally -- every fast drain
on a proxied rig exited non-zero from 2026-10-08 until the port. These tests
exist so the two copies cannot drift apart silently again.
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "assets/scripts/brief-shuffle-fast-drain.py"


def load_drain_module():
    spec = importlib.util.spec_from_file_location("brief_shuffle_fast_drain_ro", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def store(mode):
    """A rig root whose .beads/metadata.json declares `mode` (None = no file)."""
    root = Path(tempfile.mkdtemp())
    (root / ".beads").mkdir()
    if mode is not None:
        (root / ".beads" / "metadata.json").write_text(json.dumps({"dolt_mode": mode}))
    return root


class ReadonlyGateTests(unittest.TestCase):
    def setUp(self):
        self.drain = load_drain_module()
        self.drain._readonly_args_cache.clear()

    def test_proxied_backend_omits_readonly(self):
        self.assertNotIn("--readonly", self.drain.bd_list_args(store("proxied-server")))

    def test_server_backend_keeps_readonly(self):
        self.assertIn("--readonly", self.drain.bd_list_args(store("server")))

    def test_unclassifiable_store_keeps_readonly(self):
        # The safe default is the stricter one: a store we cannot classify costs
        # availability (bd refuses, the retry recovers) rather than silently
        # surrendering the mutation guard.
        self.assertIn("--readonly", self.drain.bd_list_args(store(None)))
        self.drain._readonly_args_cache.clear()
        self.assertIn("--readonly", self.drain.bd_list_args(store("something-unknown")))

    def test_canonical_query_constant_is_unchanged(self):
        # BD_LIST_ARGS is documented as byte-identical to mctl_core's and is
        # embedded in error text, so it must keep describing the canonical
        # query even though the gate may drop the flag for a given store.
        self.assertIn("--readonly", self.drain.BD_LIST_ARGS)

    def test_refusal_is_detected_on_stdout(self):
        # The non-obvious part: bd reports this on STDOUT with an EMPTY stderr,
        # so a stderr-only check never fires.
        result = subprocess.CompletedProcess(
            [], 1,
            stdout=json.dumps({"code": "proxy.readonly.unsupported",
                               "error": "strict readonly is unavailable"}),
            stderr="",
        )
        self.assertTrue(self.drain._is_proxied_readonly_refusal(result))

    def test_refusal_prose_is_a_fallback_for_older_builds(self):
        result = subprocess.CompletedProcess(
            [], 1, stdout="strict readonly is unavailable for dolt proxied-server", stderr="")
        self.assertTrue(self.drain._is_proxied_readonly_refusal(result))

    def test_unrelated_failure_is_not_a_refusal(self):
        result = subprocess.CompletedProcess(
            [], 1, stdout=json.dumps({"code": "store.locked", "error": "busy"}), stderr="")
        self.assertFalse(self.drain._is_proxied_readonly_refusal(result))

    def test_error_text_prefers_the_json_payload(self):
        # Without this a failure degraded to a bare "bd list ... failed",
        # because `result.stderr.strip() or ...` saw an empty stderr.
        self.assertEqual(
            self.drain._bd_error_text(json.dumps(
                {"code": "proxy.readonly.unsupported",
                 "error": "strict readonly is unavailable"})),
            "strict readonly is unavailable [proxy.readonly.unsupported]",
        )
        self.assertEqual(self.drain._bd_error_text("not json"), "")
        self.assertEqual(self.drain._bd_error_text(None), "")


class GateLabelNormalizationTests(unittest.TestCase):
    def setUp(self):
        self.drain = load_drain_module()

    def test_markdown_markers_do_not_change_the_gate_key(self):
        # STATUS_PATTERN anchors at line start, so a bulleted or bolded label
        # keyed the status under "- G14" / "**G14**" and gate_failure's exact
        # lookup then called a declared, PASSING gate a missing one.
        for line in ("G14: PASSED", "- G14: PASSED", "* G14: PASSED",
                     "+ G14: PASSED", "1. G14: PASSED", "2) G14: PASSED",
                     "  - **G14**: PASSED", "**G14**: PASSED",
                     "_G14_: PASSED", "`G14`: PASSED"):
            with self.subTest(line=line):
                self.assertEqual(self.drain.gate_statuses(line), {"G14": ["PASSED"]})

    def test_internal_underscores_in_a_label_survive(self):
        # Emphasis is peeled from the ENDS only.
        self.assertEqual(
            self.drain.gate_statuses("- G3 test_evidence: PASS"),
            {"G3 test_evidence": ["PASS"]},
        )

    def test_normalization_does_not_launder_a_failure(self):
        # The fix makes a declared gate FINDABLE, never passing. Widening the
        # value side is how a check stops discriminating.
        self.assertEqual(self.drain.gate_statuses("- G14: FAIL"), {"G14": ["FAIL"]})
        self.assertEqual(self.drain.gate_statuses("**G14**: BLOCKED"), {"G14": ["BLOCKED"]})


if __name__ == "__main__":
    unittest.main()
