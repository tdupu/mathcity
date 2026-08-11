# Glossary

Parent: [README.md](./README.md)

Canonical vocabulary for mathcity documentation. This is terminology, not a
policy document; binding rules live in the `POLICY*.md` files.

| Term | Meaning |
| --- | --- |
| Adjudication | A human verdict on a brief: approve, reject, revise, or defer. The verdict is recorded by `adjudicate-brief`. |
| Agent | A Codex, Claude Code, or Gas City managed worker session that performs a bounded role. |
| Artifact | A file, branch, test result, plan, issue body, PR body, or other durable output that a brief asks a human to judge. |
| Bead | A durable work record in `bd`. Beads carry task state, dependencies, ownership, and links to larger artifacts. |
| Brief | A decision artifact that explains what happened, what evidence exists, what gates passed, and what human decision is needed. Brief beads are `type=decision`. |
| Brief operator | The `mathcity.brief-operator` agent that runs deterministic brief-pipeline formula steps. It does not adjudicate. |
| Check skill | A read-only auditor that reports policy drift, for example `check-documentation-policy` or `check-city-policy`. |
| Clerk | An outside session that drains the brief stack for human adjudication using `present-briefs` and `adjudicate-brief`. |
| Formula | A Gas City TOML workflow made of ordered steps. Mathcity formulas live in `formulas/` and are indexed in `README-formulas.md`. |
| Gate | A policy or quality check that a brief must satisfy before promotion to the stack. Gates may be mechanical, review, stop, or manual gates. |
| Integration example | A documented example that needs an external system such as GitHub, a registry, Dolt, network access, a model, or a live city. |
| Local example | A documented example that runs from a clean checkout with ordinary local dependencies. |
| Mayor | The city coordination role. The Mayor supervises city progress and coordination, but should not be confused with the clerk's brief-reading duty. |
| No-brainer | A brief classified as mechanically safe enough for compact handling under the no-brainer gates and kill-switch rules. |
| Order | A scheduled or event-triggered Gas City automation that runs a formula. Orders wire formulas to runtime events or cooldowns. |
| Pack | A composable Gas City bundle containing skills, formulas, orders, agents, policies, and configuration. |
| Parent link | A documentation link near the top of an important doc that points back to its immediate parent doc or the root README. |
| Pile | The staging area for produced briefs before gate checking and stack promotion. |
| Policy | A versioned source of truth with rule IDs and pass/fail criteria. Policies are audited by check skills and amended by new-policy skills. |
| Rig | A managed repository inside a Gas City city. A rig has its own beads and work context. |
| Skill | A local instruction bundle in a `SKILL.md` file. Skills are indexed in `README-skills.md`. |
| Stack | The set of briefs ready for human presentation after pile gating and shuffle promotion. |
| Subdomain | A child pack under `subdomains/` that owns a specialized domain such as computing, LaTeX, LMFDB, or pack development. |
| Test evidence | Commands, results, logs, and interpretation showing that a claim was tested or explicitly marked not applicable. |
| Work front door | The user-facing dispatch surface `mathcity.work`, which routes beads to the correct briefed workflow. |
