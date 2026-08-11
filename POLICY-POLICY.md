# Mathcity Policy Governance

Parent: [README.md](./README.md)

| Field | Value |
| --- | --- |
| Date | 2026-07-12 |
| Version | 1.5 |
| Status | Adopted |
| Decided | the pack owner |
| Applies to | All policy documents inside the `mathcity` pack and its subdomains |
| Consumers | `skill-creator-plus`, any `check-X-policy` skill, any `new-X-policy` skill, `brief-prep`, Mayor dispatch |

Governs what a policy document IS, how policy domains are structured, how rules get IDs, how policies are adopted and amended, and how sub-policies relate to their parent. Every rule in every mathcity POLICY.md must be consistent with this document. On conflict, POLICY-POLICY.md wins.

---

## Core definitions

- **Policy domain.** A named scope of decisions that recur often enough to warrant written rules. Examples: brief-system, dev, agent-skills. Each domain has exactly one POLICY.md as its canonical source of truth.
- **Rule.** A named, enumerated, mechanically checkable constraint. Rules are numbered within their domain. Every rule has exactly one ID.
- **Rule ID.** A globally unique, immutable token of the form `<prefix><section>.<number>` (e.g., `B1.4`, `P1.6`, `SK3.1`). Once assigned, a rule ID is never reused, even after deprecation.
- **Trinity.** The three artifacts required for every live policy domain: `POLICY.md` (prose + rules) + `check-X-policy` (read-only auditor) + `new-X-policy` (sole write path for rule changes).
- **Prefix registry.** The file `mathcity/docs/rule-prefix-registry.md` — maps each one-or-two-letter prefix to its owner domain, status, and home path. A domain MUST reserve a prefix there before assigning rule IDs.

---

## Pillar 1 — Policy structure (PP1.x)

- **PP1.1 Every live policy domain has exactly one trinity.** POLICY.md + check-X-policy + new-X-policy. No partial adoption: a domain with a POLICY.md but no check skill is incomplete and the POLICY.md is not enforceable.
- **PP1.2 POLICY.md is the source of truth.** check-X-policy audits against it. new-X-policy amends it. Skills, formulas, and gates.toml cite rule IDs — not prose summaries.
- **PP1.3 check-X-policy is read-only.** It reports drift (approve / revise / defer). It never mutates bead state, files, or config. A check skill that writes anything is a PP1.3 violation.
- **PP1.4 new-X-policy is the sole write path for rules.** Rules enter, change, or exit only by the human adjudicator approving a `new-X-policy` proposal. Editing POLICY.md in place without going through new-X-policy is a violation, even for typo fixes: update via a new-X-policy micro-proposal, commit, done.
- **PP1.5 Rule IDs are globally unique and immutable.** The prefix registry enforces uniqueness across domains. Once a rule ID appears in any committed POLICY.md, it is permanent: the rule may be deprecated (status: deprecated in the rule entry) but the ID is never reassigned to a different rule.
- **PP1.6 Trinity skill naming.** The canonical names are `check-<domain>-policy` and `new-<domain>-policy`. Domains scaffolded before 2026-07-12 that use `-hygiene` as suffix are grandfathered; they must migrate to `-policy` naming on their next major amendment. New domains must use `-policy` naming from initial scaffold.
- **PP1.7 Policy wins over implementation.** On any conflict between an Adopted POLICY.md and an artifact that implements or enforces it (skill, formula, gates.toml entry, script, memory, dashboard), the policy governs. Agents follow the policy; the artifact is drift — file a repair bead same-session. An artifact is never grounds to reinterpret, soften, or effectively amend a rule.
- **PP1.8 Concision.** If two phrasings of a rule produce identical pass/fail outcomes, the shorter is correct. Rule bodies state the requirement and its pass/fail criterion; rationale lives in the Change Log; examples only where the criterion is otherwise ambiguous. Applies to policy documents, not code or skills. Length justified by pass/fail sharpness is never a violation.
- **PP1.9 Minimize bead bloat.** Bead bloat is the memory occupied by the Dolt repo. Policies must prefer designs that minimize it: beads carry identity, state, verdicts, and pointers; bulky artifacts (documents, evidence, transcripts, logs) live in the filesystem keyed by bead ID, with the bead pointing to them. Exception: content required for a bead to be adjudicable stand-alone (a verdict, a one-line rationale) belongs in the bead. A rule mandating bulky content in bead bodies without justifying why file-plus-pointer won't do is a violation.
- **PP1.10 Derived answers are not decisions.** A question whose answer is determined by an Adopted rule is resolved by derivation — act on the rule and cite its ID; never surface it to the human adjudicator as a decision. Surfacing a policy-derivable question is a violation (the determining rule ID is the evidence). Exception: a genuinely ambiguous derivation — two Adopted rules pulling opposite ways with no precedence clause — is a PP6.1(c) conflict and goes to the human adjudicator.
- **PP1.11 Policy set minimality.** Every policy document should satisfy the following property: Let X be the set of policies in the document. There does not exist a subset of policies S that can be replaced by a set of policies T such that T uses less context than S and such that the collection of policies ((X-S) union T) and X are functionally equivalent.
- **PP1.12 Adopted policies are mandatory, not advisory.** Agents, skills, and formulas must comply with every rule in every Adopted POLICY.md within their scope. Citing a rule in output is not a substitute for following it.

