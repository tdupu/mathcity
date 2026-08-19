#!/bin/sh
# Verify that MathCity can see the imported Superpowers capability pack.
set -eu

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

# Sibling-pack lookups must resolve against the PRIMARY checkout, not against
# whatever tree this script happens to run from. When the test runs inside a git
# worktree (e.g. .claude/worktrees/<name>), $ROOT is the worktree root and
# "$ROOT/.." points at the worktree container, not at the repo's parent
# directory -- so the sibling pack is not found. The git common dir always lives
# in the primary checkout, so its parent is the primary checkout root in both
# the worktree and non-worktree cases. Fall back to $ROOT outside a git repo.
PACK_HOME="$ROOT"
if common_dir="$(git -C "$ROOT" rev-parse --path-format=absolute --git-common-dir 2>/dev/null)" \
  && [ -n "$common_dir" ] && [ -d "$common_dir" ]; then
  PACK_HOME="$(cd "$common_dir/.." && pwd)"
fi

if [ -n "${SUPERPOWERS_PACK:-}" ]; then
  SUPERPOWERS_ROOT="$SUPERPOWERS_PACK"
else
  SUPERPOWERS_ROOT="$PACK_HOME/../gascity-packs/superpowers"
fi

# No baked-in default city path: a machine-specific absolute path must not live
# in a tracked file (subdomains/dev/POLICY.md P1.10). Only the opt-in live check
# needs a city, and it requires GC_CITY_PATH explicitly.
CITY="${GC_CITY_PATH:-}"
RIG="${GC_RIG_NAME:-hecke}"

fail() {
  echo "I'm sorry, I can't do that - $1" >&2
  exit 1
}

has_line() {
  printf '%s\n' "$1" | grep -Fx -- "$2" >/dev/null
}

[ -f "$ROOT/pack.toml" ] || fail "missing $ROOT/pack.toml"
[ -d "$SUPERPOWERS_ROOT" ] || fail "missing Superpowers pack at $SUPERPOWERS_ROOT"
[ -f "$SUPERPOWERS_ROOT/pack.toml" ] || fail "missing Superpowers pack.toml"

python3 - "$ROOT/pack.toml" <<'PY'
import sys
import tomllib

with open(sys.argv[1], "rb") as handle:
    data = tomllib.load(handle)

imports = data.get("imports", {})
superpowers = imports.get("superpowers")
if not superpowers:
    raise SystemExit("missing [imports.superpowers]")

source = superpowers.get("source")
if source != "../gascity-packs/superpowers":
    raise SystemExit(f"unexpected Superpowers source: {source!r}")
PY

expected_formulas="$(cat <<'EOF'
superpowers-brainstorming
superpowers-build
superpowers-code-review
superpowers-decomposition
superpowers-development
superpowers-development-item
superpowers-fix-loop
superpowers-implementation
superpowers-plan-review
superpowers-planning
superpowers-review
superpowers-task-review
EOF
)"

expected_skills="$(cat <<'EOF'
brainstorming
executing-plans
finishing-a-development-branch
receiving-code-review
requesting-code-review
subagent-driven-development
test-driven-development
using-git-worktrees
verification-before-completion
writing-plans
EOF
)"

expected_agents="$(cat <<'EOF'
brainstorming
code-quality-reviewer
code-reviewer
finisher
implementer
plan-reviewer
review-fixer
spec-reviewer
writing-plans
EOF
)"

for formula in $expected_formulas; do
  [ -f "$SUPERPOWERS_ROOT/formulas/$formula.formula.toml" ] \
    || fail "missing imported formula $formula"
done

for skill in $expected_skills; do
  [ -f "$SUPERPOWERS_ROOT/skills/$skill/SKILL.md" ] \
    || fail "missing imported skill $skill"
done

for agent in $expected_agents; do
  [ -f "$SUPERPOWERS_ROOT/agents/$agent/agent.toml" ] \
    || fail "missing imported agent target superpowers.$agent"
  [ -f "$SUPERPOWERS_ROOT/agents/$agent/prompt.template.md" ] \
    || fail "missing imported agent prompt superpowers.$agent"
done

discovered_targets="$(
  rg --no-filename -o 'superpowers\.[A-Za-z0-9_-]+' "$SUPERPOWERS_ROOT/formulas" -g '*.toml' \
    | sort -u
)"

[ -n "$discovered_targets" ] || fail "no Superpowers run targets discovered"

baseline_targets="$(cat <<'EOF'
superpowers.brainstorming
superpowers.code-quality-reviewer
superpowers.code-reviewer
superpowers.finisher
superpowers.implementer
superpowers.plan-reviewer
superpowers.spec-reviewer
superpowers.writing-plans
EOF
)"

for target in $baseline_targets; do
  has_line "$discovered_targets" "$target" \
    || fail "expected Superpowers run target not discovered: $target"
done

if [ "${RUN_LIVE_GC:-0}" = "1" ]; then
  command -v gc >/dev/null 2>&1 || fail "RUN_LIVE_GC=1 requested but gc is not on PATH"
  [ -n "$CITY" ] || fail "RUN_LIVE_GC=1 requires GC_CITY_PATH to be set to the city root"

  live_formulas="$(gc formula list --city "$CITY" --rig "$RIG" | awk '/^superpowers-/ {print $1}' | sort -u)"
  for formula in $expected_formulas; do
    has_line "$live_formulas" "$formula" \
      || fail "live formula catalog missing $formula for $RIG"
  done

  live_agents="$(gc agent list --city "$CITY" --rig "$RIG")"
  for target in $discovered_targets gc.run-operator gc.task-decomposer; do
    printf '%s\n' "$live_agents" | grep -F -- "$target" >/dev/null \
      || fail "live agent catalog missing $target for $RIG; import or expose the Superpowers rig agents before dispatch"
  done

  echo "PASS superpowers availability live smoke"
else
  echo "PASS superpowers availability static smoke"
fi
