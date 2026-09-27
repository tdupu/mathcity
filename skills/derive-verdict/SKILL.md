---
name: derive-verdict
description: Decide whether a pending question — a brief awaiting adjudication, a queue item, a "should we X?" — is DETERMINED by an Adopted policy rule, so it is derived and cited instead of spending a human decision (PP1.10). Emits exactly one of three outcomes. DERIVED — an Adopted, uncontested, mechanically-evaluable rule eliminates every option but one; quote the rule verbatim, name which option each rule kills, and do NOT surface it to the human as a decision. CONFLICT — two Adopted rules pull opposite ways and neither PP6.1(a) precedence nor PP6.1(b) subject-matter ownership resolves it; this DOES go to the human, naming both rules. UNDETERMINED — no Adopted rule reaches it; a genuine human decision. Adoption is checked PER RULE, not per document — a Draft policy governs nothing (PP2.1) and 27 individually-PROPOSED rules currently live inside Adopted documents. REFUSES loudly (CT13.4) rather than approximating when a rule is judgement-kind or when its reading is itself disputed. Read-only — never records a verdict, never closes a brief, never writes bead state; recording is [[adjudicate-brief]]'s. Trigger phrases — "does policy decide this", "derive a verdict", "is this a derivation or a decision", "can this brief be adjudicated from policy", "is this a no-brainer by derivation", "why am I being shown this", "which rule settles this" — and any moment before a brief is presented to a human.
---

> **Canonical copy**: `mathcity.derive-verdict` in this mathcity pack. Materialized agent-skills copies are fallback only.

# derive-verdict

## The gap this fills

The city has skills that **audit** state against policy (`check-X-policy`, [[check-zero]],
[[check-brief-policy]]) and skills that **record** a verdict someone already reached
([[adjudicate-brief]]). Nothing turned policy *into* the verdict. PP1.10 has mandated that act
since 2026-07-12 and it was still being performed ad hoc, one agent's reading at a time:

> **PP1.10** — *"A question whose answer is determined by an Adopted rule is resolved by
> derivation — act on the rule and cite its ID; never surface it to the human adjudicator as a
> decision. Surfacing a policy-derivable question is a violation (the determining rule ID is the
> evidence). Exception: a genuinely ambiguous derivation — two Adopted rules pulling opposite ways
> with no precedence clause — is a PP6.1(c) conflict and goes to the human adjudicator."*

This skill is the written, falsifiable form of that act. It produces a **derivation record**, not a
recorded verdict.

## Input and outcomes

**Input**: a brief bead id or brief file, or a plainly-stated pending question, **plus a closed set
of candidate options**. If the options are not enumerable, stop at step 1 — there is nothing to
eliminate.

| Outcome | Condition | Where it goes |
|---|---|---|
| **DERIVED** | One or more Adopted, uncontested, mechanically-evaluable rules eliminate every option but one | Hand to [[adjudicate-brief]] for recording. **Never** rendered to the human as a decision row (PP1.10). |
| **CONFLICT** | Two Adopted rules determine opposite options; PP6.1(a) has no precedence clause and PP6.1(b) does not settle ownership | To the human, naming **both** rules and both readings (PP6.1(c)) |
| **UNDETERMINED** | No Adopted rule reaches the question, or the only reaching rule is Draft / PROPOSED / judgement-kind / contested | To the human as a genuine decision |

Plus two refusals, which are results and must be loud (CT13.4), never silently folded into
UNDETERMINED's prose:

| Refusal | Trigger |
|---|---|
| `REFUSED_JUDGEMENT` | The reaching rule cannot be mechanically evaluated (e.g. marked `(JUDGEMENT RULE)`, or its pass criterion names something an agent must weigh) |
| `REFUSED_CONTESTED` | The rule's meaning is disputed, or the derivation would require this skill to pick between two live readings |

A refusal routes to the human **as a refusal with its reason**, distinct from UNDETERMINED: the
difference between "policy says nothing here" and "policy says something this skill is not allowed
to resolve" is the whole signal.

## Four hard constraints

1. **Only `Status: Adopted` policies may be cited, and adoption is per rule.** PP2.1: *"A POLICY.md
   in `Status: Draft` governs nothing — it may not be cited in check skills or gate formulas. Only
   `Status: Adopted` policies are enforceable."* A document-level check alone is not sufficient —
   measured 2026-09-18, **27 individually-PROPOSED rules sit inside Adopted documents**, one of
   which forbids any check skill or gate from citing it. A guard that only read document status
   would admit all 27.
2. **A contested rule is adjudicated before it is derived from, never during.** If two readings of
   the rule text are live, or this skill would have to choose one, it REFUSES. Freezing a reading
   into a derivation is making the decision while claiming not to have made one.
