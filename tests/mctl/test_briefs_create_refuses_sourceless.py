"""#173 / Taylor's ruling: `briefs_create` must REFUSE a sourceless brief.

A refusal at creation is CT13.4 working. A brick at approval is the failure mode.

WHY REFUSING IS RIGHT, not merely ruled. A brief created without a source is made
its OWN source bead at dispatch time (work.py:636), and `briefs_adjudicate` closes
that bead -- so approving it is what makes it permanently undispatchable. CT4.5
MANDATES adjudicating before dispatch. The tool was minting briefs whose
prescribed next step destroys them, and reporting it as a WARN nobody blocks on.

MBRF034 already named the exact condition and cited the right policy (B2.1). Only
its SEVERITY was wrong. This is a severity change, not a new check.

The old reasoning is recorded in BriefCreateInput's own comment -- "Optional, so
creation without one still works and warns instead of silently minting an
unusable brief" -- and is now superseded: warning did not stop the brick.

`--source` / `sources` is a real parameter, so a caller that supplies one is
unaffected. The refusal falls only on OMISSION (QUIMBY's correction, which I
verified against mcp_server.py:1297 before relaying it).

Driven through the CLI rather than at unit level, deliberately: the claim is
"creation refuses", and only the real command can show that.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_briefs_create_validate_cli import (  # noqa: E402
    REPO_ROOT,
    beads_fixture,
    body_file,
    brief_command,
    run_mctl,
    runtime_fixture,
    tree_digest,
)


def create(tmp_path: Path, *extra: str):
    city_root, rig_root = runtime_fixture(tmp_path)
    before = tree_digest(rig_root)
    result = run_mctl(
        *brief_command(
            city_root, "create",
            "--title", "Decide dispatch policy",
            "--body-file", str(body_file(tmp_path)),
            *extra,
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )
    return result, rig_root, before


def codes(payload):
    plan = payload.get("effect_plan") or {}
    return {
        "preconditions": [d["code"] for d in plan.get("preconditions") or []],
        "advisories": [d["code"] for d in plan.get("advisories") or []],
    }


def test_creating_without_a_source_is_REFUSED(tmp_path: Path):
    """The fix. MBRF034 must BLOCK the mutation, not merely mention it.

    The refusal contract is a non-zero exit and a typed FATAL on stderr -- NOT a
    plan on stdout. I wrote this test expecting JSON and was wrong about the
    shape, not the behaviour: a refused mutation produces no plan, which is
    correct and is the point.
    """
    result, _, _ = create(tmp_path, "--dry-run")
    assert result.returncode != 0, "sourceless creation must refuse"
    assert result.stdout.strip() == "", "a refused mutation must not emit a plan"
    assert "MBRF034" in result.stderr, f"the refusal must name the rule: {result.stderr}"
    assert "MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS" in result.stderr


def test_a_refused_creation_writes_NOTHING(tmp_path: Path):
    """A refusal that half-writes is worse than the brick it prevents."""
    result, rig_root, before = create(tmp_path)
    assert tree_digest(rig_root) == before, "a refused creation must leave no artifact"


def test_supplying_a_source_is_UNAFFECTED(tmp_path: Path):
    """The guard must not refuse everything -- that would pass by accident.

    QUIMBY's correction pinned: the brick fires only when sources is OMITTED.
    """
    result, _, _ = create(tmp_path, "--source", "mc-source", "--dry-run")
    assert result.returncode == 0, result.stderr
    seen = codes(json.loads(result.stdout))
    assert "MBRF034" not in seen["preconditions"]
    assert "MBRF034" not in seen["advisories"]


def test_the_refusal_still_tells_the_operator_what_to_do(tmp_path: Path):
    """A refusal without a remedy is a wall, and walls get worked around.

    Making MBRF034 fatal exposed two things the ruling did not anticipate:

    1. Its remedy became UNFOLLOWABLE. It said `bd link <new-brief-id> ...`,
       advice written for a WARN that fired AFTER creation. Refusing means
       there is no new brief id.
    2. `render_diagnostic` (diagnostics.py:78) never prints
       `suggested_next_command` AT ALL -- so every diagnostic's remedy is
       invisible at the CLI. Filed separately; this asserts the remedy reaches
       the operator regardless.
    """
    result, _, _ = create(tmp_path, "--dry-run")
    assert "policy_ref: B2.1" in result.stderr
    assert "blocking_reason:" in result.stderr, "the refusal must say WHY"
    assert "remedy:" in result.stderr, "the refusal must say what to do instead"
    assert "--source" in result.stderr, "the remedy must be followable at creation"
