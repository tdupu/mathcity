#!/usr/bin/env bash
# Dead-path detector (tdupu/mathcity#71) -- validated against the known-bad corpus.
#
# The detector's entire justification is that its prototype found two live bugs
# nobody had reported (#73), and #73 turned out to be the fifth instance of the
# most common root cause in this system. So the acceptance criterion is not
# "runs green"; it is "finds the four defects we already know about". If it
# cannot find those, it is not ready.
#
# The corpus is built here from literals rather than read from git, for two
# reasons: the fixed files no longer contain the bad strings (so the live tree
# cannot serve as a corpus), and a pinned literal survives history rewrites and
# shallow clones in a way `git show <sha>^:<path>` does not. Each literal below
# carries its provenance.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RIG_ROOT="$(cd "$HERE/../.." && pwd)"
CHECK="$RIG_ROOT/assets/scripts/checks/deadpath-check.py"
TMP="$(mktemp -d "${TMPDIR:-/tmp}/deadpath-detector.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

PASS_COUNT=0
FAIL_COUNT=0
ok()  { echo "PASS: $1"; PASS_COUNT=$((PASS_COUNT + 1)); }
no()  { echo "FAIL: $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

test -x "$CHECK" || { echo "FAIL: $CHECK is not executable"; exit 1; }

# --------------------------------------------------------------------------
# The known-bad corpus.
# --------------------------------------------------------------------------
CORPUS="$TMP/corpus"
mkdir -p "$CORPUS/formulas" "$CORPUS/assets/scripts/checks"

# Defect 1 of #73 -- formulas/brief-record-decision.toml:209 as of 2adc84b^.
# $PACK_DIR is not injected into a formula step, so this expanded to
# python3 "/assets/scripts/brief-stack-index.py" and failed.  (R2)
cat >"$CORPUS/formulas/brief-record-decision.toml" <<'EOF'
description = """
Run the stack-index helper in apply mode after the archive move succeeds:

```bash
python3 "$PACK_DIR/assets/scripts/brief-stack-index.py" remove-archived-row \
  --brief-root "{{artifact_root}}" \
  --slug "{{brief_slug}}" \
  --apply
```
"""
EOF

# Defect 2 of #73 -- formulas/brief-shuffle-fast-drain.toml:36 and :38 as of
# 2adc84b^. Bare assets/ in a runnable block; the ralph runner's cwd is an
# agent work dir, never the pack root.  (R5, twice)
cat >"$CORPUS/formulas/brief-shuffle-fast-drain.toml" <<'EOF'
description = """
Run this deterministic command exactly once:

```bash
python3 assets/scripts/brief-shuffle-fast-drain.py \
  --brief-root {{artifact_root}} \
  --gate-config assets/brief-pipeline/gates.toml \
  --max-items {{max_items}} \
  --apply --json --no-external
```
"""
EOF

# The two brief-check.sh literals fixed in 310b15a -- lines 387 and 495 of the
# pre-fix file, both replaced by $(pack_asset ...).  (R5, twice)
cat >"$CORPUS/assets/scripts/checks/brief-check.sh" <<'EOF'
#!/bin/sh
check_stack_index_path() {
  configured="assets/brief-pipeline/paths.toml"
}
check_no_brainer_classification_evidence() {
  registry="assets/brief-pipeline/no-brainer-categories.toml"
}
EOF

echo "=== 1. the known-bad corpus: all four defects are found ==="
CORPUS_OUT="$TMP/corpus.txt"
set +e
python3 "$CHECK" --root "$CORPUS" --strict-advisory >"$CORPUS_OUT" 2>&1
corpus_status=$?
set -e

expect_hit() {
  # expect_hit <rule> <path-fragment> <label>
  if grep -Eq "^(FAIL|warn): $1 .*$2" "$CORPUS_OUT"; then
    ok "$3"
  else
    no "$3 -- no $1 hit for $2"
  fi
}
expect_hit "R2" 'brief-record-decision\.toml' \
  '#73 defect 1: $PACK_DIR in a formula step (brief-record-decision.toml:209)'
expect_hit "R5" 'brief-shuffle-fast-drain\.toml' \
  '#73 defect 2: bare assets/ in a runnable block (brief-shuffle-fast-drain.toml:36,38)'
expect_hit "R5" 'brief-check\.sh' \
  '310b15a: cwd-relative pack-asset literals in brief-check.sh (:387,:495)'

# Both brief-shuffle lines, and both brief-check lines, not just one of each.
shuffle_hits="$(grep -Ec "R5 formulas/brief-shuffle-fast-drain\.toml" "$CORPUS_OUT" || true)"
[ "$shuffle_hits" -ge 2 ] \
  && ok "both brief-shuffle-fast-drain literals found (script path and --gate-config value)" \
  || no "expected 2 brief-shuffle-fast-drain hits, got $shuffle_hits"
check_hits="$(grep -Ec "R5 assets/scripts/checks/brief-check\.sh" "$CORPUS_OUT" || true)"
[ "$check_hits" -ge 2 ] \
  && ok "both brief-check.sh literals found (paths.toml and no-brainer-categories.toml)" \
  || no "expected 2 brief-check.sh hits, got $check_hits"

[ "$corpus_status" -ne 0 ] \
  && ok "the corpus run exits non-zero" \
  || no "the corpus run exited 0 despite known defects"

echo "=== 2. R5 scoping: fenced/runnable positions only, not the ~55 prose mentions ==="
PROSE="$TMP/prose"
mkdir -p "$PROSE/formulas"
cat >"$PROSE/formulas/prose-only.toml" <<'EOF'
description = """
The canonical pile root is recorded in assets/brief-pipeline/paths.toml, and the
gate config lives beside it at assets/brief-pipeline/gates.toml. See also
assets/scripts/brief-shuffle-fast-drain.py for the drain implementation.
"""
EOF
prose_hits="$(python3 "$CHECK" --root "$PROSE" --strict-advisory 2>&1 | grep -Ec '^(FAIL|warn):' || true)"
[ "$prose_hits" = "0" ] \
  && ok "prose mentions of assets/ are not flagged" \
  || no "R5 flagged $prose_hits prose mention(s); the 57-hit noise problem is back"

echo "=== 3. R2 does not flag order exec values, which are its one legal surface ==="
ORDERS="$TMP/orders-case"
mkdir -p "$ORDERS/orders"
cat >"$ORDERS/orders/legit.toml" <<'EOF'
exec = "python3 $PACK_DIR/assets/scripts/tail-end-detector.py --base-dir ."
EOF
order_hits="$(python3 "$CHECK" --root "$ORDERS" --strict-advisory 2>&1 | grep -Ec '^(FAIL|warn):' || true)"
[ "$order_hits" = "0" ] \
  && ok "\$PACK_DIR in an order exec value is not flagged" \
  || no "R2 flagged $order_hits legitimate order exec value(s)"

echo "=== 4. regression case: a formula referencing a non-existent path fails ==="
MISSING="$TMP/missing"
mkdir -p "$MISSING/formulas"
cat >"$MISSING/formulas/ghost.toml" <<'EOF'
[[steps]]
id = "ghost"
description = """
Run `<mathcity-pack-root>/assets/scripts/there-is-no-such-script.py --apply`.
"""
[steps.check]
path = "../assets/scripts/checks/there-is-no-such-check.sh"
EOF
set +e
MISSING_OUT="$(python3 "$CHECK" --root "$MISSING" 2>&1)"
missing_status=$?
set -e
grep -q "R3" <<<"$MISSING_OUT" \
  && ok "R3 fails a <mathcity-pack-root>/ reference to a file that does not ship" \
  || no "R3 missed a non-existent <mathcity-pack-root>/ path"
grep -q "R4" <<<"$MISSING_OUT" \
  && ok "R4 fails a check declaration pointing at an asset that does not ship" \
  || no "R4 missed a non-existent check path"
[ "$missing_status" -ne 0 ] \
  && ok "a formula referencing a non-existent path fails the check (exit $missing_status)" \
  || no "a formula referencing a non-existent path exited 0"

echo "=== 5. R1 allowlist: gc-beads-bd.sh passes, anything else under .gc/scripts/ fails ==="
GCS="$TMP/gcs"
mkdir -p "$GCS/skills/x"
cat >"$GCS/skills/x/SKILL.md" <<'EOF'
Run `<city-root>/.gc/scripts/gc-beads-bd.sh list` to reach the bead store.
Then run `<city-root>/.gc/scripts/escalate.sh` to file the escalation.
EOF
set +e
GCS_OUT="$(python3 "$CHECK" --root "$GCS" 2>&1)"
gcs_status=$?
set -e
grep -q "escalate.sh" <<<"$GCS_OUT" \
  && ok "R1 flags .gc/scripts/escalate.sh" \
  || no "R1 missed .gc/scripts/escalate.sh"
grep -q "gc-beads-bd.sh list" <<<"$GCS_OUT" \
  && no "R1 flagged the allowlisted gc-beads-bd.sh" \
  || ok "R1 allows gc-beads-bd.sh, the one script gascity generates"
[ "$gcs_status" -ne 0 ] && ok "R1 is blocking" || no "R1 did not block"

echo "=== 6. exemptions require a reason, and are always reported ==="
EX="$TMP/exempt"
mkdir -p "$EX/skills/y"
cat >"$EX/skills/y/SKILL.md" <<'EOF'
<!-- deadpath-ok: documents that the directory is absent -->
No rig carries a `.gc/scripts/checks/` — nothing in gascity installs one.
EOF
set +e
EX_OUT="$(python3 "$CHECK" --root "$EX" 2>&1)"
ex_status=$?
set -e
[ "$ex_status" -eq 0 ] \
  && ok "a reasoned exemption clears the blocking hit" \
  || no "a reasoned exemption did not clear the hit (exit $ex_status)"
grep -q "exemptions in force: 1" <<<"$EX_OUT" \
  && ok "the exemption is printed in the summary, not silently absorbed" \
  || no "the exemption did not appear in the summary"
grep -q "documents that the directory is absent" <<<"$EX_OUT" \
  && ok "the exemption reason is printed" \
  || no "the exemption reason was not printed"

NOREASON="$TMP/noreason"
mkdir -p "$NOREASON/skills/z"
cat >"$NOREASON/skills/z/SKILL.md" <<'EOF'
<!-- deadpath-ok: -->
No rig carries a `.gc/scripts/checks/` directory.
EOF
set +e
python3 "$CHECK" --root "$NOREASON" >/dev/null 2>&1
noreason_status=$?
set -e
[ "$noreason_status" -ne 0 ] \
  && ok "an exemption with no reason is itself an error" \
  || no "an exemption with no reason was accepted"

echo "=== 7. the live pack is green ==="
set +e
LIVE_OUT="$(python3 "$CHECK" --root "$RIG_ROOT" 2>&1)"
live_status=$?
set -e
[ "$live_status" -eq 0 ] \
  && ok "the pack has no blocking dead-path hits" \
  || no "the pack has blocking dead-path hits:
$LIVE_OUT"

echo
echo "=== SUMMARY: $PASS_COUNT passed, $FAIL_COUNT failed ==="
[ "$FAIL_COUNT" -eq 0 ]
