"""mc-lre5h: the empty "error briefs" chip is gone from the pipeline rail.

`errors` is an UNCOUNTABLE_LANE -- invariant-error briefs are not filed as briefs
at all, so nothing ever measures the count. The masthead rail nevertheless
carried an "error briefs" chip, which therefore rendered a permanent em-dash: a
label pointing at a lane the operator's real counts never populate. Remove it;
the chips that carry real counts stay.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))


def _masthead() -> str:
    from mctl_dashboard import render

    return render.masthead(
        {"stack": 7, "pile": 3, "deferred": 1}, {"city_root": "~/gt"}
    )


def test_the_pipeline_rail_has_no_error_briefs_chip():
    html = _masthead()
    assert "error briefs" not in html.lower(), "the empty error-briefs chip must be gone"
    assert "scope=errors" not in html, "its link to the errors lane must be gone too"


def test_the_real_chips_remain_on_the_rail():
    html = _masthead()
    assert "pile" in html
    assert "stack" in html
    assert "deferred" in html
