#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
TEST_DIR="$ROOT/tests/lost-bead-filter"
SCRIPT="$ROOT/assets/scripts/lost-bead-filter.py"
CHECK="$ROOT/assets/scripts/checks/lost-bead-filter-check.sh"
FIXTURES="$TEST_DIR/fixtures"
INVALID_FIXTURE="$TEST_DIR/invalid/invalid-missing-fingerprint.toml"
TMPDIR="${TMPDIR:-/tmp}/lost-bead-filter-test-$$"
VALID_FIXTURES="$TMPDIR/valid-fixtures"

cleanup() {
  rm -rf "$TMPDIR"
}
trap cleanup EXIT
mkdir -p "$TMPDIR"

probe_python() {
  local candidate="$1"
  local slug
  slug="$(printf '%s' "$candidate" | tr -c 'A-Za-z0-9_' '_')"
  local status_file="$TMPDIR/python-$slug.status"

  (
    "$candidate" -c 'import sys, tomllib; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)' >/dev/null 2>&1
    printf '%s\n' "$?" >"$status_file"
  ) &
  local pid=$!
  local waited=0
  while kill -0 "$pid" 2>/dev/null; do
    sleep 1
    waited=$((waited + 1))
    if [ "$waited" -ge 5 ]; then
      kill "$pid" 2>/dev/null || true
      wait "$pid" 2>/dev/null || true
      return 1
    fi
  done
  wait "$pid" 2>/dev/null || true
  [ -f "$status_file" ] && [ "$(cat "$status_file")" = "0" ]
}

PYTHON_BIN="${PYTHON:-}"
if [ -n "$PYTHON_BIN" ]; then
  if ! probe_python "$PYTHON_BIN"; then
    echo "I'm sorry, I can't do that - PYTHON does not point to a working Python 3.11+ interpreter." >&2
    echo "Set PYTHON to a working Python 3.11+ executable and retry." >&2
    echo "(The lost-bead filter validator uses Python tomllib to parse schema fixtures.)" >&2
    exit 1
  fi
else
  while IFS= read -r candidate; do
    if probe_python "$candidate"; then
      PYTHON_BIN="$candidate"
      break
    fi
  done < <(which -a python3 2>/dev/null | awk '!seen[$0]++')
fi

if [ -z "$PYTHON_BIN" ]; then
  echo "I'm sorry, I can't do that - no working Python 3.11+ interpreter was found." >&2
  echo "Install Python 3.11 or newer, or set PYTHON to a working interpreter, then retry." >&2
  echo "(The lost-bead filter validator uses Python tomllib to parse schema fixtures.)" >&2
  exit 1
fi

pass=0
fail=0
results=()

