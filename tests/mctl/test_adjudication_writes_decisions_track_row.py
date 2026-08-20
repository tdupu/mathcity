"""Adjudication must leave EVERY representation of a brief agreeing.

`af90cbc` (#77) closed the fourth: the brief file's own frontmatter. A fifth
was still owned by nobody -- the legacy decisions-track manifest row -- and it
was not unowned by accident. `adjudicate-brief` step 2b performed that write
itself, with a `sed -i` and a heredoc, *after* calling `mctl`. So a verdict
recorded from the dashboard, the CLI or the MCP ran `mctl` and not the skill,
and the row kept saying `ready-for-adjudication` while the bead said closed.
Measured on the live city 2026-08-04: 17 briefs read `adjudicated` in the
manifest while their files read otherwise.

The decision record is **split by track**, and these tests keep that split:

    stack-track brief   -> .beads/briefs/decisions/<bead_id>.toml
    decisions-track     -> a row in .beads/decisions-track/manifest.jsonl

A stack-track brief has no manifest row and must never be given one -- that
would invent a representation rather than sync an existing one. Absence is the
majority path, and it is silent. Every test below states which lane it
exercises.
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

#: The legacy-lane brief, shaped like the live `he-ckilh` row: the index row's
#: `slug` is the LEGACY slug, the bead id appears only in `source` and in the
#: document filename, and `legacy_n` names the manifest row. That shape is what
#: the join has to reach; a fixture whose slug happened to equal the bead id
#: would pass without exercising it.
LEGACY_ID = "mc-legacy"
LEGACY_DOC = "mc-legacy-dispatch-gate.md"
LEGACY_N = 79

#: The stack-track brief already in the shared fixture. No legacy origin.
STACK_ID = "mc-open"

FRONTMATTER = (
    "---\n"
    "artifact: gh-issue-38\n"
    "status: ready-for-adjudication\n"
    "form: full\n"
    "track: decisions-to-briefs\n"
    "---\n"
    "\n"
    "# Brief body that must not move.\n"
)

#: The end-to-end manifest: rows before and after the target, a row whose `n`
#: merely *contains* the target's digits, a blank line, and a row already
#: escaped the way `json.dumps` escapes it. All shapes the live corpus holds.
#:
#: Deliberately well-formed. A line no JSON parser accepts makes B2.10 fail
#: closed for the whole rig (`redundant_state._read_jsonl_strict` returns a
#: parse error, and `_legacy_gate_diagnostics` then blocks every mutation
#: regardless of which brief is named), and the live manifest's 204 rows all
#: parse. Malformed-line preservation is pinned at the unit level below, where
#: it can be exercised without standing in front of the migration gate.
MANIFEST_LINES = [
    '{"n": 1, "slug": "gh-auth-login", "source_bead": null, "status": "present-it-pending"}',
    '{"n": 790, "slug": "not-the-target", "status": "ready"}',
    '{"n": 79, "slug": "mc-legacy-dispatch-gate", "source_bead": "none", "form": "full",'
    ' "track": "hecke-cleanup", "status": "ready-for-adjudication", "unlock_count": 2}',
    "",
    '{"n": 8, "slug": "sigma18", "status": "adjudicated", "verdict": "D \\u2014 defer"}',
]
MANIFEST = "\n".join(MANIFEST_LINES) + "\n"

#: The same file with a line no parser will accept, for the writer's own tests.
RAW_MANIFEST = "\n".join(
    MANIFEST_LINES[:3]
    + ["", "{ this line is not JSON and must survive anyway"]
    + MANIFEST_LINES[4:]
) + "\n"


class Fixture:
    def __init__(self, city_root: Path, rig_root: Path, brief_id: str):
        self.city_root = city_root
        self.rig_root = rig_root
        self.id = brief_id

    @property
    def brief_root(self) -> Path:
        return self.rig_root / ".beads" / "briefs"

    @property
    def manifest(self) -> Path:
        return self.rig_root / ".beads" / "decisions-track" / "manifest.jsonl"

    @property
    def beads_fixture(self) -> Path:
        return self.rig_root / ".beads" / "issues.jsonl"

    @property
    def doc(self) -> Path:
        name = LEGACY_DOC if self.id == LEGACY_ID else f"{self.id}.md"
        return self.brief_root / "stack" / name


def _build(tmp_path: Path, brief_id: str, manifest: str = MANIFEST) -> Fixture:
    """The shared fixture, plus a legacy-lane brief built in the tmp copy.

    Nothing is added to the checked-in fixture files: other suites assert on
    their populations, and a brief added there to serve this one would change
    counts three directories away.
    """
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(
        BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track"
    )
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")

    fixture = Fixture(city_root, rig_root, brief_id)
    fixture.manifest.write_text(manifest, encoding="utf-8")

    # The legacy-lane bead, its document, its decision cache and its index row.
    with fixture.beads_fixture.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "id": LEGACY_ID,
                    "title": "Migrated legacy brief",
                    "status": "open",
                    "issue_type": "decision",
                    "labels": ["brief-open"],
                    "dependencies": [{"issue_id": "mc-source", "type": "blocks"}],
                    "created_at": "2026-08-10T12:00:00Z",
                    "updated_at": "2026-08-11T12:00:00Z",
                }
            )
            + "\n"
        )
    (fixture.brief_root / "decisions" / f"{LEGACY_ID}.toml").write_text(
        f'brief_id = "{LEGACY_ID}"\ntitle = "Migrated legacy brief"\nstatus = "open"\n',
        encoding="utf-8",
    )
    index = fixture.brief_root / "stack" / ".index.jsonl"
    with index.open("a", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "slug": "mc-legacy-dispatch-gate",
                    "source": LEGACY_ID,
                    "path": f".beads/briefs/stack/{LEGACY_DOC}",
                    "legacy_n": LEGACY_N,
                    "legacy_source": f"decisions-track/{LEGACY_N}-mc-legacy-dispatch-gate-brief.md",
                    "unlock_count": 5,
                }
            )
            + "\n"
        )
    for path in (
        fixture.brief_root / "stack" / LEGACY_DOC,
        fixture.brief_root / ".pile" / LEGACY_DOC,
        fixture.brief_root / "stack" / f"{STACK_ID}.md",
        fixture.brief_root / ".pile" / f"{STACK_ID}.md",
    ):
        path.write_text(FRONTMATTER, encoding="utf-8")
    return fixture


@pytest.fixture
def legacy(tmp_path: Path) -> Fixture:
    return _build(tmp_path, LEGACY_ID)


@pytest.fixture
def stack_track(tmp_path: Path) -> Fixture:
    return _build(tmp_path, STACK_ID)


def adjudicate(
    fixture: Fixture, *, verdict: str = "approve", reason: str = "ok", apply: bool = True
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
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout)


def read_frontmatter(path: Path) -> dict[str, str]:
    from mctl_core.fields import read_frontmatter as core_read

    return dict(core_read(path.read_text(encoding="utf-8")))


def bead_status(fixture: Fixture) -> str:
    rows = [
        json.loads(line)
        for line in fixture.beads_fixture.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    return str(next(row for row in rows if row["id"] == fixture.id)["status"])


def decision_toml_exists(fixture: Fixture) -> bool:
    return (fixture.brief_root / "decisions" / f"{fixture.id}.toml").is_file()


def index_row(fixture: Fixture) -> dict[str, object]:
    rows = [
        json.loads(line)
        for line in (fixture.brief_root / "stack" / ".index.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
        if line.strip()
    ]
    name = fixture.doc.name
    return next(
        row
        for row in rows
        if row.get("slug") == fixture.id or Path(str(row.get("path", ""))).name == name
    )


def manifest_row(fixture: Fixture, n: int = LEGACY_N) -> dict[str, object]:
    for line in fixture.manifest.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if row.get("n") == n:
            return row
    raise AssertionError(f"no manifest row n={n}")


# ---------------------------------------------------------------------------
# The acceptance test for the whole objective: every representation agrees.
# LANE: legacy decisions-track.
# ---------------------------------------------------------------------------


def test_every_representation_agrees_after_adjudication(legacy: Fixture):
    adjudicate(legacy, verdict="approve", reason="ok")

    assert bead_status(legacy) == "closed"
    assert decision_toml_exists(legacy)
    assert str(index_row(legacy)["status"]).startswith("adjudicated")
    assert read_frontmatter(legacy.doc)["status"].startswith("adjudicated")
    row = manifest_row(legacy)
    assert str(row["status"]).startswith("adjudicated")
    assert row["verdict"] == "approve"


def test_the_manifest_row_carries_all_four_fields(legacy: Fixture):
    """LANE: legacy. The four keys the skill's heredoc wrote, and no others."""
    adjudicate(legacy, verdict="reject", reason="not now: colons, and a comma")

    row = manifest_row(legacy)
    assert row["status"] == "adjudicated"
    assert row["verdict"] == "reject"
    assert row["verdict_note"] == "not now: colons, and a comma"
    # A date, matching the corpus; 99 of 101 live timestamped rows are dates.
    assert len(str(row["adjudicated_at"])) == 10


