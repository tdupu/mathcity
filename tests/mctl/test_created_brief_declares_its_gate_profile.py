"""A brief `briefs_create` writes must declare the gate profile it is graded by.

THE DEFECT (mc-0q6po). `plan_create_brief` mints a bead with
`issue_type="decision"` -- the call KNOWS the artifact is a decision. But
`_pile_document` writes only `status` and `source_bead`, never `gate_profile`.

The drain then falls back to the registry default: `gates.toml` declares
`default_profile = "standard"`, and `brief-shuffle-fast-drain.py` resolves
`metadata.get("gate_profile", ...default_profile...)`. So a DECISION brief is
graded against the STANDARD profile.

    profiles.standard = 18 gates -- G1..G17 (incl. G5b)
    profiles.decision =  7 gates -- G5, G5b, G8, G9, G11, G12, G13

A decision brief is therefore required to satisfy G3 shell-scripts-testable, G2
good-test, G6 LaTeX-gate, G10/G15 improve-README and G16 master-current. It
cannot: it has no shell surface, no test, no README surface and no runnable
artifact. The typed surface writes briefs it has made structurally impossible to
promote, and the pile fills with them -- measured 2026-08-29 on the live
mathcity rig: 35 real pile members, ONE promotable.

This is the same shape as the `source_bead` defect that
`test_created_brief_carries_provenance.py` covers -- a fact the creating call
already holds, dropped on the floor, and reconstructed nowhere downstream.

HOW THESE TESTS COULD FAIL (P6.2). The profile assertion drives the REAL create
path through the CLI and reads the document off disk, so it is red before the
fix and green after. The gate assertions are paired with NEGATIVE CONTROLS: a
brief that genuinely fails a decision-profile gate must STILL be rejected, and
the standard profile must STILL enforce its own wider gate set. Otherwise
"declare a profile" would degrade into "opt out of grading", which is worse than
the defect.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_briefs_create_validate_cli import (  # noqa: E402
    DEFAULT_BODY as BODY,
    beads_fixture,
    body_file,
    brief_command,
    run_mctl,
    runtime_fixture,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mctl_core.fields import read_frontmatter  # noqa: E402

SOURCE_BEAD = "mc-source"
GATE_CONFIG = REPO_ROOT / "assets" / "brief-pipeline" / "gates.toml"


def _drain():
    """The drain script, loaded as a module (hyphenated pack asset)."""
    path = SCRIPTS / "brief-shuffle-fast-drain.py"
    spec = importlib.util.spec_from_file_location("brief_shuffle_fast_drain", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _create(tmp_path: Path) -> Path:
    """Create a brief for real, with a source, and return its pile document."""
    city_root, rig_root = runtime_fixture(tmp_path)
    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "gate profile contract probe",
            "--body-file",
            str(body_file(tmp_path, BODY)),
            "--source",
            SOURCE_BEAD,
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )
    assert result.returncode == 0, f"create failed: {result.stdout}\n{result.stderr}"
    payload = json.loads(result.stdout)
    created = [
        e for e in payload.get("actual_effects", []) if e.get("kind") == "pile_markdown"
    ]
    assert created, f"no pile document was written: {payload.get('actual_effects')}"
    return Path(created[0]["path"])


def test_a_created_brief_declares_the_profile_it_will_be_graded_by(tmp_path: Path):
    """Red before the fix: frontmatter was `status` + `source_bead` and nothing else."""
    front = read_frontmatter(_create(tmp_path).read_text(encoding="utf-8"))

    assert front.get("gate_profile") == "decision", (
        "the created document does not declare a gate profile, so the drain "
        "grades this decision brief against the 18-gate standard profile it "
        f"cannot satisfy: {dict(front)!r}"
    )


def test_a_created_brief_names_its_kind(tmp_path: Path):
    """The decision profile refuses a brief whose `brief_kind` is not `decision`."""
    front = read_frontmatter(_create(tmp_path).read_text(encoding="utf-8"))

    assert front.get("brief_kind") == "decision", (
        "the decision profile rejects with 'decision brief must set brief_kind: "
        f"decision', so declaring the profile without the kind trades one "
        f"rejection for another: {dict(front)!r}"
    )


def test_the_declared_profile_is_one_the_gate_registry_actually_defines():
    """A profile name nothing defines would fail open or crash the drain."""
    with GATE_CONFIG.open("rb") as handle:
        config = tomllib.load(handle)

    assert "decision" in config.get("profiles", {}), (
        "the profile this writer declares must exist in gates.toml, or the "
        "declaration names nothing"
    )


def test_the_decision_profile_is_narrower_than_the_standard_one():
    """The whole point: standard demands gates a decision brief cannot satisfy.

    If these two sets were equal the fix would be cosmetic, so this asserts the
    premise the defect rests on rather than assuming it.
    """
    with GATE_CONFIG.open("rb") as handle:
        config = tomllib.load(handle)
    standard = set(config["profiles"]["standard"]["gates"])
    decision = set(config["profiles"]["decision"]["gates"])

    assert decision < standard, (
        "the decision profile must be a strict subset of standard, or grading a "
        "decision brief as standard would cost nothing"
    )
    # The gates a decision brief has no surface to satisfy.
    for gate in ("G2", "G3", "G6", "G10", "G16"):
        assert gate in standard and gate not in decision, (
            f"{gate} is the kind of gate that makes standard-grading fatal for a "
            "decision brief; if it moved, this test's premise needs rewriting"
        )


def test_control_the_decision_profile_still_rejects_a_bad_brief():
    """Declaring a profile must not become a way to opt out of grading."""
    drain = _drain()
    # Correct profile and kind, but no source and no action_block.
    metadata = {"status": "open", "gate_profile": "decision", "brief_kind": "decision"}

    assert drain.profile_error("decision", metadata, "# body\n") is not None, (
        "a decision brief missing feedback_sink/source_bead/action_block must "
        "still be rejected -- otherwise the profile declaration is a bypass"
    )


def test_control_the_standard_profile_still_enforces_its_wider_gate_set():
    """The standard path must be untouched by this change."""
    drain = _drain()
    unprovenanced = {"status": "open"}

    assert (
        drain.profile_error("standard", unprovenanced, "# body\n")
        == "standard brief missing provenance metadata"
    ), "the standard profile must keep rejecting an unprovenanced brief"
