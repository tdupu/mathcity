#!/usr/bin/env bash
# Smoke test for brief-briefed-base.formula.toml (F6.1 gate) — the abstract base
# owning the shared file-brief terminal + brief-producer.v1 schema.
# Run from rig root: bash mathcity/tests/brief-briefed-base/smoke_test.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FORMULA_PATH="$PACK_ROOT/formulas/brief-briefed-base.formula.toml"
PASS=0
FAIL=0
RESULTS=()

check() {
  local desc="$1" result="$2"
  if [ "$result" = "ok" ]; then
    RESULTS+=("  PASS: $desc"); PASS=$((PASS+1))
  else
    RESULTS+=("  FAIL: $desc — $result"); FAIL=$((FAIL+1))
  fi
}

# Check 1: file exists
[ -f "$FORMULA_PATH" ] && check "formula file exists" "ok" \
  || check "formula file exists" "not found at $FORMULA_PATH"

# Check 2: TOML parses
if python3 -c "import tomllib; tomllib.load(open('$FORMULA_PATH','rb'))" 2>/dev/null; then
  check "TOML parses without error" "ok"
else
  check "TOML parses without error" "tomllib parse failed"
fi

# Check 3: catalog fields present
python3 - "$FORMULA_PATH" << 'PY' && check "catalog fields present (name, description, formula, version)" "ok" \
  || check "catalog fields present" "missing fields"
import tomllib, sys
d = tomllib.load(open(sys.argv[1], "rb"))
cat = d.get("catalog", {})
missing = [k for k in ["name","description"] if not cat.get(k)]
missing += [k for k in ["formula","version"] if not d.get(k)]
if missing:
    print("MISSING: " + ", ".join(missing), file=sys.stderr); sys.exit(1)
PY

# Check 4: THREE canonical step ids, terminal is file-brief. The base MUST declare
# all three so children override intake/compose-body in position and inherit
# file-brief; if the base lost intake/compose-body, a child's overrides would
# append past the terminal and break F8.1.
python3 - "$FORMULA_PATH" << 'PY' && check "steps = intake, compose-body, file-brief (terminal file-brief)" "ok" \
  || check "steps shape" "step ids/order/terminal not as expected"
import tomllib, sys
d = tomllib.load(open(sys.argv[1], "rb"))
ids = [s["id"] for s in d.get("steps", [])]
if ids != ["intake","compose-body","file-brief"]:
    print(f"step ids: {ids}", file=sys.stderr); sys.exit(1)
if ids[-1] not in {"file-brief","brief-finalize","workflow-finalize"}:
    print(f"terminal: {ids[-1]}", file=sys.stderr); sys.exit(1)
PY

# Check 5: the terminal owns the brief-producer.v1 contract, with PARAMETERIZED
# provenance ({{source_formula}}) so each child stamps its own leaf name.
python3 - "$FORMULA_PATH" << 'PY' && check "file-brief owns brief-producer.v1 schema with parameterized {{source_formula}} provenance" "ok" \
  || check "file-brief terminal metadata" "producer_contract/path/parameterized source_formula missing"
import tomllib, sys
d = tomllib.load(open(sys.argv[1], "rb"))
md = d["steps"][-1].get("metadata", {})
if md.get("gc.brief.producer_contract") != "brief-producer.v1":
    print(f"producer_contract={md.get('gc.brief.producer_contract')!r}", file=sys.stderr); sys.exit(1)
if not md.get("gc.brief.path"):
    print("gc.brief.path missing", file=sys.stderr); sys.exit(1)
# provenance must be parameterized, NOT a hardcoded literal, so children override it
if md.get("gc.brief.source_formula") != "{{source_formula}}":
    print(f"source_formula={md.get('gc.brief.source_formula')!r} (expected the {{{{source_formula}}}} var)", file=sys.stderr); sys.exit(1)
PY

# Check 6: the provenance + terminal-action vars exist so children can override them
python3 - "$FORMULA_PATH" << 'PY' && check "source_formula + terminal_action vars declared (child-overridable)" "ok" \
  || check "base contract vars" "source_formula/terminal_action var missing"
import tomllib, sys
d = tomllib.load(open(sys.argv[1], "rb"))
v = d.get("vars", {})
if v.get("source_formula", {}).get("default") != "brief-briefed-base":
    print(f"source_formula default={v.get('source_formula')}", file=sys.stderr); sys.exit(1)
ta = v.get("terminal_action", {})
if not ta.get("enum") or "dispatch-fix" not in ta["enum"] or "file-issue" not in ta["enum"]:
    print(f"terminal_action enum={ta.get('enum')}", file=sys.stderr); sys.exit(1)
PY

# Check 7: intake + compose-body are FAIL-CLOSED abstract placeholders (they must
# refuse if run directly, so a forgotten override never proceeds with no intake).
python3 - "$FORMULA_PATH" << 'PY' && check "abstract intake + compose-body fail closed if run un-overridden" "ok" \
  || check "abstract placeholders fail-closed" "an abstract step does not fail closed"
import tomllib, sys
d = tomllib.load(open(sys.argv[1], "rb"))
by_id = {s["id"]: s for s in d["steps"]}
for sid in ("intake", "compose-body"):
    desc = by_id[sid]["description"]
    if "BLOCKED" not in desc or "drain-ack" not in desc:
        print(f"{sid} is not a fail-closed placeholder", file=sys.stderr); sys.exit(1)
PY

# Check 8: no model names in run_targets (F1.3 / F3.3)
python3 - "$FORMULA_PATH" << 'PY' && check "no model names in run_targets (F1.3/F3.3)" "ok" \
  || check "run_target model-name audit" "a model name appears in a run_target"
import tomllib, sys
d = tomllib.load(open(sys.argv[1], "rb"))
bad = {"opus","sonnet","haiku","fable"}
for s in d.get("steps", []):
    rt = s.get("metadata", {}).get("gc.run_target", "")
    if rt.strip().lower() in bad:
        print(f"step {s['id']} run_target={rt}", file=sys.stderr); sys.exit(1)
PY

# Check 9: the base never EXECUTES a commissioned action (no bare gh/gc sling)
if grep -Eq '^[[:space:]]*(gh issue create|gh pr create|gc sling)([[:space:]]|$)' "$FORMULA_PATH"; then
  check "base never EXECUTES a commissioned action (prose-only ok)" "a bare action command is present"
else
  check "base never EXECUTES a commissioned action (prose-only ok)" "ok"
fi

# Summary
echo ""
echo "brief-briefed-base smoke-test results:"
for r in "${RESULTS[@]}"; do echo "$r"; done
echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "PASS — $PASS/$((PASS+FAIL)) checks passed"; exit 0
else
  echo "FAIL — $FAIL/$((PASS+FAIL)) checks failed"; exit 1
fi
