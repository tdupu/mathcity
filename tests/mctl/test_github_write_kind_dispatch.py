"""An unknown GithubWrite kind must refuse, not default to filing an issue.

`_apply_github_write` dispatched as:

    if write.kind == "edit":  edit_issue(...)
    else:                     create_issue(...)

so any kind that reached the plan without a branch in the applier would **file a
GitHub issue** -- the loudest possible wrong action from the quietest possible
omission, and it touches state outside the city, where nothing can be rolled
back by a store repair.

This is not hypothetical. #253 proposes `comment` and `close` kinds so a split
can link children to their parent and optionally close it; whoever implements it
adds kinds to the plan first and the applier second, which is exactly the window
the old `else` made dangerous.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_core import effects  # noqa: E402
from mctl_core.context import MctlContext  # noqa: E402
from mctl_core.effects import (  # noqa: E402
    GITHUB_WRITE_KINDS,
    EffectPlan,
    GithubWrite,
    MutationError,
    _apply_github_write,
)


def _ctx(tmp_path: Path) -> MctlContext:
    return MctlContext(
        city_root=tmp_path,
        rig_id="mathcity",
        rig_root=tmp_path / "rig",
        beads_fixture=tmp_path / "issues.jsonl",
        rig_db=".beads",
        source_checkout=tmp_path,
        paths_toml=tmp_path / "paths.toml",
        gates_toml=tmp_path / "gates.toml",
        invocation_cwd=tmp_path,
        trace_id="trace-ghw-1",
        warnings=(),
        discovery_path="test",
        city_active=None,
        city_endpoint=None,
    )


def _plan() -> EffectPlan:
    return EffectPlan(
        trace_id="trace-ghw-1",
        operation="github.probe",
        target_brief_id="mc-probe",
        preconditions=(),
        advisories=(),
        bead_updates=(),
        cache_updates=(),
        event_writes=(),
        trace_writes=(),
    )


def test_the_known_kinds_are_exactly_create_and_edit():
    """A kind added to the set without an applier branch would re-open the hole.

    So the set is pinned: widening it is a deliberate act that fails this test
    first and makes the author look at the dispatch.
    """
    assert GITHUB_WRITE_KINDS == {"create", "edit"}


def test_an_unknown_kind_refuses_and_shells_nothing(tmp_path: Path, monkeypatch):
    """THE regression: before the fix this called create_issue and filed an issue."""
    called: list[str] = []
    monkeypatch.setattr(
        effects, "create_issue", lambda *a, **k: called.append("create") or "url"
    )
    monkeypatch.setattr(
        effects, "edit_issue", lambda *a, **k: called.append("edit") or "url"
    )
    write = GithubWrite(kind="comment", repo="tdupu/mathcity", body="hi", number=1)

    with pytest.raises(MutationError) as caught:
        _apply_github_write(_ctx(tmp_path), _plan(), write, [], tmp_path / "trace.jsonl")

    assert called == [], f"nothing may be shelled for an unknown kind; called {called}"
    diagnostic = caught.value.diagnostic
    assert diagnostic.code == "MGHW_UNKNOWN_WRITE_KIND"
    assert "comment" in diagnostic.message


@pytest.mark.parametrize("kind", ["close", "delete", "", "CREATE", "create "])
def test_near_misses_all_refuse(tmp_path: Path, monkeypatch, kind: str):
    """Case and whitespace variants are unknown kinds, not sloppy spellings of known ones.

    `"CREATE"` silently filing an issue would be the same defect with a shift key.
    """
    monkeypatch.setattr(effects, "create_issue", lambda *a, **k: pytest.fail("shelled"))
    monkeypatch.setattr(effects, "edit_issue", lambda *a, **k: pytest.fail("shelled"))
    write = GithubWrite(kind=kind, repo="tdupu/mathcity", body="b", number=1)

    with pytest.raises(MutationError):
        _apply_github_write(_ctx(tmp_path), _plan(), write, [], tmp_path / "trace.jsonl")


def test_a_create_still_creates(tmp_path: Path, monkeypatch):
    """The guard must not break the path it guards."""
    seen: dict[str, object] = {}

    def _create(repo, title, body, labels):
        seen.update(repo=repo, title=title, body=body, labels=labels)
        return "https://github.com/tdupu/mathcity/issues/9"

    monkeypatch.setattr(effects, "create_issue", _create)
    monkeypatch.setattr(effects, "edit_issue", lambda *a, **k: pytest.fail("wrong branch"))
    write = GithubWrite(
        kind="create", repo="tdupu/mathcity", body="body", title="t", labels=("kind/bug",)
    )

    _apply_github_write(_ctx(tmp_path), _plan(), write, [], tmp_path / "trace.jsonl")

    assert seen["title"] == "t"
    assert seen["labels"] == ("kind/bug",)


def test_an_edit_still_edits(tmp_path: Path, monkeypatch):
    seen: dict[str, object] = {}

    def _edit(repo, number, body):
        seen.update(repo=repo, number=number, body=body)
        return "https://github.com/tdupu/mathcity/issues/9"

    monkeypatch.setattr(effects, "edit_issue", _edit)
    monkeypatch.setattr(effects, "create_issue", lambda *a, **k: pytest.fail("wrong branch"))
    write = GithubWrite(kind="edit", repo="tdupu/mathcity", body="new", number=9)

    _apply_github_write(_ctx(tmp_path), _plan(), write, [], tmp_path / "trace.jsonl")

    assert seen["number"] == 9
    assert seen["body"] == "new"