3. **A rule that cannot be mechanically evaluated REFUSES loudly; it is never approximated.**
   CT13.4 (Adopted): *"A refusal is a result, and it must be loud … The defect is **silence** — a
   declined operation returning success-shaped output."* The policy set marks these: B2.13 and
   B2.14 carry `(JUDGEMENT RULE)` in their titles and state the reason
   (*"A mechanical proxy here would pass confidently on the cases it cannot see"*). Respect the
   marking; do not out-argue it.
4. **Never fabricate a rule ID.** A derivation whose cited rule does not exist, or exists and does
   not say what is claimed, is worse than no derivation — it launders an agent's preference as
   policy. Every citation carries file path, line number, and a byte-identical quote (step 6).

**On PP1.13.** Constraints 2 and 3 restate guards (b) and (c) of PP1.13, which is **PROPOSED** and
whose own text says *"Per PP2.1 no check skill or gate may cite this rule."* So this skill
**implements** those guards as its own design constraints and **must not cite PP1.13 as authority**
in any emitted derivation. The Adopted citation for the loud-refusal requirement is **CT13.4**.
This is the skill's rule-level adoption check applied to itself.

## Procedure

### 0. Refuse the wrong shape first

Stop before any policy reading if the question touches a stop-gated surface — a derivation is not a
route around a gate. Category-E / server-touching and user-skill-touching questions
([[catch-no-brainer]] steps 1–2) are refused here for the same reason they are refused there.
Emit `REFUSED_STOP_GATE` and stop.

### 1. State the question and the option set

Write the question in one sentence and enumerate the options. For a brief, the option set is the
brief's own (`mctl briefs show <bead>`; a multi-option brief that is adjudicated without naming an
option fails closed with `MOPT001`, which is the gate working). **A derivation that does not name
which option each rule eliminates is not falsifiable and is not a derivation** — the standard
Taylor set on the keystone-ruling bead: *"the derivation must be written out and must name which
ruling eliminates which option, so a reader can falsify it."*

### 2. Enumerate the corpus — the filesystem, not the registry

```bash
cd "$MATHCITY_PACK_ROOT"
ls POLICY-*.md subdomains/*/POLICY*.md
```

Measured 2026-09-18: **16 files match.** `docs/rule-prefix-registry.md` lists 13 prefix rows and
**omits `subdomains/mayor/POLICY.md` and `subdomains/policies/POLICY.md`**, both of which exist on
disk. The registry is authoritative for *prefixes*; it is not a complete inventory of *documents*.
Enumerate the filesystem and reconcile against the registry, never the reverse.

Not every match is a rule-bearing policy: `POLICY-BEAD-REVIVAL.md` has no `| Status |` row at all,
and `subdomains/brief-system/POLICY-DRIFT-AUDIT-2026-08-19.md` is an audit. **No `Status` row = not
Adopted = not citable.**

### 3. Read document status

```bash
for f in POLICY-*.md subdomains/*/POLICY*.md; do
  printf '%-52s %s\n' "$f" "$(grep -m1 -E '^\| Status \|' "$f")"
done
```

Adopted as of 2026-09-18: `POLICY-POLICY.md`, `POLICY-beads.md`, `POLICY-formulas.md`,
`subdomains/brief-system/POLICY.md`, `subdomains/dev/POLICY.md`,
`subdomains/dev/POLICY-city.md`, `subdomains/dev/POLICY-documentation.md`. Everything else is
Draft. **Re-run the command; do not trust this list.** It is a snapshot for orientation, and a
derivation resting on a stale snapshot is a fabricated citation with extra steps.

### 4. Find candidate rules — with more than one pattern

```bash
grep -rniE '<keyword-1>|<keyword-2>' POLICY-*.md subdomains/*/POLICY*.md
```

**A single grep under-reports, measured.** The `- **<ID> ` list form finds 362 rules but finds
**zero** in `POLICY-formulas.md`, `subdomains/dev/POLICY-documentation.md` and
`subdomains/latex/POLICY.md`, which write rules as `**F1.1 — …`, `**DOC1.1 — …`, `**LX1 — …`.
Search by subject-matter keyword across all 16 files, then read the surrounding pillar. **One
failed grep is not evidence of UNDETERMINED** — that is a check that could not have failed's mirror
(a diagnostic that could not have passed), and it is a P6.2 violation to report it as a result.
UNDETERMINED is established by *reading* the domains whose "Applies to" header covers the subject.

### 5. Rule-level adoption gate

For each candidate rule, refuse it if its own title carries `(PROPOSED)`:

