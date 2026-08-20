r"""The decisions-track manifest, read as a third source of brief records.

A brief has three representations -- a bead, a stack/pile file, and a row in
`.beads/decisions-track/manifest.jsonl` -- and no identity spans them. Two of
the three have readers. The third did not, and it is not small:

=========================================  =====  ==========================
population                                    n   reachable before this
=========================================  =====  ==========================
manifest rows                                204  as a migration blocker only
… whose slug matches a stack file              46  yes, through the file
… whose slug matches an archived file           0  --
… matching neither                            158  **nothing could read them**
=========================================  =====  ==========================

(Measured 2026-08-19 against the live city. The brief commissioning this
slice measured 45/159 a few days earlier; the one row that moved is a stack
file that has since appeared, and the same off-by-one runs through every
derived count below. Numbers here are the ones re-derived today.)

Of the 158 unreachable rows, **122 carry a typed `verdict`** and 36 do not;
98 carry a timestamp and 60 carry none at all.

## Why these are read, and not materialised into beads

POLICY B2.1 makes a brief a decision bead **with a source dependency**. 105 of
the 158 rows name no source bead (`source_bead` absent, `""`, or `"none"`),
and of the 42 distinct ids the rest do name only 22 resolve in the HQ store at
all. Minting beads would therefore create ~105 beads that fail B2.1 on
creation, raise `MBRF004` apiece, and grow the malformed population this repo
is trying to shrink. Materialisation makes the measured state worse.

So the manifest becomes a **read-side source**: the rows become countable and
presentable, and nothing is written -- to the manifest, to the bead store, or
to the stack.

## `source` is the load-bearing field

Every record this module produces carries `source = "manifest"`, and the
bead-derived records carry `source = "bead"`. Without that field a surface
would render a manifest row exactly like a bead-backed brief, which would
assert that a decision bead attests it. Nothing attests these rows except the
row itself. The verdict inside one carries its own provenance too
(`verdicts.SOURCE_DECISIONS_TRACK`), for the same reason.

## Three lanes, and what `unreadable` actually means

**Slice 6 got this wrong, and correcting it is the point of Slice 7.** It read
the manifest and never opened the directory the manifest lives in -- which
holds **204 `.md` files with real bodies** (median 3,073 bytes, largest
27,684). It concluded that a row without a verdict was "recorded but
unreadable", and put 36 rows in that lane. 35 of those 36 have a body sitting
beside the manifest, under a filename the reader never looked at.

Re-measured 2026-08-19 against the live city:

===========================================  =====
population                                      n
===========================================  =====
manifest rows                                  204
files in ``decisions-track/*.md``              204
rows whose slug resolves to a body file        203
rows with no body file                           1
Slice 6 ``unreadable`` rows that have a body    35
===========================================  =====

So the lanes are:

``adjudicated``
    a verdict can be read -- from the row's ``verdict`` key, or failing that
    from the body file's own frontmatter.

``pending``
    a body exists and no verdict does. That is an ordinary undecided brief and
    belongs in the queue a human works through. Slice 6 hid 35 of them.

``unreadable``
    **no body file exists.** The row proves a brief was tracked; nothing
    anywhere shows what it said. One live row (``he-rg5r-cascade-close``) is
    in this lane, and it is a hole in the corpus rather than in the reader.

Of the 158 rows this module emits, that is 125 adjudicated, 32 pending and 1
unreadable, against Slice 6's 122 / 0 / 36.

## Matching a row to its body, and the bug not to write a third time

Filenames are ``<NNN>-<slug>-brief.md``, so ``sigma18-done-vs-residual``
resolves to ``08-sigma18-done-vs-residual-brief.md``. Both affixes are
stripped **anchored** -- ``^\d+-`` and ``-brief$`` -- by the same
``normalize_stem`` the stack dedup already uses.

The anchoring is load-bearing, and this codebase has got it wrong twice.
``257-decision-brief-gate-profile-brief.md`` carries the slug
``decision-brief-gate-profile``; an unanchored ``.replace("-brief", "")``
yields ``decision-gate-profile``, matches no row, and drops that brief into
``unreadable`` without a word. The tests pin that exact filename.

## What a record carries, and what stays absent

A record now carries its body, the sections that body parses into, and the
fields its frontmatter declares -- ``unlock_count``, ``priority``, ``track``,
``form``, ``gates``, ``verdict`` -- each as a ``fields.FieldReading`` naming
the store it was read from. ``unlock_count`` is **read, never derived**: a
graph traversal returns ~0, because 508 of the 528 edges in the live HQ store
are ``related`` and one bead in 264 carries a blocking edge.

Where the row and its own file disagree, both readings are kept and the
reading is marked ``conflict``. Live: ``status`` disagrees 12 times, ``form``
3, ``unlock_count`` twice. Resolving those silently would destroy the only
copy of the fact that they disagree.

Everything genuinely missing stays missing. A row with no body reports
``body = None``, not ``""`` -- ``""`` reads as "this brief is empty" rather
than "this brief was never stored here" -- and a row with none of the five
date keys reports ``None`` rather than a synthesised timestamp. 60 rows would
otherwise render a fabricated Age.

## Deduplication

46 rows are already represented by a stack file, and emitting them again would
double-count a brief that has always been visible. They are matched by the
normalisation the measurement used -- stack filename stem, leading `NNN-`
prefix stripped, trailing `-brief` stripped -- and suppressed. The comparison
is against the stack directory rather than the stack index, because the index
is itself a cache that can be stale, and a stale index would resurrect a
duplicate.

The join to *beads* is deliberately not attempted here: `verdicts` measured it
at 0 of 126 rows by any principled key, and a join that yields nothing is a
per-call cost that buys nothing.

## Tolerant reads, and how that differs from the legacy gate

`redundant_state.legacy_manifest_state` reads this same file **strictly**: one
bad line and the whole file reports a parse error, because it feeds the B2.10
migration gate, which must fail closed before a mutation. This reader is the
opposite: a bad line costs that line and nothing else, because the point is to
make as many rows reachable as possible, and one malformed row must not hide
203 good ones. Every skipped line is reported as a diagnostic, so tolerant
never means silent.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from types import MappingProxyType
import json
import re
from typing import Iterable, Mapping

from . import fields as field_provenance
from .fields import FieldReading
from .verdicts import (
    CONFIDENCE_HIGH,
    SOURCE_BRIEF_FRONTMATTER,
    SOURCE_DECISIONS_TRACK,
    Verdict,
)


#: Which store a brief record came from. Reported on every record, from either
#: population -- see the module docstring.
SOURCE_BEAD = "bead"
SOURCE_MANIFEST = "manifest"
SOURCES = (SOURCE_BEAD, SOURCE_MANIFEST)

#: The `canonical_source` each population declares. The bead store is
#: canonical for briefs that have a bead; for a manifest-only row the manifest
#: is the only record there is, and saying `bead_store` would be false.
CANONICAL_SOURCE_BEAD = "bead_store"
CANONICAL_SOURCE_MANIFEST = "decisions_track_manifest"
CANONICAL_SOURCES = (CANONICAL_SOURCE_BEAD, CANONICAL_SOURCE_MANIFEST)

#: The lane a manifest row lands in. `adjudicated` and `pending` are the same
#: words the bead population uses and mean the same things -- a verdict can be
#: read, or the brief is still waiting for one.
STATE_ADJUDICATED = "adjudicated"
STATE_PENDING = "pending"
#: No body file exists anywhere for this row: the brief was tracked and what it
#: said is not recoverable. Slice 6 used this word for "the row has no verdict",
#: which was wrong for 35 of the 36 rows it applied to.
STATE_UNREADABLE = "unreadable"

#: Registered in assets/mctl/diagnostics.toml.
CODE_MANIFEST_UNREADABLE = "MBRF060"
CODE_MANIFEST_ROW_MALFORMED = "MBRF061"
CODE_MANIFEST_ROW_NO_SLUG = "MBRF062"
CODE_ROW_HAS_NO_BODY = "MBRF063"
CODE_BODY_UNREADABLE = "MBRF064"
CODE_BODY_NO_FRONTMATTER = "MBRF065"
CODE_BODY_AMBIGUOUS = "MBRF066"

#: The field a manifest verdict is read from, reported verbatim on the
#: `Verdict` so a reader can see it was not read off a bead.
VERDICT_FIELD = "decisions-track/manifest.jsonl:verdict"
#: Where a verdict read out of the body file's own frontmatter came from.
FRONTMATTER_VERDICT_FIELD = "frontmatter.verdict"

#: How a row key names itself in a `FieldValue`. Which keys are read is not
#: enumerated: **every** key the row holds is exposed, and so is every key the
#: body file's frontmatter holds. Both are kept, and a disagreement is
#: reported rather than resolved -- see `fields`.
ROW_FIELD_PREFIX = "decisions-track/manifest.jsonl:"

#: Timestamp keys, in the order a row's own history would have written them.
#: `adjudicated_at` covers 97 of the 98 timestamped rows; `rescinded_at`
#: covers the other 1. The rest are declared because the corpus uses them on
#: rows that a stack file currently represents, and dedup is not permanent.
#:
#: Nothing outside this tuple is read, and nothing is derived: a row with none
#: of these keys reports `None`, never the file mtime, never today.
TIMESTAMP_KEYS = (
    "adjudicated_at",
    "rescinded_at",
    "deferred_at",
    "briefed_at",
    "on_hold_since",
)

#: Keys a row offers as its identity, in preference order. `slug` is the only
#: one the live corpus uses on all 204 rows; the others are read because the
#: stack index and the pile write those spellings, and a row copied between
#: them should not become unidentifiable.
SLUG_KEYS = ("slug", "brief_id", "id")

#: `NNN-` ordering prefix and `-brief` suffix, as the stack writes them.
_ORDER_PREFIX = re.compile(r"^\d+-")
_BRIEF_SUFFIX = re.compile(r"-brief$")


#: Shared immutable default for a record with no frontmatter. A mutable `{}`
#: default on a frozen dataclass would be one dict shared by every record that
#: then looked writable.
_EMPTY_FRONTMATTER: Mapping[str, str] = MappingProxyType({})


@dataclass(frozen=True)
class ManifestIssue:
    """One row (or one file) this reader could not use, and why.

    Carried out of the module rather than rendered here: `briefs.py` owns the
    `Diagnostic` shape, including the trace id and the city/rig facts, and a
    second diagnostic builder would be a second contract.
    """

    code: str
    message: str
    line: int | None = None
    detail: str | None = None
    #: The file the issue is about, when that is not the manifest itself.
    #: `documents.py` reads stack files through this same shape, and an issue
    #: about `briefs/stack/x-brief.md` reported at the manifest's path would
    #: send an operator to the wrong file.
    location: str | None = None


@dataclass(frozen=True)
class ManifestRecord:
    """One decisions-track row, typed, with nothing added to it.

    Field order follows what a reader needs first: `slug` is the only identity
    the row has, `source` says what is (and is not) behind it, and the rest is
    what the row actually stored.
    """

    slug: str
    status: str | None
    verdict: Verdict | None
    track: str | None
    #: The row's own timestamp, or None. Never synthesised -- 60 live rows
    #: legitimately have none, and a fabricated date renders as a real Age.
    timestamp: str | None
    #: Which key `timestamp` came from, so a date is never ambiguous. None
    #: exactly when `timestamp` is None.
    timestamp_field: str | None
    #: 1-based line in the manifest. The row has no id; this is how an
    #: operator finds it again in a 204-line file of similar-looking JSON.
    line: int
    source: str = SOURCE_MANIFEST
    #: The `decisions-track/*.md` file this row's slug resolves to, or None
    #: when there is none. None is what `unreadable` means, and the only thing
    #: it means.
    body_path: Path | None = None
    #: That file's text, verbatim. None exactly when `body_path` is None, or
    #: when the file existed and could not be read -- `""` would say the brief
    #: is empty rather than that it was never stored.
    body: str | None = None
    #: The body file's frontmatter block, as written. Empty when the file has
    #: none; `MBRF065` says which of the two happened.
    frontmatter: Mapping[str, str] = _EMPTY_FRONTMATTER
    #: Every field the row and its file declare, each naming where it was read
    #: and flagging where the two disagree.
    fields: tuple[FieldReading, ...] = ()

    @property
    def decision_state(self) -> str:
        """Which lane this row is in -- see the module docstring.

        `unreadable` is about the *body*, not the verdict. A row with a body
        and no verdict is an ordinary undecided brief and goes in `pending`,
        which is where a human will find it.
        """
        if self.body_path is None:
            return STATE_UNREADABLE
        return STATE_ADJUDICATED if self.verdict is not None else STATE_PENDING

    def to_dict(self) -> dict[str, object]:
        return {
            "body_path": str(self.body_path) if self.body_path is not None else None,
            "decision_state": self.decision_state,
            "fields": field_provenance.readings_map(self.fields),
            "line": self.line,
            "slug": self.slug,
            "source": self.source,
            "status": self.status,
            "timestamp": self.timestamp,
            "timestamp_field": self.timestamp_field,
            "track": self.track,
            "verdict": self.verdict.to_dict() if self.verdict is not None else None,
        }


@dataclass(frozen=True)
class ManifestReading:
    """Every manifest-only record, plus what was skipped getting there."""

    path: Path
    records: tuple[ManifestRecord, ...]
    #: Slugs suppressed because a stack file already represents them. Kept so
    #: `197 + 158 = 355` can be checked against `46 suppressed of 204 rows`
    #: rather than asserted.
    represented: tuple[str, ...]
    rows_read: int
    issues: tuple[ManifestIssue, ...] = ()

    @property
    def state_counts(self) -> dict[str, int]:
        counts = {STATE_ADJUDICATED: 0, STATE_PENDING: 0, STATE_UNREADABLE: 0}
        for record in self.records:
            counts[record.decision_state] += 1
        return counts


def normalize_stem(stem: str) -> str:
    """A stack filename stem reduced to the slug a manifest row would carry.

    `240-dolt-quarantine-retain-verdict-blocks-222-step2-brief` ->
    `dolt-quarantine-retain-verdict-blocks-222-step2`. Only the leading
    ordering prefix is stripped: the trailing `-222-step2` is part of the
    slug, and a greedier rule would collide unrelated briefs.
    """
    return _BRIEF_SUFFIX.sub("", _ORDER_PREFIX.sub("", stem))


def represented_slugs(stack_dir: Path) -> frozenset[str]:
    """Slugs a stack file already presents, normalised for comparison.

    Only `*.md` counts. The stack also holds `.index.jsonl`, its `.bak-*`
    snapshots, and `*.md.bak*` copies; treating a backup as a representation
    would silence a row because somebody once saved a file.
    """
    try:
        entries = tuple(stack_dir.glob("*.md"))
    except OSError:
        return frozenset()
    return frozenset(normalize_stem(path.stem) for path in entries)


def body_index(directory: Path) -> tuple[dict[str, Path], tuple[ManifestIssue, ...]]:
    """Every `*.md` in `directory`, keyed by the slug a manifest row carries.

    Same `normalize_stem` the stack dedup uses, and for the same reason: one
    normalisation rule, anchored at both ends, or the two readers drift and a
    brief becomes visible to one and invisible to the other.

    Two files that normalise to one slug is ambiguity, not a choice to make
    quietly: the sorted-first file is used and `MBRF066` names both. The live
    corpus has no such collision, which is exactly why an unreported one would
    go unnoticed.
    """
    try:
        entries = sorted(directory.glob("*.md"))
    except OSError:
        return {}, ()
    index: dict[str, Path] = {}
    collisions: dict[str, list[Path]] = {}
    for path in entries:
        slug = normalize_stem(path.stem)
        if slug in index:
            collisions.setdefault(slug, [index[slug]]).append(path)
            continue
        index[slug] = path
    issues = tuple(
        ManifestIssue(
            CODE_BODY_AMBIGUOUS,
            "More than one brief body file normalises to the same slug; the first was used.",
            detail=f"slug={slug} files=" + ", ".join(item.name for item in paths),
        )
        for slug, paths in sorted(collisions.items())
    )
    return index, issues


def read_body(path: Path) -> tuple[str | None, Mapping[str, str], tuple[ManifestIssue, ...]]:
    """One brief body file: its text, its frontmatter, and what went wrong.

    A file that cannot be decoded reports `None`, never `""`. The distinction
    is the whole point of this slice: `""` says the brief is empty, `None` says
    nothing readable is stored, and Slice 6 conflated exactly those two.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return (
            None,
            _EMPTY_FRONTMATTER,
            (
                ManifestIssue(
                    CODE_BODY_UNREADABLE,
                    "Brief body file could not be read, so the row keeps only what its row says.",
                    detail=f"{path.name}: {error}",
                ),
            ),
        )
    frontmatter = field_provenance.read_frontmatter(text)
    if frontmatter:
        return text, frontmatter, ()
    return (
        text,
        _EMPTY_FRONTMATTER,
        (
            ManifestIssue(
                CODE_BODY_NO_FRONTMATTER,
                "Brief body file has no parseable frontmatter, so its recorded fields are unavailable.",
                detail=path.name,
            ),
        ),
    )


