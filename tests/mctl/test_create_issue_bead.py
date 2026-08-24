"""#170: mint an OPEN bead mirroring a GitHub issue, through the typed MCP surface.

`briefs_create` already accepts `sources=[<bead>]`; nothing minted the bead a
tracker-originated brief needs to point at, so `MWRK011` refused every issue-
derived brief for want of a legal source. `create_issue_bead` is that mint.

`fetch_issue` is monkeypatched throughout -- these tests exercise the planning
and MCP-adapter behavior, not `gh` itself, which `github_issues.py`'s own
narrower tests cover.
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
from mctl_core.github_issues import GithubIssueError, IssueSnapshot

from test_mcp_server import CITY_ROOT, SOURCE_CHECKOUT, call, tree_digest


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


def an_issue(**overrides) -> IssueSnapshot:
    fields = dict(
        repo="tdupu/mathcity",
        number=179,
        title="KEYSTONE: turn a GitHub issue into a dispatchable hygienic brief",
        body="The autonomous loop, and the one edge that does not exist.",
        labels=("kind/feature", "priority/p1"),
        state="OPEN",
        url="https://github.com/tdupu/mathcity/issues/179",
    )
    fields.update(overrides)
    return IssueSnapshot(**fields)


def patch_fetch(monkeypatch: pytest.MonkeyPatch, issue: IssueSnapshot | None, *, error: Exception | None = None):
    def fake_fetch_issue(repo: str, number: int, *, timeout: int = 30) -> IssueSnapshot:
        if error is not None:
            raise error
        assert issue is not None
        return issue

    monkeypatch.setattr(effects, "fetch_issue", fake_fetch_issue)


# --- the #188 regression: dry_run must be a TRUE no-op ----------------------


def test_dry_run_mutates_nothing_on_disk_or_in_the_bead_store(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_fetch(monkeypatch, an_issue())
    before = tree_digest(rig_root)

    structured = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/mathcity", "issue_number": 179, "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    assert structured["effect_plan"]["bead_creates"], "the plan should describe the create"
    assert tree_digest(rig_root) == before, "a dry run must not touch the bead store"


def test_omitting_dry_run_defaults_to_dry_run(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_fetch(monkeypatch, an_issue())
    before = tree_digest(rig_root)

    structured = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/mathcity", "issue_number": 179},
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    assert tree_digest(rig_root) == before


# --- fail-closed conditions ---------------------------------------------------


def test_an_issue_for_a_different_rig_is_refused_before_any_gh_call(tmp_path, monkeypatch):
    """The rig is determined by the tracker, not chosen by the caller.

    The server fixture resolves to rig "mathcity"; a hecke-tracked issue must
    be refused, and refused BEFORE fetch_issue runs at all -- checking the
    fake never got called is what proves this is a fail-fast precondition,
    not a check that happens to also refuse after a wasted network read.
    """
    city_root, rig_root = empty_rig_fixture(tmp_path)
    called = []

    def fake_fetch_issue(repo, number, *, timeout=30):
        called.append((repo, number))
        return an_issue()

    monkeypatch.setattr(effects, "fetch_issue", fake_fetch_issue)

    result = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/hecke", "issue_number": 179, "dry_run": True},
    )["result"]

    assert result.get("isError") is True
    codes = {d["code"] for d in result["structuredContent"]["diagnostics"]}
    assert "MISS005" in codes
    assert called == [], "fetch_issue must not run once the rig mismatch is known"


def test_a_closed_issue_is_refused(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_fetch(monkeypatch, an_issue(state="CLOSED"))

    result = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/mathcity", "issue_number": 179, "dry_run": True},
    )["result"]

    assert result.get("isError") is True
    codes = {d["code"] for d in result["structuredContent"]["diagnostics"]}
    assert "MISS001" in codes


def test_an_empty_body_is_refused(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_fetch(monkeypatch, an_issue(body=""))

    result = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/mathcity", "issue_number": 179, "dry_run": True},
    )["result"]

    assert result.get("isError") is True
    codes = {d["code"] for d in result["structuredContent"]["diagnostics"]}
    assert "MISS002" in codes


def test_a_failed_github_read_is_reported_not_swallowed(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_fetch(monkeypatch, None, error=GithubIssueError("gh issue view tdupu/mathcity#179 failed: not found"))

    result = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/mathcity", "issue_number": 179, "dry_run": True},
    )["result"]

    assert result.get("isError") is True
    codes = {d["code"] for d in result["structuredContent"]["diagnostics"]}
    assert "MISS004" in codes


# --- the successful plan -----------------------------------------------------


def test_the_plan_carries_the_issue_as_metadata_not_as_bd_labels(tmp_path, monkeypatch):
    """#170's own design decision: GitHub labels (`kind/feature`) contain `/`,
    which MBRF033 rejects as a bd label token -- they go into metadata instead."""
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_fetch(monkeypatch, an_issue())

    structured = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/mathcity", "issue_number": 179, "dry_run": True},
    )["result"]["structuredContent"]

    create = structured["effect_plan"]["bead_creates"][0]
    assert create["labels"] == []
    assert create["metadata"]["gh.issue"] == "tdupu/mathcity#179"
    assert create["metadata"]["gh.repo"] == "tdupu/mathcity"
    assert create["metadata"]["gh.labels"] == "kind/feature,priority/p1"
    assert create["issue_type"] == "task", "a mirror bead is work, not a decision -- it must not join the brief population"
    assert create["title"] == an_issue().title
    # BeadCreate.to_dict() (beads.py) does not serialize `body` -- same shape
    # `plan_create_brief`'s own BeadCreate already has, not something this
    # change introduces or should work around.


def test_an_unlabelled_issue_omits_the_gh_labels_key_rather_than_writing_empty(tmp_path, monkeypatch):
    """#170/#190 seam review (stripes' catch): #190's commission.py omits
    gh.labels when an issue has none, so `--has-metadata-key gh.labels` never
    false-positives on an unlabelled issue. #170 must match, not diverge --
    two implementations of one convention is not a convention. Not
    hypothetical: `gh#1`, the issue the whole #180 proof ran against, has no
    labels and would have hit this on the very first real call.
    """
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_fetch(monkeypatch, an_issue(number=1, labels=()))

    structured = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/mathcity", "issue_number": 1, "dry_run": True},
    )["result"]["structuredContent"]

    create = structured["effect_plan"]["bead_creates"][0]
    assert "gh.labels" not in create["metadata"], "absent means the issue had none; an empty string is not a measurement"
    assert create["metadata"]["gh.issue"] == "tdupu/mathcity#1"


# --- idempotency: a second call must not mint a second mirror ---------------


def test_a_second_call_for_the_same_issue_returns_the_existing_bead(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    beads_path = rig_root / ".beads" / "issues.jsonl"
    beads_path.write_text(
        '{"id": "mc-existing", "title": "mirror", "status": "open", "issue_type": "task", '
        '"metadata": {"gh.issue": "tdupu/mathcity#179"}}\n',
        encoding="utf-8",
    )
    patch_fetch(monkeypatch, an_issue())
    before = tree_digest(rig_root)

    structured = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/mathcity", "issue_number": 179, "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["applied"] is False
    assert structured["effect_plan"]["bead_creates"] == [], "no second mirror should be planned"
    codes = {d["code"] for d in structured["effect_plan"]["advisories"]}
    assert "MISS003" in codes
    assert tree_digest(rig_root) == before


# --- priority mapping (#203-adjacent: the issue's triaged severity must reach
#     the bead, not be flattened to bd's default 2) --------------------------

def test_the_priority_label_maps_to_bead_priority(tmp_path, monkeypatch):
    """A `priority/p1` issue mints a bead at bd priority 1, not the default 2."""
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_fetch(monkeypatch, an_issue())  # default labels carry priority/p1

    structured = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/mathcity", "issue_number": 179, "dry_run": True},
    )["result"]["structuredContent"]

    create = structured["effect_plan"]["bead_creates"][0]
    assert create["priority"] == 1, "the triaged priority/p1 must reach the bead"


def test_a_p3_issue_maps_to_priority_three(tmp_path, monkeypatch):
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_fetch(monkeypatch, an_issue(labels=("kind/docs", "priority/p3")))

    structured = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/mathcity", "issue_number": 179, "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["effect_plan"]["bead_creates"][0]["priority"] == 3


def test_an_issue_without_a_priority_label_leaves_priority_unset(tmp_path, monkeypatch):
    """Absent means unset, not a fabricated default: bd applies its own default.

    Same absent-not-empty discipline as `gh.labels` -- the tool must not invent a
    severity the triager never assigned."""
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_fetch(monkeypatch, an_issue(number=1, labels=("kind/feature",)))

    structured = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/mathcity", "issue_number": 1, "dry_run": True},
    )["result"]["structuredContent"]

    create = structured["effect_plan"]["bead_creates"][0]
    assert "priority" not in create, "no priority label means no --priority, not a made-up one"


def test_the_most_severe_priority_label_wins(tmp_path, monkeypatch):
    """If an issue somehow carries two priority labels, the lowest number (most
    severe) is used -- never a silent pick that could under-prioritise a p1."""
    city_root, rig_root = empty_rig_fixture(tmp_path)
    patch_fetch(monkeypatch, an_issue(labels=("priority/p3", "priority/p1")))

    structured = call(
        server(city_root, rig_root),
        "create_issue_bead",
        {"repo": "tdupu/mathcity", "issue_number": 179, "dry_run": True},
    )["result"]["structuredContent"]

    assert structured["effect_plan"]["bead_creates"][0]["priority"] == 1
