"""A three-rig city fixture: two readable, one that cannot be read.

Shared by the cross-rig read tests and the city-wide dashboard tests, because
both need the same shape and duplicating it would let the two drift into
testing different cities.

The three rigs are deliberately unlike each other:

`mathcity`       readable, artifact state trustworthy.
`gascity_packs`  readable, artifact state NOT trustworthy -- its pile carries
                 the bead id in `artifact:` frontmatter, the live convention
                 Q5 describes. This is what makes "trust differs per rig" a
                 fact the tests can assert rather than a claim.
`sick`           unreadable: its bead store is pointed at a path that does not
                 exist, so resolving its context fails FATAL. Every degraded
                 -rig assertion runs against this one.

Each rig gets its OWN bead store through the per-rig `MCTL_BEADS_FIXTURE_<rig>`
override. A single shared store would make every rig report the same briefs,
and an aggregation that double-counted or dropped a rig would still pass.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil


FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"

READABLE_RIGS = ("mathcity", "gascity_packs")
SICK_RIG = "sick"
ALL_RIGS = (*READABLE_RIGS, SICK_RIG)

CITY_TOML = """\
[defaults.rig.imports.mathcity]
source = "../source_checkout"

[[rigs]]
name = "mathcity"
db = "fixture_mathcity"

[[rigs]]
name = "gascity_packs"
db = "fixture_gascity_packs"

[[rigs]]
name = "sick"
db = "fixture_sick"
"""

#: Bead ids in the shipped fixture all start `mc-`; the second rig gets its own
#: prefix so a row's rig is provable from the row itself.
PREFIXES = {"mathcity": "mc-", "gascity_packs": "gs-"}


@dataclass(frozen=True)
class MultiRigCity:
    city_root: Path
    rig_roots: dict[str, Path]
    env: dict[str, str]

    def rig_root(self, rig: str) -> Path:
        return self.rig_roots[rig]

    def beads_path(self, rig: str) -> Path:
        return self.rig_roots[rig] / ".beads" / "issues.jsonl"


def _populate(rig_root: Path, prefix: str) -> None:
    beads = rig_root / ".beads"
    shutil.copytree(BRIEF_STATE / "briefs", beads / "briefs")
    shutil.copytree(BRIEF_STATE / "decisions-track", beads / "decisions-track")
    beads.mkdir(parents=True, exist_ok=True)
    (beads / "issues.jsonl").write_text(
        (BRIEF_STATE / "beads.jsonl").read_text(encoding="utf-8").replace("mc-", prefix),
        encoding="utf-8",
    )
    if prefix == "mc-":
        return
    for path in sorted(beads.rglob("*")):
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        if "mc-" in text:
            path.write_text(text.replace("mc-", prefix), encoding="utf-8")
        if path.name.startswith("mc-"):
            path.rename(path.with_name(prefix + path.name[len("mc-") :]))


def build(tmp_path: Path) -> MultiRigCity:
    """Build the three-rig city under `tmp_path` and return how to address it."""
    city_root = tmp_path / "city_root"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    (city_root / "city.toml").write_text(CITY_TOML, encoding="utf-8")

    rig_roots = {rig: city_root / rig for rig in ALL_RIGS}
    env: dict[str, str] = {}
    for rig in READABLE_RIGS:
        _populate(rig_roots[rig], PREFIXES[rig])
        env[f"MCTL_BEADS_FIXTURE_{rig}"] = str(rig_roots[rig] / ".beads" / "issues.jsonl")

    # Q5's live pile convention, in ONE rig only: the bead id lives in
    # `artifact:` frontmatter rather than the filename, so `<bead_id>.md`
    # cannot find a file that is sitting right there. That makes this rig's
    # artifact state untrusted while the other rig's stays trusted.
    pile = rig_roots["gascity_packs"] / ".beads" / "briefs" / ".pile"
    (pile / "07-inspect-open-brief.md").write_text(
        "---\nartifact: gs-open\n---\n\n# Inspect open brief\n", encoding="utf-8"
    )

    # The unreadable rig: a bead store path that is not a file. Resolving its
    # context raises FATAL before any read is attempted, which is the closest
    # deterministic stand-in for "the store is unreachable".
    rig_roots[SICK_RIG].mkdir(parents=True, exist_ok=True)
    env[f"MCTL_BEADS_FIXTURE_{SICK_RIG}"] = str(tmp_path / "no-such-store.jsonl")

    return MultiRigCity(city_root=city_root, rig_roots=rig_roots, env=env)
