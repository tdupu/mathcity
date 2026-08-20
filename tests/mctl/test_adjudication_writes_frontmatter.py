"""Adjudication must leave all four of a brief's representations agreeing.

`mctl` owns the bead, `decisions/<id>.toml` and `stack/.index.jsonl`. The
brief file's own frontmatter `status:` was owned by nobody, so a brief could
be closed on the bead, recorded in the decision TOML, marked adjudicated in
the index, and still read `present-it-pending` in the document the
presentation queue actually renders. Measured on the live city (GitHub #77):
35 of 88 index rows pointed at a brief whose own frontmatter already read
`adjudicated*`.

These tests pin the write side of POLICY B2.8a: the bead is a serial number,
the state lives in the file, so a write path that targets only the serial
number leaves the state behind.
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

# The live corpus' own header shape: an `artifact:` link, a `status:` the
# queue reads, and a tail of producer keys no core module knows about. The
# unknown keys are the point -- a writer that re-serialised the block would
# reorder or drop them.
LIVE_SHAPED_FRONTMATTER = (
    "---\n"
    "artifact: gh-issue-38\n"
    "status: present-it-pending\n"
    "form: compact\n"
    "track: decisions-to-briefs\n"
    "no_brainer_confidence: 0.95\n"
    "unlock_count: 7\n"
    "deposited_by: fdd99db3 (outside session)\n"
    "---\n"
    "\n"
    "# Inspect open brief\n"
    "\n"
    "Body text that must not move.\n"
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
        """The stack document the presentation queue renders."""
        return self.brief_root / "stack" / f"{BRIEF_ID}.md"

    @property
    def pile_path(self) -> Path:
        return self.brief_root / ".pile" / f"{BRIEF_ID}.md"

    @property
    def beads_fixture(self) -> Path:
        return self.rig_root / ".beads" / "issues.jsonl"


def _runtime_fixture(tmp_path: Path) -> BriefFixture:
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
    return BriefFixture(city_root, rig_root)


@pytest.fixture
def brief_fixture(tmp_path: Path) -> BriefFixture:
    fixture = _runtime_fixture(tmp_path)
    fixture.path.write_text(LIVE_SHAPED_FRONTMATTER, encoding="utf-8")
    fixture.pile_path.write_text(LIVE_SHAPED_FRONTMATTER, encoding="utf-8")
    return fixture


def adjudicate(
    fixture: BriefFixture, *, verdict: str, reason: str, apply: bool = True
) -> dict[str, object]:
    args = [
        "briefs",
        "adjudicate",
        fixture.id,
        "--city",
        str(fixture.city_root),
        "--rig",
        "mathcity",
        "--verdict",
        verdict,
        "--reason",
        reason,
        "--json",
    ]
    if not apply:
        args.append("--dry-run")
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(fixture.beads_fixture)
    result = subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def read_frontmatter(path: Path) -> dict[str, str]:
    """Read through the core's one parser, not a second one written here."""
    from mctl_core.fields import read_frontmatter as core_read

    return dict(core_read(path.read_text(encoding="utf-8")))


