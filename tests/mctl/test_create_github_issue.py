"""#185: file a GitHub issue from the typed surface, so a Mayor that finds a
defect can open the issue without a human carrying it (loop step 1).

`github_issues.py` was READ-ONLY (`fetch_issue`, `rig_for_issue`); this is the
write half. The tool is dry-run-by-default: a preview returns the fully rendered
issue in an EffectPlan and shells NOTHING (asserted with a recording fake, #188).
A live run shells `gh issue create` exactly once. A body that omits a REQUIRED
section of the target repo's live issue template is refused BEFORE any subprocess
(the repo's template is the enforcement point -- `create-issue` skill's rule).

`create_issue` and `required_template_sections` are monkeypatched throughout:
these tests exercise the planning and MCP-adapter behavior, not `gh` itself,
which `github_issues.py`'s own narrower tests cover.
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

from mctl_core import mcp_server, effects
from mctl_core.schemas import schema_errors

from test_mcp_server import CITY_ROOT, SOURCE_CHECKOUT, call, tree_digest


VALID_BODY = "### Summary\nThe pool exerts no upward pressure.\n\n### Root cause\n#99."


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


class GhRecorder:
    """Stands in for `gh issue create`; records every call and returns a URL."""

    def __init__(self, url: str = "https://github.com/tdupu/mathcity/issues/207"):
        self.calls: list[dict] = []
        self.url = url

    def __call__(self, repo, title, body, labels=(), *, timeout=30):
        self.calls.append(
            {"repo": repo, "title": title, "body": body, "labels": tuple(labels)}
        )
        return self.url


def patch_gh(monkeypatch, recorder=None, *, template=()):
    recorder = recorder or GhRecorder()
    monkeypatch.setattr(effects, "create_issue", recorder)
    monkeypatch.setattr(
        effects, "required_template_sections", lambda repo, **_: tuple(template)
    )
    return recorder


# --- dry run: a real preview with ZERO side effects (#188) -------------------


def test_dry_run_plans_the_issue_and_shells_nothing(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    recorder = patch_gh(monkeypatch)
    before = tree_digest(rig_root)

    structured = call(
        server(city_root, rig_root),
        "create_github_issue",
        {"repo": "tdupu/mathcity", "title": "bug: x", "body": VALID_BODY, "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    writes = structured["effect_plan"]["github_writes"]
    assert writes and writes[0]["title"] == "bug: x"
    assert writes[0]["repo"] == "tdupu/mathcity"
    assert recorder.calls == [], "a dry run must not shell gh"
    assert tree_digest(rig_root) == before, "a dry run must not touch the store"


def test_omitting_dry_run_defaults_to_dry_run(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    recorder = patch_gh(monkeypatch)

    structured = call(
        server(city_root, rig_root),
        "create_github_issue",
        {"repo": "tdupu/mathcity", "title": "bug: x", "body": VALID_BODY},
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    assert recorder.calls == []


# --- live run: exactly one `gh issue create`, returning the URL -------------


def test_live_run_creates_the_issue_once_and_returns_the_url(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    recorder = patch_gh(monkeypatch)

    structured = call(
        server(city_root, rig_root),
        "create_github_issue",
        {
            "repo": "tdupu/mathcity",
            "title": "bug: x",
            "body": VALID_BODY,
            "labels": ["kind/bug", "priority/p1"],
            "dry_run": False,
        },
    )["result"]["structuredContent"]

    assert structured["applied"] is True
    assert len(recorder.calls) == 1
    assert recorder.calls[0]["repo"] == "tdupu/mathcity"
    assert recorder.calls[0]["labels"] == ("kind/bug", "priority/p1")
    urls = [
        effect.get("url")
        for effect in structured["actual_effects"]
        if effect.get("kind") == "github_issue"
    ]
    assert recorder.url in urls


# --- template enforcement: refuse a body missing a REQUIRED section ----------


def test_missing_required_template_section_refused_before_any_subprocess(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    recorder = patch_gh(monkeypatch, template=["Summary", "Root cause"])

    result = call(
        server(city_root, rig_root),
        "create_github_issue",
        {
            "repo": "tdupu/mathcity",
            "title": "bug: x",
            "body": "### Summary\nonly this",
            "dry_run": False,
        },
    )["result"]

    assert result.get("isError") is True
    codes = {d["code"] for d in result["structuredContent"]["diagnostics"]}
    assert "MGHW_TEMPLATE_SECTION_MISSING" in codes
    assert recorder.calls == [], "the template check must precede every subprocess"


def test_a_body_carrying_every_required_section_is_allowed(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_gh(monkeypatch, template=["Summary", "Root cause"])

    structured = call(
        server(city_root, rig_root),
        "create_github_issue",
        {"repo": "tdupu/mathcity", "title": "bug: x", "body": VALID_BODY, "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    assert structured["effect_plan"]["github_writes"]


# --- #203 served-schema pattern: validate the SERVED response ---------------


def _output_schema(name: str) -> dict:
    return next(t for t in mcp_server.TOOLS if t.name == name).output_schema


def test_served_success_response_satisfies_declared_schema(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_gh(monkeypatch)

    structured = call(
        server(city_root, rig_root),
        "create_github_issue",
        {"repo": "tdupu/mathcity", "title": "bug: x", "body": VALID_BODY, "dry_run": True},
    )["result"]["structuredContent"]

    violations = schema_errors(structured, _output_schema("create_github_issue"))
    assert violations == [], violations
    assert all(
        isinstance(d, dict) and {"code", "message", "severity"} <= set(d)
        for d in structured["diagnostics"]
    )


def test_served_refusal_carries_typed_diagnostic_objects_not_strings(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_gh(monkeypatch, template=["Summary", "Root cause"])

    structured = call(
        server(city_root, rig_root),
        "create_github_issue",
        {"repo": "tdupu/mathcity", "title": "bug: x", "body": "### Summary\nx", "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["diagnostics"], "a refusal must carry a diagnostic"
    assert all(
        isinstance(d, dict) and {"code", "message", "severity"} <= set(d)
        for d in structured["diagnostics"]
    ), "a bare-string diagnostic is the #203 bug"
