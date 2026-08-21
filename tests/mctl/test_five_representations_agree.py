"""RED BY DESIGN — do not "fix" these tests. They pin a live gap.

`test_adjudication_writes_frontmatter.py` pins four representations: the bead,
`decisions/<id>.toml`, `stack/.index.jsonl`, and the brief file's frontmatter.
There is a fifth and nothing tests it: the **decisions-track manifest row**.

`mctl briefs adjudicate` does not write it. The `adjudicate-brief` skill does,
in place, after mctl returns. So the manifest agrees only when a human runs the
skill; adjudicate from the dashboard or MCP and it is left behind.

These fail today. That is the point -- they pin the gap before the fix, so the
fix has something to turn green rather than arriving with a claim that it works.

Two things had to be established before this could be written honestly, and
both constrain the fixture:

**1. A non-terminal manifest row blocks adjudication entirely.** B2.10 fails
closed: `MCTL_DECISIONS_TRACK_MIGRATION_BLOCKED`, and the command refuses
before writing anything. A first draft seeded the row `ready-for-adjudication`
and went red on the invocation rather than the assertion -- a test that would
have looked like it pinned the missing write and actually pinned a policy gate.

So the row must be seeded **terminal**, which in turn makes any assertion about
the manifest *status* vacuous: it reads "adjudicated" before the command runs.
The **verdict** is the part adjudication would have to add, so that is what
these assert. There is no way to express "adjudication moves a pending manifest
row" as a test, because a pending manifest row is exactly what B2.10 refuses to
adjudicate.

**2. The terminal predicate is prefix-based** -- `_is_terminal_status` in
`redundant_state.py` matches `startswith` against TERMINAL_STATUS_PREFIXES, so
the compound statuses the live corpus uses (`adjudicated:ratify(...)`,
`adjudicated:approve(bug-convoy)`) read as terminal. Verified empirically, not
assumed.

That was **not** true when these tests were written. The predicate was an exact
match against a set, so every compound status read as NON-terminal and tripped
B2.10 per-brief -- 27 of 83 untitled pending rows carried one. The same mismatch
made a decisions-track migration target 42 of 85 rows and report completion.
cozy replaced it with a single prefix-based definition (`e207e2a`, now on main).

Recorded because the earlier revision of this docstring asserted the exact-match
rule as current, and by then it was not. The fixture still seeds bare
`"adjudicated"`, which is terminal under either rule, so nothing here depends on
which one is in force.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

MCTL = SCRIPTS_ROOT / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"

BRIEF_ID = "mc-open"

FRONTMATTER = (
    "---\n"
    "artifact: gh-issue-38\n"
    "status: ready-for-adjudication\n"
    "track: decisions-to-briefs\n"
    "---\n"
    "\n"
    "# Inspect open brief\n"
    "\n"
    "Body text.\n"
)

#: Seeded **terminal**, and that is forced rather than chosen -- see the module
#: docstring. A non-terminal row trips B2.10 and adjudication never runs.
#:
#: `"adjudicated"` bare, not `"adjudicated:approve"`: the terminal test is an
#: exact match against {closed, done, terminal, adjudicated, rejected, moot}
#: (`redundant_state.py:57`), so every compound status the live corpus actually
#: uses -- `adjudicated:ratify(...)`, `adjudicated:approve(bug-convoy)` -- reads
#: as NON-terminal and trips the gate.
MANIFEST_ROW = {
    "n": 1,
    "slug": BRIEF_ID,
    "status": "adjudicated",
    "path": f"{BRIEF_ID}.md",
}


class Fixture:
    def __init__(self, city_root: Path, rig_root: Path):
        self.city_root = city_root
        self.rig_root = rig_root
        self.id = BRIEF_ID

    @property
    def brief_root(self) -> Path:
        return self.rig_root / ".beads" / "briefs"

    @property
    def path(self) -> Path:
        return self.brief_root / "stack" / f"{BRIEF_ID}.md"

    @property
    def pile_path(self) -> Path:
        return self.brief_root / ".pile" / f"{BRIEF_ID}.md"

    @property
    def beads_fixture(self) -> Path:
        return self.rig_root / ".beads" / "issues.jsonl"

    @property
    def manifest(self) -> Path:
        return self.rig_root / ".beads" / "decisions-track" / "manifest.jsonl"


@pytest.fixture
def fixture(tmp_path: Path) -> Fixture:
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(
        BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track"
    )
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")

    result = Fixture(city_root, rig_root)
    result.path.write_text(FRONTMATTER, encoding="utf-8")
    result.pile_path.write_text(FRONTMATTER, encoding="utf-8")
    result.manifest.write_text(json.dumps(MANIFEST_ROW) + "\n", encoding="utf-8")

    # The join is read off the migration's own record -- `legacy_n` on the
    # stack index row -- and is deliberately NOT inferred from the slug, because
    # a second identity rule would drift from the first the moment a slug was
    # edited. A fixture that seeds a manifest row without it constructs a state
    # the migration never produces, and the writer correctly declines to guess.
    index = result.brief_root / "stack" / ".index.jsonl"
    rows = [json.loads(line) for line in index.read_text(encoding="utf-8").splitlines() if line.strip()]
    for row in rows:
        if row.get("slug") == BRIEF_ID:
            row["legacy_n"] = MANIFEST_ROW["n"]
            row["legacy_source"] = BRIEF_ID
    index.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return result


def adjudicate(fixture: Fixture, *, verdict: str = "approve", reason: str = "ok") -> None:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(fixture.beads_fixture)
    result = subprocess.run(
        [
            sys.executable, str(MCTL), "briefs", "adjudicate", fixture.id,
            "--city", str(fixture.city_root), "--rig", "mathcity",
            "--verdict", verdict, "--reason", reason, "--json",
        ],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )
    assert result.returncode == 0, result.stderr


def manifest_row(fixture: Fixture) -> dict[str, object]:
    rows = [
        json.loads(line)
        for line in fixture.manifest.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return next(row for row in rows if row.get("slug") == fixture.id)


def bead_status(fixture: Fixture) -> str:
    rows = [
        json.loads(line)
        for line in fixture.beads_fixture.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return str(next(row for row in rows if row["id"] == fixture.id)["status"])


def frontmatter_status(fixture: Fixture) -> str:
    from mctl_core.fields import read_frontmatter

    return str(dict(read_frontmatter(fixture.path.read_text(encoding="utf-8")))["status"])


def index_row_status(fixture: Fixture) -> str:
    rows = [
        json.loads(line)
        for line in (fixture.brief_root / "stack" / ".index.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    return str(next(row for row in rows if row.get("slug") == fixture.id)["status"])


def decision_toml_exists(fixture: Fixture) -> bool:
    return (fixture.brief_root / "decisions" / f"{fixture.id}.toml").is_file()


# ---------------------------------------------------------------------------
# The fifth representation. RED.
# ---------------------------------------------------------------------------


def test_the_manifest_row_records_the_verdict(fixture: Fixture):
    """`what` was decided, not merely `that` something was."""
    adjudicate(fixture, verdict="approve")
    assert manifest_row(fixture).get("verdict") == "approve"


def test_all_five_representations_agree(fixture: Fixture):
    """The whole contract in one assertion set.

    This is lumby's acceptance criterion stated as a test: Taylor adjudicates
    and every representation agrees afterwards. Four of the five already do.
    """
    adjudicate(fixture, verdict="approve")

    disagreements = []
    if bead_status(fixture) != "closed":
        disagreements.append(f"bead={bead_status(fixture)}")
    if not decision_toml_exists(fixture):
        disagreements.append("decisions/<id>.toml missing")
    if not index_row_status(fixture).startswith("adjudicated"):
        disagreements.append(f"index={index_row_status(fixture)}")
    if not frontmatter_status(fixture).startswith("adjudicated"):
        disagreements.append(f"frontmatter={frontmatter_status(fixture)}")
    # Asserting the manifest *status* here would be vacuous: B2.10 forces the
    # row to be seeded terminal, so it reads "adjudicated" before the command
    # runs. The verdict is the part adjudication would have to add.
    if manifest_row(fixture).get("verdict") is None:
        disagreements.append("manifest carries no verdict")

    assert not disagreements, (
        "representations disagree after adjudication: " + ", ".join(disagreements)
    )
