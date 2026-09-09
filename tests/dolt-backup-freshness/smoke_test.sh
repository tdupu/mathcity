#!/bin/sh
# dolt-backup-freshness — a backup that reports success and writes nothing (#79).
#
# Case 4 is the one that keeps this check usable: a store nobody has written in
# months does not need a recent push, and failing on it is how a check earns a
# permanent place on everyone's ignore list. Staleness is measured against LOCAL
# WRITES, not the calendar, whenever a --store is given.
set -eu

SCRIPT="$(CDPATH= cd -- "$(dirname -- "$0")/../../assets/scripts" && pwd)/dolt-backup-freshness.py"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
pass=0; fail=0
mkdir -p "$TMP/bin"

# fake `gh`: prints the date recorded for the repo it is asked about
fake_gh() {  # $1 = repo suffix, $2 = ISO date (or EMPTY to simulate failure)
  printf '%s' "$2" > "$TMP/date-$1"
}
cat > "$TMP/bin/gh" <<'EOF'
#!/bin/sh
# args: api repos/OWNER/NAME --jq .pushed_at
repo=$(printf '%s\n' "$@" | grep '^repos/' | head -1)
name=$(basename "$repo")
f="$TMPDIR_FAKE/date-$name"
[ -f "$f" ] || { echo "not found" >&2; exit 1; }
v=$(cat "$f")
[ -n "$v" ] || { echo "empty" >&2; exit 1; }
echo "$v"
EOF
chmod +x "$TMP/bin/gh"

run() {  # $1 name, $2 want-exit, rest args
  n="$1"; want="$2"; shift 2
  if out="$(PATH="$TMP/bin:$PATH" TMPDIR_FAKE="$TMP" python3 "$SCRIPT" "$@" 2>&1)"; then rc=0; else rc=$?; fi
  if [ "$rc" = "$want" ]; then
    pass=$((pass + 1)); echo "  ok   $n (exit=$rc)"
  else
    fail=$((fail + 1)); echo "  FAIL $n: exit=$rc want=$want"; printf '%s\n' "$out" | sed 's/^/       /'
  fi
}

recent="$(python3 -c "import datetime as d;print((d.datetime.now(d.timezone.utc)-d.timedelta(days=1)).isoformat().replace('+00:00','Z'))")"
old="$(python3    -c "import datetime as d;print((d.datetime.now(d.timezone.utc)-d.timedelta(days=40)).isoformat().replace('+00:00','Z'))")"

echo "dolt-backup-freshness:"

# 1. CONTROL — a recently pushed backup passes
fake_gh fresh-dolt "$recent"
run "recent backup is fresh"                    0 --remote "o/fresh-dolt"

# 2. calendar-stale backup with no --store
fake_gh old-dolt "$old"
run "40-day-old backup is STALE"                1 --remote "o/old-dolt"

# 3. unreachable remote -> 2, NOT 0
fake_gh broken-dolt ""
run "unqueryable remote exits 2, not fresh"     2 --remote "o/broken-dolt"

# 4. THE ONE THAT MATTERS: old backup, but the store has not been written either.
#    Nothing to back up means nothing is wrong.
mkdir -p "$TMP/quiet"
python3 - "$TMP/quiet" <<'PY'
import os, sys, time
p = os.path.join(sys.argv[1], "chunk")
open(p, "w").close()
old = time.time() - 60 * 60 * 24 * 60      # 60 days ago
os.utime(p, (old, old))
PY
fake_gh quiet-dolt "$old"
run "quiet store with old backup is NOT stale"  0 --remote "o/quiet-dolt=$TMP/quiet"

# 5. old backup AND fresh local writes -> the #79 condition
mkdir -p "$TMP/busy"; : > "$TMP/busy/chunk"
fake_gh busy-dolt "$old"
run "written store with old backup IS stale"    1 --remote "o/busy-dolt=$TMP/busy"

echo "dolt-backup-freshness: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
