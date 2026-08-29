"""The artifact-trust warning calls a DECIDED question open, and sends you to re-open it.

THE DEFECT
----------
Every mctl response carrying artifact state emits:

    "Open design question Q5 must resolve before any artifact-state finding
     here is acted on."
    hint: "Read Q5 in subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md#q5"

Q5 is not open. Its own document says so:

    **Status:** **RESOLVED** (direction set; implementation deliberately
    deferred) · **Owner:** Taylor · **Decided:** 2026-08-19

Taylor ruled both halves. Storage: *"The brief stack was originally a single
stack but I think a better design is per rig and having the agents/application
report on the city-wide status."* Lookup: *"I don't care how the pile look-up
goes. I guess the briefs are supposed to be decision beads so it should be
however beads are looked-up."*

WHY THIS IS WORTH A TEST RATHER THAN A ONE-LINE EDIT
---------------------------------------------------
Untrusting the readings is still CORRECT -- the implementation is deferred, so
the filesystem has not caught up and MBRF021 still over-reports. Only the REASON
is wrong. But it is wrong in the expensive direction: it routes the reader to
re-open a question the owner answered, and re-asking a human a settled question
is the costliest failure this system has. It is the same shape as brief mc-tbucy
being read as unadjudicated and nearly sent back for a second verdict, on
2026-08-28, by an agent reading a status field that said otherwise.

So the assertions are paired: the message must NOT assert Q5 is unresolved, and
it must STILL warn. A fix that made the warning cheerful would be worse than the
defect, because the readings really are untrustworthy today.

  * test_the_warning_does_not_call_q5_unresolved  -- the defect. FAILS before.
  * test_the_warning_still_warns                  -- the inverse. Must not regress.
  * test_the_warning_names_what_would_clear_it    -- an untrusted state with no
                                                     stated exit is a dead end.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_core.diagnostics import Severity  # noqa: E402
from mctl_core.mcp_server import (  # noqa: E402
    ArtifactTrust,
    _untrusted_state_diagnostic,
)


class _Ctx:
    """Minimal stand-in: the diagnostic reads only these fields."""

    city_root = Path("/city")
    rig_root = Path("/city/rig")
    rig_id = "rig"
    trace_id = "trace-1"


def _diagnostic():
    trust = ArtifactTrust(
        trusted=False,
        reason="a pile file carries its bead id in frontmatter rather than its filename",
        resolved_brief_root="/city/rig/.beads/briefs",
        resolved_pile="/city/rig/.beads/briefs/.pile",
        open_question="Q5",
        reference="subdomains/dev/docs/OPEN-DESIGN-QUESTIONS.md#q5",
        withheld_codes=("MBRF021",),
    )
    return _untrusted_state_diagnostic(_Ctx(), trust)


def test_the_warning_does_not_call_q5_unresolved() -> None:
    """Q5 was decided 2026-08-19. Saying it "must resolve" invites re-litigation."""
    text = f"{_diagnostic().message} {_diagnostic().hint or ''}".lower()

    assert "must resolve" not in text, (
        "Q5 is RESOLVED (direction set, implementation deferred); this sends the "
        "reader to re-decide a question Taylor already answered"
    )
    assert "open design question q5" not in text


def test_the_warning_still_warns() -> None:
    """The inverse control. The readings ARE untrustworthy; do not soften this.

    Without this test, deleting the warning entirely would pass the test above,
    which would be strictly worse than the defect it fixes.
    """
    diagnostic = _diagnostic()

    assert diagnostic.severity == Severity.WARN
    assert diagnostic.code == "MCTL_MCP_ARTIFACT_STATE_UNTRUSTED"
    assert "not trustworthy" in diagnostic.message.lower()
    assert "mbrf021" in (diagnostic.hint or "").lower()


def test_the_warning_names_what_would_clear_it() -> None:
    """An untrusted state with no stated exit is a dead end for the reader.

    The pending work is IMPLEMENTATION, not a decision, and the message should
    say which so nobody goes looking for an owner to ask.
    """
    text = f"{_diagnostic().message} {_diagnostic().hint or ''}".lower()

    assert "implementation" in text or "implemented" in text
    assert "decided" in text or "direction" in text
