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

require_text() {
  path="$1"
  pattern="$2"
  message="$3"
  grep -Eq "$pattern" "$path" || fail "$message in $path"
}

require_gate() {
  path="$1"
  key="$2"
  if grep -Eq "$key:[[:space:]]*(FAIL|BLOCKED)\\b" "$path"; then
    fail "$key is failing or blocked"
  fi
  grep -Eq "$key:[[:space:]]*(PASS|N/A)\\b" "$path" ||
    fail "$key must be PASS or N/A"
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
  require_gate "$path" "G14 Test-execution-silent"
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
  configured="assets/brief-pipeline/paths.toml"
  [ -f "$configured" ] || fail "missing paths.toml: $configured"
  grep -Eq '^manifest[[:space:]]*=[[:space:]]*"\.beads/briefs/stack/\.index\.jsonl"' "$configured" ||
    fail "paths.toml manifest must point at stack/.index.jsonl"
}

check_no_direct_stack_producers() {
  tmp="${TMPDIR:-/tmp}/brief-direct-stack-matches.$$"
  : > "$tmp"
  find formulas -type f -name '*.toml' ! -name 'brief-shuffle.toml' |
  while IFS= read -r file; do
    case "$file" in
      formulas/brief-present-next.toml|formulas/brief-review-patrol.toml|formulas/brief-watchdog-refill.toml|formulas/brief-record-decision.toml)
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
      registry="assets/brief-pipeline/no-brainer-categories.toml"
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

check_no_brainer_execute_safety() {
  check_no_brainer_safety
  # N5 kill-switch hierarchy (POLICY.md N5, Adopted 2026-07-12): auto-execute
  # is the DEFAULT. A kill switch halts automation only when its flag file
  # EXISTS and reads `false`; absent or `true` proceeds. Check order:
  # city-wide first, then rig-level (paths.toml: kill_switch_city,
  # kill_switch_rig). Supersedes the opt-in ALLOW_NO_BRAINER_AUTO_EXECUTE
  # existence check.
  city_flag="${GC_CITY:-$HOME/gt}/.beads/auto_merge_enabled"
  rig_root="${GC_RIG_ROOT:-}"
  if [ -z "$rig_root" ]; then
    # BRIEF_ROOT is <rig_root>/.beads/briefs, so the rig root is two up.
    rig_root="$(cd "$ROOT/../.." 2>/dev/null && pwd || true)"
  fi
  rig_flag="$rig_root/.beads/auto_merge_enabled"
  for flag in "$city_flag" "$rig_flag"; do
    [ -f "$flag" ] || continue
    if [ "$(head -n 1 "$flag" | tr -d '[:space:]')" = "false" ]; then
      fail "kill switch ENGAGED ($flag reads false) — auto-execution halted (N5); route brief to the pile in compact form"
    fi
  done
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
  server-touching-safety) check_server_touching_safety ;;
  archive-sweep-record) check_archive_sweep_record ;;
  file-or-sendback-log) check_file_or_sendback_log ;;
  producer-contract) check_producer_contract ;;
  producer-repair-self-exclusion) check_producer_repair_self_exclusion ;;
  *) fail "unknown check: $COMMAND" ;;
esac
