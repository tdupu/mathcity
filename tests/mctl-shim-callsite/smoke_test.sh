#!/bin/sh
# mathcity/tests/mctl-shim-callsite/smoke_test.sh
#
# Guards the mctl entry-point contract:
#
#   1. bin/mctl exists, is executable, and execs assets/scripts/mctl.py.
#   2. bin/mctl has at least one real caller — check-briefs. An MCP server is
#      being built on this CLI; a CLI with zero callers is the top project risk,
#      so the one wired call site must not silently regress.
#   3. No skill bypasses the shim by invoking assets/scripts/mctl.py directly.
#
# Static only, in the style of tests/dolt-preflight-exit-codes/smoke_test.sh
# part A: needs no live gc, bd, Dolt server, or city.
set -eu

HERE="$(cd "$(dirname "$0")" && pwd)"
PACK="$(cd "$HERE/../.." && pwd)"
SHIM="$PACK/bin/mctl"
CALLER="$PACK/skills/check-briefs/SKILL.md"

fail() { echo "FAIL: $*" >&2; exit 1; }

echo "=== 1. the shim itself ==="

[ -f "$SHIM" ] || fail "missing entry point: bin/mctl"
[ -x "$SHIM" ] || fail "bin/mctl is not executable (chmod +x, and commit the mode bit)"
grep -q 'assets/scripts/mctl.py' "$SHIM" \
  || fail "bin/mctl does not hand off to assets/scripts/mctl.py"
grep -q '^exec ' "$SHIM" \
  || fail "bin/mctl must exec, so stdin and the exit code pass through unchanged"
echo "ok: bin/mctl is an executable exec-shim over assets/scripts/mctl.py"

echo "=== 2. check-briefs routes through the shim ==="

[ -f "$CALLER" ] || fail "missing call site: skills/check-briefs/SKILL.md"

grep -q 'bin/mctl' "$CALLER" \
  || fail "check-briefs no longer names bin/mctl — mctl is back to zero callers"
grep -q '"\$MCTL" briefs list' "$CALLER" \
  || fail "check-briefs no longer invokes 'mctl briefs list'; the stack-reading
step has regressed to hand-rolled shell"
grep -q 'decision_state' "$CALLER" \
  || fail "check-briefs invokes mctl but never consumes decision_state"

# The output contract: still a table sorted by unlock_count descending.
grep -q 'unlock_count' "$CALLER" \
  || fail "check-briefs no longer reports unlock_count"
grep -q 'unlock_count. descending\|unlock_count` descending' "$CALLER" \
  || fail "check-briefs no longer states the unlock_count-descending sort"
echo "ok: check-briefs calls bin/mctl briefs list and keeps the output contract"

echo "=== 3. nobody bypasses the shim ==="

