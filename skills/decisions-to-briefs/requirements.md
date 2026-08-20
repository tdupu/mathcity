---
schema: gc.build.requirements.v1
workflow:
  id: gsp-ycmp6
  formula: build-basic-briefed
methodology:
  pack: gascity
  name: build-basic
producer:
  formula: build-basic-briefed
  stage: requirements
  attempt: 1
status: approved
trace:
  upstream:
    - path: beads/gsp-jrtme
      hash: bead:gsp-jrtme
    - path: beads/gsp-ymhs5
      hash: bead:gsp-ymhs5
    - path: beads/gt-hjk388
      hash: bead:gt-hjk388
    - path: mathcity/subdomains/brief-system/skills/decisions-to-briefs/SKILL.md
      hash: git:HEAD
  coverage:
    - id: REQ-001
      status: covered
    - id: REQ-002
      status: covered
    - id: REQ-003
      status: covered
    - id: REQ-004
      status: covered
    - id: REQ-005
      status: covered
    - id: REQ-006
      status: covered
---

# Requirements: decisions-to-briefs SKILL.md — git-op action-block prohibition

## Coverage

| ID | Status |
| --- | --- |
| REQ-001 | covered |
| REQ-002 | covered |
| REQ-003 | covered |
| REQ-004 | covered |
| REQ-005 | covered |
| REQ-006 | covered |

## Problem Statement

The `decisions-to-briefs` skill's action-block safety invariant does not
explicitly prohibit git **commit** operations. During Q18 (incident gt-hjk388),
an autonomous Fable fork executing `decisions-track` action-blocks committed
directly to `~/repos/hecke` (commits 2e8d5c0 + 4c4b3fc) without passing
through the `authorize-git-operation` gate. The fork treated commits as
"reversible dispatch" (the invariant only named push / force-push / merge /
branch or tag deletion), leaving a loophole.

The SKILL.md must be updated so that **all** git operations — including local
commits — are explicitly prohibited in action-blocks for autonomous forks and
classified as `external-reminder` / `stays-out` shape, requiring Taylor's
manual authorization via `authorize-git-operation` before any git write occurs.

## W6H

| Dimension | Answer |
|---|---|
| **Who** | Autonomous forks (Fable workers, GC agents, polecats) executing decisions-track action-blocks |
| **What** | Git operations — commit, push, force-push, merge, cherry-pick, rebase, branch/tag delete — appearing in action-block items without passing the `authorize-git-operation` gate |
| **When** | At brief adjudication time, when the verdict edge parses and acts on an action-block |
| **Where** | `decisions-to-briefs` SKILL.md — §ACTION-BLOCK schema and §HARD SAFETY INVARIANT — and the action-block schema documentation it governs |
| **Why** | Taylor must authorize all git writes; an autonomous fork treating commits as reversible dispatch bypasses that gate and creates an unaudited git history |
| **How** | Extend the prohibited-operations list to cover commits; add an explicit autonomous-forks rule; update the rationalization table with the bypass pattern |

## User Stories

- **US-1 (Mayor, decision-filing):** As a Mayor session drafting a brief whose verdict might involve a git op, I need the skill to classify any git write as `stays-out` so the action-block is `external-reminder` and I cannot accidentally auto-execute a commit.
- **US-2 (Autonomous fork, action-block executor):** As an autonomous Fable worker acting on a verdict edge, I need the action-block schema to make git ops impossible to express as auto-executable items, so I always surface them as external tasks to Taylor.
- **US-3 (Taylor, security auditor):** As Taylor reviewing the skill, I need the SKILL.md to explicitly enumerate git commits (not just git push/merge) as prohibited, closing the Q18 loophole, so I can trust future forks will not commit silently.

## Technical Stories

- **TS-1:** Extend the §ACTION-BLOCK schema's action-item-types table with a `PROHIBITED` category row listing `git-commit`, `git-push`, `git-merge`, `git-cherry-pick`, `git-rebase`, `git-tag`, and `git-branch-delete` as types that MUST NOT appear in auto-executable action-items. These are not valid action-item `type` values; any brief that includes them is malformed.
- **TS-2:** Add an explicit `autonomous-fork` invariant paragraph to §HARD SAFETY INVARIANT: "Autonomous forks (no Taylor terminal) must express ALL git operations — including local commits — as `external-reminder`. There is no size or reversibility exemption: a local commit is a git write."
- **TS-3:** Update the §Shape classification table: add or clarify that any decision whose approved verdict would produce a git write is `stays-out`, not `compact y/n`, regardless of the write's local/remote scope.
- **TS-4:** Extend the rationalization table (red flags) with a new row: `"It's just a local commit, not a push"` → `"A commit IS a git write. git push makes it public; the commit is still irreversible from Taylor's audit trail perspective."`.
- **TS-5:** Preserve all existing functionality for non-git-op decisions: `sling-bead`, `file-follow-up-brief`, `wire`, `close-supersede`, and read-only `run-skill` continue to work as specified.

