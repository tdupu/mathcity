#!/bin/sh
# adjudicated-bead-open-audit — "decided but never started" must be detectable.
#
# Case 4 is the important one. On its first live run this audit reported eight
# beads as "NOT IN its store"; ALL EIGHT existed in the rig's gascity twin
# (~/gt/X vs ~/repos/X) and three were already CLOSED. The beads were fine, the
# prefix->store mapping was a guess. NOT-FOUND now means "absent from EVERY
# store given for the prefix", and this fixture is what keeps that true.
set -eu

SCRIPT="$(CDPATH= cd -- "$(dirname -- "$0")/../../assets/scripts" && pwd)/adjudicated-bead-open-audit.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0

# fake `bd` dispatching on cwd, so one PATH entry can serve several stores
mkdir -p "$TMP/bin"
cat > "$TMP/bin/bd" <<'EOF'
#!/bin/sh
if [ -f "./_beads.json" ]; then cat "./_beads.json"; exit 0; fi
echo "no store here" >&2; exit 1
EOF
chmod +x "$TMP/bin/bd"

brief() {  # $1 root, $2 lane, $3 name, $4 status, $5 bead
  mkdir -p "$1/$2"
  printf -- '---\nstatus: %s\nsource_bead: %s\n---\n\nbody\n' "$4" "$5" > "$1/$2/$3"
}

run() {  # $1 name, $2 want-exit, rest: args
  n="$1"; want="$2"; shift 2
  if out="$(PATH="$TMP/bin:$PATH" python3 "$SCRIPT" "$@" 2>&1)"; then rc=0; else rc=$?; fi
  if [ "$rc" = "$want" ]; then
    pass=$((pass + 1)); echo "  ok   $n (exit=$rc)"
  else
    fail=$((fail + 1)); echo "  FAIL $n: exit=$rc want=$want"
    printf '%s\n' "$out" | sed 's/^/       /'
  fi
}

echo "adjudicated-bead-open-audit:"

# 1. adjudicated brief, bead OPEN -> 1
mkdir -p "$TMP/s1"; echo '[{"id":"gt-a1b2","status":"open"}]' > "$TMP/s1/_beads.json"
brief "$TMP/r1" stack "b.md" adjudicated gt-a1b2
run "adjudicated brief with OPEN bead is caught" 1 --brief-root "$TMP/r1" --store "gt=$TMP/s1"

# 2. same brief, bead CLOSED -> 0   (control: the audit CAN pass)
mkdir -p "$TMP/s2"; echo '[{"id":"gt-a1b2","status":"closed"}]' > "$TMP/s2/_beads.json"
brief "$TMP/r2" stack "b.md" adjudicated gt-a1b2
run "adjudicated brief with CLOSED bead passes"  0 --brief-root "$TMP/r2" --store "gt=$TMP/s2"

# 3. NOT adjudicated -> not scored, even though the bead is open
mkdir -p "$TMP/s3"; echo '[{"id":"gt-a1b2","status":"open"}]' > "$TMP/s3/_beads.json"
brief "$TMP/r3" stack "b.md" draft gt-a1b2
run "un-adjudicated brief with open bead is ignored" 0 --brief-root "$TMP/r3" --store "gt=$TMP/s3"

# 4. THE FALSE-POSITIVE GUARD: absent from store A, CLOSED in store B.
#    With only store A this reports a broken reference. With both it must not.
mkdir -p "$TMP/s4a" "$TMP/s4b"
echo '[{"id":"gt-zzz9","status":"open"}]'   > "$TMP/s4a/_beads.json"
echo '[{"id":"gt-a1b2","status":"closed"}]' > "$TMP/s4b/_beads.json"
brief "$TMP/r4" stack "b.md" adjudicated gt-a1b2
run "bead found in the SECOND store is not NOT-FOUND" 0 \
    --brief-root "$TMP/r4" --store "gt=$TMP/s4a" --store "gt=$TMP/s4b"
