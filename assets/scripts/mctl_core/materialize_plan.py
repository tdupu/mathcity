"""Plan -- never perform -- the materialisation of beadless stack briefs.

`<city-root>/.beads/briefs/stack/` holds 89 markdown briefs that have no
decision bead. `artifact:` in their frontmatter names the brief's **subject**
(the bead whose disposition it decides), not a brief bead, so nothing points at
these files: the decisions-track join yields 0, `show_brief` raises `MBRF010`,
and `MOPT001` cannot fire.

D2/D3/D4 say the bead id is the docket, the system is bead-first, and every
stray document must nevertheless be migrated in. This module computes what that
migration *would* create.

## Read-only by construction

There is no write path in this module, and there cannot be one: it imports no
subprocess, no shell, and nothing from `mctl_core.beads` (which does carry a
write path). It consumes text and a bead index and returns dataclasses. The
`bd create` / `bd dep add` lines it emits are **strings**, never executed here.
`tests/mctl/test_materialize_plan.py` asserts the import ban mechanically, so
the property survives editing.

## Where a brief bead goes, and why the cross-rig blocker dissolves

Slice 5 found `he-tbmq0`'s source in another rig and flagged it as needing "a
design answer, not a link". Measured on a throwaway store, the situation is
worse than "cannot": `bd dep add <local> <foreign-id>` exits **0** and prints
`✓ Added dependency`, the row lands (`dependency_count` increments), and the
edge then appears in **no** listing -- not `bd dep list`, not the
`dependencies` array `Bead.source_dependencies` is built from. A cross-store
link written that way is invisible data loss that still satisfies a naive
`dependency_count >= 1` check of B2.1.

`bd create --deps <foreign-id>` instead fails loudly:
``Error: resolving --deps target "…": no issue found matching "…"``.

So the plan (a) places each brief bead **in the store its `artifact:` already
lives in**, which makes every source edge intra-store, and (b) writes the
source link with `bd create --deps`, never `bd dep add`, so a mistake is a
non-zero exit rather than a silent phantom. `TARGET_STORE_FALLBACK` takes the
files whose artifact resolves to nothing; those get **no** source link at all
and stay visibly malformed under `MBRF004` rather than carrying a guess.

## Verdicts are transcribed, not asserted

48 of the 89 files claim some disposition, but only 20 carry all three fields
B2.2 demands of an adjudication -- verdict, authorizer, date. Those 20 are
planned closed with the verdict written into `notes` in the exact shape
`verdicts.py::_NOTES_CANONICAL` already reads (`VERDICT: … | AUTHORIZER: … |
RATIONALE: …`), so the existing adapter resolves them at high confidence with
`source="notes"` and nothing here re-derives a verdict format.

The other 28 claim a disposition without those fields and are planned **open**,
their claim copied verbatim into a clearly-labelled prior-disposition note.
That direction is chosen deliberately, on the asymmetry `verdicts.py` already
argues: a brief wrongly opened resurfaces once and a human closes it, whereas a
brief wrongly closed with an asserted verdict is unreachable under B2.3 ("the
remedy is a NEW brief bead, never reopening the old one") and invisible
afterwards.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
import shlex
from typing import Iterable, Mapping, Sequence

#: Bead-id prefix -> the rig directory whose `.beads` store mints it. Derived
#: from every live `.beads/config.yaml` in the city, NOT from `rigs.json`:
#: `rigs.json` lists 9 rigs and omits `gt`/`gsp`/`gs`/`mc`/`cp2` entirely, and
#: an earlier pass that trusted it classified 15 references as "unknown prefix"
#: when all 15 name real, live, readable stores.
STORE_BY_PREFIX: Mapping[str, str] = {
    "as": "agent_skills",
    "cp2": "cliff-part2",
    "dv": "differential_valuations",
    "gs": "gascity",
    "gsp": "gascity-packs",
    "gt": "gt",
    "he": "hecke",
    "ho": "homog",
    "hq": "gt",
    "ja": "jacobi",
    "lm": "lmfdb",
    "mc": "mathcity",
    "mca": "magma_clifford_algebras",
    "mda": "magma_diff_alg",
    "tgi": "tdupu_github_io",
}

#: Where a brief whose `artifact:` resolves to nothing would go: the store that
#: owns `<city-root>/.beads/briefs/stack/` itself.
TARGET_STORE_FALLBACK = "gt"

#: Metadata key carrying the stack filename. This is the idempotency key, and
#: it is deliberately NOT `gc.brief.slug`: that key already exists on 826 live
#: beads written by the formula machinery (74 of them naming a current stack
#: file), so re-using it would make a re-run skip files that were never
#: materialised.
STACK_FILE_KEY = "mathcity.brief.stack_file"
MATERIALIZED_KEY = "mathcity.brief.materialized_by"
UNRESOLVED_KEY = "mathcity.brief.unresolved_artifact"

#: The value written into MATERIALIZED_KEY. A single literal, so the whole
#: batch is one `bd list` query away from being found again or undone.
MATERIALIZED_VALUE = "beadless-brief-materialization-2026-08-19"

# Problem classes the plan reports per row.
CLASS_UNRESOLVED = "P1-unresolved-artifact"
CLASS_CROSS_RIG = "P2-cross-rig-source"
CLASS_VERDICT = "P3-carries-verdict"
CLASS_DUPLICATE = "P4-bead-already-exists"
CLASS_COLLISION = "P5-existing-decision-names-the-same-artifact"

# Disposition tiers (see the module docstring).
TIER_ADJUDICATED = "A-adjudicated"
TIER_CLAIMED = "B-claimed-disposition"
TIER_OPEN = "C-no-disposition"

#: Frontmatter statuses that assert the brief was disposed of. `ready` and
#: `ready-for-adjudication` are NOT among them -- "ready for adjudication" is
#: the opposite of adjudicated, and reading it as a disposition is how a
#: previous count reached 58 instead of 35.
_DISPOSED_STATUS_PREFIXES = (
    "adjudicated",
    "approved",
    "changes_required",
    "deferred",
    "mixed-partial",
    "needs-revision",
    "on-hold-needs-revision",
    "revise",
)

#: Frontmatter keys that already name an existing bead for this very brief.
#: A row carrying one is a duplicate risk and is planned as SKIP.
_EXISTING_BEAD_KEYS = ("brief_bead", "decision_bead", "brief_record_bead", "repair_review_bead")

#: A bead id inside the free-text `artifact:` field. The prefix must be a known
#: store prefix; `gh-issue-335`, `f4f72ed` and a bare `.md` filename are
#: therefore not ids, which is the correct reading -- none of them is a bead.
_BEAD_ID = re.compile(r"\b([a-z][a-z0-9_]{1,6})-([a-z0-9]{3,8}(?:\.\d+)?)\b")

FRONTMATTER_LINE = re.compile(r"^([A-Za-z0-9_.-]+):\s*(.*)$")


@dataclass(frozen=True)
class StackFile:
    """One `.md` under the stack directory, parsed but not interpreted."""

    name: str
    frontmatter: Mapping[str, str]

    @property
    def slug(self) -> str:
        return self.name[:-3] if self.name.endswith(".md") else self.name


@dataclass(frozen=True)
class PlanRow:
    """What materialising one stack file would create. Nothing is created."""

    name: str
    artifact_raw: str
    artifact_ids: tuple[str, ...]
    resolved_ids: tuple[str, ...]
    target_store: str
    #: `issue_type` of the *artifact* bead(s) -- what the brief decides about.
    artifact_types: tuple[str, ...]
    title: str
    status: str
    verdict: str | None
    verdict_authorizer: str | None
    verdict_rationale: str | None
    tier: str
    problem_classes: tuple[str, ...]
    existing_bead: str | None
    #: Decision beads whose TITLE already names this file's artifact id.
    #: Not an auto-skip -- a title collision is evidence, not proof -- but a
    #: row carrying one must not be created before a human looks.
    collisions: tuple[str, ...]
    #: The `status:` the stack file itself claims, verbatim. Kept because for
    #: 26 of the 28 tier-B rows it is the *only* disposition evidence there is.
    claimed_status: str

    @property
    def action(self) -> str:
        if self.existing_bead:
            return "SKIP"
        return "HOLD" if self.collisions else "CREATE"

    @property
    def resolves(self) -> bool:
        return bool(self.resolved_ids)

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action,
            "artifact_ids": list(self.artifact_ids),
            "artifact_raw": self.artifact_raw,
            "artifact_types": list(self.artifact_types),
            "claimed_status": self.claimed_status,
            "collisions": list(self.collisions),
            "existing_bead": self.existing_bead,
            "name": self.name,
            "problem_classes": list(self.problem_classes),
            "resolved_ids": list(self.resolved_ids),
            "status": self.status,
            "target_store": self.target_store,
            "tier": self.tier,
            "title": self.title,
            "verdict": self.verdict,
            "verdict_authorizer": self.verdict_authorizer,
            "verdict_rationale": self.verdict_rationale,
        }


def parse_stack_file(name: str, text: str) -> StackFile:
    """Split a stack file's YAML-ish frontmatter from its body.

    Deliberately a line matcher rather than a YAML parse: several live files
    carry values a YAML loader rejects outright (an unquoted
    `needs-revision(...:...;...)` status, bare `[236]`), and a brief that fails
    to parse would silently drop out of the plan.
    """
    frontmatter: dict[str, str] = {}
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end > 0:
            for line in text[4:end].splitlines():
                match = FRONTMATTER_LINE.match(line)
                if match:
                    frontmatter[match.group(1)] = match.group(2).strip()
    return StackFile(name=name, frontmatter=frontmatter)


def artifact_ids(value: str | None) -> tuple[str, ...]:
    """Bead ids named by an `artifact:` value, in order, deduplicated.

    `none`, `none (blocks gt-g2e + brief 04)`, `gh-issue-335`, a git sha and a
    `.md` filename all yield `()`. The `none (...)` case matters: the
    parenthetical names real beads that the brief *blocks*, not the bead it
    decides about, and treating them as the source would attach the
    adjudication to the wrong work.
    """
    if not value:
        return ()
    stripped = value.strip()
    if stripped.lower().startswith("none"):
        return ()
    found: list[str] = []
    for match in _BEAD_ID.finditer(stripped):
        if match.group(1) in STORE_BY_PREFIX and match.group(0) not in found:
            found.append(match.group(0))
    return tuple(found)


def store_of(bead_id: str) -> str | None:
    prefix = bead_id.split("-", 1)[0]
    return STORE_BY_PREFIX.get(prefix)


def humanised_title(stack_file: StackFile) -> str:
    """A title from the filename.

    Not from the body: 81 of the 89 files open with the literal heading
    `§1 What is being decided`, and 3 more with a shared `[UNPREPPED …]`
    banner, so headings identify almost nothing. The slug does.
    """
    slug = stack_file.slug
    slug = re.sub(r"-brief$", "", slug)
    words = slug.replace("_", " ").replace("-", " ").split()
    return "[brief] " + " ".join(words) if words else "[brief] " + stack_file.slug


def is_disposed(status: str) -> bool:
    """Whether a frontmatter `status` asserts the brief was already disposed of.

    Public because the B1.3 shape repair must skip already-adjudicated briefs
    ("repair unless they are already closed") and needs *this* answer, not a
    second opinion. A repair tool that redefined the prefix list would drift
    from `classify_tier` the first time either side gained a status, and the
    two would then disagree about which briefs are still open.
    """
    return status.lower().startswith(_DISPOSED_STATUS_PREFIXES)


#: The in-module callers keep the original private spelling.
_disposed = is_disposed


def classify_tier(frontmatter: Mapping[str, str]) -> str:
    """Which disposition tier this brief is in. Never infers a verdict."""
    verdict = (frontmatter.get("verdict") or "").strip()
    authorizer = (frontmatter.get("adjudicated_by") or "").strip()
    date = (frontmatter.get("adjudicated_at") or "").strip()
    if verdict and authorizer and date:
        return TIER_ADJUDICATED
    if verdict or _disposed(frontmatter.get("status") or ""):
        return TIER_CLAIMED
    return TIER_OPEN


def _unquote(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def decision_titles(index: Mapping[str, Mapping[str, object]]) -> tuple[tuple[str, str], ...]:
    """`(bead id, title)` for every `type=decision` bead in the index.

    Precomputed once because the collision check is a cross product: 89 files
    against 280 decision beads.
    """
    return tuple(
        (str(bead_id), str(bead.get("title") or ""))
        for bead_id, bead in index.items()
        if bead.get("issue_type") == "decision"
    )


def build_row(
    stack_file: StackFile,
    index: Mapping[str, Mapping[str, object]],
    titles: Sequence[tuple[str, str]] | None = None,
) -> PlanRow:
    """The plan for one stack file, against a bead index keyed by bead id."""
    frontmatter = stack_file.frontmatter
    raw = frontmatter.get("artifact", "")
    ids = artifact_ids(raw)
    resolved = tuple(i for i in ids if i in index)
    stores = tuple(dict.fromkeys(store_of(i) or "?" for i in resolved))

    target = stores[0] if len(stores) == 1 else TARGET_STORE_FALLBACK
    problems: list[str] = []
    if not resolved:
        problems.append(CLASS_UNRESOLVED)
    if len(stores) > 1:
        problems.append(CLASS_CROSS_RIG)

    tier = classify_tier(frontmatter)
    verdict = _unquote(frontmatter.get("verdict", "")) or None
    if tier != TIER_OPEN:
        problems.append(CLASS_VERDICT)

    if titles is None:
        titles = decision_titles(index)
    collisions = tuple(
        sorted(
            bead_id
            for bead_id, title in titles
            if any(source in title for source in resolved)
        )
    )
    if collisions:
        problems.append(CLASS_COLLISION)

    existing = None
    for key in _EXISTING_BEAD_KEYS:
        value = (frontmatter.get(key) or "").strip()
        if value and value in index:
            existing = value
            break
    if existing:
        problems.append(CLASS_DUPLICATE)

    return PlanRow(
        name=stack_file.name,
        artifact_raw=raw,
        artifact_ids=ids,
        resolved_ids=resolved,
        target_store=target,
        artifact_types=tuple(
            str(index[i].get("issue_type") or "?") for i in resolved
        ),
        title=humanised_title(stack_file),
        status="closed" if tier == TIER_ADJUDICATED else "open",
        verdict=verdict,
        verdict_authorizer=_unquote(frontmatter.get("adjudicated_by", "")) or None,
        verdict_rationale=_unquote(frontmatter.get("verdict_note", "")) or None,
        tier=tier,
        problem_classes=tuple(problems),
        existing_bead=existing,
        collisions=collisions,
        claimed_status=frontmatter.get("status", "") or "(absent)",
    )


def build_plan(
    texts: Mapping[str, str], index: Mapping[str, Mapping[str, object]]
) -> tuple[PlanRow, ...]:
    """Plan every stack file. `texts` maps filename -> file contents."""
    titles = decision_titles(index)
    return tuple(
        build_row(parse_stack_file(name, texts[name]), index, titles)
        for name in sorted(texts)
    )


def notes_for(row: PlanRow) -> str | None:
    """The `notes` body, in the shape `verdicts.py` already parses.

    Tier A writes the canonical `VERDICT: … | AUTHORIZER: … | RATIONALE: …`.
    Tier B writes a prior-disposition line that deliberately does NOT start
    with `VERDICT:`, so `_NOTES_CANONICAL` does not match it and no unmade
    adjudication is manufactured.
    """
    if row.tier == TIER_ADJUDICATED:
        rationale = row.verdict_rationale or f"recorded in {row.name}"
        return (
            f"VERDICT: {row.verdict} | AUTHORIZER: {row.verdict_authorizer} "
            f"| RATIONALE: {rationale}"
        )
    if row.tier == TIER_CLAIMED:
        claim = row.verdict or "(no typed verdict field)"
        return (
            "UNVERIFIED-PRIOR-DISPOSITION (not an adjudication; B2.2 fields incomplete) "
            f"| stack_file: {row.name} | claimed status: {row.claimed_status} "
            f"| recorded verdict: {claim}"
        )
    return None


def metadata_for(row: PlanRow) -> dict[str, str]:
    metadata = {
        STACK_FILE_KEY: row.name,
        MATERIALIZED_KEY: MATERIALIZED_VALUE,
    }
    if not row.resolves:
        metadata[UNRESOLVED_KEY] = row.artifact_raw or "(absent)"
    return metadata


def commands_for(row: PlanRow, *, city_root: str = "$CITY") -> tuple[str, ...]:
    """The literal shell lines a later run would execute for this row.

    `--deps` rather than a follow-up `bd dep add`: see the module docstring --
    `bd dep add` to an id the store cannot resolve exits 0 and stores an edge
    that never appears in any listing.
    """
    if row.existing_bead:
        return (
            f"# SKIP {row.name}: bead {row.existing_bead} already exists "
            f"(frontmatter names it)",
        )
    if row.collisions:
        held = ", ".join(row.collisions)
        return (
            f"# HOLD {row.name}: decision bead(s) {held} already name this "
            f"file's artifact in their title -- confirm before creating",
        )
    rig_root = city_root if row.target_store == "gt" else f"{city_root}/{row.target_store}"
    parts = [
        "bd", "-C", rig_root, "create", row.title,
        "-t", "decision",
        "--metadata", json.dumps(metadata_for(row), sort_keys=True),
    ]
    for source in row.resolved_ids:
        parts += ["--deps", source]
    notes = notes_for(row)
    if notes:
        parts += ["--notes", notes]
    parts.append("--silent")
    lines = [shlex.join(parts)]
    if row.status == "closed":
        reason = f"{row.verdict} (migrated verbatim from {row.name})"
        lines.append(
            shlex.join(["bd", "-C", rig_root, "close", "<NEW-ID>", "--reason", reason])
        )
    return tuple(lines)


def rollback_commands(rows: Iterable[PlanRow], *, city_root: str = "$CITY") -> tuple[str, ...]:
    """How the whole batch is undone.

    One query per touched store finds every bead the batch wrote, by the single
    literal `MATERIALIZED_KEY` value; `bd delete --force` was verified on a
    throwaway store to remove the bead and its dependency links.
    """
    stores = sorted({row.target_store for row in rows if row.action == "CREATE"})
    lines = []
    for store in stores:
        rig_root = city_root if store == "gt" else f"{city_root}/{store}"
        lines.append(
            f"bd -C {rig_root} list --json --status all "
            f"| jq -r '.[] | select(.metadata.\"{MATERIALIZED_KEY}\" == "
            f'"{MATERIALIZED_VALUE}") | .id\' '
            f"| xargs -r -n1 bd -C {rig_root} delete --force"
        )
    return tuple(lines)


def summarise(rows: Sequence[PlanRow]) -> dict[str, object]:
    """Counts the plan asserts, recomputed from the rows themselves."""
    classes: dict[str, int] = {}
    tiers: dict[str, int] = {}
    stores: dict[str, int] = {}
    for row in rows:
        tiers[row.tier] = tiers.get(row.tier, 0) + 1
        stores[row.target_store] = stores.get(row.target_store, 0) + 1
        for problem in row.problem_classes:
            classes[problem] = classes.get(problem, 0) + 1
    return {
        "files": len(rows),
        "create": sum(1 for row in rows if row.action == "CREATE"),
        "hold": sum(1 for row in rows if row.action == "HOLD"),
        "skip": sum(1 for row in rows if row.action == "SKIP"),
        "resolves": sum(1 for row in rows if row.resolves),
        "cross_rig": sum(1 for row in rows if CLASS_CROSS_RIG in row.problem_classes),
        "problem_classes": dict(sorted(classes.items())),
        "target_stores": dict(sorted(stores.items())),
        "tiers": dict(sorted(tiers.items())),
    }