SEARCH_DIRS="$PACK/skills"
for d in "$PACK"/subdomains/*/skills; do
  [ -d "$d" ] || continue
  SEARCH_DIRS="$SEARCH_DIRS $d"
done

# Match invocation shape only — prose and comments may name the file as the
# thing NOT to call (as check-briefs does when it explains the contract).
hits=$(grep -rnE '(^|[^[:alnum:]_])(python3?|exec|bash|sh)[[:space:]][^#]*assets/scripts/mctl\.py' \
         $SEARCH_DIRS | grep -v ':[[:space:]]*#' || true)
[ -z "$hits" ] || fail "skill invokes mctl.py directly instead of bin/mctl:
$hits"
echo "ok: no skill bypasses bin/mctl"

# ===========================================================================
# Slice 7 — the skill refactor onto the mctl surface.
#
# Parts 1-3 above guard the ONE pilot call site. Parts 4-9 guard the rest of
# the slice: the register is the audit record, and these checks are what stop
# it from drifting away from the skills it describes.
# ===========================================================================

REGISTER="$PACK/subdomains/dev/docs/plans/mcp/SKILL-IMPACT-REGISTER.md"
[ -f "$REGISTER" ] || fail "missing audit record: $REGISTER"

# --- the wiring registry ---------------------------------------------------
# One row per skill whose final disposition is `replace-with-mctl` or
# `wrap-with-mctl`. Fields:
#
#   path | class | required mctl invocation fragments (comma-separated)
#
# class `mutation` additionally has to surface the mctl trace id (plan Slice 7
# step 4); class `read` mutates no canonical state and therefore does not.
#
# A skill listed here but not wired FAILS part 4. A skill wired here but absent
# from the register FAILS part 7.
WIRED='
skills/check-briefs/SKILL.md|read|briefs list
skills/adjudicate-brief/SKILL.md|mutation|briefs adjudicate,briefs defer,work dispatch
skills/create-brief/SKILL.md|mutation|briefs create,briefs validate
skills/brief-prep/SKILL.md|mutation|briefs create,briefs validate
skills/coordinate-review/SKILL.md|read|briefs doctor,briefs options
skills/work/SKILL.md|mutation|work ready,work status,work dispatch
skills/immediate-work/SKILL.md|mutation|work status,work dispatch
skills/priority-work/SKILL.md|mutation|work ready,work provenance
skills/present-briefs/SKILL.md|read|briefs list
skills/prime-clerk/SKILL.md|read|briefs list
skills/mayor-math/SKILL.md|read|work ready
skills/mayor-math-prime/SKILL.md|read|briefs list
skills/mayor-math-handoff/SKILL.md|read|briefs list,work ready
'

echo "=== 4. every wired skill invokes the mctl commands it claims ==="

printf '%s\n' "$WIRED" | while IFS='|' read -r rel class fragments; do
  [ -n "$rel" ] || continue
  f="$PACK/$rel"
  [ -f "$f" ] || fail "wired skill does not exist: $rel"
  grep -q 'bin/mctl' "$f" \
    || fail "$rel is registered as mctl-wired but never names bin/mctl"
  # The pilot's discovery pattern is the only sanctioned one: resolve the pack
  # root, then invoke "$MCTL". A second discovery rule is how a CLI ends up
  # with call sites that work in one checkout and not another.
  grep -q 'MATHCITY_PACK_ROOT' "$f" \
    || fail "$rel does not use the check-briefs pack-root discovery pattern
(MATHCITY_PACK_ROOT with the city.toml import-source fallback)"
  old_ifs=$IFS
  IFS=','
  for frag in $fragments; do
    IFS=$old_ifs
    grep -q "\"\$MCTL\" $frag" "$f" \
      || fail "$rel does not invoke '\$MCTL $frag' -- registered as wired, but
the workflow it claims to route through mctl still does not"
    IFS=','
  done
  IFS=$old_ifs
done
echo "ok: every wired skill invokes its declared mctl commands through bin/mctl"

echo "=== 5. mutation skills surface the mctl trace id ==="

printf '%s\n' "$WIRED" | while IFS='|' read -r rel class fragments; do
  [ -n "$rel" ] || continue
  [ "$class" = "mutation" ] || continue
  f="$PACK/$rel"
  # Requiring BOTH the extraction (payload key `trace_id`) and the report
  # (`MCTL-TRACE:` in the skill's own output) keeps a skill from reading the id
  # and then dropping it on the floor.
  grep -q 'trace_id' "$f" \
    || fail "$rel performs an mctl mutation but never reads the trace id"
  grep -q 'MCTL-TRACE' "$f" \
    || fail "$rel does not report the mctl trace id to its caller
(emit an 'MCTL-TRACE: <id>' line so the invocation is auditable afterwards)"
done
echo "ok: every mutation skill extracts and reports the mctl trace id"

echo "=== 6. no wired skill writes redundant brief artifacts directly ==="

# The bead store is canonical and ONE implementation owns the cache writes
# (assets/scripts/mctl_core/effects.py). A skill that still rewrites the stack
# index, the legacy decisions-track manifest, or a brief's frontmatter in place
# has not been refactored -- it has been annotated.
# ONE declared exemption, declared here so it cannot spread silently.
# adjudicate-brief still syncs the LEGACY decisions-track brief file and its
# manifest (step 2b): mctl models neither, #38 owns that tree, bulk migration is
# HELD, and removing the sync re-opens the #18 re-presentation bug that
# tests/present-briefs-defer-filter/test_defer_filter.sh guards by executing the
# writer. The exemption covers decisions-track ONLY -- the pile and
# stack/.index.jsonl checks below still apply to it in full.
LEGACY_DTRACK_EXEMPT="skills/adjudicate-brief/SKILL.md"

printf '%s\n' "$WIRED" | while IFS='|' read -r rel class fragments; do
  [ -n "$rel" ] || continue
  f="$PACK/$rel"
  if [ "$rel" = "$LEGACY_DTRACK_EXEMPT" ]; then
    # The exemption is conditional on the skill saying so, in the block that
    # uses it, so an unexplained in-place write cannot hide behind the name.
    grep -q 'LEGACY-DECISIONS-TRACK' "$f" \
      || fail "$rel claims the legacy decisions-track exemption but does not
mark the block LEGACY-DECISIONS-TRACK or explain why mctl cannot own it"
    grep -q 'decisions-track' "$f" \
      || fail "$rel holds the legacy decisions-track exemption but no longer
writes decisions-track at all -- drop it from LEGACY_DTRACK_EXEMPT"
  else
    inplace=$(grep -n 'sed -i' "$f" || true)
    [ -z "$inplace" ] || fail "$rel rewrites a brief artifact in place with sed -i:
$inplace"
  fi
  # Write shapes only: a shell redirect, a Python .write(), or open(..., "w"/"a").
  # A bare open()/read of the index is fine -- present-briefs legitimately reads
  # the stack index to build its queue.
  # The pile and the stack index are mctl's alone, exemption or not; only the
  # legacy decisions-track manifest is excused, and only for the one skill.
  PATTERN='(\.index\.jsonl|manifest\.jsonl)'
  [ "$rel" != "$LEGACY_DTRACK_EXEMPT" ] || PATTERN='\.index\.jsonl'
  cachewrite=$(grep -nE "$PATTERN" "$f" \
               | grep -E "(>>?[[:space:]]|\.write\(|open\([^)]*[\"'][wa])" || true)
  [ -z "$cachewrite" ] || fail "$rel writes a redundant brief cache artifact directly:
$cachewrite"
done
echo "ok: no wired skill edits the stack index, legacy manifest, or frontmatter in place"

echo "=== 7. the register classifies every audited skill ==="

# The final-disposition table is the audit record: markdown rows naming one of
# the four disposition tokens.
# A disposition row names both a skill and the file it lives in; the legend
# table above it names dispositions without a path, so requiring the path is
# what separates the record from its own key.
rows=$(grep -E '^\|' "$REGISTER" \
       | grep -E 'replace-with-mctl|wrap-with-mctl|no-change|blocked-by-policy' \
       | grep -E 'SKILL\.md|\.toml' || true)
[ -n "$rows" ] || fail "SKILL-IMPACT-REGISTER.md has no final-disposition table
(an unchanged register means the slice is not done)"

n_rows=$(printf '%s\n' "$rows" | wc -l | tr -d ' ')
[ "$n_rows" -ge 30 ] \
  || fail "the register classifies only $n_rows skills; every skill it audits
needs a final disposition (expected at least 30)"

# The register and the skills must agree about which workflows depend on mctl.
printf '%s\n' "$WIRED" | while IFS='|' read -r rel class fragments; do
  [ -n "$rel" ] || continue
  name=$(basename "$(dirname "$rel")")
  printf '%s\n' "$rows" | grep -qE "\`$name\`.*(replace-with-mctl|wrap-with-mctl)" \
    || fail "$name is wired to mctl but the register does not record it as
replace-with-mctl or wrap-with-mctl"
done
echo "ok: $n_rows skills classified; every wired skill agrees with the register"

echo "=== 8. no-change verdicts carry a source-of-truth reason ==="

# Plan Slice 7 step 1 and audit rule 3: `no-change` is a legitimate verdict, but
# only with a reason tied to the Section 2 source-of-truth boundaries -- the two
# adapters -- not "seemed risky".
printf '%s\n' "$rows" | grep -E 'no-change|blocked-by-policy' | while read -r row; do
  case "$row" in
    *BeadStoreAdapter*|*BriefCacheAdapter*) ;;
    *) fail "a no-change/blocked-by-policy row cites no §2 source-of-truth
boundary (it must name BeadStoreAdapter or BriefCacheAdapter):
$row" ;;
  esac
done
echo "ok: every no-change and blocked-by-policy verdict cites a §2 boundary"

echo "=== 9. no skill branches on the untrusted diagnostic codes ==="

# MBRF021 is a mass false positive (66 of 70 briefs in one rig, issue #58).
# MBRF004/MBRF005 are instrumentation under review -- `malformed` means "closed
# with no verdict FIELD", not damaged (see
# subdomains/dev/docs/MALFORMED-BRIEF-TRIAGE-2026-08-19.md).
# mctl_core/mcp_server.py already withholds MBRF021 from the actionable array;
# a skill that branches on any of the three acts on false signal.
for d in $SEARCH_DIRS; do
  hits=$(grep -rnE '(if |case |grep -q|test |\[ |\[\[ ).*MBRF(021|004|005)' "$d" || true)
  [ -z "$hits" ] || fail "skill branches on an untrusted diagnostic code:
$hits"
done
echo "ok: no skill branches on MBRF021 / MBRF004 / MBRF005"

echo "=== 10. the primes teach the MCP surface and degrade to bin/mctl ==="

# Slice 8 (#60 D1): MCP is the target surface, bin/mctl is the bridge. A PRIME is
# how a fresh session orients, so a prime that assumes the MCP is present starts
# the session blind -- external clients see ZERO tools by default
# (mcp_server.py: client_class defaults to "external"), and the .mcp.json that
# would change that is uncommitted and inert until a session restart.
#
# These checks enforce the honest-degradation contract, not prose quality:
# every prime names the surface, names the fallback, and no skill tries to
# detect the surface from a shell it cannot observe.
MCP_PRIMED='
skills/mayor-math-prime/SKILL.md
skills/mayor-math/SKILL.md
skills/mayor-math-handoff/SKILL.md
skills/prime-clerk/SKILL.md
'

FRAGMENT="$PACK/template-fragments/mctl-entry-point.md"
[ -f "$FRAGMENT" ] || fail "missing canonical call-site fragment: $FRAGMENT"

# The fragment is the single source for the tool<->command mapping. Skills point
# at it instead of restating 16 rows each; if it stops carrying the mapping, the
# pointers in the primes become dangling.
grep -q 'mcp__mctl__briefs_list' "$FRAGMENT" \
  || fail "the canonical fragment does not carry the MCP tool<->CLI mapping
(the primes delegate the tool list to it; it cannot be the source and not say so)"
grep -qi 'client_class\|external' "$FRAGMENT" \
  || fail "the canonical fragment does not explain the rollout gate
(a caller that does not know tools are hidden by default reads absence as breakage)"

printf '%s\n' "$MCP_PRIMED" | while read -r rel; do
  [ -n "$rel" ] || continue
  f="$PACK/$rel"
  [ -f "$f" ] || fail "prime does not exist: $rel"

  # 10a -- it names the typed surface at all.
  grep -q 'mcp__mctl__' "$f" \
    || fail "$rel never names the MCP surface (mcp__mctl__*)
It is a prime: it is how a session learns what control surface exists."

  # 10b -- it names the fallback. This is the load-bearing one: a prime that
  # reaches for a tool with no CLI path behind it strands every session that
  # does not have the MCP registered, which today is nearly all of them.
  grep -q 'bin/mctl' "$f" \
    || fail "$rel names the MCP but never names bin/mctl
Prefer-MCP is only safe when the fallback is stated in the same skill."

  # 10c -- it says how to tell which surface is available, and the answer must
  # be "look at your own tool list", never "call it and see".
  grep -qi 'tool list' "$f" \
    || fail "$rel does not tell the session how to detect the surface
(it must inspect its own tool list; there is no shell probe for this)"

  # 10d -- absence must be stated as normal. A prime that presents a missing
  # MCP as an error condition produces exactly the blind start this guards.
  grep -qiE 'absent|absence|not connected' "$f" \
    || fail "$rel does not state what happens when the MCP is absent
Absence is the DEFAULT (external clients see zero tools), not an error."
done
echo "ok: every prime teaches the MCP surface, its detection, and the bin/mctl fallback"

# 10e -- the tool list is not observable from the shell, so a shell test against
# mcp__mctl__ can only ever take the wrong branch. It is also the shape that
# turns an absent optional surface into a dead prime (`... || exit 1`).
for d in $SEARCH_DIRS; do
  hits=$(grep -rnE '(if |case |grep -q|test |\[ |\[\[ ).*mcp__mctl__' "$d" || true)
  [ -z "$hits" ] || fail "a skill branches in SHELL on the MCP tool surface:
$hits
Detection is the agent reading its own tool list, not a shell probe."
done
echo "ok: no skill tries to detect the MCP surface from the shell"

echo "ALL MCTL SHIM CALL-SITE CHECKS PASSED"
