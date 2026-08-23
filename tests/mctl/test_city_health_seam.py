"""The seam between `#159` and `#176`, which neither of them owns.

Found by driving the live dashboard, which is how it should have been found
sixteen hours earlier. `/city` rendered this, with nothing in between:

    "The data plane's state was not established. The probe did not answer, so
     this is a fact about the probe and not evidence about the database."

    agent_skills — healthy    hecke — healthy    ... 17 of them

**Both statements are true, and that is the defect.** After `#159` the
city-level `data_plane` says `unknown` when `gc` does not answer. After `#176`
each rig is probed directly, so seventeen `healthy` rows are seventeen real
measurements. The page asserted "we established nothing" directly above
seventeen establishments and never said why they can differ.

A reader concludes the page is broken, or believes whichever half they prefer.
That is worse than either message alone -- and neither `#159` nor `#176` is
wrong. The seam appeared when the second merged on top of the first and nobody
re-read the paragraph above.

The sentence must be CONDITIONAL. A banner that always fires is this module's
own defect one level up: it would be prose that stops meaning anything, which
is exactly what `#159`'s commit removed from this file.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.screens import city


def _rigs(*states: str):
    return [{"rig_id": f"r{i}", "state": s, "reason": ""} for i, s in enumerate(states)]


def test_the_seam_is_explained_when_the_two_disagree():
    """city-level `unknown` + per-rig `healthy` is the live state, and the
    page must say why both can be true at once."""
    html = city.health({"data_plane": "unknown", "per_rig": _rigs("healthy", "healthy"), "diagnostics": []})
    low = html.lower()
    # It must connect the two, not merely print them adjacently.
    assert "each rig" in low or "directly" in low or "answered" in low
    # And it must not resolve the tension by softening either side.
    assert "not established" in low or "did not answer" in low


def test_the_seam_is_SILENT_when_nothing_disagrees():
    """No `unknown`, so there is no tension to explain. A sentence here would
    be noise that trains the reader to skip the panel."""
    html = city.health({"data_plane": "healthy", "per_rig": _rigs("healthy", "healthy"), "diagnostics": []})
    assert "each rig was asked" not in html.lower()


def test_the_seam_is_SILENT_when_the_rigs_agree_with_the_unknown():
    """`unknown` city-level AND no rig answered either: nothing contradicts,
    so nothing needs reconciling. This is the total-outage shape."""
    html = city.health(
        {"data_plane": "unknown", "per_rig": _rigs("unreachable", "unreachable"), "diagnostics": []}
    )
    assert "each rig was asked" not in html.lower()


def test_a_partial_disagreement_still_explains():
    """One rig answered. That is still an establishment sitting under a claim
    that nothing was established."""
    html = city.health(
        {"data_plane": "unknown", "per_rig": _rigs("healthy", "unreachable"), "diagnostics": []}
    )
    assert "each rig" in html.lower() or "answered" in html.lower()
