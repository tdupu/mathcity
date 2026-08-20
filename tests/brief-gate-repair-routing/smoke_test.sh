#!/usr/bin/env bash
# Every gate must declare how a failure of it gets repaired.
#
# Defect: the owner's gate-keep ruling (2026-06-23) is a trinity per gate --
# X-policy + X-gate + improve-X. Measured 2026-08-20, exactly ONE of 17 gates
# carries it: G14 has gate_skill/improve_skill, and no other gate has either.
# Worse, NOTHING reads those two keys -- grep across the pack returns only the
# two lines that define them. The repair half of gate construction is dead
# metadata on a single gate.
#
# This test asserts the schema exists on every gate and that no gate names a
# repair that resolves to nothing -- the #69/#73 defect class (a reference to
# a script/skill nothing installs). A gate with no repair yet must say
# "unassigned" out loud rather than name a plausible skill that does not exist.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GATES="$ROOT/assets/brief-pipeline/gates.toml"

PASS_COUNT=0
FAIL_COUNT=0
ok() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
no() { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

REPORT="$(mktemp)"
# `|| true` here would make this whole file a vacuous pass: a traceback leaves
# every `val` lookup empty, which reads identically to "no problems found".
# Probed 2026-08-20 by pointing $GATES at a nonexistent file -- the suite
# reported 4 passed / exit 0. So the probe's exit status AND its output shape
# are both asserted below before any finding is trusted.
set +e
python3 - "$GATES" "$ROOT" > "$REPORT" 2>&1 <<'PY'
import sys, tomllib, pathlib
gates_path, root = sys.argv[1], pathlib.Path(sys.argv[2])
reg = tomllib.load(open(gates_path, "rb"))
VALID = {"skill", "discard", "unassigned"}
missing, bad_kind, dangling, wrong_stop = [], [], [], []
unassigned = []
for g in reg["gates"]:
    kind = g.get("repair_kind")
    if kind is None:
        missing.append(g["id"]); continue
    if kind not in VALID:
        bad_kind.append(f'{g["id"]}={kind}'); continue
    if kind == "unassigned":
        unassigned.append(g["id"])
    # A stop gate must discard, never repair: G5/G5b/G12 trip on
    # server-touching, user-skill-touching and the kill switch.
    if g["kind"] == "stop" and kind != "discard":
        wrong_stop.append(f'{g["id"]}={kind}')
    skill = g.get("repair_skill")
    if kind == "skill" and not skill:
        dangling.append(f'{g["id"]}=skill-kind-with-no-repair_skill')
    if skill:
        found = list(root.glob(f"skills/{skill}")) + list(root.glob(f"subdomains/*/skills/{skill}"))
        if not found:
            dangling.append(f'{g["id"]}->{skill}')
print("TOTAL", len(reg["gates"]))
print("MISSING", ",".join(missing))
print("BADKIND", ",".join(bad_kind))
print("DANGLING", ",".join(dangling))
print("WRONGSTOP", ",".join(wrong_stop))
print("UNASSIGNED", ",".join(unassigned))
PY
probe_rc=$?
set -e
val() { grep "^$1 " "$REPORT" | cut -d' ' -f2- ; }

# --- 0. The probe itself ran and produced the shape we are about to read -----
probe_ok=true
if [ "$probe_rc" -ne 0 ]; then
  no "gate registry probe exited $probe_rc; findings below would be vacuous"
  sed 's/^/    /' "$REPORT"
  probe_ok=false
else
  total="$(val TOTAL)"
  case "$total" in
    ''|*[!0-9]*) no "probe emitted no TOTAL line; findings below would be vacuous"; probe_ok=false ;;
    *) if [ "$total" -lt 1 ]; then
         no "probe read 0 gates; every assertion below would pass vacuously"
         probe_ok=false
       else
         for key in MISSING BADKIND DANGLING WRONGSTOP UNASSIGNED; do
           grep -q "^$key " "$REPORT" || grep -q "^$key$" "$REPORT" || {
             no "probe output is missing the $key line; findings would be vacuous"
             probe_ok=false
           }
         done
         $probe_ok && ok "probe read $total gates and emitted every finding line"
       fi ;;
  esac
fi

if ! $probe_ok; then
  rm -f "$REPORT"
  echo "brief-gate-repair-routing: $PASS_COUNT passed, $FAIL_COUNT failed"
  exit 1
fi

[ -z "$(val MISSING)" ] \
  && ok "every gate declares repair_kind" \
  || no "gates with no repair_kind: $(val MISSING)"

[ -z "$(val BADKIND)" ] \
  && ok "every repair_kind is skill|discard|unassigned" \
  || no "invalid repair_kind: $(val BADKIND)"

[ -z "$(val DANGLING)" ] \
  && ok "no gate names a repair skill that does not exist" \
  || no "repair routing points at nothing installed: $(val DANGLING)"

[ -z "$(val WRONGSTOP)" ] \
  && ok "every stop gate discards rather than repairs" \
  || no "stop gate routed to a repair: $(val WRONGSTOP)"

# Burn-down, not a failure: 13 gates genuinely have no repair skill yet and
# saying so is the honest state. This line exists so the number is visible and
# shrinks deliberately rather than silently.
echo "NOTE: gates still unassigned: $(val UNASSIGNED)"
rm -f "$REPORT"

echo "brief-gate-repair-routing: $PASS_COUNT passed, $FAIL_COUNT failed"
[ "$FAIL_COUNT" -eq 0 ]
