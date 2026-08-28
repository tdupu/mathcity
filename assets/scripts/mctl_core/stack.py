r"""The brief stack, read as a source of brief records in its own right.

`manifest.py` opens this directory to join a decisions-track row to the file
that presents it. That join covers the stack files a row claims. It does not
cover the rest, and the rest is most of them:

===========================================================  =====
population (measured 2026-08-20)                                 n
===========================================================  =====
``.beads/briefs/stack/*.md``                                    89
… joined to a decisions-track row by `manifest.py`               46
… resolved by a bead record, via `_cached_brief_document`         2
… **claimed by nothing, read by nothing**                        41
===========================================================  =====

Those 41 are this module's population. They are not stale copies of anything:
no manifest row carries their slug, no bead id matches their filename, and
their frontmatter is where the pipeline records what it did -- `status` on all
43 of the unclaimed files, `priority` on 38, `unlock_count` on 35, `verdict`
on 21. A brief adjudicated in the stack and never written to the manifest was,
before this module, a decision the city had made and could not look up.

## Why this is a population and not a repair

The same argument `manifest.py` makes about minting beads applies here, and
harder. POLICY B2.1 makes a brief a decision bead with a source dependency;
only 3 of the 43 unclaimed stack files name a `source_bead` at all. Writing
them into the manifest, or into the bead store, would manufacture rows that
fail the policy on creation -- and it would be a *write*, against files this
whole read path exists to observe without touching. So they are read, and
nothing is written: not to the stack, not to the manifest, not to bd.

## What a record can and cannot claim

`source = "stack"` and `canonical_source = "brief_stack"`. That is a weaker
claim than either sibling population makes and it is stated rather than
implied: a stack file is a document the pipeline deposited, attested by no
bead and recorded in no manifest. Its `verdict`, where it has one, is read
from its own frontmatter and says so (`verdicts.SOURCE_BRIEF_FRONTMATTER`).

Identity is the filename, normalised by the same anchored `normalize_stem`
every other lane uses -- `240-dolt-quarantine-retain-verdict-blocks-222-step2-brief.md`
is the brief `dolt-quarantine-retain-verdict-blocks-222-step2`. There is no
other identity available: `brief_slug` appears in 3 of the 43 frontmatters and
`brief_bead` in 1, so a reader that required either would drop 40 briefs.

## Dedup is by resolved path, and by nothing else

A caller passes the stack files that are already accounted for --
`ManifestReading.stack_paths` for the joined ones, and the paths bead records
resolved to for the rest. Paths, not slugs: the bead lane addresses a file as
`<bead-id>-*.md` and the manifest lane addresses it by normalised stem, and a
dedup rule that guessed one of those spellings would either double-count a
brief or hide it. Comparing what each reader actually opened cannot drift.

## A live count is not a test

Every number above is a measurement, not an invariant. The stack drained from
89 files to 54 during the session that wrote this module, taking the joined
count from 46 to 38 and this population from 41 to 14. The counts are recorded
so the reasoning can be checked; the tests pin the *arithmetic* instead --
every stack file is reached by exactly one population, none by two and none by
none. See `test_stack_source.py`.

Timestamps are read, never synthesised, for the reason the sibling module
gives at length: a file mtime rendered as an Age is a date the brief never
recorded. Only `deposited_at`, `adjudicated_at`, `deferred_at` and `revised_at`
are read, and a file carrying none of them reports `None`.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping

from . import fields as field_provenance
from .fields import FieldReading
from .manifest import (
    LANE_STACK,
    STATE_ADJUDICATED,
    STATE_PENDING,
    STATE_UNREADABLE,
    ManifestIssue,
    normalize_stem,
    read_body,
    stack_index,
)
from .verdicts import CONFIDENCE_HIGH, SOURCE_BRIEF_FRONTMATTER, Verdict


#: Which store a stack-sourced record came from, and which store is
#: authoritative for it. `brief_stack` rather than `stack_file`: the record is
#: the brief the stack holds, and `stack_file` is already the name
#: `briefs.OPTION_SOURCE_STACK_FILE` uses for a parsed options block.
SOURCE_STACK = "stack"
CANONICAL_SOURCE_STACK = "brief_stack"

#: Registered in assets/mctl/diagnostics.toml.
CODE_STACK_UNREADABLE = "MBRF067"

#: Where a stack file's verdict was read from, reported verbatim so a reader
#: can see no bead and no manifest row attested it.
VERDICT_FIELD = "stack.frontmatter.verdict"

#: Frontmatter keys the exposed fields are read from, and the timestamp keys,
#: in the order the pipeline writes them. Nothing outside these is read and
#: nothing is derived -- a file with none of the four dates reports `None`,
#: never its mtime.
FRONTMATTER_FIELD_KEYS = field_provenance.EXPOSED_FIELDS
TIMESTAMP_KEYS = ("adjudicated_at", "deferred_at", "revised_at", "deposited_at")

_EMPTY_FRONTMATTER: Mapping[str, str] = MappingProxyType({})


@dataclass(frozen=True)
class StackRecord:
    """One stack file that no manifest row and no bead claims.

    Deliberately narrower than `ManifestRecord`: there is no row to read a
    status or a track off, so both come from the document or not at all.
    """

    slug: str
    path: Path
    #: The file's text, verbatim. `None` when the file could not be read --
    #: never `""`, which would say the brief is empty.
    body: str | None
    frontmatter: Mapping[str, str] = _EMPTY_FRONTMATTER
    verdict: Verdict | None = None
    status: str | None = None
    track: str | None = None
    #: The one date this file records, or None. Never the mtime.
    timestamp: str | None = None
    timestamp_field: str | None = None
    fields: tuple[FieldReading, ...] = ()
    source: str = SOURCE_STACK

    @property
    def documents(self) -> tuple[tuple[str, Path, str | None, Mapping[str, str]], ...]:
        """The one document this record is. Same shape as `ManifestRecord`'s."""
        return ((LANE_STACK, self.path, self.body, self.frontmatter),)

    @property
    def decision_state(self) -> str:
        """The same three lanes the manifest population uses.

        `unreadable` still means "no readable document": here that is a file
        that exists and could not be decoded, which `MBRF067` reports. It is
        not a statement about the verdict.
        """
        if self.body is None:
            return STATE_UNREADABLE
        return STATE_ADJUDICATED if self.verdict is not None else STATE_PENDING

    def to_dict(self) -> dict[str, object]:
        return {
            "body_path": str(self.path),
            "decision_state": self.decision_state,
            "fields": field_provenance.readings_map(self.fields),
            "slug": self.slug,
            "source": self.source,
            "status": self.status,
            "timestamp": self.timestamp,
            "timestamp_field": self.timestamp_field,
            "track": self.track,
            "verdict": self.verdict.to_dict() if self.verdict is not None else None,
        }