def bead_status(fixture: BriefFixture) -> str:
    rows = {
        json.loads(line)["id"]: json.loads(line)
        for line in fixture.beads_fixture.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    return str(rows[fixture.id]["status"])


def decision_toml_exists(fixture: BriefFixture) -> bool:
    return (fixture.brief_root / "decisions" / f"{fixture.id}.toml").is_file()


def index_row_status(fixture: BriefFixture) -> str:
    rows = [
        json.loads(line)
        for line in (fixture.brief_root / "stack" / ".index.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    row = next(row for row in rows if row.get("slug") == fixture.id)
    return str(row["status"])


def test_all_four_representations_agree_after_adjudication(brief_fixture: BriefFixture):
    adjudicate(brief_fixture, verdict="approve", reason="ok", apply=True)

    assert bead_status(brief_fixture) == "closed"
    assert decision_toml_exists(brief_fixture)
    assert index_row_status(brief_fixture).startswith("adjudicated")
    assert read_frontmatter(brief_fixture.path)["status"].startswith("adjudicated")


def test_adjudication_writes_the_briefs_own_frontmatter(brief_fixture: BriefFixture):
    adjudicate(brief_fixture, verdict="approve", reason="ok", apply=True)

    frontmatter = read_frontmatter(brief_fixture.path)
    assert frontmatter["status"].startswith("adjudicated")
    assert frontmatter["verdict"] == "approve"


def test_every_cache_document_the_brief_owns_is_written(brief_fixture: BriefFixture):
    """A second copy left at the old status is the same drift, one directory over."""
    adjudicate(brief_fixture, verdict="approve", reason="ok", apply=True)

    assert read_frontmatter(brief_fixture.pile_path)["status"].startswith("adjudicated")


def test_the_frontmatter_write_appears_in_the_dry_run_plan(brief_fixture: BriefFixture):
    payload = adjudicate(brief_fixture, verdict="approve", reason="ok", apply=False)

    kinds = {update["kind"] for update in payload["effect_plan"]["cache_updates"]}
    assert "brief_frontmatter" in kinds
    assert read_frontmatter(brief_fixture.path)["status"] == "present-it-pending"


def test_unknown_keys_keep_their_order_and_spelling(brief_fixture: BriefFixture):
    before = read_frontmatter(brief_fixture.path)

    adjudicate(brief_fixture, verdict="approve", reason="ok", apply=True)

    after = read_frontmatter(brief_fixture.path)
    untouched = [key for key in before if key not in {"status", "verdict"}]
    assert [key for key in after if key in untouched] == untouched
    for key in untouched:
        assert after[key] == before[key]


def test_the_body_is_left_byte_for_byte(brief_fixture: BriefFixture):
    original = brief_fixture.path.read_text(encoding="utf-8")
    body = original.split("\n---\n", 1)[1]

    adjudicate(brief_fixture, verdict="approve", reason="ok", apply=True)

    assert brief_fixture.path.read_text(encoding="utf-8").split("\n---\n", 1)[1] == body


def test_only_the_lines_we_set_change(brief_fixture: BriefFixture):
    before = brief_fixture.path.read_text(encoding="utf-8").splitlines()

    adjudicate(brief_fixture, verdict="approve", reason="ok", apply=True)

    after = brief_fixture.path.read_text(encoding="utf-8").splitlines()
    changed = [line for line in after if line not in before]
    # `status` is rewritten in place and `verdict` is appended; nothing else moves.
    assert sorted(changed) == ["status: adjudicated", "verdict: approve"]


def test_the_write_is_idempotent(tmp_path: Path):
    from mctl_core.effects import _update_brief_frontmatter

    path = tmp_path / "brief.md"
    path.write_text(LIVE_SHAPED_FRONTMATTER, encoding="utf-8")
    fields = {"status": "adjudicated", "verdict": "approve"}

    _update_brief_frontmatter(path, fields)
    once = path.read_text(encoding="utf-8")
    _update_brief_frontmatter(path, fields)

    assert path.read_text(encoding="utf-8") == once


def test_an_existing_key_is_replaced_not_duplicated(tmp_path: Path):
    from mctl_core.effects import _update_brief_frontmatter

    path = tmp_path / "brief.md"
    path.write_text(
        "---\nstatus: ready\nverdict: revise\n---\n\nbody\n", encoding="utf-8"
    )

    _update_brief_frontmatter(path, {"status": "adjudicated", "verdict": "approve"})

    text = path.read_text(encoding="utf-8")
    assert text.count("status:") == 1
    assert text.count("verdict:") == 1
    assert "verdict: approve" in text


def test_a_value_a_yaml_loader_would_reject_survives_untouched(tmp_path: Path):
    """Live files carry `needs-revision(check-zero:partial;option-A)` and `[236]`."""
    from mctl_core.effects import _update_brief_frontmatter

    path = tmp_path / "brief.md"
    path.write_text(
        "---\nrelates: [236]\nnote: needs-revision(check-zero:partial;option-A)\n---\nbody\n",
        encoding="utf-8",
    )

    _update_brief_frontmatter(path, {"status": "adjudicated"})

    text = path.read_text(encoding="utf-8")
    assert "relates: [236]" in text
    assert "note: needs-revision(check-zero:partial;option-A)" in text


def test_an_empty_frontmatter_block_gains_the_keys(tmp_path: Path):
    from mctl_core.effects import _update_brief_frontmatter

    path = tmp_path / "brief.md"
    path.write_text("---\n---\n\nbody\n", encoding="utf-8")

    _update_brief_frontmatter(path, {"status": "adjudicated"})

    assert path.read_text(encoding="utf-8") == "---\nstatus: adjudicated\n---\n\nbody\n"


def test_a_brief_with_no_frontmatter_warns_and_does_not_sink_the_adjudication(
    tmp_path: Path,
):
    fixture = _runtime_fixture(tmp_path)
    fixture.path.write_text("# no header at all\n\nbody\n", encoding="utf-8")
    fixture.pile_path.write_text("# no header at all\n\nbody\n", encoding="utf-8")
    original = fixture.path.read_text(encoding="utf-8")

    payload = adjudicate(fixture, verdict="approve", reason="ok", apply=True)

    assert payload["applied"] is True
    assert bead_status(fixture) == "closed"
    assert index_row_status(fixture).startswith("adjudicated")
    codes = {
        (diagnostic["code"], diagnostic["severity"])
        for diagnostic in payload["diagnostics"]
    }
    assert ("MCTL_BRIEF_FRONTMATTER_UNWRITABLE", "WARN") in codes
    assert fixture.path.read_text(encoding="utf-8") == original


def test_an_unterminated_frontmatter_block_is_left_alone(tmp_path: Path):
    """A header that never closes is not a header we can rewrite faithfully."""
    from mctl_core.effects import BriefFrontmatterUnwritable, _update_brief_frontmatter

    path = tmp_path / "brief.md"
    original = "---\nstatus: ready\n\nbody with no closing fence\n"
    path.write_text(original, encoding="utf-8")

    with pytest.raises(BriefFrontmatterUnwritable):
        _update_brief_frontmatter(path, {"status": "adjudicated"})

    assert path.read_text(encoding="utf-8") == original


def test_a_frontmatter_write_failure_leaves_the_file_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from mctl_core import effects

    path = tmp_path / "brief.md"
    path.write_text(LIVE_SHAPED_FRONTMATTER, encoding="utf-8")

    def boom(*args, **kwargs):
        raise KeyboardInterrupt("interrupted mid-write")

    monkeypatch.setattr(effects.os, "replace", boom)
    with pytest.raises(KeyboardInterrupt):
        effects._update_brief_frontmatter(path, {"status": "adjudicated"})

    assert path.read_text(encoding="utf-8") == LIVE_SHAPED_FRONTMATTER
