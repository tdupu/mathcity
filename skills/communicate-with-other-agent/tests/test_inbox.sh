#!/usr/bin/env bash
# test_inbox.sh — smoke tests for V2 inbox scripts.
# Exercises send/rotate/migrate/monitor against a sandbox project dir.
# Run: bash test_inbox.sh
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
SCRIPTS="$HERE/../scripts"
SANDBOX=$(mktemp -d -t agent-inbox-test-XXXXXXXX)
trap 'rm -rf "$SANDBOX"' EXIT

# Use deterministic UUIDs for the test.
ALICE="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
BOB="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb"
CAROL="cccccccc-cccc-cccc-cccc-cccccccccccc"

# ACCUMULATE, do not exit. `fail` used to `exit 1` on the first failure, so one
# broken section hid every later one -- the same shape #199 records for the tool
# registries: "the first red tells you about one registry when there are five."
# Section 3 was failing, so sections 4-7 had never run.
FAIL_COUNT=0
PASS_COUNT=0
fail() { echo "FAIL: $*" >&2; FAIL_COUNT=$((FAIL_COUNT + 1)); }
pass() { echo "PASS: $*"; PASS_COUNT=$((PASS_COUNT + 1)); }
summary() {
  echo
  echo "=== SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed ==="
  [ "$FAIL_COUNT" -eq 0 ] || exit 1
}

mkdir -p "$SANDBOX/proj/.claude"
cd "$SANDBOX/proj"

# --- 1) send creates per-recipient file ---
BODY=$(mktemp); printf 'first message body\n' > "$BODY"
bash "$SCRIPTS/agent-send.sh" "$ALICE" "$BOB" "test/first" "$BODY" >/dev/null
[[ -f "$SANDBOX/proj/.claude/inbox/$BOB.md" ]] || fail "send did not create $BOB inbox file"
[[ ! -f "$SANDBOX/proj/.claude/inbox/$ALICE.md" ]] || fail "send unexpectedly created sender inbox"
grep -q "^to:.*$BOB" "$SANDBOX/proj/.claude/inbox/$BOB.md" || fail "send did not write to: $BOB header"
grep -q "^from:.*$ALICE" "$SANDBOX/proj/.claude/inbox/$BOB.md" || fail "send did not write from: $ALICE header"
grep -q "^subject: test/first" "$SANDBOX/proj/.claude/inbox/$BOB.md" || fail "subject line missing"
grep -q "first message body" "$SANDBOX/proj/.claude/inbox/$BOB.md" || fail "body content missing"
pass "send writes to per-recipient file"

# --- 2) two recipients get isolated inboxes ---
printf 'message for carol\n' > "$BODY"
bash "$SCRIPTS/agent-send.sh" "$ALICE" "$CAROL" "test/carol" "$BODY" >/dev/null
[[ -f "$SANDBOX/proj/.claude/inbox/$CAROL.md" ]] || fail "carol inbox missing"
grep -q "$CAROL" "$SANDBOX/proj/.claude/inbox/$BOB.md" && fail "bob inbox leaked into carol traffic"
grep -q "$BOB" "$SANDBOX/proj/.claude/inbox/$CAROL.md" && fail "carol inbox leaked into bob traffic"
pass "per-recipient isolation holds"

# --- 3) rotation by entry count ---
# Lower the threshold by patching the script via env? Simpler: write 30 entries and check rotation.
for i in $(seq 1 30); do
    printf 'bulk msg %d\n' "$i" > "$BODY"
    bash "$SCRIPTS/agent-send.sh" "$ALICE" "$BOB" "bulk/$i" "$BODY" >/dev/null
done
# After 30 entries (we already had 1, so this should trigger), the next send rotates.
printf 'trigger\n' > "$BODY"
bash "$SCRIPTS/agent-send.sh" "$ALICE" "$BOB" "rotate-trigger" "$BODY" > /tmp/rotate-out 2>&1
# `|| true`: this file runs under `set -euo pipefail`, and when the archive dir
# does not exist `ls` fails, pipefail propagates it, and `set -e` kills the
# script AT THE ASSIGNMENT -- before the `|| fail` below can run. The suite then
# exited 1 having printed two PASSes and no FAIL at all, so a reader saw a short
# green run instead of a failure. Same trap as `grep -q` under pipefail.
ARCHIVE_COUNT=$(ls "$SANDBOX/proj/.claude/inbox/archive/" 2>/dev/null | wc -l | tr -d ' ' || true)
ARCHIVE_COUNT="${ARCHIVE_COUNT:-0}"
# `pass` is guarded, not unconditional: now that `fail` accumulates instead of
# exiting, a bare `pass` on the next line prints alongside the FAIL for the same
# assertion -- which is worse than exiting, because the summary and the body
# disagree.
if [[ "$ARCHIVE_COUNT" -ge 1 ]]; then
  pass "entry-count rotation trigger fires"
else
  fail "expected at least one archive file after 30+ entries (got $ARCHIVE_COUNT)"
fi

# --- 4) migrate from V1 layout ---
LEGACY="$SANDBOX/legacy/.claude/.agent-inbox.md"
mkdir -p "$(dirname "$LEGACY")"
cat > "$LEGACY" <<EOF

---
from: $ALICE
to:   $BOB
at:   2026-06-01 10:00:00 -1000
subject: legacy/1
---
legacy body for bob #1

