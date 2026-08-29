#!/usr/bin/env bash
# Executable behaviour test for the revise-return re-file logic (gt-5yxup1).
#
# The formula's scan+rig-resolution lives in a sourceable pack library
# (assets/scripts/revise-return-lib.sh) precisely so it can be exercised here
# instead of only pinned by prose (POLICY P6.2 — a check must be able to fail).
#
# Covers the two observed-failing cases Taylor named:
#   * dead-scan repro: an empty root yields ZERO pending revises; a populated
#     root yields the revise slug (re-filing becomes possible once the WRITER
#     populates the aggregated root the formula scans).
#   * rig behaviour: DEFAULT re-files to the source rig; a reason that names a
#     target rig ("move to rig X") re-files into that rig instead.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
LIB="$HERE/../../assets/scripts/revise-return-lib.sh"

test -f "$LIB" || { echo "FAIL: missing lib $LIB"; exit 1; }
# shellcheck disable=SC1090
. "$LIB"

RIGS='{"rigs":[{"name":"mathcity","prefix":"mc"},{"name":"hecke","prefix":"he"},{"name":"city","prefix":"city"}]}'

fail=0
check() { # label expected actual
  if [ "$2" = "$3" ]; then
    echo "  ok: $1"
  else
    echo "  FAIL: $1 — expected [$2], got [$3]"; fail=1
  fi
}

echo "resolve_target_rig:"
# DEFAULT: no directive -> source rig from the bead prefix.
check "default -> source rig (mc)" "mathcity" \
  "$(revise_resolve_target_rig 'tighten section 3' 'mc-abc' "$RIGS")"
check "default -> source rig (he)" "hecke" \
  "$(revise_resolve_target_rig 'needs more evidence' 'he-xyz' "$RIGS")"
# RIG-MOVE: reason names a known target rig -> that rig.
check "move to rig hecke" "hecke" \
  "$(revise_resolve_target_rig 'move to rig hecke and tighten' 'mc-abc' "$RIGS")"
check "arrow-> rig city" "city" \
  "$(revise_resolve_target_rig 'revise then -> rig city' 'mc-abc' "$RIGS")"
# A directive naming an UNKNOWN rig is ignored (does not misroute) -> source rig.
check "unknown rig directive ignored -> source rig" "hecke" \
  "$(revise_resolve_target_rig 'move to rig atlantis' 'he-xyz' "$RIGS")"

echo "scan_pending:"
EMPTY="$(mktemp -d)"
check "dead-scan: empty root -> 0 pending" "" \
  "$(revise_scan_pending "$EMPTY")"

POP="$(mktemp -d)"
mkdir -p "$POP/decisions"
cat > "$POP/decisions/mc-brief1.toml" <<'EOF'
brief_id = "mc-brief1"
decision = "revise"
reason = "tighten"
source_bead = "mc-src1"
EOF
cat > "$POP/decisions/mc-brief2.toml" <<'EOF'
brief_id = "mc-brief2"
decision = "approve"
reason = "ok"
source_bead = "mc-src2"
EOF
check "populated root -> only the revise slug" "mc-brief1" \
  "$(revise_scan_pending "$POP")"

# Idempotency: a success ledger line settles the slug -> no longer pending.
printf '%s\n' '{"brief_slug":"mc-brief1","redeposited_at":"2026-08-29T00:00:00Z"}' \
  > "$POP/revise-returned.jsonl"
check "already re-deposited -> 0 pending" "" \
  "$(revise_scan_pending "$POP")"

rm -rf "$EMPTY" "$POP"
[ "$fail" -eq 0 ] && echo "PASS revise-return refile" || { echo "FAILURES"; exit 1; }
