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

from typing import Iterable, Mapping, Sequence

from .beads import Bead

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
        "created_at": bead.created_at,
        "updated_at": bead.updated_at,
    }


def describe_with_steps(bead: Bead, beads: Sequence[Bead]) -> dict[str, object]:
    """`describe`, plus the molecule's steps by the reverse index."""
    out = describe(bead)
    out["steps"] = [
        {"id": s.id, "title": s.title, "status": s.status, "kind": _text(_metadata(s), "gc.kind")}
        for s in steps_of(bead.id, beads)
    ]
    return out
