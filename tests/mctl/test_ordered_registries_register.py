"""The guard for the register of guards (#201 rule 2).

`assets/mctl/ordered-registries.toml` is itself an `assets/mctl/*.toml` whose
uniqueness is semantic: `registry-merge-gate.py` builds `by_path` as a dict, so
a duplicate `path` entry silently drops one entry's guards and the LAST one
wins. A register that quietly guards less than it claims is worse than no
register, which is the same argument its own scope note makes about
`thresholds.toml`.

Found by the gate itself. On the first merge that brought new files alongside
it, `registry-merge-gate.py --ref origin/main` reported:

    REGISTRY_GATE: UNDETERMINED -- cannot clear this SHA:
        assets/mctl/ordered-registries.toml -- an assets registry this register
        does not name

which is exactly the exit-2 path doing its job on the file that defines it.
"""

from __future__ import annotations

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTER = REPO_ROOT / "assets" / "mctl" / "ordered-registries.toml"


def _entries() -> list[dict]:
    with REGISTER.open("rb") as handle:
        return list(tomllib.load(handle).get("registry", []))


def test_the_register_parses_and_is_not_empty():
    assert REGISTER.is_file(), f"{REGISTER} is missing"
    assert _entries(), "the register declares no registries"


def test_no_duplicate_path():
    """A duplicate `path` silently drops one entry's guards -- the LAST one wins.

    `registry-merge-gate.py` keys `by_path` on `path`, so two entries for one
    file mean the gate runs only one of the two guard sets while reporting that
    the registry is guarded.
    """
    paths = [str(entry.get("path", "")) for entry in _entries()]
    duplicates = sorted({p for p in paths if paths.count(p) > 1})
    assert not duplicates, f"duplicate path entries silently drop guards: {duplicates}"


def test_every_declared_registry_exists_on_disk():
    """A register naming a file that has moved guards nothing and says it does."""
    missing = [
        str(entry["path"])
        for entry in _entries()
        if entry.get("path") and not (REPO_ROOT / str(entry["path"])).is_file()
    ]
    assert not missing, (
        f"declared registries that do not exist: {missing}. Either the file moved "
        "(update the path) or it was retired (drop the entry)."
    )


def test_every_guard_exists_on_disk():
    """A guard that is not there is the gate's exit-2 case, not a pass.

    `registry-merge-gate.py` reports a missing guard as UNDETERMINED rather than
    clean, so this failing here is the earlier, cheaper place to learn it.
    """
    missing: list[str] = []
    for entry in _entries():
        for guard in entry.get("guards", []):
            if not (REPO_ROOT / str(guard)).is_file():
                missing.append(f"{entry.get('path')} -> {guard}")
    assert not missing, f"declared guards that do not exist: {missing}"


def test_every_entry_declares_guards_semantics_and_a_note():
    """An entry with no guard is UNDETERMINED at gate time; catch it here instead.

    `semantics` and `note` are required because the register's whole argument for
    being hand-maintained is that a human checked WHY the file belongs. An entry
    with neither is an assertion nobody stands behind.
    """
    incomplete: list[str] = []
    for entry in _entries():
        path = str(entry.get("path", "<no path>"))
        if not entry.get("guards"):
            incomplete.append(f"{path}: no guards")
        if not str(entry.get("semantics", "")).strip():
            incomplete.append(f"{path}: no semantics")
        if not str(entry.get("note", "")).strip():
            incomplete.append(f"{path}: no note")
    assert not incomplete, f"incomplete register entries: {incomplete}"


def test_the_register_declares_itself():
    """The register is an assets/mctl/*.toml whose uniqueness is semantic.

    Leaving itself out is the shape `test_tool_registries_are_enumerated`'s own
    docstring warns about: "an authoritative-looking list that is quietly
    incomplete". The gate flags an undeclared assets registry as exit 2, and the
    register is not exempt from its own rule.
    """
    declared = {str(entry.get("path", "")) for entry in _entries()}
    assert "assets/mctl/ordered-registries.toml" in declared, (
        "the register must declare itself; the gate reports an undeclared "
        "assets/mctl/*.toml as UNDETERMINED, including this one"
    )
