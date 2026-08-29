"""Adjudication must ALSO mirror the verdict into the aggregated global root.

gt-5yxup1. Decision records live PER-RIG at
`<rig_root>/.beads/briefs/decisions/<id>.toml`, in the effects.py verdict schema
(`verdict`/`verdict_reason`, no `source_bead`). The three brief.decided consumer
formulas — revise-return, brief-decision-dispatch, brief-archive-sweep — scan ONE
global `artifact_root` and read the `decision`/`reason`/`source_bead` schema. Before
this fix nothing wrote that global root, so it stayed empty and every `revise`
verdict re-filed nothing (measured: 8 revises, 0 re-filings, 2026-08-27).

The fix keeps revise-return's single-scan-point design: mctl (the canonical writer,
P7.1) additionally writes each decided record into the aggregated global root, in the
schema the formulas read. These tests pin that mirror.

The aggregated root is `MCTL_AGGREGATED_BRIEF_ROOT` (env override, for isolation) or
`~/.gc/mathcity/aggregated-briefs` by default.
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

#: The stack-track brief already in the shared fixture. Its bead is blocked by
#: `mc-source` — that is the source bead the aggregated record must carry.
STACK_ID = "mc-open"
SOURCE_BEAD = "mc-source"


class Fixture:
    def __init__(self, city_root: Path, rig_root: Path, agg_root: Path):
        self.city_root = city_root
        self.rig_root = rig_root
        self.agg_root = agg_root

    @property
    def beads_fixture(self) -> Path:
        return self.rig_root / ".beads" / "issues.jsonl"

    @property
    def aggregated_record(self) -> Path:
        return self.agg_root / "decisions" / f"{STACK_ID}.toml"


def _build(tmp_path: Path) -> Fixture:
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(
        BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track"
    )
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return Fixture(city_root, rig_root, tmp_path / "agg")


def _adjudicate(
    fixture: Fixture, *, verdict: str, reason: str, apply: bool = True
) -> dict[str, object]:
    args = [
        "briefs",
        "adjudicate",
        STACK_ID,
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
    env["MCTL_AGGREGATED_BRIEF_ROOT"] = str(fixture.agg_root)
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


def _read_toml(path: Path) -> dict[str, object]:
    import tomllib

    return tomllib.loads(path.read_text(encoding="utf-8"))


def test_a_revise_verdict_lands_an_aggregated_record(tmp_path: Path):
    fixture = _build(tmp_path)

    _adjudicate(fixture, verdict="revise", reason="tighten section 3")

    assert fixture.aggregated_record.is_file(), (
        "revise verdict wrote no aggregated decision record; revise-return would "
        "scan an empty root and re-file nothing"
    )
    record = _read_toml(fixture.aggregated_record)
    assert record["decision"] == "revise"
    assert record["reason"] == "tighten section 3"
    assert record["source_bead"] == SOURCE_BEAD
    assert record["rig"] == "mathcity"


def test_the_aggregated_write_appears_in_the_dry_run_plan(tmp_path: Path):
    fixture = _build(tmp_path)

    payload = _adjudicate(fixture, verdict="revise", reason="x", apply=False)

    updates = payload["effect_plan"]["cache_updates"]
    planned = [
        item
        for item in updates
        if str(item.get("path", "")).endswith(f"decisions/{STACK_ID}.toml")
        and str(fixture.agg_root) in str(item.get("path", ""))
    ]
    assert len(planned) == 1, f"aggregated write not planned: {updates}"
    # Dry run means dry.
    assert not fixture.aggregated_record.exists()


def test_an_approve_verdict_also_aggregates(tmp_path: Path):
    """brief-decision-dispatch keys approve/reject routing on the same record, so
    the mirror is written for every terminal verdict, not only revise."""
    fixture = _build(tmp_path)

    _adjudicate(fixture, verdict="approve", reason="ok")

    record = _read_toml(fixture.aggregated_record)
    assert record["decision"] == "approve"
    assert record["source_bead"] == SOURCE_BEAD
