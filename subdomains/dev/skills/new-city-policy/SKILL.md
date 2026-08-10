---
name: new-city-policy
description: >-
  Propose and apply an amendment to the City Operations Policy
  (mathcity/subdomains/dev/POLICY-city.md, CT-rules). Use when a new CT-rule
  is needed, an existing rule is wrong/incomplete, check-city-policy surfaced
  an uncovered runtime case, or a capacity/dispatch/observability constraint
  must be codified. Trigger on "add city policy", "new city rule", "amend
  POLICY-city.md", "new-city-policy", or when check-city-policy returns a
  case outside its CT-rule set. Sole write path for CT-rules — every change
  is gated on human approval and recorded in the Change Log. Companion to
  check-city-policy.
companion: "[[check-city-policy]]"
---

# new-city-policy

Propose and commit an amendment to
[`mathcity/subdomains/dev/POLICY-city.md`](../../POLICY-city.md) — the
source-of-truth CT-rules document that `check-city-policy` enforces. This
skill is the **sole write path** for CT-rules. Every policy change is gated
on human approval and recorded in a Change Log entry before it becomes
enforceable.

**Companion:** [[check-city-policy]] — run after any amendment to confirm the
new CT-rule is detectable and that nothing in flight now violates it.

## When to use

- `check-city-policy` returns a finding with no matching CT-rule
- An existing CT-rule is wrong, ambiguous, or creates false positives
- A new runtime constraint appears (new dispatch mechanism, new rig type, new
  observability surface, a scheduling/capacity gap surfaced by an incident)
- A PROPOSED rule is to be **adopted**, **adapted**, or **struck** after a
  grilling pass
- A vocabulary/terminology rule must be codified across dispatch and skills

## Step 0 — Read current policy and version

```bash
cat <mathcity-pack-root>/subdomains/dev/POLICY-city.md
```

Note:
- the header **Status** (Draft vs Adopted) and **Date** line,
- the highest CT-rule ID within the target pillar (CT1.x … CT12.x),
- whether the rule you are touching is **Adopted** or **PROPOSED**,
- the existing pillars (new rules increment the highest ID in their pillar; a
  genuinely new theme opens a new pillar, e.g. CT13).

Also confirm the CT prefix reservation is intact:

```bash
grep '| CT |' <mathcity-pack-root>/docs/rule-prefix-registry.md
```

## Step 1 — Draft the amendment

State the amendment as a structured proposal:

```
PROPOSED AMENDMENT — <date>

Pillar: <CT1 Capacity | CT2 Dispatch | ... | CT12 Sandboxing | new-pillar CT13>
Rule ID: <CT<N>.<M> — next available in the pillar>
Rule title: <short name, e.g. "Backpressure is surfaced, never accumulated">
Adopt/adapt/strike: <new rule | adopt a PROPOSED rule | adapt existing | strike>

Trigger: <what prompted this — incident, check-city-policy finding, the human adjudicator directive>

Proposed rule text:
  <The CT-rule in the same style as existing POLICY-city.md rules — one
   paragraph, with a clear pass/fail criterion a skill or gate can cite.
   State what the rule requires, allowed exceptions, and the verdict
   (fail / revise / defer) when violated. Cite the origin if adapted from a
   Gas Town / Gas City principle.>

Pass criterion (for check-city-policy to enforce):
  <One sentence on what a checker looks for to PASS.>

Fail criterion:
  <One sentence on what triggers the finding.>

Change-log entry (draft, exact text to append):
  ### <date> — CT<N>.<M> added/adopted/amended: <rule title>
  <One sentence summary>. Triggered by: <incident or directive>.

Downstream impact:
  - Plans / formulas / live-city state currently in violation of the NEW rule: <list or "none">
  - Remediation required: <yes/no; if yes, describe — but NEVER weaken the rule to excuse it>
```

Present the draft to the human adjudicator before touching the file. Do NOT edit
POLICY-city.md until the human adjudicator approves.

## Step 2 — Present-it gate (human approval REQUIRED)

Use [[present-it]] compact form for a straightforward new rule or a PROPOSED-
to-adopted promotion:

```
DECISION:  Add/adopt CT<N>.<M> ("<rule title>") in mathcity/subdomains/dev/POLICY-city.md?
CONTEXT:   <one sentence on what triggered this>
RECOMMEND: APPROVE — <one-line rationale>
CONFIRM:   y / n / grill-me-further
```

