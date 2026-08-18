#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FORMULA="$ROOT/formulas/brief-decision-dispatch.toml"
ORDER="$ROOT/orders/brief-decision-dispatch.toml"
CHECK="$ROOT/assets/scripts/checks/brief-decision-dispatched-check.sh"

test -f "$FORMULA"
test -f "$ORDER"
test -f "$CHECK"

python3 - "$FORMULA" "$ORDER" <<'PY'
import sys
import tomllib

formula_path, order_path = sys.argv[1:]
formula = tomllib.load(open(formula_path, "rb"))
order = tomllib.load(open(order_path, "rb"))

assert formula["formula"] == "brief-decision-dispatch"
assert formula["phase"] == "vapor"
assert formula["catalog"]["name"] == "brief-decision-dispatch"
assert any(
    step.get("metadata", {}).get("gc.brief.dispatch_ledger", "").endswith("decisions-dispatched.jsonl")
    for step in formula["steps"]
)
assert order["order"]["formula"] == "brief-decision-dispatch"
assert order["order"]["trigger"] == "event"
assert order["order"]["on"] == "brief.decided"
assert order["order"]["pool"] == "mathcity.brief-operator"
PY

grep -Fq 'commission-dispatch.v1' "$FORMULA"
grep -Fq 'pending_retry' "$FORMULA"
grep -Fq 'dispatched_at' "$FORMULA"
grep -Fq 'pending_retry' "$CHECK"
grep -Fq 'dispatched_at' "$CHECK"

echo "PASS brief-decision-dispatch static smoke"
