#!/usr/bin/env bash
# The summary must report what pytest DID, not what pytest was GIVEN.
#
# THE DEFECT
# ----------
# `pytest_total="$(grep -c . "$PYTEST_LIST")"` counts the files handed to pytest.
# It was printed as `pytest: PASS (81 file(s))` -- identically whether those files
# passed or not. Sitting next to PASS it reads as a coverage result, and it was
# cited that way in merge commits, issue comments and hourly status reports for a
# day before anyone noticed it could not vary with the outcome.
#
# It is the same family as the count-without-names this suite's sibling covers,
# one level meaner: that summary withheld information it had, this one presented
# an INPUT in the grammatical position of a RESULT.
#
# HOW THIS COULD FAIL (P6.2)
# --------------------------
# The lazy version asserts "1 failed" appears somewhere in the output. pytest
# prints its own tally to stdout, so that passes without the summary being fixed
# at all -- the runner streams pytest's output verbatim. So every assertion here
# slices the SUMMARY BLOCK ONLY, after the banner, exactly as the sibling test
# does and for the same reason.
#
# The control asserts the file count is still present AND labelled `collected`.
# Deleting the input number would also make "the summary does not misreport" true,
# and would lose information a reader wants; the requirement is that it be
# labelled, not that it be removed.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
RUNNER="$ROOT/scripts/run-local-tests.sh"

PASS_COUNT=0
FAIL_COUNT=0
ok() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
no() { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

summary_of() { awk '/mathcity local test summary/{found=1} found' "$1"; }

BX="$(mktemp -d)"
mkdir -p "$BX/tests/zz-outcome-probe"
cat > "$BX/tests/zz-outcome-probe/test_outcome.py" <<'PY'
def test_one_that_passes():
    assert True


def test_one_that_fails():
    assert False, "on purpose"
PY

( cd "$ROOT" && bash "$RUNNER" "$BX/tests/zz-outcome-probe" ) > "$BX/out.txt" 2>&1
summary_of "$BX/out.txt" > "$BX/summary.txt"

# ONE file, TWO tests: so the file count (1) and the outcome (1 failed, 1 passed)
# are different numbers. If the summary reported the input, it would say "1".
if grep -qE '1 failed' "$BX/summary.txt" && grep -qE '1 passed' "$BX/summary.txt"; then
  ok "the summary reports pytest's own tally (1 failed, 1 passed)"
else
  no "the summary does not report pytest's tally -- it reported the input count"
  echo "    --- summary block ---"; sed 's/^/    /' "$BX/summary.txt"
fi

if grep -qE 'collected' "$BX/summary.txt"; then
  ok "CONTROL: the file count is retained and labelled as collected, not as a result"
else
  no "CONTROL: the input file count is unlabelled -- a reader cannot tell input from outcome"
  echo "    --- summary block ---"; sed 's/^/    /' "$BX/summary.txt"
fi

rm -rf "$BX"

# An unknown outcome must not borrow the shape of a known one.
if grep -q 'outcome not reported by pytest' "$RUNNER"; then
  ok "CONTROL: an unparseable pytest tail reports unknown rather than inventing a tally"
else
  no "no fallback: if pytest's tail cannot be parsed the summary would print an empty outcome"
fi

echo
echo "runner-reports-results-not-inputs: $PASS_COUNT passed, $FAIL_COUNT failed"
[ "$FAIL_COUNT" -eq 0 ]
