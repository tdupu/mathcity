"""The adjudication verdict path: authority is wired, and a reason is optional.

Three defects on the write path, measured against the live tree (mc-qlmh,
mc-9kwwv, mc-ewapk, mc-ba376):

1. `adjudicated_by` was written to bead metadata only, while its three readers
   (`materialize_plan.classify_tier`, `materialize_plan.build_row`,
   `mctl_dashboard/fields.py`) all read brief FRONTMATTER. So no consumer of the
   attribution could ever see it, and `classify_tier` -- which needs
   verdict AND authorizer AND date in the frontmatter -- could never reach
   `TIER_ADJUDICATED` for anything mctl adjudicated. (mc-9kwwv)

2. `mctl briefs adjudicate` had no `--adjudicated-by` flag at all, even though
   the MCP tool `briefs_relay_adjudication` accepts `adjudicated_by` and routes
   through the same core. The `adjudicate-brief` skill prescribes the CLI call,
   so every verdict recorded by following it was unattributable. (mc-ewapk / mc-ba376)

3. The core FATAL'd on an empty `--reason` (`MCTL_MUTATION_REASON_REQUIRED`),
   while the adjudication panel advertises the reason as OPTIONAL and the tool
   schema types it `["string", "null"]`. Taylor, live: "I shouldn't have to
   [give] a reason." The form invited a call the core refused. (mc-qlmh)

These tests exercise the CLI end to end through a subprocess, and read the
persisted artifacts through the core's own parser -- never the process stdout,
which is where the old R6 test found the key it was grepping for inside an
advisory that merely *named* it.
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

LIVE_SHAPED_FRONTMATTER = (
    "---\n"
    "artifact: gh-issue-38\n"
    "status: present-it-pending\n"
    "form: compact\n"
    "---\n"
    "\n"
    "# Inspect open brief\n"
    "\n"
    "Body text.\n"
)


class BriefFixture:
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


@pytest.fixture
def brief_fixture(tmp_path: Path) -> BriefFixture:
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(
        BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track"
    )
    (rig_root / ".beads" / "decisions-track" / "manifest.jsonl").write_text(
        "", encoding="utf-8"
    )
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    fixture = BriefFixture(city_root, rig_root)
    fixture.path.write_text(LIVE_SHAPED_FRONTMATTER, encoding="utf-8")
    fixture.pile_path.write_text(LIVE_SHAPED_FRONTMATTER, encoding="utf-8")
    return fixture


def run_adjudicate(fixture: BriefFixture, *extra: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(fixture.beads_fixture)
    return subprocess.run(
        [
            sys.executable, str(MCTL), "briefs", "adjudicate", fixture.id,
            "--city", str(fixture.city_root), "--rig", "mathcity",
            "--json", *extra,
        ],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )


def read_frontmatter(path: Path) -> dict[str, str]:
    from mctl_core.fields import read_frontmatter as core_read

    return dict(core_read(path.read_text(encoding="utf-8")))


# --- mc-ewapk / mc-ba376: the CLI can name the adjudicator ------------------


def test_cli_adjudicate_accepts_adjudicated_by(brief_fixture: BriefFixture) -> None:
    """`mctl briefs adjudicate --adjudicated-by NAME` is a recognised flag.

    Before the fix argparse rejects the unknown flag with exit 2 and
    'unrecognized arguments'.
    """
    result = run_adjudicate(
        brief_fixture, "--verdict", "approve", "--reason", "ok",
        "--adjudicated-by", "Taylor Dupuy",
    )
    assert result.returncode == 0, result.stderr
    assert "unrecognized arguments" not in result.stderr


# --- mc-9kwwv: authority reaches the surface its readers read ---------------


def test_frontmatter_carries_adjudicated_by_and_at(brief_fixture: BriefFixture) -> None:
    """The attribution and its date land in the brief's own frontmatter."""
    result = run_adjudicate(
        brief_fixture, "--verdict", "approve", "--reason", "ok",
        "--adjudicated-by", "Taylor Dupuy",
    )
    assert result.returncode == 0, result.stderr
    frontmatter = read_frontmatter(brief_fixture.path)
    assert frontmatter.get("adjudicated_by") == "Taylor Dupuy"
    assert frontmatter.get("adjudicated_at"), "an adjudication carries a date"


