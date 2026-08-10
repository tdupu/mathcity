#!/bin/bash
# test-9: re-running on a body that already contains the AI footer marker must
# NOT inject a second footer. This guards against stacked re-injection when
# the skill is invoked twice in a row (the second invocation's input is the
# first invocation's output).

source "$(dirname "${BASH_SOURCE[0]}")/lib.sh"
test_setup "test-9: footer injection is idempotent across re-runs"

export MOCK_GH_OLD_BODY="old body"
unset MOCK_GH_EXISTING_ARCHIVE
unset MOCK_GH_LABEL_EXISTS

NEW_BODY=$(mktemp)
cat > "$NEW_BODY" <<'EOF'
existing canonical body that already has a footer

---

<sub><!-- ai-assisted-footer -->**AI-assisted.** Earlier-injected footer content from a prior run. Should NOT be duplicated.</sub>
EOF

bash "$SCRIPT" 777 --body-file "$NEW_BODY" --reason "re-run" --repo example-owner/agent-skills
EXIT=$?

assert_exit 0 "$EXIT" "script exits 0"

# Body sent to gh must contain exactly ONE footer marker.
BODIES_LOG="${MOCK_GH_LOG}.bodies"
if [ -f "$BODIES_LOG" ]; then
  # Restrict to the gh issue edit call's body file (the script edits
  # NEW_BODY in place, so the sidecar captures the post-injection state).
  MARKER_COUNT=$(grep -c "<!-- ai-assisted-footer -->" "$BODIES_LOG" 2>/dev/null || echo 0)
  if [ "$MARKER_COUNT" -eq 1 ]; then
    echo "PASS: exactly one AI footer marker in submitted body (idempotent)"
    PASS_COUNT=$((PASS_COUNT+1))
  else
    echo "FAIL: expected 1 AI footer marker, found $MARKER_COUNT"
    FAIL_COUNT=$((FAIL_COUNT+1))
  fi
else
  echo "FAIL: no body-file sidecar log produced"
  FAIL_COUNT=$((FAIL_COUNT+1))
fi

# Label should still be applied (idempotent at GitHub layer).
assert_log_contains "gh issue edit 777 --repo example-owner/agent-skills --add-label ai-assisted" "label still applied on re-run"

rm -f "$NEW_BODY"
test_teardown
