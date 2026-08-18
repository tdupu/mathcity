#!/usr/bin/env bash
# Smoke test for the MathCity issue workflow (issue #12): the
# mathcity-issue-briefed adapter formula, the create-issue skill, and the
# shared investigation standard they both read. F6.1 gate.
# Run from rig root: bash mathcity/tests/mathcity-issue-briefed/smoke_test.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FORMULA_PATH="$PACK_ROOT/formulas/mathcity-issue-briefed.formula.toml"
BASE_PATH="$PACK_ROOT/formulas/create-issue-briefed.formula.toml"
SKILL_PATH="$PACK_ROOT/skills/create-issue/SKILL.md"
STANDARD_PATH="$PACK_ROOT/template-fragments/issue-investigation-standard.md"
DEFAULT_TARGET="tdupu/mathcity"
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

# Check 1: all three artifacts exist
missing=""
for f in "$FORMULA_PATH" "$SKILL_PATH" "$STANDARD_PATH"; do
  [ -f "$f" ] || missing="$missing ${f#$PACK_ROOT/}"
done
[ -z "$missing" ] && check "formula + skill + shared standard all exist" "ok" \
  || check "formula + skill + shared standard all exist" "missing:$missing"

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

# Check 4: adapter-over-base — extends create-issue-briefed, which must exist
python3 - "$FORMULA_PATH" "$BASE_PATH" << 'PY' && check "adapter extends create-issue-briefed (base present)" "ok" \
  || check "adapter-over-base shape" "extends missing/wrong, or base formula absent"
import tomllib, sys, os
with open(sys.argv[1], "rb") as f:
    d = tomllib.load(f)
if d.get("extends") != ["create-issue-briefed"]:
    print(f"extends={d.get('extends')!r}", file=sys.stderr); sys.exit(1)
if not os.path.isfile(sys.argv[2]):
    print("base formula file not found", file=sys.stderr); sys.exit(1)
with open(sys.argv[2], "rb") as f:
    b = tomllib.load(f)
if b.get("formula") != "create-issue-briefed":
    print(f"base formula name={b.get('formula')!r}", file=sys.stderr); sys.exit(1)
PY

# Check 5: F8.1 — the RESOLVED terminal step is a brief step.
# Resolution is simulated exactly as gascity does it (internal/formula/parser.go,
# mergeSteps): child steps override parent steps by id preserving position, and
# any non-override child step APPENDS after the parent's steps — which for this
# formula would land after `file-brief` and break F8.1. Assert no such append.
python3 - "$FORMULA_PATH" "$BASE_PATH" << 'PY' && check "F8.1: resolved terminal step is file-brief (no appended step past the brief gate)" "ok" \
  || check "F8.1 terminal step" "resolved step order/terminal not as expected"
import tomllib, sys
ALLOWED = {"file-brief","brief-finalize","workflow-finalize","publish","route"}
def load(p):
    with open(p,"rb") as f: return tomllib.load(f)
child, base = load(sys.argv[1]), load(sys.argv[2])
base_ids  = [s["id"] for s in base.get("steps", [])]
child_ids = [s["id"] for s in child.get("steps", [])]
appended = [i for i in child_ids if i not in base_ids]
if appended:
    print(f"child appends non-override steps {appended} after terminal {base_ids[-1]!r}", file=sys.stderr); sys.exit(1)
resolved = base_ids  # every child step is an in-position override
if resolved != ["intake","compose-body","file-brief"]:
    print(f"resolved step ids: {resolved}", file=sys.stderr); sys.exit(1)
if resolved[-1] not in ALLOWED:
    print(f"terminal {resolved[-1]!r} not in F8.1 allowed set", file=sys.stderr); sys.exit(1)
PY

# Check 6: the inherited terminal keeps the brief-producer.v1 contract metadata
python3 - "$BASE_PATH" << 'PY' && check "inherited file-brief carries brief-producer.v1 metadata" "ok" \
  || check "inherited terminal metadata" "producer_contract/path missing on the inherited terminal step"
import tomllib, sys
with open(sys.argv[1], "rb") as f:
    d = tomllib.load(f)
md = d["steps"][-1].get("metadata", {})
if md.get("gc.brief.producer_contract") != "brief-producer.v1":
    print(f"producer_contract={md.get('gc.brief.producer_contract')!r}", file=sys.stderr); sys.exit(1)
if not md.get("gc.brief.path"):
    print("gc.brief.path missing", file=sys.stderr); sys.exit(1)
PY