def test_the_manifest_write_appears_in_the_dry_run_plan(legacy: Fixture):
    """LANE: legacy. A plan that would touch row 79 has to say so."""
    payload = adjudicate(legacy, apply=False)

    updates = payload["effect_plan"]["cache_updates"]
    planned = [item for item in updates if item["kind"] == "decisions_track_row"]
    assert len(planned) == 1
    assert planned[0]["row_key"] == str(LEGACY_N)
    # Dry run means dry.
    assert manifest_row(legacy)["status"] == "ready-for-adjudication"


# ---------------------------------------------------------------------------
# LANE: stack-track. The majority path -- no row, no write, no warning.
# ---------------------------------------------------------------------------


def test_a_stack_track_brief_is_given_no_manifest_row(stack_track: Fixture):
    before = stack_track.manifest.read_text(encoding="utf-8")

    payload = adjudicate(stack_track)

    assert payload["applied"] is True
    assert bead_status(stack_track) == "closed"
    assert read_frontmatter(stack_track.doc)["status"].startswith("adjudicated")
    # The manifest is not merely unchanged in content -- it is untouched.
    assert stack_track.manifest.read_text(encoding="utf-8") == before


def test_a_stack_track_brief_plans_no_manifest_update(stack_track: Fixture):
    payload = adjudicate(stack_track, apply=False)

    kinds = {item["kind"] for item in payload["effect_plan"]["cache_updates"]}
    assert "decisions_track_row" not in kinds


