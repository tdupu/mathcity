---
name: new-formula-policy
description: >
  Propose and apply an amendment to the mathcity formula policy
  (mathcity/README-formulas.md + formula-creator-math hygiene gate). Use when
  a new formula convention rule is needed, the README-formulas.md index
  drifts, a new shape category is required, or check-formula-hygiene surfaces
  an uncovered case. Trigger on "update formula policy", "new formula rule",
  "amend formula policy", "new-formula-policy", or when check-formula-hygiene
  returns an UNKNOWN-CASE finding.
---

# new-formula-policy

Propose and commit an amendment to the mathcity formula index policy. The
two enforcement surfaces are:
- **`mathcity/README-formulas.md`** — the canonical index every formula must
  appear in; gate enforced by `formula-creator-math` Step 6 and `formula-work`
  approve-verdict step.
- **`formula-creator-math` SKILL.md Step 5** — the hygiene gate that checks
  briefed terminal step, catalog block, and README-formulas.md entry.

Every policy change is gated on human approval before editing either file.

**Companion:** [[check-formula-hygiene]] — run after any amendment.

## When to use

- A new formula shape category is needed (e.g., a new entry in the Shape column of README-formulas.md)
- The briefed-terminal-step set must expand (new valid terminal step id)
- A formula is missing from README-formulas.md (drift detected)
- A required var convention changes (e.g., new mandatory `[vars.artifact_root]` default)
- `check-formula-hygiene` returns an UNKNOWN-CASE finding

## Step 0 — Read current state

```bash
cat <mathcity-pack-root>/README-formulas.md
cat <mathcity-pack-root>/subdomains/dev/skills/formula-creator-math/SKILL.md | grep -A20 "Step 5"
```

Note: current formula count, shape categories, and hygiene gate assertions.

## Step 1 — Draft the amendment

```
PROPOSED AMENDMENT — <date>

Trigger: <what prompted this — drift, incident, new shape>

Target: <README-formulas.md | formula-creator-math Step 5 | both>

Current rule:
  <exact text>

Proposed rule:
  <replacement text>

Rationale:
  <why the current rule is wrong or incomplete>

Formulas currently in violation of the NEW rule: <list or "none">
Remediation required: <yes/no>
```

Present draft to the human adjudicator before touching any file.

## Step 2 — Gate on human approval

```
DECISION:  Approve proposed amendment to mathcity formula policy §<section>?
CONTEXT:   <one sentence on trigger>
RECOMMEND: APPROVE — <one-line rationale>
CONFIRM:   y / n / grill-me-further
```

the human adjudicator's approval in this conversation is required. A prior session's
"sounds good" does not carry over.

## Step 3 — Apply the amendment

After the human adjudicator approves:

1. Edit `README-formulas.md`:
   - Add/modify rows, update count in header, update shape vocabulary if needed.
2. Edit `formula-creator-math` SKILL.md Step 5 if hygiene gate changes.
3. Run gitleaks:
   ```bash
   gitleaks detect --no-git --source <mathcity-pack-root>/README-formulas.md
   ```
4. Commit both files together:
   ```bash
   cd <mathcity-pack-root>
   git add README-formulas.md \
           subdomains/dev/skills/formula-creator-math/SKILL.md
   git commit -m "policy(mathcity): <one-line summary of amendment>"
   git push origin main
   ```

## Step 4 — Verify

```bash
# Count matches header
actual=$(grep -c "^| \`" <mathcity-pack-root>/README-formulas.md)
echo "Formulas in table: $actual"
grep "^[0-9]* formulas" <mathcity-pack-root>/README-formulas.md

# Every formula TOML has a row
ls <mathcity-pack-root>/formulas/*.toml | while read f; do
  name=$(basename "$f" .toml)
  grep -q "$name" <mathcity-pack-root>/README-formulas.md \
    || echo "MISSING: $name"
done
```

## Hard rules

- Never edit README-formulas.md without human approval (Step 2 mandatory).
- Never change the policy to excuse an existing violation — fix the violation first.
- Policy is subordinate to `mathcity/subdomains/dev/POLICY.md` — conflicts: POLICY.md wins.
- Amendments are permanent — no silent rewrites of prior policy.

## Cross-references

- `mathcity/README-formulas.md` — the document this maintains
- `formula-creator-math` SKILL.md — enforces README-formulas.md gate at creation time
- `formula-work` SKILL.md — enforces README-formulas.md gate at approve-verdict time
- `check-formula-hygiene` — run after any amendment
- `mathcity/subdomains/dev/POLICY.md` — superior policy
