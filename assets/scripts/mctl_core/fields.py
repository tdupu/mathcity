"""Field-level provenance: which store each value on a brief record came from.

Slice 6 read the decisions-track manifest and reported five things off the
row. It did not open the 204 `.md` files sitting in the same directory, so it
never saw that those rows have bodies, and that the bodies carry frontmatter
holding the fields the surfaces most need -- `unlock_count`, `priority`,
`track`, `form`, `gates`, `verdict`.

Re-measured 2026-08-19 across the 293 live brief files:

======================  ==========  =================  ======
frontmatter key         stack (89)  decisions (204)     total
======================  ==========  =================  ======
``status``                      89                203     292
``artifact``                    85                203     288
``form``                        50                203     253
``track``                       49                203     252
``unlock_count``                60                132     192
``gates``                       34                140     174
``priority``                    47                 39      86
``verdict``                     22                 21      43
======================  ==========  =================  ======

(The dashboard brief reported `track` on all 293 and `gates` on 140. Neither
holds: 41 files carry no `track` key, and 140 is the decisions-track count
alone -- the stack contributes 34 more. Every other figure it quoted matches.)

## Why a value is not just a value

The consumer's requirement, verbatim: *"I want to render which is which
rather than flatten them."* A `priority` read off a bead column and a
`priority` read out of a markdown file are different kinds of claim -- one is
canonical state, the other is what somebody typed into a document at
production time -- and a surface that prints both as `P1` asserts they are
the same kind of fact.

So every value is a `FieldValue` carrying `source`, `confidence` and the exact
`field` it came from. That is deliberately the same four-field shape
`verdicts.Verdict` already uses, extended rather than reinvented: a client
that can render a verdict's provenance can render any field's.

## Disagreement is a finding, not a tie to break

Where two stores hold the same field and say different things, both readings
are kept and `conflict` is set. Picking a winner would destroy the one piece
of information nobody else has: that the bead and the document disagree.
Measured on the 157 decisions-track rows that have a body, the row and its own
file disagree on `status` 12 times, `form` 3 times and `unlock_count` twice.

Ordering is by authority, not by preference: `readings[0]` is the record's
`canonical_source` where that store holds the field, so `value` still answers
"what does this brief say" for a caller that does not care about provenance.

A brief can hold **three** accounts of itself, not two: the manifest row, the
markdown file beside the manifest, and the stack file the pipeline presents
from. Every row that has a stack file also has a decisions-track file -- all
46 of them when this was first measured on 2026-08-19 -- so the third column
is the common case for that population, not an edge one. `stack_frontmatter`
is its own source for exactly the reason above: 18 of those stack copies had
been rewritten from `form: compact` to `form: full` by the shape-repair pass
while the decisions-track copy still said `compact`, and reporting both under
one label would say a brief declared two forms without saying which document
declared which.

Comparison is on a folded key -- trimmed, case-folded, and for `priority` a
leading `P` dropped -- so `P1` against a bead's `1` is not reported as a
disagreement. The stored values stay verbatim; only the comparison folds.

## Never derived

`unlock_count` is **read**, never computed. The obvious alternative -- count
what a brief's bead unblocks -- returns approximately zero: of the 528 edges
in the live HQ store 508 are `related`, and exactly one of 264 beads carries a
blocking edge. The frontmatter number was written by whoever knew what the
brief unblocked; a traversal would quietly replace it with 0.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .materialize_plan import parse_stack_file
from .verdicts import CONFIDENCE_HIGH


#: Where a field value was read. `bead` is a canonical bd column; `manifest_row`
#: is a key on a decisions-track manifest row; `frontmatter` is a key in the
#: YAML-ish block at the top of a brief's markdown file.
SOURCE_BEAD = "bead"
SOURCE_MANIFEST_ROW = "manifest_row"
SOURCE_FRONTMATTER = "frontmatter"
#: A key in the frontmatter of the brief's *stack* file. Kept apart from
#: `frontmatter`, which on a manifest record means the file beside the
#: manifest: a brief can have both, and they disagree. Measured on the live
#: city 2026-08-20, of the rows that have both documents `form` disagreed 13
#: times, `status` 5 and `artifact` once -- and the stack copy was the newer
#: one in 14 of the 15 pairs whose text differed at all. A surface that
#: labelled both readings `frontmatter` would show the same word twice beside
#: two different answers and give a reader no way to tell which document said
#: which.
SOURCE_STACK_FRONTMATTER = "stack_frontmatter"
FIELD_SOURCES = (
    SOURCE_BEAD,
    SOURCE_MANIFEST_ROW,
    SOURCE_FRONTMATTER,
    SOURCE_STACK_FRONTMATTER,
)

#: The fields exposed with provenance on every record that can carry them.
#: `verdict` is here as well as on `BriefRecord.verdict`: the record-level
#: verdict is the resolved one, and this is every reading that resolution saw.
EXPOSED_FIELDS = ("form", "gates", "priority", "track", "unlock_count", "verdict")


@dataclass(frozen=True)
class FieldValue:
    """One store's answer for one field, verbatim, with where it came from.

    Structurally the same claim `verdicts.Verdict` makes -- text, source,
    confidence, exact field -- because it is the same kind of claim.
    """

    value: str
    source: str
    confidence: str
    #: The exact field the value came from, e.g. `frontmatter.unlock_count`.
    field: str

    def to_dict(self) -> dict[str, str]:
        return {
            "confidence": self.confidence,
            "field": self.field,
            "source": self.source,
            "value": self.value,
        }


@dataclass(frozen=True)
class FieldReading:
    """Every store's answer for one field, in authority order.

    Never empty: a field no store holds produces no `FieldReading` at all,
    because an entry whose readings are `[]` would render as "asked and found
    nothing" rather than "absent".
    """

    name: str
    readings: tuple[FieldValue, ...]

    @property
    def value(self) -> str:
        """The most authoritative reading's value, verbatim."""
        return self.readings[0].value

    @property
    def source(self) -> str:
        return self.readings[0].source

    @property
    def conflict(self) -> bool:
        """Whether two stores hold this field and disagree about it."""
        return len({_fold(self.name, reading.value) for reading in self.readings}) > 1

    def to_dict(self) -> dict[str, object]:
        return {
            "conflict": self.conflict,
            "name": self.name,
            "readings": [reading.to_dict() for reading in self.readings],
            "source": self.source,
            "value": self.value,
        }


