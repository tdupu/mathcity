#!/usr/bin/env bash
set -euo pipefail

# Proof-completeness gate: no UNRECORDED sorry/admit in the Lean project.
#
# A `sorry` is permitted ONLY when it is recorded -- named in the gap document and
# tracked by an open bead. An unrecorded sorry is a silent hole behind a green
# build, which is the single most misleading state a formalization can be in.
#
# P6.2 note: an unresolvable project dir FAILS. It must never report "0 sorries"
# because it could not look -- that reading is how a scan becomes a false
# assurance. The scan is also UNCAPPED: no `head`, which would truncate the count
# and manufacture a pass.

fail() { echo "lean-no-sorry: $*" >&2; exit 1; }

PROJ="${GC_LEAN_PROJECT_DIR:-${LEAN_PROJECT_DIR:-}}"
[ -n "$PROJ" ] || fail "no Lean project dir (set GC_LEAN_PROJECT_DIR); refusing to pass a check that cannot look"
[ -d "$PROJ" ] || fail "Lean project dir does not exist: $PROJ"

# Only the project's OWN sources. Dependencies under .lake are not ours.
# bash 3.2 on this platform has no `mapfile`; use a file list instead.
FILELIST=$(mktemp); trap 'rm -f "$FILELIST"' EXIT
find "$PROJ" -name '*.lean' -not -path '*/.lake/*' -not -path '*/lake-packages/*' 2>/dev/null | sort > "$FILELIST"
N_FILES=$(grep -c . "$FILELIST" || true)
[ "$N_FILES" -gt 0 ] || fail "no .lean files found under $PROJ -- operand did not resolve; refusing to report zero"

HITS=$(xargs -I{} grep -nE '(^|[^[:alnum:]_])(sorry|admit)([^[:alnum:]_]|$)' {} /dev/null < "$FILELIST" 2>/dev/null || true)
COUNT=$(printf '%s' "$HITS" | grep -c . || true)

if [ "$COUNT" -eq 0 ]; then
  echo "lean-no-sorry: PASS (0 sorry/admit across $N_FILES files)"
  exit 0
fi

echo "lean-no-sorry: FAIL -- $COUNT sorry/admit occurrence(s) across $N_FILES files:" >&2
printf '%s\n' "$HITS" >&2
echo "lean-no-sorry: each must be named in the gap document AND carry an open bead (see lean-gap-accounting.sh)." >&2
exit 1
