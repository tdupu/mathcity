# Documentation Policy

Parent: [README.md](./README.md)

| Field | Value |
| --- | --- |
| Status | Adopted |
| Date | 2026-08-11 |
| Decided | the pack owner |
| Applies to | Public documentation in the mathcity pack family: root READMEs, subdomain READMEs, setup guides, policy explainers, formula/skill/subdomain indexes, example documentation, and user-facing development guides |
| Rule prefix | **DOC** |
| Subordinate to | [POLICY-POLICY.md](../../POLICY-POLICY.md), [POLICY.md](./POLICY.md), [POLICY-city.md](./POLICY-city.md) |
| Enforced by | `check-documentation-policy` |
| Amended by | `new-documentation-policy` |
| Operational updater | `improve-documentation` |

This policy governs the shape and quality of mathcity documentation. It is
written for two audiences: a human user trying to understand and run mathcity,
and agents that must keep the documentation aligned with the pack source.

On conflict, source code and policy win over documentation prose. A doc that
contradicts the source is drift and must be fixed in the same documentation
pass.

---

## Pillar DOC1 — Truth, Portability, And No Slop

**DOC1.1 — Documentation follows source.**
Behavioral claims about formulas, skills, orders, policies, tests, or runtime
commands must match the current source files they describe.
Pass: non-trivial behavior claims can be traced to current source files and do
not contradict them.
Fail: a doc repeats stale behavior, names a removed surface as current, or
claims a command/action exists without source support.

**DOC1.2 — Public docs are portable.**
Public docs must not contain personal names, local usernames, absolute home
paths, private repository names, hostnames, credentials, or machine-specific
instructions. Use placeholders such as `<repo-root>`, `<city-root>`,
`<rig-root>`, `<github-owner>`, and `<repo>`.
Pass: public docs contain only portable placeholders or public URLs.
Fail: public docs expose local/private values or instructions that only work
on one machine.

**DOC1.3 — No slop.**
Documentation must be organized enough that a reader can find the current
source of truth without chasing contradictory, duplicated, orphaned, or
all-over-the-place prose.
Pass: each important topic has one canonical home; related docs are linked;
duplicate explanations either agree or point to the canonical source.
Fail: orphan docs, duplicate competing explanations, stale planned items,
missing parent links, missing index links, or inconsistent names make the
documentation hard to navigate or trust.

## Pillar DOC2 — Navigation Graph

**DOC2.1 — Root README is the entry point.**
The root `README.md` must begin with a concise technical introduction and a
human-readable Documentation Map. The map may be displayed as a hierarchy, but
the hyperlink graph is allowed to contain cross-links.
Pass: a new reader can reach setup, glossary, formulas, skills, subdomains,
policy, testing, mayor/clerk, dolt, and technical-spec docs from the root
README.
Fail: important docs are not reachable from the root README.

**DOC2.2 — Important docs link upward.**
Every important doc below the root must include a `Parent:` link near the top
that points to its immediate parent or to the root README when no closer parent
exists.
Pass: every important doc has a working parent link.
Fail: an important doc has no upward path back to the root documentation map.

**DOC2.3 — Index docs match source.**
`README-formulas.md`, `README-skills.md`, and `README-subdomains.md` are
source-aligned indexes. They must not drift from the formula files, skill
directories, or subdomain pack roots.
Pass: every current formula, skill, and subdomain appears exactly once in its
canonical index, and no stale row remains.
Fail: a missing row, ghost row, wrong alias, wrong path, or inconsistent count.

## Pillar DOC3 — Examples And Tests

**DOC3.1 — User-facing features have examples.**
Every user-facing feature needs a README surface with explicit working examples
for how to use it. Feature-level docs can live in the root README, a feature
README, a subdomain README, or another linked user guide, but they must be
reachable from the Documentation Map.
Pass: each new user-facing feature has a documented example.
Fail: a new user-facing feature ships with no usage example.

**DOC3.2 — Examples declare coverage.**
Feature docs with examples must include or link an `Example Coverage` table with
these columns: Example, Runner, Prerequisites, Command, Test path, Status, and
Issue.
Pass: a reader can tell how each example is run and how it is certified.
Fail: examples appear as untracked code blocks with no runner, prerequisites,
test path, or status.