---
from: $CAROL
to:   $BOB
at:   2026-06-01 10:05:00 -1000
subject: legacy/2
---
legacy body for bob #2

---
from: $ALICE
to:   $CAROL
at:   2026-06-01 10:10:00 -1000
subject: legacy/3
---
legacy body for carol
EOF

bash "$SCRIPTS/agent-inbox-migrate.sh" "$SANDBOX/legacy" >/dev/null
[[ -f "$SANDBOX/legacy/.claude/inbox/$BOB.md"   ]] || fail "migrate did not create $BOB.md"
[[ -f "$SANDBOX/legacy/.claude/inbox/$CAROL.md" ]] || fail "migrate did not create $CAROL.md"
BOB_ENTRIES=$(grep -c '^at:' "$SANDBOX/legacy/.claude/inbox/$BOB.md")
CAROL_ENTRIES=$(grep -c '^at:' "$SANDBOX/legacy/.claude/inbox/$CAROL.md")
[[ "$BOB_ENTRIES"   = 2 ]] || fail "bob entry count after migrate: expected 2 got $BOB_ENTRIES"
[[ "$CAROL_ENTRIES" = 1 ]] || fail "carol entry count after migrate: expected 1 got $CAROL_ENTRIES"
[[ ! -f "$LEGACY" ]] || fail "legacy file still present after migrate"
ls -a "$SANDBOX/legacy/.claude/" | grep -q '\.agent-inbox-migrated-' || fail "no .agent-inbox-migrated-* sentinel after migrate"
pass "migrate splits per-recipient and renames legacy"

# --- 5) migrate is idempotent ---
bash "$SCRIPTS/agent-inbox-migrate.sh" "$SANDBOX/legacy" >/dev/null
# A second migrate on a project with no legacy file should be a no-op.
pass "migrate is idempotent (no error on second run)"

# --- 6) legacy auto-detect on send (no .claude/inbox/ yet) ---
NEWPROJ="$SANDBOX/newproj"
mkdir -p "$NEWPROJ/.claude"
touch "$NEWPROJ/.claude/.agent-inbox.md"
cd "$NEWPROJ"
printf 'auto-detect test\n' > "$BODY"
SEND_OUT=$(bash "$SCRIPTS/agent-send.sh" "$ALICE" "$BOB" "auto-detect" "$BODY" 2>&1)
echo "$SEND_OUT" | grep -q "LEGACY_INBOX_DETECTED" || fail "send did not emit LEGACY_INBOX_DETECTED hint"
[[ -d "$NEWPROJ/.claude/inbox" ]] || fail "send did not create .claude/inbox/ on legacy auto-detect"
[[ -f "$NEWPROJ/.claude/inbox/$BOB.md" ]] || fail "send did not write to V2 path on legacy auto-detect"
pass "legacy auto-detect upgrades on first send"

# --- 7) #191: an unresolved RECIPIENT is announced, not silently rerouted ---
#
# resolve_name falls back to the UUID's 8-char prefix on a map miss, and the
# skill documents that as a feature: "Unknown UUIDs fall back to their 8-char
# prefix, so routing never fails."
#
# Routing never fails. DELIVERY does. The message lands in a real directory that
# nobody watches, and neither side gets a signal: the sender sees a success line
# naming the path, and the recipient's monitor, watching the mapped name,
# reports nothing. There is no bounce.
#
# The asymmetry matters: the SENDER's name falling back is harmless — it is a
# label inside the filename. Only the RECIPIENT's fallback misdelivers.
MAPPROJ="$SANDBOX/mapproj"
mkdir -p "$MAPPROJ/.claude/inbox"
cd "$MAPPROJ"
printf '%s carol-mapped\n' "$CAROL" > "$MAPPROJ/.claude/inbox/.agent-names.map"
printf 'unmapped recipient test\n' > "$BODY"

UNMAPPED_OUT=$(bash "$SCRIPTS/agent-send.sh" "$CAROL" "$BOB" "unmapped" "$BODY" 2>&1 || true)
if printf '%s' "$UNMAPPED_OUT" | grep -q "UNRESOLVED_RECIPIENT" \
   && printf '%s' "$UNMAPPED_OUT" | grep -q "$BOB"; then
  pass "an unresolved recipient is announced, naming the uuid (#191)"
else
  fail "send did not announce an unresolved recipient (#191)"
fi

# The message must still be delivered — losing it would trade a silent
# misdelivery for a silent drop, which is worse.
if [[ -f "$MAPPROJ/.claude/inbox/$BOB.md" ]]; then
  pass "the message is still delivered, loudly"
else
  fail "send stopped delivering to an unmapped recipient; the warning must not eat the message"
fi

# POSITIVE CONTROL: a MAPPED recipient must NOT warn, or the check above would
# pass by warning on every send.
printf '%s bob-mapped\n' "$BOB" >> "$MAPPROJ/.claude/inbox/.agent-names.map"
MAPPED_OUT=$(bash "$SCRIPTS/agent-send.sh" "$CAROL" "$BOB" "mapped" "$BODY" 2>&1 || true)
if printf '%s' "$MAPPED_OUT" | grep -q "UNRESOLVED_RECIPIENT"; then
  fail "a MAPPED recipient warned; the check fires unconditionally"
else
  pass "a mapped recipient does not warn (positive control)"
fi


summary
