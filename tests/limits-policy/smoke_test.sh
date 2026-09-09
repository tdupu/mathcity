#!/bin/sh
# limits-policy — timeouts are POLICY, not baked into scripts.
#
# Owner, 2026-09-09: "no baked-in timeouts, that should be a policy. We can give
# warnings or timeout options but it can't be baked in."
#
# Four audit scripts hardcoded their own deadlines (300s x3, 120s x1), chosen by
# whoever wrote them and invisible to whoever ran them. A store slower than one
# agent's guess fails as "unreadable" on a machine where nothing is wrong.
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
pass=0; fail=0

ok()   { pass=$((pass + 1)); echo "  ok   $1"; }
bad()  { fail=$((fail + 1)); echo "  FAIL $1"; }

echo "limits-policy:"

# 1. the policy file exists and parses
if python3 -c "import tomllib;tomllib.load(open('$ROOT/assets/mctl/limits.toml','rb'))" 2>/dev/null; then
  ok "assets/mctl/limits.toml parses"
else
  bad "limits.toml missing or malformed"
fi

# 2. every script reads the policy rather than a literal default
for s in b31-acceptance-audit adjudicated-bead-open-audit bp4-reaping-audit dolt-backup-freshness; do
  f="$ROOT/assets/scripts/$s.py"
  if grep -q '_resolve_limit(' "$f" && ! grep -qE '"--timeout", type=int, default=[0-9]+' "$f"; then
    ok "$s reads policy, no literal default"
  else
    bad "$s still carries a baked-in timeout"
  fi
done

# 3. resolution order: cli beats env beats policy
res() { python3 -c "
import sys; sys.path.insert(0, '$ROOT/assets/scripts')
from mctl_limits import resolve
print('%s %s' % resolve('bead_store_read_seconds', $1))
"; }
[ "$(res None)" = "300 policy" ]  && ok "policy value is used when nothing overrides" \
                                  || bad "policy value not used (got '$(res None)')"
[ "$(res 999)" = "999 cli" ]      && ok "--timeout overrides policy" \
                                  || bad "--timeout did not override"
[ "$(MATHCITY_BEAD_STORE_READ_SECONDS=77 python3 -c "
import sys; sys.path.insert(0, '$ROOT/assets/scripts')
from mctl_limits import resolve
print('%s %s' % resolve('bead_store_read_seconds'))
")" = "77 env" ] && ok "env overrides policy" || bad "env did not override"

# 4. 0 MEANS UNLIMITED, not "zero seconds".
#    This is the case that makes the option honest: sometimes the right answer
#    is "wait as long as it takes", and the alternative is a script silently
#    reporting a clean store because a query was cut off.
[ "$(res 0)" = "None cli" ] && ok "--timeout 0 means UNLIMITED, not instant" \
                            || bad "--timeout 0 mishandled (got '$(res 0)')"

echo "limits-policy: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
