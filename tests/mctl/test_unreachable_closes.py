"""Commits claimed by closed beads that no ref can reach.

THE FINDING (QUIMBY 71, ritt, 2026-09-17). Of 62 commit claims made by beads
closed 09-10..09-17, **50 are held by no ref at all** -- re-derived twice, once
with `git branch -a --contains` and again with `git for-each-ref --contains`
across every namespace. The four "in main" are all the same base commit,
recorded by steps titled "Implement owned work". Zero commits claimed by any
bead closed in that window are reachable as new work on main.

WHY THREE-VALUED AND NOT TWO. QUIMBY reproduced the anchoring mechanism in a
scratch repo rather than reasoning about it, and it broke the obvious design:
`git branch --contains` is **blind to `refs/salvage/`**. A two-valued sweep
therefore re-reports every commit it has already anchored, every tick, forever
-- a catch rate that can never reach zero. A detector that cannot succeed is
the same family as a check that cannot fail.

    reachable  a branch contains it                    -- fine
    anchored   any ref contains it (tags, salvage, ..) -- PRESERVED, not a finding
    stranded   neither                                 -- counts

WHY TWO FIGURES THAT NEVER MERGE. Once anchored, stranded commits go quiet
while **none has landed**. A single number reports zero while fifty sit
preserved and unlanded -- B2.13 committed by the remedy. So the report carries
`new this period` (must reach zero before enforcement is licensed) and
`standing anchored-not-landed` (falls only when a commit truly reaches a
branch), and never adds them.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "assets" / "scripts" / "check_unreachable_closes.py"


def _git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args],
                          capture_output=True, text=True).stdout.strip()


def _repo(tmp_path: Path) -> Path:
    r = tmp_path / "repo"
    r.mkdir()
    _git(r, "init", "-q", "-b", "main")
    _git(r, "config", "user.email", "t@example.com")
    _git(r, "config", "user.name", "t")
    (r / "f").write_text("1")
    _git(r, "add", "f"); _git(r, "commit", "-qm", "base")
    return r


def test_script_exists():
    assert SCRIPT.is_file(), f"{SCRIPT} missing -- every test below is vacuous"


def test_classifies_reachable_anchored_and_stranded(tmp_path):
    """The three states must be distinguished. Collapsing anchored into
    stranded is the bug that makes the catch rate unreachable."""
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))
    import importlib
    mod = importlib.import_module("check_unreachable_closes")

    r = _repo(tmp_path)
    reachable = _git(r, "rev-parse", "HEAD")

    # a commit on a branch, then the branch deleted -> stranded
    _git(r, "checkout", "-q", "-b", "tmp")
    (r / "g").write_text("2"); _git(r, "add", "g"); _git(r, "commit", "-qm", "stranded")
    stranded = _git(r, "rev-parse", "HEAD")
    _git(r, "checkout", "-q", "main"); _git(r, "branch", "-qD", "tmp")

    # another, anchored under refs/salvage/ -> preserved, NOT a finding
    _git(r, "checkout", "-q", "-b", "tmp2")
    (r / "h").write_text("3"); _git(r, "add", "h"); _git(r, "commit", "-qm", "anchored")
    anchored = _git(r, "rev-parse", "HEAD")
    _git(r, "update-ref", "refs/salvage/keep", anchored)
    _git(r, "checkout", "-q", "main"); _git(r, "branch", "-qD", "tmp2")

    assert mod.classify(r, reachable) == "reachable"
    assert mod.classify(r, stranded) == "stranded"
    assert mod.classify(r, anchored) == "anchored", (
        "refs/salvage/ must count as anchored; git branch --contains cannot see it")


def test_anchored_is_not_reported_as_a_finding(tmp_path):
    """The regression guard: a two-valued sweep re-reports what it anchored."""
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))
    import importlib
    mod = importlib.import_module("check_unreachable_closes")

    r = _repo(tmp_path)
    _git(r, "checkout", "-q", "-b", "t")
    (r / "x").write_text("x"); _git(r, "add", "x"); _git(r, "commit", "-qm", "a")
    sha = _git(r, "rev-parse", "HEAD")
    _git(r, "update-ref", "refs/salvage/keep", sha)
    _git(r, "checkout", "-q", "main"); _git(r, "branch", "-qD", "t")

    rep = mod.report(r, [("bead-1", sha)])
    assert rep["stranded"] == 0, "an anchored commit must not count as stranded"
    assert rep["anchored_not_landed"] == 1, (
        "but it must remain visible -- it is preserved, not landed")


def test_the_two_figures_are_never_merged(tmp_path):
    """Reporting one number says zero while N sit preserved and unlanded."""
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))
    import importlib
    mod = importlib.import_module("check_unreachable_closes")

    r = _repo(tmp_path)
    shas = []
    for i in range(2):
        _git(r, "checkout", "-q", "-b", f"b{i}")
        (r / f"f{i}").write_text(str(i)); _git(r, "add", f"f{i}")
        _git(r, "commit", "-qm", f"c{i}")
        shas.append(_git(r, "rev-parse", "HEAD"))
        _git(r, "checkout", "-q", "main"); _git(r, "branch", "-qD", f"b{i}")
    _git(r, "update-ref", "refs/salvage/one", shas[0])

    rep = mod.report(r, [("b1", shas[0]), ("b2", shas[1])])
    assert rep["stranded"] == 1
    assert rep["anchored_not_landed"] == 1
    assert "total" not in rep, "the two figures must not be summed into one"


def test_missing_commit_is_its_own_class(tmp_path):
    """A SHA no object exists for is not 'stranded' -- it may be foreign."""
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))
    import importlib
    mod = importlib.import_module("check_unreachable_closes")
    r = _repo(tmp_path)
    assert mod.classify(r, "0" * 40) == "absent"
