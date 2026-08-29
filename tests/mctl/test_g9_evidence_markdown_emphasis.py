r"""G9's PASS check must not be defeated by the markdown bold its producers write.

THE DEFECT. `classifier_error()` finds the evidence line with a substring test
(`"G9 No-brainer-filter:" in line`) but then asserts PASS with
`re.search(r"G9 No-brainer-filter:\s*PASS\b", line)`. Producers emit the label
as a markdown **bold run** -- `**G9 No-brainer-filter:** PASS -- ...` -- so the
character following the colon is `*`, which `\s*` cannot match. The line is
found and then misjudged.

Measured on the live city 2026-08-29:
`hecke/.beads/briefs/.pile/.rejected/he-tzcm-cbmf-264-K-rational-v2-brief/`
records `**G9 No-brainer-filter:** PASS -- no-brainer: true (cat-B merge)` and
carries `rejection.json` reason "G9 No-brainer-filter evidence must be PASS".
The brief says PASS. The gate says it does not.

WHY THIS IS WORTH FIXING EVEN THOUGH IT UNBLOCKS NOTHING. `he-tzcm` still fails
after this change -- it predates the 2026-07-26 G9 amendment and carries no
`classified_at=` -- and that rejection is correct. What changes is that the gate
stops reporting a state it did not verify (B2.13) and stops sending producers to
add a "PASS" that is already there. A diagnostic that names the wrong field is
the P6.2 mirror: not a check that cannot fail, but a failure that cannot be
acted on.

SCOPE. Emphasis is tolerated around the LABEL only. The verdict token itself
must still be a bare `PASS`; `**PASS**` is not accepted, because widening the
value side is how a check quietly stops discriminating.

HOW THESE TESTS COULD FAIL (P6.2). Three negative controls hold the gate shut:
a FAIL line, a line with no verdict at all, and a bolded line that reaches the
NEXT check and is rejected there for the real reason. If the fix were written as
"tolerate anything after the colon", control 3 turns green-for-the-wrong-reason
and the suite says so.
"""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))

_SPEC = importlib.util.spec_from_file_location(
    "fast_drain_g9", REPO_ROOT / "assets" / "scripts" / "brief-shuffle-fast-drain.py"
)
fast_drain = importlib.util.module_from_spec(_SPEC)
sys.modules[_SPEC.name] = fast_drain
_SPEC.loader.exec_module(fast_drain)

WELL_FORMED = (
    "G9 No-brainer-filter: PASS classified_at=2026-08-29T00:00:00Z "
    "classifier_state=known_non_no_brainer reason=needs-human-judgement"
)
BOLDED = (
    "**G9 No-brainer-filter:** PASS classified_at=2026-08-29T00:00:00Z "
    "classifier_state=known_non_no_brainer reason=needs-human-judgement"
)

NOT_PASS = "G9 No-brainer-filter evidence must be PASS"


def test_plain_label_passes_today():
    """Control: the unbolded spelling was never broken."""
    assert fast_drain.classifier_error(WELL_FORMED) is None


def test_bolded_label_is_accepted():
    """THE FIX. Identical evidence, bolded label, must reach the same verdict."""
    assert fast_drain.classifier_error(BOLDED) is None


def test_underscore_emphasis_is_accepted():
    assert fast_drain.classifier_error(BOLDED.replace("**", "__")) is None


# ---- negative controls: the gate must still shut ----

def test_bolded_fail_is_still_rejected():
    assert fast_drain.classifier_error(BOLDED.replace("PASS", "FAIL")) == NOT_PASS


def test_bolded_line_with_no_verdict_is_still_rejected():
    assert fast_drain.classifier_error(BOLDED.replace("PASS ", "")) == NOT_PASS


def test_bolded_line_still_faces_every_later_check():
    """The real he-tzcm shape: bolded, genuinely PASS, and missing classified_at.

    It must get PAST the PASS check and be rejected by the timestamp check --
    the accurate reason. If this returns the PASS error, the label fix did not
    happen; if it returns None, the fix went too far and dissolved G9.
    """
    line = "**G9 No-brainer-filter:** PASS -- no-brainer: true (cat-B merge)."
    assert fast_drain.classifier_error(line) == "G9 evidence must set classified_at=<ISO-8601-utc>"


def test_emphasis_is_not_tolerated_around_the_verdict_token():
    """`**PASS**` is a different claim shape and is not what producers write."""
    assert fast_drain.classifier_error(BOLDED.replace("PASS", "**PASS**")) == NOT_PASS
