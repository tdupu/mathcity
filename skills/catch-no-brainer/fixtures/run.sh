#!/usr/bin/env bash
# catch-no-brainer v0.2 fixture harness.
# Implements the SKILL.md classification rules over the 9 fixture briefs.
# Pass-bar: all 9 fixtures classify with the expected verdict shape. Exit 0 = PASS.
set -euo pipefail

cd "$(dirname "$0")"

json_escape() {
  local s="$1"
  s=${s//\\/\\\\}
  s=${s//\"/\\\"}
  s=${s//$'\n'/ }
  printf '%s' "$s"
}

classify_brief() {
  local f="$1"
  local fm
  fm=$(awk '/^---$/{c++; next} c==1{print}' "$f")

  yaml_get() { echo "$fm" | grep -E "^$1:" | head -1 | sed -E "s/^$1:[[:space:]]*//"; }
  yaml_list() { echo "$fm" | awk -v k="$1:" 'index($0,k)==1{i=1;next} /^[A-Za-z_]+:/{i=0} i && /^[[:space:]]+- /{sub(/^[[:space:]]+- /,""); print}'; }

  local branch verdict parent_closed parent_super downstream files cap_block status existing_state merged_commit exec_proof
  branch=$(yaml_get branch)
  verdict=$(yaml_get verdict)
  parent_closed=$(yaml_get parent_bead_closed)
  parent_super=$(yaml_get parent_bead_supersession_documented)
  downstream=$(yaml_get downstream_beads_reference)
  files=$(yaml_list diff_files)
  cap_block=$(yaml_get capability_blocker)
  status=$(yaml_get status)
  existing_state=$(yaml_get existing_state)
  merged_commit=$(yaml_get merged_commit)
  exec_proof=$(yaml_get execution_proof)

  # Step 1: server-touching (he-xkq3 G5 fires before G9)
  local server_re='magma/scripts/dispatch\.sh|magma/make/dispatch/|^gt-dolt|^gt-upf|\.gc/daemon|\.dolt-data/|\.gc/agent-bridge/|aia-s27'
  if echo "$files" | grep -E "$server_re" >/dev/null 2>&1; then
    printf '{"brief_path":"%s","bead_id":null,"no_brainer":false,"category":null,"reason":"cat-E-server-touching","compact_eligible":false,"confidence":1.0,"proposed_registry_extension":null,"requires_human_adjudication":false,"classified_at":"2026-07-24T00:00:00Z"}\n' "$f"
    return 0
  fi

  # Step 2: user-skill-touching (as-wjv SAFETY OVERRIDE)
  local userskill_re='\.claude/skills/|repos/agent-skills/skills/'
  if echo "$files" | grep -E "$userskill_re" >/dev/null 2>&1; then
    printf '{"brief_path":"%s","bead_id":null,"no_brainer":false,"category":null,"reason":"user-skill-touching-override","compact_eligible":false,"confidence":1.0,"proposed_registry_extension":null,"requires_human_adjudication":false,"classified_at":"2026-07-24T00:00:00Z"}\n' "$f"
    return 0
  fi

  # Step 3: capability-blocker shape
  if [[ -n "$cap_block" ]]; then
    reason="$(json_escape "resolve $cap_block")"
    printf '{"brief_path":"%s","bead_id":null,"no_brainer":false,"category":"capability-blocker","reason":"%s","compact_eligible":false,"confidence":1.0,"proposed_registry_extension":null,"requires_human_adjudication":false,"classified_at":"2026-07-24T00:00:00Z"}\n' "$f" "$reason"
    return 0
  fi

  # Step 4: he-lele 5-criterion
  local branch_ok=0 files_ok=1
  [[ "$branch" =~ ^(polecat|nux|[a-z]+-prefix)/ ]] && branch_ok=1
  if echo "$files" | grep -E '^(magma|latex|notes\.tex|DATA|configs)' >/dev/null 2>&1; then files_ok=0; fi
  if [[ "$branch_ok" == "1" ]] \
      && [[ "$parent_closed" == "true" ]] \
      && [[ "$parent_super" == "true" ]] \
      && [[ "$files_ok" == "1" ]] \
      && [[ "$downstream" == "false" ]] \
      && [[ "$verdict" =~ ^(DELETE|INVESTIGATE)$ ]]; then
    printf '{"brief_path":"%s","bead_id":null,"no_brainer":true,"category":"stale-branch","reason":null,"compact_eligible":true,"confidence":0.9,"proposed_registry_extension":null,"requires_human_adjudication":false,"classified_at":"2026-07-24T00:00:00Z"}\n' "$f"
    return 0
  fi

  # Step 5: DEFER-ratify-existing-HELD
  # Trigger: (a) verdict is DEFER; (b) status/existing_state indicates already HELD; (c) only action is ratification
  if [[ "$verdict" == "DEFER" ]] && ([[ "$status" == "HELD" ]] || [[ "$existing_state" == "HELD" ]]); then
    printf '{"brief_path":"%s","bead_id":null,"no_brainer":true,"category":"defer-ratify-held","reason":null,"compact_eligible":true,"confidence":0.9,"proposed_registry_extension":null,"requires_human_adjudication":false,"classified_at":"2026-07-24T00:00:00Z"}\n' "$f"
    return 0
  fi

  # Step 6: CLOSE-DONE-cited-commit
  # Trigger: (a) verdict is CLOSE with reason DONE; (b) merged_commit field is set (SHA evidence)
  if [[ "$verdict" == "CLOSE" ]] && [[ -n "$merged_commit" ]]; then
    printf '{"brief_path":"%s","bead_id":null,"no_brainer":true,"category":"close-done-cited-commit","reason":null,"compact_eligible":true,"confidence":0.9,"proposed_registry_extension":null,"requires_human_adjudication":false,"classified_at":"2026-07-24T00:00:00Z"}\n' "$f"
    return 0
  fi

  # Step 7: EXECUTION-CONFIRMATION-with-cryptographic-proof
  # Trigger: (a) verdict is CONFIRM; (b) execution_proof field is set (commit SHA, artifact, etc.)
  if [[ "$verdict" == "CONFIRM" ]] && [[ -n "$exec_proof" ]]; then
    printf '{"brief_path":"%s","bead_id":null,"no_brainer":true,"category":"execution-confirmation-proof","reason":null,"compact_eligible":true,"confidence":0.9,"proposed_registry_extension":null,"requires_human_adjudication":false,"classified_at":"2026-07-24T00:00:00Z"}\n' "$f"
    return 0
  fi

  # Step 8: novel shape (proposed registry extension is one-line synthesis from the failing criteria)
  local why="branch=$branch verdict=$verdict supersession=$parent_super"
  proposed="$(json_escape "new shape candidate: $why")"
  printf '{"brief_path":"%s","bead_id":null,"no_brainer":"candidate","category":null,"reason":null,"compact_eligible":false,"confidence":0.5,"proposed_registry_extension":"%s","requires_human_adjudication":true,"classified_at":"2026-07-24T00:00:00Z"}\n' "$f" "$proposed"
}

expected_for() {
  case "$1" in
    stale-branch-A.md|stale-branch-B.md|stale-branch-C.md) echo '"no_brainer":true,"category":"stale-branch"';;
    server-touching.md) echo '"reason":"cat-E-server-touching"';;
    novel-shape.md) echo '"no_brainer":"candidate"';;
    capability-blocker.md) echo '"category":"capability-blocker"';;
    defer-ratify-held.md) echo '"no_brainer":true,"category":"defer-ratify-held"';;
    close-done-cited-commit.md) echo '"no_brainer":true,"category":"close-done-cited-commit"';;
    execution-confirmation-proof.md) echo '"no_brainer":true,"category":"execution-confirmation-proof"';;
    *) echo '???';;
  esac
}

