"""R6 — a recorded verdict must carry the authority that produced it.

THE DEFECT
----------
`adjudicated_by` has three readers and no writer:

    mctl_core/materialize_plan.py:295   authorizer = frontmatter.get("adjudicated_by")
    mctl_core/materialize_plan.py:381   verdict_authorizer=_unquote(frontmatter.get(...))
    mctl_dashboard/fields.py:58         surfaced as a field

and the adjudication write path records exactly two frontmatter keys:

    effects.py   frontmatter_fields={"status": "adjudicated", "verdict": normalized}

So every verdict ever recorded leaves `adjudicated_by` absent, and its three
consumers read an empty string.

WHY THE OBVIOUS FIX IS FORBIDDEN
--------------------------------
Adding an `--adjudicated-by` argument would satisfy the letter of R6 and rebuild
the defect R8.2 exists to prevent. `created_by` is already that mistake, shipped:

    effects.py   metadata = {"created_by": "mctl", ...}   # literal, every brief

It is provenance-shaped and carries none. A caller-typed `adjudicated_by` would be
strictly worse than absent, because its presence suppresses the question. **R8.2:
authority MUST NOT be derived from any caller-supplied argument.**

So this file does NOT assert that a specific authority value is written. It asserts
the weaker, option-independent invariant: **an adjudication must not silently
record a verdict with no authority at all.** That holds whether R6 lands as a real
authority channel (R8), as an explicit refusal, or as an explicit
`authority: unavailable` marker — and it fails today under all three.

HOW THIS COULD FAIL (P6.2)
--------------------------
The vacuous version of this file asserts `"adjudicated_by" in result` against a
fixture that already carries the key in its frontmatter — passing without the
writer ever running. The fixture below therefore starts with frontmatter that has
**no** authority key, and the control asserts that starting state, so a fixture
that quietly gained the field would fail the control rather than silently green
the test.

  * `test_control_fixture_starts_without_authority` — PASSES today. If it ever
    fails, the fixture is wrong and the assertion below proves nothing.
  * `test_recorded_verdict_carries_authority` — **FAILS today.** This is R6.
"""

from __future__ import annotations

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
BRIEF_STATE = FIXTURES / "brief_state"

#: No authority key of any spelling. The variable under test is its ABSENCE.
FRONTMATTER = "---\nstatus: ready-for-adjudication\n---\n\nBody.\n"

#: Any spelling that would count as recorded authority. R6.3 fixes the canonical
#: one; the others are here so a fix that invents a second spelling still passes
#: rather than being failed for a naming choice this test has no standing to make.
AUTHORITY_KEYS = ("adjudicated_by", "authority", "authorized_by", "authorised_by")

BEAD_ID = "mc-r6"


def _seed(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track")
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")

    bead = {
        "id": BEAD_ID,
        "title": "Brief under test",
        "status": "open",
        "issue_type": "decision",
        "labels": ["brief-open"],
        "created_at": "2026-08-10T12:00:00Z",
        "updated_at": "2026-08-11T12:00:00Z",
        # a source dependency, so this test isolates AUTHORITY and not MBRF004
        "dependencies": [{"issue_id": "mc-source", "type": "blocks"}],
    }
    brief_root = rig_root / ".beads" / "briefs"
    with (rig_root / ".beads" / "issues.jsonl").open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(bead) + "\n")
    (brief_root / "decisions" / f"{BEAD_ID}.toml").write_text(
        f'brief_id = "{BEAD_ID}"\ntitle = "Brief under test"\nstatus = "open"\n',
        encoding="utf-8",
    )
    for path in (brief_root / "stack" / f"{BEAD_ID}.md", brief_root / ".pile" / f"{BEAD_ID}.md"):
        path.write_text(FRONTMATTER, encoding="utf-8")
    return city_root, rig_root


def _adjudicate(city_root: Path, rig_root: Path) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
    return subprocess.run(
        [
            sys.executable, str(MCTL), "briefs", "adjudicate", BEAD_ID,
            "--city", str(city_root), "--rig", "mathcity",
            "--verdict", "approve", "--reason", "recorded by the R6 test",
            "--json",
        ],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT), check=False,
    )


def test_control_fixture_starts_without_authority(tmp_path: Path) -> None:
    """The fixture must NOT begin with an authority key, or the test below is void."""
    _, rig_root = _seed(tmp_path)
    text = (rig_root / ".beads" / "briefs" / "stack" / f"{BEAD_ID}.md").read_text(encoding="utf-8")
    present = [k for k in AUTHORITY_KEYS if k in text]
    assert not present, f"fixture already carries authority {present}; the assertion below proves nothing"


def test_recorded_verdict_carries_authority(tmp_path: Path) -> None:
    """FAILS TODAY. A recorded verdict must not be silent about who authorised it."""
    city_root, rig_root = _seed(tmp_path)
    result = _adjudicate(city_root, rig_root)

    stack = (rig_root / ".beads" / "briefs" / "stack" / f"{BEAD_ID}.md").read_text(encoding="utf-8")
    decisions = (rig_root / ".beads" / "briefs" / "decisions" / f"{BEAD_ID}.toml").read_text(encoding="utf-8")
    written = f"{stack}\n{decisions}\n{result.stdout}"

    recorded = [k for k in AUTHORITY_KEYS if k in written]
    assert recorded, (
        "verdict recorded with NO authority of any spelling. "
        f"exit={result.returncode}. R6: a verdict must carry the authority that "
        "produced it, or be refused. Silence is neither."
    )