For rules that open a new pillar, change a pillar's scope, or affect work in
flight: use full-form [[present-it]] with all seven sections.

**the human adjudicator's approval in THIS conversation is required.** A prior session's
"sounds good" does not carry over.

## Step 3 — Apply the amendment

After the human adjudicator approves, edit
`<mathcity-pack-root>/subdomains/dev/POLICY-city.md`:

1. Add/modify the rule under the correct pillar, in numeric order, using the
   same format as existing CT-rules (bold rule ID, pass/fail criterion inline,
   PROPOSED tag if not yet adopted). To adopt a PROPOSED rule, remove the
   **(PROPOSED)** tag; to strike one, mark it **STRUCK: <date>** in the body
   (do not delete it — see hard rules).
2. Bump the **Date** line in the header table to today. If this amendment
   moves the whole document from Draft to Adopted, update the **Status** line
   too (full-procedure gate — see hard rules).
3. Append a Change Log entry at the TOP of the Change log section:

```markdown
### <date> — CT<N>.<M> added/adopted/amended: <rule title>
<One sentence summary>. Triggered by: <incident or directive>.
```

4. Run gitleaks on the amended file:

```bash
gitleaks detect --no-git \
  --source <mathcity-pack-root>/subdomains/dev/ 2>&1 | grep -v "no leaks"
```

Any leak → STOP, do not commit; report it. gitleaks FAIL is blocking.

> **Git note (outside agent):** in `<repos-root>/gascity-packs`, an OUTSIDE agent
> does not commit or push on its own — report the changed file and the exact
> proposed commit/push commands and let the human (or the calling
> orchestrator/repo-side landing agent) run them. If you are a gascity-managed inside worker
> operating under an explicit standing authorization, commit + push to the
> fork per that authorization; NEVER push to `gastownhall/gascity-packs`
> upstream.

## Step 4 — Verify with check-city-policy

After amendment, run [[check-city-policy]] to confirm:
- the new CT-rule is detectable (the audit procedure can cite the new CT-rule ID),
- nothing currently in flight fails the new rule unexpectedly,
- POLICY-city.md still parses (no broken markdown, header table intact),
- the CT prefix row in `rule-prefix-registry.md` still matches.

Quick sanity counts:

```bash
cd <mathcity-pack-root>/subdomains/dev
grep -cE 'CT[0-9]+\.[0-9]' POLICY-city.md          # total CT ID occurrences
grep -oE 'CT[0-9]+\.[0-9]+' POLICY-city.md | sort -u | wc -l   # distinct rule IDs
grep -cE '^\- \*\*C[0-9]' POLICY-city.md            # bare-C rule bullets — must be 0
```

## Hard rules

- **Never edit POLICY-city.md without human approval** (Step 2 mandatory).
- **Never amend a CT-rule to excuse an existing violation** — fix the
  violation first, then optionally amend to prevent recurrence. A policy that
  bends to legitimize what just broke is worthless.
- **CT-rule IDs are permanent** — once assigned, an ID is never reused, even
  after a rule is struck. Deprecate ≠ delete: mark **STRUCK: <date>** in the
  rule body; do not remove the text.
- **Draft may be edited freely; Adopted requires the full procedure.** While
  POLICY-city.md is `Status: Draft`, PROPOSED rules may be edited, adopted, or
  struck with a normal approval + change-log entry. Once the document (or a
  specific rule) is **Adopted**, any change requires the full present-it gate,
  a change-log entry, and a check-city-policy verification pass — no silent
  rewrites of standing policy.
- **CT prefix only** — never assign a bare `C` ID (that prefix belongs to the
  Computing domain). If a new pillar is opened, keep the CT prefix; reserve
  nothing new in the registry (CT already covers this whole document).
- **check-city-policy is the enforcer** — if a new rule cannot be expressed as
  a detectable pass/fail criterion, it is guidance, not a CT-rule; guidance
  goes in prose, not the numbered rule set.

## Cross-references

- [POLICY-city.md](../../POLICY-city.md) — the document this amends
- [[check-city-policy]] — the enforcement skill; run after every amendment
- `mathcity/docs/rule-prefix-registry.md` — CT prefix reservation
- `mathcity/POLICY-POLICY.md` — PP1.1 trinity requirement (POLICY + check + new)
- [[new-hygiene-policy]] — the P-rule (pack portability) sibling amender
- [[present-it]] — human-approval gate used in Step 2