def read_manifest(
    path: Path, *, represented: Iterable[str] = (), bodies: Path | None = None
) -> ManifestReading:
    """Read the manifest at `path`, minus rows `represented` already covers.

    Never raises. A missing manifest is the normal case for most rigs -- only
    the HQ store has one -- and an unreadable one must not take down a brief
    listing, so both report an issue and return no records.
    """
    path = Path(path)
    covered = frozenset(represented)
    if not path.is_file():
        return ManifestReading(path, (), (), 0)

    body_dir = path.parent if bodies is None else Path(bodies)
    index, issues_from_index = body_index(body_dir)

    records: list[ManifestRecord] = []
    suppressed: list[str] = []
    issues: list[ManifestIssue] = list(issues_from_index)
    rows_read = 0
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        return ManifestReading(
            path,
            (),
            (),
            0,
            (
                ManifestIssue(
                    CODE_MANIFEST_UNREADABLE,
                    "Decisions-track manifest could not be read, so its rows are unreachable.",
                    detail=str(error),
                ),
            ),
        )

    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as error:
            issues.append(
                ManifestIssue(
                    CODE_MANIFEST_ROW_MALFORMED,
                    "Decisions-track manifest row is not readable JSON and was skipped.",
                    line=line_number,
                    detail=error.msg,
                )
            )
            continue
        if not isinstance(parsed, Mapping):
            issues.append(
                ManifestIssue(
                    CODE_MANIFEST_ROW_MALFORMED,
                    "Decisions-track manifest row is not a JSON object and was skipped.",
                    line=line_number,
                    detail=f"row is a JSON {type(parsed).__name__}",
                )
            )
            continue
        rows_read += 1
        slug = _slug(parsed)
        if slug is None:
            # The slug is the row's whole identity. Without one the row cannot
            # be deduplicated, addressed, or shown -- so it is reported by
            # line number instead of emitted under an invented id.
            issues.append(
                ManifestIssue(
                    CODE_MANIFEST_ROW_NO_SLUG,
                    "Decisions-track manifest row carries no slug, so it has no identity to show.",
                    line=line_number,
                )
            )
            continue
        if slug in covered:
            suppressed.append(slug)
            continue
        record, row_issues = _record(parsed, slug, line_number, index.get(slug))
        issues.extend(row_issues)
        records.append(record)
    return ManifestReading(path, tuple(records), tuple(suppressed), rows_read, tuple(issues))


