"""Behavior tests for the Slice 2 read-only mctl brief commands."""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parents[2] / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.beads import read_beads


REPO_ROOT = Path(__file__).resolve().parents[2]
MCTL = REPO_ROOT / "assets" / "scripts" / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"


def runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(
        BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track"
    )
    (rig_root / ".beads").mkdir(exist_ok=True)
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return city_root, rig_root


def empty_rig_cli_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """A rig with a working bead store and zero briefs -- #103's exact shape,
    the CLI-side sibling of `test_mcp_server.py::empty_rig_fixture`."""
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    beads = rig_root / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    (beads / "issues.jsonl").write_text("", encoding="utf-8")
    return city_root, rig_root


def run_mctl(
    *args: str, cwd: Path, beads_fixture: Path | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
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


def tree_digest(root: Path) -> dict[Path, str]:
    return {
        path.relative_to(root): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def beads_fixture(rig_root: Path) -> Path:
    return rig_root / ".beads" / "issues.jsonl"


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(f"{json.dumps(row, sort_keys=True)}\n" for row in rows),
        encoding="utf-8",
    )
    return path


def legacy_manifest(rig_root: Path) -> Path:
    return rig_root / ".beads" / "decisions-track" / "manifest.jsonl"


def test_briefs_list_returns_only_decision_beads_and_supports_filters(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "list", "--status", "pending", "--label", "release", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert [brief["brief_id"] for brief in payload["briefs"]] == ["mc-open"]
    assert payload["briefs"][0]["bead_id"] == "mc-open"
    assert payload["briefs"][0]["canonical_source"] == "bead_store"
    assert payload["diagnostics"] == []
    assert payload["trace_id"]


def test_briefs_show_reports_canonical_bead_redundant_artifacts_and_policy_refs(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "show", "mc-open", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["brief"]["bead_id"] == "mc-open"
    assert payload["brief"]["canonical_source"] == "bead_store"
    assert payload["diagnostics"] == []
    assert {artifact["kind"] for artifact in payload["brief"]["redundant_artifacts"]} == {
        "pile",
        "stack_index",
        "decision_toml",
        "legacy_decisions_track",
    }
    assert payload["brief"]["policy_references"]
    assert payload["trace_id"]


def test_briefs_options_disables_mutations_when_doctor_reports_errors(tmp_path: Path):
    """RE-POINTED by #137 from `mc-broken` to `mc-closed`.

    The behaviour under test -- a blocking diagnostic disables the mutation
    options -- is unchanged and still real. What changed is which diagnostic
    blocks: MBRF004 became WARN so that a producer's omission cannot disable
    Taylor's verdict. `mc-closed` still raises MBRF005/ERROR.

    Its companion below pins the other half: `mc-broken` now ENABLES the
    mutations while still reporting MBRF004. Both are needed -- this one alone
    would pass against a build that disabled everything, and that one alone
    would pass against a build that reported nothing.
    """
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "options", "mc-closed", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    mutation_options = [
        option
        for option in payload["options"]
        if option["id"] in {"adjudicate", "defer", "dispatch-work"}
    ]
    assert mutation_options
    assert all(not option["enabled"] for option in mutation_options)
    assert {option["disabled_reason"]["code"] for option in mutation_options} >= {
        "MBRF005"
    }
    assert "MBRF005" in {diagnostic["code"] for diagnostic in payload["diagnostics"]}
    assert payload["trace_id"]


def test_briefs_options_allows_adjudication_over_a_warning_but_still_reports_it(
    tmp_path: Path,
):
    """#137's whole point, at the options surface: don't block -- record.

    `mc-broken`'s only defect is a missing source link (MBRF004, WARN). The
    human's verdict must be available, AND the defect must still be visible, so
    a later reader can tell a verdict recorded over a known gap from one
    recorded on a clean brief.

    Asserting both directions is load-bearing. Enablement alone would pass
    against a build that silently dropped the diagnostic -- which is exactly how
    the fix for #137 first went wrong: demoting MBRF004 removed it from the
    mutation payload entirely, because the advisories were drawn from the
    blocking subset rather than from all findings.
    """
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "options", "mc-broken", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    adjudicate = next(
        option for option in payload["options"] if option["id"] == "adjudicate"
    )
    assert adjudicate["enabled"], (
        "a producer's omission must not disable the human's verdict (#137)"
    )
    assert "MBRF004" in {diagnostic["code"] for diagnostic in payload["diagnostics"]}, (
        "the finding must still be reported -- unblocking is not unreporting"
    )


def test_briefs_doctor_reports_inconsistent_cache_without_rewriting_fixture_state(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    before = tree_digest(rig_root)

    result = run_mctl(
        *brief_command(city_root, "doctor", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert "MBRF002" in {diagnostic["code"] for diagnostic in payload["diagnostics"]}
    assert payload["severity_counts"]["ERROR"] >= 1
    assert any(
        item["brief_id"] == "mc-file-only" and item["diagnostics"]
        for item in payload["brief_diagnostics"]
    )
    assert tree_digest(rig_root) == before
    assert payload["trace_id"]


def test_briefs_doctor_blocks_unproven_legacy_decisions_track_state(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "doctor", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    codes = {diagnostic["code"] for diagnostic in json.loads(result.stdout)["diagnostics"]}
    assert "MBRF008" in codes
    assert "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED" in codes


def test_brief_commands_fail_closed_from_source_checkout_without_explicit_context():
    result = run_mctl("briefs", "list", "--json", cwd=SOURCE_CHECKOUT)

    assert result.returncode != 0
    assert "MCTL_CONTEXT_SOURCE_CHECKOUT" in result.stderr


def test_brief_commands_require_an_explicit_rig_from_source_checkout(tmp_path: Path):
    city_root, _ = runtime_fixture(tmp_path)

    result = run_mctl(
        "briefs", "list", "--city", str(city_root), "--json", cwd=REPO_ROOT
    )

    assert result.returncode != 0
    assert "MCTL_CONTEXT_SOURCE_CHECKOUT" in result.stderr


def test_runtime_bead_reader_ignores_passive_jsonl_export(monkeypatch, tmp_path: Path):
    _, rig_root = runtime_fixture(tmp_path)

    def canonical_bd_list(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout='[{"id":"mc-canonical","title":"Canonical","status":"open","issue_type":"decision","labels":["brief-open"],"dependencies":["mc-source"]}]',
            stderr="",
        )

    monkeypatch.setattr("mctl_core.beads.subprocess.run", canonical_bd_list)

    assert [bead.id for bead in read_beads(rig_root)] == ["mc-canonical"]


def test_fixture_bead_reader_requires_explicit_fixture_injection(monkeypatch, tmp_path: Path):
    _, rig_root = runtime_fixture(tmp_path)

    def unexpected_bd_list(*args, **kwargs):
        raise AssertionError("explicit fixture loading must not invoke bd")

    monkeypatch.setattr("mctl_core.beads.subprocess.run", unexpected_bd_list)

    assert [bead.id for bead in read_beads(rig_root, fixture_path=beads_fixture(rig_root))] == [
        "mc-open",
        "mc-broken",
        "mc-closed",
        "mc-adjudicated",
        "mc-work",
    ]


def test_legacy_marker_does_not_bypass_the_unproven_migration_blocker(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    marker = (
        rig_root
        / ".beads"
        / "briefs"
        / "migrations"
        / "2026-08-15-decisions-track-inventory.jsonl"
    )
    marker.parent.mkdir(parents=True)
    marker.write_text("historical migration inventory\n")

    result = run_mctl(
        *brief_command(city_root, "doctor", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    codes = {diagnostic["code"] for diagnostic in json.loads(result.stdout)["diagnostics"]}
    assert "MBRF008" in codes
    assert "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED" in codes


def test_doctor_brief_scope_ignores_unrelated_cache_and_legacy_drift(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    doctor = run_mctl(
        *brief_command(city_root, "doctor", "--brief", "mc-open", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )
    options = run_mctl(
        *brief_command(city_root, "options", "mc-open", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert doctor.returncode == 0, doctor.stderr
    assert json.loads(doctor.stdout)["diagnostics"] == []
    assert options.returncode == 0, options.stderr
    by_id = {option["id"]: option for option in json.loads(options.stdout)["options"]}
    assert by_id["adjudicate"]["enabled"]
    assert by_id["defer"]["enabled"]
    assert not by_id["dispatch-work"]["enabled"]


def test_closed_brief_diagnostic_has_canonical_data_location_and_policy_ref(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "doctor", "--brief", "mc-closed", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    diagnostic = next(
        item
        for item in json.loads(result.stdout)["diagnostics"]
        if item["code"] == "MBRF005"
    )
    assert diagnostic["facts"]["data_location"] == "bd list --all --limit 0 --json --readonly (rig database fixture_mathcity)"
    assert diagnostic["facts"]["policy_reference"] == "B2.2"


def test_nonpending_option_diagnostic_has_canonical_data_location_and_policy_ref(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "options", "mc-adjudicated", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    diagnostic = next(
        option["disabled_reason"]
        for option in json.loads(result.stdout)["options"]
        if option["id"] == "adjudicate"
    )
    assert diagnostic["code"] == "MBRF011"
    assert diagnostic["facts"]["data_location"] == "bd list --all --limit 0 --json --readonly (rig database fixture_mathcity)"
    assert diagnostic["facts"]["policy_reference"] == "B2.2"


def test_adjudicated_approved_brief_enables_dispatch_work_only(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "options", "mc-adjudicated", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    by_id = {option["id"]: option for option in json.loads(result.stdout)["options"]}
    assert not by_id["adjudicate"]["enabled"]
    assert not by_id["defer"]["enabled"]
    assert by_id["dispatch-work"]["enabled"]


def test_runtime_bead_reader_uses_complete_readonly_bd_query(monkeypatch, tmp_path: Path):
    _, rig_root = runtime_fixture(tmp_path)
    calls = []

    def canonical_bd_list(*args, **kwargs):
        calls.append((args[0], kwargs))
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=json.dumps(
                [
                    {
                        "id": "mc-canonical",
                        "title": "Canonical",
                        "status": "open",
                        "issue_type": "decision",
                        "labels": [],
                        "dependencies": [],
                    }
                ]
            ),
            stderr="",
        )

    monkeypatch.setattr("mctl_core.beads.subprocess.run", canonical_bd_list)

    assert [bead.id for bead in read_beads(rig_root)] == ["mc-canonical"]
    assert calls[0][0] == ["bd", "list", "--all", "--limit", "0", "--json", "--readonly"]
    assert calls[0][1]["cwd"] == rig_root


def test_runtime_bead_reader_preserves_unlabeled_closed_and_large_result_sets(
    monkeypatch, tmp_path: Path
):
    _, rig_root = runtime_fixture(tmp_path)
    rows = [
        {
            "id": f"mc-{index:03}",
            "title": f"Brief {index}",
            "status": "closed" if index == 54 else "open",
            "issue_type": "decision",
            "labels": [],
            "dependencies": [{"issue_id": f"mc-{index:03}", "depends_on_id": "mc-source", "type": "blocks"}],
            "verdict": "approve" if index == 54 else "",
        }
        for index in range(55)
    ]

    def canonical_bd_list(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout=json.dumps(rows),
            stderr="",
        )

    monkeypatch.setattr("mctl_core.beads.subprocess.run", canonical_bd_list)

    beads = read_beads(rig_root)
    assert len(beads) == 55
    assert beads[-1].id == "mc-054"
    assert beads[-1].status == "closed"
    assert all(bead.is_brief for bead in beads)


def test_bead_reader_uses_outgoing_depends_on_id_for_real_dependency_edges(tmp_path: Path):
    fixture = write_jsonl(
        tmp_path / "beads.jsonl",
        [
            {
                "id": "mc-real",
                "title": "Real edge brief",
                "status": "open",
                "issue_type": "decision",
                "labels": [],
                "dependencies": [
                    {"issue_id": "mc-real", "depends_on_id": "mc-source", "type": "blocks"},
                    {"issue_id": "mc-other", "depends_on_id": "mc-real", "type": "blocks"},
                ],
            }
        ],
    )

    bead = read_beads(tmp_path, fixture_path=fixture)[0]
    assert bead.source_dependencies == ("mc-source",)
    assert bead.is_brief


def test_briefs_list_includes_unlabeled_type_decision_and_closed_briefs(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    fixture = write_jsonl(
        beads_fixture(rig_root),
        [
            {
                "id": "mc-unlabeled",
                "title": "Unlabeled producer brief",
                "status": "open",
                "issue_type": "decision",
                "labels": [],
                "dependencies": [
                    {"issue_id": "mc-unlabeled", "depends_on_id": "mc-source", "type": "blocks"}
                ],
            },
            {
                "id": "mc-closed-real",
                "title": "Closed producer brief",
                "status": "closed",
                "issue_type": "decision",
                "labels": [],
                "dependencies": [
                    {"issue_id": "mc-closed-real", "depends_on_id": "mc-source", "type": "blocks"}
                ],
                "verdict": "approve",
            },
            {
                "id": "mc-work",
                "title": "Not a brief",
                "status": "open",
                "issue_type": "task",
                "labels": ["brief-open"],
            },
        ],
    )

    result = run_mctl(
        *brief_command(city_root, "list", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=fixture,
    )

    assert result.returncode == 0, result.stderr
    listed = json.loads(result.stdout)["briefs"]
    # The bead population, then every document no bead represents, sorted by
    # id. Each is listed rather than hidden and says which store it came from.
    # `mc-open` is a stack file whose bead is absent from this fixture: before
    # Slice 8 nothing read stack files, so it reached no surface at all.
    assert [brief["brief_id"] for brief in listed] == [
        "mc-unlabeled",
        "mc-closed-real",
        "legacy-unmapped",
        "mc-open",
    ]
    assert [brief["source"] for brief in listed] == [
        "bead",
        "bead",
        "manifest",
        "stack_file",
    ]


def test_list_and_show_surface_matching_legacy_migration_blocker(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    write_jsonl(
        legacy_manifest(rig_root),
        [{"slug": "mc-open", "status": "ready", "path": "mc-open.md"}],
    )

    list_result = run_mctl(
        *brief_command(city_root, "list", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )
    show_result = run_mctl(
        *brief_command(city_root, "show", "mc-open", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert list_result.returncode == 0, list_result.stderr
    assert show_result.returncode == 0, show_result.stderr
    for payload in (json.loads(list_result.stdout), json.loads(show_result.stdout)):
        codes = {diagnostic["code"] for diagnostic in payload["diagnostics"]}
        assert "MBRF008" in codes
        assert "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED" in codes


def test_options_surfaces_matching_legacy_migration_blocker(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    write_jsonl(
        legacy_manifest(rig_root),
        [{"slug": "mc-open", "status": "ready", "path": "mc-open.md"}],
    )

    result = run_mctl(
        *brief_command(city_root, "options", "mc-open", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    codes = {diagnostic["code"] for diagnostic in payload["diagnostics"]}
    assert "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED" in codes
    assert all(
        not option["enabled"]
        for option in payload["options"]
        if option["id"] in {"adjudicate", "defer", "dispatch-work"}
    )


def test_malformed_legacy_manifest_fails_closed_with_migration_blocker(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    legacy_manifest(rig_root).write_text("{not-json}\n", encoding="utf-8")

    result = run_mctl(
        *brief_command(city_root, "doctor", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    codes = {diagnostic["code"] for diagnostic in json.loads(result.stdout)["diagnostics"]}
    assert "MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED" in codes


def test_cli_briefs_list_names_the_empty_scope_rather_than_leaving_it_silent(tmp_path: Path):
    """#103: the MCP handler has carried `MCTL_BRIEFS_SCOPE_EMPTY` since
    `a822e14` -- `cli.py` calls `list_briefs_report` directly and never
    rendered it. `mctl briefs list` on an empty rig prints `briefs: []` with
    no hint that `--all-rigs` is the way to tell "nothing here" from "wrong
    scope" apart, which is the exact confusion the finder nearly reported as
    mctl being blind.
    """
    city_root, rig_root = empty_rig_cli_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "list", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["briefs"] == []
    codes = [d["code"] for d in payload["diagnostics"]]
    assert "MCTL_BRIEFS_SCOPE_EMPTY" in codes
    hint = next(d["hint"] for d in payload["diagnostics"] if d["code"] == "MCTL_BRIEFS_SCOPE_EMPTY")
    assert "all_rigs" in hint or "all-rigs" in hint


def test_cli_briefs_doctor_names_the_empty_scope_for_a_whole_rig_check(tmp_path: Path):
    city_root, rig_root = empty_rig_cli_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "doctor", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 0, result.stderr
    codes = {d["code"] for d in json.loads(result.stdout)["diagnostics"]}
    assert "MCTL_BRIEFS_SCOPE_EMPTY" in codes


def test_cli_briefs_doctor_on_one_missing_id_does_not_claim_the_scope_is_empty(tmp_path: Path):
    """A doctor check on a specific, nonexistent id is a different question
    than "does this rig have any briefs" -- the empty-scope hint would be
    misleading here (`--all-rigs` would not resolve a bad id either).

    A missing id is FATAL (`MBRF010`) and exits 1 without a JSON payload --
    a different path entirely from the empty-scope INFO hint, so this checks
    the rendered diagnostic directly rather than parsing stdout as JSON.
    """
    city_root, rig_root = empty_rig_cli_fixture(tmp_path)

    result = run_mctl(
        *brief_command(city_root, "doctor", "--brief", "mc-does-not-exist", "--json"),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode == 1
    assert "MBRF010" in result.stderr
    assert "MCTL_BRIEFS_SCOPE_EMPTY" not in result.stdout
    assert "MCTL_BRIEFS_SCOPE_EMPTY" not in result.stderr
