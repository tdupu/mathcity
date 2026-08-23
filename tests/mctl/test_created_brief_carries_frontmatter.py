"""A brief mctl creates must be one mctl can later adjudicate into.

`briefs_create` wrote the raw body as the pile document. Nothing reads a brief's
status from a body, so `briefs_adjudicate` had no header to rewrite and raised
`BriefFrontmatterUnwritable` -- at WARN, AFTER the verdict had landed on the bead.
The operation reported success with one representation silently stale.

The larger consequence: `classify_tier` (materialize_plan.py:292-298) reads
`verdict`, `adjudicated_by` and `adjudicated_at` from that block. With no block it
sees an empty mapping, so an adjudicated brief classifies `C-no-disposition`, and
`materialize_plan.py:379` turns that tier into `status="open"` -- a decided brief
re-materialising as open work.

HOW THIS TEST COULD FAIL (P6.2), stated because my FIRST attempt at covering this
could not:

  I originally asserted `classify_tier({}) != TIER_ADJUDICATED` on a HARDCODED empty
  dict. That is true forever, whatever `briefs_create` does, so it could not detect
  the fix and could not fail. It was a test that could not pass -- in a file written
  to catch tests that cannot fail.

  This one drives the REAL create path through the CLI and reads the document off
  disk, so it is red before the fix and green after. The control below asserts the
  body survives, so "has frontmatter" cannot be satisfied by writing a header over
  a destroyed document.
"""

from __future__ import annotations

import json
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

SCRIPTS = Path(__file__).resolve().parents[2] / "assets" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from mctl_core.fields import read_frontmatter  # noqa: E402

#: Reuse the SHARED default rather than defining a third private body.
#:
#: This file is the THIRD of mine to go red on a body requirement it predates:
#: #173 made a sourceless create FATAL, #169 (MBRF036) required `## Gate Evidence`,
#: and each time a test asserting something ELSE -- the brief root, the frontmatter
#: block -- failed for a reason it was not about. Patching each private BODY
#: constant fixes the instance and guarantees a fourth.
#:
#: `DEFAULT_BODY` is mutt's, introduced with #169, and `body_file()` already
#: defaults to it. Importing it means the next required section arrives here for
#: free -- and if it does not, ONE fixture is wrong instead of several.
from test_briefs_create_validate_cli import DEFAULT_BODY as BODY  # noqa: E402


def _create(tmp_path: Path) -> Path:
    """Create a brief for real, and return its pile document."""
    city_root, rig_root = runtime_fixture(tmp_path)
    result = run_mctl(
        *brief_command(
            city_root,
            "create",
            "--title",
            "frontmatter contract probe",
            "--body-file",
            str(body_file(tmp_path, BODY)),
            # #173 raised MBRF034 to FATAL: a sourceless create is refused. This
            # test is about the DOCUMENT, not B2.1 completeness, so it supplies a
            # real bead from the fixture rather than failing for an unrelated
            # -- and correct -- reason.
            "--source", "mc-source",
            "--json",
        ),
        cwd=Path(__file__).resolve().parents[2],
        beads_fixture=beads_fixture(rig_root),
    )
    assert result.returncode == 0, f"create failed: {result.stdout}\n{result.stderr}"
    payload = json.loads(result.stdout)
    created = [
        e for e in payload.get("actual_effects", []) if e.get("kind") == "pile_markdown"
    ]
    assert created, f"no pile document was written: {payload.get('actual_effects')}"
    return Path(created[0]["path"])


def test_a_created_brief_has_a_frontmatter_block(tmp_path: Path):
    """Red before the fix: the document was the raw body, starting at `##`."""
    doc = _create(tmp_path)
    text = doc.read_text(encoding="utf-8")

    assert text.lstrip().startswith("---"), (
        "the created document has no frontmatter block, so adjudication has no "
        f"header to write its verdict into. First line: {text.splitlines()[:1]!r}"
    )
    assert read_frontmatter(text), "the block is present but parses to no fields"


def test_control_the_body_survives_the_frontmatter_block(tmp_path: Path):
    """Otherwise 'has frontmatter' could be satisfied by discarding the brief."""
    doc = _create(tmp_path)
    text = doc.read_text(encoding="utf-8")

    assert "Ship it?" in text, (
        "the body did not survive: a frontmatter block must be added to the "
        "document, not written over it"
    )


def test_the_created_status_agrees_with_its_sibling_decision_record(tmp_path: Path):
    """Two representations written by ONE call must not disagree about status.

    The `decision_toml` written by the same create says `status = "open"`. A
    frontmatter block saying anything else would be a five-representation
    disagreement manufactured at creation time.
    """
    doc = _create(tmp_path)
    front = read_frontmatter(doc.read_text(encoding="utf-8"))

    assert front.get("status") == "open", (
        "created frontmatter status disagrees with the decision record written by "
        f"the same call (decision_toml says 'open'): {dict(front)!r}"
    )
