"""Artifact trust must not untrust a rig for a convention it already handles (#148).

Q5 has two halves. The rig-root-vs-city-root resolution question is the repo
owner's and is untouched here. The other half was mechanical and stale:
`_frontmatter_lookup_mismatch` untrusted a whole rig whenever any pile file's
`artifact:` value differed from its filename, asserting that "the <bead_id>.md
lookup cannot find artifacts that exist".

Both halves of that were wrong by the time it was written:

  1. `redundant_state` already resolves by `artifact:` frontmatter (mc-crc4o,
     whose comment records "Q5 (RESOLVED 2026-08-19)").
  2. `artifact:` frequently names the brief's SUBJECT, not a bead --
     `feat/snfs-scaling-test`, `.gc-builds` -- so the "mismatch" said nothing
     about artifact state at all.

Measured on the live city when this was narrowed: hecke, gascity-packs and
lmfdb all reported trusted afterwards, where all three had been untrusted.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))
from mctl_core.mcp_server import (  # noqa: E402
    _BEAD_SHAPED_ARTIFACT,
    _frontmatter_lookup_mismatch,
)


def _pile(tmp_path: Path, files: dict[str, str]) -> Path:
    pile = tmp_path / ".pile"
    pile.mkdir()
    for name, artifact in files.items():
        (pile / name).write_text(f"---\nartifact: {artifact}\n---\n\nbody\n")
    return pile


def test_a_single_claimant_is_healthy_not_a_defect(tmp_path):
    """The case that was untrusting three live rigs.

    Walking `X.md` whose `artifact:` names bead `B`, X.md itself claims B, so
    one claimant means "B's cache is X.md, reachable by frontmatter" -- exactly
    what mc-crc4o made work.
    """
    pile = _pile(tmp_path, {"mc-aaa1.md": "mc-zzz9"})
    assert _frontmatter_lookup_mismatch(pile) is None


def test_two_claimants_for_one_bead_still_untrusts(tmp_path):
    """The control: this check must still be able to FAIL.

    Ambiguity is the surviving unbelievable reading -- the resolver reports
    `ambiguous` and no caller can tell which file is that bead's cache. Without
    this test, narrowing the condition could have silently made it a no-op.
    """
    pile = _pile(tmp_path, {"mc-bbb2.md": "mc-ccc3", "mc-ccc3.md": "mc-ccc3"})
    result = _frontmatter_lookup_mismatch(pile)
    assert result is not None
    assert result[1] == "mc-ccc3"


def test_subject_style_artifact_values_are_not_bead_lookups(tmp_path):
    """`artifact:` names the brief's SUBJECT as often as a bead.

    Reporting "the <bead_id>.md lookup cannot find artifacts that exist" about
    a brief whose subject is a git branch is a category error, not a
    measurement. Both values here are real, from the live city.
    """
    pile = _pile(tmp_path, {
        "he-x9xi5p.md": "feat/snfs-scaling-test",
        "gsp-mkp5uq.md": ".gc-builds",
    })
    assert _frontmatter_lookup_mismatch(pile) is None


def test_bead_shape_classification(tmp_path):
    """Pins which values count as bead references at all."""
    assert _BEAD_SHAPED_ARTIFACT.match("he-6nb")
    assert _BEAD_SHAPED_ARTIFACT.match("gsp-ioek")
    assert not _BEAD_SHAPED_ARTIFACT.match("feat/snfs-scaling-test")
    assert not _BEAD_SHAPED_ARTIFACT.match(".gc-builds")


def test_absent_pile_is_not_a_mismatch(tmp_path):
    """An unmaterialised pile is the empty state, not a data problem (#149)."""
    assert _frontmatter_lookup_mismatch(tmp_path / "nope") is None
