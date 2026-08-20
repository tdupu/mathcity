# Policies Subdomain

Home for policy management skills in the mathcity pack.

## Purpose

This subdomain houses the meta-policy and cross-domain policy management
skills: skills that CREATE, CHECK, or AMEND policy documents rather than
enforce domain-specific rules.

## Skills (migration target)

The following skills from the mathcity root and agent-skills should migrate
here (tracked in a follow-up bead per PP1.12 + amendment B):

**Meta-policy:**
- `check-policy-policy` — audits POLICY-POLICY.md compliance
- `new-policy-policy` — amends POLICY-POLICY.md
- `new-policy-type` — scaffolds new policy domain trinities

**Cross-cutting policy management:**
- `new-skills-policy` — amends agent-skills placement policy
- `check-gc-policies` — audits gascity-level policies

**Domain-specific policy skills** stay in their own subdomain
(e.g., `check-brief-policy` stays in `subdomains/brief-system/`).

## Naming

All pack-root policy files follow `POLICY-<kebab-domain>.md` (PP5.4).
This subdomain's own policy file is `POLICY.md` per PP5.3.
