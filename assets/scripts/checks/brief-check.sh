#!/bin/sh
set -eu

COMMAND="${1:-}"
if [ -z "$COMMAND" ]; then
  echo "usage: brief-check.sh <check-name>" >&2
  exit 2
fi

# Rig-relative default per assets/brief-pipeline/paths.toml (gsp-3al3);
# step checks run with the rig root as cwd. Override via BRIEF_ROOT.
ROOT="${BRIEF_ROOT:-.beads/briefs}"

fail() {
  echo "brief-check: $*" >&2
  exit 1
}

metadata_value() {
  key="$1"
  if [ -z "${GC_BEAD_ID:-}" ] || ! command -v gc >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
    return 0
  fi
  gc bd show "$GC_BEAD_ID" --json 2>/dev/null |
    jq -r --arg key "$key" '.[0].metadata[$key] // empty' 2>/dev/null || true
}

first_match() {
  pattern="$1"
  find . -path "$pattern" -type f 2>/dev/null | sort | head -n 1
}

brief_path() {
  if [ -n "${GC_BRIEF_PATH:-}" ]; then
    printf '%s\n' "$GC_BRIEF_PATH"
    return 0
  fi
  value="$(metadata_value "gc.brief.path")"
  if [ -n "$value" ]; then
    printf '%s\n' "$value"
    return 0
  fi
  value="$(metadata_value "brief.path")"
  if [ -n "$value" ]; then
    printf '%s\n' "$value"
    return 0
  fi
  first_match "./$ROOT/.staging/*/brief.md"
}

require_file() {
  path="$1"
  [ -n "$path" ] || fail "missing path"
  [ -f "$path" ] || fail "missing file: $path"
}

require_dir() {
  path="$1"
  [ -d "$path" ] || fail "missing directory: $path"
}

# pack_asset <path-under-assets/> -- locate a file that ships in this pack,
# without depending on the working directory.
#
# Since cc58a95 check scripts are resolved FROM THE PACK at cook time
# (`path = "../assets/scripts/checks/<name>.sh"`), but the ralph runner still
# runs them with the agent work dir as cwd, which is never the pack root. A
# cwd-relative literal thus resolves to nothing in production even though it
# resolves fine under the test suite, which runs from the pack root. Anchor on
# the script's own location instead: assets/scripts/checks/.. /.. -> assets.
#
# Always exits 0 and always prints a path, so `set -e` cannot trip here and the
# caller's own -f test remains the thing that decides. When the asset cannot be
# found the cwd-relative form is printed unchanged, so callers that refuse on a
# missing file go on refusing exactly as before.
pack_asset() {
  pa_rel="$1"
  pa_assets="$(CDPATH= cd -- "$(dirname -- "$0")/../.." 2>/dev/null && pwd || true)"
  if [ -n "$pa_assets" ] && [ -f "$pa_assets/$pa_rel" ]; then
    printf '%s\n' "$pa_assets/$pa_rel"
    return 0
  fi
  printf '%s\n' "assets/$pa_rel"
}

# pack_dir <path-under-pack-root> -- the pack_asset counterpart for things that
# live at the pack ROOT rather than under assets/ (formulas/, gates/).
# assets/scripts/checks/../../.. -> the pack itself.
#
# Same contract as pack_asset: always exits 0, always prints a path, falls back
# to the cwd-relative form when the target cannot be found. The caller decides
# what an unresolvable path means -- and for a SCAN the caller must decide
# explicitly, because an unresolvable scan root yields no matches, which is
# indistinguishable from a clean result.
pack_dir() {
  pd_rel="$1"
  pd_root="$(CDPATH= cd -- "$(dirname -- "$0")/../../.." 2>/dev/null && pwd || true)"
  if [ -n "$pd_root" ] && [ -e "$pd_root/$pd_rel" ]; then
    printf '%s\n' "$pd_root/$pd_rel"
    return 0
  fi
  printf '%s\n' "$pd_rel"
}

require_text() {
  path="$1"
  pattern="$2"
  message="$3"
  grep -Eq "$pattern" "$path" || fail "$message in $path"
}

require_frontmatter_key_value() {
  path="$1"
  key="$2"
  expected="$3"
  awk -v key="$key" -v expected="$expected" '
    BEGIN { in_frontmatter = 0; closed = 0; found = 0; invalid = 0 }
    NR == 1 {
      if ($0 != "---") { invalid = 1; exit }
      in_frontmatter = 1
      next
    }
    in_frontmatter && $0 == "---" {
      closed = 1
      exit
    }
    in_frontmatter {
      line = $0
      prefix = "^" key "[[:space:]]*:"
      if (line ~ prefix) {
        sub(prefix, "", line)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
        if (line ~ /^".*"$/ || line ~ /^'"'"'.*'"'"'$/) {
          line = substr(line, 2, length(line) - 2)
        }
        if (line == expected) { found = 1 }
      }
    }
    END { exit(!invalid && closed && found ? 0 : 1) }
  ' "$path" || fail "frontmatter $key must equal $expected in $path"
}

require_frontmatter_key() {
  path="$1"
  key="$2"
  frontmatter_has_key "$path" "$key" ||
    fail "frontmatter $key must have a value in $path"
}

frontmatter_has_key() {
  path="$1"
  key="$2"
  awk -v key="$key" '
    BEGIN { in_frontmatter = 0; closed = 0; found = 0; invalid = 0 }
    NR == 1 {
      if ($0 != "---") { invalid = 1; exit }
      in_frontmatter = 1
      next
    }
    in_frontmatter && $0 == "---" {
      closed = 1
      exit
    }
    in_frontmatter {
      line = $0
      prefix = "^" key "[[:space:]]*:"
      if (line ~ prefix) {
        sub(prefix, "", line)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", line)
        if (length(line) > 0) { found = 1 }
      }
    }
    END { exit(!invalid && closed && found ? 0 : 1) }
  ' "$path"
}

check_profile_common() {
  path="$1"
  profile="$2"
  require_file "$path"
  require_frontmatter_key_value "$path" "gate_profile" "$profile"
  require_frontmatter_key_value "$path" "feedback_sink" "brief_quality_failure"
  check_no_brainer_classification_evidence
}

check_action_block() {
  path="$1"
  require_text "$path" '^action_block:[[:space:]]*$' "missing action_block"
  require_text "$path" '^  on_approve:' "action_block missing on_approve"
  require_text "$path" '^  on_reject:' "action_block missing on_reject"
  require_text "$path" '^  on_defer:' "action_block missing on_defer"
}

check_decision_profile() {
  path="$(brief_path)"
  check_profile_common "$path" "decision"
  require_frontmatter_key_value "$path" "brief_kind" "decision"
  if ! frontmatter_has_key "$path" "source_bead"; then
    require_frontmatter_key "$path" "legacy_source"
  fi
  check_action_block "$path"
}

