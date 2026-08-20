"""The presentation queue must not change size when the caller's cwd changes.

Clerk sweep B4, reproduced 2026-08-20 against the live city index
(``<city-root>/.beads/briefs/stack/.index.jsonl``, 88 rows):

    cd <city-root> && <Method 1 selector>   ->  34 entries
    cd /tmp        && <Method 1 selector>   ->  63 entries

Same selector, same index, same briefs. The mechanism is two defects that
compound:

1. ``frontmatter_status()`` resolved every relative index path against
   ``Path.cwd()``. The index carries three path serializations -- 45
   city-root-relative ``.beads/briefs/stack/x.md``, 40 absolute, 3
   briefs-root-relative ``stack/x.md``. From the city root 85 of 88 resolve
   (only the 3 bare rows break); from anywhere else only the 40 absolute ones
   do, so 48 rows become unreadable. The clerk attributed the split to the 3
   bare rows alone -- measured, it is the 45 ``.beads/...`` rows that dominate.
2. ``frontmatter_status()`` then failed OPEN on ``OSError``, returning "" for
   an unreadable brief. "" is not terminal, so all 48 unreadable rows were
   treated as pending. That is fail-open on a filter whose entire job is to
   HIDE resolved briefs, so it re-presents adjudicated work -- the B2.3
   violation the filter exists to prevent.

The fix anchors resolution on the brief root derived from ``stack_dir`` and
fails CLOSED with a stderr warning, so an unreadable brief is skipped loudly
rather than presented silently.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SKILL = REPO_ROOT / "skills" / "present-briefs" / "SKILL.md"


def extract_method1_selector() -> str:
    """Pull the SHIPPED Method 1 heredoc out of SKILL.md.

    The test runs the real embedded program, not a copy of it, so the test
    cannot drift away from what agents actually execute.
    """
    text = SKILL.read_text()
    match = re.search(r"""python3 - "\$STACK_DIR" <<'PY'\n(.*?)\nPY\n""", text, re.S)
    assert match, "could not extract the Method 1 selector heredoc from SKILL.md"
    return match.group(1)


@pytest.fixture(scope="module")
def selector(tmp_path_factory) -> Path:
    path = tmp_path_factory.mktemp("selector") / "method1.py"
    path.write_text(extract_method1_selector())
    return path


def write_brief(path: Path, status: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nstatus: {status}\n---\n\n# brief\n")


@pytest.fixture()
def city(tmp_path: Path) -> Path:
    """A city whose index reproduces all three live path serializations.

    Six briefs, two per serialization: one ready, one adjudicated. A correct
    selector emits exactly the three ready ones from any cwd.
    """
    stack = tmp_path / "city" / ".beads" / "briefs" / "stack"
    rows = []
    for kind, ready_name, done_name in (
        ("cityrel", "10-cityrel-ready-brief.md", "11-cityrel-done-brief.md"),
        ("absolute", "20-abs-ready-brief.md", "21-abs-done-brief.md"),
        ("briefsrel", "30-bare-ready-brief.md", "31-bare-done-brief.md"),
    ):
        for name, status in ((ready_name, "ready"), (done_name, "adjudicated")):
            write_brief(stack / name, status)
            if kind == "cityrel":
                serialized = f".beads/briefs/stack/{name}"
            elif kind == "absolute":
                serialized = str(stack / name)
            else:
                serialized = f"stack/{name}"
            rows.append(f'{{"path": {serialized!r}, "status": "ready", "unlock_count": 1}}')
    (stack / ".index.jsonl").write_text("\n".join(rows).replace("'", '"') + "\n")
    return tmp_path / "city"


def run_selector(selector: Path, stack_dir: Path, cwd: Path):
    return subprocess.run(
        [sys.executable, str(selector), str(stack_dir)],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=False,
    )


def emitted(result) -> set:
    return {line.split(" ", 1)[1] for line in result.stdout.splitlines() if " " in line}


def test_queue_size_is_independent_of_cwd(selector, city, tmp_path):
    """The B4 reproduction, as a test: two cwds, one queue."""
    stack = city / ".beads" / "briefs" / "stack"
    foreign = tmp_path / "elsewhere"
    foreign.mkdir()

    from_city = run_selector(selector, stack, city)
    from_foreign = run_selector(selector, stack, foreign)

    assert emitted(from_city) == emitted(from_foreign), (
        "queue contents depend on the caller's cwd: "
        f"{len(emitted(from_city))} from the city root vs "
        f"{len(emitted(from_foreign))} from elsewhere"
    )


def test_adjudicated_briefs_are_hidden_from_every_serialization(selector, city, tmp_path):
    """All three path forms must resolve, so all three adjudicated briefs hide."""
    stack = city / ".beads" / "briefs" / "stack"
    for cwd in (city, tmp_path):
        result = run_selector(selector, stack, cwd)
        names = {Path(p).name for p in emitted(result)}
        assert names == {
            "10-cityrel-ready-brief.md",
            "20-abs-ready-brief.md",
            "30-bare-ready-brief.md",
        }, f"from cwd={cwd}: emitted {sorted(names)}"


def test_unreadable_brief_fails_closed_and_is_reported(selector, city, tmp_path):
    """An unresolvable row is skipped -- and never silently.

    Fail-open here means an adjudicated brief whose file moved gets re-presented.
    Fail-closed with no warning means work vanishes with no trace. Both are
    wrong; the row is skipped AND named on stderr.
    """
    stack = city / ".beads" / "briefs" / "stack"
    index = stack / ".index.jsonl"
    index.write_text(
        index.read_text()
        + '{"path": ".beads/briefs/stack/99-vanished-brief.md", "status": "ready", "unlock_count": 9}\n'
    )

    result = run_selector(selector, stack, tmp_path)

    assert not any("99-vanished-brief.md" in p for p in emitted(result)), (
        "an unreadable brief was presented; frontmatter_status still fails open"
    )
    assert "99-vanished-brief.md" in result.stderr, (
        "an unreadable brief was dropped silently; the skip must be surfaced"
    )


def test_selector_does_not_resolve_against_cwd(selector):
    """Anchor the fix itself, so the defect class cannot quietly return."""
    source = selector.read_text()
    assert "Path.cwd()" not in source, (
        "the Method 1 selector resolves index paths against Path.cwd(); "
        "index paths are relative to the brief root, not to the caller"
    )
