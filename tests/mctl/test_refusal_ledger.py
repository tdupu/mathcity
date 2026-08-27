"""Every dashboard/CLI/MCP refusal is recorded durably (bead mc-rmqt).

The precondition for mc-3q4v's refusal -> defect -> repair auto-routing is that
a refusal is *written down*. Before this ledger, a `MutationError` aborted
before any `EffectPlan` -- so no trace row was emitted -- and was caught at the
presentation boundaries (`cli.py`, `mcp_server.py`), formatted for display, and
discarded. The `trace:` id shown to the operator dereferenced to nothing.

These tests fix the trace id shown to the operator to a durable `refused` row
in the same append-only trace store successful mutations use, so it resolves
through `mctl trace show` and the MCP `trace_show` tool. The observed-failing
case for every guarantee below is "before the ledger, the row did not exist and
the id did not resolve" (P6.2).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import stat
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

MCTL = SCRIPTS_ROOT / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"

TRACE_ID_RE = re.compile(r"^trace_id:\s*(\S+)\s*$", re.MULTILINE)


def runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    source_checkout = tmp_path / "source_checkout"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, source_checkout)
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(
        BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track"
    )
    (rig_root / ".beads" / "decisions-track" / "manifest.jsonl").write_text(
        "", encoding="utf-8"
    )
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return city_root, rig_root


def run_mctl(*args: str, beads_fixture: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    if beads_fixture is not None:
        env["MCTL_BEADS_FIXTURE"] = str(beads_fixture)
    return subprocess.run(
        [sys.executable, str(MCTL), *args],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def beads_fixture(rig_root: Path) -> Path:
    return rig_root / ".beads" / "issues.jsonl"


def trace_rows(rig_root: Path) -> list[dict[str, object]]:
    traces = rig_root / ".beads" / "mctl" / "traces"
    rows: list[dict[str, object]] = []
    if not traces.is_dir():
        return rows
    for path in sorted(traces.glob("*.jsonl")):
        rows.extend(
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    return rows


def refused_rows(rig_root: Path) -> list[dict[str, object]]:
    return [row for row in trace_rows(rig_root) if row.get("phase") == "refused"]


def operator_trace_id(result: subprocess.CompletedProcess[str]) -> str:
    match = TRACE_ID_RE.search(result.stderr)
    assert match, f"no trace_id shown to the operator in stderr:\n{result.stderr}"
    return match.group(1)


# --- CLI briefs surface (cli.py:639) ---------------------------------------


def test_cli_briefs_refusal_writes_a_durable_row(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)

    # `defer` with no --reason refuses with MCTL_MUTATION_REASON_REQUIRED,
    # the canonical contract-fault code from the mc-3q4v brief.
    result = run_mctl(
        "briefs", "defer", "mc-open", "--until", "2999-01-01",
        "--city", str(city_root), "--rig", "mathcity",
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    assert "MCTL_MUTATION_REASON_REQUIRED" in result.stderr

    rows = refused_rows(rig_root)
    assert rows, "the refusal left no durable row in the trace ledger"
    row = rows[0]
    assert row["code"] == "MCTL_MUTATION_REASON_REQUIRED"
    assert row["recorded_at"], "the refusal row carries no timestamp"
    assert str(row["surface"]).startswith("cli"), row["surface"]
    assert row["trace_id"] == operator_trace_id(result)
    # Context is preserved for later classification.
    assert row["diagnostic"]["facts"]["rig_name"] == "mathcity"


def test_operator_trace_id_now_resolves(tmp_path: Path):
    """The bead's core complaint: the id shown to the operator resolved to nothing."""
    city_root, rig_root = runtime_fixture(tmp_path)

    refusal = run_mctl(
        "briefs", "defer", "mc-open", "--until", "2999-01-01",
        "--city", str(city_root), "--rig", "mathcity",
        beads_fixture=beads_fixture(rig_root),
    )
    trace_id = operator_trace_id(refusal)

    shown = run_mctl(
        "trace", "show", trace_id,
        "--city", str(city_root), "--rig", "mathcity", "--json",
        beads_fixture=beads_fixture(rig_root),
    )

    assert shown.returncode == 0, shown.stderr
    record = json.loads(shown.stdout)["trace"]
    assert record["trace_id"] == trace_id
    assert record["outcome"] == "refused"
    assert record["refusal"]["code"] == "MCTL_MUTATION_REASON_REQUIRED"


