"""Behavior tests for the Slice 1 mctl context command."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
MCTL = REPO_ROOT / "assets" / "scripts" / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"


def run_mctl(
    *args: str, cwd: Path, mctl: Path = MCTL
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(mctl), "context", *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def test_context_json_resolves_registered_city_fixture():
    result = run_mctl(
        "--city", str(CITY_ROOT), "--rig", "mathcity", "--json", cwd=REPO_ROOT
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["city_root"] == str(CITY_ROOT.resolve())
    assert payload["rig_id"] == "mathcity"
    assert payload["rig_db"] == "fixture_mathcity"
    assert payload["source_checkout"] == str(SOURCE_CHECKOUT.resolve())
    assert payload["paths_toml"] == str(
        (SOURCE_CHECKOUT / "assets" / "brief-pipeline" / "paths.toml").resolve()
    )
    assert payload["gates_toml"] == str(
        (SOURCE_CHECKOUT / "assets" / "brief-pipeline" / "gates.toml").resolve()
    )
    assert payload["trace_id"]


def test_context_explain_reports_cwd_discovery_and_implicit_rig_warning(tmp_path: Path):
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)

    result = run_mctl("--explain", cwd=city_root)

    assert result.returncode == 0, result.stderr
    assert "City discovery: cwd ancestry" in result.stdout
    assert "MCTL_CONTEXT_IMPLICIT_RIG" in result.stdout


def test_context_from_source_checkout_without_city_fails_closed():
    result = run_mctl("--json", cwd=SOURCE_CHECKOUT)

    assert result.returncode != 0
    assert "MCTL_CONTEXT_SOURCE_CHECKOUT" in result.stderr
    assert "--city <city-root> --rig mathcity" in result.stderr


def test_context_from_nested_source_checkout_does_not_resolve_parent_city(tmp_path: Path):
    city_root = tmp_path / "city_root"
    source_checkout = city_root / "source_checkout"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    (city_root / "city.toml").write_text(
        "[[rigs]]\n"
        'name = "mathcity"\n\n'
        "[rigs.imports.mathcity]\n"
        'source = "source_checkout"\n'
    )
    nested_scripts = source_checkout / "assets" / "scripts"
    nested_scripts.mkdir()
    shutil.copy2(MCTL, nested_scripts / "mctl.py")
    shutil.copytree(MCTL.parent / "mctl_core", nested_scripts / "mctl_core")

    result = run_mctl(
        "--json", cwd=source_checkout, mctl=nested_scripts / "mctl.py"
    )

    assert result.returncode != 0
    assert "MCTL_CONTEXT_SOURCE_CHECKOUT" in result.stderr


def test_context_rejects_unknown_rig():
    result = run_mctl(
        "--city", str(CITY_ROOT), "--rig", "unknown", "--json", cwd=SOURCE_CHECKOUT
    )

    assert result.returncode != 0
    assert "MCTL_CONTEXT_UNKNOWN_RIG" in result.stderr


def test_context_defaults_rig_db_to_rig_id_when_db_is_not_configured(tmp_path: Path):
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    (city_root / "city.toml").write_text(
        "[[rigs]]\n"
        'name = "mathcity"\n\n'
        "[rigs.imports.mathcity]\n"
        'source = "../source_checkout"\n'
    )

    result = run_mctl("--city", str(city_root), "--rig", "mathcity", "--json", cwd=tmp_path)

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["rig_db"] == "mathcity"


@pytest.mark.parametrize("missing_name", ["paths.toml", "gates.toml"])
def test_context_fails_when_required_pipeline_file_is_missing(
    tmp_path: Path, missing_name: str
):
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    (source_checkout / "assets" / "brief-pipeline" / missing_name).unlink()

    result = run_mctl("--city", str(city_root), "--rig", "mathcity", "--json", cwd=tmp_path)

    assert result.returncode != 0
    assert "FATAL" in result.stderr
    assert "MCTL_CONTEXT_MISSING" in result.stderr
