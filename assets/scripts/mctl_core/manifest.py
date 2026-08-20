"""The decisions-track manifest, read as a third source of brief records.

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

## Two lanes, and why the second is not `pending`

A row with a typed verdict is `adjudicated`: the verdict text is right there.

A row without one is `unreadable` -- recorded but unreadable. The row proves a
brief existed and was tracked; it does not show what the brief said or what
was decided. Calling that `pending` would put 36 rows with no body, no bead
and no file into the queue a human works through, presenting an un-decidable
item as decidable. Calling it `adjudicated` would claim a verdict nobody can
read. It is its own lane because it is its own fact.

## What a record does not carry

No body, no sections, no options. There is no file and no bead behind these
rows, so there is nothing to parse; a `body: ""` would read as "this brief is
empty" rather than "this brief was never stored here". Absent stays absent --
which is also why a row with no timestamp reports `None` rather than a
synthesised one. 60 rows would otherwise render a fabricated Age.

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

from dataclasses import dataclass
from pathlib import Path
import json
import re
from typing import Iterable, Mapping

from .verdicts import CONFIDENCE_HIGH, SOURCE_DECISIONS_TRACK, Verdict


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

#: The lane a manifest row lands in. `adjudicated` is the same word the bead
#: population uses and means the same thing -- a verdict can be read.
STATE_ADJUDICATED = "adjudicated"
#: Recorded, but unreadable: the row exists, and what it said cannot be shown.
STATE_UNREADABLE = "unreadable"

#: Registered in assets/mctl/diagnostics.toml.
CODE_MANIFEST_UNREADABLE = "MBRF060"
CODE_MANIFEST_ROW_MALFORMED = "MBRF061"
CODE_MANIFEST_ROW_NO_SLUG = "MBRF062"

#: The field a manifest verdict is read from, reported verbatim on the
#: `Verdict` so a reader can see it was not read off a bead.
VERDICT_FIELD = "decisions-track/manifest.jsonl:verdict"

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

    @property
    def decision_state(self) -> str:
        return STATE_ADJUDICATED if self.verdict is not None else STATE_UNREADABLE

    def to_dict(self) -> dict[str, object]:
        return {
            "decision_state": self.decision_state,
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
        counts = {STATE_ADJUDICATED: 0, STATE_UNREADABLE: 0}
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


def read_manifest(
    path: Path, *, represented: Iterable[str] = ()
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

    records: list[ManifestRecord] = []
    suppressed: list[str] = []
    issues: list[ManifestIssue] = []
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
        records.append(_record(parsed, slug, line_number))
    return ManifestReading(path, tuple(records), tuple(suppressed), rows_read, tuple(issues))


def manifest_records(manifest_path: Path, stack_dir: Path) -> ManifestReading:
    """The manifest-only records for one rig: read, then deduplicated."""
    return read_manifest(manifest_path, represented=represented_slugs(stack_dir))


def _record(row: Mapping[str, object], slug: str, line: int) -> ManifestRecord:
    timestamp, timestamp_field = _timestamp(row)
    return ManifestRecord(
        slug=slug,
        status=_text(row.get("status")),
        verdict=_verdict(row),
        track=_text(row.get("track")),
        timestamp=timestamp,
        timestamp_field=timestamp_field,
        line=line,
    )


def _verdict(row: Mapping[str, object]) -> Verdict | None:
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
    if not isinstance(value, str) or not value.strip():
        return None
    return Verdict(value.strip(), SOURCE_DECISIONS_TRACK, CONFIDENCE_HIGH, VERDICT_FIELD)


def _timestamp(row: Mapping[str, object]) -> tuple[str | None, str | None]:
    for key in TIMESTAMP_KEYS:
        value = row.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip(), key
    return None, None


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