def test_a_stack_track_brief_does_not_warn(stack_track: Fixture):
    """Absence is the normal case, so it must not spend a WARN.

    A warning on the majority path is a warning operators learn to ignore.
    """
    payload = adjudicate(stack_track)

    codes = {diagnostic["code"] for diagnostic in payload["diagnostics"]}
    assert "MCTL_DECISIONS_TRACK_ROW_UNWRITABLE" not in codes


def test_adjudication_succeeds_with_no_manifest_file_at_all(tmp_path: Path):
    """LANE: stack-track, on a rig that never had a decisions-track tree."""
    fixture = _build(tmp_path, STACK_ID)
    fixture.manifest.unlink()

    payload = adjudicate(fixture)

    assert payload["applied"] is True
    assert bead_status(fixture) == "closed"
    assert str(index_row(fixture)["status"]).startswith("adjudicated")


# ---------------------------------------------------------------------------
# Byte preservation, idempotence, and the shapes the corpus actually holds.
# LANE: legacy.
# ---------------------------------------------------------------------------


def test_every_non_target_line_is_byte_identical(legacy: Fixture):
    """204 rows, one verdict: 203 lines must come out exactly as they went in."""
    before = legacy.manifest.read_text(encoding="utf-8").split("\n")

    adjudicate(legacy)

    after = legacy.manifest.read_text(encoding="utf-8").split("\n")
    assert len(after) == len(before)
    target = next(
        index
        for index, line in enumerate(before)
        if line.strip().startswith('{"n": 79,')
    )
    for index, (was, now) in enumerate(zip(before, after)):
        if index == target:
            assert was != now, "the target row was not rewritten"
            continue
        assert now == was, f"line {index} changed: {was!r} -> {now!r}"