def test_persisted_authority_is_not_read_from_stdout(brief_fixture: BriefFixture) -> None:
    """R6, non-vacuously: the authority is in the PERSISTED artifacts.

    The old R6 test grepped `result.stdout`, where the
    `MBRF_ADJUDICATOR_UNRECORDED` advisory names `adjudicated_by`; a verdict
    could pass while recording nothing. Here the advisory cannot be present
    (authority IS supplied) and the check reads only stack + decisions.
    """
    result = run_adjudicate(
        brief_fixture, "--verdict", "approve", "--reason", "ok",
        "--adjudicated-by", "Taylor Dupuy",
    )
    assert result.returncode == 0, result.stderr
    stack = brief_fixture.path.read_text(encoding="utf-8")
    decisions = (
        brief_fixture.brief_root / "decisions" / f"{brief_fixture.id}.toml"
    ).read_text(encoding="utf-8")
    assert "adjudicated_by" in f"{stack}\n{decisions}"


def test_classify_tier_reaches_adjudicated(brief_fixture: BriefFixture) -> None:
    """With verdict + authorizer + date now all in frontmatter, the tier is reachable."""
    from mctl_core.materialize_plan import TIER_ADJUDICATED, classify_tier

    result = run_adjudicate(
        brief_fixture, "--verdict", "approve", "--reason", "ok",
        "--adjudicated-by", "Taylor Dupuy",
    )
    assert result.returncode == 0, result.stderr
    frontmatter = read_frontmatter(brief_fixture.path)
    assert classify_tier(frontmatter) == TIER_ADJUDICATED


def test_unattributed_verdict_stays_below_adjudicated(brief_fixture: BriefFixture) -> None:
    """No adjudicator supplied -> no authority forged, so the tier is NOT adjudicated.

    The visibility design (#152): an unattributed verdict is recorded but is not
    dressed as fully adjudicated. `classify_tier` demands an authorizer, so a
    verdict with none stays at `TIER_CLAIMED`, and the advisory fires.
    """
    from mctl_core.materialize_plan import TIER_ADJUDICATED, classify_tier

    result = run_adjudicate(brief_fixture, "--verdict", "approve", "--reason", "ok")
    assert result.returncode == 0, result.stderr
    frontmatter = read_frontmatter(brief_fixture.path)
    assert "adjudicated_by" not in frontmatter
    assert classify_tier(frontmatter) != TIER_ADJUDICATED


# --- mc-qlmh: the reason is optional, to match the panel and the schema -----


def test_adjudicate_without_reason_succeeds(brief_fixture: BriefFixture) -> None:
    """An empty reason is a legal call -- the form must not force what the schema does not.

    Before the fix the core raised MCTL_MUTATION_REASON_REQUIRED (FATAL) on an
    empty reason, so a bare verdict pressed on the panel came back 409.
    """
    result = run_adjudicate(brief_fixture, "--verdict", "approve", "--reason", "")
    assert result.returncode == 0, result.stderr
    assert "MCTL_MUTATION_REASON_REQUIRED" not in result.stderr
    payload = json.loads(result.stdout)
    assert payload.get("applied") is True


def test_adjudicate_with_omitted_reason_succeeds(brief_fixture: BriefFixture) -> None:
    """Omitting --reason entirely is equally legal (the panel omits it too)."""
    result = run_adjudicate(brief_fixture, "--verdict", "revise")
    assert result.returncode == 0, result.stderr
    assert "MCTL_MUTATION_REASON_REQUIRED" not in result.stderr
