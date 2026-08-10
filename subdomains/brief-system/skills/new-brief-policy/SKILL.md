---
name: new-brief-policy
description: >-
  Propose and apply an amendment to the brief-system POLICY.md
  (mathcity/subdomains/brief-system/POLICY.md). Use when the user says
  "update brief policy", "new brief rule", "amend brief-policy", "add a
  rule to the brief system", "run new-brief-policy", or when check-brief-policy
  surfaces a case the policy doesn't cover. Sole write path for brief-system
  rules (PP1.4). Every change is gated on human approval and recorded in
  the policy's Change Log before taking effect. Companion to check-brief-policy
  (read-only auditor).
---

# new-brief-policy

Propose and commit an amendment to the brief-system policy. Every policy change
is gated on human approval and recorded in the Change Log at the bottom of
[POLICY.md](../../POLICY.md) before any dependent skill or formula is updated.

**This is the sole write path for brief-system rules (PP1.4).** Editing
`POLICY.md` in place without going through this skill — even for typos — is
a PP1.4 violation. Use this skill for micro-proposals too.

---

## When to use

- `check-brief-policy` returned a **revise** finding that requires a rule change
- A new brief workflow case falls outside existing rules (UNKNOWN-CASE finding)
- An existing rule is wrong or incomplete
- the human adjudicator wants to add, deprecate, or reword a brief-system rule

---

## Procedure

### Step 1 — Read the current policy

```bash
cat <mathcity-pack-root>/subdomains/brief-system/POLICY.md
# Also read the prefix registry to confirm the next rule ID:
cat <mathcity-pack-root>/docs/rule-prefix-registry.md
```

Identify:
- The section the new rule belongs to (B, N, L, E, T, D, S)
- The last rule ID in that section — new rule gets the next integer

### Step 2 — Draft the proposal

Write a concise proposal:

```
## Proposed brief-system rule amendment

**Rule ID:** <prefix><section>.<n>  (e.g. B1.7, N4, E2)
**Section:** <Pillar or section title>
**Status:** proposed

### Rule text
<One or two sentences. Must be mechanically checkable.>

### Rationale
<Why this rule is needed. Cite the case that exposed the gap.>

### What changes
- POLICY.md: add rule <ID> to <section>
- [If any gate/formula is affected]: gates.toml entry <G-id> adds rule <ID>
  to its `rules` field.
- [If any skill invokability changes]: list affected skills.

### What does NOT change
<List anything a reader might expect to change but won't.>
```

### Step 3 — Present to the human adjudicator

Surface the proposal clearly. Ask for one of:
- **approve** — proceed to commit
- **revise** — incorporate feedback, re-present
- **defer** — record as pending, stop

Do NOT modify any file until the human adjudicator approves.

### Step 4 — On approval: amend the policy

**4a.** Add the rule to the correct section in `POLICY.md`. Rules are numbered
sequentially; do not renumber existing rules.

**4b.** Append to the Change Log at the bottom of `POLICY.md`:

```markdown
| <date> | Add rule <ID>: <one-line summary> | <the human adjudicator's rationale, brief> |
```

**4c.** If the rule affects a gate (PP4.2), add the rule ID to the `rules`
field in `mathcity/assets/brief-pipeline/gates.toml`.

**4d.** If the policy was previously `Status: Draft` and this is an adoption
proposal: update the header to `Status: Adopted`, set `Date` to today.

### Step 5 — Commit

```bash
cd <repos-root>/gascity-packs
git add mathcity/subdomains/brief-system/POLICY.md
# Also add gates.toml if changed:
git add mathcity/assets/brief-pipeline/gates.toml
git commit -m "policy(brief-system): add rule <ID> — <one-line summary>"
```

Do NOT push unless the human adjudicator explicitly asks. Report the commit and await
instruction.

---

## Rule ID assignment

Rule IDs in the brief-system use these section prefixes (from the prefix
registry):

| Prefix | Section |
| --- | --- |
| B1 | Brief production |
| B2 | Brief lifecycle (pile, adjudication, ordering, deferral) |
| B3 | Closure discipline |
| B4 | Magma packages |
| N | No-brainer automation |
| L | LaTeX rules |
| E | Experiment design |
| T | Testing / spec |
| D | Documentation |
| S | Server-touching work |

New sections (e.g. for a new sub-policy pillar) must first reserve a prefix
in `mathcity/docs/rule-prefix-registry.md` (PP5.2).

---

## Deprecation

To deprecate a rule rather than add one:

1. In `POLICY.md`, strike the rule title: `~~Rule B1.x Title~~`
2. Add `Status: deprecated (superseded by <new-id>)` under the rule
3. In the Change Log, record the deprecation
4. In `gates.toml`, any gate listing the deprecated rule ID keeps it (for
   audit trail) but also lists the superseding rule ID

Never delete a rule ID — IDs are permanent (PP1.5, PP2.4).
