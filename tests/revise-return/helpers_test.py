"""#209: test the deposit helpers that ship INLINE in revise-return.toml.

WHY THIS EXISTS

`tests/revise-return/smoke_test.sh` says it plainly: *"The pack has NO live
formula-execution harness"*, so it pins the formula's SHAPE by parsing TOML.
`refile_test.sh` covers the three functions that live in
`assets/scripts/revise-return-lib.sh`. Between them they cover everything
except the part that actually re-deposits.

The deposit step defines FIVE more functions inside the TOML string --
`is_redeposited`, `pending_retry_count`, `next_slug`, `ledger_line`,
`redeposit_slug` -- and nothing could reach them. That is not a hypothetical
gap. `PACK_ROOT` resolved with one `dirname` too few, pointed `LIB` at
`<pack-root>/orders/assets/scripts/...`, and the step exited 1 BEFORE ANY SCAN
-- so every revise verdict was recorded, the order fired, the wisp was claimed
and closed, and no brief was ever re-deposited. The formula's own comment names
why it survived: *"This is the only dirname-chain in the pack, so it had no
sibling to be checked against."* Inline-in-formula logic has no sibling and no
test.

So this harness extracts the shell that SHIPS -- via `tomllib`, so what is
tested is the rendered string after TOML unescaping, not a copy -- pulls out the
top-level function definitions, and exercises them in a scratch tree. The
formula is not modified: a refactor into the lib would be the better home, but
it changes what a live city executes when the pin advances, and this gets the
coverage without that risk.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FORMULA = ROOT / "formulas" / "revise-return.toml"

#: Every top-level helper the deposit step defines inline.
EXPECTED_HELPERS = (
    "is_redeposited",
    "pending_retry_count",
    "next_slug",
    "ledger_line",
    "redeposit_slug",
)


def _shipped_shell() -> str:
    """The rendered bash of the deposit step, exactly as a runtime would see it."""
    data = tomllib.loads(FORMULA.read_text(encoding="utf-8"))
    blocks: list[str] = []
    for step in data.get("steps", []):
        text = str(step.get("description", ""))
        blocks.extend(re.findall(r"```bash\n(.*?)```", text, re.DOTALL))
    assert blocks, "no ```bash block found in revise-return.toml"
    return "\n".join(blocks)


def _extract_functions(shell: str, names: tuple[str, ...]) -> str:
    """Just the `name() { ... }` definitions, by brace counting.

    The step's top level resolves PACK_ROOT, sources the lib and can `exit 1`,
    so the whole block cannot simply be sourced. Taking the definitions alone
    is what makes the helpers reachable without running the step.
    """
    out: list[str] = []
    lines = shell.splitlines()
    for name in names:
        start = next(
            (i for i, line in enumerate(lines) if re.match(rf"^{re.escape(name)}\(\)\s*\{{", line)),
            None,
        )
        assert start is not None, f"helper {name}() not found in the shipped shell"
        depth = 0
        body: list[str] = []
        for line in lines[start:]:
            depth += line.count("{") - line.count("}")
            body.append(line)
            if depth <= 0:
                break
        assert depth <= 0, f"helper {name}() never closed its brace"
        out.append("\n".join(body))
    return "\n\n".join(out)


def _run(snippet: str, tmp_path: Path, *, ledger: str = "") -> subprocess.CompletedProcess:
    ledger_path = tmp_path / "revise-returned.jsonl"
    if ledger:
        ledger_path.write_text(ledger, encoding="utf-8")
    script = tmp_path / "harness.sh"
    script.write_text(
        "set -uo pipefail\n"
        f'ROOT="{tmp_path}"\n'
        f'LEDGER="{ledger_path}"\n'
        + _extract_functions(_shipped_shell(), EXPECTED_HELPERS)
        + "\n"
        + snippet
        + "\n",
        encoding="utf-8",
    )
    return subprocess.run(
        ["bash", str(script)], capture_output=True, text=True, cwd=tmp_path
    )


def test_every_expected_helper_is_present_in_the_shipped_shell():
    """If a helper is renamed or moved, this harness must fail rather than skip it.

    A test that silently stops covering what it names is worse than no test --
    that is the shape of the defect this file was written for.
    """
    text = _extract_functions(_shipped_shell(), EXPECTED_HELPERS)
    for name in EXPECTED_HELPERS:
        assert f"{name}()" in text


@pytest.mark.parametrize(
    "slug,expected",
    [
        ("mc-abc-brief", "mc-abc-brief-r1"),
        ("mc-abc-brief-r1", "mc-abc-brief-r2"),
        ("mc-abc-brief-r9", "mc-abc-brief-r10"),
        ("mc-abc-brief-r10", "mc-abc-brief-r11"),
        # A slug that merely CONTAINS -r<digit> mid-name must version its tail,
        # not its middle: `%-r*` strips the shortest match from the right.
        ("a-r1-thing-r2", "a-r1-thing-r3"),
        # Non-numeric tail is not a revision counter, so it gains one.
        ("mc-abc-rX", "mc-abc-rX-r1"),
        ("mc-abc-r", "mc-abc-r-r1"),
    ],
)
def test_next_slug_versions_the_tail(tmp_path: Path, slug: str, expected: str):
    """Re-deposit names must advance, and must never collide with the original."""
    proc = _run(f'next_slug "{slug}"', tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == expected


def test_is_redeposited_requires_a_success_line(tmp_path: Path):
    """A pending_retry line must NOT count as done, or a failure becomes permanent.

    The idempotency ledger carries both outcomes for the same slug. Matching the
    slug alone would read a failed attempt as a completed one and the brief
    would never come back -- which is this issue's whole symptom.
    """
    ledger = (
        json.dumps({"brief_slug": "mc-1", "pending_retry": True, "failed_at": "t"}) + "\n"
        + json.dumps({"brief_slug": "mc-2", "redeposited_slug": "mc-2-r1", "redeposited_at": "t"}) + "\n"
    )
    proc = _run(
        'if is_redeposited "mc-1"; then echo ONE-DONE; else echo ONE-PENDING; fi\n'
        'if is_redeposited "mc-2"; then echo TWO-DONE; else echo TWO-PENDING; fi',
        tmp_path,
        ledger=ledger,
    )
    assert proc.returncode == 0, proc.stderr
    assert "ONE-PENDING" in proc.stdout
    assert "TWO-DONE" in proc.stdout


def test_is_redeposited_is_false_with_no_ledger(tmp_path: Path):
    """First run: no ledger file. Absence must read as "not yet", never as done."""
    proc = _run('if is_redeposited "mc-1"; then echo DONE; else echo PENDING; fi', tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert "PENDING" in proc.stdout


def test_is_redeposited_does_not_match_a_different_slug(tmp_path: Path):
    """`mc-1` must not be satisfied by `mc-12`'s success line."""
    ledger = json.dumps(
        {"brief_slug": "mc-12", "redeposited_slug": "mc-12-r1", "redeposited_at": "t"}
    ) + "\n"
    proc = _run(
        'if is_redeposited "mc-1"; then echo DONE; else echo PENDING; fi',
        tmp_path,
        ledger=ledger,
    )
    assert proc.returncode == 0, proc.stderr
    assert "PENDING" in proc.stdout, (
        "a longer slug's success line must not satisfy a shorter slug -- that "
        "would strand mc-1 permanently"
    )


