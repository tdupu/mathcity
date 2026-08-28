#!/usr/bin/env bash
# Smoke test for report-fix-briefed.formula.toml (F6.1 gate) — the dashboard
# "Report" box formula (decision mc-3q4v). Adapter over brief-briefed-base.
# Run from rig root: bash mathcity/tests/report-fix-briefed/smoke_test.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FORMULA_PATH="$PACK_ROOT/formulas/report-fix-briefed.formula.toml"
BASE_PATH="$PACK_ROOT/formulas/brief-briefed-base.formula.toml"
GATE_PATH="$PACK_ROOT/assets/scripts/report_fix_evidence_gate.py"
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

# Check 1: formula + base + gate all exist
missing=""
for f in "$FORMULA_PATH" "$BASE_PATH" "$GATE_PATH"; do
  [ -f "$f" ] || missing="$missing ${f#$PACK_ROOT/}"
done
[ -z "$missing" ] && check "formula + base + evidence-gate all exist" "ok" \
  || check "formula + base + evidence-gate all exist" "missing:$missing"

# Check 2: TOML parses
if python3 -c "import tomllib; tomllib.load(open('$FORMULA_PATH','rb'))" 2>/dev/null; then
  check "TOML parses without error" "ok"
else
  check "TOML parses without error" "tomllib parse failed"
fi

# Check 3: catalog fields present
python3 - "$FORMULA_PATH" << 'PY' && check "catalog fields present" "ok" \
  || check "catalog fields present" "missing fields"
import tomllib, sys
d = tomllib.load(open(sys.argv[1], "rb"))
cat = d.get("catalog", {})
missing = [k for k in ["name","description"] if not cat.get(k)]
missing += [k for k in ["formula","version"] if not d.get(k)]
if missing:
    print("MISSING: " + ", ".join(missing), file=sys.stderr); sys.exit(1)
PY

# Check 4: adapter-over-base — extends brief-briefed-base, which must exist
python3 - "$FORMULA_PATH" "$BASE_PATH" << 'PY' && check "adapter extends brief-briefed-base (base present)" "ok" \
  || check "adapter-over-base shape" "extends missing/wrong, or base absent"
import tomllib, sys, os
d = tomllib.load(open(sys.argv[1], "rb"))
if d.get("extends") != ["brief-briefed-base"]:
    print(f"extends={d.get('extends')!r}", file=sys.stderr); sys.exit(1)
b = tomllib.load(open(sys.argv[2], "rb"))
if b.get("formula") != "brief-briefed-base":
    print(f"base formula name={b.get('formula')!r}", file=sys.stderr); sys.exit(1)
PY

# Check 5: F8.1 — resolved terminal is file-brief with NO appended step past the
# brief gate. Simulated exactly as gascity does it (parser.go mergeSteps): child
# steps override by id in position; any non-override child step appends after the
# parent's steps, which for this formula would land after file-brief. Assert none.
python3 - "$FORMULA_PATH" "$BASE_PATH" << 'PY' && check "F8.1: resolved terminal is file-brief (no appended step past the brief gate)" "ok" \
  || check "F8.1 terminal step" "resolved order/terminal not as expected"
import tomllib, sys
ALLOWED = {"file-brief","brief-finalize","workflow-finalize","publish","route"}
child = tomllib.load(open(sys.argv[1], "rb"))
base  = tomllib.load(open(sys.argv[2], "rb"))
base_ids  = [s["id"] for s in base.get("steps", [])]
child_ids = [s["id"] for s in child.get("steps", [])]
appended = [i for i in child_ids if i not in base_ids]
if appended:
    print(f"child appends non-override steps {appended} after terminal {base_ids[-1]!r}", file=sys.stderr); sys.exit(1)
resolved = base_ids
if resolved != ["intake","compose-body","file-brief"]:
    print(f"resolved step ids: {resolved}", file=sys.stderr); sys.exit(1)
if resolved[-1] not in ALLOWED:
    print(f"terminal {resolved[-1]!r} not in F8.1 allowed set", file=sys.stderr); sys.exit(1)
PY

# Check 6: the INHERITED terminal carries brief-producer.v1 metadata (owned by the
# base) — the leaf must not re-declare file-brief (that would re-spell the schema).
python3 - "$FORMULA_PATH" "$BASE_PATH" << 'PY' && check "file-brief inherited from base (schema not re-spelled in the leaf)" "ok" \
  || check "inherited terminal" "leaf re-declares file-brief, or base terminal lacks the contract"
import tomllib, sys
child = tomllib.load(open(sys.argv[1], "rb"))
base  = tomllib.load(open(sys.argv[2], "rb"))
child_ids = [s["id"] for s in child.get("steps", [])]
if "file-brief" in child_ids:
    print("leaf re-declares file-brief — must inherit it from the base", file=sys.stderr); sys.exit(1)
md = base["steps"][-1].get("metadata", {})
if md.get("gc.brief.producer_contract") != "brief-producer.v1" or not md.get("gc.brief.path"):
    print("base terminal missing brief-producer.v1 contract", file=sys.stderr); sys.exit(1)
