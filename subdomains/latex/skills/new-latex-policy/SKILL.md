---
name: new-latex-policy
description: Propose and apply an amendment to the LaTeX Subdomain Policy (mathcity/subdomains/latex/POLICY.md, LX-rules). Sole write path for LX-rule changes (PP1.4) - rules enter, change, or exit ONLY through a proposal approved by the human adjudicator in conversation, recorded in the policy Change Log. Use when the user says "new latex rule", "amend latex policy", "update the LX rules", "new-latex-policy", "deprecate LX<n>", when check-latex-hygiene reports a finding that matches no LX-rule (its defer path routes here), or when a LaTeX workflow incident exposes an uncovered case. Companion to check-latex-hygiene (read-only auditor). NOT for creating work beads - that is new-latex-bead; this skill amends policy RULES only.
---

# new-latex-policy

Propose and commit an amendment to the LaTeX subdomain policy. Every policy
change is gated on human approval and recorded in the Change Log at the
bottom of [POLICY.md](../../POLICY.md) before any dependent skill, gate, or
formula is updated.

**This is the sole write path for LX-rules (PP1.4).** Editing
`subdomains/latex/POLICY.md` in place without going through this skill —
even for typos — is a PP1.4 violation. Use this skill for micro-proposals
too.

**Trinity role:** POLICY.md (source of truth) + [[check-latex-hygiene]]
(read-only auditor) + this skill (sole write path) = the LX trinity (PP1.1).

---

## When to use

- `check-latex-hygiene` returned a **defer** finding that matches no LX-rule
  (its hard-rules section routes uncovered cases here)
- A LaTeX workflow incident exposes a gap (new he-d4l-class failure shape)
- An existing LX-rule is wrong, ambiguous, or produces false positives
- the human adjudicator wants to add, deprecate, or reword an LX-rule
- The policy needs a lifecycle transition (Draft → Adopted per PP2.2, or a
  scope change to the covered-rig list in the header table)
- A rule owned by a neighboring policy (L-rules in brief-system, BP7/BP8 in
  POLICY-beads.md, he-jwmy charter items) needs an LX-side counterpart — check
  the division-of-labor block at the top of POLICY.md FIRST so the rule
  lands in the right document (misplaced rules go to that domain's own
  new-X-policy skill instead)

## NOT for

- Creating or advancing LaTeX work beads → [[new-latex-bead]]
- Auditing beads/diffs against existing rules → [[check-latex-hygiene]]
- Amending brief-system L-rules (gate G6 brief behavior) → [[new-brief-policy]]
- Amending BP-rules (bead lifecycle) → `new-math-bead-policy`
- Amending the he-jwmy LaTeX-gate charter — that is a hecke decision bead,
  not a mathcity policy file

---

## Procedure

### Step 0 — Pre-flight

```bash
test -f <mathcity-pack-root>/subdomains/latex/POLICY.md || echo MISSING
```

If missing, stop: restore the file (git checkout or re-import the pack)
before proposing anything.

### Step 1 — Read the current policy and registry

```bash
cat <mathcity-pack-root>/subdomains/latex/POLICY.md
cat <mathcity-pack-root>/docs/rule-prefix-registry.md
```

Identify:

- The pillar the new rule belongs to (see the pillar table below) — new rule
  gets the next integer in that pillar (LX4.7 exists → next is LX4.8)
- Whether the concern is genuinely LX-side (bead-side LaTeX workflow
  mechanics) per the division-of-labor block — on conflict, LX wins for
  workflow mechanics, BP wins for bead lifecycle, L wins for brief behavior
- The policy `Status:` in the header table (Draft policies govern nothing —
  PP2.1 — but their amendment discipline is identical)

### Step 2 — Draft the proposal

