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
#: The `verdict:` key in a brief markdown file's own frontmatter. Distinct from
#: `decisions_track`, which is the manifest *row*: 21 decisions-track files and
#: 22 stack files carry a frontmatter verdict, and folding the two together
#: would claim the manifest recorded a decision that only the document holds.
SOURCE_BRIEF_FRONTMATTER = "brief_frontmatter"

#: `notes` is a fourth value beyond the three the plan named. It is kept
#: distinct rather than folded into `typed_field` because folding it in would
#: report a parsed prose block as a typed column -- the exact over-claim of
#: provenance this module exists to prevent. 7 live briefs resolve only here.
SOURCES = (
    SOURCE_TYPED_FIELD,
    SOURCE_CLOSE_REASON,
    SOURCE_NOTES,
    SOURCE_DECISIONS_TRACK,
    SOURCE_BRIEF_FRONTMATTER,
)

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
CODE_NOT_A_KILL_SWITCH_BRIEF = "MBRF055"
CODE_DECLARED_NO_SUBJECT = "MBRF056"

#: What `non_brief_code` says when it removes a bead from the population.
NON_BRIEF_MESSAGES = {
    CODE_NOT_A_BRIEF: (
        "Decision bead is a git-operation authorization receipt, not a brief (B2.1); "
        "it is a standalone decision bead and has no source to link."
    ),
    CODE_NOT_A_KILL_SWITCH_BRIEF: (
        "Decision bead records a kill-switch engagement or release, not a brief "
        "(B2.1/N5); it is a standalone decision bead and has no source to link."
    ),
}

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
#: Anchored to the start of the field the skill writes it into, NOT a substring
#: search. Slice 2 matched the bare name anywhere in the body, and measured
#: across all 280 live decision beads that exempted **5 real briefs** which
#: merely mention the skill in prose -- `gt-s4r3a1` ("the human approval gate
#: wherever one applies (e.g. `authorize-git-operation` for pushes/PRs)"),
#: `gt-5fxchl`, `gt-8lba37`, `gt-gr755h`, `gsp-qtadi`. A brief that drops out of
#: the population is invisible afterwards, which is precisely the failure a
#: false exemption must not have, so the marker is the skill's own sentence.
_GIT_AUTHORIZATION_MARKER = re.compile(
    r"^\s*(?:#+\s*)?Authoriz(?:ation|ed)\b[^\n]{0,60}?\bauthorize-git-operation\b",
    re.IGNORECASE,
)

#: The tag agents put in a receipt's title when they write one by hand:
#: `[decision][git-auth] AUTHORIZED: …`, `[authorize-git] …`. A bracketed tag is
#: a deliberate structured marker, unlike the free prose the bare name matched.
_GIT_AUTHORIZATION_TAG = re.compile(
    r"\[\s*(?:git-auth|authorize-git(?:-operation)?)\s*\]", re.IGNORECASE
)

#: The receipt template from the same skill's Step 3:
#: `--notes "Operation: <type>. Target: <ref>. Verdict: <AUTHORIZED|DENIED>."`
#: 3 of the 120 live `MBRF004`-blocked beads (`he-0g69g`, `gsp-l5vi`,
#: `gt-d8ztsx`) were written to this template by hand, without the description
#: sentence the marker looks for. Reading the skill's own two output shapes is
#: the same rule, not a wider one.
#:
#: BOTH keys are required, in the skill's order. Neither is distinctive alone --
#: real briefs describe operations and real briefs record verdicts -- and the
#: verdict word must be the skill's `AUTHORIZED`/`DENIED` enum rather than
#: B2.2's `approve`/`reject`/`revise`/`defer`, which is what a brief carries.
#: Measured across all 280 live decision beads this pair matches 49 beads, 47
#: of which also carry the marker, and the other 2 are push receipts by title.
#: Zero false positives.
_RECEIPT_OPERATION = re.compile(r"(?:^|\n)[ \t]*Operation\s*:\s*\S", re.IGNORECASE)
_RECEIPT_VERDICT = re.compile(
    r"\bVerdict\s*:\s*(?:AUTHORIZED|DENIED|DEFERRED|MODIFIED)\b"
)