def manifest_records(manifest_path: Path, stack_dir: Path) -> ManifestReading:
    """The manifest-only records for one rig: read, joined to bodies, deduped.

    Bodies come from the manifest's own directory, because that is where they
    are: 204 `.md` files sit beside `manifest.jsonl`, and Slice 6 read the one
    without ever listing the other.

    **This is half of an answer, and must not be used to build a roster on its
    own.** It drops every row a stack file's slug matches -- 46 live -- on the
    assumption that the caller emits the stack side. Slices 6 and 7 made that
    assumption and no reader kept it, so the 46 reached nothing at all. The
    roster reads `documents.read_documents`, which merges the two instead and
    can prove nothing was subtracted. What remains here is the manifest half,
    for callers that want exactly that and know what it excludes.
    """
    return read_manifest(manifest_path, represented=represented_slugs(stack_dir))


def _record(
    row: Mapping[str, object], slug: str, line: int, body_path: Path | None
) -> tuple[ManifestRecord, tuple[ManifestIssue, ...]]:
    timestamp, timestamp_field = _timestamp(row)
    if body_path is None:
        body: str | None = None
        frontmatter: Mapping[str, str] = _EMPTY_FRONTMATTER
        issues: tuple[ManifestIssue, ...] = (
            ManifestIssue(
                CODE_ROW_HAS_NO_BODY,
                "Decisions-track row has no brief body file, so what it said cannot be shown.",
                line=line,
                detail=f"slug={slug}",
            ),
        )
    else:
        body, frontmatter, issues = read_body(body_path)
        issues = tuple(replace(issue, line=line) for issue in issues)
    record = ManifestRecord(
        slug=slug,
        status=_text(row.get("status")),
        verdict=_verdict(row, frontmatter),
        track=_text(row.get("track")) or _text(frontmatter.get("track")),
        timestamp=timestamp,
        timestamp_field=timestamp_field,
        line=line,
        body_path=body_path,
        body=body,
        frontmatter=frontmatter,
        fields=_fields(row, frontmatter),
    )
    return record, issues