PY

# Check 7: PROVENANCE — the leaf overrides source_formula to its own name, and sets
# terminal_action = dispatch-fix (this box commissions a fix, not an issue/PR).
python3 - "$FORMULA_PATH" << 'PY' && check "leaf stamps provenance (source_formula=report-fix-briefed) + terminal_action=dispatch-fix" "ok" \
  || check "provenance/action override" "source_formula or terminal_action default wrong"
import tomllib, sys
d = tomllib.load(open(sys.argv[1], "rb"))
v = d.get("vars", {})
if v.get("source_formula", {}).get("default") != "report-fix-briefed":
    print(f"source_formula default={v.get('source_formula')}", file=sys.stderr); sys.exit(1)
ta = v.get("terminal_action", {})
if ta.get("default") != "dispatch-fix" or ta.get("enum") != ["dispatch-fix"]:
    print(f"terminal_action={ta}", file=sys.stderr); sys.exit(1)
PY

# Check 8: SCOPE — target_repo is a CLOSED enum of the owned repo only (an upstream
# fix must be refused at intake, never silently dispatched against unowned code).
python3 - "$FORMULA_PATH" << 'PY' && check "scope: target_repo enum closed to tdupu/mathcity (owned-only)" "ok" \
  || check "scope enum" "target_repo enum missing or not owned-only"
import tomllib, sys
d = tomllib.load(open(sys.argv[1], "rb"))
tr = d.get("vars", {}).get("target_repo", {})
if tr.get("default") != "tdupu/mathcity":
    print(f"default={tr.get('default')!r}", file=sys.stderr); sys.exit(1)
if tr.get("enum") != ["tdupu/mathcity"]:
    print(f"enum={tr.get('enum')!r} (must be owned-only)", file=sys.stderr); sys.exit(1)
PY

# Check 9: the evidence gate is delegated to the single code-owner, not re-rolled.
# The overridden intake must SHELL OUT to report_fix_evidence_gate.py.
if grep -q 'report_fix_evidence_gate.py' "$FORMULA_PATH"; then
  check "intake delegates the evidence gate to report_fix_evidence_gate.py (one owner, tested)" "ok"
else
  check "evidence-gate delegation" "intake does not reference report_fix_evidence_gate.py"
fi

# Check 10: NEVER-DISPATCH — the formula drafts and files a brief; it must NEVER
# EXECUTE the fix dispatch. `build-basic-briefed` / `gc sling` may appear in prose
# (post-approval narration) but not as a bare executed command.
if grep -Eq '^[[:space:]]*(gc sling|gh pr create)([[:space:]]|$)' "$FORMULA_PATH"; then
  check "never EXECUTES the fix dispatch (prose-only mentions ok)" "a bare dispatch command invocation is present"
else
  check "never EXECUTES the fix dispatch (prose-only mentions ok)" "ok"
fi

# Check 11: no model names in run_targets (F1.3 / F3.3)
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

# Check 12: COMPATIBILITY CONTRACT — the overridden intake writes the note marker
# the overridden compose-body greps for, with `sources:` inside the read window.
python3 - "$FORMULA_PATH" << 'PY' && check "intake/compose-body note contract (marker + sources within grep -A6)" "ok" \
  || check "intake/compose-body note contract" "marker missing or sources outside the read window"
import tomllib, sys
d = tomllib.load(open(sys.argv[1], "rb"))
by_id = {s["id"]: s for s in d["steps"]}
marker = "report-fix-briefed intake:"
compose = by_id["compose-body"]["description"]
if marker not in compose:
    print("compose-body does not grep the expected marker", file=sys.stderr); sys.exit(1)
intake = by_id["intake"]["description"]
lines = intake.splitlines()
idx = [i for i, l in enumerate(lines) if marker in l]
if not idx:
    print("overridden intake never writes the marker", file=sys.stderr); sys.exit(1)
# The marker appears in the `bd update` note (with the fields) AND in the prose
# describing the contract. At least one occurrence must carry `sources:` within
# its 6-line read window — that is the note block compose-body actually greps.
if not any(any("sources:" in l for l in lines[i+1:i+7]) for i in idx):
    print(f"no marker occurrence has sources: within 6 lines", file=sys.stderr); sys.exit(1)
PY

# Check 13: gc formula show (soft — requires the pack installed to the live city)
if command -v gc >/dev/null 2>&1; then
  if gc formula show report-fix-briefed >/dev/null 2>&1; then
    check "gc formula show report-fix-briefed succeeds" "ok"
  else
    RESULTS+=("  SKIP: gc formula show — formula not loaded into the live city yet (expected pre-install / city down)")
  fi
else
  RESULTS+=("  SKIP: gc formula show — gc not on PATH")
fi

# Summary
echo ""
echo "report-fix-briefed smoke-test results:"
for r in "${RESULTS[@]}"; do echo "$r"; done
echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "PASS — $PASS/$((PASS+FAIL)) checks passed"; exit 0
else
  echo "FAIL — $FAIL/$((PASS+FAIL)) checks failed"; exit 1
fi