check_lost_bead_filter_profile() {
  path="$(brief_path)"
  check_profile_common "$path" "lost_bead_filter"
  require_frontmatter_key_value "$path" "brief_kind" "lost_bead_filter"
  for key in source_bead fingerprint threshold_count distinct_bead_count replay_command false_positive_risk; do
    require_frontmatter_key "$path" "$key"
  done
}

check_producer_repair_profile() {
  path="$(brief_path)"
  check_profile_common "$path" "producer_repair"
  require_frontmatter_key_value "$path" "brief_kind" "producer_repair"
  require_frontmatter_key_value "$path" "producer_contract" "brief-producer-repair.v1"
  for key in repair_source_formula repair_failed_gate repair_failure_fingerprint replay_command; do
    require_frontmatter_key "$path" "$key"
  done
}

check_brief_quality_failure_record() {
  path="$(brief_path)"
  require_file "$path"
  for key in schema brief_id brief_kind gate_profile source_bead source_surface failed_gate failure_summary failure_fingerprint status; do
    awk -v key="$key" '
      $0 ~ "^[[:space:]]*" key "[[:space:]]*=" {
        value = $0
        sub("^[[:space:]]*" key "[[:space:]]*=[[:space:]]*", "", value)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
        if (value != "" && value != "\"\"" && value != "''''") found = 1
      }
      END { exit(found ? 0 : 1) }
    ' "$path" || fail "TOML field $key must have a value in $path"
  done
  require_toml_key_value "$path" "schema" "brief_quality_failure.v1"
  require_toml_key_value "$path" "status" "untriaged"
}

require_toml_key_value() {
  path="$1"
  key="$2"
  expected="$3"
  awk -v key="$key" -v expected="$expected" '
    $0 ~ "^[[:space:]]*" key "[[:space:]]*=" {
      value = $0
      sub("^[[:space:]]*" key "[[:space:]]*=[[:space:]]*", "", value)
      gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
      if (value ~ /^".*"$/) value = substr(value, 2, length(value) - 2)
      if (value == expected) found = 1
    }
    END { exit(found ? 0 : 1) }
  ' "$path" || fail "TOML $key must equal $expected in $path"
}

# Default gate-evidence vocabulary is POLICY B1.4's "evidence or an explicit
# N/A". A gate whose rule mandates its own vocabulary passes it as $3; see the
# G14 call site below. Widening is deliberately per-gate, never global: the
# literal `PASS` token is what gate-test-evidence.sh keys on to fire G1's
# five-field structural check, so accepting `PASSED` for G1 would silently
# skip that check.
GATE_STATUS_DEFAULT="PASS|N/A"

require_gate() {
  path="$1"
  key="$2"
  accepted="${3:-$GATE_STATUS_DEFAULT}"
  if grep -Eq "$key:[[:space:]]*(FAIL|BLOCKED)\\b" "$path"; then
    fail "$key is failing or blocked"
  fi
  grep -Eq "$key:[[:space:]]*($accepted)\\b" "$path" ||
    fail "$key must be one of: $accepted"
}

check_jsonl() {
  manifest="$1"
  [ -f "$manifest" ] || return 0
  if command -v jq >/dev/null 2>&1; then
    line_no=0
    while IFS= read -r line || [ -n "$line" ]; do
      line_no=$((line_no + 1))
      [ -z "$line" ] && continue
      printf '%s\n' "$line" | jq -e . >/dev/null 2>&1 ||
        fail "invalid JSONL in $manifest at line $line_no"
    done < "$manifest"
  fi
}

check_test_evidence() {
  path="$(brief_path)"
  require_file "$path"
  require_text "$path" '^##*[[:space:]]+Gate Evidence\b|^Gate Evidence\b' "missing Gate Evidence section"
  require_gate "$path" "G1 Test-evidence"
}

check_mechanical_gates() {
  path="$(brief_path)"
  require_file "$path"
  require_text "$path" '^##*[[:space:]]+Gate Evidence\b|^Gate Evidence\b' "missing Gate Evidence section"
  require_gate "$path" "G1 Test-evidence"
  require_gate "$path" "G3 Shell-scripts-testable"
  require_gate "$path" "G5 Server-touching"
  require_gate "$path" "G5b User-skill-touching"
  require_gate "$path" "G7 Artifacts-staging"
  require_gate "$path" "G8 Brief-record"
  require_gate "$path" "G10 Improve-README"
  require_gate "$path" "G11 Breadcrumb"
  require_gate "$path" "G12 Auto-merge-kill-switch"
  require_gate "$path" "G13 Stale-claim"
  # POLICY T7 gives G14 its own tri-state vocabulary — PASSED / NOT APPLICABLE
  # / REQUIRED. Only the first two are passing states; REQUIRED means execution
  # is still owed before adjudication, so it falls through and fails closed.
  require_gate "$path" "G14 Test-execution-silent" "PASSED|PASS|NOT APPLICABLE|N/A"
  require_gate "$path" "G15 Improve-README-silent"
  require_gate "$path" "G16 Master-current"
}

check_disposition() {
  path="$(brief_path)"
  require_file "$path"
  require_text "$path" '^Disposition:[[:space:]]*(promote|reject|blocked)\b' "missing gate disposition"
}

check_pile_entry() {
  path="$(metadata_value "gc.brief.path")"
  if [ -z "$path" ]; then
    path="$(find "$ROOT/.pile" -mindepth 1 -maxdepth 1 -type f -name '*.md' 2>/dev/null | sort | head -n 1)"
  fi
  require_file "$path"
  require_text "$path" '^##*[[:space:]]+Gate Evidence\b|^Gate Evidence\b' "pile entry lacks Gate Evidence"
}

check_pile_nonempty() {
  find "$ROOT/.pile" -mindepth 1 -maxdepth 1 -type f -name '*.md' 2>/dev/null | grep -q . ||
    fail "no markdown briefs in $ROOT/.pile"
}