mkdir -p "$VALID_FIXTURES"
for fixture in "$FIXTURES"/*.toml; do
  case "$(basename "$fixture")" in
    invalid-*) ;;
    *) cp "$fixture" "$VALID_FIXTURES/" ;;
  esac
done

record() {
  local desc="$1"
  local status="$2"
  local detail="${3:-}"
  if [ "$status" = "ok" ]; then
    results+=("PASS: $desc")
    pass=$((pass + 1))
  else
    results+=("FAIL: $desc - $detail")
    fail=$((fail + 1))
  fi
}

expect_ok() {
  local desc="$1"
  shift
  if "$@" >"$TMPDIR/out" 2>"$TMPDIR/err"; then
    record "$desc" ok
  else
    record "$desc" fail "$(cat "$TMPDIR/err")"
  fi
}

expect_fail() {
  local desc="$1"
  local expected="$2"
  shift 2
  if "$@" >"$TMPDIR/out" 2>"$TMPDIR/err"; then
    record "$desc" fail "command unexpectedly passed"
  elif grep -F "$expected" "$TMPDIR/err" >/dev/null 2>&1; then
    record "$desc" ok
  else
    record "$desc" fail "stderr did not contain '$expected': $(cat "$TMPDIR/err")"
  fi
}

expect_ok "Python script compiles" env PYTHONPYCACHEPREFIX="$TMPDIR/pycache" "$PYTHON_BIN" -m py_compile "$SCRIPT"
expect_ok "valid fixtures pass validator" env PYTHON="$PYTHON_BIN" "$CHECK" "$VALID_FIXTURES"
expect_fail "invalid fixture fails loudly" "missing root_cause.fingerprint" "$PYTHON_BIN" "$SCRIPT" validate "$INVALID_FIXTURE"

expect_ok "downstream rollup command succeeds" "$PYTHON_BIN" "$SCRIPT" rollup-downstream --input "$VALID_FIXTURES" --threshold 3 --output "$TMPDIR/downstream.jsonl"
if grep -F '"kind":"downstream_filter_rule"' "$TMPDIR/downstream.jsonl" >/dev/null 2>&1 \
  && grep -F '"fingerprint":"empty_assignee_after_verified_sling"' "$TMPDIR/downstream.jsonl" >/dev/null 2>&1 \
  && grep -F '"count":3' "$TMPDIR/downstream.jsonl" >/dev/null 2>&1; then
  record "downstream rollup emits threshold candidate" ok
else
  record "downstream rollup emits threshold candidate" fail "$(cat "$TMPDIR/downstream.jsonl")"
fi

expect_ok "below-threshold downstream rollup succeeds" "$PYTHON_BIN" "$SCRIPT" rollup-downstream --input "$VALID_FIXTURES" --threshold 4 --output "$TMPDIR/downstream-below.jsonl"
if grep -F '"kind":"downstream_filter_rule"' "$TMPDIR/downstream-below.jsonl" >/dev/null 2>&1; then
  record "below-threshold downstream rollup emits no candidate" fail "$(cat "$TMPDIR/downstream-below.jsonl")"
else
  record "below-threshold downstream rollup emits no candidate" ok
fi

expect_ok "upstream rollup command succeeds" "$PYTHON_BIN" "$SCRIPT" rollup-upstream --input "$VALID_FIXTURES" --threshold 3 --output "$TMPDIR/upstream.jsonl"
if grep -F '"kind":"upstream_repair_brief"' "$TMPDIR/upstream.jsonl" >/dev/null 2>&1 \
  && grep -F '"suspected_source":"mathcity.work"' "$TMPDIR/upstream.jsonl" >/dev/null 2>&1 \
  && grep -F '"repair_target":"mathcity.work verify-assignee gate"' "$TMPDIR/upstream.jsonl" >/dev/null 2>&1; then
  record "upstream rollup emits known-source repair candidate" ok
else
  record "upstream rollup emits known-source repair candidate" fail "$(cat "$TMPDIR/upstream.jsonl")"
fi

if grep -F '"failure_class":"UNKNOWN_PROVENANCE"' "$TMPDIR/upstream.jsonl" >/dev/null 2>&1 \
  && grep -F '"repair_target":"dispatch provenance recording"' "$TMPDIR/upstream.jsonl" >/dev/null 2>&1; then
  record "unknown provenance routes to provenance repair" ok
else
  record "unknown provenance routes to provenance repair" fail "$(cat "$TMPDIR/upstream.jsonl")"
fi

if grep -F '"failure_class":"UNKNOWN_PROVENANCE"' "$TMPDIR/upstream.jsonl" | grep -F 'mathcity.work verify-assignee gate' >/dev/null 2>&1; then
  record "unknown provenance does not blame mathcity.work" fail "$(grep -F '"failure_class":"UNKNOWN_PROVENANCE"' "$TMPDIR/upstream.jsonl")"
else
  record "unknown provenance does not blame mathcity.work" ok
fi

expect_ok "downstream formula parses" "$PYTHON_BIN" -c "import tomllib; tomllib.load(open('$ROOT/formulas/lost-bead-classification-rollup.toml','rb'))"
expect_ok "upstream formula parses" "$PYTHON_BIN" -c "import tomllib; tomllib.load(open('$ROOT/formulas/lost-bead-upstream-repair-rollup.toml','rb'))"

if grep -F 'This step must not run `bd close`' "$ROOT/formulas/lost-bead-classification-rollup.toml" >/dev/null 2>&1; then
  record "downstream file-brief has evidence-first self-close contract" fail "file-brief still forbids closing its own step"
elif grep -F "close this step" "$ROOT/formulas/lost-bead-classification-rollup.toml" >/dev/null 2>&1 \
  && grep -F "bd dep list" "$ROOT/formulas/lost-bead-classification-rollup.toml" >/dev/null 2>&1 \
  && grep -F "manifest cache row" "$ROOT/formulas/lost-bead-classification-rollup.toml" >/dev/null 2>&1; then
  record "downstream file-brief has evidence-first self-close contract" ok
else
  record "downstream file-brief has evidence-first self-close contract" fail "missing close instruction, dependency verification, or manifest verification"
fi

for path in \
  "$ROOT/skills/bead-check/SKILL.md" \
  "$ROOT/subdomains/dev/skills/strand-sweep/SKILL.md" \
  "$ROOT/skills/create-bead-manifest/SKILL.md" \
  "$ROOT/skills/refine-bead-manifest/SKILL.md"; do
  if grep -F "lost-bead-classification.v1" "$path" >/dev/null 2>&1 \
    && grep -F "fingerprint" "$path" >/dev/null 2>&1; then
    record "classification contract present in ${path#$ROOT/}" ok
  else
    record "classification contract present in ${path#$ROOT/}" fail "missing schema or fingerprint"
  fi
done

# The path-B provenance event moved from a bare `bd create --type event` in
# the skill to `mctl work dispatch-event`, so the fingerprints this filter
# matches on are no longer typed into the markdown -- they are derived in
# mctl_core/work.py. Checking the old spelling would now pin the very
# bare-command shape the skill-hygiene policy removed, so the contract is
# checked at BOTH ends instead: the skill must still name the schema and the
# command that writes it, and the producer must still emit both fingerprints.
work_core="$ROOT/assets/scripts/mctl_core/work.py"
if grep -F "dispatch-provenance.v1" "$ROOT/skills/work/SKILL.md" >/dev/null 2>&1 \
  && grep -F "work dispatch-event" "$ROOT/skills/work/SKILL.md" >/dev/null 2>&1 \
  && grep -F "dispatch-provenance.v1" "$work_core" >/dev/null 2>&1 \
  && grep -F "empty_assignee_after_verified_sling" "$work_core" >/dev/null 2>&1 \
  && grep -F "verified_sling_claimed" "$work_core" >/dev/null 2>&1; then
  record "mathcity.work provenance and strand hooks documented" ok
else
  record "mathcity.work provenance and strand hooks documented" fail "missing provenance hook"
fi

if grep -F "bd create --type decision" "$ROOT/formulas/lost-bead-classification-rollup.toml" >/dev/null 2>&1 \
  && grep -F "bd dep add" "$ROOT/formulas/lost-bead-classification-rollup.toml" >/dev/null 2>&1 \
  && grep -F "bd create --type decision" "$ROOT/formulas/lost-bead-upstream-repair-rollup.toml" >/dev/null 2>&1 \
  && grep -F "bd dep add" "$ROOT/formulas/lost-bead-upstream-repair-rollup.toml" >/dev/null 2>&1; then
  record "rollup formulas create linked decision brief beads" ok
else
  record "rollup formulas create linked decision brief beads" fail "missing bd decision/link contract"
fi

echo "lost-bead-filter smoke test results:"
for item in "${results[@]}"; do
  echo "  $item"
done

if [ "$fail" -eq 0 ]; then
  echo "PASS - $pass checks passed"
  exit 0
fi

echo "FAIL - $fail checks failed"
exit 1
