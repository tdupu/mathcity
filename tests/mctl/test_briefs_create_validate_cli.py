"""Behavior tests for Slice 5 brief creation and validation.

Creation is bead-first: the canonical `type=decision` bead is written before
any redundant artifact, and a failure after the bead write must leave no
half-written cache behind. Validation is the read-only proof that canonical
and redundant state still agree, so it must never repair what it reports.

These tests drive the CLI through the MCTL_BEADS_FIXTURE seam. The seam
cannot prove a real write works, so creation is *also* covered against a real
bd store in tests/mctl/test_real_bead_store.py.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MCTL = REPO_ROOT / "assets" / "scripts" / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
CREATE_VALIDATE_STATE = FIXTURES / "create_validate_state"


def runtime_fixture(tmp_path: Path, *, legacy_manifest: str = "") -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    shutil.copytree(CREATE_VALIDATE_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(
        CREATE_VALIDATE_STATE / "decisions-track", rig_root / ".beads" / "decisions-track"
    )
    (rig_root / ".beads" / "decisions-track" / "manifest.jsonl").write_text(
        legacy_manifest, encoding="utf-8"
    )
    shutil.copy2(CREATE_VALIDATE_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return city_root, rig_root


def run_mctl(
    *args: str, cwd: Path, beads_fixture: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if beads_fixture is not None:
        env["MCTL_BEADS_FIXTURE"] = str(beads_fixture)
    return subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def brief_command(city_root: Path, *args: str) -> tuple[str, ...]:
    return ("briefs", *args, "--city", str(city_root), "--rig", "mathcity")


def beads_fixture(rig_root: Path) -> Path:
    return rig_root / ".beads" / "issues.jsonl"


def tree_digest(root: Path) -> dict[Path, str]:
    return {
        path.relative_to(root): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def body_file(tmp_path: Path, text: str = "## What is being decided\n\nShip it?\n") -> Path:
    path = tmp_path / "body.md"
    path.write_text(text, encoding="utf-8")
    return path


def diagnostic_codes(payload: dict[str, object]) -> set[str]:
    return {
        str(diagnostic.get("code"))
        for diagnostic in payload.get("diagnostics", [])  # type: ignore[union-attr]
    }


# --------------------------------------------------------------------------
# briefs create
# --------------------------------------------------------------------------


def test_create_dry_run_returns_a_bead_first_plan_and_writes_nothing(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    before = tree_digest(rig_root)

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "Decide dispatch policy",
            "--body-file",
            str(body_file(tmp_path)),
            "--source",
            "mc-source",
            "--dry-run",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is False
    plan = payload["effect_plan"]
    assert plan["operation"] == "briefs.create"
    assert len(plan["bead_creates"]) == 1
    create = plan["bead_creates"][0]
    assert create["issue_type"] == "decision"
    assert create["title"] == "Decide dispatch policy"
    assert create["sources"] == ["mc-source"]
    # The redundant artifacts are planned, but only as consequences of the bead.
    assert plan["file_creates"], "the pile markdown cache must be planned"
    assert plan["cache_updates"], "the decision cache must be planned"
    assert payload["trace_id"] == plan["trace_id"]
    assert tree_digest(rig_root) == before


def test_create_dry_run_does_not_write_a_trace_row(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "Decide dispatch policy",
            "--body-file",
            str(body_file(tmp_path)),
            "--source",
            "mc-source",
            "--dry-run",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    assert not (rig_root / ".beads" / "mctl").exists()


def test_create_writes_the_decision_bead_before_the_redundant_artifacts(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "Decide dispatch policy",
            "--body-file",
            str(body_file(tmp_path)),
            "--source",
            "mc-source",
            "--label",
            "brief-open",
            "--requested-by",
            "operator",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    kinds = [effect["kind"] for effect in payload["actual_effects"]]
    assert kinds[0] == "bead_create", f"the canonical bead must be written first, saw {kinds}"
    assert "pile_markdown" in kinds
    assert "cache_update" in kinds

    new_id = payload["actual_effects"][0]["target"]
    rows = {row["id"]: row for row in read_jsonl(beads_fixture(rig_root))}
    assert new_id in rows
    assert rows[new_id]["issue_type"] == "decision"
    assert rows[new_id]["status"] == "open"
    assert rows[new_id]["labels"] == ["brief-open"]
    assert rows[new_id]["metadata"]["requested_by"] == "operator"
    assert rows[new_id]["dependencies"][0]["depends_on_id"] == "mc-source"

    pile = rig_root / ".beads" / "briefs" / ".pile" / f"{new_id}.md"
    decision_cache = rig_root / ".beads" / "briefs" / "decisions" / f"{new_id}.toml"
    assert pile.is_file()
    assert "What is being decided" in pile.read_text(encoding="utf-8")
    assert f'brief_id = "{new_id}"' in decision_cache.read_text(encoding="utf-8")


def test_create_does_not_write_the_presentable_stack_index(tmp_path: Path):
    """B2.10: producers write to .pile; the shuffler owns .pile -> stack."""
    city_root, rig_root = runtime_fixture(tmp_path)
    stack_index = rig_root / ".beads" / "briefs" / "stack" / ".index.jsonl"
    before = stack_index.read_text(encoding="utf-8")

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "Decide dispatch policy",
            "--body-file",
            str(body_file(tmp_path)),
            "--source",
            "mc-source",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    assert stack_index.read_text(encoding="utf-8") == before


def test_create_records_planned_then_applied_trace_rows(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "Decide dispatch policy",
            "--body-file",
            str(body_file(tmp_path)),
            "--source",
            "mc-source",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    trace_id = json.loads(result.stdout)["trace_id"]
    trace_files = list((rig_root / ".beads" / "mctl" / "traces").glob("*.jsonl"))
    assert trace_files
    phases = [
        row["phase"] for row in read_jsonl(trace_files[0]) if row.get("trace_id") == trace_id
    ]
    assert phases == ["planned", "applied"]


def test_create_rejects_an_empty_title(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "   ",
            "--body-file",
            str(body_file(tmp_path)),
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MBRF030" in result.stderr


def test_create_rejects_an_empty_body(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "Decide dispatch policy",
            "--body-file",
            str(body_file(tmp_path, "\n  \n")),
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MBRF031" in result.stderr


def test_create_rejects_a_bypass_pile_label(tmp_path: Path):
    """B2.4: one fixed pile; urgency is ordering, not a side lane."""
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "Decide dispatch policy",
            "--body-file",
            str(body_file(tmp_path)),
            "--label",
            "urgent-pile",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MBRF032" in result.stderr


def test_create_rejects_a_malformed_label(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "Decide dispatch policy",
            "--body-file",
            str(body_file(tmp_path)),
            "--label",
            "not a label",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MBRF033" in result.stderr


def test_create_rejects_an_unreadable_body_file(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "Decide dispatch policy",
            "--body-file",
            str(tmp_path / "absent.md"),
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MBRF031" in result.stderr


def test_create_without_a_source_warns_that_the_brief_is_incomplete(tmp_path: Path):
    """B2.1: a brief is a decision bead WITH a source link."""
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "Decide dispatch policy",
            "--body-file",
            str(body_file(tmp_path)),
            "--dry-run",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "MBRF034" in diagnostic_codes(payload)
    assert payload["applied"] is False


def test_create_is_blocked_by_legacy_decisions_track_uncertainty(tmp_path: Path):
    city_root, rig_root = runtime_fixture(
        tmp_path, legacy_manifest='{"slug":"mc-legacy","status":"ready"}\n'
    )

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "Decide dispatch policy",
            "--body-file",
            str(body_file(tmp_path)),
            "--source",
            "mc-source",
            "--dry-run",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED" in result.stderr


def test_a_failure_after_bead_creation_leaves_no_half_written_cache(tmp_path: Path):
    """The bead is canonical and survives; the partial cache must not."""
    city_root, rig_root = runtime_fixture(tmp_path)
    decisions = rig_root / ".beads" / "briefs" / "decisions"
    shutil.rmtree(decisions)
    # A regular file where the decision cache directory belongs: the pile
    # write succeeds, the decision cache write then fails.
    decisions.write_text("not a directory\n", encoding="utf-8")
    pile = rig_root / ".beads" / "briefs" / ".pile"
    before = sorted(path.name for path in pile.iterdir())

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "Decide dispatch policy",
            "--body-file",
            str(body_file(tmp_path)),
            "--source",
            "mc-source",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0, "a rolled-back cache write must not report success"
    payload = json.loads(result.stdout)
    assert payload["applied"] is True
    assert "MCTL_REDUNDANT_CACHE_ROLLED_BACK" in diagnostic_codes(payload)

    new_id = payload["actual_effects"][0]["target"]
    rows = {row["id"] for row in read_jsonl(beads_fixture(rig_root))}
    assert new_id in rows, "the canonical bead must survive a redundant-cache failure"
    assert sorted(path.name for path in pile.iterdir()) == before, (
        "the pile markdown written before the failure must have been rolled back"
    )


def test_create_refuses_to_clobber_an_existing_pile_cache(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core.effects import apply_file_create, FileCreate

    path = rig_root / ".beads" / "briefs" / ".pile" / "mc-consistent.md"
    try:
        apply_file_create(FileCreate("pile_markdown", path, "clobbered"))
    except OSError:
        pass
    else:  # pragma: no cover - the assertion below reports the failure
        raise AssertionError("a create effect must refuse to overwrite an existing file")
    assert "Decide the dispatch policy" in path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# briefs validate
# --------------------------------------------------------------------------


def test_validate_succeeds_for_consistent_canonical_and_redundant_state(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "validate", "mc-consistent", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["scope"] == "mc-consistent"
    assert payload["valid"] is True
    assert payload["severity_counts"]["ERROR"] == 0
    assert payload["severity_counts"]["FATAL"] == 0


def test_validate_detects_canonical_and_redundant_divergence(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "validate", "mc-divergent", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["valid"] is False
    assert "MBRF020" in diagnostic_codes(payload)


def test_validate_does_not_repair_the_divergence_it_reports(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    before = tree_digest(rig_root)

    result = run_mctl(
        *brief_command(city_root, "validate", "mc-divergent", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    assert tree_digest(rig_root) == before


def test_validate_reports_stale_redundant_artifacts_without_modifying_them(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    before = tree_digest(rig_root)

    result = run_mctl(
        *brief_command(city_root, "validate", "mc-stale", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "MBRF001" in diagnostic_codes(payload)
    assert tree_digest(rig_root) == before


def test_validate_flags_a_canonical_brief_with_no_redundant_artifact(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "validate", "mc-uncached", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "MBRF021" in diagnostic_codes(payload)
    # A missing cache is redundancy loss, not canonical corruption.
    assert payload["severity_counts"]["ERROR"] == 0


def test_validate_rejects_an_unknown_brief_id(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "validate", "mc-does-not-exist", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MBRF010" in result.stderr


def test_validate_requires_a_brief_id_or_all(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "validate", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MBRF014" in result.stderr


def test_validate_all_returns_aggregate_severity_counts(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "validate", "--all", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["scope"] == "--all"
    counts = payload["severity_counts"]
    assert set(counts) == {"INFO", "WARN", "ERROR", "FATAL"}
    assert counts["ERROR"] >= 1  # mc-divergent
    assert counts["WARN"] >= 1  # mc-uncached
    assert sum(counts.values()) == len(payload["diagnostics"])
    validated = {entry["brief_id"] for entry in payload["brief_diagnostics"]}
    assert {"mc-consistent", "mc-divergent", "mc-stale", "mc-uncached"} <= validated


def test_validate_all_does_not_modify_any_redundant_state(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    before = tree_digest(rig_root)

    result = run_mctl(
        *brief_command(city_root, "validate", "--all", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    assert tree_digest(rig_root) == before


def test_validate_without_json_renders_human_output(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "validate", "--all"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    try:
        json.loads(result.stdout)
    except ValueError:
        pass
    else:  # pragma: no cover - assertion below reports the failure
        raise AssertionError("briefs validate without --json must not emit JSON")
    assert "validate" in result.stdout.lower()
    assert "MBRF020" in result.stdout


def test_create_without_json_renders_human_output(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "Decide dispatch policy",
            "--body-file",
            str(body_file(tmp_path)),
            "--source",
            "mc-source",
            "--dry-run",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    try:
        json.loads(result.stdout)
    except ValueError:
        pass
    else:  # pragma: no cover - assertion below reports the failure
        raise AssertionError("briefs create without --json must not emit JSON")
    assert "briefs.create" in result.stdout
    assert "applied: False" in result.stdout


def test_create_makes_the_brief_root_for_a_registered_rig(tmp_path: Path):
    """#147: creation materialises the cache for a rig whose root resolves.

    SUPERSEDES `test_create_aborts_when_the_resolved_brief_root_does_not_exist`
    and `test_create_dry_run_also_aborts_on_a_missing_brief_root`. Their reasoning
    is preserved here because the concern was legitimate even though the premise
    was false, and the next reader deserves the argument rather than its absence:

        "A missing brief root is a resolution failure, not a directory to make.
         paths.toml declares rig-relative artifact paths, but the live city keeps
         its brief tree at the city root, so the two disagree. Until that is
         settled, an unguarded mkdir would quietly build a parallel shadow tree
         under the rig root and nothing downstream would notice."

    Both claims fail, measured:

    1. "The two disagree." `hq.rig_root` IS the city root, so the tree at
       `<city-root>/.beads/briefs` is hq's OWN rig-relative tree. One tree,
       described twice. A guard against a thing diverging from itself cannot fire
       correctly.
    2. "An unguarded mkdir would build a shadow tree." SEVEN formulas already
       `mkdir -p "{{artifact_root}}/.pile"` unguarded on the normal path
       (stick-dog, #149). The guard forbade in `briefs_create` exactly what the
       pipeline does routinely elsewhere -- preventing the FIRST tree while
       permitting every later one.

    Cost, measured before the change: 6 of 16 registered rigs could never receive
    a FIRST brief; `agent_skills` held 3 decision beads it could not add to; and
    CT4.5 was unsatisfiable for `mathcity`, the rig that owns `mctl`.

    The surviving concern -- something should notice a brief tree appearing where
    one should not -- is pinned by the two refusal tests below. This test is the
    permissive half and is deliberately not shipped alone: on its own it would
    pass against a build that makes directories anywhere, which is the
    shadow-tree fear made real.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    brief_root = rig_root / ".beads" / "briefs"
    shutil.rmtree(brief_root)

    result = run_mctl(
        *brief_command(
            city_root, "create",
            "--title", "Decide dispatch policy",
            "--body-file", str(body_file(tmp_path)),
            "--source", "mc-source",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, f"{result.stdout[:400]}{result.stderr[:400]}"
    assert brief_root.is_dir(), "the brief root was not created"
    for sub in ("stack", ".pile", "decisions"):
        assert (brief_root / sub).is_dir(), f"{sub} was not created"


def test_create_refuses_for_an_unregistered_rig_and_makes_nothing(tmp_path: Path):
    """The restrictive half: creation may not make a tree for a rig that is not one.

    Registration is enforced a layer up -- `MCTL_CONTEXT_UNKNOWN_RIG` fires before
    `briefs_create` resolves any layout -- so this pins that the upstream guard
    stays in front of the newly-permissive one. Asserting the REFUSAL alone would
    not: it also asserts that no directory appeared anywhere under the city.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    before = {p for p in city_root.rglob("briefs") if p.is_dir()}

    result = run_mctl(
        *("briefs", "create", "--title", "x", "--body-file", str(body_file(tmp_path)),
          "--city", str(city_root), "--rig", "not-a-registered-rig", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0, "creation succeeded for an unregistered rig"
    assert "MCTL_CONTEXT_UNKNOWN_RIG" in (result.stdout + result.stderr)
    after = {p for p in city_root.rglob("briefs") if p.is_dir()}
    assert after == before, f"directories appeared for an unregistered rig: {after - before}"


def test_create_refuses_when_the_resolved_path_is_not_a_directory(tmp_path: Path):
    """The other restrictive half: a resolved path that cannot BE a directory.

    `mkdir` would raise here, so a create-on-first-use that assumed it could
    always make the directory would turn a named refusal into an OSError.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    brief_root = rig_root / ".beads" / "briefs"
    shutil.rmtree(brief_root)
    brief_root.write_text("not a directory\n", encoding="utf-8")

    result = run_mctl(
        *brief_command(
            city_root, "create",
            "--title", "x", "--body-file", str(body_file(tmp_path)), "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0, "creation succeeded through a non-directory"
    assert "MBRF035" in (result.stdout + result.stderr), (
        f"refused without the named code: {result.stdout[:300]}{result.stderr[:300]}"
    )

