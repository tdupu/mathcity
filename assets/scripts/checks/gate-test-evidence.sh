#!/bin/sh
# gate-test-evidence.sh
#
# Gate: test-evidence
# Briefs and merge candidates MUST carry per-test evidence or an explicit
# unrunnable declaration before they enter the brief stack.
#
# For each test cited in §6 / "Gate Evidence / G1 Test-evidence" that is
# recorded as PASS, the brief must include ALL five structured fields:
#   - a file path  (e.g. "magma/test/test-264.mag", "tests/foo.py")
#   - an exact command  (e.g. "magma -b magma/test/test-264.mag")
#   - an exit code  (e.g. "exit code 0", "exit: 0")
#   - a pass/fail outcome  (PASS or FAILED / FAIL)
#   - a wall time  (e.g. "3.2s", "wall time: 12s", "45m")
#
# If G1 Test-evidence is N/A, the brief must include an explicit
# unrunnable reason (a non-empty line following the N/A declaration).
#
# This gate is purely mechanical: it reads the brief file and exits 0
# (gate passes) or 1 (gate fails) with a reason on stderr.  No judgment
# is applied; anything requiring judgment routes to a human/Mayor gate.
#
# Inputs (in priority order):
#   GC_BRIEF_PATH    -- absolute path to the brief markdown file
#   gc.brief.path    -- metadata key (read via gc bd show if GC_BEAD_ID set)
#   fallback         -- first <BRIEF_ROOT>/.staging/*/brief.md found
#                       (default .beads/briefs, rig-relative per paths.toml)
#
# Exit 0  -- gate passes
# Exit 1  -- gate FAILS (details on stderr)

set -eu

SCRIPT_DIR="$(dirname "$0")"

# ---------------------------------------------------------------------------
# Brief path resolution (reuse brief-check.sh helpers by sourcing its logic
# indirectly -- we duplicate the minimal path-resolution logic here so this
# script remains self-contained and callable standalone).
# ---------------------------------------------------------------------------

# Rig-relative default per assets/brief-pipeline/paths.toml (gsp-3al3).
ROOT="${BRIEF_ROOT:-.beads/briefs}"

fail() {
  echo "GATE-REJECT: test-evidence -- $*" >&2
  exit 1
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
  value="$(metadata_value "brief.path")"
  if [ -n "$value" ]; then
    printf '%s\n' "$value"
    return 0
  fi
  # Fallback: first staging brief found
  find . -path "./$ROOT/.staging/*/brief.md" -type f 2>/dev/null | sort | head -n 1
}

# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------

path="$(brief_path)"
[ -n "$path" ] || fail "cannot determine brief path (set GC_BRIEF_PATH or GC_BEAD_ID)"
[ -f "$path" ] || fail "brief file not found: $path"

# 1. Gate Evidence section must exist
grep -Eq '^##*[[:space:]]+Gate Evidence\b|^Gate Evidence\b' "$path" ||
  fail "missing 'Gate Evidence' section in $path"

# 2. G1 Test-evidence must be declared (not absent/silent)
grep -Eq '^G1 Test-evidence:[[:space:]]' "$path" ||
  fail "G1 Test-evidence is not declared in $path (silent = gate blocked)"

# 3. G1 Test-evidence must not be FAIL or BLOCKED
if grep -Eq '^G1 Test-evidence:[[:space:]]*(FAIL|BLOCKED)\b' "$path"; then
  fail "G1 Test-evidence is FAIL or BLOCKED in $path"
fi

# 4a. If PASS: the evidence block must contain all five required fields.
#    We look for each field pattern anywhere in the G1 evidence block
#    (between "G1 Test-evidence: PASS" and the next "G[0-9]" gate line
#    or end-of-file).  The patterns are intentionally broad to match
#    natural prose ("exit code 0", "exit: 0", "3.2s", "wall time: 12s").

