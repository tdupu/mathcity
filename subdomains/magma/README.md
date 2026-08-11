# mathcity-magma

Parent: [../../README-subdomains.md](../../README-subdomains.md)

Standards for Magma packages in mathcity-governed project repos
(reference implementation: `hecke`'s `magma/` tree). Nested child pack of
`mathcity/` per
[ADR 0002](../../docs/adr/0002-mathcity-subdomain-pack-model.md).

Contents:

- **[POLICY.md](./POLICY.md)** — the Magma Packages Policy: seven pillars
  (package structure & naming, README requirements, testing, bead-package
  coupling, profiling, pipeline connections, dependency rules) with
  per-rule pass/fail criteria (M1.1–M7.5), an anti-pattern audit table,
  and a Change Log. Source-of-truth for the `check-magma-hygiene` gate;
  amendments follow the `new-hygiene-policy` pattern.

## Skills

| Skill | Purpose |
| --- | --- |
| `check-magma-hygiene` | Audit a package, diff, or whole Magma project against POLICY.md's M-rules; verdicts approve/revise/fail with rule IDs and triggering files |
| `new-magma-package` | Scaffold a policy-compliant new package: header block, spec entry, README section stub, test stub, tracking bead |

Related skills in sibling packs: `improve-package-README`,
`profile-magma`, `mag-to-notebook`, `notebook-to-mag`,
`notebook-to-package` (mathcity-computing); `magma-to-textfile`,
`textfile-to-magma`, `magma-to-lmfdb-object`, `database-to-magma`
(mathcity-lmfdb); `is-good-test` (mathcity parent).

Import alias convention (ADR 0002): skills materialize as
`mathcity-magma.<skill>`.

Import independently of the parent pack:

```toml
[imports."mathcity-magma"]
source = "https://github.com/<github-owner>/mathcity/tree/main/subdomains/magma"
```
