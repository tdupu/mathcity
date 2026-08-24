"""#185/#52: make an existing GitHub issue hygienic IN PLACE, additively.

`update-issue` rewrites an issue body into one canonical statement and folds the
prior versions away -- consolidation semantics that fit a Magma package tracker
and are DESTRUCTIVE on an agent-maintained one, where the history of an issue is
evidence. `standardize_github_issue` must therefore APPEND a
`## Standardized restatement` section and preserve every existing byte. It is a
transform, not a gate.

`fetch_issue`/`edit_issue` are monkeypatched: these tests exercise the additive
composition and the idempotence, not `gh`.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import mcp_server, effects, issue_standardize
from mctl_core.github_issues import IssueSnapshot
from mctl_core.schemas import schema_errors

from test_mcp_server import CITY_ROOT, SOURCE_CHECKOUT, call, tree_digest

MARKER = "## Standardized restatement"
ORIGINAL = "some old body\n\nfiled 2026-01-01, never templated\n- a\n- b"


def empty_rig_fixture(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    beads = rig_root / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    (beads / "issues.jsonl").write_text("", encoding="utf-8")
    return city_root, rig_root


def server(city_root: Path, rig_root: Path):
    environment = {"MCTL_BEADS_FIXTURE": str(rig_root / ".beads" / "issues.jsonl")}
    return mcp_server.MctlMcpServer(
        default_city=city_root, default_rig="mathcity", client_class="internal", env=environment
    )


def an_issue(body=ORIGINAL, **overrides) -> IssueSnapshot:
    fields = dict(
        repo="tdupu/mathcity",
        number=102,
        title="a headingless issue",
        body=body,
        labels=("kind/bug",),
        state="OPEN",
        url="https://github.com/tdupu/mathcity/issues/102",
    )
    fields.update(overrides)
    return IssueSnapshot(**fields)


class EditRecorder:
    def __init__(self, url="https://github.com/tdupu/mathcity/issues/102"):
        self.calls: list[dict] = []
        self.url = url

    def __call__(self, repo, number, body, *, timeout=30):
        self.calls.append({"repo": repo, "number": number, "body": body})
        return self.url


def patch(monkeypatch, issue, recorder=None):
    recorder = recorder or EditRecorder()
    monkeypatch.setattr(issue_standardize, "fetch_issue", lambda *a, **k: issue)
    monkeypatch.setattr(effects, "edit_issue", recorder)
    return recorder


# --- additive composition: original preserved byte-for-byte -----------------


def test_the_composed_body_is_the_original_plus_an_appended_section(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch(monkeypatch, an_issue())

    structured = call(
        server(city_root, rig_root),
        "standardize_github_issue",
        {"repo": "tdupu/mathcity", "issue_number": 102, "dry_run": True},
    )["result"]["structuredContent"]

    write = structured["effect_plan"]["github_writes"][0]
    assert write["kind"] == "edit"
    assert write["issue_number"] == 102
    assert write["body"].startswith(ORIGINAL), "every original byte must be preserved as a prefix"
    assert MARKER in write["body"][len(ORIGINAL):], "the section is appended, never interleaved"


# --- dry run posts nothing ---------------------------------------------------


def test_dry_run_shells_nothing(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    recorder = patch(monkeypatch, an_issue())

    call(
        server(city_root, rig_root),
        "standardize_github_issue",
        {"repo": "tdupu/mathcity", "issue_number": 102, "dry_run": True},
    )

    assert recorder.calls == []


# --- live run edits once -----------------------------------------------------


def test_live_run_edits_the_issue_once(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    recorder = patch(monkeypatch, an_issue())

    structured = call(
        server(city_root, rig_root),
        "standardize_github_issue",
        {"repo": "tdupu/mathcity", "issue_number": 102, "dry_run": False},
    )["result"]["structuredContent"]

    assert structured["applied"] is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0]["body"].startswith(ORIGINAL)


# --- idempotence: a second run detects the marker and no-ops -----------------


def test_a_second_run_detects_the_marker_and_no_ops(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    already = ORIGINAL + "\n\n" + MARKER + "\n### Summary\nx\n"
    recorder = patch(monkeypatch, an_issue(body=already))

    structured = call(
        server(city_root, rig_root),
        "standardize_github_issue",
        {"repo": "tdupu/mathcity", "issue_number": 102, "dry_run": False},
    )["result"]["structuredContent"]

    assert structured["applied"] is False, "an already-standardized issue must not be re-edited"
    assert structured["effect_plan"]["github_writes"] == []
    codes = {d["code"] for d in structured["diagnostics"]}
    assert "MGHW_ALREADY_STANDARDIZED" in codes
    assert recorder.calls == []


# --- #203 served-schema pattern ---------------------------------------------


def _output_schema(name: str) -> dict:
    return next(t for t in mcp_server.TOOLS if t.name == name).output_schema


def test_served_success_response_satisfies_declared_schema(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch(monkeypatch, an_issue())

    structured = call(
        server(city_root, rig_root),
        "standardize_github_issue",
        {"repo": "tdupu/mathcity", "issue_number": 102, "dry_run": True},
    )["result"]["structuredContent"]

    assert schema_errors(structured, _output_schema("standardize_github_issue")) == []


def test_served_noop_response_carries_typed_diagnostic_objects(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    already = ORIGINAL + "\n\n" + MARKER + "\nx"
    patch(monkeypatch, an_issue(body=already))

    structured = call(
        server(city_root, rig_root),
        "standardize_github_issue",
        {"repo": "tdupu/mathcity", "issue_number": 102, "dry_run": True},
    )["result"]["structuredContent"]

    assert schema_errors(structured, _output_schema("standardize_github_issue")) == []
    assert structured["diagnostics"]
    assert all(
        isinstance(d, dict) and {"code", "message", "severity"} <= set(d)
        for d in structured["diagnostics"]
    )
