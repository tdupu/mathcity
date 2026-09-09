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

echo "adjudicated-bead-open-audit: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
