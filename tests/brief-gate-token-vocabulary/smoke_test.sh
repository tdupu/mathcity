#!/usr/bin/env bash
# G14 gate-token vocabulary (POLICY T7 / gates.toml G14).
#
# T7 mandates a tri-state test-execution declaration whose literal tokens are
# PASSED / NOT APPLICABLE / REQUIRED. The gate-evidence enforcers historically
# matched only `(PASS|N/A)\b`, so `PASSED` failed the word boundary and
# `NOT APPLICABLE` matched nothing: a policy-conformant brief was rejected as
# "missing required gate G14".
#
# This test pins the widened vocabulary AND the fail-closed boundary:
#   accepted for G14 : PASSED, NOT APPLICABLE, PASS, N/A
#   rejected for G14 : FAIL, BLOCKED, REQUIRED (execution still owed per T7),
#                      a gate line with no status token, an absent gate row
#   unchanged elsewhere: PASSED / NOT APPLICABLE are NOT accepted for other
#                      gates — POLICY grants the tri-state to G14 only, and
#                      gate-test-evidence.sh's five-field structural check
#                      fires on the literal `PASS` token for G1, so widening
#                      G1 would silently skip it.
#
# Both gate-evidence enforcers are covered:
#   assets/scripts/checks/brief-check.sh        (`require_gate`)
#   assets/scripts/brief-shuffle-fast-drain.py  (`STATUS_PATTERN` + accepted set)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CHECK="$ROOT/assets/scripts/checks/brief-check.sh"
DRAIN="$ROOT/assets/scripts/brief-shuffle-fast-drain.py"
GATES="$ROOT/assets/brief-pipeline/gates.toml"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/brief-gate-token-vocabulary.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT
# Canonical pile membership is the bead query (POLICY B2.4), so the drain
# needs a bead source. This fixture has no bd store, so it injects an empty
# one through the same seam mctl_core.beads.read_beads uses: no brief bead
# means UNRESOLVED, not closed, so these slugs still drain.
BEAD_FIXTURE="$TMP/beads.jsonl"
: >"$BEAD_FIXTURE"

test -f "$CHECK"
test -f "$DRAIN"
test -f "$GATES"

failures=0
note_failure() {
  printf 'brief-gate-token-vocabulary: %s\n' "$1" >&2
  failures=$((failures + 1))
}

G14="G14 Test-execution-silent"

# ---------------------------------------------------------------------------
# Enforcer 1 — brief-check.sh mechanical-gates / require_gate
# ---------------------------------------------------------------------------

# Write a mechanical-gates fixture in which every shell-checked gate is PASS
# except the named key, which carries $3 verbatim. An empty $3 emits the gate
# line with no status token at all; the literal "OMIT" drops the row entirely.
write_mechanical_fixture() {
  out="$1"
  target_key="$2"
  status="$3"
  {
    printf '## Gate Evidence\n'
    for key in \
      "G1 Test-evidence" \
      "G3 Shell-scripts-testable" \
      "G5 Server-touching" \
      "G5b User-skill-touching" \
      "G7 Artifacts-staging" \
      "G8 Brief-record" \
      "G10 Improve-README" \
      "G11 Breadcrumb" \
      "G12 Auto-merge-kill-switch" \
      "G13 Stale-claim" \
      "G14 Test-execution-silent" \
      "G15 Improve-README-silent" \
      "G16 Master-current"
    do
      if [ "$key" = "$target_key" ]; then
        case "$status" in
          OMIT) : ;;
          "") printf '%s:\n' "$key" ;;
          *) printf '%s: %s\n' "$key" "$status" ;;
        esac
      else
        printf '%s: PASS\n' "$key"
      fi
    done
  } >"$out"
}

expect_shell() {
  label="$1"
  key="$2"
  status="$3"
  want="$4" # accept | reject
  fixture="$TMP/shell-$(printf '%s' "$label" | tr ' /' '__').md"
  write_mechanical_fixture "$fixture" "$key" "$status"
  if GC_BRIEF_PATH="$fixture" sh "$CHECK" mechanical-gates >/dev/null 2>&1; then
    got=accept
  else
    got=reject
  fi
  [ "$got" = "$want" ] ||
    note_failure "brief-check.sh mechanical-gates: $label — expected $want, got $got"
}