def test_pending_retry_count_counts_only_this_slug(tmp_path: Path):
    """The retry-limit guard (>= 3 -> terminal) is only sound if the count is exact."""
    ledger = "".join(
        json.dumps({"brief_slug": slug, "pending_retry": True, "failed_at": "t"}) + "\n"
        for slug in ("mc-1", "mc-1", "mc-2", "mc-1")
    )
    proc = _run('pending_retry_count "mc-1"; pending_retry_count "mc-2"', tmp_path, ledger=ledger)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.split() == ["3", "1"]


def test_pending_retry_count_is_zero_with_no_ledger(tmp_path: Path):
    """Must print 0, not empty: the caller compares it with `-ge 3` arithmetically."""
    proc = _run('pending_retry_count "mc-1"', tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "0"


def test_ledger_line_shapes_differ_by_outcome(tmp_path: Path):
    """Success carries `redeposited_at`; failure carries `pending_retry`.

    `is_redeposited` keys on exactly that difference, so these two shapes are a
    contract between the two helpers rather than cosmetic.
    """
    if not _has_jq():
        pytest.skip("jq not installed; ledger_line is a jq wrapper")
    proc = _run(
        'ledger_line "mc-1" "mc-src" "did a thing" "mc-1-r1" success\n'
        'ledger_line "mc-1" "mc-src" "tried a thing" "mc-1-r1" failure',
        tmp_path,
    )
    assert proc.returncode == 0, proc.stderr
    ok, bad = (json.loads(line) for line in proc.stdout.strip().splitlines())
    assert ok["redeposited_at"] and ok["redeposited_slug"] == "mc-1-r1"
    assert "pending_retry" not in ok
    assert bad["pending_retry"] is True and "redeposited_at" not in bad
    assert bad["failed_at"]


def test_redeposit_slug_terminalizes_a_record_with_no_source_bead(tmp_path: Path):
    """No source bead means brief-prep can never pour, so retrying forever is wrong.

    This is the one deposit-path branch reachable with no `gc`, no `bd` and no
    live city, which is why it is the branch asserted here.
    """
    if not _has_jq():
        pytest.skip("jq not installed; the terminalize branch writes via jq")
    decisions = tmp_path / "decisions"
    decisions.mkdir(parents=True, exist_ok=True)
    (decisions / "mc-9.toml").write_text(
        'decision = "revise"\nreason = "please tighten section 4"\n', encoding="utf-8"
    )

    proc = _run('redeposit_slug "mc-9"', tmp_path)

    assert proc.returncode == 0, proc.stderr
    assert "TERMINAL mc-9: missing-source-bead" in proc.stdout
    row = json.loads((tmp_path / "revise-returned.jsonl").read_text().strip())
    assert row["action"] == "undepositable"
    assert row["undepositable_reason"] == "missing-source-bead"
    assert row["redeposited_at"], "a terminal row must be a SUCCESS-shaped line"


def test_redeposit_slug_skips_a_non_revise_record(tmp_path: Path):
    """An approve verdict must not be re-deposited by the revise consumer."""
    decisions = tmp_path / "decisions"
    decisions.mkdir(parents=True, exist_ok=True)
    (decisions / "mc-8.toml").write_text(
        'decision = "approve"\nreason = "looks good"\nsource_bead = "mc-src"\n',
        encoding="utf-8",
    )

    proc = _run('redeposit_slug "mc-8"', tmp_path)

    assert proc.returncode == 0, proc.stderr
    assert "not a revise (approve): mc-8" in proc.stdout
    assert not (tmp_path / "revise-returned.jsonl").exists() or not (
        tmp_path / "revise-returned.jsonl"
    ).read_text().strip()


def test_redeposit_slug_warns_on_a_missing_record(tmp_path: Path):
    """A slug with no decision record is reported, not silently skipped."""
    (tmp_path / "decisions").mkdir(parents=True, exist_ok=True)

    proc = _run('redeposit_slug "mc-nope"', tmp_path)

    assert proc.returncode == 0, proc.stderr
    assert "WARN: missing record for mc-nope" in proc.stdout


def _has_jq() -> bool:
    from shutil import which

    return which("jq") is not None
