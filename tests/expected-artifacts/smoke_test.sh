#!/usr/bin/env bash
# RED TEST for #142 -- the evidence keystone.
#
# HOW THIS COULD FAIL (required by P6.2): it fails today, on every assertion,
# because `gc.expected_artifacts.v1` is declared by no formula in this pack.
# Run it against the parent commit and every check below reports FAIL.
#
# What it pins, and why each matters:
#   1. At least one formula DECLARES the key -- without a declaration the field
#      is永 absent, and an always-absent field renders identically to "we did not
#      look" (#104).
#   2. The value is a JSON array -- `Metadata` is map[string]string upstream, so
#      structured values ride as JSON under a `.v1` key. That is the existing
#      house convention (gc.graphv2_vars.v1 is parsed with json.Unmarshal).
#   3. Every declared path is RELATIVE, never absolute and never cwd-anchored.
#      An artifact path resolved against the runtime cwd is the #71 defect:
#      the agent work dir is not the pack root, so an absolute or bare-relative
#      path silently resolves to nothing and `is_complete` reads false for
#      healthy work -- the exact inversion #115 exists to prevent.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
KEY="gc.expected_artifacts.v1"
PASS=0; FAIL=0
ok()  { printf 'PASS: %s\n' "$1"; PASS=$((PASS+1)); }
no()  { printf 'FAIL: %s\n' "$1"; FAIL=$((FAIL+1)); }

echo "=== 1. at least one formula declares $KEY ==="
declarers=$(grep -rl "$KEY" "$ROOT/formulas" 2>/dev/null || true)
if [ -n "$declarers" ]; then
  ok "declared in: $(echo "$declarers" | xargs -n1 basename | tr '\n' ' ')"
else
  no "no formula declares $KEY -- the keystone is not laid"
fi

echo "=== 2. every declared value parses as a JSON array of strings ==="
bad=0
while IFS= read -r f; do
  [ -n "$f" ] || continue
  python3 - "$f" "$KEY" <<'PY' || bad=1
import json,re,sys
src=open(sys.argv[1],encoding="utf-8").read()
key=sys.argv[2]
found=False
for m in re.finditer(re.escape(key)+r'"?\s*=\s*"((?:[^"\\]|\\.)*)"', src):
    found=True
    raw=m.group(1).encode().decode("unicode_escape")
    v=json.loads(raw)
    assert isinstance(v,list) and all(isinstance(x,str) for x in v), f"not a JSON array of strings: {raw!r}"
sys.exit(0 if found else 1)
PY
done <<< "$declarers"
if [ -n "$declarers" ] && [ "$bad" = "0" ]; then
  ok "all declared values are JSON arrays of strings"
else
  no "declared values missing or not a JSON array of strings"
fi

echo "=== 3. no declared artifact path is absolute or cwd-anchored ==="
abs=$(grep -rh "$KEY" "$ROOT/formulas" 2>/dev/null | grep -oE '"/[^"]*"|\\"/[^\\]*\\"' || true)
if [ -z "$declarers" ]; then
  # P6.2 applied to this test: with zero declarations there is nothing to
  # check, and reporting PASS here would be indistinguishable from "we looked
  # and found no absolute paths". A check that cannot fail must not render as
  # a check that passed.
  no "NOT EVALUATED -- no declarations exist to check (this is not a pass)"
elif [ -z "$abs" ]; then
  ok "no absolute paths declared (cwd-relative resolution is the #71 defect)"
else
  no "absolute path(s) declared: $abs"
fi

echo ""
echo "=== SUMMARY: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ]