---

## Pillar 2 — Policy lifecycle (PP2.x)

- **PP2.1 Lifecycle states: Draft → Adopted → Deprecated.** A POLICY.md in `Status: Draft` governs nothing — it may not be cited in check skills or gate formulas. Only `Status: Adopted` policies are enforceable.

  > **Bootstrap exception:** `POLICY-POLICY.md` itself is exempt from this restriction while in `Status: Draft`; it governs by authorial intent until first adopted. This exception is self-annulling upon adoption.

- **PP2.2 Adoption requires the human adjudicator sign-off.** A Draft transitions to Adopted when the human adjudicator explicitly approves the document in conversation or via a decision bead. The adopting date is recorded in the header table.
- **PP2.3 Amendment goes through new-X-policy.** No in-place edits to an Adopted POLICY.md except via a new-X-policy proposal approved by the human adjudicator. Each change is appended to the Change Log at the bottom of the document with its date and the human adjudicator's rationale.
- **PP2.4 Deprecated rules are tombstoned, not deleted.** A deprecated rule stays in the document with `~~strikethrough~~` title and `Status: deprecated (superseded by <new-id>)`.
- **PP2.5 Revision co-existence.** A Draft revision of an Adopted policy does NOT suspend the Adopted version: the last Adopted text remains in force until the revision is Adopted (one-way ratchet). The revision's header must name the commit hash or date of the Adopted text currently in force. Only one revision Draft may exist per domain at a time.
- **PP2.6 Emergency amendment (hot-fix path).** For active-harm situations (data loss, credential exposure, runaway automation): the human adjudicator's explicit in-conversation approval suffices to apply a rule change immediately, PROVIDED (a) a decision bead records it same-session; (b) the Change Log row is written same-session marked `EMERGENCY`; (c) a retroactive full `new-X-policy` proposal is filed within 7 days or the change auto-reverts to proposal status. This path is not usable for convenience edits — PP1.4's micro-proposal path remains the norm.

---

## Pillar 3 — Sub-policies (PP3.x)

- **PP3.1 Sub-policies are sections first.** A new concern that belongs under an existing domain starts as a lettered section of that domain's POLICY.md with its own rule prefix series (e.g., E-rules for experiments inside brief-system). This is the default for all new rule families.
- **PP3.2 Promotion threshold.** A sub-policy graduates to its own POLICY.md (its own domain + trinity) when ALL THREE hold: (a) the sub-policy has more than 20 enumerated, non-deprecated rule IDs (mechanically counted as `grep -cE '^\- \*\*<prefix>[0-9]'` in the domain's POLICY.md); (b) it has or clearly warrants its own `check-X-policy` skill; (c) it has an independent amendment cadence (changes to it don't co-move with the parent domain). Below this threshold, stay as a section.
- **PP3.3 Rule IDs survive promotion.** When a sub-policy section graduates to its own file, all its rule IDs are preserved unchanged. No renumbering. The prefix registry entry is updated to point to the new file. Cross-references in other policies and check skills need no update.

