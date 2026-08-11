#!/bin/sh
# Static smoke test for the commission-work-briefed formula.
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FORMULA="$ROOT/formulas/commission-work-briefed.toml"
RECORD="$ROOT/formulas/brief-record-decision.toml"
DISPATCH="$ROOT/formulas/brief-decision-dispatch.toml"

fail() {
  echo "I'm sorry, I can't do that - $1" >&2
  exit 1
}

[ -f "$FORMULA" ] || fail "missing $FORMULA"
[ -f "$RECORD" ] || fail "missing $RECORD"
[ -f "$DISPATCH" ] || fail "missing $DISPATCH"

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
grep -q 'Interpreted Objective' "$FORMULA" \
  || fail "commissioning does not require an interpreted objective"
grep -q 'Verifiable Goals' "$FORMULA" \
  || fail "commissioning does not require verifiable goals"
grep -q 'Translation Check' "$FORMULA" \
  || fail "commissioning does not require a translation check"
grep -q 'Existing Work Reconciliation' "$FORMULA" \
  || fail "commissioning does not require existing-work reconciliation"
grep -q 'Proposed Dispatch Graph' "$FORMULA" \
  || fail "commissioning does not require a graph"
grep -q 'Selected Formulas' "$FORMULA" \
  || fail "commissioning brief does not require selected formulas"
grep -q 'Live Catalog Evidence' "$FORMULA" \
  || fail "commissioning brief does not require live catalog evidence"
grep -q 'Test Gates' "$FORMULA" \
  || fail "commissioning brief does not require test gates"
grep -q 'Brief Gates' "$FORMULA" \
  || fail "commissioning brief does not require brief gates"
grep -q 'Continuation' "$FORMULA" \
  || fail "commissioning brief does not require a continuation section"
grep -q 'gc agent list' "$FORMULA" \
  || fail "commissioning does not enumerate the live agent catalog"
grep -q 'RUN_LIVE_GC=1 bash tests/superpowers-availability/smoke_test.sh' "$FORMULA" \
  || fail "commissioning does not fail closed on Superpowers availability"
grep -q 'unavailable follow-up work' "$FORMULA" \
  || fail "commissioning does not mark unavailable capabilities as follow-up"
grep -q 'commission-dispatch.v1' "$FORMULA" \
  || fail "commissioning does not emit a continuation contract"
grep -q 'terminal_brief_required = true' "$FORMULA" \
  || fail "continuation contract does not require terminal brief"
grep -q 'Brief gates appear' "$FORMULA" \
  || fail "review does not check brief gates"
grep -q 'Tests or verification gates appear' "$FORMULA" \
  || fail "review does not check test gates"
grep -q 'continuation_contract = "commission-dispatch.v1"' "$RECORD" \
  || fail "brief-record-decision does not preserve commission continuation contract"
grep -q 'commission-dispatch.v1' "$DISPATCH" \
  || fail "brief-decision-dispatch does not consume commission continuation contract"
grep -q 'blocked work item' "$DISPATCH" \
  || fail "brief-decision-dispatch does not require visible blocked work on failed commission approval dispatch"

echo "PASS commission-work-briefed static smoke"
