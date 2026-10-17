#!/bin/sh
# bead-drift-report.sh — READ-ONLY drift report between the bead stores under
# REPOS_ROOT and their twins under GT_ROOT.
#
# Why read-only. Most city stores run dolt_mode=proxied-server, which refuses
# push/pull/sync outright, and every data-plane op (bd dolt pull/push, bd
# import) requires the authorize-git-operation gate -- which an unattended job
# cannot obtain. So this script MEASURES drift and reports it; a human runs the
# gated union for each store it flags. It opens no store, writes nothing, and
# issues only SELECT COUNT(*).
#
# Pairing. Stores are paired by .beads/metadata.json dolt_database, never by
# directory name: a store directory and its twin can differ in spelling
# (hyphen vs underscore), and name-matching such a pair is what silently
# produced a remote-only union on 2026-10-15. Where the two sides disagree on
# the database name, TWIN_ALIASES in the conf supplies the mapping.
#
# WHAT THIS DOES NOT MEASURE. The delta is COUNT(*) on issues, so it detects a
# count difference, not divergence. Two stores with equal counts can hold
# different content: a 2026-10-15 import reported 2417 same-timestamp rows and
# only hashing proved 0 of them differed. Treat every number as a LOWER BOUND
# on drift, and a +0 as "no count drift", never as "in sync".
#
# Embedded stores have no database on a shared server, so a server query is
# meaningless for them; they are reported EMBEDDED, never as a read failure.
#
# Exits 0 only if every server-backed store was READ. An unreadable store is a
# LOUD failure with a nonzero exit, never a silent skip -- a report that cannot
# fail is the defect this script exists to avoid.
#
# Usage: bead-drift-report.sh [--conf <path>]   (default ~/.gc/bead-drift.conf)

set -u

CONF="${BEAD_DRIFT_CONF:-${HOME}/.gc/bead-drift.conf}"
[ "${1:-}" = "--conf" ] && { CONF="${2:?--conf needs a path}"; shift 2; }

# --- Dependency pre-flight (POLICY.md P1.14): probe before sourcing, never let
# --- the shell error on `source`, and never fall back to a default silently.
if [ ! -f "$CONF" ]; then
  echo "I'm sorry, I can't do that — no bead-drift conf at $CONF."
  echo "Run /setup-bead-drift to create it from assets/bead-drift.conf.example."
  echo "(The conf supplies the Dolt endpoints and store roots this report compares.)"
  exit 1
fi
# shellcheck disable=SC1090
. "$CONF"

for v in MYSQL_BIN REPOS_ROOT GT_ROOT DB_HOST REPOS_PORT GT_PORT MYSQL_USER; do
  eval "val=\${$v:-}"
  [ -n "${val}" ] && continue
  echo "I'm sorry, I can't do that — $CONF does not set $v."
  echo "Run /setup-bead-drift to regenerate it, or add $v by hand."
  echo "(Every value is needed to reach both Dolt servers and locate both store roots.)"
  exit 1
done

if [ ! -x "$MYSQL_BIN" ]; then
  echo "I'm sorry, I can't do that — no executable mysql client at $MYSQL_BIN."
  echo "Install one (brew install mysql-client) and set MYSQL_BIN in $CONF."
  echo "(Dolt ships no 'dolt sql --host' and no 'dolt sql-client', so an external client is required.)"
  exit 1
fi

for d in "$REPOS_ROOT" "$GT_ROOT"; do
  [ -d "$d" ] && continue
  echo "I'm sorry, I can't do that — store root $d does not exist."
  echo "Correct REPOS_ROOT / GT_ROOT in $CONF."
  echo "(The report compares each store under one root against its twin under the other.)"
  exit 1
done

count() { # count <port> <db> -> issue count, empty on failure
  "$MYSQL_BIN" --protocol=TCP -h "$DB_HOST" -P "$1" -u "$MYSQL_USER" \
    --ssl-mode=DISABLED -N -B -e "SELECT COUNT(*) FROM \`$2\`.issues;" 2>/dev/null
}
meta() { python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2],''))" "$1" "$2" 2>/dev/null; }
alias_for() {
  for pair in $TWIN_ALIASES; do
    case "$pair" in "$1":*) echo "${pair#*:}"; return ;; esac
  done
  echo "$1"
}

echo "[drift] START $(date -u +%Y-%m-%dT%H:%M:%SZ)"
printf '%-26s %-26s %8s %8s %8s  %s\n' STORE TWIN_DB THIS TWIN DELTA MODE

fail=0; drift=0; read_ok=0
for rp in "$REPOS_ROOT"/*/; do
  rmeta="${rp}.beads/metadata.json"
  [ -f "$rmeta" ] || continue
  name=$(basename "$rp")
  rdb=$(meta "$rmeta" dolt_database); [ -n "$rdb" ] || continue

  if [ "$(meta "$rmeta" dolt_mode)" = "embedded" ]; then
    printf '%-26s %-26s %8s %8s %8s  %s\n' "$name" "$rdb" EMBEDDED - - embedded
    continue
  fi

  want=$(alias_for "$rdb")
  gdb=""; gmode="-"
  for gp in "$GT_ROOT"/*/ "$GT_ROOT"/; do
    gmeta="${gp}.beads/metadata.json"
    [ -f "$gmeta" ] || continue
    [ "$(meta "$gmeta" dolt_database)" = "$want" ] || continue
    gdb="$want"; gmode=$(meta "$gmeta" dolt_mode); break
  done

  this=$(count "$REPOS_PORT" "$rdb")
  if [ -z "$this" ]; then
    printf '%-26s %-26s %8s %8s %8s  %s\n' "$name" "${gdb:--}" READ_FAIL - - "$gmode"
    fail=$((fail+1)); continue
  fi
  read_ok=$((read_ok+1))

  if [ -z "$gdb" ]; then
    printf '%-26s %-26s %8s %8s %8s  %s\n' "$name" "(no twin)" "$this" - - -
    continue
  fi
  twin=$(count "$GT_PORT" "$gdb")
  if [ -z "$twin" ]; then
    printf '%-26s %-26s %8s %8s %8s  %s\n' "$name" "$gdb" "$this" READ_FAIL - "$gmode"
    fail=$((fail+1)); continue
  fi
  d=$((twin-this))
  printf '%-26s %-26s %8s %8s %+8d  %s\n' "$name" "$gdb" "$this" "$twin" "$d" "$gmode"
  [ "$d" -ne 0 ] && drift=$((drift+1))
done

echo "[drift] stores read=$read_ok  count_drift=$drift  read_failures=$fail"
[ "$drift" -ne 0 ] && {
  echo "[drift] ACTION: $drift store(s) show count drift. Run the gated union (authorize-git-operation) per nonzero DELTA."
  echo "[drift] NOTE: +0 means no COUNT drift, not identical content. Only hashing proves content equality."
}
if [ "$fail" -ne 0 ]; then
  echo "[drift] FAILED $(date -u +%Y-%m-%dT%H:%M:%SZ) — $fail store(s) unreadable; the numbers above are INCOMPLETE"
  exit 1
fi
echo "[drift] DONE $(date -u +%Y-%m-%dT%H:%M:%SZ)"
