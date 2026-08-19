---
name: check-build-formulas-and-skills
description: >
  Completeness audit for the mathcity formula and skill catalogs. Checks:
  (1) every formula TOML in mathcity/formulas/ has a row in README-formulas.md,
  (2) every skill dir in mathcity/**/skills/ has a row in README-skills.md,
  (3) every MathCity-owned briefed/work-boundary formula passes
  check-formula-hygiene (briefed terminal step, no model-name run_target,
  policy conformance). Reports all gaps and routes
  to repair skills. Trigger phrases: "check build", "check formulas and
  skills", "check-build-formulas-and-skills", "are all formulas indexed",
  "are all skills indexed", "formula/skill coverage audit".
---

# check-build-formulas-and-skills

Completeness and policy audit across the full mathcity pack family.
Report-only by default — never edits, never commits.

Canonical tables:
- [README-formulas.md](../../../../README-formulas.md) — every formula TOML in
  `formulas/` must appear here exactly once.
- [README-skills.md](../../../../README-skills.md) — every `SKILL.md` under
  `skills/` or `subdomains/*/skills/` must appear here exactly once.

**Companion tools:**
- `check-formula-hygiene` — per-formula F-rule check (read POLICY-formulas.md)
- `new-formula-policy` — amend POLICY-formulas.md when a rule is missing
- `update-README` — re-sync README-formulas.md / README-skills.md drift
- `new-skills-policy` — amend skills policy when a rule is missing

## Pre-flight

```bash
# `gc dolt health` is THREE-valued: 0 healthy, 2 reachable-but-quarantined
# (non-fatal), 1/other unreachable. See template-fragments/dolt-preflight.md.
_dolt_out=$(gc dolt health 2>&1); _dolt_rc=$?
case "$_dolt_rc" in
  0) ;;
  2) ;;   # reachable; auto-GC blocked by a standing compaction quarantine.
          # NON-FATAL and NOT this skill's business: bd resolves beads normally.
          # Proceed SILENTLY — the reporting skills surface it (Variant B).
  *) echo "I'm sorry, I can't do that — Dolt is unreachable."
     echo "Run 'gc dolt start' and retry."
     exit 1 ;;
esac
```

## Phase 1 — Formula completeness (README-formulas.md coverage)

### 1a. Enumerate all formula TOMLs

```bash
PACK=<mathcity-pack-root>
find "$PACK/formulas" -maxdepth 1 -name "*.toml" \
  | sed 's|.*/||; s|\.toml$||' | sort > /tmp/formulas-on-disk.txt
cat /tmp/formulas-on-disk.txt | wc -l
```

### 1b. Extract indexed names from README-formulas.md

```bash
grep '^\| `' "$PACK/README-formulas.md" \
  | sed "s/^\| \`//; s/\`.*//" | sort > /tmp/formulas-indexed.txt
cat /tmp/formulas-indexed.txt | wc -l
```

### 1c. Report gaps

```bash
echo "=== In formulas/ but NOT in README-formulas.md ==="
comm -23 /tmp/formulas-on-disk.txt /tmp/formulas-indexed.txt

echo "=== In README-formulas.md but NOT in formulas/ (stale entries) ==="
comm -13 /tmp/formulas-on-disk.txt /tmp/formulas-indexed.txt
```

Missing from index → run `/update-README` or add rows via `/new-formula-policy`.
Stale index entries → run `/update-README` to prune.

## Phase 2 — Skill completeness (README-skills.md coverage)

### 2a. Enumerate all skill directories on disk

```bash
PACK=<mathcity-pack-root>
find "$PACK" -name "SKILL.md" -path "*/skills/*" \
  | sed 's|.*/skills/||; s|/SKILL\.md$||' | sort > /tmp/skills-on-disk.txt
cat /tmp/skills-on-disk.txt | wc -l
```

### 2b. Extract indexed names from README-skills.md

```bash
grep '^\| `' "$PACK/README-skills.md" \
  | sed "s/^\| \`//; s/\`.*//" | sort > /tmp/skills-indexed.txt
cat /tmp/skills-indexed.txt | wc -l
```

### 2c. Report gaps

```bash
echo "=== In skills/ dirs but NOT in README-skills.md ==="
comm -23 /tmp/skills-on-disk.txt /tmp/skills-indexed.txt