def test_a_malformed_line_survives_verbatim(tmp_path: Path):
    """Unit level: B2.10 refuses the whole rig if the manifest has one.

    It still has to be right. `_update_stack_index`'s sibling loop drops blank
    lines, and the skill's heredoc re-serialised every row -- either would have
    deleted this line outright rather than preserved it.
    """
    from mctl_core.effects import _update_decisions_track_row

    path = tmp_path / "manifest.jsonl"
    path.write_text(RAW_MANIFEST, encoding="utf-8")

    _update_decisions_track_row(path, "79", {"status": "adjudicated"})

    before = RAW_MANIFEST.split("\n")
    after = path.read_text(encoding="utf-8").split("\n")
    assert len(after) == len(before)
    for index, (was, now) in enumerate(zip(before, after)):
        if was.strip().startswith('{"n": 79,'):
            assert now != was
            continue
        assert now == was, f"line {index} changed: {was!r} -> {now!r}"


def test_a_row_whose_n_merely_contains_the_target_digits_is_untouched(legacy: Fixture):
    """`790` must not answer for `79`."""
    adjudicate(legacy)

    assert manifest_row(legacy, 790) == {
        "n": 790,
        "slug": "not-the-target",
        "status": "ready",
    }


def test_the_rewritten_row_keeps_the_files_own_key_order(legacy: Fixture):
    before = list(manifest_row(legacy))

    adjudicate(legacy)

    after = list(manifest_row(legacy))
    # Existing keys stay put and in order; new keys are appended.
    assert after[: len(before)] == before


def test_the_write_is_idempotent(tmp_path: Path):
    from mctl_core.effects import _update_decisions_track_row

    path = tmp_path / "manifest.jsonl"
    path.write_text(MANIFEST, encoding="utf-8")
    fields = {"status": "adjudicated", "verdict": "approve", "verdict_note": "ok"}

    _update_decisions_track_row(path, "79", fields)
    once = path.read_text(encoding="utf-8")
    _update_decisions_track_row(path, "79", fields)

    assert path.read_text(encoding="utf-8") == once


def test_re_adjudicating_to_the_same_verdict_changes_nothing(legacy: Fixture):
    """The end-to-end form of idempotence, through the CLI."""
    adjudicate(legacy, verdict="approve", reason="ok")
    once = legacy.manifest.read_text(encoding="utf-8")

    # Re-running the writer with the identical plan must not perturb the file.
    from mctl_core.effects import _update_decisions_track_row

    row = manifest_row(legacy)
    _update_decisions_track_row(
        legacy.manifest,
        str(LEGACY_N),
        {
            "status": "adjudicated",
            "verdict": "approve",
            "verdict_note": "ok",
            "adjudicated_at": str(row["adjudicated_at"]),
        },
        ("defer_until",),
    )

    assert legacy.manifest.read_text(encoding="utf-8") == once


def test_a_terminal_verdict_clears_a_defer_window(tmp_path: Path):
    from mctl_core.effects import _update_decisions_track_row

    path = tmp_path / "manifest.jsonl"
    path.write_text('{"n": 7, "status": "ready", "defer_until": "2999-01-01"}\n', "utf-8")

    _update_decisions_track_row(
        path, "7", {"status": "adjudicated", "verdict": "approve"}, ("defer_until",)
    )

    assert "defer_until" not in json.loads(path.read_text(encoding="utf-8").strip())


