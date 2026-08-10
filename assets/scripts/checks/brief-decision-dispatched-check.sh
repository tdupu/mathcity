#!/bin/sh
# Idempotency check for brief-decision-dispatch.
#
# Verifies that every pending slug has been appended to the dispatch ledger
# ($HOME/.gc/mathcity/briefs/decisions-dispatched.jsonl). Used as the step check for
# the dispatch-decisions step — ensures the dispatched record is durable
# before the step completes, and prevents re-dispatch of the same slug.
#
# exit 0  -> every processed slug has a SUCCESS line in the ledger
# exit 1  -> one or more processed slugs lack a success line (retry)
#
# A SUCCESS line carries "dispatched_at". This includes both normal success
# lines and TERMINAL "undispatchable" lines (action=undispatchable) — both
# carry "dispatched_at" so the slug is treated as settled. A failed-dispatch
# diagnostic line carries "pending_retry":true and NO "dispatched_at" (C3c):
# it must NOT satisfy this check, so the failed slug is retried on the next
# wake (up to the 3-retry limit enforced by the dispatch step itself).
#
# Inputs (env):
#   BRIEF_ROOT            brief pipeline artifact root (default: $HOME/.gc/mathcity/briefs)
#   PENDING_SLUGS         space-separated list of slugs that were dispatched
#                         (set by scan-undispatched step); if empty, exit 0
set -eu

ROOT="${BRIEF_ROOT:-$HOME/.gc/mathcity/briefs}"
LEDGER="$ROOT/decisions-dispatched.jsonl"
PENDING="${PENDING_SLUGS:-}"

fail() {
  echo "brief-decision-dispatched-check: $*" >&2
  exit 1
}

# If no slugs were pending, nothing to verify.
if [ -z "$(echo "$PENDING" | tr -d ' ')" ]; then
  echo "no pending slugs; dispatch check passes vacuously"
  exit 0
fi

# The ledger must exist once dispatch has run.
[ -f "$LEDGER" ] || fail "missing dispatch ledger: $LEDGER"

# Each pending slug must have a SUCCESS line (one carrying "dispatched_at").
# A lone pending_retry diagnostic line does not count.
missing=""
for slug in $PENDING; do
  if ! grep "\"brief_slug\":[[:space:]]*\"$slug\"" "$LEDGER" 2>/dev/null \
       | grep -q '"dispatched_at"'; then
    missing="$missing $slug"
  fi
done

if [ -n "$(echo "$missing" | tr -d ' ')" ]; then
  fail "slugs not successfully dispatched (no success line): $missing"
fi

echo "brief-decision-dispatched-check: all pending slugs have a success line in $LEDGER"
exit 0
