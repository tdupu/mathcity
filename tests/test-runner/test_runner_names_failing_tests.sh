#!/usr/bin/env bash
# The runner's SUMMARY must name what failed. A count is not a summary.
#
# THE DEFECT
# ----------
# `run-local-tests.sh` reported `shell: 40 pass / 1 fail (of 41)` and
# `pytest: FAIL (70 file(s))` and nothing else. Twice in one evening an agent had
# to run all 41 shell tests individually, or re-run the whole pytest suite, to
# answer "which one?" -- a question the runner already knew the answer to and
# discarded.
#
# It is the sibling of the exit-code question. The exit code is honest and
# unread; the summary is read and uninformative. Between them, the instrument the
# team uses to decide whether it is safe to merge tells you that something is
# wrong and gives you no way to act on it.
#
# HOW THESE TESTS COULD HAVE FAILED (P6.2)
# ----------------------------------------
# The tempting wrong version asserts the failing name appears ANYWHERE in the
# output. That passes today and always would: the runner echoes `shell: <script>`
# before running each one, so every name is already in the log -- which is
# precisely why the information was useless. These tests therefore assert against
# the SUMMARY BLOCK ONLY, sliced after the `mathcity local test summary` banner.
#
# And each has a control in the opposite direction: the summary must NOT name the
# test that passed. A fix that dumped every script name into the summary would
# satisfy "names the failure" while restoring the original problem, so the
# passing-name assertion is what makes the failing-name assertion mean something.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$HERE/../.." && pwd)"
RUNNER="$ROOT/scripts/run-local-tests.sh"

PASS_COUNT=0
FAIL_COUNT=0
ok() { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
no() { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

#: Everything after the summary banner. The banner is the contract: before it is
#: a log, after it is the thing a human reads to decide.
summary_of() {
  awk '/mathcity local test summary/{found=1} found' "$1"
}

# --- shell ------------------------------------------------------------------
SBX="$(mktemp -d)"
mkdir -p "$SBX/tests/zz-runner-probe"
printf '#!/bin/sh\necho "this one fails on purpose"\nexit 1\n' \
  > "$SBX/tests/zz-runner-probe/failing_probe_test.sh"
printf '#!/bin/sh\necho "this one passes"\nexit 0\n' \
  > "$SBX/tests/zz-runner-probe/passing_probe_test.sh"
chmod +x "$SBX/tests/zz-runner-probe/"*.sh

# Run the real runner against the probe dir, from the repo so it resolves.
( cd "$ROOT" && bash "$RUNNER" "$SBX/tests/zz-runner-probe" ) > "$SBX/out.txt" 2>&1
RC=$?
summary_of "$SBX/out.txt" > "$SBX/summary.txt"

if [ "$RC" -ne 0 ]; then
  ok "CONTROL: the runner still exits non-zero when a shell test fails"
else
  no "CONTROL: runner exited 0 with a failing shell test; the fixture is not exercising a failure"
fi

if grep -q 'failing_probe_test' "$SBX/summary.txt"; then
  ok "the summary NAMES the failing shell test"
else
  no "the summary does not name the failing shell test -- it reported a count and discarded the name"
  echo "    --- summary block ---"; sed 's/^/    /' "$SBX/summary.txt"
fi

if grep -q 'passing_probe_test' "$SBX/summary.txt"; then
  no "the summary names the PASSING test too -- naming everything is the same as naming nothing"
else
  ok "CONTROL: the summary does not name the passing shell test"
fi

rm -rf "$SBX"

# --- pytest -----------------------------------------------------------------
PBX="$(mktemp -d)"
mkdir -p "$PBX/tests/zz-runner-pyprobe"
cat > "$PBX/tests/zz-runner-pyprobe/test_probe.py" <<'PY'
def test_probe_that_passes():
    assert True


def test_probe_that_fails():
    assert False, "fails on purpose"
PY

( cd "$ROOT" && bash "$RUNNER" "$PBX/tests/zz-runner-pyprobe" ) > "$PBX/out.txt" 2>&1
summary_of "$PBX/out.txt" > "$PBX/summary.txt"

if grep -q 'test_probe_that_fails' "$PBX/summary.txt"; then
  ok "the summary NAMES the failing pytest test"
else
  no "the summary does not name the failing pytest test -- 'pytest: FAIL (N file(s))' is not actionable"
  echo "    --- summary block ---"; sed 's/^/    /' "$PBX/summary.txt"
fi

if grep -q 'test_probe_that_passes' "$PBX/summary.txt"; then
  no "the summary names the PASSING pytest test too"
else
  ok "CONTROL: the summary does not name the passing pytest test"
fi

rm -rf "$PBX"

echo
echo "runner-names-failing-tests: $PASS_COUNT passed, $FAIL_COUNT failed"
[ "$FAIL_COUNT" -eq 0 ]
