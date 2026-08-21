"""#137 — a verdict must be recordable on a brief whose producer omitted the source link.

THE DEFECT
----------
`MBRF004` ("Brief bead has no source dependency", B2.1) is severity **ERROR**, and
the mutation path blocks on ERROR or FATAL. So `briefs_adjudicate` on such a brief
returns `MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS` and **the verdict cannot be written
at all**. A producer omitting a field makes the brief permanently unadjudicable —
the gap between a queue Taylor can read and a decision he can record.

HOW THESE TESTS COULD HAVE FAILED (P6.2)
----------------------------------------
The obvious wrong version of this file adjudicates a brief that *already has* a
dependency, watches it succeed, and reports the gate healthy. That fixture cannot
fail, because it never constructs the condition. So the variable is isolated
explicitly and asserted in three directions, with the two controls run against
today's code:

  * `test_control_a_...`  a bead WITH a dependency adjudicates.  PASSES today.
    If this ever fails, the harness is broken and every verdict below is void.
  * `test_a_verdict_can_be_recorded_...`  a bead with NO dependency and NO
    declaration.  **FAILS today**, with MBRF004 as the blocking code. This is the
    issue.
  * `test_control_b_...`  a bead that DECLARES it has no subject (B2.1a).
    PASSES today, via MBRF056/INFO.

Control B is the load-bearing one for whoever fixes this: **the escape hatch
already exists.** `declares_no_subject()` reads a `no-subject` label, a
`[no-subject]` title tag, or a whole-line `Source: none`. So the fix is not
"invent a way to say the brief has no subject" — it is deciding what to do about
briefs that are silent, which B2.1a deliberately treats as different from briefs
that declare. Any fix that makes silence compliant erases that distinction, and
the diagnostic's own comment says why it must not: *"silence must not become
compliance, or the diagnostic becomes a no-op for the omissions it exists to
surface."*

The three beads differ in EXACTLY ONE field each. Nothing else varies.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
MCTL = SCRIPTS_ROOT / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"

FRONTMATTER = "---\nstatus: ready-for-adjudication\n---\n\nBody.\n"

#: The one field under test. Everything else about these three beads is identical.
WITH_DEPENDENCY = {"dependencies": [{"issue_id": "mc-source", "type": "blocks"}]}
OMITTED = {}                                   # silent: no link, no declaration
DECLARED = {"labels": ["brief-open", "no-subject"]}   # B2.1a declaration


def _seed(tmp_path: Path, bead_id: str, variant: dict) -> tuple[Path, Path]:
    """Build a city fixture holding one brief bead shaped by `variant`."""
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(
        BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track"
    )
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")

    bead = {
        "id": bead_id,
        "title": "Brief under test",
        "status": "open",
        "issue_type": "decision",
        "labels": ["brief-open"],
        "created_at": "2026-08-10T12:00:00Z",
        "updated_at": "2026-08-11T12:00:00Z",
    }
    bead.update(variant)

    brief_root = rig_root / ".beads" / "briefs"
    with (rig_root / ".beads" / "issues.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(bead) + "\n")
    (brief_root / "decisions" / f"{bead_id}.toml").write_text(
        f'brief_id = "{bead_id}"\ntitle = "Brief under test"\nstatus = "open"\n',
        encoding="utf-8",
    )
    for path in (brief_root / "stack" / f"{bead_id}.md", brief_root / ".pile" / f"{bead_id}.md"):
        path.write_text(FRONTMATTER, encoding="utf-8")
    return city_root, rig_root


def _adjudicate(city_root: Path, rig_root: Path, bead_id: str) -> subprocess.CompletedProcess:
    """Apply is the DEFAULT; `--dry-run` is the opt-out. There is no `--apply`.

    `MCTL_BEADS_FIXTURE` is how the suite points mctl at a fixture bead store —
    without it the run exits 2 on context resolution, which is a usage error and
    not the gate. Control A caught exactly that on the first run of this file.
    """
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
    return subprocess.run(
        [
            sys.executable, str(MCTL), "briefs", "adjudicate", bead_id,
            "--city", str(city_root), "--rig", "mathcity",
            "--verdict", "approve", "--reason", "recorded by #137 test",
            "--json",
        ],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT), check=False,
    )


def _blocking_code(result: subprocess.CompletedProcess) -> str | None:
    """The refusal is written to STDERR, not the `--json` payload.

    A blocked mutation prints nothing on stdout and emits

        [FATAL] MCTL_MUTATION_BLOCKED_BY_DIAGNOSTICS: ...
        blocking_code: MBRF004

    on stderr. Parsing stdout returns nothing, which is why the first draft of
    this file reported `blocking codes = []` next to a real refusal — a failing
    test that could not say WHY it failed, which is the same defect class as a
    passing test that could not fail.
    """
    for line in (result.stderr or "").splitlines():
        if line.startswith("blocking_code:"):
            return line.split(":", 1)[1].strip()
    return None


# --- CONTROL A -------------------------------------------------------------
def test_control_a_a_brief_with_a_source_dependency_can_be_adjudicated(tmp_path: Path):
    """If this fails the fixture is wrong and every verdict below is meaningless."""
    city_root, rig_root = _seed(tmp_path, "mc-dep", WITH_DEPENDENCY)
    result = _adjudicate(city_root, rig_root, "mc-dep")
    assert result.returncode == 0, (
        "control: a brief WITH a dependency must adjudicate today.\n"
        f"stdout={result.stdout[:600]}\nstderr={result.stderr[:600]}"
    )


# --- THE ISSUE: red today --------------------------------------------------
#: `strict=True` is load-bearing and not a default. A plain `xfail` reports
#: XPASS and stays GREEN when the bug is fixed, so the marker would outlive the
#: defect silently and this file would become a test that cannot fail -- the
#: exact P6.2 shape it was written to demonstrate. Strict turns the day #137 is
#: fixed into a loud failure whose remedy is deleting this marker, which is how
#: the fix and the test that named the defect stay attached to each other.
@pytest.mark.xfail(
    reason="#137: MBRF004 blocks adjudication of a silently-omitted source link",
    strict=True,
)
def test_a_verdict_can_be_recorded_when_the_producer_omitted_the_source_dependency(
    tmp_path: Path,
):
    """#137. Differs from control A by ONE field: no `dependencies`.

    Red today: MBRF004 is ERROR, the mutation path blocks on ERROR, and the
    verdict is refused. A producer's omission makes the brief unadjudicable.
    """
    city_root, rig_root = _seed(tmp_path, "mc-omitted", OMITTED)
    result = _adjudicate(city_root, rig_root, "mc-omitted")

    # Pin WHY it is red. Without this the test could go green on a fix that
    # merely changed the failure mode, or red on something unrelated to #137.
    if result.returncode != 0:
        assert _blocking_code(result) == "MBRF004", (
            "this test is red, but not for the reason #137 describes — the "
            f"blocking code is {_blocking_code(result)!r}, not MBRF004. Fix the "
            "fixture before reading this as evidence."
        )

    assert result.returncode == 0, (
        "#137: a verdict must be recordable on a brief whose producer omitted the "
        "source link. Today the mutation is refused with MBRF004.\n"
        f"blocking_code={_blocking_code(result)}\nstderr={result.stderr[:800]}"
    )


# --- CONTROL B -------------------------------------------------------------
def test_control_b_a_brief_declaring_no_subject_can_be_adjudicated(tmp_path: Path):
    """B2.1a's escape hatch already works, and the fix should not reinvent it.

    Differs from the failing case by ONE field: the `no-subject` label. That is
    the whole difference between a declaration (MBRF056, INFO, non-blocking) and
    a silent omission (MBRF004, ERROR, blocking).
    """
    city_root, rig_root = _seed(tmp_path, "mc-declared", DECLARED)
    result = _adjudicate(city_root, rig_root, "mc-declared")
    assert result.returncode == 0, (
        "control: B2.1a declares no-subject compliant; this must adjudicate today.\n"
        f"blocking_code={_blocking_code(result)}\n"
        f"stdout={result.stdout[:600]}\nstderr={result.stderr[:600]}"
    )