def test_cli_work_refusal_writes_a_durable_row(tmp_path: Path):
    """The second CLI catch site (cli.py:750) records too."""
    city_root, rig_root = runtime_fixture(tmp_path)

    result = run_mctl(
        "work", "dispatch", "mc-does-not-exist",
        "--city", str(city_root), "--rig", "mathcity",
        beads_fixture=beads_fixture(rig_root),
    )

    assert result.returncode != 0
    rows = refused_rows(rig_root)
    assert rows, "the work refusal left no durable row"
    assert str(rows[0]["surface"]).startswith("cli")
    assert rows[0]["trace_id"] == operator_trace_id(result)


# --- MCP surface (mcp_server.py:3063) --------------------------------------


def _mcp_call(instance, name: str, arguments: dict) -> dict:
    return instance.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
    )


def test_mcp_refusal_writes_a_durable_row_and_resolves(tmp_path: Path):
    from mctl_core import mcp_server

    city_root, rig_root = runtime_fixture(tmp_path)
    instance = mcp_server.MctlMcpServer(
        default_city=city_root,
        default_rig="mathcity",
        client_class="internal",
        env={"MCTL_BEADS_FIXTURE": str(beads_fixture(rig_root))},
    )

    # briefs_defer with an empty reason refuses in the core.
    response = _mcp_call(
        instance,
        "briefs_defer",
        {"brief_id": "mc-open", "until": "2999-01-01", "reason": "", "dry_run": False},
    )

    payload = json.loads(response["result"]["content"][0]["text"])
    codes = {d["code"] for d in payload["diagnostics"]}
    assert "MCTL_MUTATION_REASON_REQUIRED" in codes
    envelope_trace_id = payload["trace_id"]

    rows = refused_rows(rig_root)
    assert rows, "the MCP refusal left no durable row"
    assert str(rows[0]["surface"]).startswith("mcp")
    assert rows[0]["trace_id"] == envelope_trace_id

    shown = _mcp_call(instance, "trace_show", {"trace_id": envelope_trace_id})
    record = json.loads(shown["result"]["content"][0]["text"])["trace"]
    assert record["outcome"] == "refused"


# --- fail-loud on an unwritable ledger (P6.1 / P6.2) -----------------------


def test_unwritable_ledger_is_loud_and_does_not_swallow_the_refusal(tmp_path: Path):
    """A ledger write that fails must announce itself, without losing the refusal.

    The observed-failing case for the fail-loud path: the traces directory is
    made read-only, so `record_refusal` cannot append. Both the original
    refusal AND a distinct MCTL_REFUSAL_LEDGER_UNWRITABLE signal must surface.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    traces = rig_root / ".beads" / "mctl" / "traces"
    traces.mkdir(parents=True)
    read_only = stat.S_IRUSR | stat.S_IXUSR
    traces.chmod(read_only)
    try:
        result = run_mctl(
            "briefs", "defer", "mc-open", "--until", "2999-01-01",
            "--city", str(city_root), "--rig", "mathcity",
            beads_fixture=beads_fixture(rig_root),
        )
    finally:
        traces.chmod(stat.S_IRWXU)

    assert result.returncode != 0
    # The original refusal is not lost behind the IO failure.
    assert "MCTL_MUTATION_REASON_REQUIRED" in result.stderr
    # The ledger failure announces itself at the point of failure.
    assert "MCTL_REFUSAL_LEDGER_UNWRITABLE" in result.stderr


# --- unit: fold understands the refused phase ------------------------------


def test_fold_reports_a_refused_only_trace_as_refused():
    from mctl_core import trace

    rows = [
        {
            "trace_id": "t-1",
            "phase": "refused",
            "code": "MCTL_MUTATION_REASON_REQUIRED",
            "surface": "cli:briefs.defer",
            "recorded_at": "2026-08-27T00:00:00Z",
        }
    ]
    record = trace.fold(rows, "t-1")
    assert record is not None
    assert record["outcome"] == "refused"
    assert record["refusal"]["code"] == "MCTL_MUTATION_REASON_REQUIRED"