run "...and IS a finding when only the first store is given" 1 \
    --brief-root "$TMP/r4" --store "gt=$TMP/s4a"

# 5. archive is one dir per brief -> needs a RECURSIVE scan
mkdir -p "$TMP/s5"; echo '[{"id":"gt-a1b2","status":"open"}]' > "$TMP/s5/_beads.json"
brief "$TMP/r5" "archive/some-brief-dir" "b.md" adjudicated gt-a1b2
run "nested archive brief is scanned"            1 --brief-root "$TMP/r5" --store "gt=$TMP/s5"

# 6. no lane at all -> 2, distinct from "nothing found"
mkdir -p "$TMP/r6"
run "missing lanes exit 2, not 0"                2 --brief-root "$TMP/r6" --store "gt=$TMP/s5"

# 7. MIGRATION INVENTORY: an adjudication whose brief no longer exists as a file
#    Rows carry NO bead id field -- it is recovered from legacy_slug/legacy_file.
#    This lane exists because #72's headline case (gsp-eu2) lives only here, and
#    a brief-file-only scan reported OK for exactly the bead the issue was about.
mkdir -p "$TMP/s7"; echo '[{"id":"gsp-eu2","status":"open"}]' > "$TMP/s7/_beads.json"
mkdir -p "$TMP/r7/stack"
printf '%s\n' '{"file_status":"adjudicated","legacy_slug":"specialist-agents-gsp-eu2","legacy_file":"/x/146-specialist-agents-gsp-eu2-brief.md"}' > "$TMP/inv7.jsonl"
run "inventory row with an OPEN bead is caught" 1 \
    --brief-root "$TMP/r7" --store "gsp=$TMP/s7" --inventory "$TMP/inv7.jsonl"

# 8. A THREE-CHARACTER SUFFIX MUST MATCH.
#    gsp-eu2's suffix is 3 chars. The first version of the scan pattern floored
#    at 4 and excluded the one bead this lane was added to find.
if PATH="$TMP/bin:$PATH" python3 "$SCRIPT" --brief-root "$TMP/r7" \
     --store "gsp=$TMP/s7" --inventory "$TMP/inv7.jsonl" 2>&1 | grep -q 'gsp-eu2'; then
  pass=$((pass + 1)); echo "  ok   three-character bead suffix is matched"
else
  fail=$((fail + 1)); echo "  FAIL gsp-eu2 (3-char suffix) not matched"
fi

# 9. DECORATED statuses count. The live inventory holds
#    "adjudicated:approve-b(push=false)" and ~30 others; an equality test
#    against "adjudicated" would silently drop every one of them.
mkdir -p "$TMP/s9"; echo '[{"id":"he-pb7b","status":"open"}]' > "$TMP/s9/_beads.json"
mkdir -p "$TMP/r9/stack"
printf '%s\n' '{"file_status":"adjudicated:approve-b(move-cliff-part2;rehome-filed)","legacy_slug":"x-he-pb7b"}' > "$TMP/inv9.jsonl"
run "decorated adjudicated:... status still counts" 1 \
    --brief-root "$TMP/r9" --store "he=$TMP/s9" --inventory "$TMP/inv9.jsonl"

# 10. a missing inventory is REPORTED, and does not silently pass
mkdir -p "$TMP/s10"; echo '[]' > "$TMP/s10/_beads.json"; mkdir -p "$TMP/r10/stack"
if PATH="$TMP/bin:$PATH" python3 "$SCRIPT" --brief-root "$TMP/r10" \
     --store "gt=$TMP/s10" --inventory "$TMP/nope.jsonl" 2>&1 | grep -q "inventory not found"; then
  pass=$((pass + 1)); echo "  ok   missing inventory is reported, not ignored"
else
  fail=$((fail + 1)); echo "  FAIL missing inventory passed silently"
fi

echo "adjudicated-bead-open-audit: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
