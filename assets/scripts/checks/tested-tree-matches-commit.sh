#!/bin/sh
# tested-tree-matches-commit.sh — does the tree you TESTED match the tree you SHIP?
#
# THE DEFECT (#200, measured on #190 at d0ce2b0): an author edited a file to fix
# a failing test, ran the suite (GREEN), committed, and shipped a SHA that did
# not contain the fix -- it was never staged. The reviewer ran the same suite at
# the SHA and got 1 FAILED. Every check passed on something that is not what
# shipped: the suite was genuinely green, the reviewer genuinely careful, and
# the artifact still wrong.
#
# Nothing compared the two trees. This does.
#
# It is a REPORT about what a test run described, so it names every file that
# differs rather than only the count -- "your suite result does not describe
# HEAD" is unactionable without the list.
#
# Usage:  tested-tree-matches-commit.sh [--staged-ok]
#   default      any difference between the WORKING TREE and HEAD is reported
#   --staged-ok  staged-but-uncommitted changes are tolerated (mid-commit use)
set -eu

MODE="${1:-}"

if ! git rev-parse --git-dir >/dev/null 2>&1; then
  echo "I'm sorry, I can't do that -- this is not a git repository." >&2
  echo "The check compares your working tree against HEAD; there is no HEAD here." >&2
  exit 1
fi

if ! git rev-parse --verify HEAD >/dev/null 2>&1; then
  echo "TESTED_TREE: no HEAD yet (unborn branch); nothing to compare against."
  exit 0
fi

# Tracked files whose content differs from HEAD. Untracked files are NOT
# included: a new file that is not committed cannot have been imported by a
# committed test, so it cannot silently change a suite result the way an edited
# tracked file can. Listing them would make this noisy on every scratch file and
# train people to ignore it.
if [ "$MODE" = "--staged-ok" ]; then
  DIFFERING=$(git diff --name-only 2>/dev/null || true)
  SCOPE="unstaged changes"
else
  DIFFERING=$(git diff --name-only HEAD 2>/dev/null || true)
  SCOPE="differences from HEAD (staged or not)"
fi

if [ -z "$DIFFERING" ]; then
  echo "TESTED_TREE: OK -- the working tree matches HEAD, so a suite run here describes what ships."
  exit 0
fi

COUNT=$(printf '%s\n' "$DIFFERING" | grep -c . || true)

echo "TESTED_TREE: MISMATCH -- $COUNT file(s) differ from HEAD ($SCOPE)." >&2
echo >&2
echo "A suite run in this tree does NOT describe the commit you are about to ship." >&2
echo "That is #200: green locally, red at the SHA, because the change was never staged." >&2
echo >&2
printf '%s\n' "$DIFFERING" | sed 's/^/    /' >&2
echo >&2
echo "Either commit these, or re-run the suite against HEAD:" >&2
echo "    git stash --include-untracked && <run suite> ; git stash pop" >&2
exit 1
