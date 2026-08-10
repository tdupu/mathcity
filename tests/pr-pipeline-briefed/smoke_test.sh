#!/usr/bin/env bash
# Smoke test for pr-pipeline-briefed.formula.toml (F6.1 gate).
# Run from rig root: bash mathcity/tests/pr-pipeline-briefed/smoke_test.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FORMULA_PATH="$PACK_ROOT/formulas/pr-pipeline-briefed.formula.toml"
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

# Check 3: catalog fields present (name, description, formula, version)
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

# Check 4: exactly three steps intake -> compose-body -> file-brief, terminal is a brief step
python3 - "$FORMULA_PATH" << 'PY' && check "steps = intake, compose-body, file-brief (terminal brief step)" "ok" \
  || check "steps shape" "step ids/order/terminal not as expected"
import tomllib, sys
with open(sys.argv[1], "rb") as f:
    d = tomllib.load(f)
ids = [s["id"] for s in d.get("steps", [])]
if ids != ["intake","compose-body","file-brief"]:
    print(f"step ids: {ids}", file=sys.stderr); sys.exit(1)
if ids[-1] not in {"file-brief","brief-finalize","workflow-finalize"}:
    print(f"terminal: {ids[-1]}", file=sys.stderr); sys.exit(1)
PY

# Check 5: terminal file-brief carries brief-producer.v1 contract metadata
python3 - "$FORMULA_PATH" << 'PY' && check "file-brief carries brief-producer.v1 metadata" "ok" \
  || check "file-brief metadata" "producer_contract/path/source_formula missing on terminal step"
import tomllib, sys
with open(sys.argv[1], "rb") as f:
    d = tomllib.load(f)
term = d["steps"][-1]
md = term.get("metadata", {})
need = {"gc.brief.producer_contract":"brief-producer.v1", "gc.brief.source_formula":"pr-pipeline-briefed"}
for k,v in need.items():
    if md.get(k) != v:
        print(f"{k}={md.get(k)!r} expected {v!r}", file=sys.stderr); sys.exit(1)
if not md.get("gc.brief.path"):
    print("gc.brief.path missing", file=sys.stderr); sys.exit(1)
PY

# Check 6: required vars declared (source_bead, brief_slug) with brief_slug pattern
python3 - "$FORMULA_PATH" << 'PY' && check "required vars source_bead + brief_slug (with pattern) declared" "ok" \
  || check "required vars" "source_bead/brief_slug not declared as required or pattern missing"
import tomllib, sys
with open(sys.argv[1], "rb") as f:
    d = tomllib.load(f)
v = d.get("vars", {})
ok = v.get("source_bead",{}).get("required") is True
ok = ok and v.get("brief_slug",{}).get("required") is True
ok = ok and bool(v.get("brief_slug",{}).get("pattern"))
if not ok:
    print(f"source_bead={v.get('source_bead')} brief_slug={v.get('brief_slug')}", file=sys.stderr); sys.exit(1)
PY

# Check 7: no model names in run_targets (F1.3 / F3.3) — every gc.run_target is a fleet address or a var
python3 - "$FORMULA_PATH" << 'PY' && check "no model names in run_targets (F1.3/F3.3)" "ok" \
  || check "run_target model-name audit" "a model name (opus/sonnet/haiku/fable) appears in a run_target"
import tomllib, sys
with open(sys.argv[1], "rb") as f:
    d = tomllib.load(f)
bad = {"opus","sonnet","haiku","fable"}
for s in d.get("steps", []):
    rt = s.get("metadata", {}).get("gc.run_target", "")
    if rt.strip().lower() in bad:
        print(f"step {s['id']} run_target={rt}", file=sys.stderr); sys.exit(1)
PY

# Check 8: never-push guard — the verbs may appear in backtick-quoted prose
# (describing what the FORMULA refuses to do, or what happens post-approval), but
# must NEVER appear as an executed shell command. An executed command starts the
# line (after optional whitespace); prose wraps the verb in `backticks` or mid-
# sentence. Fail only on a bare line-start invocation.
if grep -Eq '^[[:space:]]*(git push|gh pr create)([[:space:]]|$)' "$FORMULA_PATH"; then
  check "never EXECUTES git push / gh pr create (prose-only mentions ok)" "a bare push/PR command invocation is present"
else
  check "never EXECUTES git push / gh pr create (prose-only mentions ok)" "ok"
fi

# Check 9: gc formula show (soft — requires the pack installed to the live city)
if command -v gc >/dev/null 2>&1; then
  if gc formula show pr-pipeline-briefed >/dev/null 2>&1; then
    check "gc formula show pr-pipeline-briefed succeeds" "ok"
  else
    RESULTS+=("  SKIP: gc formula show — formula not loaded into the live city yet (expected pre-install)")
  fi
else
  RESULTS+=("  SKIP: gc formula show — gc not on PATH")
fi

# Summary
echo ""
echo "pr-pipeline-briefed smoke-test results:"
for r in "${RESULTS[@]}"; do echo "$r"; done
echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "PASS — $PASS/$((PASS+FAIL)) checks passed"
  exit 0
else
  echo "FAIL — $FAIL/$((PASS+FAIL)) checks failed"
  exit 1
fi
