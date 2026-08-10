# mathcity-dev

Pack-development workflow for the owned mathcity pack family
(`mathcity/` + its subdomain child packs, per
[ADR 0002](../../../docs/adr/0002-mathcity-subdomain-pack-model.md)).

Contents:

- **[POLICY.md](./POLICY.md)** — the Pack Portability & Boundary Policy:
  four pillars (reproducibility/portability, ownership boundary,
  upstream-change discipline, plan-time impact review) with per-rule
  pass/fail criteria (P1.1–P4.3), the approve/revise/reject/defer verdict
  vocabulary, and the three input shapes (plan doc, beads convoy,
  current-state audit). Source-of-truth for the `check-hygiene` gate skill
  and for priming the mathcity mayor.

## Skills

| Skill | Purpose |
| --- | --- |
| `check-plan-hygiene` | Gate a plan doc or beads convoy against POLICY.md's four pillars before build; verdicts approve/revise/reject/defer with violated P-rules and a re-derivation brief |
| `check-build-hygiene` | Audit the live install (binaries, repos, imports, skill sinks) against POLICY.md; drift list with per-item remediation |
| `skill-creator-math` | Create a skill in the mathcity pack family and wire both exposure routes (the sanctioned P1.8 procedure) |
| `update-README` | Keep the pack family's READMEs + exposure in sync after any owned-pack change — run at the end of every skill-move or pack-change session |
| `new-hygiene-policy` | Propose and apply an amendment to `mathcity/subdomains/dev/POLICY.md`; gates every change on human approval and records it in a Change Log before the rule becomes enforceable |

Import alias convention (ADR 0002): skills materialize as
`mathcity-dev.<skill>`.

Import independently of the parent pack:

```toml
[imports."mathcity-dev"]
source = "https://github.com/tdupu/mathcity/tree/main/subdomains/dev"
```
