#!/bin/sh
# mathcity/tests/dolt-preflight-exit-codes/smoke_test.sh
#
# Guards the three-valued `gc dolt health` contract (issues #7, #8) AND the
# reporting-vs-working split that decides who prints on exit 2.
#
#   exit 0                        -> healthy, proceed silently (both classes)
#   exit 2                        -> reachable, compaction quarantined: NON-FATAL
#                                    Variant A (working skill)   -> SILENT, proceed
#                                    Variant B (reporting skill) -> print the block, proceed
#   exit 1 / 78 / 127 / anything  -> unreachable, abort with the P1.14 message
#
# Three parts:
#   A. classification — every file carrying the pre-flight is in exactly one
#                       class list. A new call site in neither list FAILS here,
#                       so a skill cannot drift in unclassified.
#   B. static        — no call site may collapse the probe back to a boolean `||`
#                      test, and no reporting site may truncate the health report
#                      with `head` (the quarantine block is printed LAST).
#   C. dynamic       — the published fragment blocks AND the real blocks shipped
#                      in the call sites are executed against stub `gc` binaries
#                      returning each exit code.
#
# Self-contained: needs no live gc, bd, Dolt server, or city.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
PACK="$(cd "$HERE/../.." && pwd)"
FRAGMENT="$PACK/template-fragments/dolt-preflight.md"

fail() { echo "FAIL: $*" >&2; exit 1; }

# ---------------------------------------------------------------------------
# The classification. This is the load-bearing part of the test: the rule is
# "if the skill's purpose is to report on city health, use Variant B; otherwise
# Variant A" (template-fragments/dolt-preflight.md, Rule 5).
# ---------------------------------------------------------------------------

# Variant A — working skills. Exit 2 produces NO output.
VARIANT_A="
skills/check-briefs/SKILL.md
skills/check-molecules/scripts/enumerate-molecules.sh
skills/create-bead-manifest/SKILL.md
skills/refine-bead-manifest/SKILL.md
skills/simple-work/SKILL.md
skills/work/SKILL.md
subdomains/dev/skills/check-build-formulas-and-skills/SKILL.md
subdomains/dev/skills/formula-creator-math/SKILL.md
subdomains/dev/skills/formula-work/SKILL.md
subdomains/dev/skills/push-the-fleet/SKILL.md
subdomains/dev/skills/strand-sweep/SKILL.md
subdomains/dev/skills/testing-work/SKILL.md
"

# Variant B — reporting skills. Exit 2 prints the full quarantine block.
# These three are also the ONLY files sanctioned to report-and-continue on the
# abort branch instead of exiting (fragment Rule 7): their job is diagnosing a
# dead city, and wake-city's own remedy for exit 1 is `gc dolt start`.
VARIANT_B="
skills/wake-city/SKILL.md
subdomains/dev/skills/city-status/SKILL.md
subdomains/dev/skills/hourly-check/SKILL.md
"

# Prose-only: these mention `gc dolt health` in narrative text, with no probe.
PROSE_ONLY="
skills/check-molecules/SKILL.md
skills/check-work/SKILL.md
"

echo "=== A. classification: every call site is in exactly one class ==="

[ -f "$FRAGMENT" ] || fail "canonical fragment missing: template-fragments/dolt-preflight.md"

