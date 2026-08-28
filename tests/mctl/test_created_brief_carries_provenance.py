"""A brief `briefs_create` writes must carry the provenance its creation enforced.

THE DEFECT (R8). `plan_create_brief` REFUSES a sourceless create -- MBRF034 is
FATAL since #173, so a created brief is *guaranteed* to have a source bead. The
pile document it then writes, via `_pile_document`, was
`---\nstatus: open\n---\n\n<body>`: status and nothing else. The source the call
just insisted on was dropped on the floor.

Downstream, `brief-shuffle-fast-drain.py::profile_error` asks the standard
profile for `source_bead | artifact | brief_bead` in the frontmatter and rejects
the brief as "standard brief missing provenance metadata" when it finds none. So
every brief created through the single code-enforced writer (POLICY B2.11) is
rejected by the drain for lacking a fact its own creation made mandatory.

The two halves also disagreed about SPELLING. `mctl_core` resolves a brief's own
bead through `("brief_bead", "brief_id", "bead_id", "slug", "id", "source")`
(effects.py `_row_matches`, redundant_state.py `_row_id`); the drain accepted
three of those names. A live brief carrying `bead_id: gt-3ibad0` -- provenance
present, spelled the way mctl itself reads it -- is rejected today.

HOW THESE TESTS COULD FAIL (P6.2). The provenance assertions drive the REAL
create path through the CLI and read the document off disk, so they are red
before the fix and green after. Each is paired with a NEGATIVE CONTROL asserting
that a brief with genuinely no provenance is STILL rejected, and that the
filename-derived keys every producer writes (`brief_slug`, `slug`, `id`) do NOT
satisfy the gate -- otherwise widening the vocabulary would turn a real check
into one that cannot fail, which is worse than no check.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_briefs_create_validate_cli import (  # noqa: E402
    DEFAULT_BODY as BODY,
    beads_fixture,
    body_file,
    brief_command,
    run_mctl,
    runtime_fixture,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mctl_core.fields import read_frontmatter  # noqa: E402

SOURCE_BEAD = "mc-source"


def _drain():
    """The drain script, loaded as a module.

    It ships as a standalone pack asset with a hyphenated name, so it is loaded
    by path rather than imported -- the same seam
    `tests/brief-shuffle-fast-drain` uses.
    """
    path = SCRIPTS / "brief-shuffle-fast-drain.py"
    spec = importlib.util.spec_from_file_location("brief_shuffle_fast_drain", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _create(tmp_path: Path) -> Path:
    """Create a brief for real, with a source, and return its pile document."""
    city_root, rig_root = runtime_fixture(tmp_path)
    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "provenance contract probe",
            "--body-file",
            str(body_file(tmp_path, BODY)),
            "--source",
            SOURCE_BEAD,
            "--json",
        ),
        cwd=REPO_ROOT,
        beads_fixture=beads_fixture(rig_root),
    )
    assert result.returncode == 0, f"create failed: {result.stdout}\n{result.stderr}"
    payload = json.loads(result.stdout)
    created = [
        e for e in payload.get("actual_effects", []) if e.get("kind") == "pile_markdown"
    ]
    assert created, f"no pile document was written: {payload.get('actual_effects')}"
    return Path(created[0]["path"])


def test_a_created_brief_records_the_source_its_creation_required(tmp_path: Path):
    """Red before the fix: the frontmatter was `status: open` and nothing else."""
    front = read_frontmatter(_create(tmp_path).read_text(encoding="utf-8"))

    assert front.get("source_bead") == SOURCE_BEAD, (
        "the created document does not name the source bead that MBRF034 refused "
        f"to create it without, so its provenance exists only on the bead: {dict(front)!r}"
    )


def test_the_drain_accepts_a_brief_this_writer_created(tmp_path: Path):
    """The end-to-end claim: the sole enforced writer's output clears the gate."""
    document = _create(tmp_path)
    text = document.read_text(encoding="utf-8")
    drain = _drain()

    assert drain.profile_error("standard", drain.parse_frontmatter(document), text) is None, (
        "the drain rejects a brief written by the single code-enforced brief "
        "writer (POLICY B2.11), whose creation refuses to proceed without a source"
    )


def test_control_a_brief_with_no_provenance_at_all_is_still_rejected():
    """The gate must still be able to fail, or the fix is a P6.2 violation."""
    drain = _drain()
    unprovenanced = {"status": "open", "priority": "P2", "review_gate": "approved"}

    assert (
        drain.profile_error("standard", unprovenanced, "# body\n")
        == "standard brief missing provenance metadata"
    ), "a brief naming no source, artifact or bead must still be rejected"


def test_control_filename_derived_keys_do_not_satisfy_the_gate():
    """`slug`/`id`/`brief_slug` are the FILENAME, not provenance.

    Every producer writes one, so accepting them would make the gate vacuous --
    a check that could not fail. `mctl_core`'s identity ladder includes `slug`
    and `id`; the drain's provenance vocabulary deliberately does not.
    """
    drain = _drain()
    for key in ("brief_slug", "slug", "id"):
        metadata = {"status": "open", key: "some-brief-slug"}
        assert (
            drain.profile_error("standard", metadata, "# body\n")
            == "standard brief missing provenance metadata"
        ), f"{key!r} is the filename, not provenance, and must not clear the gate"


def test_the_drain_reads_provenance_the_way_mctl_spells_it():
    """A live brief carries `bead_id`; mctl reads it, the drain did not.

    Evidence: `.beads/briefs/.pile/.rejected/gt-3ibad0-master-methodology-design/
    brief.md` carries `bead_id: gt-3ibad0` and is rejected as unprovenanced.
    """
    drain = _drain()
    for key in ("source_bead", "artifact", "brief_bead", "brief_id", "bead_id", "source"):
        metadata = {"status": "open", key: "gt-3ibad0"}
        assert drain.profile_error("standard", metadata, "# body\n") is None, (
            f"{key!r} names the brief's bead in mctl_core's own identity ladder, "
            "so the drain must not call a brief carrying it unprovenanced"
        )
