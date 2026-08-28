"""report-fix-briefed evidence gate (decision mc-3q4v, design D5 / P6.1 / P6.2).

THE RULE
--------
The dashboard "Report" box drafts a fix-brief only from an evidence-backed report.
`report_fix_evidence_gate.evidence_verdict` is the single code-owner of that rule:
    (a repro OR a locatable code site)  AND  (>=1 related/source bead).
A field carrying the literal `<unknown -- needs input>` placeholder is ABSENT, so
fabricated-looking evidence cannot satisfy the gate.

HOW THIS TEST COULD FAIL (P6.2 -- an OBSERVED failing branch)
-------------------------------------------------------------
The whole point of a fail-closed gate is the refusal path. If the gate were
vacuous (always PASS), `test_blocks_when_no_evidence` and the executed-CLI
`test_cli_refuses_*` cases would fail: they feed the gate a report with no repro,
no code site and no source and REQUIRE it to refuse -- both as a Verdict.ok==False
and as a non-zero process exit with the missing list on stdout. The refusal is
observed, not asserted-into-existence. A gate that only ever saw evidence-present
inputs (the test_r6 vacuous-pass shape) is exactly what this exercises against.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

GATE_TOOL = SCRIPTS_ROOT / "report_fix_evidence_gate.py"

from report_fix_evidence_gate import (  # noqa: E402
    UNKNOWN_MARKER,
    BLOCK_EXIT,
    evidence_verdict,
)


# --- pure-function verdicts -------------------------------------------------

def test_blocks_when_no_evidence():
    """OBSERVED failing branch: no repro, no code site, no source -> refuse, both missing."""
    v = evidence_verdict(repro="", code_site="", sources="")
    assert v.ok is False
    assert "repro-or-code-site" in v.missing
    assert "related-bead-or-source" in v.missing


def test_blocks_when_repro_but_no_source():
    v = evidence_verdict(repro="crashes on `mctl adjudicate` with empty reason", code_site="", sources="")
    assert v.ok is False
    assert v.missing == ["related-bead-or-source"]


def test_blocks_when_source_but_no_repro_or_site():
    v = evidence_verdict(repro="", code_site="", sources="mc-abc")
    assert v.ok is False
    assert v.missing == ["repro-or-code-site"]


def test_passes_with_repro_and_source():
    v = evidence_verdict(repro="steps: open /orders, click cancel -> 500", code_site="", sources="mc-abc")
    assert v.ok is True
    assert v.missing == []


def test_passes_with_code_site_and_source():
    v = evidence_verdict(repro="", code_site="app.py:360 _index_by_id", sources="mc-abc, mc-def")
    assert v.ok is True
    assert v.missing == []


def test_unknown_marker_counts_as_absent():
    """A `<unknown -- needs input>` placeholder must NOT satisfy the gate."""
    v = evidence_verdict(repro=UNKNOWN_MARKER, code_site=UNKNOWN_MARKER, sources="mc-abc")
    assert v.ok is False
    assert "repro-or-code-site" in v.missing


def test_whitespace_only_counts_as_absent():
    v = evidence_verdict(repro="   ", code_site="\t", sources="mc-abc")
    assert v.ok is False


# --- executed CLI (fail-closed exit codes the formula relies on) ------------

def _run(**kw):
    args = [sys.executable, str(GATE_TOOL)]
    for k, val in kw.items():
        args += [f"--{k.replace('_', '-')}", val]
    return subprocess.run(args, capture_output=True, text=True)


def test_cli_refuses_no_evidence_nonzero_exit():
    """OBSERVED: the process the formula intake shells out to actually exits non-zero."""
    r = _run(repro="", code_site="", sources="")
    assert r.returncode == BLOCK_EXIT
    assert r.stdout.startswith("BLOCKED:")
    assert "repro-or-code-site" in r.stdout
    assert "related-bead-or-source" in r.stdout


def test_cli_passes_with_evidence_zero_exit():
    r = _run(repro="open /orders, cancel -> 500", code_site="", sources="mc-abc")
    assert r.returncode == 0
    assert r.stdout.strip() == "PASS"


def test_cli_json_shape():
    # --json is a store_true flag; invoke it bare.
    r = subprocess.run(
        [sys.executable, str(GATE_TOOL), "--json"],
        capture_output=True, text=True,
    )
    assert r.returncode == BLOCK_EXIT
    assert '"ok": false' in r.stdout


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
