# ADR 0002: Mathcity Subdomain Pack Model

Parent: [../TECHNICAL-SPEC.md](../TECHNICAL-SPEC.md)

## Status

Adopted.

## Decision

Mathcity is a parent Gas City pack with nested child packs under
`subdomains/`. The parent pack owns shared skills, formulas, orders, agents,
policies, tests, and documentation. Each subdomain child pack owns the skills,
policies, and assets for one domain-specific workflow family.

## Naming

| Location | Pack alias shape |
| --- | --- |
| `skills/<name>` | `mathcity.<name>` |
| `subdomains/<sub>/skills/<name>` | `mathcity-<sub>.<name>` |

Examples:

- `skills/work/SKILL.md` materializes as `mathcity.work`.
- `subdomains/dev/skills/improve-documentation/SKILL.md` materializes as
  `mathcity-dev.improve-documentation`.
- `subdomains/lmfdb/skills/search-lmfdb/SKILL.md` materializes as
  `mathcity-lmfdb.search-lmfdb`.

## Consequences

Subdomain README and policy files are part of the public documentation graph.
When a subdomain, skill, or policy is added, update
[../../README-subdomains.md](../../README-subdomains.md),
[../../README-skills.md](../../README-skills.md), and the root
[../../README.md](../../README.md) when the new surface is important enough
for the documentation map.
