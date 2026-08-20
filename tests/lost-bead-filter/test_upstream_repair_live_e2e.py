"""RED-phase E2E test (Codex TDD directive, 2026-07-28, BEAD upstream repair track).

Proves the live path this repo's smoke_test.sh does NOT cover: that the
lost-bead-upstream-repair-rollup formula has actually fired against real
(non-fixture) classification data and filed a real linked decision-brief
bead in bd — not just that the Python rollup script's JSONL shape is
correct (smoke_test.sh already covers that).

This test is expected to FAIL until a live dispatch of
lost-bead-upstream-repair-rollup runs naturally against real classification
records and files a real decision brief. It is intentionally NOT satisfied
by fixtures, synthetic data, or force-claims.
"""
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _bd_search(query: str) -> str:
    result = subprocess.run(
        ["bd", "search", query],
        capture_output=True, text=True, cwd=str(Path.home() / "gt"), timeout=20,
    )
    return result.stdout


def test_real_classification_root_has_data():
    """The default classification_root (.beads/lost-bead-classifications)
    must contain at least one real lost-bead-classification.v1 record
    before an upstream rollup can produce anything from live data."""
    candidates = [
        Path.home() / "gt" / ".beads" / "lost-bead-classifications",
        Path.home() / "gt" / "gascity-packs" / ".beads" / "lost-bead-classifications",
    ]
    found = [p for p in candidates if p.exists() and any(p.glob("*.toml"))]
    assert found, (
        "No real (non-fixture) lost-bead-classification.v1 records exist at "
        f"any of {candidates} — the downstream classification step has never "
        "written real cache data to the default classification_root, so the "
        "upstream rollup has nothing real to consume."
    )


def test_real_upstream_repair_decision_brief_exists():
    """A real (bd-created) upstream repair decision brief, per the
    lost-bead-upstream-repair-rollup formula's file-brief step contract
    ('Approve repair R to prevent future beads with failure fingerprint F
    from being lost?'), must exist in bd."""
    hits = _bd_search("Approve repair")
    assert "No issues found" not in hits and hits.strip(), (
        "No upstream repair decision brief has ever been filed in bd "
        "(bd search 'Approve repair' found nothing) — the "
        "lost-bead-upstream-repair-rollup formula's file-brief step has "
        "never fired against real data end-to-end."
    )


if __name__ == "__main__":
    failures = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS: {name}")
            except AssertionError as exc:
                print(f"FAIL: {name} - {exc}")
                failures += 1
    sys.exit(1 if failures else 0)
