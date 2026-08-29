"""mc-q3m5q: per-verdict textbox conditionality + a defer duration picker.

Taylor's spec (2026-08-28): "At most one textbox, ever. The default is none."
The one reason textbox is shown-and-REQUIRED only for revise, no-brainer, or an
opt-in; defer takes a duration (days/weeks/months), not prose.

  | move            | control                       |
  | approve         | none                          |
  | revise          | one textbox, REQUIRED         |
  | no-brainer      | one textbox, REQUIRED         |
  | reject          | none unless opted in -> req.  |
  | defer           | duration picker (d/w/mo)      |
  | any + opt-in    | one textbox, REQUIRED         |

The panel is one form with a submit button per move, so requiredness is both
rendered (`required` + `formnovalidate` on the moves that need no reason) AND
enforced server-side (the authoritative gate, JS-off safe): a move that needs a
reason and carries none is refused before anything is written. These tests pin
the rendered structure and every row of the table through the real flow.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from test_dashboard_mutation_safety import bead, dashboard_for, strip_tags  # noqa: E402

from mctl_dashboard.app import Request  # noqa: E402


def _open_option():
    return [{"id": "adjudicate", "enabled": True, "description": "Record a verdict."}]


_MULTI = {
    "bead_id": "he-1",
    "decision_options": [
        {"label": "A", "title": "Merge as filed"},
        {"label": "B", "title": "Split first"},
    ],
}


def _panel(brief=None, prefill=None):
    from mctl_dashboard import state
    from mctl_dashboard.screens import panel

    return panel.entry(brief or {"bead_id": "he-1"}, _open_option(), state.ViewState(), prefill=prefill)


def _button(html: str, move: str) -> str:
    m = re.search(rf'<button[^>]*value="{re.escape(move)}"[^>]*>', html)
    assert m, f"no move button {move!r}"
    return m.group(0)


# --- render: at most ONE textbox, and it is the reason box ------------------


def test_at_most_one_textbox_renders_for_a_plain_brief():
    html = _panel()
    assert html.count("<textarea") == 1, "the spec is at most one textbox, ever"
    assert 'name="reason"' in html
    # The always-on second textarea (the no-brainer reason) is gone.
    assert 'name="no_brainer_reason"' not in html


def test_at_most_one_textbox_renders_even_for_a_multi_option_brief():
    html = _panel(_MULTI)
    assert html.count("<textarea") == 1
    # The propose-your-own box is no longer a second textarea.
    assert 'name="option_other"' not in html


def test_the_reason_box_is_required_and_not_labelled_optional():
    html = _panel()
    tag = re.search(r"<textarea[^>]*name=\"reason\"[^>]*>", html)
    assert tag and "required" in tag.group(0), "the reason box must render required"
    assert "optional" not in tag.group(0).lower(), "the placeholder must not say Optional"


# --- render: which moves need the reason (formnovalidate wiring) ------------


def test_approve_needs_no_reason():
    btn = _button(_panel(), "approve")
    assert "formnovalidate" in btn, "approve must not be blocked by the required reason"
    assert 'data-reason="none"' in btn


def test_revise_requires_the_reason():
    btn = _button(_panel(), "revise")
    assert "formnovalidate" not in btn, "revise must enforce the required reason"
    assert 'data-reason="required"' in btn


def test_reject_needs_no_reason_by_default():
    btn = _button(_panel(), "reject")
    assert "formnovalidate" in btn
    assert 'data-reason="none"' in btn


def test_the_no_brainer_optin_declares_it_requires_a_reason():
    html = _panel()
    checkbox = re.search(r'<input[^>]*name="no_brainer"[^>]*>', html)
    assert checkbox and "data-requires-reason" in checkbox.group(0)


# --- render: defer is a duration picker, not prose --------------------------


def test_defer_renders_a_duration_picker_not_a_textarea():
    html = _panel()
    group = html.split('data-move-group="defer"', 1)
    assert len(group) == 2, "there must be a defer move group"
    defer_group = group[1].split("</div>\n")[0] if "</div>\n" in group[1] else group[1]
    # A duration: a number and a unit selector of days/weeks/months.
    assert 'name="days"' in html
    assert 'name="days_unit"' in html, "defer needs a days/weeks/months unit picker"
    for unit in ("days", "weeks", "months"):
        assert f'value="{unit}"' in html, unit
    btn = _button(html, "defer")
    assert "formnovalidate" in btn, "defer takes a duration, not a required reason"


# --- flow: the six rows of the table, end to end ----------------------------


def test_approve_with_no_reason_applies(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    r = dashboard.handle(
        Request.post("/preview", operation="adjudicate", brief_id="mc-open", move="approve", reason="")
    )
    assert r.status == 200, strip_tags(r.body)[:300]
    assert bead(rig_root, "mc-open")["status"] == "closed"


def test_revise_with_no_reason_is_refused_and_writes_nothing(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    r = dashboard.handle(
        Request.post("/preview", operation="adjudicate", brief_id="mc-open", move="revise", reason="")
    )
    assert r.status >= 400, "revise with no reason must be refused"
    assert bead(rig_root, "mc-open")["status"] == "open", "nothing may be written"


def test_revise_with_a_reason_applies(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    r = dashboard.handle(
        Request.post(
            "/preview", operation="adjudicate", brief_id="mc-open", move="revise", reason="add the fields"
        )
    )
    assert r.status == 200, strip_tags(r.body)[:300]
    assert bead(rig_root, "mc-open")["metadata"]["verdict"] == "revise"


def test_reject_with_no_reason_applies(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    r = dashboard.handle(
        Request.post("/preview", operation="adjudicate", brief_id="mc-open", move="reject", reason="")
    )
    assert r.status == 200, strip_tags(r.body)[:300]
    assert bead(rig_root, "mc-open")["metadata"]["verdict"] == "reject"


def test_reject_with_optin_and_no_reason_is_refused(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    r = dashboard.handle(
        Request.post(
            "/preview", operation="adjudicate", brief_id="mc-open",
            move="reject", reason="", no_brainer="1",
        )
    )
    assert r.status >= 400, "reject opted-in with no reason must be refused"
    assert bead(rig_root, "mc-open")["status"] == "open"


def test_defer_needs_no_reason_and_converts_the_unit(tmp_path: Path):
    dashboard, _, rig_root = dashboard_for(tmp_path)
    r = dashboard.handle(
        Request.post(
            "/preview", operation="adjudicate", brief_id="mc-open",
            move="defer", reason="", days="2", days_unit="weeks",
        )
    )
    assert r.status == 200, strip_tags(r.body)[:300]
    assert bead(rig_root, "mc-open")["status"] == "deferred"


def test_the_defer_duration_unit_is_converted_to_days():
    from mctl_dashboard.app import OPERATIONS, _arguments_for

    args = _arguments_for(OPERATIONS["defer"], "mc-open", {"days": "2", "days_unit": "weeks"})
    assert args["days"] == 14, "two weeks must resolve to 14 days"
    args_mo = _arguments_for(OPERATIONS["defer"], "mc-open", {"days": "3", "days_unit": "months"})
    assert args_mo["days"] == 90, "three months must resolve to 90 days"
