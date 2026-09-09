"""#131: escalations must be queryable.

`escalate.sh` files an escalation as `bd create` + `bd label add human`. So an
escalation IS a bead carrying the `human` label, and "what is escalated right
now" is a label query.

`beads_list` could filter by status, issue_type and has_verdict — but not by
label, so the one question the escalation machinery exists to answer had no
typed reader. Capability present, surface absent: the CT13.2 shape #163
records for blast_radius.

A NEW tool was deliberately not added. `beads_list` already reads beads and
already declares its scope, and registering another tool costs the five
hand-maintained rosters #199 enumerates. A filter on the existing reader is the
smaller change and keeps one bead-read surface.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

from mctl_core.bead_reads import beads_list_payload  # noqa: E402
from mctl_core.beads import Bead  # noqa: E402


def _bead(bead_id, labels=(), status="open"):
    return Bead(
        id=bead_id, title=f"t-{bead_id}", status=status, issue_type="task",
        labels=tuple(labels), source_dependencies=(),
        created_at=None, updated_at=None, raw={},
    )


STORE = (
    _bead("mc-esc1", labels=("human",)),
    _bead("mc-esc2", labels=("human", "priority/p1")),
    _bead("mc-plain", labels=()),
    _bead("mc-other", labels=("commission",)),
)


def _ids(payload):
    return {b["id"] for b in payload["beads"]}


def test_filtering_by_label_selects_only_that_label():
    payload = beads_list_payload(STORE, labels=("human",))
    assert _ids(payload) == {"mc-esc1", "mc-esc2"}


def test_the_scope_block_states_the_label_filter():
    """The scope block is what makes a narrowed read quotable (#245)."""
    payload = beads_list_payload(STORE, labels=("human",))
    scope = payload["scope"]
    assert scope["label_filter"] == ["human"]
    assert scope["matched"] == 2
    assert scope["total_in_store"] == 4


def test_no_label_filter_is_still_a_census():
    """Positive control: without the filter nothing is dropped, or the test
    above would pass against a reader that returned nothing."""
    payload = beads_list_payload(STORE)
    assert _ids(payload) == {"mc-esc1", "mc-esc2", "mc-plain", "mc-other"}
    assert payload["scope"]["label_filter"] is None


def test_multiple_labels_are_an_OR():
    """`human` OR `commission` — an AND would make "what is escalated" require
    knowing every other label a bead carries."""
    payload = beads_list_payload(STORE, labels=("human", "commission"))
    assert _ids(payload) == {"mc-esc1", "mc-esc2", "mc-other"}


def test_an_unmatched_label_returns_empty_not_everything():
    payload = beads_list_payload(STORE, labels=("nonexistent",))
    assert _ids(payload) == set()
    assert payload["scope"]["matched"] == 0
