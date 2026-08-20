r"""The two *document* brief populations -- stack files and decisions-track
rows -- read together, and joined so the join never subtracts.

Slice 6 made the decisions-track manifest readable and Slice 7 attached its
bodies. Both suppressed a manifest row whenever a file in
`.beads/briefs/stack/` normalised to the same slug, on the stated ground that
"a stack file already represents them". Measured on the live city 2026-08-19,
nothing read stack files as records:

=========================================  =====  =============================
population                                    n   reachable before this slice
=========================================  =====  =============================
manifest rows                                204   158 (46 suppressed)
… suppressed rows appearing in the roster      0   **none of the 46**
stack files                                   89   2, and only as a bead's body
… stack files reaching no surface             87   --
=========================================  =====  =============================

So the dedup was a **net loss**: it removed 46 rows in favour of documents no
reader opened. `gh-38-decisions-track-classifier-verify-close-brief.md` --
deposited 2026-08-19, awaiting a verdict, `status: present-it-pending` -- was
invisible to `briefs list --all-rigs` for exactly this reason, and it has no
manifest row at all, so it was never even a dedup casualty. It was simply
never read.

## The invariant

**No input document is suppressed without an emitted record that represents
it.** Stated arithmetically, and asserted by the tests:

    len(records) + len(duplicates) + len(unusable) == documents_read

`duplicates` is not a count of things thrown away: every entry names the
`brief_id` of the record that now carries that document, and every emitted
record names in `also_recorded_in` the documents folded into it. `unusable`
is the third lane and it is deliberately separate -- a manifest row with no
slug has no identity to merge on, so it is neither emitted nor represented,
and it must be counted where that is visible rather than absorbed into the
duplicate total. Live, `unusable` is 0.

## Authority: the stack file leads, and the row is kept beside it

Where a manifest row and a stack file describe one brief (46 live pairs), the
record's `canonical_source` is the **stack file**, and the field order is

    stack frontmatter  ->  manifest row  ->  decisions-track body frontmatter

Why that order, and not the reverse:

* The stack file *is* the brief. The manifest row is an index entry **about**
  the brief, and the decisions-track `.md` is a snapshot copy taken when the
  row was written -- 40 of the 46 are byte-identical to the stack file and
  the 6 that differ are all older than it.
* The suppression this module replaces already asserted the stack file was
  the better representation. Keeping that judgement and emitting the record
  is the whole correction; reversing it would be a second, unargued change.
* A stack file is the only one of the three a human is currently working
  through. Rendering a live `present-it-pending` brief under a tracking
  row's `briefed` would describe the pipeline rather than the decision.

Nothing is resolved away. Every field a second store holds stays in
`FieldReading.readings` with `conflict` set -- the mechanism Slice 7 already
uses for row-vs-body disagreement, extended to a third reading rather than
duplicated. Live, the row and the stack file disagree on `status` 28 times,
`form` 4 times and `gates` once; those 33 facts exist nowhere else.

Which fields those are is not enumerated. Every key a stack file's header
holds and every key a row holds is exposed, so `status` -- which disagrees 28
times and which an enumerated reader did not carry at all -- arrives with no
special case, and so does anything a producer invents tomorrow.

## What a stack record is not allowed to invent

Every frontmatter key is **read or absent**; none is computed. A timestamp
comes from one of the
keys in `STACK_TIMESTAMP_KEYS` or is `None`; 43 live files carry
`deposited_at`, 21 carry `adjudicated_at`, and a file with neither reports no
date rather than its mtime. A file that cannot be decoded reports
`body = None`, never `""`.

## Reuse, not reimplementation

There is no parser and no normaliser here. `manifest.body_index` supplies the
slug index (and the `MBRF066` ambiguity report) for the stack directory
exactly as it does for the decisions-track directory; `manifest.read_body`
reads a file's text and frontmatter; `manifest.normalize_stem` is the single
anchored `^\d+-` / `-brief$` rule both sides join on; `fields` builds every
reading; `verdicts` types the verdict. This module is the join and nothing
else.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping

from . import fields as field_provenance
from .fields import FieldReading
from .manifest import (
    CANONICAL_SOURCE_MANIFEST,
    CODE_MANIFEST_ROW_NO_SLUG,
    SOURCE_MANIFEST,
    STATE_ADJUDICATED,
    STATE_PENDING,
    STATE_UNREADABLE,
    ManifestIssue,
    ManifestRecord,
    body_index,
    first_timestamp,
    normalize_stem,
    read_body,
    read_manifest,
)
from .verdicts import CONFIDENCE_HIGH, SOURCE_BRIEF_FRONTMATTER, Verdict


#: A record read from a file in `.beads/briefs/stack/`. Joins the existing
#: `bead` / `manifest` vocabulary; a surface that cannot tell the three apart
#: would assert that a deposited markdown file is an attested decision bead.
SOURCE_STACK_FILE = "stack_file"

#: The `canonical_source` a stack-sourced record declares. Not `bead_store`
#: (there is no bead) and not `decisions_track_manifest` (the row, where one
#: exists, is an index entry about this file rather than the file itself).
CANONICAL_SOURCE_STACK_FILE = "brief_stack_file"

#: Registered in assets/mctl/diagnostics.toml. `MBRF060`-`MBRF066` already
#: cover the manifest side and the per-file body read, and are reused verbatim
#: -- a second code for "this file has no frontmatter" would be a second
#: contract for one fact.
CODE_STACK_DIR_UNREADABLE = "MBRF067"
CODE_STORED_BODIES_DIFFER = "MBRF068"

#: Date keys a stack file may carry, in the order its own history writes them:
#: the last thing that happened to the brief is the date to show. Measured
#: across the 89 live files -- `deposited_at` 43, `adjudicated_at` 21,
#: `approved_at` 3, `deferred_at` 1, and the rest one apiece. Nothing outside
#: this tuple is read and nothing is derived; a file with none of them reports
#: `None`, never its mtime.
STACK_TIMESTAMP_KEYS = (
    "adjudicated_at",
    "rescinded_at",
    "deferred_at",
    "approved_at",
    "revised_at",
    "researched_at",
    "deposited_at",
    "drafted_at",
)

#: How a stack file's frontmatter reading names itself, so a merged record's
#: two frontmatter readings are distinguishable. The decisions-track body keeps
#: the bare `frontmatter.<name>` spelling `manifest.py` already emits. Applied
#: to whatever keys the file holds -- there is no key list.
STACK_FIELD_PREFIX = "briefs/stack:"

_EMPTY_FRONTMATTER: Mapping[str, str] = MappingProxyType({})


@dataclass(frozen=True)
class StackRecord:
    """One `.beads/briefs/stack/*.md`, typed, with nothing added to it."""

    slug: str
    path: Path
    #: The file's text, verbatim. `None` exactly when the file could not be
    #: decoded -- `""` would say the brief is empty rather than unreadable.
    body: str | None
    frontmatter: Mapping[str, str]
    status: str | None
    verdict: Verdict | None
    track: str | None
    timestamp: str | None
    timestamp_field: str | None
    fields: tuple[FieldReading, ...]

    @property
    def decision_state(self) -> str:
        """`unreadable` is about the body, exactly as it is for a row.

        A stack file always has a path, so the lane turns on whether its text
        could be read at all -- which is the same question `manifest.py` asks
        of a row, asked of the one document a stack record has.
        """
        if self.body is None:
            return STATE_UNREADABLE
        return STATE_ADJUDICATED if self.verdict is not None else STATE_PENDING


@dataclass(frozen=True)
class Duplicate:
    """One input document folded into an emitted record, and which one.

    Never a bare count. `represented_by` is the `brief_id` a caller can look
    up to find the document again, which is what makes suppression auditable
    rather than a claim.
    """

    #: `manifest_row` or `stack_file`.
    kind: str
    #: Where the document is: a path, or `<manifest>:<line>` for a row.
    location: str
    #: The `brief_id` of the record that now carries it.
    represented_by: str


@dataclass(frozen=True)
class Unusable:
    """One input document that could be neither emitted nor represented.

    Its own diagnostic says why (a row with no slug, `MBRF062`). Counted in
    its own lane so the invariant arithmetic stays exact instead of quietly
    absorbing it into `duplicates`, which would claim something represents it.
    """

    kind: str
    location: str
    code: str


@dataclass(frozen=True)
class BriefDocument:
    """One emitted brief, and every input document folded into it.

    Exactly one of the two lanes is always present. Both present is a merged
    pair; the stack side leads, for the reasons in the module docstring.
    """

    stack: StackRecord | None
    row: ManifestRecord | None
    #: The decisions-track body file behind `row`, when this is a merged pair
    #: and that body is not the one being shown. Named so the document is
    #: reachable even though its text is not repeated in the payload.
    row_body_path: Path | None = None
    #: Where `row` is: `<manifest path>:<line>`. Carried rather than derived,
    #: because `ManifestRecord` holds its line number and not the file it came
    #: from, and a record that named the wrong manifest would be worse than
    #: one that named none.
    row_location: str | None = None

    def __post_init__(self) -> None:
        if self.stack is None and self.row is None:
            raise ValueError("a BriefDocument must carry a stack file, a row, or both")

    @property
    def brief_id(self) -> str:
        return self.stack.slug if self.stack is not None else self.row.slug  # type: ignore[union-attr]

    @property
    def source(self) -> str:
        return SOURCE_STACK_FILE if self.stack is not None else SOURCE_MANIFEST

    @property
    def canonical_source(self) -> str:
        return (
            CANONICAL_SOURCE_STACK_FILE
            if self.stack is not None
            else CANONICAL_SOURCE_MANIFEST
        )

    @property
    def merged(self) -> bool:
        return self.stack is not None and self.row is not None

    @property
    def body(self) -> str | None:
        return self.stack.body if self.stack is not None else self.row.body  # type: ignore[union-attr]

    @property
    def body_path(self) -> Path | None:
        return self.stack.path if self.stack is not None else self.row.body_path  # type: ignore[union-attr]

    @property
    def status(self) -> str | None:
        if self.stack is not None and self.stack.status:
            return self.stack.status
        return self.row.status if self.row is not None else None

    @property
    def verdict(self) -> Verdict | None:
        """The first verdict any of this brief's documents records.

        Order follows authority, and each `Verdict` carries the document it
        was read from, so a stack verdict and a row verdict are never
        conflated. Live, the two never both exist: 4 pairs have a row verdict
        only and 1 has a file verdict only, so this resolution changes no
        answer today -- it fixes the *order* for the day it does.
        """
        if self.stack is not None and self.stack.verdict is not None:
            return self.stack.verdict
        return self.row.verdict if self.row is not None else None

    @property
    def track(self) -> str | None:
        if self.stack is not None and self.stack.track:
            return self.stack.track
        return self.row.track if self.row is not None else None

    @property
    def timestamp(self) -> str | None:
        if self.stack is not None and self.stack.timestamp:
            return self.stack.timestamp
        return self.row.timestamp if self.row is not None else None

    @property
    def timestamp_field(self) -> str | None:
        if self.stack is not None and self.stack.timestamp:
            return self.stack.timestamp_field
        return self.row.timestamp_field if self.row is not None else None

    @property
    def decision_state(self) -> str:
        """A merged record is adjudicated when *either* document says so.

        `unreadable` still means no readable body anywhere: on a merged pair
        the stack file is shown, and a row whose own body is missing is not
        unreadable while that file is there.
        """
        if self.body is None:
            return STATE_UNREADABLE
        return STATE_ADJUDICATED if self.verdict is not None else STATE_PENDING

    @property
    def fields(self) -> tuple[FieldReading, ...]:
        """Every store's reading of every field, in authority order.

        The two sides' `FieldReading`s are concatenated rather than resolved:
        `fields.reading` already orders candidates by authority and
        `FieldReading.conflict` already reports disagreement, so a merged
        record is the stack readings followed by the row's -- which is exactly
        `[stack frontmatter, manifest row, decisions-track frontmatter]`.
        """
        if self.stack is None:
            return self.row.fields  # type: ignore[union-attr]
        if self.row is None:
            return self.stack.fields
        by_name: dict[str, list[field_provenance.FieldValue]] = {
            item.name: list(item.readings) for item in self.stack.fields
        }
        for item in self.row.fields:
            by_name.setdefault(item.name, []).extend(item.readings)
        return tuple(
            FieldReading(name, tuple(values)) for name, values in sorted(by_name.items())
        )

    @property
    def also_recorded_in(self) -> tuple[str, ...]:
        """Every other document describing this brief, by location.

        The record `body` comes from one document; this names the rest, so a
        merged pair's other two locations stay reachable rather than being
        implied by their absence.
        """
        if not self.merged:
            return ()
        locations = [self.row_location or f"decisions-track row {self.row.line}"]  # type: ignore[union-attr]
        if self.row_body_path is not None:
            locations.append(str(self.row_body_path))
        return tuple(locations)


@dataclass(frozen=True)
class DocumentReading:
    """Both document populations, joined, with the arithmetic to check it."""

    records: tuple[BriefDocument, ...]
    duplicates: tuple[Duplicate, ...]
    unusable: tuple[Unusable, ...]
    #: Every input document opened: manifest rows plus stack `*.md` files.
    documents_read: int
    issues: tuple[ManifestIssue, ...] = ()

    @property
    def balanced(self) -> bool:
        """The no-subtraction invariant, as a value rather than a promise."""
        return (
            len(self.records) + len(self.duplicates) + len(self.unusable)
            == self.documents_read
        )

    @property
    def state_counts(self) -> dict[str, int]:
        counts = {STATE_ADJUDICATED: 0, STATE_PENDING: 0, STATE_UNREADABLE: 0}
        for record in self.records:
            counts[record.decision_state] += 1
        return counts


def read_stack(
    stack_dir: Path, *, claimed: Mapping[Path, str] | None = None
) -> tuple[tuple[StackRecord, ...], tuple[Duplicate, ...], int, tuple[ManifestIssue, ...]]:
    """Every `*.md` in the stack directory, as records.

    `claimed` maps a path already carried by some other record -- in practice
    a bead whose cached document is that file -- to that record's `brief_id`.
    Those files are reported as duplicates rather than emitted twice; two live
    files are in this lane, both `<bead-id>-…-brief.md`.

    Never raises. A stack directory that cannot be listed costs the stack
    population and nothing else: 197 bead-backed briefs and 204 manifest rows
    must still list.
    """
    stack_dir = Path(stack_dir)
    claimed = {} if claimed is None else claimed
    if not stack_dir.is_dir():
        return (), (), 0, ()
    try:
        entries = sorted(stack_dir.glob("*.md"))
    except OSError as error:
        return (
            (),
            (),
            0,
            (
                ManifestIssue(
                    CODE_STACK_DIR_UNREADABLE,
                    "Brief stack directory could not be listed, so its files are unreachable.",
                    detail=str(error),
                    location=str(stack_dir),
                ),
            ),
        )
    # `body_index` is the same slug index the decisions-track join uses, and it
    # is what reports MBRF066 when two files normalise to one slug. A second
    # index here would be a second normalisation rule.
    index, ambiguity = body_index(stack_dir)
    issues = tuple(
        ManifestIssue(item.code, item.message, detail=item.detail, location=str(stack_dir))
        for item in ambiguity
    )
    records: list[StackRecord] = []
    duplicates: list[Duplicate] = []
    all_issues = list(issues)
    for slug, path in sorted(index.items()):
        if path in claimed:
            duplicates.append(
                Duplicate(SOURCE_STACK_FILE, str(path), claimed[path])
            )
            continue
        record, row_issues = _stack_record(slug, path)
        all_issues.extend(row_issues)
        records.append(record)
    # Files `body_index` collapsed into an ambiguity are still input documents.
    # They are reported by MBRF066 and represented by the file that won the
    # slug, so they belong in `duplicates` and not in the emitted count.
    for path in entries:
        slug = normalize_stem(path.stem)
        if index.get(slug) == path or path in claimed:
            continue
        duplicates.append(Duplicate(SOURCE_STACK_FILE, str(path), slug))
    return tuple(records), tuple(duplicates), len(entries), tuple(all_issues)


def read_documents(
    manifest_path: Path, stack_dir: Path, *, claimed: Mapping[Path, str] | None = None
) -> DocumentReading:
    """Both document populations for one rig, joined so nothing is subtracted.

    The manifest is read with **no** suppression -- `read_manifest`'s
    `represented` argument is deliberately not used here, because suppression
    was the defect. Rows whose slug matches a stack file are merged into that
    file's record instead, and reported as duplicates naming it.
    """
    stack_records, duplicates, files_read, stack_issues = read_stack(
        stack_dir, claimed=claimed
    )
    reading = read_manifest(manifest_path)
    by_slug = {record.slug: record for record in stack_records}

    documents: list[BriefDocument] = []
    merged_rows: dict[str, ManifestRecord] = {}
    duplicates = list(duplicates)
    issues = list(stack_issues) + list(reading.issues)
    for row in reading.records:
        if row.slug in by_slug:
            merged_rows[row.slug] = row
            duplicates.append(
                Duplicate(
                    SOURCE_MANIFEST,
                    f"{reading.path}:{row.line}",
                    row.slug,
                )
            )
            continue
        documents.append(BriefDocument(stack=None, row=row))
    for record in stack_records:
        row = merged_rows.get(record.slug)
        document = BriefDocument(
            stack=record,
            row=row,
            row_body_path=row.body_path if row is not None else None,
            row_location=f"{reading.path}:{row.line}" if row is not None else None,
        )
        if document.merged and _bodies_differ(document):
            issues.append(
                ManifestIssue(
                    CODE_STORED_BODIES_DIFFER,
                    "This brief is stored twice with different text; the stack file is shown "
                    "and the other copy is named in `also_recorded_in`.",
                    detail=f"slug={record.slug} other={row.body_path}",
                    location=str(record.path),
                )
            )
        documents.append(document)

    unusable = tuple(
        Unusable(SOURCE_MANIFEST, f"{reading.path}:{issue.line}", issue.code)
        for issue in reading.issues
        if issue.code == CODE_MANIFEST_ROW_NO_SLUG
    )
    return DocumentReading(
        records=tuple(sorted(documents, key=lambda item: item.brief_id)),
        duplicates=tuple(duplicates),
        unusable=unusable,
        documents_read=files_read + reading.rows_read,
        issues=tuple(issues),
    )


def _bodies_differ(document: BriefDocument) -> bool:
    """Whether a merged pair's two stored copies hold different text.

    40 of the 46 live pairs are byte-identical; the 6 that are not are a
    finding about the corpus, and showing one copy without saying the other
    exists and differs would silently pick a winner.
    """
    row = document.row
    if row is None or row.body is None or document.stack is None:
        return False
    return row.body != document.stack.body


def _stack_record(slug: str, path: Path) -> tuple[StackRecord, tuple[ManifestIssue, ...]]:
    body, frontmatter, issues = read_body(path)
    issues = tuple(
        ManifestIssue(
            issue.code, issue.message, detail=issue.detail or path.name, location=str(path)
        )
        for issue in issues
    )
    timestamp, timestamp_field = first_timestamp(frontmatter, STACK_TIMESTAMP_KEYS)
    return (
        StackRecord(
            slug=slug,
            path=path,
            body=body,
            frontmatter=frontmatter,
            status=_frontmatter_text(frontmatter, "status"),
            verdict=_stack_verdict(frontmatter),
            track=_frontmatter_text(frontmatter, "track"),
            timestamp=timestamp,
            timestamp_field=timestamp_field,
            fields=_stack_fields(frontmatter),
        ),
        issues,
    )


def _stack_fields(frontmatter: Mapping[str, str]) -> tuple[FieldReading, ...]:
    """Every key the file's header holds, whatever it is.

    Not an enumeration. The 89 live stack files carry ~100 distinct keys
    between them -- `shape`, `no_brainer_confidence`, `server_touching`,
    `review_gate`, `capability_blocker`, `deposited_by` -- and a reader that
    named six of them in advance made the rest undeclarable.
    """
    return field_provenance.readings(
        field_provenance.frontmatter_store(frontmatter, prefix=STACK_FIELD_PREFIX)
    )


def _stack_verdict(frontmatter: Mapping[str, str]) -> Verdict | None:
    """The file's own typed verdict, or None. 22 live files carry one.

    `high` confidence for the same reason `manifest.py` grades a row's
    `verdict` key high: the value was written into a field meant to hold a
    verdict and nothing had to be inferred. It says the *document* records
    this -- `source` on the record is what says no bead attests it.
    """
    value = field_provenance.frontmatter_value(
        frontmatter, "verdict", field=f"{STACK_FIELD_PREFIX}frontmatter.verdict"
    )
    if value is None:
        return None
    return Verdict(value.value, SOURCE_BRIEF_FRONTMATTER, CONFIDENCE_HIGH, value.field)


def _frontmatter_text(frontmatter: Mapping[str, str], name: str) -> str | None:
    value = field_provenance.frontmatter_value(frontmatter, name)
    return None if value is None else value.value