check_shuffle_result() {
  stack_count="$(find "$ROOT/stack" -mindepth 1 -maxdepth 1 -type f -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"
  rejected_count="$(find "$ROOT/.pile/.rejected" -mindepth 1 -maxdepth 2 -type f -name '*.md' 2>/dev/null | wc -l | tr -d ' ')"
  if [ "${stack_count:-0}" -eq 0 ] && [ "${rejected_count:-0}" -eq 0 ]; then
    # Empty-pile no-op route (gsp-3al3): with nothing promoted and nothing
    # rejected, pass ONLY when the pile itself is empty (there was nothing to
    # shuffle). A non-empty pile here means a selected brief never received a
    # disposition — that is still a failure.
    if find "$ROOT/.pile" -mindepth 1 -maxdepth 1 -type f -name '*.md' 2>/dev/null | grep -q .; then
      fail "no promoted or rejected brief found (pile still has pending briefs)"
    fi
    # #20: "empty pile" means no top-level files at all. A pile holding
    # non-.md files (*.md.bak residue, or a brief whose .md was removed while a
    # .bak survived) is NOT empty — every selector here globs '*.md', so such a
    # pile read as empty and passed vacuously, hiding two pending-review briefs
    # for weeks. A residue-only pile is a distinct, alarmable state, never the
    # same as a truly-empty one. Fail loud so orphans/residue are surfaced.
    residue="$(find "$ROOT/.pile" -mindepth 1 -maxdepth 1 -type f ! -name '.*' 2>/dev/null | wc -l | tr -d ' ')"
    if [ "${residue:-0}" -gt 0 ]; then
      fail "pile holds ${residue} non-.md file(s) but no .md brief and nothing shuffled — possible orphaned briefs or unreaped .bak residue in $ROOT/.pile (a .bak-only pile is NOT an empty pile; see #20)"
    fi
  fi
  check_jsonl "$ROOT/stack/.index.jsonl"
}

check_manifest() {
  mkdir -p "$ROOT/stack"
  check_jsonl "$ROOT/stack/.index.jsonl"
}

claim_item_metadata_value() {
  # gc.brief.slug / gc.brief.claim_result are written by claim-item onto ITS
  # OWN step bead, not onto finalize's bead — metadata_value() alone (which
  # only reads $GC_BEAD_ID, i.e. finalize's own bead when this runs as
  # finalize's check) can never see them. Cross-step lookup mirrors what
  # brief-shuffle.toml's process-item/finalize step descriptions already
  # specify in prose, and the same two-hop pattern used by gascity's own
  # design-review-approved.sh / implementation-review-approved.sh: resolve
  # this bead's gc.root_bead_id, then find the sibling claim-item step bead
  # for the same workflow run via that root id.
  key="$1"
  if [ -z "${GC_BEAD_ID:-}" ] || ! command -v gc >/dev/null 2>&1 || ! command -v jq >/dev/null 2>&1; then
    return 0
  fi
  root_id="$(gc bd show "$GC_BEAD_ID" --json 2>/dev/null |
    jq -r '.[0].metadata["gc.root_bead_id"] // empty' 2>/dev/null || true)"
  [ -n "$root_id" ] || return 0
  gc bd list --all --metadata-field "gc.root_bead_id=$root_id" --json --limit=0 2>/dev/null |
    jq -r --arg key "$key" '
      [.[] | select(.metadata["gc.step_ref"] == "brief-shuffle.claim-item")]
      | .[0].metadata[$key] // empty
    ' 2>/dev/null || true
}

check_staging_clear() {
  slug="$(claim_item_metadata_value "gc.brief.slug")"
  claim_result="$(claim_item_metadata_value "gc.brief.claim_result")"
  if [ "$claim_result" = "empty" ] || [ -z "$slug" ]; then
    # Empty-pile no-op route: nothing was ever claimed, nothing to clear.
    return 0
  fi
  if [ -e "$ROOT/.staging/$slug" ]; then
    fail "staging entry not cleared: $ROOT/.staging/$slug still exists after finalize"
  fi
}

check_stack_index_path() {
  configured="$(pack_asset brief-pipeline/paths.toml)"
  [ -f "$configured" ] || fail "missing paths.toml: $configured"
  grep -Eq '^manifest[[:space:]]*=[[:space:]]*"\.beads/briefs/stack/\.index\.jsonl"' "$configured" ||
    fail "paths.toml manifest must point at stack/.index.jsonl"
}

check_no_direct_stack_producers() {
  tmp="${TMPDIR:-/tmp}/brief-direct-stack-matches.$$"
  : > "$tmp"
  # FAIL CLOSED. This check SCANS, and a scan that cannot reach its root finds
  # nothing -- which is byte-for-byte what "no violations" looks like. Anchoring
  # the path is therefore not sufficient on its own: if resolution ever fails
  # again, refusing is the only honest answer, because reporting PASS here means
  # asserting something was verified that was never looked at.
  formulas_dir="$(pack_dir formulas)"
  [ -d "$formulas_dir" ] ||
    fail "cannot resolve the formulas/ directory (tried: $formulas_dir) — refusing rather than reporting a clean scan that never ran"
  find "$formulas_dir" -type f -name '*.toml' ! -name 'brief-shuffle.toml' |
  while IFS= read -r file; do
    # Match on the basename: $file is now absolute whenever the pack resolved,
    # so the old `formulas/<name>` prefix patterns would silently stop excluding
    # these four and report them as violations.
    case "${file##*/}" in
      brief-present-next.toml|brief-review-patrol.toml|brief-watchdog-refill.toml|brief-record-decision.toml)
        continue
        ;;
    esac
    grep -nE 'BRIEF_PATH="\{\{artifact_root\}\}/stack/|mkdir -p "\{\{artifact_root\}\}/stack"|stack/manifest\.jsonl|manifest\.jsonl' "$file" |
      sed "s|^|$file:|" >> "$tmp" || true
  done
  if [ -s "$tmp" ]; then
    cat "$tmp" >&2
    rm -f "$tmp"
    fail "producer formulas must deposit to .pile; only brief-shuffle writes stack"
  fi
  rm -f "$tmp"
}

check_decision_record() {
  # One-bead model (brief-system POLICY.md B2.2): the CANONICAL adjudication
  # record is the verdict recorded on the brief bead itself (type=decision,
  # closed). The decisions/*.toml file checked here is a redundancy channel
  # (B2.8: files are cache), not a separate decision bead.
  path="$(metadata_value "gc.brief.decision_path")"
  if [ -z "$path" ]; then
    path="$(find "$ROOT/decisions" -mindepth 1 -maxdepth 1 -type f -name '*.toml' 2>/dev/null | sort | head -n 1)"
  fi
  require_file "$path"
  require_text "$path" '^decision[[:space:]]*=' "decision record must set decision"
  # C2: pin source_bead so the approve dispatch path can never silently no-op.
  # The write-decision step always emits a source_bead line (possibly empty for
  # a legacy brief with no manifest source), so require the KEY to be present.
  require_text "$path" '^source_bead[[:space:]]*=' \
    "decision record must set source_bead (brief-decision-dispatch keys routing on it)"
}

check_watchdog_record() {
  require_dir "$ROOT"
  mkdir -p "$ROOT/watchdog"
}

