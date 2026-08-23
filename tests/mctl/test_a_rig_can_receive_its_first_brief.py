"""#147: a rig whose root resolves must be able to receive its FIRST brief.

`briefs_create` refuses with MBRF035 (FATAL) when `.beads/briefs/` is absent. The
refusal guards a real hazard -- writing through a MIS-RESOLVED root would build a
brief tree somewhere nothing reads. But it has no remedy path: no provisioning
command, no create-on-first-use. So a rig in that state can never receive a first
brief, and MEASURED on the live city that is 6 of 16 registered rigs, one of which
(`agent_skills`) already holds 3 decision beads it can never add to.

It also makes CT4.5 unsatisfiable for `mathcity` specifically -- no formula dispatch
without a hygienic brief filed first, and the rig that owns `mctl` cannot receive
one. Its own repair work has nowhere to land.

WHY THE HAZARD DOES NOT APPLY WHEN THE RIG ROOT RESOLVES
--------------------------------------------------------
The guard's docstring warns that the declared contract (`paths.toml`, rig-relative)
and the live layout ("the city keeps its brief tree at the city root") disagree.
They do not: `context_rigs` reports `hq.rig_root == <city-root>`, so that "city
root" tree IS hq's ordinary rig-relative tree. Rig-relative is the live convention,
demonstrated by `briefs_list --all_rigs` reading briefs per-rig from five rigs.

And the tree is CACHE, not canon: B2.8 makes the bead store canonical, and `hecke`
returns 45 open briefs while holding `stack=0` on disk. A rig with beads and no
cache directory is ordinary, not broken.

So creating the directory under a root that already resolves is not inventing a
location -- it is materializing the cache for a location already agreed.

WHAT THIS TEST ASSERTS, AND WHY IT IS SHAPED THIS WAY
-----------------------------------------------------
It asserts the OUTCOME -- a rig with a resolvable root can receive its first brief --
not the mechanism. Create-on-first-use, a provisioning step, or provisioning at rig
registration would all satisfy it. That is deliberate: the mechanism is an open
decision, and a test written against one implementation would have to be rewritten
if another is chosen.

The control asserts the guard STILL REFUSES when the rig root itself is absent.
Without it, "the rig can receive a brief" is satisfiable by deleting the guard --
which would restore exactly the hazard it was written for.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_briefs_create_validate_cli import (  # noqa: E402
    beads_fixture,
    body_file,
    brief_command,
    run_mctl,
    runtime_fixture,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
BODY = "## What is being decided\n\nWhether a fresh rig can receive a brief.\n"


def _create(city_root: Path, rig_root: Path, tmp_path: Path):
    return run_mctl(
        *brief_command(
            city_root, "create",
            "--title", "first brief in this rig",
            "--body-file", str(body_file(tmp_path, BODY)),
            # #173 raised MBRF034 to FATAL: creation REFUSES a sourceless brief
            # rather than minting one its own approval would brick. These tests
            # are about the brief ROOT, not about B2.1 completeness, so they must
            # supply a source or they fail for an unrelated -- and correct --
            # reason. Written before #173 landed; the omission was an assumption
            # that #173 overturned on purpose.
            "--source", "mc-source",
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )


def test_a_rig_with_no_brief_tree_can_still_receive_its_first_brief(tmp_path: Path):
    """#147. Red today: MBRF035 refuses and offers no way forward."""
    city_root, rig_root = runtime_fixture(tmp_path)
    # The rig exists and resolves; only the brief cache is absent -- exactly the
    # live state of mathcity, agent_skills and four others.
    shutil.rmtree(rig_root / ".beads" / "briefs")

    result = _create(city_root, rig_root, tmp_path)

    assert result.returncode == 0, (
        "a rig whose root resolves cannot receive its first brief: "
        f"{result.stdout[:400]}{result.stderr[:400]}"
    )
    payload = json.loads(result.stdout)
    written = [e.get("kind") for e in payload.get("actual_effects", [])]
    assert "pile_markdown" in written, f"no document was written: {written}"


def test_control_the_guard_still_refuses_when_the_PATH_IS_NOT_A_DIRECTORY(tmp_path: Path):
    """The hazard that must keep being refused, and it is not the one I first wrote.

    My first control deleted the whole rig root. That fails EARLIER, at context
    resolution, with `MCTL_CONTEXT_BEADS_FIXTURE_MISSING` -- the beads fixture lives
    under the rig root, so removing it never reaches MBRF035 at all. Worth recording:
    an absent rig root is already caught by a different guard one layer up, so
    MBRF035's stated hazard is narrower than its docstring implies.

    What DOES reach it: the resolved path exists and is not a directory. `mkdir`
    would fail there, and a create-on-first-use that assumed it could always make
    the directory would turn a clean refusal into an OSError.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    briefs = rig_root / ".beads" / "briefs"
    shutil.rmtree(briefs)
    briefs.write_text("not a directory\n", encoding="utf-8")

    result = _create(city_root, rig_root, tmp_path)

    assert result.returncode != 0, (
        "creation succeeded through a path that is not a directory"
    )
    assert "MBRF035" in (result.stdout + result.stderr), (
        "refused, but not with the named diagnostic: "
        f"{result.stdout[:300]}{result.stderr[:300]}"
    )


def test_control_a_rig_that_already_has_a_tree_is_unaffected(tmp_path: Path):
    """The ordinary path must not change while fixing the empty one."""
    city_root, rig_root = runtime_fixture(tmp_path)

    result = _create(city_root, rig_root, tmp_path)

    assert result.returncode == 0, f"{result.stdout[:300]}{result.stderr[:300]}"