# The mandated tri-state passing states must be accepted.
expect_shell "G14 PASSED" "$G14" "PASSED — suite green 2026-08-19" accept
expect_shell "G14 NOT APPLICABLE" "$G14" "NOT APPLICABLE — prose-only artifact" accept
# Legacy vocabulary must keep working.
expect_shell "G14 PASS" "$G14" "PASS" accept
expect_shell "G14 N-A" "$G14" "N/A — no runnable surface" accept
# Fail-closed boundary.
expect_shell "G14 FAIL" "$G14" "FAIL — suite red" reject
expect_shell "G14 BLOCKED" "$G14" "BLOCKED — no runner" reject
expect_shell "G14 REQUIRED" "$G14" "REQUIRED — owed by the build worker" reject
expect_shell "G14 no token" "$G14" "" reject
expect_shell "G14 prose only" "$G14" "10 verification commands run, all green" reject
expect_shell "G14 row absent" "$G14" OMIT reject

# The widening is G14-scoped: other gates keep POLICY B1.4's PASS / N/A.
expect_shell "G1 PASSED" "G1 Test-evidence" "PASSED — suite green" reject
expect_shell "G15 NOT APPLICABLE" "G15 Improve-README-silent" "NOT APPLICABLE" reject
expect_shell "G1 PASS" "G1 Test-evidence" "PASS" accept

# ---------------------------------------------------------------------------
# Enforcer 2 — brief-shuffle-fast-drain.py STATUS_PATTERN + accepted statuses
# ---------------------------------------------------------------------------

expect_drain() {
  label="$1"
  target_key="$2"
  status="$3"
  want="$4" # promote | reject
  slug="drain-$(printf '%s' "$label" | tr ' /A-Z' '__a-z')"
  briefs="$TMP/$slug/.beads/briefs"
  mkdir -p "$briefs/.pile"
  python3 - "$GATES" "$briefs/.pile/$slug.md" "$slug" "$target_key" "$status" <<'PY'
import sys
import tomllib

gates_path, out_path, slug, target_key, status = sys.argv[1:6]
with open(gates_path, "rb") as handle:
    config = tomllib.load(handle)
keys = {gate["id"]: gate["evidence_key"] for gate in config["gates"]}
lines = []
for gate_id in config["profiles"]["standard"]["gates"]:
    key = keys[gate_id]
    if key == target_key:
        if status == "OMIT":
            continue
        line = f"{key}:" if status == "" else f"{key}: {status}"
    else:
        line = f"{key}: PASS"
        if gate_id == "G9":
            line += (
                " classifier_state=known_non_no_brainer"
                " reason=g14-vocabulary-fixture"
                " classified_at=2026-08-19T00:00:00Z"
            )
    lines.append(line)
body = "\n".join(lines)
with open(out_path, "w", encoding="utf-8") as handle:
    handle.write(
        f"---\nbrief_slug: {slug}\ngate_profile: standard\n"
        f"source_bead: g14-vocab-source\n---\n\n"
        f"## Gate Evidence\n{body}\n"
    )
PY
  report="$(python3 "$DRAIN" --brief-root "$briefs" --gate-config "$GATES" --bead-fixture "$BEAD_FIXTURE" --max-items 1 --apply --json --no-external)"
  got="$(printf '%s' "$report" | python3 -c '
import json
import sys

report = json.load(sys.stdin)
slug = sys.argv[1]
print("promote" if slug in report.get("promoted", []) else "reject")
' "$slug")"
  [ "$got" = "$want" ] ||
    note_failure "fast-drain: $label — expected $want, got $got"
}

expect_drain "G14 PASSED" "$G14" "PASSED — suite green 2026-08-19" promote
expect_drain "G14 NOT APPLICABLE" "$G14" "NOT APPLICABLE — prose-only artifact" promote
expect_drain "G14 PASS" "$G14" "PASS" promote
expect_drain "G14 N-A" "$G14" "N/A — no runnable surface" promote
expect_drain "G14 FAIL" "$G14" "FAIL — suite red" reject
expect_drain "G14 BLOCKED" "$G14" "BLOCKED — no runner" reject
expect_drain "G14 REQUIRED" "$G14" "REQUIRED — owed by the build worker" reject
expect_drain "G14 no token" "$G14" "" reject
expect_drain "G14 row absent" "$G14" OMIT reject
expect_drain "G1 PASSED" "G1 Test-evidence" "PASSED — suite green" reject

if [ "$failures" -ne 0 ]; then
  printf 'brief-gate-token-vocabulary: %d expectation(s) failed\n' "$failures" >&2
  exit 1
fi

printf 'brief-gate-token-vocabulary: ok\n'