check_test_execution_record() {
  path="$(metadata_value "gc.test.request_path")"
  if [ -z "$path" ]; then
    path="$(find "$ROOT/test-execution" -mindepth 1 -maxdepth 1 -type f -name '*.toml' 2>/dev/null | sort | head -n 1)"
  fi
  require_file "$path"
  require_text "$path" '^test_command[[:space:]]*=' "test execution request must set test_command"
  require_text "$path" '^risk[[:space:]]*=' "test execution request must set risk"
  if grep -Eq '^risk[[:space:]]*=[[:space:]]*"high"' "$path"; then
    require_text "$path" '^authorized_by[[:space:]]*=[[:space:]]*"the human adjudicator"' "high-risk test execution requires the human adjudicator authorization"
  fi
}

check_breadcrumb() {
  path="$(metadata_value "gc.experiment.breadcrumb_path")"
  if [ -z "$path" ]; then
    path="$(find "$ROOT/experiments" -path '*/breadcrumb.toml' -type f 2>/dev/null | sort | head -n 1)"
  fi
  require_file "$path"
  require_text "$path" '^source[[:space:]]*=' "breadcrumb must set source"
}

check_no_brainer_safety() {
  path="$(brief_path)"
  [ -n "$path" ] && [ -f "$path" ] || return 0
  if grep -Eq 'G5 Server-touching:[[:space:]]*(FAIL|BLOCKED)' "$path"; then
    fail "server-touching gate blocks no-brainer handling"
  fi
  if grep -Eq 'G5b User-skill-touching:[[:space:]]*(FAIL|BLOCKED)' "$path"; then
    fail "user-skill-touching gate blocks no-brainer handling"
  fi
}

check_no_brainer_classification_evidence() {
  path="$(brief_path)"
  require_file "$path"
  g9_lines="$(grep -E 'G9 No-brainer-filter:' "$path" || true)"
  [ -n "$g9_lines" ] || fail "missing G9 No-brainer-filter evidence in $path"
  g9_line_count="$(printf '%s\n' "$g9_lines" | grep -c . | tr -d ' ')"
  [ "$g9_line_count" = "1" ] ||
    fail "G9 evidence must contain exactly one G9 No-brainer-filter line in $path"
  g9_line="$g9_lines"
  printf '%s\n' "$g9_line" | grep -Eq 'G9 No-brainer-filter:[[:space:]]*PASS' ||
    fail "missing passing G9 No-brainer-filter evidence in $path"
  printf '%s\n' "$g9_line" | grep -Eq 'classified_at=[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z' ||
    fail "G9 evidence must set classified_at=<ISO-8601-utc> in $path"

  state_count="$(printf '%s\n' "$g9_line" | grep -Eo 'classifier_state=(known_no_brainer|known_non_no_brainer|candidate|capability_blocker|safety_blocked)' | wc -l | tr -d ' ')"
  [ "$state_count" = "1" ] ||
    fail "G9 evidence must contain exactly one classifier_state=known_no_brainer|known_non_no_brainer|candidate|capability_blocker|safety_blocked"

  state="$(printf '%s\n' "$g9_line" | grep -Eo 'classifier_state=(known_no_brainer|known_non_no_brainer|candidate|capability_blocker|safety_blocked)' | head -n 1 | cut -d= -f2)"
  case "$state" in
    known_no_brainer)
      printf '%s\n' "$g9_line" | grep -Eq 'category=[A-Za-z0-9._-]+' ||
        fail "known_no_brainer G9 evidence must set category in $path"
      category="$(printf '%s\n' "$g9_line" | grep -Eo 'category=[A-Za-z0-9._-]+' | head -n 1 | cut -d= -f2)"
      [ "$category" != "none" ] || fail "known_no_brainer G9 evidence must set a registry category, not category=none"
      registry="$(pack_asset brief-pipeline/no-brainer-categories.toml)"
      [ -f "$registry" ] || fail "missing no-brainer category registry: $registry"
      grep -Eq '^id[[:space:]]*=[[:space:]]*"'"$category"'"' "$registry" ||
        fail "known_no_brainer category is not in $registry: $category"
      printf '%s\n' "$g9_line" | grep -Eq 'stop_gates_clear=true' ||
        fail "known_no_brainer G9 evidence requires stop_gates_clear=true in $path"
      confidence="$(printf '%s\n' "$g9_line" | grep -Eo 'confidence=([0-9]+([.][0-9]+)?)' | head -n 1 | cut -d= -f2)"
      [ -n "$confidence" ] || fail "known_no_brainer G9 evidence must set confidence"
      awk -v c="$confidence" 'BEGIN { exit (c >= 0.85 ? 0 : 1) }' ||
        fail "known_no_brainer confidence must be >= 0.85"
      ;;
    known_non_no_brainer)
      printf '%s\n' "$g9_line" | grep -Eq 'reason=[^;]+' ||
        fail "known_non_no_brainer G9 evidence must set reason in $path"
      ;;
    candidate)
      printf '%s\n' "$g9_line" | grep -Eq 'proposed_registry_extension=[^;]+' ||
        fail "candidate G9 evidence must set proposed_registry_extension in $path"
      ;;
    capability_blocker)
      printf '%s\n' "$g9_line" | grep -Eq 'reason=[^;]+' ||
        fail "capability_blocker G9 evidence must set blocker reason in $path"
      ;;
    safety_blocked)
      printf '%s\n' "$g9_line" | grep -Eq 'stop_gate=(G5|G5b|L4)' ||
        fail "safety_blocked G9 evidence must name stop_gate=G5, G5b, or L4 in $path"
      ;;
  esac
}

# ---------------------------------------------------------------------------
# no-brainer auto-execution gate
#
# This subcommand is the LAST thing that runs before a classified no-brainer
# is auto-executed, so it is the only place a safety property can actually be
# enforced.  It used to be an advisory audit: it passed when the brief could
# not be resolved, it never looked at classifier evidence, it never saw
# `server_touching: true` in frontmatter, and it permitted execution whenever
# the N5 brake file was merely absent.
#
# Decision order (each step is terminal; every terminal decision is audited):
#
#   1. brief unresolvable                -> REFUSE  brief_unresolvable
#   2. stop gates (category E, G5b, L4)  -> REFUSE  stop_gate_*
#   3. classifier evidence               -> REFUSE  classifier_not_no_brainer
#                                                 / classifier_evidence_invalid
#   4. N5 kill switch reads `false`      -> REFUSE  kill_switch_engaged
#   5. DRY-RUN pinned or token unreadable-> REFUSE  dry_run_pinned /
#                                                   dry_run_token_invalid
#   6. otherwise                         -> PERMIT
#
# Steps 1-3 are evaluated BEFORE any switch or mode state is consulted, so a
# server-touching brief is refused regardless of how the city is configured.
#
# ARMED is the DEFAULT (POLICY.md N5 Adopted 2026-07-12, reaffirmed by the
# owner 2026-08-19): the mode tokens are brakes, not enablers, so an absent
# token proceeds.  What makes that default safe is steps 1-3 and the audit
# record, not the token -- this gate previously permitted a `server_touching:
# true` brief, an unresolvable path, a brief with no classifier evidence, and
# confidence=0.5, all of which now refuse.
#
# `brief-check.sh no-brainer-mode` reports the active mode; `no-brainer-disarm`
# pins DRY-RUN in one command from any rig, needing no authorization.
# ---------------------------------------------------------------------------