def test_deferral_writes_the_un_defer_date(legacy: Fixture):
    """LANE: legacy. The #18 producer half, now owned by mctl rather than a skill."""
    args = [
        "briefs",
        "defer",
        legacy.id,
        "--city",
        str(legacy.city_root),
        "--rig",
        "mathcity",
        "--reason",
        "later",
        "--until",
        "2999-01-01",
        "--json",
    ]
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(legacy.beads_fixture)
    result = subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stdout + result.stderr

    row = manifest_row(legacy)
    assert row["status"] == "ready"
    assert row["defer_until"] == "2999-01-01"


# ---------------------------------------------------------------------------
# The join, and its refusals.
# ---------------------------------------------------------------------------


def test_the_join_is_read_from_legacy_n_not_guessed_from_slugs(tmp_path: Path):
    """The live `he-ckilh` shape: the bead id appears only in the filename."""
    from mctl_core.context import resolve_context
    from mctl_core.effects import _decisions_track_row_key

    fixture = _build(tmp_path, LEGACY_ID)
    ctx = resolve_context(
        REPO_ROOT,
        city=fixture.city_root,
        rig="mathcity",
        require_runtime_city=True,
        require_explicit_runtime=True,
        env={"MCTL_BEADS_FIXTURE": str(fixture.beads_fixture)},
    )

    assert _decisions_track_row_key(ctx, LEGACY_ID) == str(LEGACY_N)
    assert _decisions_track_row_key(ctx, STACK_ID) == ""


def test_legacy_source_is_the_fallback_when_legacy_n_is_absent(tmp_path: Path):
    from mctl_core.effects import _legacy_row_key

    assert (
        _legacy_row_key(
            {"legacy_source": "decisions-track/08-sigma18-done-vs-residual-brief.md"}
        )
        == "8"
    )
    # `null` is the recorded way of saying "no legacy origin", not a guess.
    assert _legacy_row_key({"legacy_source": None}) == ""
    assert _legacy_row_key({}) == ""


def test_a_missing_row_warns_and_does_not_sink_the_adjudication(tmp_path: Path):
    """The index points at row 79 and the manifest no longer holds it."""
    manifest = '{"n": 1, "slug": "gh-auth-login", "status": "ready"}\n'
    fixture = _build(tmp_path, LEGACY_ID, manifest=manifest)
    before = fixture.manifest.read_text(encoding="utf-8")

    payload = adjudicate(fixture)

    assert payload["applied"] is True
    assert bead_status(fixture) == "closed"
    assert read_frontmatter(fixture.doc)["status"].startswith("adjudicated")
    codes = {
        (diagnostic["code"], diagnostic["severity"])
        for diagnostic in payload["diagnostics"]
    }
    assert ("MCTL_DECISIONS_TRACK_ROW_UNWRITABLE", "WARN") in codes
    assert fixture.manifest.read_text(encoding="utf-8") == before


def test_two_rows_claiming_one_n_are_left_alone(tmp_path: Path):
    from mctl_core.effects import (
        DecisionsTrackRowUnwritable,
        _update_decisions_track_row,
    )

    path = tmp_path / "manifest.jsonl"
    original = '{"n": 79, "status": "ready"}\n{"n": 79, "status": "adjudicated"}\n'
    path.write_text(original, encoding="utf-8")

    with pytest.raises(DecisionsTrackRowUnwritable):
        _update_decisions_track_row(path, "79", {"status": "adjudicated"})

    assert path.read_text(encoding="utf-8") == original


def test_a_write_failure_leaves_the_manifest_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    from mctl_core import effects

    path = tmp_path / "manifest.jsonl"
    path.write_text(MANIFEST, encoding="utf-8")

    def boom(*args, **kwargs):
        raise KeyboardInterrupt("interrupted mid-write")

    monkeypatch.setattr(effects.os, "replace", boom)
    with pytest.raises(KeyboardInterrupt):
        effects._update_decisions_track_row(path, "79", {"status": "adjudicated"})

    assert path.read_text(encoding="utf-8") == MANIFEST
