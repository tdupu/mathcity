"""mc-mft4c: a typed brief could not say it had not computed an unlock count.

`create-brief`'s contract (`skills/create-brief/SKILL.md:60,67`) declares
`unlock_count: <int> | UNKNOWN-NOT-COMPUTED` and requires the sentinel when the
number cannot be measured. `_pile_document` — the only code-enforced brief
writer under B2.11 — emitted neither, so the record could not distinguish
"the producer did not compute one" from "the producer does not emit this field".

Absent and the sentinel both RENDER as `—`, so this changes no pixel. It changes
what the record asserts, which is the same distinction protected by
`body_elided` over a silent omission (#229), `expired: None` over `False` (#66),
`dashboard: unknown` over a silent `both` (mc-i4d6u), and `gate_state_known:
false` over an invented PROMOTABLE (#226).

TWO THINGS THIS MUST NEVER BECOME, and the tests below exist for them:

1. **`0`.** The contract forbids it in as many words: `0` is a MEASUREMENT
   claiming the brief blocks nothing, and it sorts a live blocker to the bottom
   of an `unlock_count`-ranked stack.

2. **A DERIVED count.** `briefs.py:1821` records the measurement that settled
   this: counting what a brief's bead unblocks returns ~0, because 508 of the
   live store's 528 edges are `related` and 1 bead in 264 carries a blocking
   edge. So a derivation would produce exactly the false zero of (1). I set out
   to build that derivation and stopped only on reading that line.
"""
from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.effects import UNLOCK_COUNT_NOT_COMPUTED, _pile_document


def _frontmatter(doc: str) -> dict[str, str]:
    assert doc.startswith("---\n"), doc[:40]
    block = doc.split("---", 2)[1]
    out = {}
    for line in block.strip().splitlines():
        key, _, value = line.partition(":")
        out[key.strip()] = value.strip()
    return out


# --- the field is present and is the sentinel ------------------------------


def test_a_created_brief_states_that_no_unlock_count_was_computed() -> None:
    fm = _frontmatter(_pile_document("body", ("mc-src",)))
    assert fm["unlock_count"] == UNLOCK_COUNT_NOT_COMPUTED


def test_it_is_present_even_with_no_sources() -> None:
    """`source_bead` is conditional; the sentinel is not."""
    fm = _frontmatter(_pile_document("body", ()))
    assert fm["unlock_count"] == UNLOCK_COUNT_NOT_COMPUTED


def test_the_sentinel_is_never_zero() -> None:
    """The contract forbids `0` because it is a measurement claiming the brief
    blocks nothing, which sorts a live blocker to the bottom of the ranking."""
    fm = _frontmatter(_pile_document("body", ("mc-src",)))
    assert fm["unlock_count"] != "0"
    assert UNLOCK_COUNT_NOT_COMPUTED != "0"


def test_the_sentinel_is_not_numeric_at_all() -> None:
    """A derived count would be numeric and ~0 for nearly every brief. The
    reader's contract is int-OR-SENTINEL, and this producer supplies the
    sentinel because it does not know what the brief unblocks."""
    with __import__("pytest").raises(ValueError):
        float(UNLOCK_COUNT_NOT_COMPUTED)


# --- the reader's side of the contract -------------------------------------


def test_the_reader_turns_the_sentinel_into_None_not_zero() -> None:
    """The whole point of the sentinel: unknown must stay distinguishable from
    a measured zero rather than impersonating one."""
    from mctl_dashboard.screens.stack import unlock_count

    assert unlock_count({"unlock_count": UNLOCK_COUNT_NOT_COMPUTED}) is None
    assert unlock_count({"unlock_count": 0}) == 0.0, "a real zero must survive as a real zero"
    assert unlock_count({"unlock_count": 7}) == 7.0


# --- what must not change --------------------------------------------------


def test_caller_supplied_frontmatter_is_left_alone() -> None:
    """A body that already has a header is returned untouched — a caller that
    supplied frontmatter must not be given a second block."""
    body = "---\nstatus: custom\nunlock_count: 12\n---\n\nbody"
    assert _pile_document(body, ("mc-src",)) == body


def test_the_existing_keys_still_appear() -> None:
    """Adding a key must not displace `status` or `source_bead` — the latter is
    what the standard profile's provenance check reads."""
    fm = _frontmatter(_pile_document("body", ("mc-src",)))
    assert fm["status"] == "open"
    assert fm["source_bead"] == "mc-src"