NB_CLASSIFIER_VERSION="mathcity.catch-no-brainer v0.4 (PRELIMINARY)"

nb_json_escape() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g' | tr -d '\n'
}

# absent | true | false | other
nb_flag_state() {
  if [ ! -f "$1" ]; then
    printf 'absent\n'
    return 0
  fi
  case "$(head -n 1 "$1" | tr -d '[:space:]')" in
    true) printf 'true\n' ;;
    false) printf 'false\n' ;;
    *) printf 'other\n' ;;
  esac
}

# absent | armed | disarmed | pin_expired | invalid
#
# The token is a BRAKE, not an enabler (paths.toml's standing language, and
# the owner's ruling of 2026-08-19): ARMED is the default, so an ABSENT token
# means auto-execute. Only a token that positively says `false` pins DRY-RUN.
#
#   absent       -> ARMED   (default; nobody has pinned this rig)
#   true         -> ARMED   (explicit, same effect as absent)
#   false        -> DRY-RUN (pinned by a deliberate act)
#   false+expires-> DRY-RUN until the instant given, then the ARMED default
#                   resumes on its own -- a TEMPORARY disarm, for pinning
#                   dry-run across a migration without having to remember to
#                   undo it
#   anything else-> DRY-RUN (invalid)
#
# `invalid` refusing is not an exception to brakes-not-enablers. An ABSENT
# token is "nobody configured this, take the default"; a MALFORMED token is
# "somebody tried to say something and it cannot be read", which is not the
# same claim. mctl's live-dispatch doctrine already resolves that ambiguity
# the same way -- an unknown control plane refuses rather than proceeds.
#
# `disarmed` stays distinct from `absent` in the audit trail and the mode
# report, so an operator can confirm a rollback actually landed rather than
# inferring it from silence.
nb_arm_state() {
  path="$1"
  if [ ! -f "$path" ]; then
    printf 'absent\n'
    return 0
  fi
  case "$(head -n 1 "$path" | tr -d '[:space:]')" in
    true) printf 'armed\n'; return 0 ;;
    false) : ;;
    *) printf 'invalid\n'; return 0 ;;
  esac
  # Only a `false` pin carries an expiry: it bounds how long DRY-RUN is held.
  expires="$(grep -Eo '^expires=[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z' "$path" | head -n 1 | cut -d= -f2)"
  if [ -n "$expires" ]; then
    now="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    # ISO-8601 UTC sorts lexicographically, so no date arithmetic is needed.
    if [ "$(printf '%s\n%s\n' "$expires" "$now" | sort | tail -n 1)" = "$now" ] &&
       [ "$now" != "$expires" ]; then
      printf 'pin_expired\n'
      return 0
    fi
  fi
  printf 'disarmed\n'
}

# Durable audit record.  N7 requires that an auto-execution be reconstructable
# afterwards; an unwritable sink therefore REFUSES rather than executing
# silently.
nb_audit() {
  nb_decision="$1"
  nb_reason="$2"
  nb_dir="$ROOT/decisions"
  nb_log="$nb_dir/no-brainer-execution.jsonl"
  if ! mkdir -p "$nb_dir" 2>/dev/null; then
    echo "brief-check: cannot create the no-brainer audit sink ($nb_dir) — refusing auto-execution; an unreconstructable execution is worse than a dry run" >&2
    exit 1
  fi
  if ! printf '{"recorded_at":"%s","gate":"no-brainer-execute-safety","mode":"%s","decision":"%s","reason":"%s","brief_path":"%s","classifier_version":"%s","classifier_state":"%s","category":"%s","confidence":"%s","classified_at":"%s","armed_city":"%s","armed_rig":"%s","kill_switch_city":"%s","kill_switch_rig":"%s","city_root":"%s","rig_root":"%s","agent":"%s"}\n' \
      "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
      "$(nb_json_escape "$NB_MODE")" \
      "$(nb_json_escape "$nb_decision")" \
      "$(nb_json_escape "$nb_reason")" \
      "$(nb_json_escape "$NB_BRIEF")" \
      "$(nb_json_escape "$NB_CLASSIFIER_VERSION")" \
      "$(nb_json_escape "$NB_STATE")" \
      "$(nb_json_escape "$NB_CATEGORY")" \
      "$(nb_json_escape "$NB_CONFIDENCE")" \
      "$(nb_json_escape "$NB_CLASSIFIED_AT")" \
      "$(nb_json_escape "$NB_ARM_CITY")" \
      "$(nb_json_escape "$NB_ARM_RIG")" \
      "$(nb_json_escape "$NB_KS_CITY")" \
      "$(nb_json_escape "$NB_KS_RIG")" \
      "$(nb_json_escape "$NB_CITY_ROOT")" \
      "$(nb_json_escape "$NB_RIG_ROOT")" \
      "$(nb_json_escape "${GC_AGENT:-unknown}")" \
      >> "$nb_log" 2>/dev/null; then
    echo "brief-check: cannot append to the no-brainer audit log ($nb_log) — refusing auto-execution" >&2
    exit 1
  fi
}

nb_refuse() {
  nb_audit "REFUSED" "$1"
  fail "$2"
}

