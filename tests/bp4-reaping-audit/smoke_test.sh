#!/bin/sh
# bp4-reaping-audit — BP4.2(b), BP4.2(c) and BP4.4(d) had no enforcement (#238).
#
# Cases 2 and 3 are the ones that matter. BP4.2(c) governs the state AT CLOSE
# TIME, not today. A first version of this audit compared against TODAY's state
# and reported 24 violations on hecke; applying the temporal rule took it to 11.
# The 13 difference were survivors that were open when the duplicate was reaped
# and closed LATER because the work actually got done -- the rule working.
# Case 3 is that shape and MUST pass.
set -eu

SCRIPT="$(CDPATH= cd -- "$(dirname -- "$0")/../../assets/scripts" && pwd)/bp4-reaping-audit.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0

mkbd() {  # $1 dir, $2 json
  mkdir -p "$1/bin" "$1/rig"
  printf '%s' "$2" > "$1/beads.json"
  printf '#!/bin/sh\ncat "%s/beads.json"\n' "$1" > "$1/bin/bd"
  chmod +x "$1/bin/bd"
}

run() {  # $1 name, $2 dir, $3 want
  if out="$(PATH="$2/bin:$PATH" python3 "$SCRIPT" --rig-root "$2/rig" 2>&1)"; then rc=0; else rc=$?; fi
  if [ "$rc" = "$3" ]; then
    pass=$((pass + 1)); echo "  ok   $1 (exit=$rc)"
  else
    fail=$((fail + 1)); echo "  FAIL $1: exit=$rc want=$3"; printf '%s\n' "$out" | sed 's/^/       /'
  fi
}

echo "bp4-reaping-audit:"

# 1. duplicate closed against an OPEN survivor -> clean (control)
mkbd "$TMP/a" '[{"id":"he-a1a1","status":"closed","closed_at":"2026-07-10T00:00:00Z","close_reason":"duplicate: canonical copy is he-b2b2"},
                {"id":"he-b2b2","status":"open"}]'
run "duplicate with an OPEN survivor is clean"        "$TMP/a" 0

# 2. survivor was ALREADY closed when the duplicate was reaped -> violation
mkbd "$TMP/b" '[{"id":"he-a1a1","status":"closed","closed_at":"2026-07-14T00:00:00Z","close_reason":"duplicate: canonical copy is he-b2b2"},
                {"id":"he-b2b2","status":"closed","closed_at":"2026-07-03T00:00:00Z"}]'
run "survivor closed BEFORE the duplicate is a violation" "$TMP/b" 1

# 3. survivor closed AFTER -> NOT a violation (the 13 that the naive check got wrong)
mkbd "$TMP/c" '[{"id":"he-a1a1","status":"closed","closed_at":"2026-07-10T00:00:00Z","close_reason":"duplicate: canonical copy is he-b2b2"},
                {"id":"he-b2b2","status":"closed","closed_at":"2026-07-12T00:00:00Z"}]'
run "survivor closed AFTER the duplicate is clean"    "$TMP/c" 0

# 4. BP4.2(b): supersede naming no bead at all
mkbd "$TMP/d" '[{"id":"he-a1a1","status":"closed","closed_at":"2026-07-10T00:00:00Z","close_reason":"superseded, no longer needed"}]'
run "supersede naming no absorbing bead is a violation" "$TMP/d" 1

# 5. BP4.4(d): a DECISION bead closed by an AUTOMATED SWEEP.
#    The fixture uses gascity's literal reaper close reason
#    (reaper.sh:68 WORKFLOW_ROOT_CLOSE_REASON) because that is what the rule is
#    actually about -- a sweep reaping adjudication history.
mkbd "$TMP/e" '[{"id":"he-a1a1","status":"closed","issue_type":"decision","closed_at":"2026-07-10T00:00:00Z","close_reason":"stale inactive workflow root auto-closed by reaper"},
                {"id":"he-b2b2","status":"open"}]'
run "swept DECISION bead is a violation"              "$TMP/e" 1

# 5b. THE FALSE-POSITIVE GUARD. A human closing a decision as a duplicate or a
#     supersede is ADJUDICATION, not reaping -- B2.2 makes adjudication history
#     permanent, it does not make a decision bead unclosable.
#
#     This check's first live run against the kolchin mathcity rig reported two
#     violations, and BOTH were adjudications:
#       mc-wg331  "REJECTED by Taylor 2026-08-27 18:46 EDT..."
#       mc-kjot0  "Superseded by mc-y88p0 (P0), which revises the same..."
#     The old pattern matched "supersed" anywhere in the reason, so any reasoned
#     human verdict using the word was reported as a policy violation.
mkbd "$TMP/e2" '[{"id":"he-a1a1","status":"closed","issue_type":"decision","closed_at":"2026-07-10T00:00:00Z","close_reason":"Superseded by he-b2b2 (P0), which revises the same source and carries a finding this one lacked."},
                 {"id":"he-b2b2","status":"open"}]'
run "human supersede of a decision is NOT a violation" "$TMP/e2" 0

mkbd "$TMP/e3" '[{"id":"he-a1a1","status":"closed","issue_type":"decision","closed_at":"2026-07-10T00:00:00Z","close_reason":"REJECTED by Taylor 2026-07-10. Candidate 1 is refuted at source and must not ship."},
                 {"id":"he-b2b2","status":"open"}]'
run "human REJECTED verdict is NOT a violation"        "$TMP/e3" 0

# 6. a decision bead closed on a VERDICT is normal, not a reaping
mkbd "$TMP/f" '[{"id":"he-a1a1","status":"closed","issue_type":"decision","closed_at":"2026-07-10T00:00:00Z","close_reason":"Adjudicated: approve by the human adjudicator"}]'
run "adjudicated decision bead is NOT flagged"        "$TMP/f" 0

# 7. unreadable store -> 2
mkdir -p "$TMP/g/bin" "$TMP/g/rig"; printf '#!/bin/sh\nexit 1\n' > "$TMP/g/bin/bd"; chmod +x "$TMP/g/bin/bd"
run "unreadable store exits 2, not 0"                 "$TMP/g" 2

echo "bp4-reaping-audit: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
