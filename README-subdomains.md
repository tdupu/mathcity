# Subdomains Index

Parent: [README.md](./README.md)

Canonical index of mathcity child packs under `subdomains/`.

| Subdomain | Pack | Purpose | README | Policy |
| --- | --- | --- | --- | --- |
| `brief-system` | `mathcity-brief-system` | Decision pipeline: brief formulas, gates, orders, and review agents. | [README](./subdomains/brief-system/README.md) | [POLICY](./subdomains/brief-system/POLICY.md) |
| `computing` | `mathcity-computing` | Heavy computation workflows, Magma/Sage/PARI runs, UPF jobs, and computation result briefs. | [README](./subdomains/computing/README.md) | [POLICY](./subdomains/computing/POLICY.md) |
| `dev` | `mathcity-dev` | Pack development, policy, hygiene checks, formula/skill creation, documentation policy, and city operations policy. | [README](./subdomains/dev/README.md) | [POLICY](./subdomains/dev/POLICY.md) |
| `latex` | `mathcity-latex` | Notes-tier LaTeX screening, label/reference checks, and LaTeX workflow policy. | [README](./subdomains/latex/README.md) | [POLICY](./subdomains/latex/POLICY.md) |
| `lmfdb` | `mathcity-lmfdb` | LMFDB queries, database pipelines, object serialization, and schema/type workflows. | [README](./subdomains/lmfdb/README.md) | [POLICY](./subdomains/lmfdb/POLICY.md) |
| `magma` | `mathcity-magma` | Magma package standards, README/test conventions, profiling, and package hygiene. | [README](./subdomains/magma/README.md) | [POLICY](./subdomains/magma/POLICY.md) |
| `proof-assist` | `mathcity-proof-assist` | Proof-assistant and search surfaces for Lean/Mathlib, Stacks, arXiv, and scholarly lookup. | [README](./subdomains/proof-assist/README.md) | none |

## Maintenance

Run `mathcity-dev.improve-documentation` after adding, removing, or renaming a
subdomain. Run `mathcity-dev.check-documentation-policy` to verify this table
matches the `subdomains/*/pack.toml` roots.