#: N5 records engaging or releasing the auto-merge kill switch "as a STANDALONE
#: decision bead (a kill-switch authorization record -- its own bead, not a
#: brief verdict; unaffected by the one-bead model)". B2.1 names the same class.
#:
#: Matched on the title, because the title is where the record states what it
#: records, and the act must *govern* the switch: the verb, then at most two
#: words, then the switch. `gsp-pxcu` is a policy-amendment bead whose body
#: discusses the switch hierarchy; `Should the rig-level kill-switch default to
#: engaged?` is a brief asking a question about it. Both contain the switch and
#: an act word, and neither is a record.
#:
#: This is deliberately narrower than the class B2.1 names. There is exactly
#: **one** such bead in the live 280 (`gt-0i99e`, and it is closed, so it is
#: not among the 120 this slice measures), which is far too little evidence to
#: generalise a phrasing from. A record written some other way stays in the
#: population and keeps raising `MBRF004` -- a human then looks at it. That is
#: the safe direction to fail: a missing exemption is visible, a wrong one is
#: not.
_KILL_SWITCH_RECORD = re.compile(
    r"\b(?:engag(?:e|ed|es|ing|ement)|releas(?:e|ed|es|ing)|disengag\w*|"
    r"re-?arm\w*|trip(?:s|ped|ping)?|flips?|flipped|flipping)\b"
    r"(?:\s+[\w./>-]+){0,2}\s+"
    r"(?:kill[-\s]?switch|auto_merge_enabled)",
    re.IGNORECASE,
)


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

    Slice 2 implemented the push-authorization half by the skill's body marker.
    Slice 5 completes it: the same skill's receipt template (which 3 live
    receipts use instead of the marker), and the kill-switch records N5
    likewise requires to be standalone beads.

    **B2.1's third exempt class, "non-brief adjudications", is deliberately NOT
    implemented.** Many of the 71 live `MBRF004`-blocked beads that remain are
    plausibly in it -- session handoffs, memory-migrated policy rules,
    server-run authorizations -- and no rule separates them from a real brief
    without also catching real briefs. Widening this function until the number
    looked better would manufacture exactly the false exemptions B2.1 exists
    to prevent, so the residue stays in the population and is reported to a
    human instead:
    `subdomains/dev/docs/MBRF004-TRIAGE-2026-08-19.md`.
    """
    if not bead.is_brief:
        return False
    return non_brief_code(bead) is None


def non_brief_code(bead: Bead) -> str | None:
    """Which B2.1 exemption removes this decision bead, or None if none does.

    Returned rather than a bool so `_doctor_briefs` can say *why* a bead left
    the population. A bead that is quietly dropped from a listing looks
    identical to a bead that was lost.
    """
    if is_git_authorization_receipt(bead):
        return CODE_NOT_A_BRIEF
    if is_kill_switch_record(bead):
        return CODE_NOT_A_KILL_SWITCH_BRIEF
    return None


def is_git_authorization_receipt(bead: Bead) -> bool:
    """A receipt written by the `authorize-git-operation` skill.

    Only structured markers count -- the skill's receipt sentence at the head of
    a field, its `Operation:`/`Verdict:` notes template, or an explicit
    `[git-auth]` title tag. A bead that merely *mentions* the skill in prose
    stays in the population and keeps raising `MBRF004`.

    That leaves 16 live receipts unexempted, written loosely enough that
    nothing structured identifies them ("Taylor authorized git PUSH: master ->
    tdupu/hecke (7 commits)", whose body says only "authorize-git-operation
    gate."). They are listed in the triage doc for a human to confirm. Failing
    that way round is the point: an unexempted receipt is visible in the
    MBRF004 list, whereas a real brief wrongly exempted disappears from every
    surface and nobody finds out.
    """
    if _GIT_AUTHORIZATION_TAG.search(bead.title or ""):
        return True
    for value in (bead.description, bead.raw.get("notes"), bead.raw.get("design")):
        if not isinstance(value, str) or not value:
            continue
        if _GIT_AUTHORIZATION_MARKER.search(value):
            return True
        operation = _RECEIPT_OPERATION.search(value)
        if operation is None:
            continue
        verdict = _RECEIPT_VERDICT.search(value)
        if verdict is not None and verdict.start() > operation.start():
            return True
    return False


def is_kill_switch_record(bead: Bead) -> bool:
    """A record of engaging or releasing the auto-merge kill switch (N5)."""
    return bool(_KILL_SWITCH_RECORD.search(bead.title or ""))


#: The bd label form of B2.1a's declaration. A label is the most deliberate
#: shape available -- it cannot be typed by accident mid-sentence, and it is
#: queryable with `bd list --label`, so the declaring population stays
#: countable without parsing prose.
NO_SUBJECT_LABEL = "no-subject"

#: The title-tag form: `[no-subject] Should we keep the fast-drain order?`.
#: Bracketed tags are how this pack already marks a deliberate structured
#: claim in a title (`_GIT_AUTHORIZATION_TAG`), so it is the same rule, not a
#: wider one.
_NO_SUBJECT_TAG = re.compile(r"\[\s*no-subject\s*\]", re.IGNORECASE)

#: The body form: a `Source: none` line, ANCHORED to a whole line. The manifest
#: spells this field `source_bead`, and briefs are written by hand, so
#: `Source bead:` and `source-bead:` are the same declaration.
#:
#: The anchors are the whole point. An unanchored search for `source.*none`
#: matches "the source bead is none of the ones above" and "no source bead was
#: found", turning a sentence that DESCRIBES an omission into a declaration
#: that excuses it -- which is the loophole B2.1a exists to not open. Two
#: shipped defects in this repo came from unanchored matching, so the value
#: must be the entire line and nothing else.
_NO_SUBJECT_DECLARATION = re.compile(
    r"^\s*(?:[-*]\s*)?(?:#+\s*)?(?:\*\*)?source(?:[ _-]bead)?(?:\*\*)?\s*:\s*none\s*\.?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


def declares_no_subject(bead: Bead) -> bool:
    """Whether this brief DECLARES that it is about no bead (B2.1a).

    B2.1a admits "this brief is about no bead" as a legitimate statement, so a
    brief that makes it is compliant rather than `MBRF004`. The declaration is
    read here, and only from a structured marker the brief's author had to
    write on purpose: the `no-subject` label, a `[no-subject]` title tag, or a
    whole-line `Source: none` in a body field.

    **Silence is not a declaration.** A bead that merely omits its source link
    returns False and keeps raising `MBRF004`, which is what separates B2.1a
    from a no-op. The distinction is load-bearing: the great majority of live
    beads with no source link are omissions rather than statements -- briefs
    that plainly have a subject and failed to record it, most of them naming
    that subject in their own title or body. Inferring a declaration from their
    silence would relabel every one of them compliant and delete the signal
    that they are recoverable.

    This is the same discipline as `is_git_authorization_receipt`: only
    structured markers count, and a bead that merely discusses having no
    subject in prose stays in the population. Failing that way round is
    deliberate -- an undeclared brief is visible in the `MBRF004` list, whereas
    one wrongly read as declaring disappears into compliance and nobody finds
    out.
    """
    if _NO_SUBJECT_TAG.search(bead.title or ""):
        return True
    if any(label.strip().lower() == NO_SUBJECT_LABEL for label in bead.labels):
        return True
    for value in (bead.description, bead.raw.get("notes"), bead.raw.get("design")):
        if isinstance(value, str) and value and _NO_SUBJECT_DECLARATION.search(value):
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
    non_brief = non_brief_code(bead)
    if non_brief is not None:
        return VerdictReading(None, non_brief, NON_BRIEF_MESSAGES[non_brief], KIND_EMPTY)

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


#: The verdict texts that count as an approval, wherever `read_verdict` found them.
APPROVING_VERDICT_TEXTS = frozenset({"accept", "accepted", "approve", "approved"})


def is_approved_for_dispatch(bead: Bead, *, track: DecisionsTrack | None = None) -> bool:
    """Whether this bead carries a closed, approving verdict.

    The single definition of "approved for dispatch" (#160). `work.py` and
    `briefs.py` each grew their own copy of this check and it drifted: the
    `work.py` copy only read the typed `metadata.verdict` / `decision` /
    `recorded_verdict` fields, which resolved 10 of 139 closed decision beads
    city-wide, while `close_reason` -- the field `bd close` actually writes,
    non-empty on 138 of those 139 -- was never consulted. `briefs_list` and
    `work_status` disagreed on the same bead as a result. Both now call this.
    """
    if bead.status.lower() not in {"closed", "done"}:
        return False
    verdict = read_verdict(bead, track=track)
    if verdict is None:
        return False
    return verdict.text.strip().lower() in APPROVING_VERDICT_TEXTS


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
