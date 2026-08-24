"""The diagnostic code registry and the source must stay in lockstep.

The 1,134-line implementation plan was the sole registry of stable diagnostic
codes, and nothing compared it to the code. That produced three separate
drifts: MWRK001-MWRK003 mean different things in the plan and in work.py,
MOPT001 exists only in the plan, and MBRF010-MBRF013 exist only in the code.

assets/mctl/diagnostics.toml is now the single source of truth. These tests
fail whenever a code is emitted without being registered, or registered
without being reachable — so the drift class cannot silently reappear before
Slice 6 freezes these codes into MCP schemas.
"""
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
CORE = REPO_ROOT / "assets" / "scripts" / "mctl_core"
REGISTRY = REPO_ROOT / "assets" / "mctl" / "diagnostics.toml"

# Names matching the code pattern that are environment variables, not codes.
NOT_CODES = {
    "MCTL_BEADS_FIXTURE",
    "MCTL_ALL_RIGS_DEADLINE_SECONDS",
    "MCTL_BD_TIMEOUT_SECONDS",
    "MCTL_ENABLE_LIVE_DISPATCH",
    "MCTL_MCP_CLIENT_CLASS",
    "MCTL_MCP_ENABLE_EXTERNAL_TOOLS",
}

# Families are a union: MDTB is decisions-to-briefs (#177), MISS/MCMS came
# from main, MORD is orders_status/formulas_catalog reads (#203). A family
# missing from this allowlist is invisible to the scanner, so its codes read as
# "registered but never emitted" however they are written.
CODE_PATTERN = re.compile(
    r'"(MBRF\d{3}|MBRF_[A-Z_]+|MCMS_[A-Z_]+|MCTL_[A-Z_]+|MDTB\d{3}|MISS\d{3}|MOPT\d{3}|MORD_[A-Z_]+|MWRK\d{3}|MWRK_[A-Z_]+)"'
)

VALID_SEVERITIES = {"INFO", "WARN", "ERROR", "FATAL"}


def registered() -> dict[str, dict[str, object]]:
    return tomllib.loads(REGISTRY.read_text(encoding="utf-8"))


def emitted() -> set[str]:
    codes: set[str] = set()
    for path in CORE.glob("*.py"):
        codes |= {m.group(1) for m in CODE_PATTERN.finditer(path.read_text(encoding="utf-8"))}
    return codes - NOT_CODES


def test_registry_exists_and_is_parseable():
    assert REGISTRY.is_file(), f"{REGISTRY} is missing"
    assert registered(), "the diagnostic registry is empty"


def test_every_emitted_code_is_registered():
    unregistered = sorted(emitted() - set(registered()))
    assert not unregistered, (
        f"codes emitted by mctl_core but absent from {REGISTRY.name}: {unregistered}. "
        "Register them, or the plan and the code have drifted again."
    )


def test_every_registered_code_is_reachable():
    stale = sorted(set(registered()) - emitted())
    assert not stale, (
        f"codes registered in {REGISTRY.name} but no longer emitted: {stale}. "
        "Remove them, or restore the check that raised them."
    )


def test_every_registered_code_declares_a_valid_severity():
    bad = {
        code: entry.get("severity")
        for code, entry in registered().items()
        if entry.get("severity") not in VALID_SEVERITIES
    }
    assert not bad, f"invalid severities (plan §4 allows {sorted(VALID_SEVERITIES)}): {bad}"


def test_every_registered_code_documents_a_meaning():
    empty = sorted(code for code, entry in registered().items() if not str(entry.get("meaning", "")).strip())
    assert not empty, f"registered codes with no meaning: {empty}"


def test_severity_registry_matches_the_diagnostics_module():
    """The registry's severity vocabulary must match the code's enum."""
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core.diagnostics import Severity

    assert {severity.value for severity in Severity} == VALID_SEVERITIES
