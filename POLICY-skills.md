# Mathcity Skills Policy

Parent: [README.md](./README.md)

| Field | Value |
| --- | --- |
| Status | Draft |
| Date | 2026-07-21 |
| Decided | the pack owner |
| Applies to | Creation, placement, exposure, naming, and lifecycle of skills across the mathcity pack family and its agent-skills consumers (all subdomains, all agents) |
| Consumers | `skill-creator-math`, `skill-creator-plus`, `check-skill-hygiene`, `new-skills-policy`, `update-README`, mayor priming (`mayor-math`), any agent adding/moving/renaming a skill |

Governs how skills come into existence, where they live, how they are exposed to both sinks (plain sessions + city agents), how they are named and indexed, and when a skill may be retired. On conflict with POLICY-POLICY.md, POLICY-POLICY.md wins.

Rule prefix: **SK** (reserved in `mathcity/docs/rule-prefix-registry.md` per PP5.2).

Relationship to the dev domain (P-rules): the concrete filesystem-exposure mechanics for pack skills currently live in `subdomains/dev/POLICY.md` (P1.3, P1.8, P1.12–P1.14, P1.16). Those P-rules remain in force and authoritative until, and unless, a `new-skills-policy` session migrates the skill-lifecycle subject matter into SK-rules. Per PP3.1 (sub-policies are sections first) and PP6.1 (cross-domain precedence), any SK-rule that touches skill exposure MUST carry an explicit precedence clause against the corresponding P-rule at the time it is added. Until the first SK-rule is adopted, this document reserves the domain and asserts no independent rules.

---

## Rules

None yet.

Per PP5.1, a newly scaffolded policy domain carries **zero pre-populated rules** — rules enter this document only through a human-approved `new-skills-policy` proposal (PP1.4, the sole write path). Per PP2.1 this Draft governs nothing until Adopted (PP2.2); it may not be cited in check skills or gate formulas while in Draft. Its purpose today is to reserve the **SK** domain under the PP5.4 pack-root naming convention (`POLICY-skills.md`), as directed by the human adjudicator's #68 adjudication ("there should be a POLICY-skills.md, all policies should follow this naming convention").

Trinity status (PP1.1): `POLICY-skills.md` (this file) exists; `check-skill-hygiene` is the interim read-only auditor and should migrate to `check-skills-policy` per PP1.6 on the first SK amendment; `new-skills-policy` is the write path. The domain is **incomplete** (PP1.1) and therefore unenforceable until its first SK-rule is adopted and the trinity is confirmed.

---

## Change Log

| Date | Change | Rationale |
| --- | --- | --- |
| 2026-07-21 | Initial Draft scaffold; zero rules; SK prefix registry row repointed from `agent-skills/POLICY.md` to `POLICY-skills.md` (pack root, PP5.4) and status Pending → Draft | the human adjudicator directive (Q19): #68 adjudication — "there should be a POLICY-skills.md, all policies should follow this naming convention" |
