"""The adjudicated screen said the verdict was unreadable. It is readable.

The screen carried: "The verdict itself is not readable, only that one was
recorded... to_dict never emits it" -- and rendered an em dash in the verdict
column. Measured against the live city, all 197 adjudicated briefs carry a
verdict object with `text`, `source` and `confidence`. approve 84, revise 10,
and so on.

So the screen was withholding the one column it exists for, on the strength of
a claim that had stopped being true. That is worse than an empty column: it
tells the operator the data does not exist.

Provenance travels with it, because it matters: a verdict lifted out of a
close_reason at low confidence is not the same artifact as a typed field.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.screens import pipeline


def _brief(verdict=None, **over):
    row = {"brief_id": "b1", "bead_id": "b1", "title": "t", "rig_id": "hq",
           "decision_state": "adjudicated"}
    if verdict is not None:
        row["verdict"] = verdict
    row.update(over)
    return row


def test_the_verdict_text_is_rendered():
    html = pipeline.adjudicated([_brief({"text": "approve", "source": "typed_field",
                                         "confidence": "high"})])
    assert "approve" in html


def test_the_old_claim_is_gone():
    html = pipeline.adjudicated([_brief({"text": "approve", "source": "typed_field",
                                         "confidence": "high"})])
    assert "not readable" not in html


def test_provenance_travels_with_the_verdict():
    """close_reason at low confidence is not a typed field, and must not look
    like one."""
    html = pipeline.adjudicated([_brief({"text": "REJECT-MOOT", "source": "close_reason",
                                         "confidence": "low"})])
    assert "close_reason" in html
    assert "low" in html


def test_a_brief_with_no_verdict_still_renders_a_dash():
    html = pipeline.adjudicated([_brief()])
    assert "&mdash;" in html or "—" in html
