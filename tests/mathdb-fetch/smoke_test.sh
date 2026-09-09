#!/bin/sh
# mathdb-fetch — read-only MathDB access, on the terms MathDB states.
#
# Cases 1 and 2 are the load-bearing ones. MathDB's robots.txt and Terms both
# grant crawler access CONDITIONALLY -- identify accurately, respect the
# Disallow list, reasonable rate. A tool that quietly drifts off those terms
# damages the project's standing with a site it wants to keep reading, and no
# test failure would tell us. So the terms are asserted, not just followed.
set -eu

SCRIPT="$(CDPATH= cd -- "$(dirname -- "$0")/../../assets/scripts" && pwd)/mathdb-fetch.py"
pass=0; fail=0
ok()  { pass=$((pass + 1)); echo "  ok   $1"; }
bad() { fail=$((fail + 1)); echo "  FAIL $1"; }

echo "mathdb-fetch:"

# 1. THE DISALLOW LIST IS REFUSED IN CODE, not merely avoided by habit.
python3 - "$SCRIPT" <<'PY' && ok "robots.txt Disallow prefixes are refused" || bad "a Disallow prefix was allowed"
import importlib.util, sys
spec = importlib.util.spec_from_file_location("m", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
for p in ("/new", "/new/x", "/bookmarks", "/bookmarks/y", "/moderation"):
    try:
        m._refuse_if_disallowed(p)
    except m.Refused:
        continue
    raise SystemExit(f"{p} was NOT refused")
m._refuse_if_disallowed("/p/1/some-slug")     # must still be allowed
PY

# 2. IT IDENTIFIES ITSELF. "identify themselves accurately" is a term of access.
python3 - "$SCRIPT" <<'PY' && ok "User-Agent names the project and a contact route" || bad "User-Agent is not identifying"
import importlib.util, sys
spec = importlib.util.spec_from_file_location("m", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
ua = m.USER_AGENT
assert "mathcity" in ua.lower(), ua
assert "github.com/tdupu/mathcity" in ua, ua
assert "contact" in ua.lower(), ua
PY

# 3. JSON-LD parses into the documented shape.
python3 - "$SCRIPT" <<'PY' && ok "JSON-LD mainEntity parses" || bad "JSON-LD parse broke"
import importlib.util, sys, json
spec = importlib.util.spec_from_file_location("m", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
html = ('<script type="application/ld+json">'
        '{"@context":"x","mainEntity":{"@type":"Question","name":"N",'
        '"text":"T","answerCount":2,"upvoteCount":5}}</script>')
blob = m.JSONLD.search(html)
e = json.loads(blob.group(1))["mainEntity"]
assert e["name"] == "N" and e["text"] == "T" and e["answerCount"] == 2
PY

# 4. HONEST ABSENCE. status/tags are NOT in the JSON-LD; they must come back
#    null with html_fields_parsed false, never regex-guessed. A wrong "solved"
#    on an open problem is the confident-wrong answer this codebase keeps
#    finding, and it would be invisible.
grep -q '"html_fields_parsed": False' "$SCRIPT" \
  && grep -q '"status": None' "$SCRIPT" \
  && ok "status/tags reported as unread, not guessed" \
  || bad "status/tags are being inferred from HTML"

# 5. UNREACHABLE IS EXIT 2, NOT 0. "could not ask" is not "asked and found none".
grep -q 'MATHDB: UNREACHABLE' "$SCRIPT" && grep -q 'return 2' "$SCRIPT" \
  && ok "network failure exits 2, distinct from clean" \
  || bad "network failure not separated from success"

# 6. VERIFICATION IS NEVER DISABLED. A tool that pulls outside text into a
#    decision record must be able to attribute it.
if grep -qE 'CERT_NONE|check_hostname *= *False|verify *= *False' "$SCRIPT"; then
  bad "SSL verification is disabled somewhere"
else
  ok "SSL verification is never disabled"
fi

# 7. RATE IS A PARAMETER WITH A NON-ZERO DEFAULT.
grep -q '"--delay", type=float, default=1.0' "$SCRIPT" \
  && ok "default request delay is non-zero" \
  || bad "no non-zero default delay"

echo "mathdb-fetch: $pass passed, $fail failed"
[ "$fail" -eq 0 ]
