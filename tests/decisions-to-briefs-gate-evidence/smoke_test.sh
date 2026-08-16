#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SKILL="$ROOT/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md"

require_text() {
  local pattern="$1"
  local message="$2"
  if ! rg -q -- "$pattern" "$SKILL"; then
    printf 'decisions-to-briefs gate evidence check failed: %s\n' "$message" >&2
    exit 1
  fi
}

require_text '## Gate Evidence' 'skill must require a Gate Evidence section'
require_text 'gate_profile: decision' 'skill must name the decision gate profile'
require_text 'G5 Server-touching:' 'decision profile must include G5 evidence'
require_text 'G5b User-skill-touching:' 'decision profile must include G5b evidence'
require_text 'G8 Brief-record:' 'decision profile must include G8 evidence'
require_text 'BEFORE deposit' 'G8 evidence must require the brief bead before pile deposit'
require_text 'G9 No-brainer-filter:' 'decision profile must include G9 evidence'
require_text 'classifier_state=' 'G9 evidence must be machine-readable'
require_text 'classified_at=<YYYY-MM-DDTHH:MM:SSZ>' 'G9 evidence must require a UTC timestamp'
require_text 'G11 Breadcrumb:' 'decision profile must include G11 evidence'
require_text 'G12 Auto-merge-kill-switch:' 'decision profile must include G12 evidence'
require_text 'G13 Stale-claim:' 'decision profile must include G13 evidence'

if rg -q 'PASS\|N/A|PASSED' "$SKILL"; then
  printf 'decisions-to-briefs gate evidence check failed: template must not contain PASS|N/A or PASSED tokens\n' >&2
  exit 1
fi

printf 'decisions-to-briefs gate evidence check: ok\n'