```bash
grep -rnE '^-? ?\*\*[A-Z]{1,3}[0-9]+(\.[0-9]+)?[^*]*\(PROPOSED' POLICY-*.md subdomains/*/POLICY*.md
```

27 hits as of 2026-09-18 (`PP1.13`, and 26 CT-rules in `subdomains/dev/POLICY-city.md`). A rule is
citable only if **its document is Adopted AND its own entry is not marked PROPOSED**. Record every
candidate you discarded here and why — a discarded candidate is part of the derivation's evidence.

### 6. Evaluability and contest gates

- `grep -n 'JUDGEMENT RULE' <file>` — a hit on the candidate → `REFUSED_JUDGEMENT`, stop.
- Read the rule's own pass/fail criterion. If it asks a reader to *weigh* something, it is
  judgement-kind whether or not it carries the marker → `REFUSED_JUDGEMENT`, stop.
- If the rule text admits two readings that select different options, or if any open bead, brief,
  ADR or change-log row disputes its meaning → `REFUSED_CONTESTED`, stop, and say which two
  readings.

### 7. Quote at source, verbatim

```bash
grep -n -F '<first eight words of the rule>' <policy-file>
```

Record: **file path, line number, and the quoted text copied from the file** — not retyped from
memory, not paraphrased. The pass bar is that a reader can re-run `grep -n -F` on your quote and hit
your line. A quote that does not reproduce is a fabricated citation and voids the derivation.

### 8. Determine, or find the conflict

For each surviving rule, state **which options it eliminates and which it leaves standing**.

- Exactly one option survives across all cited rules → **DERIVED**.
- More than one survives → **UNDETERMINED** (policy narrows without determining; say so, and say
  which options policy already killed — that is real value even when a decision is still owed).
- Two rules leave disjoint survivors → apply PP6.1 **in order** before calling it a conflict:
  **(a)** an explicit written precedence clause in either domain's POLICY.md wins; **(b)** absent a
  clause, the domain whose `Applies to` header owns the subject matter wins; **(c)** only if
  neither settles it — *"genuinely ambiguous conflicts → defer to the human adjudicator, never
  resolve by inference"* — is it **CONFLICT**. Skipping (a) and (b) manufactures conflicts and
  spends the human decision PP1.10 exists to save.

### 9. Emit the record, including what you did not check

```json
{"question":"<one sentence>","options":["A","B","C"],
 "outcome":"DERIVED|CONFLICT|UNDETERMINED|REFUSED_JUDGEMENT|REFUSED_CONTESTED|REFUSED_STOP_GATE",
 "verdict":"<the determined option, or null>",
 "citations":[{"rule_id":"B2.3","document":"subdomains/brief-system/POLICY.md","line":289,
               "doc_status":"Adopted","rule_proposed":false,
               "quote":"<verbatim>","eliminates":["B","C"]}],
 "discarded_candidates":[{"rule_id":"PP1.13","reason":"rule marked PROPOSED inside an Adopted document"}],
 "consulted":["POLICY-POLICY.md","subdomains/brief-system/POLICY.md"],
 "not_consulted":[{"document":"subdomains/magma/POLICY.md","reason":"Draft — governs nothing (PP2.1)"},
                  {"document":"subdomains/lmfdb/POLICY.md","reason":"not read; subject matter judged unrelated"}],
 "derived_at":"<ISO-8601-utc>"}
```

**`consulted` + `not_consulted` must together account for every file step 2 enumerated.** Silence
about an unread document is how a derivation smuggles in a claim of completeness it never earned.
"Not read" is an acceptable entry; an absent entry is not.

Alongside the JSON, write the human-readable derivation: question, option set, each rule quoted with
what it kills, and the surviving option.

## Routing

| Outcome | Action |
|---|---|
| DERIVED | Hand the record to [[adjudicate-brief]] for recording. Do **not** put it in the human's decision table (PP1.10). If the human must see it, it is a derivation notice, not a decision. |
| CONFLICT | To the human via [[present-it]] / [[present-briefs]], naming both rules verbatim and both readings. The recommendation is which rule should carry the missing precedence clause. |
| UNDETERMINED | To the human as a genuine decision, with the narrowing you did achieve. Where the gap is repeated, the follow-up is a `new-X-policy` proposal — Taylor: *"If we can't make any progress, chances are our policies are too weak and we need to modify them."* |
| Any REFUSED | To the human with the named reason. Never route around it, never re-ask a different way until one answers (CT13.4). |

## ADR 0006 is PROPOSED — this skill does not record

`docs/adr/0006-agents-may-record-policy-derived-verdicts.md` reads
**`Proposed (2026-09-15) … Not adopted.`** It would grant an agent authority to record a real
verdict on a brief when an Adopted rule determines the answer. **That grant is not in force.**