# Resolve the city/rig roots and every switch and token into NB_* variables.
# Shared by the gate, the mode report, and the disarm command so all three
# answer from exactly the same state.
nb_resolve_mode() {
  NB_CITY_ROOT="${GC_CITY:-$HOME/gt}"
  NB_RIG_ROOT="${GC_RIG_ROOT:-}"
  if [ -z "$NB_RIG_ROOT" ]; then
    # BRIEF_ROOT is <rig_root>/.beads/briefs, so the rig root is two up.
    NB_RIG_ROOT="$(cd "$ROOT/../.." 2>/dev/null && pwd || true)"
  fi
  # Whether the rig root is REAL, tracked separately from whether it is set.
  # The fallback above cannot fail loudly -- `|| true` and a relative `.` both
  # yield a plausible-looking value -- so the kill-switch path then composed
  # against a non-rig directory, found no file, and read absence as "brake
  # off". An operator-engaged control was skipped while the gate reported
  # armed_and_gates_clear: a positive claim that it had been read.
  #
  # An unresolvable environment is NOT evidence that the brake is off, so
  # callers fail closed on this flag rather than inferring from the flag file.
  NB_RIG_ROOT_RESOLVED=yes
  if [ -z "$NB_RIG_ROOT" ] || [ ! -d "$NB_RIG_ROOT/.beads" ]; then
    NB_RIG_ROOT_RESOLVED=no
  fi
  NB_ARM_CITY_PATH="$NB_CITY_ROOT/.beads/no_brainer_auto_execute_armed"
  NB_ARM_RIG_PATH="$NB_RIG_ROOT/.beads/no_brainer_auto_execute_armed"
  NB_KS_CITY="$(nb_flag_state "$NB_CITY_ROOT/.beads/auto_merge_enabled")"
  NB_KS_RIG="$(nb_flag_state "$NB_RIG_ROOT/.beads/auto_merge_enabled")"
  NB_ARM_CITY="$(nb_arm_state "$NB_ARM_CITY_PATH")"
  NB_ARM_RIG="$(nb_arm_state "$NB_ARM_RIG_PATH")"
  # ARMED is the default. DRY-RUN needs a positive pin at either level --
  # either token saying `false` (unexpired) or being unreadable is enough, so
  # returning to DRY-RUN stays a one-place act. The N5 brakes are folded in
  # here for the REPORT only, so an operator asking "am I armed" is told no
  # when a kill switch is holding it; the gate still reports an engaged brake
  # under its own distinct reason code.
  NB_MODE="armed"
  case "$NB_ARM_CITY" in disarmed | invalid) NB_MODE="dry-run" ;; esac
  case "$NB_ARM_RIG" in disarmed | invalid) NB_MODE="dry-run" ;; esac
  if [ "$NB_KS_CITY" = "false" ] || [ "$NB_KS_RIG" = "false" ]; then
    NB_MODE="dry-run"
  fi
  # Same treatment when the rig brake could not be READ at all. The report
  # answers "will something auto-execute here", and the answer is no -- the
  # gate refuses with kill_switch_unreadable. Reporting ARMED would be the
  # requirement-2 failure on its own: a banner asserting a cleared brake,
  # printed immediately before a refusal saying the brake was never read.
  if [ "$NB_RIG_ROOT_RESOLVED" != "yes" ]; then
    NB_MODE="dry-run"
  fi
}

# `brief-check.sh no-brainer-mode` — the straight answer to "which mode is
# this city in right now, and how do I change it?".  Read-only: it writes
# nothing, audits nothing, and always exits 0, so it is safe to run anywhere.
report_no_brainer_mode() {
  nb_resolve_mode
  if [ "$NB_MODE" = "armed" ]; then
    echo "no-brainer auto-execution mode: ARMED"
    echo "  a classified no-brainer WILL be executed without being surfaced."
    echo "  the classifier making that call is $NB_CLASSIFIER_VERSION."
    if [ "$NB_ARM_CITY" = "absent" ] && [ "$NB_ARM_RIG" = "absent" ]; then
      echo "  ARMED is the DEFAULT — this rig is armed because no token pins it,"
      echo "  not because anyone configured it. That is the intended semantics."
    fi
  else
    echo "no-brainer auto-execution mode: DRY-RUN"
    echo "  no-brainers are classified and recorded; nothing is executed."
  fi
  echo ""
  echo "  city mode token    $NB_ARM_CITY_PATH  [$NB_ARM_CITY]"
  echo "  rig mode token     $NB_ARM_RIG_PATH  [$NB_ARM_RIG]"
  echo "  city kill switch   $NB_CITY_ROOT/.beads/auto_merge_enabled  [$NB_KS_CITY]"
  echo "  rig kill switch    $NB_RIG_ROOT/.beads/auto_merge_enabled  [$NB_KS_RIG]"
  case "$NB_ARM_CITY$NB_ARM_RIG" in
    *disarmed*) echo "  (dry-run is explicitly pinned — someone put it there, it did not lapse)" ;;
    *invalid*) echo "  (a mode token is unreadable — holding DRY-RUN until it is fixed or removed)" ;;
    *pin_expired*) echo "  (a dry-run pin has expired — the ARMED default resumed on its own)" ;;
  esac
  echo ""
  echo "  to pin DRY-RUN (always allowed, no authorization, takes effect immediately):"
  echo "    brief-check.sh no-brainer-disarm"
  echo "  to pin DRY-RUN only until a deadline, then auto-resume ARMED:"
  # printf '%s\n', not echo: these lines contain literal \n that must survive.
  printf '%s\n' "    printf 'false\\nexpires=<ISO-8601-utc>\\n' > $NB_ARM_RIG_PATH"
  echo "  to return to ARMED:"
  echo "    rm -f $NB_ARM_CITY_PATH $NB_ARM_RIG_PATH   # absent = armed default"
  echo ""
  printf '{"mode":"%s","armed_city":"%s","armed_rig":"%s","kill_switch_city":"%s","kill_switch_rig":"%s","classifier_version":"%s"}\n' \
    "$NB_MODE" "$NB_ARM_CITY" "$NB_ARM_RIG" "$NB_KS_CITY" "$NB_KS_RIG" \
    "$(nb_json_escape "$NB_CLASSIFIER_VERSION")"
}

# `brief-check.sh no-brainer-disarm` — the recovery path, deliberately a
# single command.  Under an ARMED default this is the control that matters:
# it is the one an operator reaches for when something is going wrong, so it
# takes no authorization, needs no argument, and works from any rig.  Going
# back to ARMED is a deliberate `rm` of the tokens rather than a helper, so
# the easy direction is always the safe one.
disarm_no_brainer() {
  nb_resolve_mode
  # #94, and the SAME root cause as the fail-permissive kill switch: when the
  # rig root does not resolve, NB_ARM_RIG_PATH composes against whatever the
  # cwd happens to be (or filesystem root), and disarm cheerfully writes a
  # token there. The operator is then told dry-run is pinned while the rig
  # token sits in an unrelated directory -- a phantom brake, which is worse
  # than no brake because it reads as one.
  #
  # The CITY token is still written: its path is well-defined from GC_CITY,
  # it pins dry-run globally, and keeping the safe direction easy matters more
  # than symmetry. Only the rig token is withheld, and it is said out loud.
  nb_disarm_tokens="$NB_ARM_CITY_PATH"
  if [ "$NB_RIG_ROOT_RESOLVED" = "yes" ]; then
    nb_disarm_tokens="$nb_disarm_tokens $NB_ARM_RIG_PATH"
  fi
  for nb_token in $nb_disarm_tokens; do
    nb_token_dir="$(dirname "$nb_token")"
    if ! mkdir -p "$nb_token_dir" 2>/dev/null; then
      fail "cannot create $nb_token_dir to pin dry-run"
    fi
    if ! printf 'false\n' > "$nb_token" 2>/dev/null; then
      fail "cannot write $nb_token to pin dry-run"
    fi
  done
  if [ "$NB_RIG_ROOT_RESOLVED" = "yes" ]; then
    echo "no-brainer auto-execution pinned to DRY-RUN (both tokens now read false)."
    echo "  $NB_ARM_CITY_PATH"
    echo "  $NB_ARM_RIG_PATH"
  else
    echo "no-brainer auto-execution pinned to DRY-RUN via the CITY token only."
    echo "  $NB_ARM_CITY_PATH"
    echo "  rig token NOT written: the rig root did not resolve, so there is no"
    echo "  rig to pin. Set GC_RIG_ROOT or run from inside the rig to pin it too."
  fi
  echo "verify with: brief-check.sh no-brainer-mode"
}

