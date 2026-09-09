#!/bin/sh
# b31-acceptance-audit — the audit must distinguish three outcomes, not two.
#
# The failure mode being guarded against is a check that collapses "I could not
# look" into "I looked and it was clean" (P6.2). Exit 2 must stay distinct from
# exit 0, and a fake `bd` on PATH is used so the fixtures do not depend on any
# live bead store.
set -eu

SCRIPT="$(CDPATH= cd -- "$(dirname -- "$0")/../../assets/scripts" && pwd)/b31-acceptance-audit.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0

mkbd() {  # $1 = dir, $2 = JSON payload, $3 = exit code
  mkdir -p "$1/bin" "$1/rig"
  printf '%s' "$2" > "$1/payload.json"
  cat > "$1/bin/bd" <<EOF
#!/bin/sh
cat "$1/payload.json"
exit $3
EOF
  chmod +x "$1/bin/bd"
}

run() {  # $1 name, $2 dir, $3 want-exit, $4 extra args
  if out="$(PATH="$2/bin:$PATH" python3 "$SCRIPT" --rig-root "$2/rig" $4 2>&1)"; then
    rc=0
  else
    rc=$?
  fi
  if [ "$rc" = "$3" ]; then
    pass=$((pass + 1)); echo "  ok   $1 (exit=$rc)"
  else
    fail=$((fail + 1)); echo "  FAIL $1: exit=$rc want=$3"
    printf '%s\n' "$out" | sed 's/^/       /'
  fi
}

echo "b31-acceptance-audit:"

# 1. in-scope closure WITHOUT acceptance -> 1
mkbd "$TMP/a" '[{"id":"mc-1","status":"closed","closed_at":"2026-09-09T10:00:00Z","metadata":{},"title":"x"}]' 0
run "in-scope closure missing acceptance fails" "$TMP/a" 1 ""

# 2. same bead WITH acceptance -> 0  (control: the check can pass)
mkbd "$TMP/b" '[{"id":"mc-1","status":"closed","closed_at":"2026-09-09T10:00:00Z","metadata":{"mctl_close_acceptance":"limb 2, evidence in mc-9"},"title":"x"}]' 0
run "in-scope closure with acceptance passes" "$TMP/b" 0 ""

# 3. closure BEFORE the cutoff is grandfathered, not scored -> 0
#    Without this the audit would fail permanently on 589 historical closures
#    that could not have carried a field that did not exist.
mkbd "$TMP/c" '[{"id":"mc-1","status":"closed","closed_at":"2020-01-01T10:00:00Z","metadata":{},"title":"x"}]' 0
run "pre-cutoff closure is grandfathered"     "$TMP/c" 0 ""

# 4. unreadable store -> 2, NOT 0 and NOT 1
mkbd "$TMP/d" 'not json at all' 1
run "unreadable store exits 2 (not clean)"    "$TMP/d" 2 ""

# 5. undated closure is bucketed, never silently assumed old
mkbd "$TMP/e" '[{"id":"mc-1","status":"closed","metadata":{},"title":"x"}]' 0
run "undated closure does not fail the audit"  "$TMP/e" 0 ""
if PATH="$TMP/e/bin:$PATH" python3 "$SCRIPT" --rig-root "$TMP/e/rig" --json 2>/dev/null \
     | grep -q '"undated_closures": 1'; then
  pass=$((pass + 1)); echo "  ok   undated closure is REPORTED, not dropped"
else
  fail=$((fail + 1)); echo "  FAIL undated closure not reported in JSON"
fi

echo "b31-acceptance-audit: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