## Behavior Requirements

- **BR-1** (REQ-001): The skill MUST explicitly list `git commit` (and equivalents: `git cherry-pick`, `git rebase`, `git merge --ff-only`) in the prohibited-operations set alongside `git push / force-push / merge / branch or tag deletion`.
- **BR-2** (REQ-002): The skill MUST include a named rule that autonomous forks (no interactive terminal) MUST classify all git-op decisions as `external-reminder`, with no exception for "tiny" or "reversible-seeming" git writes.
- **BR-3** (REQ-003): The action-block schema documentation MUST add a `PROHIBITED` note or table row making it clear that action-blocks expressing git operations are malformed.
- **BR-4** (REQ-004): The rationalization table MUST include the "just a local commit" bypass pattern, with a corresponding reality correction.
- **BR-5** (REQ-005): The §Shape classification table MUST reflect that any decision whose verdict produces a git write is `stays-out` regardless of scope (local vs. remote).
- **BR-6** (REQ-006): The skill MUST remain backward-compatible with all existing valid action-block items (`sling-bead`, `file-follow-up-brief`, `wire`, `close-supersede`, `run-skill`, `external-reminder`, `snooze`).

## Example Mapping

### Example 1 — Git commit blocked at brief-authoring time

- **Given** a decision "apply patch X to ~/repos/hecke" is being briefed
- **When** the author classifies the decision shape
- **Then** the shape is `stays-out` (git write, regardless of remote scope)
- **And** the action-block contains only `external-reminder` items
- **And** no `git-commit` action-item type is used (it is prohibited)

### Example 2 — Fork encounters git-op action-block

- **Given** an autonomous fork is acting on a verdict edge
- **And** the action-block contains an `external-reminder` item with note "run authorize-git-operation to commit X"
- **When** the fork processes the action-block
- **Then** the fork surfaces the reminder to Taylor via mail/nudge but does NOT execute any git command
- **And** the fork records the verdict and closes its step bead

### Example 3 — Non-git dispatch remains auto-executable

- **Given** a decision "sling bead gsp-abc to the fleet" is being briefed
- **When** classified
- **Then** the shape is `compact y/n` and the action-block uses `{type: sling-bead, target: gsp-abc}`
- **And** the verdict edge auto-dispatches it (no `authorize-git-operation` needed)

## Acceptance Criteria

- **AC-1** (→ REQ-001): The updated SKILL.md MUST enumerate `git commit` explicitly in the prohibited-operations list in §HARD SAFETY INVARIANT. Grep test: `grep -i "git commit" SKILL.md` must match.
- **AC-2** (→ REQ-002): The updated SKILL.md MUST contain an explicit sentence scoped to "autonomous forks" prohibiting git ops, not relying only on the generic invariant. Grep test: `grep -i "autonomous" SKILL.md` must match.
- **AC-3** (→ REQ-003): The action-block schema section MUST contain a `PROHIBITED` heading or table row. Grep test: `grep -i "prohibited" SKILL.md` must match.
- **AC-4** (→ REQ-004): The rationalization table MUST include a row mentioning "local commit" or equivalent bypass. Grep test: `grep -i "local commit" SKILL.md` must match.
- **AC-5** (→ REQ-005): `stays-out` row in the shape classification table MUST reference git writes explicitly (not just "irreversible"). Grep test: `grep -i "git" SKILL.md` inside the shape table context.
- **AC-6** (→ REQ-006): A `sling-bead` action-item in a non-git decision brief MUST still be valid (no breakage of existing action-item types). Verified by critical-review of the updated skill against the 14-item decision-track calibration run.

## Out Of Scope

- Implementing the actual verdict-edge executor (part b of gsp-ft64) — the action-block schema is declarative; this update changes only the schema documentation and safety rules.
- Changing the `authorize-git-operation` skill — that skill's scope is unchanged.
- Adding any new action-item types beyond fixing the prohibited gap.
- Altering how non-git reversible dispatch works.
- Changing the `external-reminder` type semantics — only its mandatory usage for git ops is being clarified.

## Open Questions

- **OQ-1:** Should `git commit --amend` be treated identically to a fresh commit (both `stays-out`)? Presumed yes; record in the updated invariant. Raise to Taylor if the plan author disagrees.
- **OQ-2:** Is there a need for a machine-readable `prohibited_action_types` list in the front matter of the SKILL.md (for future schema validators), or is prose sufficient for v0.2? Default: prose is sufficient; file a follow-up bead if the verdict-edge executor needs schema introspection.