def read_frontmatter(text: str) -> Mapping[str, str]:
    """The frontmatter block of a brief file, as `materialize_plan` reads it.

    Delegated rather than re-implemented. That parser is a line matcher on
    purpose: several live files carry values a YAML loader rejects outright
    (an unquoted `needs-revision(...:...;...)` status, a bare `[236]`), and a
    strict parse would drop those briefs entirely instead of losing one key.
    """
    return parse_stack_file("frontmatter", text).frontmatter


def frontmatter_value(
    frontmatter: Mapping[str, str], name: str, *, key: str | None = None
) -> FieldValue | None:
    """One frontmatter key as a `FieldValue`, or None when it is absent."""
    value = _unquote(frontmatter.get(key or name, ""))
    if not value:
        return None
    return FieldValue(value, SOURCE_FRONTMATTER, CONFIDENCE_HIGH, f"frontmatter.{key or name}")


def stack_frontmatter_value(
    frontmatter: Mapping[str, str], name: str, *, key: str | None = None
) -> FieldValue | None:
    """One stack-file frontmatter key as a `FieldValue`, or None when absent.

    Same read as `frontmatter_value`, under its own source and its own `field`
    spelling, so two documents' answers to one question stay tellable apart.
    """
    value = _unquote(frontmatter.get(key or name, ""))
    if not value:
        return None
    return FieldValue(
        value, SOURCE_STACK_FRONTMATTER, CONFIDENCE_HIGH, f"stack.frontmatter.{key or name}"
    )


def row_value(row: Mapping[str, object], name: str, *, field: str) -> FieldValue | None:
    """One manifest-row key as a `FieldValue`, or None when it is absent.

    Numbers are stringified rather than dropped: `unlock_count` is an integer
    on 149 rows and a string in frontmatter, and a reader that skipped the
    integer would report the document as the only source of a value the row
    also holds.
    """
    return _scalar(row.get(name), SOURCE_MANIFEST_ROW, field)


def bead_value(raw: Mapping[str, object], name: str, *, field: str) -> FieldValue | None:
    """One canonical bd column as a `FieldValue`, or None when it is absent."""
    return _scalar(raw.get(name), SOURCE_BEAD, field)


def reading(name: str, *candidates: FieldValue | None) -> FieldReading | None:
    """A `FieldReading` over whichever candidates exist, in the order given.

    Returns None when no store holds the field. Absent stays absent.
    """
    present = tuple(candidate for candidate in candidates if candidate is not None)
    return FieldReading(name, present) if present else None


def readings_map(readings: tuple[FieldReading, ...]) -> dict[str, object]:
    """The `fields` payload: field name -> reading, sorted, absences omitted."""
    return {item.name: item.to_dict() for item in sorted(readings, key=lambda item: item.name)}


def _scalar(value: object, source: str, field: str) -> FieldValue | None:
    if isinstance(value, bool) or value is None:
        # A bool is not a value any of these fields takes, and `None` is the
        # JSON spelling of absent. Neither becomes a reading.
        return None
    if isinstance(value, str):
        text = value.strip()
    elif isinstance(value, (int, float)):
        text = str(value)
    elif isinstance(value, (list, tuple)):
        text = ", ".join(str(item) for item in value)
    else:
        return None
    return FieldValue(text, source, CONFIDENCE_HIGH, field) if text else None


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1].strip()
    return value


def _fold(name: str, value: str) -> str:
    """The comparison key for one value. Folds only; never rewrites the value.

    `priority: P1` in a document and `priority: 1` on a bead are the same
    claim in two spellings, and reporting them as a disagreement would bury
    the 17 real ones under 47 false positives.
    """
    folded = value.strip().casefold()
    if name == "priority" and folded.startswith("p"):
        folded = folded[1:].strip()
    return folded
