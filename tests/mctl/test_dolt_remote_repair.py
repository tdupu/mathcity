"""P1.11 repair: correct a malformed bead remote, only after verifying the target.

The companion to `dolt-remote-check.py`. The check found that 7 of 7 stores carry
a `/./` segment GitHub rejects; this repairs one, and refuses rather than
repairing to a target it could not verify.

The refusal cases are the point. A repair that pointed bead data at a PUBLIC repo
would be worse than the breakage it fixes — `tdupu/mathcity` sits beside
`tdupu/mathcity-dolt` and is public, and CLAUDE.md forbids bead data on the code
repo outright.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "assets" / "scripts" / "dolt-remote-repair.py"


def _module():
    spec = importlib.util.spec_from_file_location("dolt_remote_repair", SCRIPT)
    assert spec and spec.loader, f"cannot load {SCRIPT}"
    mod = importlib.util.module_from_spec(spec)
    sys.modules["dolt_remote_repair"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_the_script_exists_and_loads():
    assert SCRIPT.is_file()
    assert hasattr(_module(), "normalize")


@pytest.mark.parametrize(
    "bad,good",
    [
        # THE measured case, on all seven stores.
        (
            "git+ssh://git@github.com/./tdupu/mathcity-dolt.git",
            "git+ssh://git@github.com/tdupu/mathcity-dolt.git",
        ),
        (
            "git+ssh://git@github.com/./tdupu/gascity-HQ-dolt.git",
            "git+ssh://git@github.com/tdupu/gascity-HQ-dolt.git",
        ),
        # `/../` would resolve somewhere ELSE entirely, which is worse than failing.
        (
            "git+ssh://git@github.com/../tdupu/hecke-dolt.git",
            "git+ssh://git@github.com/tdupu/hecke-dolt.git",
        ),
        ("git+https://github.com/tdupu//mathcity-dolt", "git+https://github.com/tdupu/mathcity-dolt"),
    ],
)
def test_normalize_strips_non_canonical_segments(bad: str, good: str):
    assert _module().normalize(bad) == good


def test_normalize_leaves_the_schemes_own_slashes_alone():
    """`://` must survive; a regex that ate it would silently retarget the remote."""
    url = "git+ssh://git@github.com/tdupu/mathcity-dolt.git"
    assert _module().normalize(url) == url


def test_normalize_is_idempotent():
    """A second run must be a no-op, so the script is safe to re-run after a partial."""
    mod = _module()
    once = mod.normalize("git+ssh://git@github.com/./tdupu/mathcity-dolt.git")
    assert mod.normalize(once) == once


@pytest.mark.parametrize(
    "url,expected",
    [
        ("git+ssh://git@github.com/tdupu/mathcity-dolt.git", "tdupu/mathcity-dolt"),
        # The MALFORMED form must still resolve to the INTENDED target, so the
        # privacy probe reports on the repo the operator meant.
        ("git+ssh://git@github.com/./tdupu/gascity-HQ-dolt.git", "tdupu/gascity-HQ-dolt"),
        ("git+https://github.com/tdupu/hecke-dolt", "tdupu/hecke-dolt"),
    ],
)
def test_owner_repo_parsing(url: str, expected: str):
    assert _module().owner_repo(url) == expected


def test_a_public_target_is_refused(monkeypatch):
    """P1.11 allows bead data only on a verified-PRIVATE target.

    `tdupu/mathcity` is public and sits beside `tdupu/mathcity-dolt`; CLAUDE.md
    forbids bead data on the code repo outright. A repair that pointed there
    would be worse than the breakage.
    """
    mod = _module()
    monkeypatch.setattr(
        mod, "run",
        lambda cmd, cwd=None, timeout=60: _fake(cmd, private=False),
    )
    refusals = mod.verify_target(
        "git+ssh://git@github.com/tdupu/mathcity-dolt.git", "tdupu/mathcity-dolt"
    )
    assert any("NOT private" in r for r in refusals), refusals


def test_a_non_dolt_target_is_refused(monkeypatch):
    mod = _module()
    monkeypatch.setattr(mod, "run", lambda cmd, cwd=None, timeout=60: _fake(cmd, private=True))
    refusals = mod.verify_target(
        "git+ssh://git@github.com/tdupu/mathcity.git", "tdupu/mathcity"
    )
    assert any("-dolt" in r for r in refusals), refusals


def test_an_unreachable_target_is_refused(monkeypatch):
    """Unreachable is a refusal, not a warning: the repair would write a dead URL."""
    mod = _module()

    def _unreachable(cmd, cwd=None, timeout=60):
        if cmd[:2] == ["git", "ls-remote"]:
            return _proc(cmd, 128, "", "fatal: repository not found")
        return _fake(cmd, private=True)

    monkeypatch.setattr(mod, "run", _unreachable)
    refusals = mod.verify_target(
        "git+ssh://git@github.com/tdupu/nope-dolt.git", "tdupu/nope-dolt"
    )
    assert any("does not resolve" in r for r in refusals), refusals


def test_a_verified_private_dolt_target_has_no_refusals(monkeypatch):
    """The passing case, so the refusals are not merely 'always red'."""
    mod = _module()
    monkeypatch.setattr(mod, "run", lambda cmd, cwd=None, timeout=60: _fake(cmd, private=True))
    assert mod.verify_target(
        "git+ssh://git@github.com/tdupu/mathcity-dolt.git", "tdupu/mathcity-dolt"
    ) == []


def test_dry_run_writes_nothing(tmp_path: Path):
    """`--apply` is opt-in; the default must not touch the file."""
    mod = _module()
    beads = tmp_path / ".beads"
    beads.mkdir()
    cfg = beads / "config.yaml"
    original = 'sync.remote: "git+ssh://git@github.com/./tdupu/mathcity-dolt.git"\n'
    cfg.write_text(original, encoding="utf-8")

    message = mod.patch_config(
        tmp_path,
        "git+ssh://git@github.com/./tdupu/mathcity-dolt.git",
        "git+ssh://git@github.com/tdupu/mathcity-dolt.git",
        False,
    )

    assert "WOULD" in message
    assert cfg.read_text(encoding="utf-8") == original, "a dry run must not write"


def test_apply_rewrites_only_the_remote(tmp_path: Path):
    mod = _module()
    beads = tmp_path / ".beads"
    beads.mkdir()
    cfg = beads / "config.yaml"
    cfg.write_text(
        'dolt.mode: server\n'
        'sync.remote: "git+ssh://git@github.com/./tdupu/mathcity-dolt.git"\n'
        'other.key: keep-me\n',
        encoding="utf-8",
    )

    mod.patch_config(
        tmp_path,
        "git+ssh://git@github.com/./tdupu/mathcity-dolt.git",
        "git+ssh://git@github.com/tdupu/mathcity-dolt.git",
        True,
    )

    text = cfg.read_text(encoding="utf-8")
    assert "github.com/tdupu/mathcity-dolt.git" in text
    assert "/./" not in text
    assert "dolt.mode: server" in text, "unrelated keys must survive"
    assert "other.key: keep-me" in text


def _proc(cmd, code, out, err):
    import subprocess

    return subprocess.CompletedProcess(cmd, code, out, err)


def _fake(cmd, *, private: bool):
    if cmd[:2] == ["git", "ls-remote"]:
        return _proc(cmd, 0, "deadbeef\tHEAD\n", "")
    if cmd[:3] == ["gh", "repo", "view"]:
        return _proc(cmd, 0, '{"isPrivate": %s}' % ("true" if private else "false"), "")
    return _proc(cmd, 0, "", "")