# Check 7: TARGETING — the default target resolves to tdupu/mathcity.
# This is the core defect issue #12 exists to fix: upstream write-issue hardcodes
# gastownhall/gascity, and the base formula's default was "" (guess from checkout).
python3 - "$FORMULA_PATH" "$DEFAULT_TARGET" << 'PY' && check "default target_repo resolves to tdupu/mathcity" "ok" \
  || check "default targeting" "target_repo default is not tdupu/mathcity"
import tomllib, sys
with open(sys.argv[1], "rb") as f:
    d = tomllib.load(f)
tr = d.get("vars", {}).get("target_repo", {})
if tr.get("default") != sys.argv[2]:
    print(f"default={tr.get('default')!r} expected {sys.argv[2]!r}", file=sys.stderr); sys.exit(1)
if tr.get("required"):
    print("target_repo is required with no default — the default must resolve", file=sys.stderr); sys.exit(1)
PY

# Check 8: TARGETING — the declared alternatives are accepted, and only declared
# targets are accepted (an unrecognized target must not silently file elsewhere).
python3 - "$FORMULA_PATH" << 'PY' && check "alternate targets accepted (gascity-packs, gascity) and enum is closed" "ok" \
  || check "alternate targeting" "recognized alternatives missing from the target_repo enum"
import tomllib, re, sys
with open(sys.argv[1], "rb") as f:
    d = tomllib.load(f)
tr = d.get("vars", {}).get("target_repo", {})
enum = tr.get("enum") or []
if not enum:
    print("target_repo has no enum — targeting is not a closed declared set", file=sys.stderr); sys.exit(1)
for required in ("tdupu/mathcity", "tdupu/gascity-packs", "gastownhall/gascity"):
    if required not in enum:
        print(f"{required!r} missing from enum {enum}", file=sys.stderr); sys.exit(1)
if tr.get("default") not in enum:
    print(f"default {tr.get('default')!r} not in its own enum", file=sys.stderr); sys.exit(1)
