"""A city-wide apply lost the rig, and the loss was invisible.

Measured against the running dashboard before the fix:

    rig-scoped (--rig hecke)   preview 200 -> apply 200   verdict landed
    city-wide  (no --rig)      preview 200 -> apply 000   nothing landed

The apply form posts only `token`. `_apply` then asks `_rig_for(request)` which
finds no rig in city scope, and `context_resolve` raises
`MCTL_CONTEXT_RIG_REQUIRED`. The exception is unhandled, so the handler dies and
the connection is dropped: **HTTP 000, no page, no diagnostic.**

**Taylor adjudicates city-wide** -- one queue across 17 rigs is the point of the
dashboard -- so the final step of the loop was broken on precisely the path he
takes, while every rig-scoped test passed. That is why "nobody has adjudicated
end to end" stayed true without anyone finding a cause.

The fix is NOT to put the rig in the form. `Preview.rig` already records the rig
the plan was taken against, and `_rig_for` re-reads the request so that a confirm
naming a *different* rig is caught as a change. Echoing the preview's own rig back
through the form would make that comparison compare a value to itself -- a check
that cannot fail, which is the defect class this dashboard exists to not commit.

So: fall back to the preview's recorded rig when the request names none, keep
detecting an explicit mismatch, and **refuse loudly when no rig can be determined
at all.** A verdict that cannot be routed must never write to a default -- losing
the rig means the verdict goes nowhere or somewhere wrong, and both are worse than
a refusal.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.app import Dashboard, Request


def test_the_request_rig_wins_when_it_names_one():
    """An explicit `?rig=` must still be honoured, so a genuine mismatch is
    still detectable by `Preview.matches`."""
    from mctl_dashboard.app import rig_for_apply

    class _P:
        rig = "hecke"

    assert rig_for_apply("gascity", _P()) == "gascity"


def test_the_preview_rig_is_used_when_the_request_names_none():
    """The city-wide apply form posts only the token. That is not a rig
    switch -- it is the form not carrying one -- so the plan's own rig stands."""
    from mctl_dashboard.app import rig_for_apply

    class _P:
        rig = "hecke"

    assert rig_for_apply(None, _P()) == "hecke"


def test_neither_gives_nothing_so_the_caller_must_refuse():
    """The failure direction that matters.

    If no rig can be determined the verdict must NOT be written to a default.
    Losing the rig means the write goes nowhere or somewhere wrong, and both
    are worse than a refusal.
    """
    from mctl_dashboard.app import rig_for_apply

    class _P:
        rig = None

    assert rig_for_apply(None, _P()) is None


def test_an_empty_string_rig_is_not_a_rig():
    """`_rig_for` already normalises blanks to None; this must not resurrect
    one as a truthy value."""
    from mctl_dashboard.app import rig_for_apply

    class _P:
        rig = "hecke"

    assert rig_for_apply("", _P()) == "hecke"


# ---------------------------------------------------------------------------
# a failure must be a page, never a dropped connection
# ---------------------------------------------------------------------------


def test_a_failing_mutation_renders_a_page_instead_of_raising():
    """The second defect, and the worse one.

    When apply raised, the server dropped the connection: HTTP 000, no page, no
    diagnostic. The operator clicks Apply and gets nothing at all -- which
    teaches them the click did nothing, when it might have done anything.

    Any failure on a mutation route must come back as a response.
    """
    from mctl_dashboard.app import Dashboard, Request

    class _Exploding:
        def call(self, *a, **k):
            raise RuntimeError("boom")

        def list_tools(self):
            return []

        def clone(self):
            return self

    app = Dashboard(_Exploding(), city_wide=True, rig=None)
    response = app.handle(Request.post("/apply", token="deadbeef"))
    assert response is not None
    assert response.status >= 400
    assert response.body
