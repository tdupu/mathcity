---
name: new-computing-policy
description: >-
  Propose and apply an amendment to the Computing Policy
  (mathcity/subdomains/computing/POLICY.md, C1.x–C4.x rules). Use when the
  user says "new computing rule", "amend computing policy", "update computing
  policy", "add a caching rule", "add a testing rule", "run new-computing-policy",
  or when check-computing-policy surfaces a case the policy does not cover.
  Sole write path for computing domain rules (PP1.4). Every change is gated
  on human approval and recorded in the policy's Change Log before taking
  effect. Companion to check-computing-policy (read-only auditor). Policy home:
  mathcity/subdomains/computing/POLICY.md.
---

# new-computing-policy

Propose and commit an amendment to the computing policy. Every policy change
is gated on human approval and recorded in the Change Log at the bottom of
[POLICY.md](../../POLICY.md) before any dependent skill or formula is updated.

**This is the sole write path for computing domain rules (PP1.4).** Editing
`POLICY.md` in place without going through this skill — even for typos — is
a PP1.4 violation. Use this skill for micro-proposals too.

---

## When to use

- `check-computing-policy` returned a **revise** finding that requires a rule change
- A new caching, DRY, testing, or regression case falls outside existing rules
- An existing rule is wrong, incomplete, or has become obsolete
- the human adjudicator wants to add, deprecate, or reword a computing rule
- A new pillar is needed (requires new sub-prefix: C5.x, C6.x, etc.)

---

## Procedure

### Step 1 — Read the current policy

```bash
cat <mathcity-pack-root>/subdomains/computing/POLICY.md
# Also read the prefix registry to confirm current rule IDs:
cat <mathcity-pack-root>/docs/rule-prefix-registry.md
```

Identify:
- The section the new rule belongs to (C1 / C2 / C3 / C4 / new pillar)
- The last rule ID in that section — new rule gets the next integer
- Whether the rule overlaps with M-rules (see companion note below)

### Step 2 — Draft the proposal

Write a concise proposal:

```
## Proposed computing policy rule amendment

**Rule ID:** C<pillar>.<n>  (e.g., C1.7, C3.7, C4.7)
**Section:** <Pillar title>
**Status:** proposed
**Conflicts / overlaps:** [list any M-rule this complements or supersedes]

### Rule text
<One or two sentences. Must be mechanically checkable by check-computing-policy.>

### Rationale
<Why this rule is needed. Cite the case that exposed the gap — a bead ID,
a check-computing-policy finding, or a concrete incident.>

### What changes
- POLICY.md: add rule <ID> to section <C<n>>
- check-computing-policy: add/update the corresponding Check <n> step
- [If any gate/formula is affected]: gates.toml entry <G-id> adds rule <ID>
  to its `rules` field.
- [If any companion skill is affected]: list them.

### What does NOT change
<Anything a reader might expect to change but won't — especially M-rules
that remain unchanged.>
```

### Step 3 — Overlap check

Before presenting, verify the proposed rule does not duplicate or
conflict with an existing M-rule:

```bash
# Search magma POLICY.md for related rules
grep -n "cache\|memo\|DRY\|factor\|test\|regression\|assert\|blast" \
  <mathcity-pack-root>/subdomains/magma/POLICY.md | head -20
```

If an M-rule already covers the case exactly: do NOT duplicate — instead
propose a cross-reference amendment to the existing M-rule or a note in
POLICY.md pointing to the M-rule. If the C-rule is a generalization of
the M-rule (applies beyond Magma), proceed with the C-rule and add a
"Companion policy" note citing PP6.1 precedence.

### Step 4 — Present to the human adjudicator

Surface the proposal clearly. Ask for one of:
- **approve** — proceed to commit
- **revise** — incorporate feedback, re-present
- **defer** — record as pending, stop

Do NOT modify any file until the human adjudicator approves.

### Step 5 — On approval: amend the policy

**5a.** Add the rule to the correct section in `POLICY.md`. Rules are numbered
sequentially; do not renumber existing rules. Insert after the last rule
in the section (or before the anti-patterns table if the last rule ends
the pillar).

**5b.** If the rule belongs to a new pillar: add a new `## Pillar N — <Title> (C<N>.x)`
section before the Anti-patterns table.

**5c.** Update the Anti-patterns table with the new rule's signature pattern
and rule ID.

**5d.** Append to the Change Log at the bottom of `POLICY.md`:

```markdown
| <date> | Add rule <ID>: <one-line summary> | <the human adjudicator's rationale, brief> |
```

**5e.** Update `check-computing-policy/SKILL.md` to add or update the
corresponding Check step for the new rule. The check must have at least
one bash command (even if approximate).

**5f.** If the rule affects a gate (PP4.2), add the rule ID to the `rules`
field in `mathcity/assets/brief-pipeline/gates.toml`.

**5g.** If the policy was previously `Status: Draft` and this is an adoption
proposal: update the header to `Status: Adopted`, set `Date` to today,
increment `Version` to 1.0.

### Step 6 — Commit (with human authorization)

```bash
cd <repos-root>/gascity-packs
git add mathcity/subdomains/computing/POLICY.md
git add mathcity/subdomains/computing/skills/check-computing-policy/SKILL.md
# Also add gates.toml if changed:
git add mathcity/assets/brief-pipeline/gates.toml
git commit -m "policy(computing): add rule <ID> — <one-line summary>"
```

Do NOT push unless the human adjudicator explicitly asks. Report the commit hash and await
instruction.

---

## Rule ID assignment

Computing policy uses section prefixes under the `C` domain prefix:

| Prefix | Pillar |
| --- | --- |
| C1 | Caching and memoization |
| C2 | Code factoring and DRY |
| C3 | Intrinsic and function testing |
| C4 | Regression testing |
| C5+ | Future pillars (reserve via this skill) |

To reserve a new pillar prefix series (e.g., C5): add the pillar section
to POLICY.md AND note it in the Change Log. No change to the prefix registry
is needed — the registry row for `C` already covers all C<n>.<m> IDs.

---

## Deprecation

To deprecate a rule rather than add one:

1. In `POLICY.md`, strike the rule title: `~~Rule C1.x Title~~`
2. Add `Status: deprecated (superseded by <new-id>)` under the rule
3. In the Change Log, record the deprecation with date and rationale
4. In `check-computing-policy/SKILL.md`, update the relevant check to
   note the rule is deprecated and cite the superseding rule
5. In `gates.toml`, any gate listing the deprecated rule ID keeps it (for
   audit trail) but also lists the superseding rule ID

Never delete a rule ID — IDs are permanent (PP1.5, PP2.4).

---

## Promotion

This policy starts as a standalone domain (`Status: Draft`). When adopted:
- the human adjudicator must explicitly approve in conversation or via a decision bead (PP2.2)
- Header transitions: `Status: Draft → Adopted`, `Date` updated, `Version: 1.0`
- The policy is then enforceable and may be cited in gates.toml `rules` fields

The computing domain was created with 17 rules across 4 pillars. If rules
exceed 40 and a natural sub-domain emerges, create a sub-policy section
first (PP3.1), then promote via a new-computing-policy proposal (PP3.2).
