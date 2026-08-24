#!/usr/bin/env bash
# Static resolution/behaviour test for the revise-return path (#209, fix
# candidate 2). The pack has NO live formula-execution harness, so this test
# pins the formula + order SHAPE the way the sibling brief-decision-dispatch
# smoke test does: it parses the two TOMLs and asserts the trigger condition,
# the vapor claim shape, the idempotency ledger, and the re-deposit-via-the-
# sanctioned-path contract.
#
# The behaviour under test: a `brief.decided` verdict of `revise` must
# mechanically re-deposit a fresh brief from the decision record's revision
# instructions (the `reason` field) instead of dying silently. Before #209 the
# revise arm of brief-decision-dispatch created a follow-up bead that nothing
# turned back into a brief; this formula is that missing consumer.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
FORMULA="$ROOT/formulas/revise-return.toml"
ORDER="$ROOT/orders/revise-return.toml"

test -f "$FORMULA"
test -f "$ORDER"

python3 - "$FORMULA" "$ORDER" <<'PY'
import sys
import tomllib

formula_path, order_path = sys.argv[1:]
formula = tomllib.load(open(formula_path, "rb"))
order = tomllib.load(open(order_path, "rb"))

# --- formula identity + claim shape --------------------------------------
assert formula["formula"] == "revise-return", formula.get("formula")
# vapor: same staffing lesson as brief-decision-dispatch -- a graph-v2 root is
# a blocked container the demand probe never counts; a vapor root is the shape
# gc staffs to a pool via a city event order.
assert formula["phase"] == "vapor", formula.get("phase")
assert formula["catalog"]["name"] == "revise-return"

# --- the idempotency ledger rides in a step's metadata -------------------
assert any(
    str(step.get("metadata", {}).get("gc.brief.revise_ledger", "")).endswith(
        "revise-returned.jsonl"
    )
    for step in formula["steps"]
), "no step declares the revise-returned.jsonl ledger in gc.brief.revise_ledger"

# --- the order is the brief.decided event trigger ------------------------
assert order["order"]["formula"] == "revise-return"
assert order["order"]["trigger"] == "event"
assert order["order"]["on"] == "brief.decided"
assert order["order"]["scope"] == "city"
assert order["order"]["pool"] == "mathcity.brief-operator"
PY

# --- behaviour contract, asserted against the description prose -----------
# The revise branch: acts ONLY on decision == "revise" records.
grep -Fq 'revise' "$FORMULA"
# Re-deposit through the EXISTING sanctioned deposit path (brief-prep pour),
# NOT a hand-written governed brief path (POLICY B2.8).
grep -Fq 'bd mol pour brief-prep' "$FORMULA"
# The revision instructions come from the decision record's reason field.
grep -Fq 'reason' "$FORMULA"
grep -Fq 'source_bead' "$FORMULA"
# Idempotency: a success ledger line marks a slug re-deposited; repeated /
# coalesced brief.decided events are safe.
grep -Fq 'revise-returned.jsonl' "$FORMULA"
grep -Fq 'already re-deposited' "$FORMULA"

echo "PASS revise-return static smoke"
