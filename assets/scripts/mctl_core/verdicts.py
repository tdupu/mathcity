"""Read the verdict a closed brief already carries.

`_verdict()` looked in `metadata.verdict`, `decision`, and `recorded_verdict`.
Two of those three are not bd columns at all, so they could never hit, and
measured across the live six-store city they resolved **10 of 139** closed
decision beads. `close_reason` -- the field `bd close` actually writes -- is
non-empty on **138 of 139** and was never read at all. The corpus was in far
better shape than the reader.

**The corpus needs no migration for this; the reader needed one.** Nothing in
this module writes.

## Why this is a parser and not a fourth key lookup

`close_reason` is free text, and across the live corpus it carries five
different kinds of thing. Only the first is a verdict:

===================  ==========================================================
verdict              ``approve: YES, this is a no-brainer...``
execution record     ``All five decisions implemented: memory governor...``
supersession         ``superseded by he-saeno4 (B4 decision recorded there)``
withdrawal           ``Brief he-tqze KILLED -- jumbled; replaced by he-t0c9``
free narrative       ``Closed``
===================  ==========================================================

An execution record means the verdict happened *earlier and elsewhere*; a
supersession means it lives on *another bead*. Reading either as a verdict
would manufacture an adjudication that nobody ever made -- the same mass
false positive `MBRF021` produced, which this repo is still cleaning up after.
So the four non-verdict shapes return `None` **with a diagnostic naming which
shape it was**, never a guess, and the caller can say *why* a brief is not
readable instead of only that it is not.

The recognisers are anchored at the start of the text (or of its first line)
rather than being substring searches, because these strings were written to a
convention -- the disposition leads. A substring search for "approve" matches
"Superseded -- fork-canonical merge flow adopted", which is precisely the
error class this module exists to avoid.

## Provenance is part of the answer

Every `Verdict` carries `source` and `confidence`. It has to: of the 10 typed
values in the live corpus, 7 sit beside a `legacy verdict backfill:`
`close_reason` they were copied from, and 5 of the 10 disagree with the
`close_reason` next to them -- `A-RESUBMIT-WITH-TARGET-MASTER` against
`A-RESUBMIT-WITH-CORRECT-TARGET-NAME`, and four more like it. A surface that
rendered all verdicts identically would be asserting a uniformity the data
does not have, so a typed field that contradicts its own cited source is
reported at low confidence rather than silently preferred.

(The audit that motivated this slice put the backfill count at 9 and the
disagreements at 2 of 7 spot-checked; both numbers above are re-derived
against all 139 closed beads.)

## The decisions-track lane, measured

`policy_refs.B2.10` calls `.beads/decisions-track/manifest.jsonl` migration
input rather than an active presentation lane. Slice 2 revisits that, and the
measurement settles it: of the manifest's **126 rows carrying a typed
`verdict`, 0 join to any decision bead** by any principled key -- bead id,
brief source dependency, or `metadata.brief_path` slug. 97 of the 126 carry no
`source_bead` at all, and the 20 distinct beads the rest name are work items,
none of them `type=decision`. The two lanes are disjoint populations: the
decisions-track briefs were never materialised as decision beads.

The join is implemented here anyway, because it is the lane a migration would
use and a reader that cannot see it cannot report that it is empty. It is
**not** wired into `_decision_state`: doing so would buy zero rows today at
the cost of a per-call file read on every brief listing.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Iterable, Mapping, Sequence

from .beads import Bead


#: Where a verdict was read from. Always reported -- see the module docstring.
SOURCE_TYPED_FIELD = "typed_field"
SOURCE_CLOSE_REASON = "close_reason"
SOURCE_NOTES = "notes"
SOURCE_DECISIONS_TRACK = "decisions_track"

#: `notes` is a fourth value beyond the three the plan named. It is kept
#: distinct rather than folded into `typed_field` because folding it in would
#: report a parsed prose block as a typed column -- the exact over-claim of
#: provenance this module exists to prevent. 7 live briefs resolve only here.
SOURCES = (SOURCE_TYPED_FIELD, SOURCE_CLOSE_REASON, SOURCE_NOTES, SOURCE_DECISIONS_TRACK)

CONFIDENCE_HIGH = "high"
CONFIDENCE_MEDIUM = "medium"
CONFIDENCE_LOW = "low"
CONFIDENCES = (CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, CONFIDENCE_LOW)

#: bd columns and metadata keys that are meant to hold a verdict outright.
#: `verdict` is the live one; `decision` and `recorded_verdict` never existed
#: as columns but are read for the fixtures and callers that still set them.
TYPED_VERDICT_KEYS = ("verdict", "decision", "recorded_verdict")

#: Why a close_reason is not a verdict. Registered in assets/mctl/diagnostics.toml.
CODE_SUPERSESSION = "MBRF050"
CODE_EXECUTION_RECORD = "MBRF051"
CODE_WITHDRAWAL = "MBRF052"
CODE_UNREADABLE = "MBRF053"
CODE_NOT_A_BRIEF = "MBRF054"

#: How `close_reason` was classified, independent of whether it resolved.
KIND_VERDICT = "verdict"
KIND_SUPERSESSION = "supersession"
KIND_EXECUTION_RECORD = "execution_record"
KIND_WITHDRAWAL = "withdrawal"
KIND_NARRATIVE = "narrative"
KIND_EMPTY = "empty"

_KIND_CODES = {
    KIND_SUPERSESSION: CODE_SUPERSESSION,
    KIND_EXECUTION_RECORD: CODE_EXECUTION_RECORD,
    KIND_WITHDRAWAL: CODE_WITHDRAWAL,
    KIND_NARRATIVE: CODE_UNREADABLE,
    KIND_EMPTY: CODE_UNREADABLE,
}

_KIND_MESSAGES = {
    KIND_SUPERSESSION: (
        "Closed brief's close_reason points at a successor bead; the decision was "
        "recorded there, not here."
    ),
    KIND_EXECUTION_RECORD: (
        "Closed brief's close_reason reports work carried out against a verdict "
        "given earlier and elsewhere."
    ),
    KIND_WITHDRAWAL: (
        "Closed brief was withdrawn, killed, or closed as moot; no verdict was given on it."
    ),
    KIND_NARRATIVE: "Closed brief carries no readable verdict in any known field.",
    KIND_EMPTY: "Closed brief carries no readable verdict in any known field.",
}


# --------------------------------------------------------------------------
# recognisers
# --------------------------------------------------------------------------

# The decision lives on another bead. `Superseded --` (em dash, no id) is the
# same shape written without the pointer, and is treated the same way: it still
# says "not here".
_SUPERSESSION = re.compile(
    r"^\s*(?:superseded\b|supersedes\b|duplicate\b|transferred\s+to\b|moved\s+to\b)",
    re.IGNORECASE,
)
_SUPERSEDED_INLINE = re.compile(r"\bsuperseded\s+by\b", re.IGNORECASE)

# The brief was withdrawn rather than decided. `moot`/`stale` closures record
# that the question stopped applying, not that anyone answered it.
_WITHDRAWAL = re.compile(
    r"^\s*(?:"
    r"moot\b|stale\b|permanently\s+blocked\b|"
    r"brief\s+\S+\s+KILLED\b|brief\s+CANCEL-CLOSED\b|"
    r"cancelled\b|canceled\b|withdrawn\b|killed\b|"
    # xkcd-927 closures say the brief should never have been raised.
    r"xkcd-927\b"
    r")",
    re.IGNORECASE,
)

# The work was done. Whoever authorised it did so somewhere this text is not.
_EXECUTION_RECORD = re.compile(
    r"^\s*(?:"
    r"executed\b|"
    r"(?:decision|verdict)\s+(?:executed|implemented|fully\s+executed|fully\s+documented)\b|"
    r"(?:both\s+)?push(?:es)?\s+executed\b|"
    r"push[^:\n]{0,40}receipt\b|"
    r"push/sync\s+authorization\s+receipt\b|"
    r"published\b|"
    r"repair\s+complete\b|"
    r"verified\b|"
    r"root\s+cause\s+diagnosed\b|"
    r"done\s*:|"
    r"bookkeeping\s+correction\b|"
    r"brief-record\s+(?:closed|resolved)\b|"
    r"all\s+(?:\d+|\w+)\s+(?:implementation\s+items|decisions?|amendments)\b"
    r")",
    re.IGNORECASE,
)

# A verdict recorded as a pointer to where the verdict is written down. The
# semicolon matters: `Decision recorded: <text>` states the decision, whereas
# `Decision recorded; verdicts in <file>` names a file and states nothing.
_VERDICT_ELSEWHERE = re.compile(
    r"^\s*decision\s+recorded\s*[;,]|"
    r"\bsee\s+(?:the\s+)?verdict\s+comment\b",
    re.IGNORECASE,
)

# Each pattern captures the verdict itself, so the recorded text is the
# decision and not the sentence that introduces it.
_VERDICT_PATTERNS = (
    re.compile(
        r"^\s*legacy\s+verdict\s+backfill\s*:\s*(?P<verdict>.+?)"
        r"(?:\s+per\s+decisions\.jsonl.*)?$",
        re.IGNORECASE | re.DOTALL,
    ),
    # `Taylor verdict: X`, `Taylor verdict 2026-07-22: X`, `Taylor verdict A (date): X`
    re.compile(r"^\s*taylor\s+verdict\b[^:\n]{0,40}:\s*(?P<verdict>.+)$", re.IGNORECASE | re.DOTALL),
    # `approve:`, `APPROVED --`, `approved Q18 ...`: the inflection varies, so
    # the suffix is matched rather than a bare \b, which `APPROVED` fails.
    re.compile(r"^\s*(?P<verdict>approv(?:e|ed|al)\b.*)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"^\s*(?P<verdict>reject(?:ed)?\b.*)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"^\s*(?P<verdict>revis(?:e|ed)\b.*)$", re.IGNORECASE | re.DOTALL),
    # The actor is kept inside the capture: "Taylor ratified 2026-07-03 as-is"
    # is the record, and "ratified 2026-07-03 as-is" is a fragment of one.
    re.compile(
        r"^\s*(?P<verdict>taylor\s+(?:ratified|approved|confirmed|adopted)\b.*)$",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"^\s*(?P<verdict>policy\s+(?:decision\s+recorded|ratified)\b.*)$",
        re.IGNORECASE | re.DOTALL,
    ),
    re.compile(
        r"^\s*decision\s+recorded\b[^:\n]{0,30}:\s*(?P<verdict>.+)$", re.IGNORECASE | re.DOTALL
    ),
    re.compile(r"^\s*decision\s*:\s*(?P<verdict>.+)$", re.IGNORECASE | re.DOTALL),
    re.compile(r"^\s*(?P<verdict>decision\s+recorded\s*\.?)\s*$", re.IGNORECASE),
)

#: The canonical shape the adjudicate-brief skill writes into `notes`:
#: `VERDICT: approve | AUTHORIZER: Taylor | RATIONALE: ...`. Anchored to a line
#: start and requiring the `VERDICT:` key, so prose that merely discusses a
#: verdict does not match.
_NOTES_CANONICAL = re.compile(
    r"^\s*VERDICT\s*[:=]\s*(?P<verdict>[^|\n]+?)\s*(?:\||$)", re.IGNORECASE | re.MULTILINE
)

#: The `authorize-git-operation` skill stamps this into the bead body it
#: creates. It is the only structured marker these receipts carry -- they have
#: no distinguishing label or metadata key -- and it is far safer than matching
#: their titles, which real briefs about authorisation also match.
_GIT_AUTHORIZATION_MARKER = re.compile(r"authorize-git-operation", re.IGNORECASE)


@dataclass(frozen=True)
class Verdict:
    """A verdict that was actually recorded, and where it was found.

    `text` is the verdict as written -- never normalised into a controlled
    vocabulary, because the live corpus records verdicts as everything from
    `approve` to `PER-ITEM-VERBATIM-PASSED-TO-MAYOR-FOR-DECOMPOSITION`, and
    collapsing those would lose the decision.
    """

    text: str
    source: str
    confidence: str
    #: The exact field the text came from, e.g. `metadata.verdict`.
    field: str

    def to_dict(self) -> dict[str, str]:
        return {
            "confidence": self.confidence,
            "field": self.field,
            "source": self.source,
            "text": self.text,
        }


@dataclass(frozen=True)
class VerdictReading:
    """The verdict, or the typed reason there is not one.

    A caller that only wants the verdict uses `read_verdict`. A caller that has
    to explain an unadjudicated brief to an operator wants this: "the decision
    is on the successor bead" and "nobody ever decided this" are different
    facts, and only one of them is a defect.
    """

    verdict: Verdict | None
    code: str | None = None
    message: str | None = None
    #: How `close_reason` read, whether or not it resolved.
    kind: str = KIND_EMPTY

    @property
    def resolved(self) -> bool:
        return self.verdict is not None


@dataclass(frozen=True)
class CloseReasonReading:
    kind: str
    text: str | None = None


class DecisionsTrack:
    """The legacy `.beads/decisions-track/manifest.jsonl` lane.

    Measured on the live city: 126 rows carry a typed `verdict` and **none of
    them joins to a decision bead**. Kept because it is the lane a migration
    would read, and because a reader that cannot see it cannot prove it empty.
    """

    def __init__(self, rows: Sequence[Mapping[str, object]] = ()):
        self._by_key: dict[str, str] = {}
        for row in rows:
            verdict = row.get("verdict")
            if not isinstance(verdict, str) or not verdict.strip():
                continue
            for key in _track_keys(row):
                self._by_key.setdefault(key, verdict.strip())

    @classmethod
    def from_rows(cls, rows: Iterable[Mapping[str, object]]) -> "DecisionsTrack":
        return cls(tuple(rows))

    @classmethod
    def load(cls, rig_root: Path) -> "DecisionsTrack":
        """Read the manifest under `rig_root`, or an empty track if unreadable.

        Never raises: this is a supplementary lane, and a brief listing must
        not fail because a legacy migration file is malformed.
        """
        path = Path(rig_root) / ".beads" / "decisions-track" / "manifest.jsonl"
        rows: list[Mapping[str, object]] = []
        try:
            with path.open(encoding="utf-8") as handle:
                for line in handle:
                    stripped = line.strip()
                    if not stripped:
                        continue
                    try:
                        value = json.loads(stripped)
                    except json.JSONDecodeError:
                        continue
                    if isinstance(value, dict):
                        rows.append(value)
        except OSError:
            return cls(())
        return cls(tuple(rows))

    def verdict_for(self, bead: Bead) -> str | None:
        for key in _bead_track_keys(bead):
            found = self._by_key.get(key)
            if found:
                return found
        return None

    def __len__(self) -> int:
        return len(self._by_key)


def _track_keys(row: Mapping[str, object]) -> tuple[str, ...]:
    """Identifiers a manifest row offers for joining to a bead.

    `decision_bead`/`bead`/`bead_id` would name the bead outright; no live row
    carries one. `source_bead` names the work the brief was about, which is
    how a brief bead's own source dependency identifies it.
    """
    keys: list[str] = []
    for field in ("decision_bead", "bead", "bead_id", "source_bead"):
        value = row.get(field)
        if isinstance(value, str) and value and value != "none":
            keys.append(value)
    return tuple(keys)


def _bead_track_keys(bead: Bead) -> tuple[str, ...]:
    return (bead.id, *bead.source_dependencies)


def is_brief_bead(bead: Bead) -> bool:
    """Whether this decision bead is a brief at all.

    POLICY B2.1 says in as many words that decision beads created for other
    purposes -- push authorizations, kill-switch records, non-brief
    adjudications -- stay standalone beads rather than joining the brief
    population. `Bead.is_brief` implements none of that sentence; it asks only
    `issue_type == "decision"`, which is why 36 closed `authorize-git-operation`
    receipts are currently counted as malformed briefs.

    This implements the push-authorization half, which is the measurable one:
    those receipts carry the skill's own marker in their body. The remaining
    B2.1 exemptions are Slice 5's, which owns the population filter itself.
    """
    if not bead.is_brief:
        return False
    return not is_git_authorization_receipt(bead)


def is_git_authorization_receipt(bead: Bead) -> bool:
    for value in (bead.description, bead.raw.get("notes"), bead.raw.get("design")):
        if isinstance(value, str) and _GIT_AUTHORIZATION_MARKER.search(value):
            return True
    return False


def brief_population(beads: Iterable[Bead]) -> tuple[Bead, ...]:
    """The beads that are briefs, with the B2.1 non-briefs removed."""
    return tuple(bead for bead in beads if is_brief_bead(bead))


def classify_close_reason(text: str | None) -> CloseReasonReading:
    """Which of the five things this `close_reason` is."""
    if not text or not text.strip():
        return CloseReasonReading(KIND_EMPTY)
    stripped = text.strip()
    first_line = stripped.splitlines()[0]
    if _SUPERSESSION.match(first_line) or _SUPERSEDED_INLINE.search(first_line):
        return CloseReasonReading(KIND_SUPERSESSION)
    if _WITHDRAWAL.match(first_line):
        return CloseReasonReading(KIND_WITHDRAWAL)
    if _EXECUTION_RECORD.match(first_line):
        return CloseReasonReading(KIND_EXECUTION_RECORD)
    if _VERDICT_ELSEWHERE.search(first_line):
        return CloseReasonReading(KIND_NARRATIVE)
    for pattern in _VERDICT_PATTERNS:
        match = pattern.match(stripped)
        if match:
            return CloseReasonReading(KIND_VERDICT, " ".join(match.group("verdict").split()))
    return CloseReasonReading(KIND_NARRATIVE)


def read_verdict(bead: Bead, *, track: DecisionsTrack | None = None) -> Verdict | None:
    """The verdict this bead carries, or None. Never a guess."""
    return read_verdict_reading(bead, track=track).verdict


def read_verdict_reading(bead: Bead, *, track: DecisionsTrack | None = None) -> VerdictReading:
    """The verdict, or the typed reason there is not one.

    Precedence is bead-first: a field on the bead outranks the legacy manifest,
    and an explicitly typed field outranks text that had to be parsed.
    """
    if is_git_authorization_receipt(bead):
        return VerdictReading(
            None,
            CODE_NOT_A_BRIEF,
            "Decision bead is an authorize-git-operation receipt, not a brief (B2.1); "
            "it belongs outside the brief population rather than gaining a verdict.",
            KIND_EMPTY,
        )

    close_reason = bead.raw.get("close_reason")
    close_reason = close_reason if isinstance(close_reason, str) else None
    reading = classify_close_reason(close_reason)

    typed = _typed_verdict(bead)
    if typed is not None:
        text, field = typed
        return VerdictReading(
            Verdict(text, SOURCE_TYPED_FIELD, _typed_confidence(text, reading), field),
            kind=reading.kind,
        )

    notes = bead.raw.get("notes")
    if isinstance(notes, str):
        match = _NOTES_CANONICAL.search(notes)
        if match:
            text = " ".join(match.group("verdict").split())
            if text:
                return VerdictReading(
                    Verdict(text, SOURCE_NOTES, CONFIDENCE_HIGH, "notes"),
                    kind=reading.kind,
                )

    if reading.kind == KIND_VERDICT and reading.text:
        return VerdictReading(
            Verdict(reading.text, SOURCE_CLOSE_REASON, CONFIDENCE_MEDIUM, "close_reason"),
            kind=reading.kind,
        )

    if track is not None:
        found = track.verdict_for(bead)
        if found:
            return VerdictReading(
                Verdict(
                    found,
                    SOURCE_DECISIONS_TRACK,
                    CONFIDENCE_LOW,
                    "decisions-track/manifest.jsonl:verdict",
                ),
                kind=reading.kind,
            )

    return VerdictReading(
        None,
        _KIND_CODES.get(reading.kind, CODE_UNREADABLE),
        _KIND_MESSAGES.get(reading.kind, _KIND_MESSAGES[KIND_NARRATIVE]),
        reading.kind,
    )


def _typed_verdict(bead: Bead) -> tuple[str, str] | None:
    for key in TYPED_VERDICT_KEYS:
        value = bead.raw.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip(), key
    metadata = bead.raw.get("metadata")
    if isinstance(metadata, Mapping):
        for key in TYPED_VERDICT_KEYS:
            value = metadata.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip(), f"metadata.{key}"
    return None


def _typed_confidence(text: str, reading: CloseReasonReading) -> str:
    """High, unless the typed value contradicts the source it cites.

    7 of the 10 typed values in the live corpus sit beside a `legacy verdict
    backfill:` close_reason they were copied from, and 5 of the 10 disagree
    with the close_reason beside them. A disagreement is not resolvable from
    here -- both readings are on the bead -- so it is reported rather than
    picked between.
    """
    if reading.kind != KIND_VERDICT or not reading.text:
        return CONFIDENCE_HIGH
    return CONFIDENCE_HIGH if _same_verdict(text, reading.text) else CONFIDENCE_LOW


def _same_verdict(left: str, right: str) -> bool:
    """Whether two recordings of a verdict say the same thing.

    Prefix agreement counts: a typed `approve` beside a close_reason reading
    `approve: gate-fix re-verification test` is the same verdict with its
    subject attached, not a contradiction. Only a genuine divergence --
    `A-RESUBMIT-WITH-TARGET-MASTER` against
    `A-RESUBMIT-WITH-CORRECT-TARGET-NAME` -- lowers confidence.
    """
    first, second = _normalize(left), _normalize(right)
    if not first or not second:
        return False
    return first.startswith(second) or second.startswith(first)


def _normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.lower())