So, today:

- This skill **derives** and hands the derivation to [[adjudicate-brief]]; it never calls
  `mctl briefs adjudicate|defer`, never closes a brief bead, never writes bead or cache state.
- The recording call names a real adjudicator in `--adjudicated-by`. **A derivation is not an
  adjudicator.** Attributing a recorded verdict to this skill's output would assert the ADR's grant
  as though it were adopted, which is forging an authority nobody granted.
- Emitting DERIVED does **not** license auto-execution. Auto-execution is
  [[catch-no-brainer]]'s armed path with its own gates; derivation adds no fifth category until the
  ADR is adopted.

**What changes if ADR 0006 is adopted**, so the delta is one edit and not a rewrite:

1. Derived adjudication becomes a fifth no-brainer category, inheriting the existing stop gates,
   the two-level kill switch and the audit ledger — no second brake.
2. A typed recording surface appears that enforces the rule-level adoption gate in code; this skill
   calls it instead of handing off, and steps 5–7 become its preconditions rather than this file's
   discipline.
3. Stored verdicts cite the governing **document plus verbatim rule text, not the rule ID** (ADR
   0006 §Decision 3 and §Consequences: IDs stay inside the policy system, forbidden in beads,
   briefs and stored verdicts). **Until then this skill emits both** — the ID because PP1.10's own
   text makes it the evidence (*"the determining rule ID is the evidence"*), the verbatim quote
   because that is what a reader can check. If the ADR is adopted, the ID stays in this skill's
   in-session record and is dropped from anything stored on a bead.
4. Independence becomes structural: an agent may never adjudicate a brief it authored.
5. Every derived verdict faces a refutation attempt before it closes, and **refutations are keyed
   by the cited rule** — a high refutation rate condemns the rule, not the agent.

## Pass / fail

**Pass** — every one of these holds:

- The outcome is exactly one of the six, stated as a token, not implied by prose.
- Every cited rule: document Adopted, rule entry not PROPOSED, quote reproduces under `grep -n -F`,
  file+line recorded.
- Every citation names the options it eliminates; DERIVED leaves exactly one standing.
- CONFLICT shows PP6.1(a) and (b) tried and failed before (c) was reached.
- `consulted` + `not_consulted` account for every file step 2 enumerated.
- A judgement-kind or contested rule produced a refusal, not a best guess.
- Nothing was written to a bead, a brief file, or a cache.

**Fail** — any one of these:

- A rule ID that does not resolve, or resolves and does not say what was claimed.
- A Draft document or a PROPOSED rule cited as authority (including PP1.13 — see above).
- DERIVED emitted on a rule that has to be interpreted to reach the verdict.
- UNDETERMINED concluded from one failed grep rather than from reading the owning domains.
- A DERIVED question presented to the human as a decision (PP1.10 violation; the rule ID is the
  evidence against you).
- A refusal rendered as success-shaped output, or worked around by re-asking (CT13.4).

## What this skill does NOT do

- ❌ Record a verdict, close a brief, or write any bead/cache state (that is [[adjudicate-brief]]
  via `mctl`; ADR 0006 is Proposed)
- ❌ Auto-execute anything, or mint a no-brainer category ([[catch-no-brainer]] owns arming)
- ❌ Amend, soften, or reinterpret a rule — encoding implements policy, and on any disagreement the
  Adopted rule text wins (PP1.7)
- ❌ Derive from a Draft policy, a PROPOSED rule, an ADR, a skill's prose, a memory, or a dashboard
- ❌ Derive from a recorded decision bead or a keystone ruling. That is a different authority class
  with its own evidence rules; this skill's authority is Adopted policy **rule text** only, and
  conflating the two is how an unratified reading acquires the look of policy.
- ❌ Pick a reading of a contested rule, or approximate a judgement-kind one
- ❌ Audit running state against policy (that is `check-X-policy` / [[check-zero]])
- ❌ Propose a new rule (that is `new-X-policy`, the sole write path per PP1.4)

## Status

v0.1, 2026-09-18. All counts in this file (16 policy files, 362 enumerated rules, 27 PROPOSED-in-
Adopted, the Adopted/Draft split) were measured on that date and are orientation only — **step 3
and step 5 re-measure them, and the commands, not these numbers, are the contract.**

Cross-references: [[adjudicate-brief]] (recording), [[catch-no-brainer]] (mechanical no-brainer
classes and the arming gates), [[check-zero]] (rule-set quality, PP4.5), [[check-brief-policy]]
(B-rule audit), [[present-it]] / [[present-briefs]] (the human channel), [[mayor-math]] (primary
caller).
