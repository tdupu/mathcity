#!/bin/sh
# Regression test for tdupu/mathcity#18.
#
# defer is a non-terminal verdict: a deferred decision brief legitimately keeps
# manifest status="ready". Before the fix, present-briefs' Method 3 selector
# filtered on status alone, so every deferred brief resurfaced on the next run.
# The fix is two halves that must BOTH hold:
#   (producer) the verdict writer puts defer_until into the manifest on defer;
#   (selector) present-briefs skips a ready brief whose defer_until is future.
#
# The selector half still extracts and runs the ACTUAL embedded heredoc from
# present-briefs' SKILL.md, so it exercises the shipped code rather than a copy.
#
# The producer half used to do the same against a heredoc inside
# adjudicate-brief. That writer is GONE -- not weakened, relocated. The skill
# was one of four callers of the same act (dashboard, CLI, MCP, skill), so a
# manifest write that only ran when the skill ran left the row stale on the
# other three routes. `mctl_core/effects.py::_update_decisions_track_row` now
# owns it for every caller, and the producer half below calls THAT. Same two
# assertions, against the implementation that actually ships rather than a copy
# of it embedded in documentation.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
PACK="$(cd "$HERE/../.." && pwd)"
PB="$PACK/skills/present-briefs/SKILL.md"
PASS=0; FAIL=0
ok()  { echo "PASS: $1"; PASS=$((PASS+1)); }
bad() { echo "FAIL: $1"; FAIL=$((FAIL+1)); }

# --- extract the legacy fallback selector heredoc from present-briefs ---
SEL="$(mktemp)"
awk '/^### Method 2 — decisions-track legacy fallback/{section=1;next} section&&/python3 - "\$DECISIONS_DIR" <<'"'"'PY'"'"'/{f=1;next} f&&/^PY$/{exit} f{print}' "$PB" > "$SEL"
[ -s "$SEL" ] || { echo "FAIL: could not extract selector heredoc"; exit 1; }

# --- the shipped manifest writer, called directly ---
# Args mirror the old heredoc's, so the two PRODUCER cases below are unchanged:
#   <manifest> <n> <manifest-status> <verdict> <note> <today> [defer_until]
WR="$(mktemp)"
cat >"$WR" <<'PY'
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[1])
from mctl_core.effects import _update_decisions_track_row

path, n, ms, verdict, note, today = (
    Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5], sys.argv[6], sys.argv[7]
)
defer_until = sys.argv[8] if len(sys.argv) > 8 else ""
if ms == "ready":
    # Non-terminal: keep it ripe and record the un-defer date (#18).
    fields = {"status": ms}
    if defer_until:
        fields["defer_until"] = defer_until
    _update_decisions_track_row(path, n, fields)
else:
    _update_decisions_track_row(
        path,
        n,
        {"status": ms, "verdict": verdict, "verdict_note": note, "adjudicated_at": today},
        ("defer_until",),
    )
PY

future="2999-01-01"; past="2000-01-01"

echo "=== SELECTOR: future-deferred brief must be skipped; past/malformed/no-defer presented ==="
DD="$(mktemp -d)"
printf '%s\n' \
  '{"n":1,"status":"ready","unlock_count":1}' \
  "{\"n\":2,\"status\":\"ready\",\"defer_until\":\"$future\",\"unlock_count\":1}" \
  "{\"n\":3,\"status\":\"ready\",\"defer_until\":\"$past\",\"unlock_count\":1}" \
  '{"n":4,"status":"ready","defer_until":"2026-8-5","unlock_count":1}' \
  '{"n":5,"status":"adjudicated","unlock_count":1}' > "$DD/manifest.jsonl"
for n in 1 2 3 4 5; do printf '# brief\n' > "$DD/0$n-slug-brief.md"; done
out="$(python3 "$SEL" "$DD" 2>/dev/null | sed 's|.*/0||;s/-slug-brief.md//' | tr '\n' ' ')"
case " $out " in *" 2 "*) bad "future-deferred brief (n=2) was presented: [$out]";; *) ok "future-deferred brief (n=2) skipped";; esac
case " $out " in *" 1 "*) ok "no-defer brief (n=1) presented";;      *) bad "no-defer brief (n=1) missing: [$out]";; esac
case " $out " in *" 3 "*) ok "past-deferred brief (n=3) presented";; *) bad "past-deferred brief (n=3) missing: [$out]";; esac
case " $out " in *" 4 "*) ok "malformed-defer brief (n=4) presented (fail-open)";; *) bad "malformed-defer brief (n=4) missing: [$out]";; esac
case " $out " in *" 5 "*) bad "adjudicated brief (n=5) was presented: [$out]";; *) ok "adjudicated brief (n=5) skipped";; esac

echo "=== PRODUCER: mctl writes defer_until on defer, clears it on terminal ==="
SCRIPTS="$PACK/assets/scripts"
MAN="$(mktemp)"; printf '%s\n' '{"n":7,"status":"ready"}' > "$MAN"
python3 "$WR" "$SCRIPTS" "$MAN" 7 ready defer "later" "$(date +%Y-%m-%d)" "$future" >/dev/null 2>&1
got="$(python3 -c "import json;print(json.loads(open('$MAN').readline()).get('defer_until',''))")"
[ "$got" = "$future" ] && ok "defer verdict wrote defer_until=$future" || bad "defer_until not written (got [$got])"
# now adjudicate it terminally -> defer_until must be cleared
python3 "$WR" "$SCRIPTS" "$MAN" 7 adjudicated approve "ok" "$(date +%Y-%m-%d)" "" >/dev/null 2>&1
gone="$(python3 -c "import json;print('present' if 'defer_until' in json.loads(open('$MAN').readline()) else 'cleared')")"
[ "$gone" = "cleared" ] && ok "terminal verdict cleared defer_until" || bad "defer_until not cleared on terminal verdict"

rm -rf "$SEL" "$WR" "$DD" "$MAN"
echo ""
echo "=== SUMMARY: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