fail=0
echo "=== catch-no-brainer v0.2 fixture run ==="
for f in stale-branch-A.md stale-branch-B.md stale-branch-C.md server-touching.md novel-shape.md capability-blocker.md defer-ratify-held.md close-done-cited-commit.md execution-confirmation-proof.md; do
  out=$(classify_brief "$f")
  exp=$(expected_for "$f")
  echo "$out"
  if ! echo "$out" | grep -Eq '"confidence":[0-9]+(\.[0-9]+)?'; then
    echo "  FAIL: $f missing confidence"
    fail=1
  fi
  if command -v jq >/dev/null 2>&1; then
    if ! echo "$out" | jq -e '
      (.brief_path | type == "string" and length > 0)
      and (.no_brainer == true or .no_brainer == false or .no_brainer == "candidate")
      and (.compact_eligible | type == "boolean")
      and (.confidence | type == "number")
      and (.classified_at | test("^[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z$"))
      and (.requires_human_adjudication | type == "boolean")
      and (has("category") and has("reason") and has("proposed_registry_extension"))
    ' >/dev/null; then
      echo "  FAIL: $f schema invalid"
      fail=1
    fi
  fi
  if echo "$out" | grep -F "$exp" >/dev/null; then
    echo "  PASS: $f"
  else
    echo "  FAIL: $f"
    echo "  expected substring: $exp"
    fail=1
  fi
done

if ! GC_BRIEF_PATH="valid-g9-evidence.md" sh ../../../assets/scripts/checks/brief-no-brainer-classification-evidence.sh; then
  echo "  FAIL: valid-g9-evidence.md"
  fail=1
else
  echo "  PASS: valid-g9-evidence.md"
fi

echo ""
if [[ $fail -ne 0 ]]; then
  echo "FIXTURE FAILED (one or more cases misclassified)"
  exit 1
fi
echo "ALL 9 FIXTURES PASSED"
exit 0
