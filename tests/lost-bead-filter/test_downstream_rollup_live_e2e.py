#!/usr/bin/env python3
"""RED-phase E2E test for the downstream lost-bead filter/rollup chain.

Unlike smoke_test.sh (which validates schema-shaped TOML fixtures only),
this test builds REAL bd beads (source beads + linked event beads), runs
the real lost-bead-filter.py rollup-downstream script against them, and
then checks whether a linked `type=decision` brief was actually filed --
proving (or disproving) the full chain described in
lost-bead-classification-rollup.toml's "file-brief" step, not just the
script-level candidate JSONL.

Expected result as of 2026-07-28: FAILS. The formula's "file-brief" step
is pure LLM-dispatched prose (bd create/bd dep add run by a live
mathcity.brief-operator worker reading the step description) -- there is
no deterministic script that performs it. This test intentionally proves
that gap rather than mocking it away.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ROLLUP_SCRIPT = REPO_ROOT / "assets/scripts/lost-bead-filter.py"

CLASSIFICATION_TEMPLATE = '''schema = "lost-bead-classification.v1"
bead_id = "{bead_id}"
observed_at = "2026-07-29T00:00:0{i}Z"
observer = "{event_id}"

[finding]
lost_class = "immediate_strand"
evidence = ["RED-test synthetic evidence {i}"]

[disposition]
recommendation = "resling"
rationale = "RED-test synthetic rationale"
reversible = true

[root_cause]
class = "no_worker_claimed"
suspected_source = "math-city-work"
repair_candidate = true
fingerprint = "red_test_synthetic_fingerprint"
'''


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30, **kw)


def bd_create(cwd, title, issue_type="task"):
    result = run(["bd", "create", title, "-t", issue_type, "--silent"], cwd=cwd)
    if result.returncode != 0:
        print(f"bd create failed: {result.stderr}", file=sys.stderr)
        raise SystemExit(1)
    return result.stdout.strip()


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        init = run(["bd", "init", "--quiet"], cwd=scratch)
        if init.returncode != 0:
            print(f"bd init failed: {init.stderr}", file=sys.stderr)
            return 1

        source_ids = [bd_create(scratch, f"source-work-item-{i}") for i in range(3)]
        event_ids = [bd_create(scratch, f"lost-bead-classification observation {i}", "event") for i in range(3)]
        for eid, sid in zip(event_ids, source_ids):
            link = run(["bd", "dep", "relate", eid, sid], cwd=scratch)
            if link.returncode != 0:
                print(f"bd dep relate failed: {link.stderr}", file=sys.stderr)
                return 1

        classification_root = scratch / "classifications"
        classification_root.mkdir()
        for i, (sid, eid) in enumerate(zip(source_ids, event_ids)):
            (classification_root / f"{sid}.toml").write_text(
                CLASSIFICATION_TEMPLATE.format(bead_id=sid, event_id=eid, i=i)
            )

        output_path = scratch / "downstream-candidates.jsonl"
        rollup = run(
            [
                "python3", str(ROLLUP_SCRIPT), "rollup-downstream",
                "--input", str(classification_root),
                "--threshold", "3",
                "--output", str(output_path),
            ]
        )
        if rollup.returncode != 0:
            print(f"rollup-downstream failed unexpectedly: {rollup.stderr}", file=sys.stderr)
            return 1

        candidates = [json.loads(line) for line in output_path.read_text().splitlines() if line.strip()]
        if len(candidates) != 1 or candidates[0]["kind"] != "downstream_filter_rule":
            print("FAIL (unexpected): script-level candidate JSONL was not produced as expected.", file=sys.stderr)
            return 1
        print("GREEN (script level): rollup-downstream correctly grouped 3 real bd-created "
              "event/source beads into 1 downstream_filter_rule candidate.")

        # --- This is the part that is expected to be RED ---
        decisions = run(["bd", "list", "-t", "decision", "--json"], cwd=scratch)
        decision_beads = json.loads(decisions.stdout) if decisions.stdout.strip() else []

        linked_decision = None
        for d in decision_beads:
            tree = run(["bd", "dep", "tree", d["id"], "--json"], cwd=scratch)
            linked_ids = set()
            try:
                tree_data = json.loads(tree.stdout) if tree.stdout.strip() else {}
                linked_ids = {n.get("id") for n in tree_data.get("nodes", [])} if isinstance(tree_data, dict) else set()
            except json.JSONDecodeError:
                pass
            if set(event_ids).issubset(linked_ids):
                linked_decision = d
                break

        if linked_decision is None:
            print(
                "RED (expected failure): no `type=decision` bead was created and linked to all 3 "
                "contributing classification event beads after rollup-downstream produced a "
                "threshold candidate. The formula's 'file-brief' step (needs=collect-labels) is "
                "pure LLM-dispatched prose in lost-bead-classification-rollup.toml -- it instructs "
                "a live mathcity.brief-operator worker to run `bd create --type decision` + "
                "`bd dep add`, but no deterministic script performs this. Filing the brief, linking "
                "it to the contributing event/source beads, and including the replay command + "
                "false-positive risk currently requires a real LLM-dispatched formula run; it "
                "cannot be proven or exercised as a pure script-level GREEN test.",
                file=sys.stderr,
            )
            return 1

        body = linked_decision.get("description", "")
        missing = [
            field for field in ("replay", "false-positive", "fingerprint")
            if field not in body.lower()
        ]
        if missing:
            print(f"RED (expected failure): linked decision brief exists but is missing required "
                  f"content: {missing}", file=sys.stderr)
            return 1

        for sid in source_ids:
            src = run(["bd", "show", sid, "--json"], cwd=scratch)
            src_data = json.loads(src.stdout)
            if isinstance(src_data, list):
                src_data = src_data[0]
            if src_data.get("status") != "open":
                print(f"RED (expected failure): source bead {sid} was mutated (status="
                      f"{src_data.get('status')}) -- file-brief must not mutate source beads.",
                      file=sys.stderr)
                return 1

        print("GREEN (full chain): linked decision brief filed correctly, no source beads mutated.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
