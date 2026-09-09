#!/bin/sh
# orphaned-spec-watch — a spec whose root convoy is gone (#5).
#
# Case 1 is the control and MUST pass: on the live kolchin city all 5 open
# specs have live roots, so the detector's first real run returned OK. A
# detector that only ever returns OK is indistinguishable from one that is
# broken, and this suite exists to tell those apart.
set -eu

SCRIPT="$(CDPATH= cd -- "$(dirname -- "$0")/../../assets/scripts" && pwd)/orphaned-spec-watch.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0

mkdir -p "$TMP/bin"
cat > "$TMP/bin/bd" <<'EOF'
#!/bin/sh
[ -f "./_beads.json" ] && { cat "./_beads.json"; exit 0; }
echo "no store" >&2; exit 1
EOF
chmod +x "$TMP/bin/bd"

mk() { mkdir -p "$TMP/$1"; printf '%s' "$2" > "$TMP/$1/_beads.json"; }

run() {  # $1 name, $2 dir, $3 want-exit, $4 want-substring
  if out="$(PATH="$TMP/bin:$PATH" python3 "$SCRIPT" --rig-root "$TMP/$2" 2>&1)"; then rc=0; else rc=$?; fi
  ok=1
  [ "$rc" = "$3" ] || ok=0
  [ -n "${4:-}" ] && { printf '%s' "$out" | grep -q "$4" || ok=0; }
  if [ "$ok" = 1 ]; then pass=$((pass+1)); echo "  ok   $1 (exit=$rc)"
  else fail=$((fail+1)); echo "  FAIL $1: exit=$rc want=$3"; printf '%s\n' "$out" | sed 's/^/       /'; fi
}

echo "orphaned-spec-watch:"

# 1. CONTROL — spec with an OPEN root is fine
mk a '[{"id":"hq-s1","status":"open","metadata":{"gc.kind":"spec","gc.root_bead_id":"hq-r1"}},
       {"id":"hq-r1","status":"open"}]'
run "spec with a live root passes"            a 0 "every open spec has a live root"

# 2. root CLOSED -> orphaned
mk b '[{"id":"hq-s1","status":"open","metadata":{"gc.kind":"spec","gc.root_bead_id":"hq-r1"}},
       {"id":"hq-r1","status":"closed"}]'
run "spec whose root is CLOSED is orphaned"   b 1 "root closed"

# 3. root ABSENT from the store -> orphaned, and said differently
mk c '[{"id":"hq-s1","status":"open","metadata":{"gc.kind":"spec","gc.root_bead_id":"hq-gone"}}]'
run "spec whose root is ABSENT is orphaned"   c 1 "root ABSENT"

# 4. a CLOSED spec is finished bookkeeping, not an orphan
mk d '[{"id":"hq-s1","status":"closed","metadata":{"gc.kind":"spec","gc.root_bead_id":"hq-r1"}},
       {"id":"hq-r1","status":"closed"}]'
run "closed spec is not reported"             d 0

# 5. a spec naming NO root is bucketed, never assumed orphaned.
#    Inventing a root would manufacture findings -- the same discipline the
#    other audits use for undated closures and unresolvable bead ids.
mk e '[{"id":"hq-s1","status":"open","metadata":{"gc.kind":"spec"}}]'
run "rootless spec is reported, not scored"   e 0 "name no root"

# 6. a NON-spec bead with a dead root is not this detector's business
mk f '[{"id":"hq-w1","status":"open","metadata":{"gc.kind":"workflow","gc.root_bead_id":"hq-gone"}}]'
run "non-spec bead is ignored"                f 0

# 7. unreadable store -> 2, NOT 0
mkdir -p "$TMP/g"
run "unreadable store exits 2, not clean"     g 2

echo "orphaned-spec-watch: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
