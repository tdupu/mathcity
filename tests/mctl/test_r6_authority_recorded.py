"""R6 — a recorded verdict must carry the authority that produced it.

THE DEFECT (mc-9kwwv)
---------------------
`adjudicated_by` had three readers and, on the surface they read, no writer:

    mctl_core/materialize_plan.py:295   authorizer = frontmatter.get("adjudicated_by")
    mctl_core/materialize_plan.py:381   verdict_authorizer=_unquote(frontmatter.get(...))
    mctl_dashboard/fields.py:58         surfaced as a field

The adjudication write path recorded `adjudicated_by` on bead METADATA only, so
none of the three FRONTMATTER readers could ever see it, and `classify_tier` --
which needs verdict AND authorizer AND date in the frontmatter -- could never
reach `TIER_ADJUDICATED` for anything mctl adjudicated. The fix wires
`adjudicated_by` and `adjudicated_at` into the frontmatter (effects.py,
`plan_adjudication`).

THE ADOPTED CHANNEL (mc-ba376 / mc-ewapk)
-----------------------------------------
An earlier draft of this file argued (as "R8.2") that authority MUST NOT be a
caller-supplied argument, and asserted only the weak invariant that a verdict
must not be *silently* unattributed. That strict position was NOT adopted:
R8.2 lived only here, in no POLICY.md, and blocked nothing. What was adopted is
the #152 design -- a caller names the adjudicator through `--adjudicated-by`
(CLI) / `adjudicated_by` (`briefs_relay_adjudication`), and omitting it is
allowed but LOUD: `MBRF_ADJUDICATOR_UNRECORDED` fires at WARN so a silent
self-approval cannot pass unseen. So this file now pins the adopted invariant in
both directions.

WHY THIS IS NOT VACUOUS (P6.2)
------------------------------
The old `test_recorded_verdict_carries_authority` searched a blob that INCLUDED
`result.stdout`, where the `MBRF_ADJUDICATOR_UNRECORDED` advisory names the
literal string `adjudicated_by`. The test therefore passed on the diagnostic
that fires when authority is MISSING -- a complaint mentioning the key was read
as the key being recorded. The searched blob here is the PERSISTED artifacts
only (stack frontmatter + decision TOML); `result.stdout` is never in it. The
absent-authority case is a separate test that asserts nothing is forged and the
advisory is loud.
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

#: Any spelling that would count as recorded authority.
AUTHORITY_KEYS = ("adjudicated_by", "authority", "authorized_by", "authorised_by")

BEAD_ID = "mc-r6"
ADJUDICATOR = "Taylor Dupuy (R6 test)"


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


def _adjudicate(city_root: Path, rig_root: Path, *extra: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(rig_root / ".beads" / "issues.jsonl")
    return subprocess.run(
        [
            sys.executable, str(MCTL), "briefs", "adjudicate", BEAD_ID,
            "--city", str(city_root), "--rig", "mathcity",
            "--verdict", "approve", "--reason", "recorded by the R6 test",
            "--json", *extra,
        ],
        capture_output=True, text=True, env=env, cwd=str(REPO_ROOT), check=False,
    )


def _persisted(rig_root: Path) -> str:
    """The PERSISTED representations only -- never process stdout."""
    stack = (rig_root / ".beads" / "briefs" / "stack" / f"{BEAD_ID}.md").read_text(encoding="utf-8")
    decisions = (rig_root / ".beads" / "briefs" / "decisions" / f"{BEAD_ID}.toml").read_text(encoding="utf-8")
    return f"{stack}\n{decisions}"


def test_control_fixture_starts_without_authority(tmp_path: Path) -> None:
    """The fixture must NOT begin with an authority key, or the tests below are void."""
    _, rig_root = _seed(tmp_path)
    text = (rig_root / ".beads" / "briefs" / "stack" / f"{BEAD_ID}.md").read_text(encoding="utf-8")
    present = [k for k in AUTHORITY_KEYS if k in text]
    assert not present, f"fixture already carries authority {present}; the assertions below prove nothing"


def test_recorded_verdict_carries_authority(tmp_path: Path) -> None:
    """A named adjudicator is persisted where the frontmatter readers read it."""
    city_root, rig_root = _seed(tmp_path)
    result = _adjudicate(city_root, rig_root, "--adjudicated-by", ADJUDICATOR)
    assert result.returncode == 0, result.stderr

    written = _persisted(rig_root)  # NOTE: stdout is deliberately not in here.
    recorded = [k for k in AUTHORITY_KEYS if k in written]
    assert recorded, (
        "a named verdict recorded NO authority in any persisted artifact. "
        f"exit={result.returncode}. R6: the authority must reach the surface its "
        "readers read, not merely be echoed in stdout."
    )
    assert ADJUDICATOR in written, "the adjudicator's name itself must be persisted"


def test_an_unattributed_verdict_forges_nothing_and_is_loud(tmp_path: Path) -> None:
    """No `--adjudicated-by` -> no authority is forged, and the advisory fires.

    The #152 visibility design: an unattributed adjudication is recorded but is
    not dressed with an authority it never had, and it is not silent -- the
    persisted artifacts carry no authority key, and `MBRF_ADJUDICATOR_UNRECORDED`
    is emitted in the structured diagnostics.
    """
    city_root, rig_root = _seed(tmp_path)
    result = _adjudicate(city_root, rig_root)
    assert result.returncode == 0, result.stderr

    written = _persisted(rig_root)
    forged = [k for k in AUTHORITY_KEYS if k in written]
    assert not forged, f"authority {forged} appeared with no adjudicator supplied"

    payload = json.loads(result.stdout)
    codes = {d["code"] for d in payload.get("diagnostics", [])}
    assert "MBRF_ADJUDICATOR_UNRECORDED" in codes, (
        "an unattributed verdict must be LOUD, not silent"
    )