echo "=== In README-skills.md but NOT in skills/ (stale) ==="
comm -13 /tmp/skills-on-disk.txt /tmp/skills-indexed.txt
```

Missing from index → `skill-creator-math` step 7 (append to README-skills.md).
Stale entries → `update-README`.

## Phase 3 — Formula policy hygiene (F-rule sweep)

For each MathCity-owned briefed/work-boundary formula TOML, run
check-formula-hygiene inline. Critical F-rule shortcuts — scan all at once:

### 3a. Briefed terminal step (mandatory)

```bash
PACK=<mathcity-pack-root>
for f in "$PACK/formulas/"*.toml; do
  name=$(basename "$f" .toml)
  case "$name" in
    *-briefed|work-briefed|commission-work-briefed) ;;
    *) echo "SKIP  $name  (not a briefed/work-boundary formula)"; continue ;;
  esac
  # Extract the last step id
  last_id=$(python3 -c "
import tomllib, sys
d = tomllib.load(open('$f', 'rb'))
steps = d.get('steps', [])
print(steps[-1]['id'] if steps else 'NO-STEPS')
" 2>/dev/null)
  case "$last_id" in
    file-brief|brief-finalize|workflow-finalize|publish|route)
      echo "PASS  $name  (terminal: $last_id)" ;;
    *)
      echo "FAIL  $name  (terminal: $last_id — must be a briefed/work-boundary terminal step)" ;;
  esac
done
```

### 3b. No model names as gc.run_target (F1.3)

```bash
PACK=<mathcity-pack-root>
grep -rn '"fable"\|"opus"\|"sonnet"\|"haiku"' \
  "$PACK/formulas/" | grep "run_target\|plan_target\|model" \
  && echo "F1.3 VIOLATIONS FOUND" || echo "F1.3 CLEAN"
```

### 3c. README-formulas.md count header matches actual count

```bash
PACK=<mathcity-pack-root>
indexed=$(grep '^\| `' "$PACK/README-formulas.md" | wc -l | tr -d ' ')
header=$(grep -m1 'formulas in' "$PACK/README-formulas.md" | grep -o '[0-9]*' | head -1)
[ "$indexed" = "$header" ] \
  && echo "Count header correct: $indexed" \
  || echo "Count mismatch: header says $header, actual $indexed rows"
```

## Phase 4 — Sink coverage (Sink A agent-skills symlinks)

Every skill in `<mathcity-pack-root>/**/skills/` must have a Sink A
symlink in `<repos-root>/agent-skills/skills/`:

```bash
find <mathcity-pack-root> -name "SKILL.md" -path "*/skills/*" \
  | sed 's|.*/skills/||; s|/SKILL\.md$||' | while read skill; do
  if [ -L <repos-root>/agent-skills/skills/"$skill" ]; then
    echo "Sink A OK   $skill"
  else
    echo "Sink A MISS $skill  — run skill-creator-math step 5"
  fi
done
```

## Output format

```
check-build-formulas-and-skills — <date>

PHASE 1 — Formula coverage (README-formulas.md)
  On disk: <N>  |  Indexed: <M>
  Missing from index: <list or NONE>
  Stale index entries: <list or NONE>

PHASE 2 — Skill coverage (README-skills.md)
  On disk: <N>  |  Indexed: <M>
  Missing from index: <list or NONE>
  Stale index entries: <list or NONE>

PHASE 3 — Formula hygiene
  Briefed terminal step: <N> PASS / <M> FAIL
  F1.3 (no model-name run_target): PASS | FAIL
  Count header: PASS | FAIL

PHASE 4 — Sink coverage
  Sink A: <N> OK / <M> MISSING

OVERALL: PASS | WARN | FAIL

Repair routes:
  Missing index rows → /update-README
  F1.3 violations → /check-formula-hygiene <formula>, then /new-formula-policy
  Missing Sink A → /skill-creator-math step 5
  Missing Sink B → ln -s ... <city-root>/.claude/skills/<sink-name>
```

## What this skill does NOT do

- Does NOT repair any drift — it reports only
- Does NOT commit or push
- Does NOT run `gitleaks` (use `check-formula-hygiene` per formula for that)
- Does NOT check materialized skill sinks as source — canonical source is `<mathcity-pack-root>`