---

## Pillar 4 — Relationship to gates.toml and formulas (PP4.x)

- **PP4.1 Policy check skills cite rule IDs directly. Pipeline formulas and brief-producing skills cite gate IDs. `gates.toml` is the join layer.**
- **PP4.2 Every gate entry in gates.toml must carry a `rules` field.** The `rules` field is a list of rule IDs that the gate enforces (e.g., `rules = ["B1.5", "B1.7"]`). A gate with no `rules` field is a PP4.2 violation (audited by the domain's check skill (e.g. `check-brief-policy` for brief-system gates)).
- **PP4.3 Gate IDs are never deleted or reused.** A superseded gate gets `required = false` and a `superseded_by` field; its ID remains in the registry permanently.
- **PP4.4 Reverse traceability.** Every rule in an Adopted POLICY.md that is described as "gated" must be named by at least one gate's `rules` field in `gates.toml`. An orphaned gate claim (gate `rules` lists a rule ID that no POLICY.md defines) is also a PP4.4 violation.
- **PP4.5 check-zero required on policy documents.** Before any policy document transitions from Draft to Adopted (PP2.2), and before any new rule proposed via new-X-policy is human-approved, check-zero must be run on the rule set and must pass. A policy that has not passed check-zero cannot be Adopted.

---

## Pillar 5 — Scaffolding new domains (PP5.x)

- **PP5.1 New domains are scaffolded via `skill-creator-plus --policy-domain <name>`.** The scaffolder creates: (a) `POLICY.md` in `Status: Draft` with zero rules and the standard header table; (b) stub `check-<name>-policy` skill with empty audit checklist; (c) stub `new-<name>-policy` skill with proposal template. No rules are pre-populated — rules only enter via the first `new-X-policy` session.
- **PP5.2 Prefix registration is a prerequisite.** Before the scaffolder runs, the caller must have a reserved prefix in `mathcity/docs/rule-prefix-registry.md`. The scaffolder checks this and refuses without it.
- **PP5.3 Skill placement.** `check-X-policy` and `new-X-policy` skills live in the domain's subdomain directory (e.g. `subdomains/<domain>/skills/`) and are exposed to agent sessions via the standard mathcity symlink mechanism. See the dev domain (P1.x) for the concrete filesystem layout.
- **PP5.4 Policy document file naming.** Pack-root policy files are named `POLICY-<kebab-domain>.md` (e.g., `POLICY-beads.md`, `POLICY-POLICY.md`). Subdomain policy files are named `POLICY.md` within their subdomain directory. No other naming form is permitted for new policy documents. Files predating this rule are renamed on first touch (rename-on-touch, not bulk-migrate).

---

## Pillar 6 — Cross-domain relations (PP6.x)

- **PP6.1 Cross-domain precedence.** On conflict between two Adopted domain policies: (a) an explicit written precedence clause in the relevant domain POLICY.md wins; (b) absent a clause, the domain whose "Applies to" header owns the subject matter wins; (c) genuinely ambiguous conflicts → defer to the human adjudicator, never resolve by inference. Every pair of domains that cite each other normatively MUST carry an explicit precedence clause.
- **PP6.2 Normative citations are acyclic.** Cross-domain citations are either normative (imports the other rule's force) or informational. Normative citation edges must form a DAG; a cycle is resolved by demoting one direction to informational and adding a PP6.1 precedence clause.
- **PP6.3 Skill-violates-policy protocol.** When a check skill finds that another skill's behavior contradicts an Adopted rule: (a) the POLICY.md governs — agents follow the policy, not the skill; (b) a follow-up bead is filed against the offending skill in the same session; (c) repeated violation by an auto-executing skill is grounds for engaging the N5 kill-switch hierarchy (`auto_merge_enabled`, city-wide or rig-level). A skill-drift finding with no filed bead is a PP6.3 violation.

---

## Current policy domains

The canonical registry is at `mathcity/docs/rule-prefix-registry.md` (PP5.2). Do not duplicate it here — the registry is the authoritative source of truth for all domain prefixes, home paths, and statuses.

---

## Verdict vocabulary (shared across all policy check skills)

| Verdict | Meaning |
| --- | --- |
| **approve** | Current state is compliant; no action required |
| **revise** | Drift found; each item listed with the rule violated and one-line remediation |
| **defer** | A human call is needed; the open question is stated explicitly |

`check-X-policy` skills never emit **reject** (reject applies only to artifacts, not to audits of running state).

---

## Change Log

| Date | Change | Rationale |
| --- | --- | --- |
| 2026-07-12 | Initial draft | the human adjudicator directive: policy-first rollout of brief system; POLICY-POLICY scaffolds the governance layer |
| 2026-07-12 | v1.0 adoption + 7 amendments (PP2.5, PP2.6, PP4.4, PP6.1-6.3, naming convention PP1.6, citation chain fix, bootstrap self-exception) | the human adjudicator directive: adopt POLICY-POLICY.md and merge all audit improvements from 2026-07-12 Fable policy audit |
| 2026-07-12 | v1.1: add PP1.7 (policy wins over implementation) | the human adjudicator directive; triggered by same-day F4 incident (check-brief-policy enforcing superseded N5 semantics) |
| 2026-07-12 | v1.1: add PP1.8 (concision — shortest faithful phrasing) | the human adjudicator directive: policies must inform humans and agents at minimum token cost |
| 2026-07-12 | v1.1: add PP1.9 (minimize bead bloat) | the human adjudicator directive (bulkiness policy, grilling session): bead bloat = Dolt repo memory; grounds the bead-state/file-content split |
| 2026-07-12 | v1.2: add PP1.10 (derived answers are not decisions) | the human adjudicator directive after the gate-table-authority question (answer already determined by PP1.2/PP1.7): "that is a no-brainer, because policy is the source of truth… that is a policy" |
| 2026-07-12 | v1.2: PP6.3 parenthetical repointed from dead `ALLOW_NO_BRAINER_AUTO_EXECUTE` to the N5 `auto_merge_enabled` hierarchy | PP1.7 drift fix (F8); N5 semantics superseded 2026-07-12 |
| 2026-07-12 | v1.2: PP1.8 concision — rationale clauses moved out of PP1.2 (rule-ID citations survive renumbering/deprecation) and PP2.4 (tombstones preserve audit trails and prevent ID reuse) into this log | PP1.8 compliance (post-as-36nz verification findings); pass/fail outcomes unchanged |
| 2026-07-19 | v1.3: add PP1.11 (policy set minimality — no subset S replaceable by a smaller T without changing functional equivalence) | the human adjudicator directive verbatim (Q19) |
| 2026-07-19 | v1.4: add PP1.12 (adopted policies mandatory, not advisory — compliance required, not just citation) and PP4.5 (check-zero required before adoption and before any new-X-policy rule is approved) | the human adjudicator directive (Q19): #67 adjudication — "policies must be enforced"; "check-zero should be run over all policies" |
| 2026-07-19 | v1.5: add PP5.4 (POLICY-<domain>.md naming convention for pack-root policy files; rename-on-touch for pre-convention files); rename BEADPOLICY.md → POLICY-beads.md (first application); create subdomains/policies/ for policy management skills | the human adjudicator directive (Q19): #68 adjudication — "there should be a POLICY-skills.md, all policies should follow this naming convention" |
| 2026-07-23 | v1.6: remove stale italic note from PP6.1 ("Known instance without a clause: brief-system (B3.7) ↔ bead-policy (BP2.4)") — both sides now carry a resolving clause; PP1.10's mention of "no precedence clause" (concept explanation) left intact | the human adjudicator directive (#24): stale-instance cleanup — the named pair is resolved, so the remediation note no longer applies |
