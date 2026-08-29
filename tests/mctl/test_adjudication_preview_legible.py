"""mc-5fo2a: the verdict preview reads as a plan, not a raw JSON dump.

The effect-plan panel rendered a readable table AND a `<pre class="plan">` block
holding the entire effect plan pretty-printed as JSON -- trace ids, advisories,
nested facts and all. Escaped in the source, it decodes in the browser to a wall
of `{ "trace_id": ... }` the operator has to read past to find the one line that
matters. mc-5fo2a: present the planned action in readable form and drop the raw
blob.

The machine-readable `data-plan-json` ATTRIBUTE stays -- it is not visible text,
and the staleness digest and other tooling read it. The test therefore asserts on
what a reader actually SEES (tags stripped, entities decoded): no JSON object
dump, and the readable summary -- the move, the target, the effect -- present.
"""
from __future__ import annotations

import html as _html
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from test_dashboard_mutation_safety import dashboard_for, preview, strip_tags  # noqa: E402


def _visible_text(body: str) -> str:
    """What the reader sees: element content only, entities decoded."""
    return _html.unescape(strip_tags(body))


def test_the_preview_shows_no_raw_json_blob(tmp_path: Path):
    dashboard, _, _ = dashboard_for(tmp_path)

    body = preview(dashboard).body
    visible = _visible_text(body)

    # No pretty-printed plan dump element, and no JSON object the reader must
    # decode by eye -- the trace id and the advisories keys are the tell.
    assert '<pre class="plan">' not in body, "the raw plan JSON dump must be gone"
    assert '"trace_id"' not in visible, "a raw JSON blob is still shown to the reader"
    assert '"advisories"' not in visible, "a raw JSON blob is still shown to the reader"


def test_the_preview_presents_the_plan_in_readable_form(tmp_path: Path):
    dashboard, _, _ = dashboard_for(tmp_path)

    body = preview(dashboard).body
    visible = _visible_text(body)

    # The move, the target, and the effect are stated in plain words/rows.
    assert "mc-open" in visible, "the target brief must be named"
    assert "closed" in visible, "the planned canonical status must be legible"
    # The effect table still labels its rows in words, not JSON keys.
    assert "canonical bead update" in visible
    # The machine-readable attribute is retained for the staleness digest.
    assert "data-plan-json" in body
