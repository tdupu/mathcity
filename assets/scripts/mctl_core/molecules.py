"""Molecule identity (#109) -- the noun the city dashboard census is built on.

Design: `<city-root>/docs/D1-molecule-identity-proposal.md`, read off three live
beads before it was written rather than inferred from the formula spec.

A MOLECULE IS ONE EXECUTION OF ONE FORMULA, and its identity is its root bead
id. Each dispatch mints a NEW root, so one source bead dispatched four times is
four molecules -- which is exactly what makes "this has been attempted four
times" visible instead of looking like one complicated bead.

THE PREDICATE. `gc.kind == "workflow"`. The city already declares this; nobody
had read it. Three bead classes, three clean signatures:

    root      gc.kind = "workflow"           no gc.root_bead_id   has gc.formula_name
    step      gc.kind = "workflow-finalize"  gc.root_bead_id=root no gc.formula_name
    ordinary  gc.kind absent                 absent               absent

THE EDGE POINTS AT THE ROOT, AND THE HANDOFF SAID OTHERWISE. The dashboard
handoff defines a molecule as "a workflow root bead *carrying*
`gc.root_bead_id`". That is backwards. The root does not carry it; steps carry
it and point at the root. `beads.Bead.workflow_root_id` documented it backwards
too -- corrected in this branch. Anyone building from the handoff sentence
builds the edge in the wrong direction, so `is_step` keys on the pointer.

WHY STEPS ARE KEYED ON THE POINTER AND NOT ON `gc.kind`. `workflow-finalize`
implies a namespaced family (`workflow-implement`, `workflow-review`, ...) that
is NOT enumerated. A step predicate keyed on the kind vocabulary goes stale the
moment a kind is added; `gc.root_bead_id` presence cannot.

WHAT THIS MODULE DELIBERATELY DOES NOT DO. It does not report molecule *state*.
`advancing` / `stalled` / `stranded` / `dormant` require the evidence chain
(#115), which is blocked because four of its five links record nothing today.
A molecule row showing a state it cannot derive is a plausible-empty-result
failure wearing a different mask, so `describe()` omits the key entirely rather
than defaulting it.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from .beads import Bead, BeadReadError, read_beads
from .diagnostics import Diagnostic, Severity

#: The exact `gc.kind` of a molecule root. EXACT: `workflow-finalize` and every
#: other step kind startswith `workflow`, so a prefix test inverts the whole
#: population and calls every step a root.
ROOT_KIND = "workflow"

#: The step -> root pointer. Presence of this key IS the step predicate.
ROOT_POINTER = "gc.root_bead_id"

#: `gc.root_store_ref` is prefixed (`rig:gascity-packs`), not a bare rig id.
_RIG_REF_PREFIX = "rig:"

#: Stage artifacts live under this namespace, one key per stage.
_ARTIFACT_PREFIX = "gc.build."


def _metadata(bead: Bead) -> Mapping[str, object]:
    raw = bead.raw.get("metadata")
    return raw if isinstance(raw, Mapping) else {}


def _text(metadata: Mapping[str, object], key: str) -> str | None:
    """A metadata string, or None. Empty-string is None: `gc` writes empty
    values for unset keys, and reporting "" as a value would be a guess."""
    value = metadata.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def is_molecule_root(bead: Bead) -> bool:
    """Whether this bead IS a molecule -- one run of one formula."""
    return _text(_metadata(bead), "gc.kind") == ROOT_KIND


def is_step(bead: Bead) -> bool:
    """Whether this bead is a step OF some molecule.

    Keyed on the pointer, not the kind vocabulary -- see module docstring.
    """
    return _text(_metadata(bead), ROOT_POINTER) is not None


def root_id_of(bead: Bead) -> str | None:
    """The molecule this step belongs to, or None if it is not a step."""
    return _text(_metadata(bead), ROOT_POINTER)


def steps_of(root_id: str, beads: Iterable[Bead]) -> tuple[Bead, ...]:
    """Every step pointing at `root_id`, via the reverse index.

    The root's own `dependencies` array also materialises step beads, but it
    holds only the step the root is *blocked by* -- one edge where a molecule
    has many. The reverse index is authoritative; `dependencies` is a shortcut.
    """
    return tuple(b for b in beads if root_id_of(b) == root_id)


def roots_in(beads: Iterable[Bead]) -> tuple[Bead, ...]:
    return tuple(b for b in beads if is_molecule_root(b))


def is_closed_status(status: str | None) -> bool:
    """Whether a bead status is terminal (`closed`/`done`).

    Public because the cancel path (mc-x06e) and the evidence links must agree on
    what "still open" means; a second private copy would drift the first time the
    vocabulary gained a status.
    """
    return (status or "").strip().lower() in _CLOSED_STATUSES


def open_steps_of(root_id: str, beads: Iterable[Bead]) -> tuple[Bead, ...]:
    """The steps of `root_id` that are NOT closed -- what a cancel must close."""
    return tuple(s for s in steps_of(root_id, beads) if not is_closed_status(s.status))


def _rig_of(metadata: Mapping[str, object]) -> str | None:
    ref = _text(metadata, "gc.root_store_ref")
    if ref is None:
        return None
    return ref[len(_RIG_REF_PREFIX):] if ref.startswith(_RIG_REF_PREFIX) else ref


def _artifacts_of(metadata: Mapping[str, object]) -> dict[str, str]:
    """Stage artifacts, keyed by stage rather than by full metadata key.

    These are the substrate for the artifact link of the evidence chain
    (#115): they name real paths a step was supposed to produce.
    """
    out: dict[str, str] = {}
    for key, value in metadata.items():
        if not key.startswith(_ARTIFACT_PREFIX):
            continue
        if isinstance(value, str) and value.strip():
            out[key[len(_ARTIFACT_PREFIX):]] = value.strip()
    return dict(sorted(out.items()))


# --- the evidence core (#115), buildable slice only -------------------------
#
# The issue owner measured the live event log and ruled the full five-link
# chain (claimed -> agent_active -> commit -> artifact -> step_closed) NOT
# BUILDABLE as specified: four of five links have no emitter, and building a
# positional `broken_at` regardless would blame link 1 (`claimed`) on every
# healthy step -- the exact defect inverted (P6.2's mirror: a check that
# could not have failed must not render as passed). What follows is the
# honest subset: read the declaration #142 already lays down, derive
# `is_complete` three-valued from it, and represent all five links with a
# tri-state that never claims more than the city can measure.

#: `gc.expected_artifacts.v1` -- a JSON array of path strings, set at formula-
#: authoring time (#142). `.v1`-suffixed keys holding JSON are the house
#: convention for structured metadata (see `gc.graphv2_vars.v1`).
EXPECTED_ARTIFACTS_KEY = "gc.expected_artifacts.v1"

IS_COMPLETE_COMPLETE = "complete"
IS_COMPLETE_INCOMPLETE = "incomplete"
#: "We did not measure", never a fallback to bead status. A closed bead with
#: no declaration is `unknown`, not `complete` -- self-reported completion is
#: the defect #115 exists to stop trusting.
IS_COMPLETE_UNKNOWN = "unknown"


def _expected_artifacts_of(metadata: Mapping[str, object]) -> list[str] | None:
    """The step's declared artifact paths, or `None` -- "no declaration".

    `None` covers three cases that must all read alike downstream: the key is
    absent, its value is blank, and its value is present but does not parse
    as a JSON array of strings. A malformed declaration must NOT become `[]`
    ("declared zero artifacts") -- that would let `is_complete` report
    `complete` for a step that simply failed to author its metadata
    correctly, which is a false positive, not an honest empty case. Never
    raises: a formula author's typo must not crash a read.
    """
    raw = _text(metadata, EXPECTED_ARTIFACTS_KEY)
    if raw is None:
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError, ValueError):
        return None
    if not isinstance(parsed, list) or not all(isinstance(item, str) for item in parsed):
        return None
    return [item.strip() for item in parsed if item.strip()]


def _completion_of(metadata: Mapping[str, object]) -> dict[str, object]:
    """`is_complete`, THREE-VALUED, derived only from declared-vs-actual
    artifacts -- never from bead status.

    Carries its own inputs (`declared`/`present`/`missing`) so the verdict
    shows its work (honesty invariant Sec 5.5: a derived state carries its
    inputs), rather than asserting a bare word a reader has to trust.
    """
    declared = _expected_artifacts_of(metadata)
    if declared is None:
        return {
            "is_complete": IS_COMPLETE_UNKNOWN,
            "declared": None,
            "present": [],
            "missing": [],
        }
    actual_paths = set(_artifacts_of(metadata).values())
    present = [path for path in declared if path in actual_paths]
    missing = [path for path in declared if path not in actual_paths]
    return {
        "is_complete": IS_COMPLETE_INCOMPLETE if missing else IS_COMPLETE_COMPLETE,
        "declared": declared,
        "present": present,
        "missing": missing,
    }


LINK_RECORDED = "recorded"
#: No emitter exists for this link in the city today. Deliberately never
#: `not_yet` -- `not_yet` claims an emitter exists and simply has not fired,
#: which is a stronger and false claim for these three links.
LINK_NOT_RECORDED = "not_recorded"
#: An emitter exists and has not fired for this step.
LINK_NOT_YET = "not_yet"

#: The five links of the evidence chain (#115), in chain order. This is
#: DISPLAY order only -- `broken_at` does NOT walk this list picking the
#: first `not_yet` link. See `_broken_at` for why that would be dishonest.
EVIDENCE_LINK_ORDER = ("claimed", "agent_active", "commit", "artifact", "step_closed")

#: Measured against the live event log (#115's scope ruling): these three
#: have no emitter in the city today.
_NO_EMITTER_LINKS = frozenset({"claimed", "agent_active", "commit"})

#: Bead-status values this city treats as closed. Shared with `work.py` /
#: `briefs.py`'s own `{"closed", "done"}` convention rather than inventing a
#: second one here.
_CLOSED_STATUSES = frozenset({"closed", "done"})


def _evidence_links(
    step_metadata: Mapping[str, object], step_status: str, actual_artifacts: Mapping[str, str]
) -> tuple[dict[str, object], ...]:
    """The five evidence links, each an honest tri-state object.

    `step_metadata` is accepted (and currently unused) so a future emitter
    for `claimed`/`agent_active`/`commit` has an obvious place to read from
    without changing every caller's signature.
    """
    del step_metadata  # no emitter reads step metadata for the three links yet
    links: list[dict[str, object]] = []
    for name in EVIDENCE_LINK_ORDER:
        if name in _NO_EMITTER_LINKS:
            links.append(
                {
                    "link": name,
                    "status": LINK_NOT_RECORDED,
                    "reason": f"No emitter exists for the {name!r} link in this city today (#115).",
                }
            )
        elif name == "artifact":
            if actual_artifacts:
                links.append(
                    {
                        "link": name,
                        "status": LINK_RECORDED,
                        "reason": (
                            f"{len(actual_artifacts)} gc.build.* artifact(s) recorded for this step."
                        ),
                    }
                )
            else:
                links.append(
                    {
                        "link": name,
                        "status": LINK_NOT_YET,
                        "reason": "gc.build.* records artifacts; none is recorded for this step yet.",
                    }
                )
        else:  # step_closed
            closed = step_status.strip().lower() in _CLOSED_STATUSES
            links.append(
                {
                    "link": name,
                    "status": LINK_RECORDED if closed else LINK_NOT_YET,
                    "reason": f"Bead status is {step_status!r}.",
                }
            )
    return tuple(links)


def _broken_at(step_status: str, completion: Mapping[str, object]) -> dict[str, object]:
    """The ONE genuine, checkable break -- and nothing else.

    An earlier draft named the first `not_yet` link in chain order. That is
    the exact defect #115 was filed to prevent, shifted from `claimed` to
    `artifact`/`step_closed`: with only those two links observable and no
    staleness/timing signal, "advancing" (healthy, still in flight) and
    "stalled" (broken) are INDISTINGUISHABLE from a bare `not_yet`. Naming
    the first one regardless renders "Break: artifact" on every healthy
    in-flight step -- a check that could not have failed rendering as failed
    (the honesty invariants' mirror: a check that could not have PASSED must
    not render as a finding; here it is a check that could not have FAILED,
    yet, rendering as one).

    The one break this city CAN check today: a step whose bead status is
    CLOSED (`step_closed` recorded) but whose DECLARED `expected_artifacts`
    are still MISSING. That is not "not yet" -- the step already claims to
    be done, so a missing declared artifact is a genuine, checkable defect:
    completion self-reported without producing the declared output. This is
    exactly the `is_complete == "incomplete"` case occurring on a closed
    step.

    Every other case -- open/in-flight, no declaration (nothing to check),
    or closed with every declared artifact present -- reports `broken_at:
    None` with a reason. `None` here is NOT a claim the whole chain is
    healthy: `claimed`/`agent_active`/`commit` have no emitter and remain
    unassessed regardless of this verdict.
    """
    declared = completion.get("declared")
    missing = completion.get("missing") or []
    closed = step_status.strip().lower() in _CLOSED_STATUSES
    if closed and declared is not None and missing:
        return {
            "broken_at": "artifact",
            "broken_at_reason": (
                f"Bead status is closed (step_closed recorded), but {len(missing)} of "
                f"{len(declared)} declared artifact(s) are missing -- completion was "
                "self-reported without producing the declared output."
            ),
        }
    return {
        "broken_at": None,
        "broken_at_reason": (
            "No genuine break. Distinguishing an advancing step from a stalled one needs a "
            "staleness/timing signal no recorder provides today, so a merely not-yet link on "
            "an open step is never named as broken -- only a closed step with a missing "
            "declared artifact is. claimed/agent_active/commit have no emitter and remain "
            "unassessed either way; this is not a claim the whole chain is healthy."
        ),
    }


def _step_view(step: Bead) -> dict[str, object]:
    """One step's identity plus its derived completion and evidence (#115)."""
    metadata = _metadata(step)
    completion = _completion_of(metadata)
    actual = _artifacts_of(metadata)
    links = _evidence_links(metadata, step.status, actual)
    broken = _broken_at(step.status, completion)
    return {
        "id": step.id,
        "title": step.title,
        "status": step.status,
        "kind": _text(metadata, "gc.kind"),
        "expected_artifacts": completion["declared"],
        "artifacts": actual,
        "artifacts_present": completion["present"],
        "artifacts_missing": completion["missing"],
        "is_complete": completion["is_complete"],
        "evidence": {"links": list(links), **broken},
    }


def describe(bead: Bead) -> dict[str, object]:
    """The molecule's identity and field map.

    Raises ValueError on a non-root: describing a step as a molecule is the
    conflation this module exists to prevent, and returning a half-populated
    dict would let it pass silently.

    Every value is read or None. Nothing is defaulted, inferred, or synthesised
    -- a root that never recorded a worker reports `worker: None`, which is
    "there is none", not "we did not look".
    """
    if not is_molecule_root(bead):
        raise ValueError(
            f"{bead.id} is not a molecule root: gc.kind is "
            f"{_text(_metadata(bead), 'gc.kind')!r}, expected {ROOT_KIND!r}. "
            f"A step points at its root via {ROOT_POINTER}; it is not one."
        )
    m = _metadata(bead)
    return {
        "id": bead.id,
        # The title is the FORMULA NAME and is identical across every run of
        # that formula -- 45 live roots share `build-basic-briefed`. Carried
        # for display, never as an identifier.
        "title": bead.title,
        "formula": _text(m, "gc.formula_name"),
        "formula_source": _text(m, "gc.formula_source"),
        "contract": _text(m, "gc.formula_contract"),
        "graph_key": _text(m, "gc.graphv2_root_key"),
        "rig": _rig_of(m),
        "routed_to": _text(m, "gc.routed_to"),
        # The root records its own session, so the census's "who" column needs
        # no join against fleet_sessions.
        "worker": _text(m, "gc.session_name"),
        # Three DIFFERENT bead ids ride on one root -- this one, the artifact
        # scope, and the convoy -- and the artifact paths nest two of them.
        # Anything assuming they are one id is wrong on every molecule.
        "artifact_root": _text(m, "gc.var.artifact_root"),
        "convoy": _text(m, "gc.var.convoy_id"),
        "input_convoy": _text(m, "gc.input_convoy_id"),
        "artifacts": _artifacts_of(m),
        "status": bead.status,
        # Whether a deliberate cancel (mc-x06e) has anything to act on: a
        # molecule whose ROOT is already closed/done has finished or been
        # cancelled and there is nothing to stop. The dashboard renders its
        # cancel control only when this is true; the finer "a step is
        # mid-execution, force required" answer comes from the tool's dry run.
        "is_cancellable": not is_closed_status(bead.status),
        "created_at": bead.created_at,
        "updated_at": bead.updated_at,
    }


def describe_with_steps(bead: Bead, beads: Sequence[Bead]) -> dict[str, object]:
    """`describe`, plus the molecule's steps by the reverse index.

    Each step carries its derived `is_complete` and evidence (#115) alongside
    the identity fields `describe_with_steps` has always reported.
    """
    out = describe(bead)
    out["steps"] = [_step_view(s) for s in steps_of(bead.id, beads)]
    return out


# --- the report surface (#111) ----------------------------------------------

#: Molecule roots are `type: task`, and the discriminator is METADATA
#: (`gc.kind`), not type. So there is no narrowing read: the store must be
#: asked for every task and filtered here. `read_beads`' own docstring records
#: what that costs on the largest rig -- 30,364 rows to use 80, 9-11s a view.
#: Declared rather than discovered: a molecules view on a large rig pays a full
#: task read, and the fix would be a `gc.kind` index, not a caller change.
MOLECULE_BEAD_TYPE = "task"


@dataclass(frozen=True)
class MoleculeReport:
    molecules: tuple[dict[str, object], ...]
    diagnostics: tuple[Diagnostic, ...]

    def to_dict(self) -> dict[str, object]:
        return {"molecules": [dict(m) for m in self.molecules]}


def _unreadable(rig_root: Path, error: BaseException) -> Diagnostic:
    return Diagnostic(
        code="MCTL_MOLECULES_STORE_UNREADABLE",
        severity=Severity.ERROR,
        message=f"The bead store could not be read, so NO molecule count is available: {error}",
        rig_path=str(rig_root),
        hint=(
            "This is 'we could not look', not 'there are none'. An empty list "
            "here would be a plausible-empty-result: it would read as a city "
            "with nothing running."
        ),
    )


def build_molecules(
    rig_root: Path,
    *,
    fixture_path: Path | None = None,
    with_steps: bool = False,
) -> MoleculeReport:
    """Every molecule in one rig.

    On an unreadable store this returns NO molecules AND a diagnostic saying
    why -- never a bare empty list. An empty molecules list with no diagnostic
    means 'this rig genuinely has none'; those two must not render alike.
    """
    try:
        beads = read_beads(rig_root, fixture_path=fixture_path, issue_type=MOLECULE_BEAD_TYPE)
    except (BeadReadError, OSError) as error:
        return MoleculeReport(molecules=(), diagnostics=(_unreadable(rig_root, error),))

    roots = roots_in(beads)
    rows = tuple(
        describe_with_steps(root, beads) if with_steps else describe(root) for root in roots
    )
    return MoleculeReport(molecules=rows, diagnostics=())


def build_molecule(
    rig_root: Path,
    molecule_id: str,
    *,
    fixture_path: Path | None = None,
) -> MoleculeReport:
    """One molecule with its steps, or a diagnostic naming why not.

    A missing id and an unreadable store are DIFFERENT failures and get
    different codes: 'no such molecule' is an answer, 'we could not ask' is not.
    """
    try:
        beads = read_beads(rig_root, fixture_path=fixture_path, issue_type=MOLECULE_BEAD_TYPE)
    except (BeadReadError, OSError) as error:
        return MoleculeReport(molecules=(), diagnostics=(_unreadable(rig_root, error),))

    for bead in beads:
        if bead.id == molecule_id and is_molecule_root(bead):
            return MoleculeReport(molecules=(describe_with_steps(bead, beads),), diagnostics=())

    present = any(b.id == molecule_id for b in beads)
    return MoleculeReport(
        molecules=(),
        diagnostics=(
            Diagnostic(
                code="MCTL_MOLECULES_NOT_A_MOLECULE" if present else "MCTL_MOLECULES_NO_SUCH_ID",
                severity=Severity.ERROR,
                message=(
                    f"{molecule_id} exists but is not a molecule root "
                    f"(gc.kind is not {ROOT_KIND!r})"
                    if present
                    else f"No bead {molecule_id} in this rig."
                ),
                rig_path=str(rig_root),
                hint=(
                    "A step points at its root via gc.root_bead_id; it is not one."
                    if present
                    else "Check the rig: a molecule id is rig-scoped."
                ),
            ),
        ),
    )
