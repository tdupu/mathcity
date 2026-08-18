# mathcity-dev

Parent: [../../README-subdomains.md](../../README-subdomains.md)

Pack-development workflow for the owned mathcity pack family
(`mathcity/` + its subdomain child packs, per
[ADR 0002](../../docs/adr/0002-mathcity-subdomain-pack-model.md)).

Contents:

- **[POLICY.md](./POLICY.md)** — the Pack Portability & Boundary Policy:
  four pillars (reproducibility/portability, ownership boundary,
  upstream-change discipline, plan-time impact review) with per-rule
  pass/fail criteria (P1.1–P4.3), the approve/revise/reject/defer verdict
  vocabulary, and the three input shapes (plan doc, beads convoy,
  current-state audit). Source-of-truth for the `check-hygiene` gate skill
  and for priming the mathcity mayor.
- **[POLICY-city.md](./POLICY-city.md)** — runtime city operations policy:
  dispatch, queueing, molecules, observability, interruption, and cleanup.
- **[POLICY-documentation.md](./POLICY-documentation.md)** — documentation
  policy: source-aligned docs, examples, tests, setup, parent links, and the
  `improve-documentation` workflow.

## Filing an issue

One entry point: the **`create-issue`** skill (mathcity pack root). There is exactly
one real copy; the user-level skill directory, the city sink, and `agent-skills` are
**symlinks** to it. A second real `create-issue/SKILL.md` anywhere is drift — delete
it and symlink.

**Target any repository.** `owner/name` is a free parameter; `tdupu/mathcity` is the
default, not a boundary. Name a different repo in the invocation and the skill reads
that target's live templates, labels, and conventions.

**Three kinds, three paths.** Stages 0–4 (resolve target, duplicate search, verify on
current main, design/policy alignment) and the approval gate are universal. After
that the paths diverge:

| Kind | Path |
| --- | --- |
| `bug` | reduce to an MRE if you can · root cause with `file:line` · **≥2 fix candidates** · out of scope |
| `feat` | **wheel check** (why doesn't something existing cover this?) · proposal · alternatives · blast radius |
| `docs` | correction · where · **example usage** (required) · why the current text misleads |

**An MRE is not a filing gate.** A bug may be filed without a reproduction, provided
the gap is explicit — the reproduction field reads `not yet reduced — reduction is
step 1`. Reducing it becomes the first work step, not a precondition for recording
the defect.

**Templates.** The target's live `.github/ISSUE_TEMPLATE/` is authoritative whenever
it exists — it is the enforcement point and it changes without telling you. Targets
with no forms (the common case once targeting is arbitrary) get the canonical shapes
carried inline in the skill, derived from this repo's own richer field set.

**Nothing files before a human approves the exact body** (P3.2). After filing, the
skill offers to work the issue; on yes it routes through a bead into
[`mathcity.work`](../../skills/work/SKILL.md), which takes beads rather than issue
numbers.

**Changing the investigation** means editing
[`template-fragments/issue-investigation-standard.md`](../../template-fragments/issue-investigation-standard.md)
— one copy, read by every surface — not the skill.

## Skills

| Skill | Purpose |
| --- | --- |
| `adjust-workers` | Scale concurrent run-operators on a Gas City rig through the briefed pack-change workflow. |
| `audit-recent-work` | Account for work adjudicated over a session or date range, including brief records, decisions, and in-flight molecules. |
| `check-build-formulas-and-skills` | Audit formula and skill catalog completeness plus formula hygiene. |
| `check-build-hygiene` | Audit the live install (binaries, repos, imports, skill sinks) against POLICY.md; drift list with per-item remediation. |
| `check-city-policy` | Audit a plan, diff, or running-city state against the City Operations Policy. |
| `check-documentation-policy` | Audit mathcity documentation against POLICY-documentation.md and recommend fixes. |
| `check-defer` | Flag places where a framework is making reasoning decisions that should be model calls. |
| `check-formula-hygiene` | Audit one formula or formula-creation skill against POLICY-formulas.md. |
| `check-plan-hygiene` | Gate a plan doc or beads convoy against POLICY.md's four pillars before build; verdicts approve/revise/reject/defer with violated P-rules and a re-derivation brief. |
| `check-wheel` | Check for existing resources before building new machinery and route reinvention concerns through hygiene review. |
| `check-zero` | Survey existing formulas, skills, beads, code, libraries, and known mathematics before building from scratch. |
| `city-status` | Read-only fleet and work-queue snapshot with tmux, sessions, molecules, briefs, and Dolt state. |
| `formula-creator-math` | Create mathcity formula TOML with the required briefed-terminal convention. |
| `formula-work` | Dispatch a bead to the formula-creator-math formula and gate the result behind a human decision brief. |
| `hourly-check` | 12-hour city health watchdog that reports fleet, molecule, brief, and Dolt stalls. |
| `improve-documentation` | Update docs, examples, tests, parent links, and indexes after user-facing changes. |
| `new-city-policy` | Propose and apply a human-gated amendment to POLICY-city.md. |
| `new-documentation-policy` | Propose and apply a human-gated amendment to POLICY-documentation.md. |
| `new-formula-policy` | Propose and apply an amendment to formula policy and the formula-creator hygiene gate. |
| `new-hygiene-policy` | Propose and apply an amendment to `mathcity/subdomains/dev/POLICY.md`; gates every change on human approval and records it in a Change Log before the rule becomes enforceable. |
| `push-the-fleet` | Saturate the fleet by dispatching ready, unblocked beads through the standard briefed work path. |
| `skill-creator-math` | Create a skill in the mathcity pack family and wire both exposure routes (the sanctioned P1.8 procedure). |
| `strand-sweep` | Find slung-but-never-run beads and molecules, dead run targets, orphaned wisps, and deadlocked molecules. |
| `switch-city-worker-provider` | Controlled runbook for switching selected workers between Claude-backed and Codex-backed providers. |
| `testing-work` | Dispatch a bead through the smoke-test-briefed formula for lightweight test execution and a terminal brief. |
| `update-README` | Keep the pack family's READMEs + exposure in sync after any owned-pack change — run at the end of every skill-move or pack-change session. |

Import alias convention (ADR 0002): skills materialize as
`mathcity-dev.<skill>`.

Import independently of the parent pack:

```toml
[imports."mathcity-dev"]
source = "https://github.com/<github-owner>/mathcity/tree/main/subdomains/dev"
```