@dataclass(frozen=True)
class StackReading:
    """Every unclaimed stack record, plus what was skipped getting there."""

    path: Path
    records: tuple[StackRecord, ...]
    #: Files another reader already accounts for, named rather than merely
    #: subtracted, so `89 = 46 joined + 2 bead-resolved + 41 emitted` can be
    #: checked instead of asserted.
    claimed: tuple[Path, ...]
    files_read: int
    issues: tuple[ManifestIssue, ...] = ()

    @property
    def state_counts(self) -> dict[str, int]:
        counts = {STATE_ADJUDICATED: 0, STATE_PENDING: 0, STATE_UNREADABLE: 0}
        for record in self.records:
            counts[record.decision_state] += 1
        return counts


def stack_records(stack_dir: Path, *, claimed: Iterable[Path] = ()) -> StackReading:
    """Every stack `*.md` no other reader claims, as records.

    Never raises. A rig with no stack directory is the ordinary case and
    reports nothing, exactly as a rig with no manifest does.
    """
    stack_dir = Path(stack_dir)
    already = frozenset(Path(path) for path in claimed)
    index, issues = stack_index(stack_dir)
    records: list[StackRecord] = []
    skipped: list[Path] = []
    for slug in sorted(index):
        path = index[slug]
        if path in already:
            skipped.append(path)
            continue
        record, record_issues = _record(slug, path)
        issues = issues + record_issues
        records.append(record)
    return StackReading(
        stack_dir, tuple(records), tuple(skipped), len(index), tuple(issues)
    )


def _record(slug: str, path: Path) -> tuple[StackRecord, tuple[ManifestIssue, ...]]:
    body, frontmatter, issues = read_body(path)
    if body is None:
        issues = issues + (
            ManifestIssue(
                CODE_STACK_UNREADABLE,
                "Stack brief file could not be read, so the brief it holds cannot be shown.",
                detail=path.name,
            ),
        )
    timestamp, timestamp_field = _timestamp(frontmatter)
    return (
        StackRecord(
            slug=slug,
            path=path,
            body=body,
            frontmatter=frontmatter,
            verdict=_verdict(frontmatter),
            status=_text(frontmatter.get("status")),
            track=_text(frontmatter.get("track")),
            timestamp=timestamp,
            timestamp_field=timestamp_field,
            fields=_fields(frontmatter),
        ),
        issues,
    )


def _fields(frontmatter: Mapping[str, str]) -> tuple[FieldReading, ...]:
    """The exposed fields this file declares, under the stack lane's source.

    `stack_frontmatter`, not `frontmatter`: the same key read from the same
    kind of document in a different directory is a different claim, and a
    record that said `frontmatter` here would be indistinguishable from a
    manifest record's decisions-track reading.
    """
    readings = []
    for name in FRONTMATTER_FIELD_KEYS:
        reading = field_provenance.reading(
            name, field_provenance.stack_frontmatter_value(frontmatter, name)
        )
        if reading is not None:
            readings.append(reading)
    return tuple(readings)


def _verdict(frontmatter: Mapping[str, str]) -> Verdict | None:
    """The file's own verdict, or None.

    Confidence is `high` for the reason `manifest._verdict` gives: the value
    was written into a field meant to hold a verdict and nothing was inferred
    to find it. What that does *not* claim is that a bead or a manifest row
    agrees -- `source` on the record is what says that, and it says `stack`.
    """
    value = field_provenance.stack_frontmatter_value(frontmatter, "verdict")
    if value is None:
        return None
    return Verdict(value.value, SOURCE_BRIEF_FRONTMATTER, CONFIDENCE_HIGH, VERDICT_FIELD)


def _timestamp(frontmatter: Mapping[str, str]) -> tuple[str | None, str | None]:
    for key in TIMESTAMP_KEYS:
        value = _text(frontmatter.get(key))
        if value is not None:
            return value, key
    return None, None


def _text(value: object) -> str | None:
    if isinstance(value, str):
        text = value.strip()
        if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
            text = text[1:-1].strip()
        return text or None
    return None


__all__ = [
    "CANONICAL_SOURCE_STACK",
    "CODE_STACK_UNREADABLE",
    "SOURCE_STACK",
    "StackReading",
    "StackRecord",
    "normalize_stem",
    "stack_records",
]