# Search skills + subdomain skills only; docs and the fragment itself may quote
# the probe as prose or audit vocabulary.
SEARCH_DIRS="$PACK/skills"
for d in "$PACK"/subdomains/*/skills; do
  [ -d "$d" ] || continue
  SEARCH_DIRS="$SEARCH_DIRS $d"
done

in_list() { # $1 = relative path, $2 = list
  for _e in $2; do
    [ "$_e" = "$1" ] && return 0
  done
  return 1
}

# Every listed file must exist and actually carry the probe (catches renames
# and stale entries — a class list that names a dead file proves nothing).
for rel in $VARIANT_A $VARIANT_B $PROSE_ONLY; do
  [ -f "$PACK/$rel" ] || fail "class list names a missing file: $rel"
  grep -q 'gc dolt health' "$PACK/$rel" \
    || fail "class list names $rel, but it no longer invokes gc dolt health"
done

# No file may be in two classes.
for rel in $VARIANT_A; do
  if in_list "$rel" "$VARIANT_B" || in_list "$rel" "$PROSE_ONLY"; then
    fail "$rel is in more than one class list"
  fi
done
for rel in $VARIANT_B; do
  in_list "$rel" "$PROSE_ONLY" && fail "$rel is in more than one class list"
done

# THE ANTI-ROT ASSERTION: every file carrying the probe must be classified.
unclassified=""
for f in $(grep -rl 'gc dolt health' $SEARCH_DIRS | sort); do
  rel="${f#"$PACK"/}"
  if in_list "$rel" "$VARIANT_A" || in_list "$rel" "$VARIANT_B" \
     || in_list "$rel" "$PROSE_ONLY"; then
    continue
  fi
  unclassified="$unclassified $rel"
done
[ -z "$unclassified" ] || fail "unclassified Dolt pre-flight call site(s):$unclassified
Every call site must be listed in VARIANT_A (working skill: silent on exit 2),
VARIANT_B (reporting skill: surfaces the quarantine), or PROSE_ONLY in
$0. See template-fragments/dolt-preflight.md — 'if the skill's purpose is to
report on city health, use Variant B; otherwise use Variant A'."

n_a=$(echo $VARIANT_A | wc -w | tr -d ' ')
n_b=$(echo $VARIANT_B | wc -w | tr -d ' ')
n_p=$(echo $PROSE_ONLY | wc -w | tr -d ' ')
echo "ok: $((n_a + n_b + n_p)) files classified ($n_a Variant A, $n_b Variant B, $n_p prose-only)"

echo "=== B. static: no boolean or truncating probes; per-class shape ==="

hits=$(grep -rn 'gc dolt health >/dev/null' $SEARCH_DIRS || true)
[ -z "$hits" ] || fail "boolean Dolt probe reintroduced (exit 2 would abort):
$hits"

hits=$(grep -rn 'gc dolt health.*| *head' $SEARCH_DIRS || true)
[ -z "$hits" ] || fail "Dolt health output truncated with head; the compaction
quarantine block is printed last and would be discarded:
$hits"

for rel in $VARIANT_A $VARIANT_B; do
  f="$PACK/$rel"
  # The exit code must be captured and branched on, never discarded.
  grep -q '_dolt_rc\|DOLT_RC' "$f" \
    || fail "$rel invokes gc dolt health without capturing its exit code"
  grep -q 'uarantine' "$f" \
    || fail "$rel invokes gc dolt health but never handles the exit-2 quarantine case"
done

# Variant A: the 2 branch must be explicitly present and empty.
for rel in $VARIANT_A; do
  grep -q '^  2) ;;' "$PACK/$rel" \
    || fail "$rel is classified Variant A (working skill) but its exit-2 branch is
not the silent form '  2) ;;'. Working skills must produce no output on a
standing quarantine — see template-fragments/dolt-preflight.md, Variant A."
done

# Variant B: must actually surface the quarantine block and the reclaim path.
for rel in $VARIANT_B; do
  f="$PACK/$rel"
  grep -q "sed -n '/\^Compaction quarantine:/,\$p'" "$f" \
    || fail "$rel is classified Variant B (reporting skill) but never extracts the
'Compaction quarantine:' block from the health report. Variant A is silent ONLY
because Variant B surfaces this — see template-fragments/dolt-preflight.md, Rule 6."
  grep -q 'gc dolt compact' "$f" \
    || fail "$rel is classified Variant B but never names the reclaim path (gc dolt compact)"
done
echo "ok: $n_a Variant A sites silent-on-2, $n_b Variant B sites surface the block"

echo "=== C. dynamic: pre-flight behavior per exit code ==="

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$TMP/bin"

QUARANTINE_REPORT='Server: running (PID 1, port 58506, latency 117ms)

Backups: none found

Compaction quarantine: 2 (auto-GC blocked)
  hecke: post-flatten table value hash changed with row-count increase (held 33d04h)
  hq: post-flatten table value hash changed with row-count increase (held 36d08h)'

make_gc() { # $1 = exit code, $2 = stdout payload
  { echo '#!/bin/sh'
    printf 'cat <<'"'"'GCEOF'"'"'\n%s\nGCEOF\n' "$2"
    echo "exit $1"
  } > "$TMP/bin/gc"
  chmod +x "$TMP/bin/gc"
}

extract() { # $1 = source file, $2 = awk start pattern, $3 = label
  awk "/$2/,/^esac\$/" "$1" > "$TMP/block.sh"
  grep -q '^esac$' "$TMP/block.sh" \
    || fail "could not extract the pre-flight block from $3"
  echo 'echo PROCEEDED' >> "$TMP/block.sh"
}

run_block() { PATH="$TMP/bin:$PATH" sh "$TMP/block.sh" 2>&1; }

# --- shared assertions ------------------------------------------------------

assert_exit0_silent() { # $1 = label
  make_gc 0 'Server: running (PID 1, port 58506, latency 117ms)'
  out=$(run_block) || fail "$1: exit 0 must not abort"
  [ "$out" = "PROCEEDED" ] \
    || fail "$1: exit 0 must proceed silently; got: $out"
}

assert_exit2_silent() { # $1 = label  (Variant A)
  make_gc 2 "$QUARANTINE_REPORT"
  out=$(run_block) || fail "$1: exit 2 (quarantine) must NOT abort — that is issue #8"
  [ "$out" = "PROCEEDED" ] \
    || fail "$1: Variant A must produce NO output on exit 2 and proceed; got:
$out"
}

assert_exit2_surfaces() { # $1 = label  (Variant B)
  make_gc 2 "$QUARANTINE_REPORT"
  out=$(run_block) || fail "$1: exit 2 (quarantine) must NOT abort — that is issue #8"
  case "$out" in *PROCEEDED*) ;; *) fail "$1: exit 2 must proceed; got: $out" ;; esac
  echo "$out" | grep -qi 'quarantine' \
    || fail "$1: Variant B must surface the quarantine on exit 2; got: $out"
  echo "$out" | grep -q 'hecke' \
    || fail "$1: Variant B must name each quarantined database; got: $out"
  echo "$out" | grep -q 'hq' \
    || fail "$1: Variant B must name each quarantined database; got: $out"
  echo "$out" | grep -q '33d04h' \
    || fail "$1: Variant B must report the held-duration; got: $out"
  echo "$out" | grep -q 'gc dolt compact' \
    || fail "$1: Variant B must point at the reclamation path; got: $out"
  if echo "$out" | grep -qi "I'm sorry"; then
    fail "$1: exit 2 must not emit the abort message"
  fi
}

assert_aborts() { # $1 = label, $2 = "strict" to also require a fix action
  for rc in 1 78 127; do
    make_gc "$rc" 'unreachable'
    if out=$(run_block); then
      fail "$1: exit $rc must abort; got: $out"
    fi
    if echo "$out" | grep -q PROCEEDED; then
      fail "$1: exit $rc must not proceed; got: $out"
    fi
    echo "$out" | grep -qi "I'm sorry, I can't do that" \
      || fail "$1: exit $rc must keep the P1.14 message shape; got: $out"
    if [ "${2:-}" = "strict" ]; then
      echo "$out" | grep -q 'gc dolt start\|gc start' \
        || fail "$1: exit $rc must name a fix action (P1.14)"
    fi
  done
}

# --- C1. the two published fragment blocks ----------------------------------
# These are what a skill author copies, so both must satisfy the FULL contract,
# including the aborting `*` branch.

extract "$FRAGMENT" '^# --- P1\.14 Dolt pre-flight \(three-valued' "the fragment (Variant A)"
cp "$TMP/block.sh" "$TMP/fragment-a.sh"
assert_exit0_silent  "fragment Variant A"
assert_exit2_silent  "fragment Variant A"
assert_aborts        "fragment Variant A" strict
echo "ok: fragment Variant A -> 0 silent, 2 SILENT + proceeds, 1/78/127 abort"

extract "$FRAGMENT" '^# --- P1\.14 Dolt pre-flight .* REPORTING' "the fragment (Variant B)"
cp "$TMP/block.sh" "$TMP/fragment-b.sh"
assert_exit0_silent    "fragment Variant B"
assert_exit2_surfaces  "fragment Variant B"
cp "$TMP/fragment-b.sh" "$TMP/block.sh"
assert_aborts          "fragment Variant B" strict
echo "ok: fragment Variant B -> 0 silent, 2 surfaces hecke/hq + hold time + reclaim, 1/78/127 abort"

# The two variants must differ in the `2` branch ONLY.
sed -n '/^  \*)/,/^esac$/p' "$TMP/fragment-a.sh" > "$TMP/abort-a"
sed -n '/^  \*)/,/^esac$/p' "$TMP/fragment-b.sh" > "$TMP/abort-b"
[ -s "$TMP/abort-a" ] || fail "could not isolate the fragment Variant A abort branch"
cmp -s "$TMP/abort-a" "$TMP/abort-b" \
  || fail "the abort branch must be byte-identical in Variant A and Variant B;
the variants may differ in the exit-2 branch and nothing else:
$(diff "$TMP/abort-a" "$TMP/abort-b" || true)"
echo "ok: abort branch byte-identical across both variants"

# --- C2. every live Variant A call site -------------------------------------
# Per-skill wording of the abort message differs by design (fragment Rule 4);
# the predicate does not, so these are checked non-strict.

for rel in $VARIANT_A; do
  extract "$PACK/$rel" '^_dolt_out=\$\(gc dolt health' "$rel"
  assert_exit0_silent "$rel"
  assert_exit2_silent "$rel"
  assert_aborts       "$rel"
done
echo "ok: $n_a live Variant A call sites -> silent on 2, abort on 1/78/127"

# --- C3. live Variant B call sites ------------------------------------------
# wake-city ships an executable case block; run it. city-status and hourly-check
# are prose-directed report blocks with no `case` — part B covers them
# statically (they must extract the quarantine block and name the reclaim path).

extract "$PACK/skills/wake-city/SKILL.md" '^_dolt_out=\$\(gc dolt health' "wake-city"
make_gc 2 "$QUARANTINE_REPORT"
out=$(run_block) || fail "wake-city: exit 2 must not abort"
echo "$out" | grep -qi 'quarantin' || fail "wake-city: exit 2 must surface the quarantine; got: $out"
echo "$out" | grep -q 'hecke'      || fail "wake-city: exit 2 must name each quarantined DB; got: $out"
echo "$out" | grep -q 'hq'         || fail "wake-city: exit 2 must name each quarantined DB; got: $out"
echo "$out" | grep -q '36d08h'     || fail "wake-city: exit 2 must report the held-duration; got: $out"
echo "$out" | grep -q 'gc dolt compact' || fail "wake-city: exit 2 must name the reclaim path; got: $out"
# Exit 2 is NOT a stall cause: wake-city must not report Dolt as down.
if echo "$out" | grep -q 'dolt: DOWN'; then
  fail "wake-city: exit 2 must not be reported as DOWN (this is issue #8); got: $out"
fi
# Exit 1 must still be distinguished from 2 (the whole point of issues #7/#8).
for rc in 1 78 127; do
  make_gc "$rc" 'unreachable'
  out=$(run_block) || fail "wake-city: exit $rc must not hard-fail the diagnosis"
  echo "$out" | grep -q 'dolt: DOWN' \
    || fail "wake-city: exit $rc must report Dolt DOWN; got: $out"
  if echo "$out" | grep -qi 'quarantin'; then
    fail "wake-city: exit $rc must not be reported as a quarantine; got: $out"
  fi
done
echo "ok: live wake-city (Variant B) -> surfaces on 2, reports DOWN on 1/78/127"

echo "ALL DOLT-PREFLIGHT EXIT-CODE + CLASSIFICATION CHECKS PASSED"