check_no_brainer_execute_safety() {
  NB_MODE="dry-run"
  NB_STATE=""
  NB_CATEGORY=""
  NB_CONFIDENCE=""
  NB_CLASSIFIED_AT=""

  nb_resolve_mode
  if [ "$NB_MODE" = "armed" ]; then
    echo "brief-check: no-brainer auto-execution is ARMED for $NB_RIG_ROOT. The classifier deciding this is $NB_CLASSIFIER_VERSION — PRELIMINARY. Return to dry-run at any time with: brief-check.sh no-brainer-disarm" >&2
  fi

  # --- 1. the artifact itself -------------------------------------------
  NB_BRIEF="$(brief_path)"
  if [ -z "$NB_BRIEF" ] || [ ! -f "$NB_BRIEF" ]; then
    nb_refuse "brief_unresolvable" \
      "cannot resolve the brief under evaluation (${NB_BRIEF:-<empty>}) — refusing auto-execution; safety cannot be asserted about an artifact that was never read"
  fi

  # --- 2. stop gates, before any switch or arming state ------------------
  # N3/S7: category E (server-touching) and G5b (user-skill-touching) are
  # stop-gates, not preferences.  Frontmatter is checked as well as the gate
  # token: brief-prep's Override 1 is expressed as `server_touching: true`,
  # and the token-only check let that shape through.
  if grep -Eq '^server_touching:[[:space:]]*true\b' "$NB_BRIEF" ||
     grep -Eq 'G5 Server-touching:[[:space:]]*(FAIL|BLOCKED)' "$NB_BRIEF"; then
    nb_refuse "stop_gate_server_touching" \
      "category E / server-touching brief — auto-execution is forbidden regardless of kill-switch or arming state (N3, S7); route to explicit adjudication"
  fi
  if grep -Eq '^user_skill_touching_override:[[:space:]]*true\b' "$NB_BRIEF" ||
     grep -Eq 'G5b User-skill-touching:[[:space:]]*(FAIL|BLOCKED)' "$NB_BRIEF"; then
    nb_refuse "stop_gate_user_skill_touching" \
      "user-skill-touching brief — auto-execution is forbidden regardless of kill-switch or arming state (N3, G5b); route to explicit adjudication"
  fi

  # --- 3. classifier evidence -------------------------------------------
  nb_g9="$(grep -E 'G9 No-brainer-filter:' "$NB_BRIEF" || true)"
  if [ -z "$nb_g9" ] || [ "$(printf '%s\n' "$nb_g9" | grep -c .)" != "1" ]; then
    nb_refuse "classifier_evidence_invalid" \
      "auto-execution requires exactly one G9 No-brainer-filter evidence line in $NB_BRIEF"
  fi
  NB_STATE="$(printf '%s\n' "$nb_g9" | grep -Eo 'classifier_state=[a-z_]+' | head -n 1 | cut -d= -f2)"
  NB_CATEGORY="$(printf '%s\n' "$nb_g9" | grep -Eo 'category=[A-Za-z0-9._-]+' | head -n 1 | cut -d= -f2)"
  NB_CONFIDENCE="$(printf '%s\n' "$nb_g9" | grep -Eo 'confidence=[0-9]+([.][0-9]+)?' | head -n 1 | cut -d= -f2)"
  NB_CLASSIFIED_AT="$(printf '%s\n' "$nb_g9" | grep -Eo 'classified_at=[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z' | head -n 1 | cut -d= -f2)"

  if [ "$NB_STATE" = "safety_blocked" ]; then
    nb_refuse "stop_gate_classifier_safety_blocked" \
      "classifier recorded classifier_state=safety_blocked — auto-execution is forbidden (N3)"
  fi
  if [ -n "$NB_STATE" ] && [ "$NB_STATE" != "known_no_brainer" ]; then
    nb_refuse "classifier_not_no_brainer" \
      "classifier_state=$NB_STATE is not an auto-executable classification; only known_no_brainer executes"
  fi
  if [ -z "$NB_STATE" ] || [ -z "$NB_CLASSIFIED_AT" ]; then
    nb_refuse "classifier_evidence_invalid" \
      "G9 evidence must record classifier_state and classified_at=<ISO-8601-utc> in $NB_BRIEF"
  fi
  if ! printf '%s\n' "$nb_g9" | grep -Eq 'G9 No-brainer-filter:[[:space:]]*PASS'; then
    nb_refuse "classifier_evidence_invalid" "G9 No-brainer-filter evidence does not read PASS in $NB_BRIEF"
  fi
  if ! printf '%s\n' "$nb_g9" | grep -Eq 'stop_gates_clear=true'; then
    nb_refuse "classifier_evidence_invalid" "known_no_brainer G9 evidence requires stop_gates_clear=true in $NB_BRIEF"
  fi
  nb_registry="$(pack_asset brief-pipeline/no-brainer-categories.toml)"
  if [ -z "$NB_CATEGORY" ] || [ "$NB_CATEGORY" = "none" ] || [ ! -f "$nb_registry" ] ||
     ! grep -Eq '^id[[:space:]]*=[[:space:]]*"'"$NB_CATEGORY"'"' "$nb_registry"; then
    nb_refuse "classifier_evidence_invalid" \
      "known_no_brainer category '${NB_CATEGORY:-<unset>}' is not present in $nb_registry"
  fi
  if [ -z "$NB_CONFIDENCE" ] || ! awk -v c="$NB_CONFIDENCE" 'BEGIN { exit (c >= 0.85 ? 0 : 1) }'; then
    nb_refuse "classifier_evidence_invalid" \
      "known_no_brainer confidence '${NB_CONFIDENCE:-<unset>}' is below the N8 auto-execution threshold of 0.85"
  fi

  # --- 4. N5 kill-switch hierarchy (retained brakes) ---------------------
  # Fail CLOSED when the rig-level brake could not be read at all. Permitting
  # here would treat "I could not look" as "I looked and it was off", and the
  # reason string would assert a read that never happened.
  if [ "$NB_RIG_ROOT_RESOLVED" != "yes" ]; then
    nb_refuse "kill_switch_unreadable" \
      "rig root could not be resolved (GC_RIG_ROOT and BRIEF_ROOT unset, and '${NB_RIG_ROOT:-<empty>}' is not a rig) — the rig kill switch was NOT read, so auto-execution is refused; set GC_RIG_ROOT or run from inside the rig"
  fi
  if [ "$NB_KS_CITY" = "false" ] || [ "$NB_KS_RIG" = "false" ]; then
    nb_refuse "kill_switch_engaged" \
      "kill switch ENGAGED (city=$NB_KS_CITY rig=$NB_KS_RIG) — auto-execution halted (N5); route brief to the pile in compact form"
  fi

  # --- 5. mode: ARMED is the default; DRY-RUN must be pinned -------------
  # An explicit pin is reported distinguishably from a malformed token, so a
  # rollback is confirmable rather than inferred from silence.
  if [ "$NB_ARM_CITY" = "disarmed" ] || [ "$NB_ARM_RIG" = "disarmed" ]; then
    nb_refuse "dry_run_pinned" \
      "no-brainer auto-execution is pinned to DRY-RUN (city=$NB_ARM_CITY rig=$NB_ARM_RIG) — classification recorded, nothing executed"
  fi
  if [ "$NB_ARM_CITY" = "invalid" ] || [ "$NB_ARM_RIG" = "invalid" ]; then
    nb_refuse "dry_run_token_invalid" \
      "a no-brainer mode token is unreadable (city=$NB_ARM_CITY rig=$NB_ARM_RIG) — an unreadable instruction is not consent to execute; write `true` or `false`, or remove the file to take the ARMED default"
  fi

  # --- 6. permitted ------------------------------------------------------
  nb_audit "PERMITTED" "armed_and_gates_clear"
}

