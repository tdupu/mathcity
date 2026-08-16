#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
RUNNER="$ROOT/scripts/run-local-tests.sh"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/mathcity-runner-self-test.XXXXXX")"
PASS_TMP="$(mktemp -d "${TMPDIR:-/tmp}/mathcity-runner-self-test-pass.XXXXXX")"
trap 'rm -rf "$TMP" "$PASS_TMP"' EXIT

mkdir -p "$TMP/pass" "$TMP/fail" "$TMP/custom" "$TMP/stdin" "$TMP/zzz"

cat >"$TMP/pass/smoke_test.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH

cat >"$TMP/custom/test_custom.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH

cat >"$TMP/stdin/read_stdin_test.sh" <<'SH'
#!/usr/bin/env bash
set -eu
# This must see EOF. If the runner leaves the discovery list on stdin, this
# read can consume the next test path and silently shrink the suite.
if IFS= read -r line; then
  echo "child test unexpectedly read from runner stdin: $line" >&2
  exit 9
fi
exit 0
SH

cat >"$TMP/zzz/after_stdin_test.sh" <<SH
#!/usr/bin/env bash
set -eu
printf 'after-stdin-ran\n' >"$TMP/after-stdin.marker"
exit 0
SH

cat >"$TMP/fail/red_test.sh" <<'SH'
#!/usr/bin/env bash
exit 7
SH

status=0
output="$(bash "$RUNNER" "$TMP" 2>&1)" || status=$?
if [ "$status" -eq 0 ]; then
  echo "runner self-test failed: failing child test produced exit 0" >&2
  printf '%s\n' "$output" >&2
  exit 1
fi
grep -Fq "$TMP/fail/red_test.sh" <<<"$output" || {
  echo "runner self-test failed: red_test.sh was not discovered" >&2
  printf '%s\n' "$output" >&2
  exit 1
}
grep -Fq "$TMP/zzz/after_stdin_test.sh" <<<"$output" || {
  echo "runner self-test failed: test after stdin reader was not discovered/run" >&2
  printf '%s\n' "$output" >&2
  exit 1
}
test -f "$TMP/after-stdin.marker" || {
  echo "runner self-test failed: after-stdin marker was not written" >&2
  printf '%s\n' "$output" >&2
  exit 1
}
grep -Fq "shell:  4 pass / 1 fail (of 5)" <<<"$output" || {
  echo "runner self-test failed: summary did not preserve child failure" >&2
  printf '%s\n' "$output" >&2
  exit 1
}

mkdir -p "$PASS_TMP/only"
cat >"$PASS_TMP/only/smoke_test.sh" <<'SH'
#!/usr/bin/env bash
exit 0
SH

bash "$RUNNER" "$PASS_TMP" >/dev/null
echo "test runner failure propagation: ok"