if grep -Eq '^G1 Test-evidence:[[:space:]]*PASS\b' "$path"; then

  # Extract the G1 block: from the G1 PASS line to the next Gx gate line
  # or to EOF. Use awk for portability (no GNU-only options).
  g1_block="$(awk '
    /^G1 Test-evidence:[[:space:]]*PASS/ { in_block=1; print; next }
    in_block && /^G[0-9]/ { in_block=0 }
    in_block { print }
  ' "$path")"

  # File path: a token containing "/" or ending in common test extensions
  printf '%s\n' "$g1_block" |
    grep -Eq '([a-zA-Z0-9._/-]+\.(mag|sh|py|m|sage|rb|go|rs|ts|js)|[a-zA-Z0-9._-]+/[a-zA-Z0-9._/-]+)' ||
    fail "G1 Test-evidence PASS block lacks a test file path in $path"

  # Command: look for a shell-invocable command pattern
  printf '%s\n' "$g1_block" |
    grep -Eq '(magma|bash|sh|python|python3|pytest|node|make|go test|cargo test|sage|ruby|rspec)\b' ||
    fail "G1 Test-evidence PASS block lacks an exact test command in $path"

  # Exit code: numeric exit indication
  printf '%s\n' "$g1_block" |
    grep -Eq '(exit[[:space:]](code[[:space:]])?[0-9]+|exit:[[:space:]]*[0-9]+|\bexit\b[[:space:]]*=[[:space:]]*[0-9]+|returned[[:space:]][0-9]+)' ||
    fail "G1 Test-evidence PASS block lacks an exit code in $path"

  # Pass/fail outcome
  printf '%s\n' "$g1_block" |
    grep -Eq '\b(PASS(ED)?|FAIL(ED)?)\b' ||
    fail "G1 Test-evidence PASS block lacks a PASS/FAIL outcome label in $path"

  # Wall time
  printf '%s\n' "$g1_block" |
    grep -Eq '([0-9]+(\.[0-9]+)?[[:space:]]*(ms|s|sec|m|min|h|hour)|wall[[:space:]]time[[:space:]]*:?[[:space:]]*[0-9])' ||
    fail "G1 Test-evidence PASS block lacks a wall time in $path"

  exit 0
fi

# 4b. If N/A: must include an explicit unrunnable reason (non-empty text
#    after the N/A declaration — at least one word beyond "N/A").
if grep -Eq '^G1 Test-evidence:[[:space:]]*N/A\b' "$path"; then

  # The reason must appear on the same line after "N/A" or on the
  # immediately following non-blank line.
  same_line_reason="$(grep -E '^G1 Test-evidence:[[:space:]]*N/A\b' "$path" |
    sed 's/^G1 Test-evidence:[[:space:]]*N\/A[[:space:]]*//')"

  if [ -n "$(printf '%s' "$same_line_reason" | tr -d '[:space:]')" ]; then
    exit 0  # reason on same line
  fi

  # Check the line immediately following the N/A declaration.
  # The following line must be non-empty AND must not be the start of
  # the next gate entry (which would mean there is no reason, just the
  # next gate line immediately after).
  next_line="$(awk '
    /^G1 Test-evidence:[[:space:]]*N\/A/ { found=1; next }
    found { print; exit }
  ' "$path")"

  # Reject if the next line is itself another gate declaration
  is_gate_line="$(printf '%s\n' "$next_line" | grep -Ec '^G[0-9]' || true)"
  if [ -n "$(printf '%s' "$next_line" | tr -d '[:space:]')" ] && [ "${is_gate_line:-0}" -eq 0 ]; then
    exit 0  # reason on following line, and it is not a gate entry
  fi

  fail "G1 Test-evidence is N/A but no unrunnable reason is given in $path"
fi

# If we reach here the declaration has an unrecognised status.
fail "G1 Test-evidence has an unrecognised status (expected PASS or N/A) in $path"