```
## Proposed LX-rule amendment

**Rule ID:** LX<pillar>.<n>   (next available in the pillar — never reuse)
**Pillar:** <pillar number + title>
**Status:** proposed

### Rule text
<One or two sentences, in the house style: bold title, then body, ending
 with an explicit pass criterion and an explicit fail → verdict
 (revise | fail | auto-reject). If it cannot be stated with a mechanical
 pass/fail criterion, it is guidance, not a rule — it does not go in
 POLICY.md.>

### Rationale
<Why this rule is needed. Cite the incident, bead, or
 check-latex-hygiene finding that exposed the gap.>

### What changes
- POLICY.md: add rule LX<p>.<n> to Pillar <p>; add Change Log row
- [If the Non-negotiables checklist is affected]: add/adjust the bullet
- [If gate G6 or another gates.toml entry enforces it]: add the rule ID to
  that gate's `rules` field in mathcity/assets/brief-pipeline/gates.toml
  (PP4.2). The latex-gate FORMULA (mathcity/gates/latex-gate.toml) cites
  gate IDs, not rule IDs (PP4.1) — it normally needs no edit.
- [If check-latex-hygiene's checklist needs a new line]: list it here; the
  skill edit ships in the same commit so auditor and policy stay in sync
  (PP1.2).

### What does NOT change
<Anything a reader might expect to change but won't — especially: existing
 rule IDs are never renumbered (PP1.5).>

### Downstream impact
- Beads/diffs currently in violation of the NEW rule: <list or "none">
- Remediation required: <yes/no; if yes, one line each>
```

### Step 3 — Present to the human adjudicator (mandatory gate)

Present the proposal via AskUserQuestion (or [[present-it]] compact form for
a straightforward single-rule addition):

```
DECISION:  Add LX<p>.<n> ("<rule title>") to subdomains/latex/POLICY.md?
CONTEXT:   <one sentence on what triggered this>
RECOMMEND: <approve | approve-with-edit | your honest recommendation>
CONFIRM:   approve / revise / defer
```

For batch proposals, pillar-scope changes, coverage-scope changes (the
covered-file definition or the covered-rig list), or adoption proposals: use
full-form [[present-it]].

the human adjudicator's options:

- **approve** — proceed to Step 4
- **revise** — incorporate feedback, re-present (loop here)
- **defer** — record the proposal as pending (a bead in the owning rig,
  labeled `[LATEX]`, body = the proposal verbatim) and STOP

**Do NOT modify any file until the human adjudicator approves. No implicit approval:
silence, or approval of a different proposal in the same conversation, does
not transfer (the LX3.4 stale-approval principle applies to policy too).**

### Step 4 — On approval: amend the policy

**4a.** Add the rule to the correct pillar in `POLICY.md`, in the house
style, at the next integer. Never renumber existing rules (PP1.5).

**4b.** If the rule is checklist-worthy, update the **Non-negotiables**
section.

**4c.** Append to the Change Log table at the bottom of `POLICY.md`:

```markdown
| <date> | Add LX<p>.<n>: <one-line summary> | <the human adjudicator's rationale, brief> |
```

**4d.** Update the `Date` field in the header table to today.

**4e.** If a gate enforces the rule (PP4.2), add the rule ID to that gate's
`rules` field in `mathcity/assets/brief-pipeline/gates.toml`.

**4f.** If [[check-latex-hygiene]]'s procedure checklist needs a matching
line, edit it in the same change set (PP1.2 — auditor cites rule IDs and
must stay in sync).

**4g.** If this is an **adoption** proposal (PP2.2): set the header
`Status:` to `Adopted`, record the adopting date and decision channel
(conversation or decision bead) in the header table, and note the adoption
in the Change Log.

### Step 5 — Commit

```bash
cd <repos-root>/gascity-packs
git add mathcity/subdomains/latex/POLICY.md
# plus gates.toml and/or check-latex-hygiene/SKILL.md if changed:
git add mathcity/assets/brief-pipeline/gates.toml \
        mathcity/subdomains/latex/skills/check-latex-hygiene/SKILL.md
git commit -m "policy(latex): add LX<p>.<n> — <one-line summary>"
```

Do NOT push unless the human adjudicator explicitly asks. Report the commit and await
instruction. (Record the verdict per decision-recording discipline:
`record-decision` / bead note as applicable.)

### Step 6 — Verify

