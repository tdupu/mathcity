#!/bin/sh
# Static smoke test for the commission-work-briefed formula.
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FORMULA="$ROOT/formulas/commission-work-briefed.toml"

fail() {
  echo "I'm sorry, I can't do that - $1" >&2
  exit 1
}

[ -f "$FORMULA" ] || fail "missing $FORMULA"

python3 - "$FORMULA" <<'PY'
import sys
import tomllib

path = sys.argv[1]
with open(path, "rb") as handle:
    data = tomllib.load(handle)

if data.get("formula") != "commission-work-briefed":
    raise SystemExit("formula name mismatch")

steps = data.get("steps", [])
ids = [step.get("id") for step in steps]
expected = [
    "intake-objective",
    "reconcile-existing-work",
    "design-dispatch-plan",
    "review-dispatch-plan",
    "file-brief",
]
if ids != expected:
    raise SystemExit(f"unexpected steps: {ids!r}")

if steps[-1].get("id") != "file-brief":
    raise SystemExit("terminal step is not file-brief")

metadata = steps[-1].get("metadata", {})
if metadata.get("gc.brief.source_formula") != "commission-work-briefed":
    raise SystemExit("terminal brief metadata missing source formula")
PY

grep -q 'Original Request' "$FORMULA" \
  || fail "commissioning does not preserve original request"
grep -q 'Existing Work Reconciliation' "$FORMULA" \
  || fail "commissioning does not require existing-work reconciliation"
grep -q 'Proposed Dispatch Graph' "$FORMULA" \
  || fail "commissioning does not require a graph"
grep -q 'commission-dispatch.v1' "$FORMULA" \
  || fail "commissioning does not emit a continuation contract"
grep -q 'terminal_brief_required = true' "$FORMULA" \
  || fail "continuation contract does not require terminal brief"
grep -q 'Brief gates appear' "$FORMULA" \
  || fail "review does not check brief gates"
grep -q 'Tests or verification gates appear' "$FORMULA" \
  || fail "review does not check test gates"

echo "PASS commission-work-briefed static smoke"