def _fields(
    row: Mapping[str, object], frontmatter: Mapping[str, str]
) -> tuple[FieldReading, ...]:
    """Every field either store holds, read from the row first and the file second.

    Row first because the manifest is this record's `canonical_source`; the
    file is the same brief's other account of itself. Both are kept, and a
    disagreement is reported rather than resolved -- 17 live rows disagree
    with their own body file, and that is a finding about the corpus.

    The set of fields is **not enumerated**. An earlier reading took six named
    keys off the row and six off the file, which meant a brief declaring
    anything else declared it to nobody. Whatever a row or a header holds is
    what comes back.
    """
    return field_provenance.readings(
        field_provenance.row_store(row, prefix=ROW_FIELD_PREFIX),
        field_provenance.frontmatter_store(frontmatter),
    )


def _verdict(row: Mapping[str, object], frontmatter: Mapping[str, str]) -> Verdict | None:
    """The row's typed verdict, with its provenance, or None.

    Confidence is `high` -- the same grade `verdicts` gives a typed field on a
    bead -- and for the same reason: the value was written into a field meant
    to hold a verdict, and nothing had to be parsed or inferred to find it.

    That is a narrower claim than it looks. It says the row's verdict field
    says this. It does not say a bead, a file, or a human attests it; `source`
    on the record is what says that, and it says `manifest`. The `low`
    confidence `verdicts.read_verdict_reading` gives a decisions-track verdict
    is about a different act -- carrying a manifest verdict *across a join*
    onto a bead, which can pick the wrong row. There is no join here.
    """
    value = row.get("verdict")
    if isinstance(value, str) and value.strip():
        return Verdict(value.strip(), SOURCE_DECISIONS_TRACK, CONFIDENCE_HIGH, VERDICT_FIELD)
    # Failing the row, the brief's own file. 21 decisions-track files record a
    # frontmatter verdict, and 3 of them sit on rows whose `verdict` key is
    # absent -- Slice 6 could not see those at all. The source says which
    # document attested it, so the two are never conflated.
    from_file = field_provenance.frontmatter_value(frontmatter, "verdict")
    if from_file is None:
        return None
    return Verdict(
        from_file.value, SOURCE_BRIEF_FRONTMATTER, CONFIDENCE_HIGH, FRONTMATTER_VERDICT_FIELD
    )


def first_timestamp(
    row: Mapping[str, object], keys: Iterable[str] = TIMESTAMP_KEYS
) -> tuple[str | None, str | None]:
    """The first date `row` actually carries, and which key it came from.

    `keys` is a parameter because a stack file's frontmatter spells its dates
    differently from a manifest row (`deposited_at` on 43 live files, against
    the row's `briefed_at`), and the rule -- take the first key present,
    verbatim, or report None -- is the same one either way. Nothing is
    derived: no mtime, no today.
    """
    for key in keys:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip(), key
    return None, None


def _timestamp(row: Mapping[str, object]) -> tuple[str | None, str | None]:
    return first_timestamp(row, TIMESTAMP_KEYS)


def _slug(row: Mapping[str, object]) -> str | None:
    for key in SLUG_KEYS:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def _text(value: object) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None
