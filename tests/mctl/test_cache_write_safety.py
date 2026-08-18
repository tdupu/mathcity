"""Redundant cache writes must be atomic, serialized, and TOML-safe.

The cache writers read a whole file, mutate in memory, and write it back with
`path.write_text` — no temp-and-rename, no lock. An interrupted adjudication
truncates the decision TOML or the whole stack `.index.jsonl`, and a
concurrent shuffler drain is a lost update. The TOML writer also splits each
line on the first `=` and re-emits every value quoted, so it corrupts
multi-line strings and silently coerces non-strings.
"""
from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _core_on_path():
    import sys

    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))


def test_toml_update_preserves_non_string_values(tmp_path: Path):
    from mctl_core.effects import _update_simple_toml

    path = tmp_path / "decision.toml"
    path.write_text(
        'slug = "mc-abc"\nunlock_count = 8\nready = true\n', encoding="utf-8"
    )

    _update_simple_toml(path, {"status": "adjudicated"})

    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert parsed["status"] == "adjudicated"
    assert parsed["unlock_count"] == 8, "integer was coerced to a string"
    assert parsed["ready"] is True, "boolean was coerced to a string"


def test_toml_update_does_not_edit_inside_a_multiline_string(tmp_path: Path):
    """The line-splitting writer rewrites any line that looks like the key.

    A reason block containing `status = ...` gets that line rewritten while
    the real top-level `status` key is left alone, so the verdict is silently
    lost and unrelated prose is mutated instead.
    """
    from mctl_core.effects import _update_simple_toml

    path = tmp_path / "decision.toml"
    path.write_text(
        'slug = "mc-abc"\n'
        'reason = """\nstatus = "quoted in the reason"\ndone\n"""\n'
        'status = "pending"\n',
        encoding="utf-8",
    )

    _update_simple_toml(path, {"status": "adjudicated"})

    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert parsed["status"] == "adjudicated", "the real status key was not updated"
    assert "quoted in the reason" in parsed["reason"], "prose inside a string was rewritten"


def test_toml_update_preserves_non_string_values_being_updated(tmp_path: Path):
    from mctl_core.effects import _update_simple_toml

    path = tmp_path / "decision.toml"
    path.write_text('slug = "mc-abc"\nunlock_count = 8\n', encoding="utf-8")

    _update_simple_toml(path, {"unlock_count": 9})

    parsed = tomllib.loads(path.read_text(encoding="utf-8"))
    assert parsed["unlock_count"] == 9, "integer was coerced to a string"


def test_toml_update_is_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A crash mid-write must leave the original file intact, not truncated."""
    from mctl_core import effects

    path = tmp_path / "decision.toml"
    original = 'slug = "mc-abc"\nstatus = "pending"\n'
    path.write_text(original, encoding="utf-8")

    def boom(*args, **kwargs):
        raise KeyboardInterrupt("interrupted mid-write")

    monkeypatch.setattr(effects.os, "replace", boom)
    with pytest.raises(KeyboardInterrupt):
        effects._update_simple_toml(path, {"status": "adjudicated"})

    assert path.read_text(encoding="utf-8") == original


def test_stack_index_update_is_atomic(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    from mctl_core import effects

    path = tmp_path / ".index.jsonl"
    original = json.dumps({"brief_id": "mc-abc", "status": "pending"}) + "\n"
    path.write_text(original, encoding="utf-8")

    def boom(*args, **kwargs):
        raise KeyboardInterrupt("interrupted mid-write")

    monkeypatch.setattr(effects.os, "replace", boom)
    with pytest.raises(KeyboardInterrupt):
        effects._update_stack_index(path, "mc-abc", {"status": "adjudicated"})

    assert path.read_text(encoding="utf-8") == original


def test_stack_index_write_takes_a_lock(tmp_path: Path):
    """mctl is not the only writer of .index.jsonl; the shuffler drains it too."""
    from mctl_core.effects import _stack_index_lock_path, _update_stack_index

    path = tmp_path / ".index.jsonl"
    path.write_text(json.dumps({"brief_id": "mc-abc", "status": "pending"}) + "\n", encoding="utf-8")

    lock_path = _stack_index_lock_path(path)
    _update_stack_index(path, "mc-abc", {"status": "adjudicated"})

    assert lock_path.exists(), "no lock file was created for the shared stack index"
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    assert rows[0]["status"] == "adjudicated"


def _hammer_stack_index(path: str, target: str, value: str) -> None:
    import sys

    sys.path.insert(0, str(REPO_ROOT / "assets" / "scripts"))
    from mctl_core.effects import _update_stack_index

    for _ in range(20):
        _update_stack_index(Path(path), target, {"status": value})


def test_concurrent_stack_index_writers_do_not_lose_updates(tmp_path: Path):
    """Two writers serialize; neither update is lost."""
    import multiprocessing

    path = tmp_path / ".index.jsonl"
    path.write_text(
        json.dumps({"brief_id": "a", "status": "pending"}) + "\n"
        + json.dumps({"brief_id": "b", "status": "pending"}) + "\n",
        encoding="utf-8",
    )

    procs = [
        multiprocessing.Process(target=_hammer_stack_index, args=(str(path), "a", "adjudicated")),
        multiprocessing.Process(target=_hammer_stack_index, args=(str(path), "b", "deferred")),
    ]
    for proc in procs:
        proc.start()
    for proc in procs:
        proc.join(timeout=60)

    rows = {
        json.loads(line)["brief_id"]: json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }
    assert rows["a"]["status"] == "adjudicated"
    assert rows["b"]["status"] == "deferred", "a concurrent writer lost its update"
