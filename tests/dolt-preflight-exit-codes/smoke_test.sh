#!/bin/sh
# mathcity/tests/dolt-preflight-exit-codes/smoke_test.sh
#
# Guards the three-valued `gc dolt health` contract (issues #7, #8).
#
#   exit 0 -> healthy, proceed silently
#   exit 2 -> reachable, compaction quarantined: NON-FATAL, warn and proceed
#   exit 1 / 78 / 127 / anything else -> unreachable, abort with the P1.14 message
#
# Two parts:
#   A. static  — no call site may collapse the probe back to a boolean `||` test,
#                and no reporting site may truncate the health report with `head`
#                (the quarantine block is printed LAST).
#   B. dynamic — the real pre-flight block from enumerate-molecules.sh is executed
#                against stub `gc` binaries returning each exit code.
#
# Self-contained: needs no live gc, bd, Dolt server, or city.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
PACK="$(cd "$HERE/../.." && pwd)"
PREFLIGHT_SRC="$PACK/skills/check-molecules/scripts/enumerate-molecules.sh"
FRAGMENT="$PACK/template-fragments/dolt-preflight.md"

fail() { echo "FAIL: $*" >&2; exit 1; }

echo "=== A. static: no boolean or truncating probes ==="

[ -f "$FRAGMENT" ] || fail "canonical fragment missing: template-fragments/dolt-preflight.md"

# Search skills + subdomain skills only; docs and the fragment itself quote the
# broken idiom on purpose, as the explanation of what not to do.
SEARCH_DIRS="$PACK/skills $PACK/subdomains"

hits=$(grep -rn 'gc dolt health >/dev/null' $SEARCH_DIRS || true)
[ -z "$hits" ] || fail "boolean Dolt probe reintroduced (exit 2 would abort):
$hits"

hits=$(grep -rn 'gc dolt health.*| *head' $SEARCH_DIRS || true)
[ -z "$hits" ] || fail "Dolt health output truncated with head; the compaction
quarantine block is printed last and would be discarded:
$hits"

hits=$(grep -rln 'gc dolt health' $SEARCH_DIRS || true)
for f in $hits; do
  case "$f" in
    # Prose-only mentions: no probe to guard.
    */check-work/SKILL.md|*/check-molecules/SKILL.md) continue ;;
  esac
  # The exit code must be captured and branched on, never discarded.
  grep -q '_dolt_rc\|DOLT_RC' "$f" \
    || fail "$f invokes gc dolt health without capturing its exit code"
  grep -q 'uarantine' "$f" \
    || fail "$f invokes gc dolt health but never handles the exit-2 quarantine case"
done
echo "ok: $(echo "$hits" | wc -w | tr -d ' ') call sites, all exit-code-aware"

echo "=== B. dynamic: pre-flight behavior per exit code ==="

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"

# Extract the live Dolt pre-flight block from the real script, so this test
# tracks the shipped code rather than a copy of it.
awk '/^_dolt_out=\$\(gc dolt health/,/^esac$/' "$PREFLIGHT_SRC" > "$TMP/preflight.sh"
grep -q '^esac$' "$TMP/preflight.sh" \
  || fail "could not extract the pre-flight block from $PREFLIGHT_SRC"
echo 'echo PROCEEDED' >> "$TMP/preflight.sh"

QUARANTINE_REPORT='Server: running (PID 1, port 58506, latency 117ms)

Backups: none found

Compaction quarantine: 2 (auto-GC blocked)
  hecke: post-flatten table value hash changed with row-count increase (held 27d16h)
  hq: post-flatten table value hash changed with row-count increase (held 30d20h)'

make_gc() { # $1 = exit code, $2 = stdout payload
  { echo '#!/bin/sh'
    printf 'cat <<'"'"'GCEOF'"'"'\n%s\nGCEOF\n' "$2"
    echo "exit $1"
  } > "$TMP/bin/gc"
  chmod +x "$TMP/bin/gc"
}

run_preflight() { PATH="$TMP/bin:$PATH" sh "$TMP/preflight.sh" 2>&1; }

# --- exit 0: proceed, no warning ---
make_gc 0 'Server: running (PID 1, port 58506, latency 117ms)'
out=$(run_preflight) || fail "exit 0 must not abort"
echo "$out" | grep -q PROCEEDED || fail "exit 0 must proceed"
echo "$out" | grep -qi 'WARNING' && fail "exit 0 must be silent, got: $out"
echo "ok: exit 0 -> proceeds silently"

# --- exit 2: proceed, warn, name the quarantined databases ---
make_gc 2 "$QUARANTINE_REPORT"
out=$(run_preflight) || fail "exit 2 (quarantine) must NOT abort — this is the bug"
echo "$out" | grep -q PROCEEDED || fail "exit 2 must proceed; got: $out"
echo "$out" | grep -qi 'quarantine'  || fail "exit 2 must warn about the quarantine"
echo "$out" | grep -q 'hecke'        || fail "exit 2 warning must name the quarantined DBs"
echo "$out" | grep -q 'hq'           || fail "exit 2 warning must name the quarantined DBs"
echo "$out" | grep -q 'gc dolt compact' || fail "exit 2 warning must point at the reclamation path"
echo "$out" | grep -qi "I'm sorry" && fail "exit 2 must not emit the abort message"
echo "ok: exit 2 -> warns, names hecke/hq, points at gc dolt compact, proceeds"

# --- exit 1 / 78 / 127: abort with the P1.14 message ---
for rc in 1 78 127; do
  make_gc "$rc" 'unreachable'
  out=$(run_preflight) && fail "exit $rc must abort"
  echo "$out" | grep -q PROCEEDED && fail "exit $rc must not proceed"
  echo "$out" | grep -qi "I'm sorry, I can't do that" \
    || fail "exit $rc must keep the P1.14 message shape; got: $out"
  echo "$out" | grep -q 'gc dolt start\|gc start' \
    || fail "exit $rc must name a fix action (P1.14)"
  echo "ok: exit $rc -> aborts with the P1.14 message"
done

echo "ALL DOLT-PREFLIGHT EXIT-CODE CHECKS PASSED"
