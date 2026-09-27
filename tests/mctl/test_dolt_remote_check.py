"""P1.11's gate: the bead-data remote must reach a verified-private `<repo>-dolt`.

The observed failing case is not synthetic. Every bead store in the fleet --
7 of 7, both machines -- carried:

    git+ssh://git@github.com/./tdupu/mathcity-dolt.git

which GitHub rejects as an invalid repository name, so no store could push. The
cost was that it was never read as a URL defect: `city.toml` recorded it as "the
kolchin ma replica is a flattened, diverged replica that cannot sync" and capped
five agent pools at zero on that basis (#274).

These tests pin the shape logic, which is the part that would have caught it at
any point in the last month.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECK = REPO_ROOT / "assets" / "scripts" / "checks" / "dolt-remote-check.py"


def _module():
    spec = importlib.util.spec_from_file_location("dolt_remote_check", CHECK)
    assert spec and spec.loader, f"cannot load {CHECK}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["dolt_remote_check"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_the_check_script_exists_and_loads():
    assert CHECK.is_file(), f"{CHECK} is missing"
    assert hasattr(_module(), "check_shape")


def test_the_measured_defect_is_a_finding():
    """THE observed failing case (P6.2): the URL every store actually carried."""
    findings = _module().check_shape("git+ssh://git@github.com/./tdupu/mathcity-dolt.git")
    assert findings, "the /./ URL must be a finding -- this is the live defect"
    assert any("'/./'" in f for f in findings), findings


def test_the_corrected_url_is_clean():
    """The passing case, so the gate is not merely 'always red'."""
    assert _module().check_shape("git+ssh://git@github.com/tdupu/mathcity-dolt.git") == []


@pytest.mark.parametrize(
    "url",
    [
        "git+ssh://git@github.com/../tdupu/mathcity-dolt.git",
        "git+ssh://git@github.com/tdupu//mathcity-dolt.git",
    ],
)
def test_other_non_canonical_segments_are_findings(url: str):
    """`/../` is the same class and worse: it resolves somewhere else entirely."""
    assert _module().check_shape(url), f"{url} must be a finding"


def test_a_non_dolt_target_is_a_finding():
    """P1.11 allows bead data only on a dedicated `<repo>-dolt` repository.

    `tdupu/mathcity` is PUBLIC, so this is the case CLAUDE.md forbids outright:
    "Bead data must NEVER be pushed to the code repos."
    """
    findings = _module().check_shape("git+ssh://git@github.com/tdupu/mathcity.git")
    assert any("-dolt" in f for f in findings), findings


def test_a_non_git_backed_scheme_is_a_finding():
    """bd's `NativeSchemes` are the git+* family here; a bare ssh:// is not stored."""
    assert _module().check_shape("ssh://git@github.com/tdupu/mathcity-dolt.git")


@pytest.mark.parametrize(
    "url,expected",
    [
        ("git+ssh://git@github.com/tdupu/mathcity-dolt.git", "tdupu/mathcity-dolt"),
        ("git+ssh://git@github.com/tdupu/hecke-dolt.git", "tdupu/hecke-dolt"),
        # The malformed form must still resolve to the INTENDED target, so the
        # privacy probe reports on the repo the operator meant.
        ("git+ssh://git@github.com/./tdupu/gascity-HQ-dolt.git", "tdupu/gascity-HQ-dolt"),
        ("git+https://github.com/tdupu/mathcity-dolt", "tdupu/mathcity-dolt"),
    ],
)
def test_owner_repo_parsing(url: str, expected: str):
    assert _module().owner_repo(url) == expected


def test_configured_remote_is_read_from_bd_not_from_the_config_file():
    """The two sources disagree, and reading the file would call a fix a success.

    Measured: `.beads/config.yaml` was corrected on this laptop and
    `bd dolt remote list` kept reporting the OLD value, because the remote is
    registered inside the Dolt database. A check that parsed the YAML would have
    reported OK while bd still used the broken URL -- so asking bd is the whole
    point of this function, and that is what is pinned here.
    """
    body = CHECK.read_text(encoding="utf-8").split("def configured_remote")[1].split("\ndef ")[0]

    assert '"bd", "dolt", "remote", "list"' in body, (
        "configured_remote must ask bd for the remote it will actually use"
    )
