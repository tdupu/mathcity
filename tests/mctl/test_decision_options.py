"""MOPT001: adjudicating a multi-option brief requires naming the option.

The plan defines `BriefOption` twice, incompatibly. §2 defines it as a
*decision* option parsed out of the brief markdown (label, heading, line span,
raw text, confidence); Slice 2 defines it as an *enabled action* (adjudicate /
defer / validate) and instructs `briefs options` to compute those. The
implementation built the Slice 2 one, so `--option`, `--compare-options`, and
MOPT001 — all of which mean §2's decision option — had nothing behind them.

Real briefs enumerate decision options as list items under an Options section:

    ## §4 — Options

    - **(A) One tracked bead per defect.** *(recommended)* ...
    - **(B) Single omnibus bead.** ...

Confirmed in 4 of 5 briefs on the live pile. An unqualified `--verdict approve`
on such a brief silently records a verdict against no particular option, which
is the most realistic way to record the wrong decision through this tool.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MCTL = REPO_ROOT / "assets" / "scripts" / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"

BRIEF = "mc-pending"
SOURCE = "source-pending"

MULTI_OPTION_BODY = """# Brief

## §1 — What is being decided (INVARIANT)

Whether to do the thing.

## §4 — Options

- **(A) Do it now.** *(recommended)* Cheapest path.
- **(B) Defer it.** Costs a cycle.
- **(C) Drop it.** Rejected: status quo produced this brief.

## §5 — SAFETY

This brief does not authorize the edit.
"""

SINGLE_OPTION_BODY = """# Brief

## §4 — Options

- **(A) Do it now.** The only path.
"""

NO_OPTION_BODY = """# Brief

## §1 — What is being decided (INVARIANT)

Whether to do the thing. No options section at all.
"""


def beads_payload() -> list[dict[str, object]]:
    return [
        {
            "id": BRIEF,
            "title": "Pending brief",
            "status": "open",
            "issue_type": "decision",
            "labels": ["brief-open"],
            "dependencies": [
                {"issue_id": BRIEF, "depends_on_id": SOURCE, "type": "related"}
            ],
            "created_at": "2026-08-10T12:00:00Z",
            "updated_at": "2026-08-11T12:00:00Z",
        },
        {
            "id": SOURCE,
            "title": "Source work",
            "status": "open",
            "issue_type": "task",
            "labels": [],
            "created_at": "2026-08-10T12:00:00Z",
            "updated_at": "2026-08-11T12:00:00Z",
        },
    ]


def runtime(tmp_path: Path, body: str | None) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    beads = rig_root / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "briefs" / ".pile").mkdir(parents=True)
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    if body is not None:
        (beads / "briefs" / ".pile" / f"{BRIEF}.md").write_text(body, encoding="utf-8")
    fixture = beads / "issues.jsonl"
    fixture.write_text(
        "".join(json.dumps(r, sort_keys=True) + "\n" for r in beads_payload()), encoding="utf-8"
    )
    return city_root, fixture


def adjudicate(city_root: Path, fixture: Path, *extra: str):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(fixture)
    return subprocess.run(
        [
            sys.executable, str(MCTL), "briefs", "adjudicate", BRIEF,
            "--verdict", "approve", "--reason", "option test", *extra,
            "--city", str(city_root), "--rig", "mathcity", "--json",
        ],
        cwd=REPO_ROOT, text=True, capture_output=True, check=False, env=env,
    )


def test_multi_option_brief_requires_an_option(tmp_path: Path):
    city_root, fixture = runtime(tmp_path, MULTI_OPTION_BODY)

    result = adjudicate(city_root, fixture)

    assert result.returncode != 0
    assert "MOPT001" in result.stderr, result.stderr


def test_naming_the_option_unblocks_adjudication(tmp_path: Path):
    city_root, fixture = runtime(tmp_path, MULTI_OPTION_BODY)

    result = adjudicate(city_root, fixture, "--option", "A")

    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["applied"] is True


def test_single_option_brief_does_not_require_an_option(tmp_path: Path):
    city_root, fixture = runtime(tmp_path, SINGLE_OPTION_BODY)

    result = adjudicate(city_root, fixture)

    assert result.returncode == 0, result.stderr


def test_brief_with_no_options_section_is_unaffected(tmp_path: Path):
    """Most briefs have no options; the guard must not block them."""
    city_root, fixture = runtime(tmp_path, NO_OPTION_BODY)

    result = adjudicate(city_root, fixture)

    assert result.returncode == 0, result.stderr


def test_brief_with_no_markdown_cache_is_unaffected(tmp_path: Path):
    """The bead is canonical; a missing markdown cache must not block a verdict."""
    city_root, fixture = runtime(tmp_path, None)

    result = adjudicate(city_root, fixture)

    assert result.returncode == 0, result.stderr


def test_unknown_option_label_is_rejected(tmp_path: Path):
    city_root, fixture = runtime(tmp_path, MULTI_OPTION_BODY)

    result = adjudicate(city_root, fixture, "--option", "Z")

    assert result.returncode != 0
    assert "MOPT002" in result.stderr, result.stderr


def test_parser_extracts_labels_headings_and_spans(tmp_path: Path):
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core.briefs import parse_decision_options

    options = parse_decision_options(MULTI_OPTION_BODY)

    assert [o.label for o in options] == ["A", "B", "C"]
    assert options[0].heading == "Do it now."
    assert options[0].start_line < options[1].start_line
    assert all(o.confidence == "explicit" for o in options)
    assert "recommended" in options[0].raw_text


def test_parser_ignores_bold_parens_outside_an_options_section():
    """Scope the parser so ordinary prose cannot fabricate options."""
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core.briefs import parse_decision_options

    body = "# Brief\n\n## §2 — Analysis\n\n- **(A) Not an option.** Just prose.\n"
    assert parse_decision_options(body) == ()


def test_a_doubled_options_section_yields_each_label_once():
    """Some brief bodies carry §4 twice — a human `§4 — Alternatives named` and
    an appended machine `§4 — Options` — so both sections enumerate A/B/C and the
    parser produced six options (A,B,C,A,B,C). A label identifies an option, so a
    repeat is a duplicate, not a new choice: each distinct label appears once,
    keeping its first occurrence.
    """
    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core.briefs import parse_decision_options

    body = (
        "# Brief\n\n"
        "## §4 — Alternatives named\n\n"
        "- **(A) Approve behind the spike.** *(recommended)*\n"
        "- **(B) Reference-only interim.**\n"
        "- **(C) Defer.**\n\n"
        "## §4 — Options\n\n"
        "- **(A) Approve behind the spike** *(recommended)* Fuller restatement.\n"
        "- **(B) Reference-only interim** Restated.\n"
        "- **(C) Defer** Park.\n"
    )
    options = parse_decision_options(body)

    assert [o.label for o in options] == ["A", "B", "C"]
    # first occurrence wins — the human alternatives heading, not the appendix
    assert options[0].heading == "Approve behind the spike."
