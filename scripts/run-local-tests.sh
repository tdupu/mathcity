#!/usr/bin/env bash
# Run the local mathcity test suite without relying on filename-specific loops.
set -uo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/run-local-tests.sh [--list] [TEST_ROOT_OR_FILE ...]

Runs every shell test under tests/ plus pytest files under tests/.
Default root: tests

Discovery rules:
  shell:  every *.sh file under the selected roots
  pytest: every test_*.py or *_test.py file under the selected roots

The runner exits nonzero if any discovered test fails.
EOF
}

LIST_ONLY=0
ROOTS=()
while [ "$#" -gt 0 ]; do
  case "$1" in
    --list)
      LIST_ONLY=1
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      while [ "$#" -gt 0 ]; do
        ROOTS+=("$1")
        shift
      done
      break
      ;;
    -*)
      echo "unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      ROOTS+=("$1")
      ;;
  esac
  shift
done

if [ "${#ROOTS[@]}" -eq 0 ]; then
  ROOTS=(tests)
fi

PYTHON_BIN="${PYTHON:-python3}"
TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/mathcity-local-tests.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT
SHELL_LIST="$TMP_DIR/shell-tests.txt"
PYTEST_LIST="$TMP_DIR/pytest-tests.txt"
: >"$SHELL_LIST"
: >"$PYTEST_LIST"

for root in "${ROOTS[@]}"; do
  if [ -d "$root" ]; then
    find "$root" -type f -name '*.sh' >>"$SHELL_LIST"
    find "$root" -type f \( -name 'test_*.py' -o -name '*_test.py' \) >>"$PYTEST_LIST"
  elif [ -f "$root" ]; then
    case "$root" in
      *.sh)
        printf '%s\n' "$root" >>"$SHELL_LIST"
        ;;
      *.py)
        base="$(basename "$root")"
        case "$base" in
          test_*.py|*_test.py) printf '%s\n' "$root" >>"$PYTEST_LIST" ;;
        esac
        ;;
    esac
  else
    echo "missing test root or file: $root" >&2
    exit 2
  fi
done

sort -u "$SHELL_LIST" -o "$SHELL_LIST"
sort -u "$PYTEST_LIST" -o "$PYTEST_LIST"

shell_total="$(grep -c . "$SHELL_LIST" || true)"
pytest_total="$(grep -c . "$PYTEST_LIST" || true)"

if [ "$LIST_ONLY" -eq 1 ]; then
  echo "shell tests ($shell_total):"
  sed 's/^/  /' "$SHELL_LIST"
  echo
  echo "pytest files ($pytest_total):"
  sed 's/^/  /' "$PYTEST_LIST"
  exit 0
fi

if [ "$shell_total" -eq 0 ] && [ "$pytest_total" -eq 0 ]; then
  echo "no tests discovered under: ${ROOTS[*]}" >&2
  exit 1
fi

shell_pass=0
shell_fail=0
# The NAMES, not just the count. A summary that reports "1 fail" and
# discards which one sends the reader back through every test to recover
# something this loop already knew.
shell_failed_names=()

while IFS= read -r script; do
  [ -n "$script" ] || continue
  echo
  echo "================================================================"
  echo "shell: $script"
  echo "================================================================"
  if bash "$script" </dev/null; then
    shell_pass=$((shell_pass + 1))
  else
    shell_fail=$((shell_fail + 1))
    shell_failed_names+=("$script")
  fi
done <"$SHELL_LIST"

pytest_pass=0
pytest_fail=0
if [ "$pytest_total" -gt 0 ]; then
  pytest_args=()
  while IFS= read -r test_file; do
    [ -n "$test_file" ] || continue
    pytest_args+=("$test_file")
  done <"$PYTEST_LIST"

  echo
  echo "================================================================"
  echo "pytest: $pytest_total file(s)"
  echo "================================================================"
  # tee, so the run still streams live AND the summary can name what failed.
  # pipefail is set above, so the `if` still sees pytest's status, not tee's.
  PYTEST_OUTPUT="$TMP_DIR/pytest-output.txt"
  if "$PYTHON_BIN" -m pytest "${pytest_args[@]}" 2>&1 | tee "$PYTEST_OUTPUT"; then
    pytest_pass=1
  else
    pytest_fail=1
  fi
fi

echo
echo "================================================================"
echo "mathcity local test summary"
echo "shell:  $shell_pass pass / $shell_fail fail (of $((shell_pass + shell_fail)))"
if [ "$shell_fail" -gt 0 ]; then
  for failed_script in "${shell_failed_names[@]}"; do
    echo "  FAILED  $failed_script"
  done
fi
if [ "$pytest_total" -gt 0 ]; then
  if [ "$pytest_fail" -gt 0 ]; then
    echo "pytest: FAIL ($pytest_total file(s))"
    # pytest already names every failure; the summary used to throw that away.
    if [ -f "${PYTEST_OUTPUT:-}" ]; then
      grep -E '^(FAILED|ERROR) ' "$PYTEST_OUTPUT" | sed 's/^/  /' || true
    fi
  else
    echo "pytest: PASS ($pytest_total file(s))"
  fi
else
  echo "pytest: SKIP (0 file(s))"
fi
echo "================================================================"

if [ "$shell_fail" -gt 0 ] || [ "$pytest_fail" -gt 0 ]; then
  exit 1
fi