Run [[check-latex-hygiene]] on a representative `[LATEX]` bead or branch to
confirm: the new rule ID is citable by the auditor, POLICY.md still parses
(header table, pillar order, Change Log intact), and nothing in flight
fails the new rule unexpectedly. Surprises → report to the human adjudicator; never
quietly weaken the rule to make an existing violation pass.

---

## Rule ID assignment

LX pillars (from POLICY.md; prefix LX reserved in
`mathcity/docs/rule-prefix-registry.md`):

| Pillar | Scope |
| --- | --- |
| LX1 | What LaTeX work is a bead (coverage, inline tags, shadow TODOs, promotion) |
| LX2 | Stage taxonomy (labels, entry criteria, monotonicity) |
| LX3 | Quality gates (check-latex evidence floor, claim limits, approval) |
| LX4 | Atomization (section atoms, epics, caps, floors) |
| LX5 | LaTeX-to-LMFDB coupling (knowls, label verification, direction of truth) |
| LX6 | Merge policy (HOLD status, pre/post screening, pure-move) |
| LX7 | Compile-failure MREs |
| LX8 | Computation dependencies (traceability, autogen, dep edges, notebook loop) |
| LX9 | Anti-patterns (named rejected shapes) |

A rule that fits no pillar opens a new pillar (LX10+) — that is a
pillar-scope change: full-form presentation in Step 3, and consider PP3.2
(promotion threshold) if the new pillar looks like its own domain.

---

## Deprecation

To deprecate a rule rather than add one:

1. In `POLICY.md`, strike the rule title: `~~LX<p>.<n> Title~~`
2. Add `Status: deprecated (superseded by <new-id>)` under the rule
3. Record the deprecation in the Change Log
4. Any gates.toml entry listing the deprecated ID keeps it (audit trail) and
   also lists the superseding ID (PP4.3 analogue)
5. Remove the corresponding [[check-latex-hygiene]] checklist line only if
   the superseding rule's line replaces it

Never delete a rule ID — IDs are permanent (PP1.5, PP2.4).

---

## Hard rules

- **Never edit POLICY.md without the human adjudicator's explicit approval in this
  conversation or a decision bead** (Step 3 is mandatory, PP1.4/PP2.3).
- **Never change an LX-rule to excuse an existing violation** — fix the
  violation, then optionally amend to prevent recurrence.
- **Rule IDs are permanent** (PP1.5) — deprecate with tombstone, never
  delete or renumber.
- **Mechanical or it isn't a rule** — every rule ships with a pass criterion
  a skill can check and a named fail verdict; otherwise it is guidance and
  belongs elsewhere.
- **Respect the division of labor** — L-rules (brief behavior), BP-rules
  (bead lifecycle), and the he-jwmy charter are amended in THEIR homes, not
  here; this skill writes only to `subdomains/latex/POLICY.md`.
- **Do not push** without explicit instruction; never push to
  `gastownhall/gascity-packs` upstream.
- This skill amends rules; it never creates work beads ([[new-latex-bead]])
  and never adjudicates diffs (LX3.4 is the human adjudicator's gate).

---

## Cross-references

- `mathcity/subdomains/latex/POLICY.md` — the document this amends (LX-rules)
- `mathcity/POLICY-POLICY.md` — PP1.4 (sole write path), PP1.5 (ID
  immutability), PP2 (lifecycle), PP4 (gates), PP5.2 (prefix registry)
- `mathcity/docs/rule-prefix-registry.md` — LX prefix reservation
- [[check-latex-hygiene]] — the read-only auditor; keep its checklist in
  sync (Step 4f) and run it after every amendment (Step 6)
- [[new-latex-bead]] — creates work beads under these rules (not policy)
- [[new-brief-policy]] — amends L-rules (brief-system side of LaTeX)
- `new-math-bead-policy` (agent-skills) — amends BP-rules
- [[new-hygiene-policy]] — the P-rule analogue whose procedure this skill
  followed before it existed
- `mathcity/assets/brief-pipeline/gates.toml` — gate `rules` fields (PP4.2)
- `mathcity/gates/latex-gate.toml` — the formula layer (cites gates, not
  rules — PP4.1)
