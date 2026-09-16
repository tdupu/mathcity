# Glossary

Parent: [README.md](./README.md)

Canonical vocabulary for mathcity documentation. This is terminology, not a
policy document; binding rules live in the `POLICY*.md` files.

| Term | Meaning |
| --- | --- |
| Adjudication | A human verdict on a brief: approve, reject, revise, or defer. The verdict is recorded by `adjudicate-brief`. Only a human adjudicates — see **Derivation** and **Relay** for the two other acts that also end in a recorded verdict, and are not this one. |
| Derivation | Computing a brief's verdict from an adopted rule and recording it with that rule quoted. The agent is the *authorizer*; the rule is the *authority*. Mandated rather than optional: the policy-policy makes surfacing a policy-derivable question a violation. A derivation must be **written out and name which rule eliminates which option, so a reader can falsify it** — pointing at a rule is not a derivation. |
| Derived verdict | The record a Derivation produces. Names the governing document and quotes the rule text **verbatim**; it does not cite a rule ID, because IDs are not stable enough to survive as an audit trail. The cited rule must be **individually** adopted — adoption is per rule, and an Adopted document may still contain individually PROPOSED rules that govern nothing. |
| Relay | Recording a verdict *someone else* reached. Calling the relay tool does not make the caller the adjudicator. Distinct from both Adjudication (deciding) and Derivation (computing). |
| Attestation | The recorded identity of whoever rendered a verdict. A verdict without it is **undeterminable** — not trusted-by-default — and fails closed at dispatch. No migration can supply it after the fact; the only remedy is a fresh approve. |
| Self-adjudication | The same agent session BOTH authored and approved a brief. Blocked at write time and again at dispatch. Note what it is *not*: an agent adjudicating another author's brief is independent and permitted — the refusal text asks for "an independent adjudicator", not for a human. |
| Agent | A Codex, Claude Code, or Gas City managed worker session that performs a bounded role. |
| Artifact | A file, branch, test result, plan, issue body, PR body, or other durable output that a brief asks a human to judge. |
| Bead | A durable work record in `bd`. Beads carry task state, dependencies, ownership, and links to larger artifacts. |
| Bead prefix | The leading token of a bead ID (`gsp-`, `mc-`, `he-`). It names the store the bead **originated in**, which is not necessarily the store it currently lives in — beads migrated from a retired store keep their origin prefix (ADR 0003). Do not infer a bead's current location from its prefix. |
| Brief | A decision artifact that explains what happened, what evidence exists, what gates passed, and what human decision is needed. Brief beads are `type=decision`. |
| Brief operator | The `mathcity.brief-operator` agent that runs deterministic brief-pipeline formula steps. It does not adjudicate. |
| Check skill | A read-only auditor that reports policy drift, for example `check-documentation-policy` or `check-city-policy`. |
| Clerk | An outside session that drains the brief stack for human adjudication using `present-briefs` and `adjudicate-brief`. |
| Formula | A Gas City TOML workflow made of ordered steps. Mathcity formulas live in `formulas/` and are indexed in `README-formulas.md`. |
| Gate | A policy or quality check that a brief must satisfy before promotion to the stack. Gates may be mechanical, review, stop, or manual gates. |
| Integration example | A documented example that needs an external system such as GitHub, a registry, Dolt, network access, a model, or a live city. |
| Legacy tree | A copy of the mathcity pack living inside `gascity-packs/` (`~/gt/gascity-packs/mathcity`, `~/repos/gascity-packs/mathcity`), retired in favour of `tdupu/mathcity`. Not a fork and not a checkout — a vendored copy in a different repository. |
| Local example | A documented example that runs from a clean checkout with ordinary local dependencies. |
| Mayor | The city coordination role. The Mayor supervises city progress and coordination, but should not be confused with the clerk's brief-reading duty. |
| No-brainer | A brief resolvable **without spending a human decision** — by obviousness (a skilled reviewer would approve without hesitation) or by Derivation from an adopted rule. The two are different and cross-cutting: a brief can be obvious with no rule covering it, or forced by composed rules nobody would guess from a summary. Auto-execution is **ON by default**; the kill switches are brakes, not gates. Stop gates always block regardless of category — server-touching, user-skill-touching, LaTeX, and mathematical content. *(Corrected 2026-09-15: the prior entry said "compact handling", a body shape retired by ADR 0001, and scoped the term to "mechanically safe", which excludes derivation.)* |
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
