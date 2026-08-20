#!/usr/bin/env bash
# POLICY B2.11/B2.12: every file touching a brief artifact must be registered.
#
# The principle: repeated work goes behind `mctl`; `mctl` is the single point of
# failure by design. An unregistered writer is how the city gets a confident
# wrong answer instead of an error.
#
# This check compares REFERENCES, not writes, against
# assets/brief-pipeline/brief-writers.toml. That over-approximates deliberately
# -- see the register's header for the write-detector that was prototyped and
# rejected for missing a real writer. Registering a harmless reader costs a
# line; missing a writer costs an afternoon.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REGISTER="${REGISTER_OVERRIDE:-$ROOT/assets/brief-pipeline/brief-writers.toml}"

PASS_COUNT=0
FAIL_COUNT=0
ok() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
no() { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

REPORT="$(mktemp)"
set +e
python3 - "$ROOT" "$REGISTER" > "$REPORT" 2>&1 <<'PY'
import sys, tomllib
from pathlib import Path
root, register = Path(sys.argv[1]), Path(sys.argv[2])
reg = tomllib.load(register.open("rb"))
SEARCH = ["assets/scripts"]
EXT = {".py", ".sh"}
total_arts = 0
for art in reg.get("artifact", []):
    total_arts += 1
    literal = art["path"].split("/")[-1]
    registered = {r["file"] for r in art.get("referencer", [])}
    found = set()
    for base in SEARCH:
        for f in (root / base).rglob("*"):
            if not f.is_file() or f.suffix not in EXT or "__pycache__" in str(f):
                continue
            try:
                if literal in f.read_text(errors="replace"):
                    found.add(str(f.relative_to(root)))
            except OSError:
                continue
    for f in sorted(found - registered):
        print(f"UNREGISTERED {art['path']} {f}")
    for f in sorted(registered - found):
        print(f"STALE {art['path']} {f}")
    for r in art.get("referencer", []):
        if r["role"] == "violation" and not r.get("since"):
            print(f"UNDATED {art['path']} {r['file']}")
print(f"ARTIFACTS {total_arts}")
PY
probe_rc=$?
set -e

# --- 0. The probe ran and produced its shape ---------------------------------
# Without this the greps below all return empty on a traceback, and empty reads
# exactly like "no violations found".
# `|| true`: under `set -e` a non-matching grep inside a command
# substitution aborts the script BEFORE the diagnostic below can print --
# it exits 1 with no message, which is a silent failure rather than a
# reported one. Probed: REGISTER_OVERRIDE=/nonexistent.toml produced
# exit 1 and zero output until this was added.
arts="$(grep '^ARTIFACTS ' "$REPORT" 2>/dev/null | awk '{print $2}' || true)"
if [ "$probe_rc" -ne 0 ] || ! [ "${arts:-0}" -ge 1 ] 2>/dev/null; then
  no "register probe failed (rc=$probe_rc); findings below would be vacuous"
  sed 's/^/    /' "$REPORT"
  rm -f "$REPORT"
  echo "brief-writer-authority: $PASS_COUNT passed, $FAIL_COUNT failed"
  exit 1
fi
ok "register probe read $arts governed artifact(s)"

# --- 1. No unregistered referencer -------------------------------------------
if grep -q '^UNREGISTERED ' "$REPORT"; then
  no "a file touches a governed brief artifact without being registered (B2.11)"
  grep '^UNREGISTERED ' "$REPORT" | sed 's/^/    /'
else
  ok "every file touching a governed artifact is registered"
fi

# --- 2. No stale registration ------------------------------------------------
# A register that names files which no longer reference the artifact rots into
# a list nobody trusts.
if grep -q '^STALE ' "$REPORT"; then
  no "the register names a file that no longer references the artifact"
  grep '^STALE ' "$REPORT" | sed 's/^/    /'
else
  ok "no stale entries in the register"
fi

# --- 3. Every violation is dated ---------------------------------------------
# B2.12: the burn-down may only shrink, which requires knowing when each was
# admitted.
if grep -q '^UNDATED ' "$REPORT"; then
  no "a registered violation has no 'since' date (B2.12)"
  grep '^UNDATED ' "$REPORT" | sed 's/^/    /'
else
  ok "every registered violation carries a date"
fi

echo "NOTE: registered violations still to burn down: $(python3 -c "
import tomllib,sys
d=tomllib.load(open('$REGISTER','rb'))
print(sum(1 for a in d['artifact'] for r in a['referencer'] if r['role']=='violation'))")"
rm -f "$REPORT"

echo "brief-writer-authority: $PASS_COUNT passed, $FAIL_COUNT failed"
[ "$FAIL_COUNT" -eq 0 ]
