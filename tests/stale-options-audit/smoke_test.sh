#!/bin/sh
# stale-options-audit — §4 options overtaken by later material (#235).
#
# Cases 2 and 3 are the controls that keep this honest. The signal requires BOTH
# comments AND updated_at > created_at: comment_count alone catches routine
# discussion on an untouched bead, and updated_at alone moves for reasons that
# have nothing to do with new material (a label, a status change). Either one on
# its own would make this fire constantly and get ignored.
set -eu

SCRIPT="$(CDPATH= cd -- "$(dirname -- "$0")/../../assets/scripts" && pwd)/stale-options-audit.py"
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

run() {  # $1 name, $2 dir, $3 want, rest args
  n="$1"; d="$2"; want="$3"; shift 3
  if out="$(PATH="$TMP/bin:$PATH" python3 "$SCRIPT" --rig-root "$TMP/$d" "$@" 2>&1)"; then rc=0; else rc=$?; fi
  if [ "$rc" = "$want" ]; then pass=$((pass+1)); echo "  ok   $n (exit=$rc)"
  else fail=$((fail+1)); echo "  FAIL $n: exit=$rc want=$want"; printf '%s\n' "$out" | sed 's/^/       /'; fi
}

echo "stale-options-audit:"

# 1. comments AND updated-after-created -> flagged
mk a '[{"id":"mc-1","issue_type":"decision","status":"open","comment_count":2,
        "created_at":"2026-08-01T00:00:00Z","updated_at":"2026-08-05T00:00:00Z"}]'
run "post-deposit material is flagged"         a 1

# 2. CONTROL: comments but NEVER updated -> not flagged
mk b '[{"id":"mc-1","issue_type":"decision","status":"open","comment_count":2,
        "created_at":"2026-08-01T00:00:00Z","updated_at":"2026-08-01T00:00:00Z"}]'
run "comments alone do not flag"               b 0

# 3. CONTROL: updated but no comments -> not flagged
mk c '[{"id":"mc-1","issue_type":"decision","status":"open","comment_count":0,
        "created_at":"2026-08-01T00:00:00Z","updated_at":"2026-08-05T00:00:00Z"}]'
run "an update alone does not flag"            c 0

# 4. a non-decision bead is not this tool's business
mk d '[{"id":"mc-1","issue_type":"task","status":"open","comment_count":2,
        "created_at":"2026-08-01T00:00:00Z","updated_at":"2026-08-05T00:00:00Z"}]'
run "non-decision bead ignored"                d 0

# 5. --open-only skips closed decisions.
#    A closed decision's options can no longer be selected, so it cannot be the
#    harm #235 describes.
mk e '[{"id":"mc-1","issue_type":"decision","status":"closed","comment_count":2,
        "created_at":"2026-08-01T00:00:00Z","updated_at":"2026-08-05T00:00:00Z"}]'
run "closed decision skipped under --open-only" e 0 --open-only
run "...but counted without it"                 e 1

# 6. unreadable store -> 2, not 0
mkdir -p "$TMP/f"
run "unreadable store exits 2, not clean"      f 2

echo "stale-options-audit: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