**DOC3.3 — Documented examples are runnable.**
Every documented example must be runnable from a clean checkout with declared
prerequisites. Examples may require Codex, Claude Code, Gas City agents,
network, GitHub, registry access, Dolt, or model calls, but those requirements
must be explicit.
Pass: each example is classified as local, agent, integration, or planned, and
its command is reproducible under the stated prerequisites.
Fail: a documented example depends on hidden local state, unstated agents, or
unstated credentials.

**DOC3.4 — New features require reasonable tests.**
New user-facing features require tests and examples before completion. Tests
should be the cheapest meaningful certification: smoke, fixture, regression,
or example execution where possible; agent-heavy or costly tests must be routed
through the appropriate briefed test path.
Pass: a new feature has at least one reasonable test tied to its documented
example or behavior.
Fail: a new feature has no test, or only a token-heavy/costly test when a cheap
smoke or fixture test would certify the behavior.

**DOC3.5 — Existing gaps are grandfathered, not ignored.**
Existing features without examples or tests are reported as backlog unless the
current change touches them. Planned or grandfathered gaps must have an issue
link or an explicit issue-needed finding.
Pass: old gaps are visible and tracked.
Fail: old gaps are silently presented as complete documentation.

## Pillar DOC4 — Planned Work

**DOC4.1 — Planned features need issues.**
Planned features may be documented, but they must be clearly labeled planned
and must link to an issue in the mathcity issue tracker.
Pass: every planned feature mention has an issue link or an explicit blocked
issue-filing note.
Fail: planned work is described as future intent with no tracker reference.

**DOC4.2 — Current and planned surfaces are distinct.**
Current behavior, planned behavior, and known gaps must be separated.
Pass: readers can tell what exists now, what is planned, and what is known
missing.
Fail: docs mix future design with current instructions in a way that could make
an agent or user run a nonexistent command.

## Pillar DOC5 — Setup And Operations

**DOC5.1 — SETUP.md covers supported operator environments.**
`SETUP.md` must explain setup from first principles for MacOS, Linux, Windows,
Codex, and Claude Code. If a path is not supported or not yet known to work,
the doc must say so plainly.
Pass: setup docs identify prerequisites, supported/unsupported paths, and
where to go next.
Fail: setup docs imply unsupported environments work or omit major operator
paths.

**DOC5.2 — Dolt setup is separated and linked.**
Bead backup and Dolt remote setup live in `README-dolt.md` or linked Dolt setup
docs, not scattered across unrelated README sections.
Pass: root docs link to the Dolt guide and do not duplicate private setup
details.
Fail: Dolt instructions are duplicated, stale, or mixed into unrelated docs.

**DOC5.3 — Mayor and clerk operations are separated.**
Mayor operation and outside-clerk adjudication must each have their own linked
documentation surface.
Pass: `README-mayor.md` and `README-clerk.md` exist or equivalent docs are
linked, and the root README distinguishes the roles.
Fail: Mayor and clerk duties are conflated or unavailable from the root docs.

## Pillar DOC6 — Documentation Workflow

**DOC6.1 — Feature work runs improve-documentation.**
Any feature change, formula change, skill change, policy change, or user-facing
workflow change must run `improve-documentation` before completion.
Pass: the change includes documentation updates or a recorded N/A reason.
Fail: a user-facing change lands with no documentation pass.

**DOC6.2 — check-documentation-policy is the acceptance audit.**
After a documentation refactor or feature-doc update, run
`check-documentation-policy` and compare its findings against the requested
documentation changes.
Pass: the checker catches the expected requirements and reports no unexplained
drift.
Fail: the checker misses a requested change, reports false current behavior, or
cannot explain how to remediate a finding.

---

## Change Log

### 2026-08-11 — Initial Draft
Created the documentation policy domain inside `mathcity-dev`. Seed rules cover
source-aligned docs, no slop, parent links, example coverage, clean-checkout
runnability, setup docs, Dolt separation, mayor/clerk docs, and the
`improve-documentation` workflow.

### 2026-08-11 — Adopted
Adopted after the documentation-refactor plan was approved. The policy is now
the acceptance checklist for the README refactor, examples/testing docs, and
planned-work issue tracking.
