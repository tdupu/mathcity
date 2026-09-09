#!/bin/sh
# brief-path-resolver-drift — #65's third condition, made mechanical.
#
#   "A test that fails when a NEW writer appears with its own path logic —
#    same shape as tests/mctl-shim-callsite/smoke_test.sh"
#
# Measured 2026-09-09: 70 files name a brief path literal and 63 never call
# artifact_layout(). Too many to convert in one pass, which is why #65 is a
# stabilise-then-harden issue. So this does what brief-writers.toml does for
# writers — record the known population, fail on anything new.
#
# THE LIST MAY SHRINK; IT MAY NOT GROW (B2.12's rule, applied to path logic).
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
REG="$ROOT/assets/brief-pipeline/path-resolvers.toml"
pass=0; fail=0

echo "brief-path-resolver-drift:"

[ -f "$REG" ] || { echo "  FAIL register missing: $REG"; exit 1; }

# The scan and the register must agree. Anything on disk that is not registered
# is NEW path logic and fails; anything registered that is gone should be
# removed (the list shrinking is the goal, so that is a NOTE, not a failure).
out="$(python3 - "$ROOT" "$REG" <<'PY'
import pathlib, re, sys, tomllib
root = pathlib.Path(sys.argv[1])
reg = tomllib.load(open(sys.argv[2], "rb"))
known = {e["path"] for e in reg["file"]}

PAT = re.compile(r'\.beads/briefs|"\.beads"\s*,\s*"briefs"')
found = set()
for sub in ("assets/scripts", "skills", "formulas"):
    for f in sorted((root / sub).rglob("*")):
        if not f.is_file() or f.suffix not in (".py", ".sh", ".toml", ".md"):
            continue
        try:
            t = f.read_text(errors="replace")
        except Exception:
            continue
        if PAT.search(t):
            found.add(str(f.relative_to(root)))

new = sorted(found - known)
gone = sorted(known - found)
print("NEW:" + ",".join(new))
print("GONE:" + ",".join(gone))
PY
)"
new="$(printf '%s\n' "$out" | sed -n 's/^NEW://p')"
gone="$(printf '%s\n' "$out" | sed -n 's/^GONE://p')"

if [ -z "$new" ]; then
  pass=$((pass + 1)); echo "  ok   no unregistered brief-path logic"
else
  fail=$((fail + 1))
  echo "  FAIL new file(s) with independent brief-path logic:"
  printf '%s\n' "$new" | tr ',' '\n' | sed 's/^/       /'
  echo "       Route through redundant_state.artifact_layout(), or add an entry"
  echo "       to assets/brief-pipeline/path-resolvers.toml with a reason."
fi

# Shrinking is the goal, so a registered file that no longer matches is GOOD.
# It is reported so the register can be trimmed, never as a failure — a check
# that punishes progress is a check people route around.
if [ -n "$gone" ]; then
  echo "  NOTE registered file(s) no longer name a brief path literal —"
  echo "       remove them from the register (this is the list shrinking):"
  printf '%s\n' "$gone" | tr ',' '\n' | sed 's/^/       /'
fi

# The canonical resolver must still exist and be what the register names.
if grep -q "def artifact_layout" "$ROOT/assets/scripts/mctl_core/redundant_state.py"; then
  pass=$((pass + 1)); echo "  ok   canonical resolver artifact_layout() exists"
else
  fail=$((fail + 1)); echo "  FAIL artifact_layout() is gone — the register names a resolver that does not exist"
fi

# Report the burn-down so progress is visible rather than implied.
without="$(python3 -c "
import tomllib,sys
d=tomllib.load(open('$REG','rb'))
print(sum(1 for e in d['file'] if not e['uses_resolver']))
")"
echo "  NOTE $without registered file(s) still carry independent path logic (was 63 on 2026-09-09)"

echo "brief-path-resolver-drift: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