check_archive_sweep_record() {
  require_dir "$ROOT"
  mkdir -p "$ROOT/archive"
}

check_server_touching_safety() {
  path="$(brief_path)"
  [ -n "$path" ] && [ -f "$path" ] || return 0
  # Mechanical check: frontmatter key server_touching: true blocks auto-dispatch.
  # This is the machine form of brief-prep §"Safety overrides" Override 1 and
  # present-it §"Compact form" NEVER rules.  No judgment applied here; any match
  # must route to the human adjudicator for explicit adjudication.
  if grep -Eq '^server_touching:[[:space:]]*true\b' "$path"; then
    fail "server_touching: true — brief requires explicit the human adjudicator adjudication; auto-dispatch and auto-approval are forbidden"
  fi
  # Also block if the gate evidence section records the gate as failing/blocked.
  if grep -Eq 'G5 Server-touching:[[:space:]]*(FAIL|BLOCKED)' "$path"; then
    fail "G5 Server-touching gate is FAIL/BLOCKED — brief requires the human adjudicator adjudication"
  fi
}


check_file_or_sendback_log() {
  log="$ROOT/decisions/file-or-sendback.jsonl"
  require_file "$log"
  check_jsonl "$log"
  if command -v jq >/dev/null 2>&1; then
    last="$(tail -n 1 "$log")"
    [ -n "$last" ] || fail "empty route log: $log"
    printf '%s\n' "$last" | jq -e '
      (.bead_id | type == "string")
      and (.brief_slug | type == "string" and length > 0)
      and (.decision | type == "string" and length > 0)
      and (.choice == "FILE" or .choice == "SEND-BACK")
      and (.reason | type == "string" and length > 0)
      and (.timestamp | type == "string" and length > 0)
      and (.agent_id | type == "string" and length > 0)
      and (if .choice == "FILE"
           then (.target_bead_id | type == "string" and length > 0)
           else true end)
    ' >/dev/null 2>&1 ||
      fail "route log last entry missing required keys or invalid choice: $log"
  fi
}

check_producer_contract() {
  path="$(brief_path)"
  require_file "$path"
  require_text "$path" '^producer_contract:[[:space:]]*brief-producer\.v1\b' "brief missing producer_contract"
  require_text "$path" '^source_formula:[[:space:]]*[A-Za-z0-9._-]+' "brief missing source_formula"
  require_text "$path" '^source_step:[[:space:]]*[A-Za-z0-9._-]+' "brief missing source_step"
}

check_producer_repair_self_exclusion() {
  path="$(brief_path)"
  require_file "$path"
  require_text "$path" '^producer_contract:[[:space:]]*brief-producer-repair\.v1\b' "repair brief missing self-exclusion producer_contract"
  require_text "$path" '^repair_source_formula:[[:space:]]*"?[A-Za-z0-9._-]+"?[[:space:]]*$' "repair brief missing repair_source_formula"
  require_text "$path" '^repair_failed_gate:[[:space:]]*"?[A-Za-z0-9._-]+"?[[:space:]]*$' "repair brief missing repair_failed_gate"
  require_text "$path" '^repair_failure_fingerprint:[[:space:]]*"?[A-Za-z0-9._-]+"?[[:space:]]*$' "repair brief missing repair_failure_fingerprint"
}

case "$COMMAND" in
  test-evidence) check_test_evidence ;;
  mechanical-gates) check_mechanical_gates ;;
  disposition) check_disposition ;;
  pile-entry) check_pile_entry ;;
  pile-nonempty) check_pile_nonempty ;;
  shuffle-result) check_shuffle_result ;;
  manifest-current) check_manifest ;;
  staging-clear) check_staging_clear ;;
  stack-index-path) check_stack_index_path ;;
  no-direct-stack-producers) check_no_direct_stack_producers ;;
  decision-record) check_decision_record ;;
  watchdog-record) check_watchdog_record ;;
  test-execution-record) check_test_execution_record ;;
  breadcrumb) check_breadcrumb ;;
  no-brainer-safety) check_no_brainer_safety ;;
  no-brainer-classification-evidence) check_no_brainer_classification_evidence ;;
  no-brainer-execute-safety) check_no_brainer_execute_safety ;;
  no-brainer-mode) report_no_brainer_mode ;;
  no-brainer-disarm) disarm_no_brainer ;;
  server-touching-safety) check_server_touching_safety ;;
  archive-sweep-record) check_archive_sweep_record ;;
  file-or-sendback-log) check_file_or_sendback_log ;;
  producer-contract) check_producer_contract ;;
  producer-repair-self-exclusion) check_producer_repair_self_exclusion ;;
  decision-profile) check_decision_profile ;;
  lost-bead-filter-profile) check_lost_bead_filter_profile ;;
  producer-repair-profile) check_producer_repair_profile ;;
  brief-quality-failure-record) check_brief_quality_failure_record ;;
  *) fail "unknown check: $COMMAND" ;;
esac
