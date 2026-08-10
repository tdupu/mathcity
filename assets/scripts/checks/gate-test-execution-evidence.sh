#!/bin/sh
# gate-test-execution-evidence.sh
#
# Gate G-test-execution, step 2: when brief claims PASSED, verify that §5
# (Test evidence) contains the exact command, exit code, and wall time.
#
# Exit 0 = PASS
# Exit 1 = FAIL
# Exit 2 = SKIP (brief does not claim PASSED; this step is not applicable)
#
# Source spec: he-8akk (G-test-execution gate)
#
set -eu

# Rig-relative default per assets/brief-pipeline/paths.toml (gsp-3al3).
ROOT="${BRIEF_ROOT:-.beads/briefs}"

fail() {
  echo "gate-test-execution-evidence: $*" >&2
  exit 1
}

skip() {
  echo "gate-test-execution-evidence: SKIP — $*"
  exit 0
}

metadata_value() {
  key="$1"
  if [ -z "${GC_BEAD_ID:-}" ] || ! command -v gc >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
    return 0
  fi
  gc bd show "$GC_BEAD_ID" --json 2>/dev/null |
    jq -r --arg key "$key" '.[0].metadata[$key] // empty' 2>/dev/null || true
}

brief_path() {
  if [ -n "${GC_BRIEF_PATH:-}" ]; then
    printf '%s\n' "$GC_BRIEF_PATH"
    return 0
  fi
  value="$(metadata_value "gc.brief.path")"
  if [ -n "$value" ]; then
    printf '%s\n' "$value"
    return 0
  fi
  find . -path "./$ROOT/.staging/*/brief.md" -type f 2>/dev/null | sort | head -n 1
}

BRIEF="$(brief_path)"
[ -n "$BRIEF" ] || fail "gate_blocked_reason: test-execution-evidence-incomplete — could not resolve brief path"
[ -f "$BRIEF" ] || fail "gate_blocked_reason: test-execution-evidence-incomplete — brief not found: $BRIEF"

# Only run when the declaration says PASSED.
if ! grep -Eq '^test-execution:[[:space:]]*PASSED' "$BRIEF"; then
  skip "declaration is not PASSED; evidence check does not apply"
fi

# Determine evidence scope: brief itself, or a cited log artifact.
# When the brief says "PASSED — log at <path>", try to read that file too.
LOG_PATH=""
DECL="$(grep -E '^test-execution:[[:space:]]*PASSED' "$BRIEF" | head -n 1)"
# Extract "log at <path>" reference if present.
if printf '%s\n' "$DECL" | grep -Eq 'log at '; then
  LOG_PATH="$(printf '%s\n' "$DECL" | sed 's/.*log at //' | tr -d '[:space:]')"
fi

# Collect evidence text (brief §5 plus optional log file).
EVIDENCE_TMPFILE="$(mktemp /tmp/gate-te-ev-XXXXXX)"
trap 'rm -f "$EVIDENCE_TMPFILE"' EXIT

# Extract §5 block from brief (from "## 5" or "## Test evidence" to next "## ").
awk '
  /^#{1,3}[[:space:]]*(5[[:space:]]|[Tt]est[[:space:]][Ee]vidence)/ { in_section=1; next }
  in_section && /^#{1,3}[[:space:]]/ { in_section=0 }
  in_section { print }
' "$BRIEF" >> "$EVIDENCE_TMPFILE"

# Also append the whole brief (some evidence may be inline rather than §5).
cat "$BRIEF" >> "$EVIDENCE_TMPFILE"

# Append log file if it resolves.
if [ -n "$LOG_PATH" ] && [ -f "$LOG_PATH" ]; then
  cat "$LOG_PATH" >> "$EVIDENCE_TMPFILE"
fi

MISSING=""

# -----------------------------------------------------------------------
# Check 1: exact command
# Patterns: "Command:", "Cmd:", a fenced shell block, or "magma -b"/"time magma".
# -----------------------------------------------------------------------
if ! grep -Eiq \
  '(^Command:|^Cmd:|^```[[:space:]]*(sh|bash|magma|zsh)?|magma[[:space:]]+-[a-z]|Attach\(|LoadPackage\()' \
  "$EVIDENCE_TMPFILE"; then
  MISSING="${MISSING}command "
fi

# -----------------------------------------------------------------------
# Check 2: exit code
# Patterns: "exit 0", "exit: 0", "Exit code: 0", "returned 0", "status: 0",
# "exit status 0", or non-zero variants (any digit).
# -----------------------------------------------------------------------
if ! grep -Eiq \
  '(exit[[:space:]:]+[0-9]|[Ee]xit[[:space:]]+code[[:space:]]*:[[:space:]]*[0-9]|returned[[:space:]]+[0-9]|status[[:space:]]*:[[:space:]]*[0-9])' \
  "$EVIDENCE_TMPFILE"; then
  MISSING="${MISSING}exit-code "
fi

# -----------------------------------------------------------------------
# Check 3: wall time
# Patterns: "real <N>", "Elapsed:", "wall time:", "Wall:", ISO-8601 PT<N>S,
# "Ns" as standalone, or "time: <N>".
# -----------------------------------------------------------------------
if ! grep -Eiq \
  '(^real[[:space:]]+[0-9]|[Ee]lapsed[[:space:]]*:[[:space:]]*[0-9]|[Ww]all[[:space:]]+(time[[:space:]]*:)?[[:space:]]*[0-9]|PT[0-9]+(\.[0-9]+)?S|[Tt]ime[[:space:]]*:[[:space:]]*[0-9]+(\.[0-9]+)?s)' \
  "$EVIDENCE_TMPFILE"; then
  MISSING="${MISSING}wall-time "
fi

# -----------------------------------------------------------------------
# Guard: "test file exists" language without execution evidence triggers FAIL.
# (Spec: "the test file exists at <path>" is NOT execution evidence.)
# If the only test-related content mentions file existence, FAIL.
# -----------------------------------------------------------------------
if [ -n "$MISSING" ]; then
  fail "gate_blocked_reason: test-execution-evidence-incomplete — missing fields: ${MISSING}— citing a test file path is not execution evidence; re-run tests and attach command + exit-code + wall-time"
fi

# -----------------------------------------------------------------------
# If "PASSED — see <bead/commit>", do best-effort resolution check.
# -----------------------------------------------------------------------
if printf '%s\n' "$DECL" | grep -Eq 'see [a-z]{2}-[a-z0-9]+|see [0-9a-f]{7,40}'; then
  REF="$(printf '%s\n' "$DECL" | grep -Eo '(see [a-z]{2}-[a-z0-9]+|see [0-9a-f]{7,40})' | head -n 1 | sed 's/see //')"
  # Try bead resolution
  if printf '%s\n' "$REF" | grep -Eq '^[a-z]{2}-[a-z0-9]+$'; then
    if command -v bd >/dev/null 2>&1; then
      bd show "$REF" >/dev/null 2>&1 || fail "gate_blocked_reason: test-execution-evidence-incomplete — cited bead $REF could not be resolved"
    fi
  fi
  # Try git commit resolution
  if printf '%s\n' "$REF" | grep -Eq '^[0-9a-f]{7,40}$'; then
    if command -v git >/dev/null 2>&1; then
      git log -1 "$REF" >/dev/null 2>&1 || fail "gate_blocked_reason: test-execution-evidence-incomplete — cited commit $REF could not be resolved"
    fi
  fi
fi

echo "gate-test-execution-evidence: PASS — command, exit-code, and wall-time all present"
exit 0
