#!/usr/bin/env bash
# Smoke test for smoke-test-briefed.toml (self-test, F6.1 baseline)
# Run from rig root: bash mathcity/tests/smoke-test-briefed-self/smoke_test.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FORMULA_PATH="$PACK_ROOT/formulas/smoke-test-briefed.toml"
PASS=0
FAIL=0
RESULTS=()

check() {
  local desc="$1" result="$2"
  if [ "$result" = "ok" ]; then
    RESULTS+=("  PASS: $desc")
    PASS=$((PASS+1))
  else
    RESULTS+=("  FAIL: $desc — $result")
    FAIL=$((FAIL+1))
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
with open(sys.argv[1], "rb") as f:
    d = tomllib.load(f)
cat = d.get("catalog", {})
missing = [k for k in ["name","description"] if not cat.get(k)]
missing += [k for k in ["formula","version"] if not d.get(k)]
if missing:
    print("MISSING: " + ", ".join(missing), file=sys.stderr); sys.exit(1)
PY

# Check 4: terminal step is file-brief / brief-finalize / workflow-finalize
python3 - "$FORMULA_PATH" << 'PY' && check "terminal step is a brief step" "ok" \
  || check "terminal step is a brief step" "terminal step is not file-brief/brief-finalize/workflow-finalize"
import tomllib, sys
with open(sys.argv[1], "rb") as f:
    d = tomllib.load(f)
steps = d.get("steps", [])
if not steps:
    print("NO STEPS", file=sys.stderr); sys.exit(1)
last = steps[-1]["id"]
if last not in {"file-brief","brief-finalize","workflow-finalize"}:
    print(f"last step: {last}", file=sys.stderr); sys.exit(1)
PY

# Check 5: gc formula show (soft — requires the pack installed to the live city)
if command -v gc >/dev/null 2>&1; then
  if gc formula show smoke-test-briefed >/dev/null 2>&1; then
    check "gc formula show smoke-test-briefed succeeds" "ok"
  else
    RESULTS+=("  SKIP: gc formula show — formula not loaded into the live city yet (expected pre-install)")
  fi
else
  RESULTS+=("  SKIP: gc formula show — gc not on PATH")
fi

# Check 6: testing-work SKILL.md exists
[ -f "$PACK_ROOT/subdomains/dev/skills/testing-work/SKILL.md" ] \
  && check "testing-work SKILL.md exists" "ok" \
  || check "testing-work SKILL.md exists" "not found"

# Summary
echo ""
echo "smoke-test-briefed self-test results:"
for r in "${RESULTS[@]}"; do echo "$r"; done
echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "PASS — $PASS/$((PASS+FAIL)) checks passed"
  exit 0
else
  echo "FAIL — $FAIL/$((PASS+FAIL)) checks failed"
  exit 1
fi