for e in enum:
    if not re.fullmatch(r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+", e):
        print(f"enum entry {e!r} is not owner/name", file=sys.stderr); sys.exit(1)
PY

# Check 9: NEVER-FILE GATE — the verb may appear in backtick-quoted prose
# (describing what happens post-approval), but must NEVER be an executed shell
# command in the formula. An executed command starts the line after optional
# whitespace. Same convention as tests/create-issue-briefed/smoke_test.sh check 8.
if grep -Eq '^[[:space:]]*gh issue create([[:space:]]|$)' "$FORMULA_PATH"; then
  check "formula never EXECUTES gh issue create (prose-only mentions ok)" "a bare issue-create command invocation is present"
else
  check "formula never EXECUTES gh issue create (prose-only mentions ok)" "ok"
fi

# Check 10: NEVER-FILE-BEFORE-APPROVAL — in the two prose surfaces the verb IS
# executed eventually, so position is what matters: every executed invocation must
# come after the approval-gate heading.
gate_ok=""
for f in "$SKILL_PATH" "$STANDARD_PATH"; do
  [ -f "$f" ] || { gate_ok="${f##*/}: file missing"; break; }
  gate_line=$(grep -niE '^#+ .*approval gate' "$f" | head -1 | cut -d: -f1 || true)
  if [ -z "$gate_line" ]; then
    gate_ok="${f##*/}: no approval-gate heading found"; break
  fi
  first_file=$(grep -nE '^[[:space:]]*gh issue create([[:space:]]|$)' "$f" | head -1 | cut -d: -f1 || true)
  if [ -n "$first_file" ] && [ "$first_file" -lt "$gate_line" ]; then
    gate_ok="${f##*/}: gh issue create at line $first_file precedes the approval gate at line $gate_line"; break
  fi
done
[ -z "$gate_ok" ] && check "skill + standard file only AFTER the approval gate" "ok" \
  || check "approve-before-file gate" "$gate_ok"

# Check 11: no model names in run_targets (F1.3 / F3.3)
python3 - "$FORMULA_PATH" << 'PY' && check "no model names in run_targets (F1.3/F3.3)" "ok" \
  || check "run_target model-name audit" "a model name (opus/sonnet/haiku/fable) appears in a run_target or a run_target-bound var"
import tomllib, sys
with open(sys.argv[1], "rb") as f:
    d = tomllib.load(f)
bad = {"opus","sonnet","haiku","fable"}
for s in d.get("steps", []):
    rt = s.get("metadata", {}).get("gc.run_target", "")
    if rt.strip().lower() in bad:
        print(f"step {s['id']} run_target={rt}", file=sys.stderr); sys.exit(1)
for name, v in (d.get("vars") or {}).items():
    if "target" not in name:
        continue
    vals = [v.get("default")] + list(v.get("enum") or [])
    for val in vals:
        if isinstance(val, str) and val.strip().lower() in bad:
            print(f"var {name} has model name {val!r}", file=sys.stderr); sys.exit(1)
PY

# Check 12: COMPATIBILITY CONTRACT — the overridden intake must still write the
# note marker the INHERITED compose-body greps for, with template_path inside the
# 5-line window `grep -A5` gives it. Breaking this silently composes the body
# against no template at all.
python3 - "$FORMULA_PATH" "$BASE_PATH" << 'PY' && check "overridden intake preserves the compose-body note contract (marker + template_path within grep -A5)" "ok" \
  || check "intake/compose-body note contract" "marker missing, or template_path outside the 5-line window"
import tomllib, sys
def load(p):
    with open(p,"rb") as f: return tomllib.load(f)
child, base = load(sys.argv[1]), load(sys.argv[2])
compose = [s for s in base["steps"] if s["id"] == "compose-body"][0]
marker = "create-issue-briefed intake:"
if marker not in compose["description"]:
    print("base compose-body no longer greps the expected marker", file=sys.stderr); sys.exit(1)
intake = [s for s in child.get("steps", []) if s["id"] == "intake"]
if not intake:
    print("child does not override intake", file=sys.stderr); sys.exit(1)
lines = intake[0]["description"].splitlines()
idx = [i for i, l in enumerate(lines) if marker in l]
if not idx:
    print(f"overridden intake never writes the {marker!r} marker", file=sys.stderr); sys.exit(1)
i = idx[0]
window = lines[i+1:i+6]
if not any("template_path:" in l for l in window):
    print(f"template_path not within 5 lines of the marker; window={window}", file=sys.stderr); sys.exit(1)
PY

# Check 13: ONE shared standard — both surfaces reference the same fragment path,
# and neither carries its own copy of the discipline.
ref_err=""
for f in "$SKILL_PATH" "$FORMULA_PATH"; do
  grep -q "template-fragments/issue-investigation-standard.md" "$f" \
    || ref_err="$ref_err ${f##*/}"
done
[ -z "$ref_err" ] && check "skill + formula both reference the one shared standard" "ok" \
  || check "shared standard referenced" "no reference in:$ref_err"

# Check 14: the standard is target-parameterized, not hardcoded to one upstream.
# The core defect: upstream write-issue names gastownhall/gascity as THE target.
# Mentioning it as one row of the routing table is correct; using it in the
# command examples is the bug.
if grep -qE '(--repo|repos/)[[:space:]]*"?\$TARGET_REPO"?' "$STANDARD_PATH" \
   && grep -q "$DEFAULT_TARGET" "$STANDARD_PATH"; then
  if grep -nE '^[[:space:]]*(gh (issue|pr) list|gh issue create|gh pr list)' "$STANDARD_PATH" | grep -q 'gastownhall/gascity'; then
    check "standard parameterizes the target (no hardcoded repo in commands)" "a gh command in the standard hardcodes gastownhall/gascity"
  else
    check "standard parameterizes the target (no hardcoded repo in commands)" "ok"
  fi
else
  check "standard parameterizes the target (no hardcoded repo in commands)" "standard does not use \$TARGET_REPO in gh commands, or never names the default target"
fi

# Check 15: skill frontmatter declares the expected name
if [ -f "$SKILL_PATH" ] && head -5 "$SKILL_PATH" | grep -q '^name: create-issue$'; then
  check "skill frontmatter declares name: create-issue" "ok"
else
  check "skill frontmatter" "name: create-issue missing from frontmatter"
fi

# Check 16: gc formula show (soft — requires the pack installed to the live city)
if command -v gc >/dev/null 2>&1; then
  if gc formula show mathcity-issue-briefed >/dev/null 2>&1; then
    check "gc formula show mathcity-issue-briefed succeeds" "ok"
  else
    RESULTS+=("  SKIP: gc formula show — formula not loaded into the live city yet (expected pre-install)")
  fi
else
  RESULTS+=("  SKIP: gc formula show — gc not on PATH")
fi

# Summary
echo ""
echo "mathcity-issue-briefed smoke-test results:"
for r in "${RESULTS[@]}"; do echo "$r"; done
echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "PASS — $PASS/$((PASS+FAIL)) checks passed"
  exit 0
else
  echo "FAIL — $FAIL/$((PASS+FAIL)) checks failed"
  exit 1
fi
