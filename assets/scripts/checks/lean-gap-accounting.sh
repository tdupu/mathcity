#!/usr/bin/env bash
set -euo pipefail

# Three-count invariant for a bounded formalization scope:
#
#   count(sorry/admit in project) == count(gap entries) == count(open gap beads)
#
# This is the definition of done: every hole is named in the manuscript and
# tracked as work. Counts that merely "look about right" are not equal.
#
# P6.2 note: every operand that fails to resolve is a FAIL. A missing gap document
# does not mean zero gaps; an unreachable bead store does not mean zero beads.
# All scans are uncapped -- a `head` here would truncate a count into a false pass.

fail() { echo "lean-gap-accounting: $*" >&2; exit 1; }

PROJ="${GC_LEAN_PROJECT_DIR:-${LEAN_PROJECT_DIR:-}}"
GAPDOC="${GC_LEAN_GAP_DOCUMENT:-}"
GAPLABEL="${GC_LEAN_GAP_LABEL:-lean-gap}"

[ -n "$PROJ" ]   || fail "no Lean project dir (set GC_LEAN_PROJECT_DIR)"
[ -d "$PROJ" ]   || fail "Lean project dir does not exist: $PROJ"
[ -n "$GAPDOC" ] || fail "no gap document (set GC_LEAN_GAP_DOCUMENT); refusing to assume zero gaps"
[ -f "$GAPDOC" ] || fail "gap document does not exist: $GAPDOC -- a missing document is not zero gaps"
command -v bd >/dev/null 2>&1 || fail "bd is required on PATH to count gap beads"

# bash 3.2 on this platform has no `mapfile`; use a file list instead.
FILELIST=$(mktemp); trap 'rm -f "$FILELIST"' EXIT
find "$PROJ" -name '*.lean' -not -path '*/.lake/*' -not -path '*/lake-packages/*' 2>/dev/null | sort > "$FILELIST"
N_FILES=$(grep -c . "$FILELIST" || true)
[ "$N_FILES" -gt 0 ] || fail "no .lean files under $PROJ -- operand did not resolve"

# `grep -c` exits 1 when a file has zero matches, and `set -o pipefail` would then
# kill the script silently on a CLEAN project -- the exact case this gate must be
# able to pass. Neutralise the pipeline's status explicitly.
N_SORRY=$( { xargs -I{} grep -cE '(^|[^[:alnum:]_])(sorry|admit)([^[:alnum:]_]|$)' {} < "$FILELIST" 2>/dev/null || true; } | awk '{s+=$1} END{print s+0}')

# Gap entries are explicitly marked in the manuscript, one per line:
#   %% LEAN-GAP: <id> -- <description>
N_GAP=$(grep -cE '^[[:space:]]*%+[[:space:]]*LEAN-GAP:' "$GAPDOC" 2>/dev/null || true)

# `--label` is singular (bd list -l); `--labels` is not a flag and exits nonzero.
# Count from --json rather than the pretty rows: row glyphs are presentation and
# have changed before, and a regex that stops matching would silently count zero.
BD_OUT=$(bd list --label "$GAPLABEL" --status open --json 2>&1) || fail "bd could not list gap beads -- an unreachable store is not zero beads: $BD_OUT"
N_BEAD=$(printf '%s' "$BD_OUT" | python3 -c '
import json,sys
try:
    d=json.load(sys.stdin)
except Exception as e:
    sys.stderr.write("lean-gap-accounting: bd --json was not parseable: %s\n" % e); sys.exit(3)
if isinstance(d,dict):
    d=d.get("issues") or d.get("results") or d.get("beads") or []
print(len(d) if isinstance(d,list) else 0)
') || fail "could not parse bd --json output -- refusing to assume zero beads"

echo "lean-gap-accounting: sorries=$N_SORRY gap_entries=$N_GAP open_beads=$N_BEAD"

if [ "$N_SORRY" -eq "$N_GAP" ] && [ "$N_GAP" -eq "$N_BEAD" ]; then
  echo "lean-gap-accounting: PASS (all three counts equal: $N_SORRY)"
  exit 0
fi

echo "lean-gap-accounting: FAIL -- counts differ (sorries=$N_SORRY, gap_entries=$N_GAP, open_beads=$N_BEAD)" >&2
echo "lean-gap-accounting: every sorry needs a '%% LEAN-GAP: <id>' line in $GAPDOC and an open bead labelled '$GAPLABEL'." >&2
exit 1
