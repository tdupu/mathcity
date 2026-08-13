#!/usr/bin/env bash
# Smoke test for the pool-agent wake_mode/min_active_sessions invariant (issue #10).
# Run from rig root: bash mathcity/tests/brief-operator-pool-config/smoke_test.sh
#
# THE INVARIANT
#
#   No agent.toml may pair  wake_mode = "fresh"  with  min_active_sessions >= 1.
#
# Why it is a bug, not a style preference:
#
#   min_active_sessions >= 1 creates standing pool demand, so when the member is
#   not live the reconciler issues a RESUME against the existing session bead.
#   wake_mode = "fresh" means that resume replays a stale/dead session's
#   pre_start hook, which hangs and is killed at the ~30s resume deadline. Every
#   subsequent reconcile re-attempts the identical doomed resume, so the pool
#   never materializes a live member and sits at 0 sessions permanently — the
#   exact opposite of what a nonzero minimum is asking for.
#
#   gascity has a guard for this (cmd/gc/pool_desired_state.go, gastownhall/
#   gascity#4849) but it only skips the resume when the session bead is in
#   StateAsleep. Sessions wedged this way are observed in `creating` /
#   `start-pending`, never `asleep`, so the guard does not fire. Until that
#   guard is broadened, the pack must not emit the configuration at all.
#
# The scan is pack-wide on purpose: this must catch a future regression in ANY
# agent, not just brief-operator.
#
# Self-contained: needs no live gc, bd, Dolt server, or city. Requires python3
# (tomllib, stdlib >= 3.11), which the sibling smoke tests already assume.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PACK_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
BRIEF_OPERATOR_TOML="$PACK_ROOT/agents/brief-operator/agent.toml"
PASS=0
FAIL=0
RESULTS=()

check() {
  local desc="$1" result="$2"
  if [ "$result" = "ok" ]; then
    RESULTS+=("  PASS: $desc")
    PASS=$((PASS+1))
  else
    RESULTS+=("  FAIL: $desc — $result")
    FAIL=$((FAIL+1))
  fi
}

# Collect every agent.toml in the pack, excluding VCS internals and any nested
# formula worktrees (which are transient checkouts, not shipped pack config).
AGENT_TOMLS=()
while IFS= read -r f; do
  AGENT_TOMLS+=("$f")
done < <(find "$PACK_ROOT" -name agent.toml -not -path '*/.git/*' -not -path '*/worktrees/*' | sort)

# Check 1: the scan actually found agent.toml files. Without this a broken find
# would make every later assertion pass vacuously.
if [ "${#AGENT_TOMLS[@]}" -gt 0 ]; then
  check "scan found agent.toml files to inspect (${#AGENT_TOMLS[@]})" "ok"
else
  check "scan found agent.toml files to inspect" "no agent.toml found under $PACK_ROOT"
fi

# Check 2: THE INVARIANT — no agent pairs wake_mode="fresh" with min>=1.
# min_active_sessions is optional and defaults to 0 when absent.
if [ "${#AGENT_TOMLS[@]}" -gt 0 ] && violations=$(python3 - "${AGENT_TOMLS[@]}" 2>&1 << 'PY'
import sys, tomllib
bad = []
for path in sys.argv[1:]:
    with open(path, "rb") as fh:
        d = tomllib.load(fh)
    wake = str(d.get("wake_mode", "")).strip()
    try:
        minimum = int(d.get("min_active_sessions", 0) or 0)
    except (TypeError, ValueError):
        print(f"{path}: min_active_sessions is not an integer: "
              f"{d.get('min_active_sessions')!r}", file=sys.stderr)
        sys.exit(1)
    if wake == "fresh" and minimum >= 1:
        bad.append(f'{path}: wake_mode="fresh" with min_active_sessions={minimum}')
if bad:
    print("\n".join(bad), file=sys.stderr)
    sys.exit(1)
PY
); then
  check "no agent.toml pairs wake_mode=\"fresh\" with min_active_sessions >= 1" "ok"
else
  check "no agent.toml pairs wake_mode=\"fresh\" with min_active_sessions >= 1" \
    "self-defeating pool config present (issue #10): $violations"
fi

# Check 3: brief-operator specifically pinned to min_active_sessions = 0.
# Check 2 is the general invariant; this pins the agent that actually regressed,
# so a future edit that drops wake_mode="fresh" cannot quietly restore min=1
# and re-wedge the pool by the other route.
if [ ! -f "$BRIEF_OPERATOR_TOML" ]; then
  check "brief-operator sets min_active_sessions = 0" "not found at $BRIEF_OPERATOR_TOML"
elif actual=$(python3 - "$BRIEF_OPERATOR_TOML" 2>&1 << 'PY'
import sys, tomllib
with open(sys.argv[1], "rb") as fh:
    d = tomllib.load(fh)
got = int(d.get("min_active_sessions", 0) or 0)
if got != 0:
    print(f"min_active_sessions = {got}", file=sys.stderr)
    sys.exit(1)
PY
); then
  check "brief-operator sets min_active_sessions = 0" "ok"
else
  check "brief-operator sets min_active_sessions = 0" "$actual"
fi

# Summary
echo ""
echo "brief-operator-pool-config smoke-test results:"
for r in "${RESULTS[@]}"; do echo "$r"; done
echo ""
if [ "$FAIL" -eq 0 ]; then
  echo "PASS — $PASS/$((PASS+FAIL)) checks passed"
  exit 0
else
  echo "FAIL — $FAIL/$((PASS+FAIL)) checks failed"
  exit 1
fi
