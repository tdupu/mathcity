#!/usr/bin/env bash
# Run from any directory; uses only a temporary directory, removed on exit.
set -euo pipefail
if ! command -v sage >/dev/null 2>&1; then
    echo "Missing SageMath: install SageMath and put sage on PATH to run this fixture." >&2
    exit 1
fi
pack_root="$(cd "$(dirname "$0")/../.." && pwd)"
fixture="$pack_root/subdomains/latex/skills/generate-graphics/assets/cycle_graph.py"
work_dir="$(mktemp -d)"
trap 'rm -rf "$work_dir"' EXIT
export MPLCONFIGDIR="$work_dir/matplotlib"
export DOT_SAGE="$work_dir/sage"
sage -python "$fixture" "$work_dir/first"
sage -python "$fixture" "$work_dir/second"
sage -python - "$work_dir" "$fixture" <<'PYCHECK'
import hashlib
import json
from pathlib import Path
import sys

root = Path(sys.argv[1])
source = Path(sys.argv[2])
first = json.loads((root / "first/cycle-graph.json").read_text())
second = json.loads((root / "second/cycle-graph.json").read_text())
assert first["computed"] == second["computed"]
assert first["computed"]["spectrum_with_multiplicity"] == [-2, 0, 0, 2]
assert first["computed"]["degrees"] == [2, 2, 2, 2]
assert first["source"]["sha256"] == hashlib.sha256(source.read_bytes()).hexdigest()
assert first["render_review"]["status"] == "pending"
for directory, manifest in [(root / "first", first), (root / "second", second)]:
    archived_source = directory / manifest["source"]["path"]
    assert hashlib.sha256(archived_source.read_bytes()).hexdigest() == manifest["source"]["sha256"]
    for artifact in manifest["artifacts"]:
        path = directory / artifact["path"]
        assert path.stat().st_size > 100
        assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact["sha256"]
    assert all(check["passed"] for check in manifest["checks"])
# Hash checking can detect a subsequently changed asset.
original = root / "first/cycle-graph.png"
original.write_bytes(original.read_bytes() + b"corruption-test")
png_record = next(a for a in first["artifacts"] if a["format"] == "image/png")
assert hashlib.sha256(original.read_bytes()).hexdigest() != png_record["sha256"]
print("PASS: exact finite invariants, semantic rerun, hashes, and stale-asset detection")
PYCHECK
if sage -python "$fixture" "$work_dir/second" >"$work_dir/refusal.log" 2>&1; then
    echo "FAIL: generator overwrote an existing destination" >&2
    exit 1
fi
if ! grep -q 'Output directory already exists' "$work_dir/refusal.log"; then
    cat "$work_dir/refusal.log" >&2
    exit 1
fi
echo "PASS: existing destination rejected"
