#!/bin/sh
# #200: the check must FAIL when the tested tree differs from HEAD, and PASS
# when it does not. Both halves matter -- a check that always failed would
# "catch" the defect and be useless, which is the vacuous-check class P6.2 is
# about.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
CHECK="$HERE/../../assets/scripts/checks/tested-tree-matches-commit.sh"
PASS=0; FAIL=0
ok()  { echo "PASS: $1"; PASS=$((PASS+1)); }
bad() { echo "FAIL: $1" >&2; FAIL=$((FAIL+1)); }

[ -x "$CHECK" ] || { echo "FAIL: $CHECK missing or not executable" >&2; exit 1; }

SANDBOX=$(mktemp -d)
trap 'rm -rf "$SANDBOX"' EXIT
cd "$SANDBOX"
git init -q .
git config user.email t@e; git config user.name t
printf 'one\n' > f.txt
git add f.txt && git commit -qm init

# 1. clean tree -> OK
if (cd "$SANDBOX" && sh "$CHECK" >/dev/null 2>&1); then
  ok "a clean tree reports OK"
else
  bad "a clean tree was reported as a mismatch"
fi

# 2. the DEFECT: edited but not staged -> must fail, and name the file
printf 'two\n' > f.txt
OUT="$(cd "$SANDBOX" && sh "$CHECK" 2>&1 || true)"
if printf '%s' "$OUT" | grep -q 'MISMATCH'; then
  ok "an unstaged edit is reported as a mismatch (#200)"
else
  bad "an unstaged edit was NOT caught -- this is the defect itself"
fi
if printf '%s' "$OUT" | grep -q 'f.txt'; then
  ok "the report names the differing file"
else
  bad "the report does not name the file, so it is unactionable"
fi

# 3. staged but not committed -> still a mismatch by default (it is not in HEAD)
git add f.txt
if (cd "$SANDBOX" && sh "$CHECK" >/dev/null 2>&1); then
  bad "a staged-but-uncommitted change was reported clean; it is not in HEAD"
else
  ok "staged-but-uncommitted still differs from HEAD"
fi

# 4. --staged-ok tolerates it, for mid-commit use
if (cd "$SANDBOX" && sh "$CHECK" --staged-ok >/dev/null 2>&1); then
  ok "--staged-ok tolerates a staged change"
else
  bad "--staged-ok did not tolerate a staged change"
fi

# 5. committed -> clean again (positive control after the cycle)
git commit -qm second
if (cd "$SANDBOX" && sh "$CHECK" >/dev/null 2>&1); then
  ok "after committing, the tree matches HEAD again"
else
  bad "a committed tree was still reported as a mismatch"
fi

echo
echo "=== SUMMARY: $PASS passed, $FAIL failed ==="
[ "$FAIL" -eq 0 ] || exit 1
