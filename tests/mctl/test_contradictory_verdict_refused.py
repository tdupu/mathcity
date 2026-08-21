"""A form that can submit two verdicts must not silently pick one.

Taylor: *"You can apparently simultaneously accept and reject. That is not
good."*

Measured against the served dashboard before the fix:

    POST /preview  verdict=approve & verdict=reject   -> 200, planned "approve"
    POST /preview  verdict=reject  & verdict=approve  -> 200, planned "reject"

No diagnostic, a token issued, ready to apply. `Request.from_wire` took
`values[0]` from `parse_qs` and discarded the rest, so **the verdict that won was
whichever came first on the wire** -- a function of DOM order, not of intent.

The radios are exclusive in a browser, so this is not reachable by clicking. That
makes it *more* worth refusing rather than less: the paths that can reach it are
a replayed request, a scripted client, a proxy that reorders, or the next UI that
adds a second control. A surface that resolves contradictory input by position is
one refactor away from recording a decision nobody made.

Refuse, do not repair. There is no correct way to guess which of two opposite
verdicts an operator meant.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.app import Request


def _wire(body: str) -> Request:
    return Request.from_wire("POST", "/preview", body)


# ---------------------------------------------------------------------------
# the request records the contradiction instead of hiding it
# ---------------------------------------------------------------------------


def test_a_repeated_field_is_recorded_as_duplicated():
    request = _wire("operation=adjudicate&verdict=approve&verdict=reject")
    assert "verdict" in request.duplicated


def test_the_duplicate_values_are_kept_for_the_message():
    request = _wire("verdict=approve&verdict=reject")
    assert request.duplicated["verdict"] == ("approve", "reject")


def test_a_single_valued_field_is_not_flagged():
    request = _wire("operation=adjudicate&verdict=approve")
    assert request.duplicated == {}


def test_a_field_repeated_with_the_SAME_value_is_not_a_contradiction():
    """Two identical values express one intent; only disagreement is a problem."""
    request = _wire("verdict=approve&verdict=approve")
    assert request.duplicated == {}


def test_first_value_still_wins_for_readers_that_do_not_check():
    """The dict stays usable; the contradiction is surfaced alongside it, so a
    caller that forgets to check is no worse off than before -- and the mutation
    path does check."""
    request = _wire("verdict=approve&verdict=reject")
    assert request.form["verdict"] == "approve"


def test_query_strings_are_checked_too():
    request = Request.from_wire("GET", "/queue?scope=stack&scope=errors")
    assert "scope" in request.duplicated


# ---------------------------------------------------------------------------
# the mutation path refuses
# ---------------------------------------------------------------------------


def _app(tmp_path):
    """Reuse the view tests' harness rather than inventing a second one."""
    from test_dashboard_views import dashboard_for

    app, _client, _city, _rig = dashboard_for(tmp_path)
    return app


def test_preview_refuses_contradictory_verdicts(tmp_path):
    response = _app(tmp_path).handle(
        _wire("operation=adjudicate&brief_id=b1&rig=mathcity&verdict=approve&verdict=reject")
    )
    assert response.status == 400
    assert "verdict" in response.body
    assert "approve" in response.body and "reject" in response.body


def test_the_refusal_names_the_defect_not_just_the_field(tmp_path):
    response = _app(tmp_path).handle(
        _wire("operation=adjudicate&brief_id=b1&rig=mathcity&verdict=approve&verdict=reject")
    )
    body = response.body.lower()
    assert "contradict" in body or "more than one" in body


def test_a_clean_mutation_is_unaffected(tmp_path):
    """The guard must not break the ordinary path."""
    response = _app(tmp_path).handle(
        _wire("operation=adjudicate&brief_id=mc-open&rig=mathcity&verdict=revise&reason=x")
    )
    assert response.status != 400
