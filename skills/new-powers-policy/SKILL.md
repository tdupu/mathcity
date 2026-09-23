---
name: new-powers-policy
description: >-
  Amend the default workflow settings for latexpowers, mathpowers,
  teachingpowers, or leanpowers with an explicit local-versus-global scope.
  Use when the user says to add, change, or clarify a powers rule, default,
  convention, or quality floor.
---

# Amend powers policy

This skill is the sole route for changing the default behavior of the powers
routers. It supports four targets: `latexpowers`, `mathpowers`,
`teachingpowers`, and `leanpowers`. A change is either **global**—it applies
every time the named power is used—or **local**—it applies only in the named
repository.

## Scope is explicit

Read the user's scope before editing.

- **Global** edits the canonical owning skill(s), so the setting applies in
  future sessions and repositories. Resolve symlinks and edit the canonical
  source; never create a duplicate skill merely to avoid resolving a link.
- **Local** edits the repository-root `POWERS.md`, creating it only when the
  user explicitly requests a local policy and it is absent. A local section
  may add or tighten a global default, but may not silently weaken a global
  quality floor.

If the user names a power but not the scope, ask one question before editing:
“Should this apply globally to `<power>` or only in `<repository>`?” Do not
infer global scope from the fact that the request is made in one repository.
An explicit `global` or `local` request is the authorization for that scoped
change; do not add a second adoption gate.

Do not route a global powers change through a repository-policy skill. In
particular, `new-latex-policy` amends the separate mathcity LX policy; it does
not govern global `using-latexpowers` defaults.

## Power map

| User target | Router to read and amend |
| --- | --- |
| `latexpowers` | `using-latexpowers/SKILL.md` |
| `mathpowers` | `using-mathpowers/SKILL.md` |
| `teachingpowers` | `using-teachingpowers/SKILL.md`; if the setting lives in the delegated teaching workflow, amend that canonical workflow too |
| `leanpowers` | `using-leanpowers/SKILL.md`; if the setting belongs to a named Lean leaf, amend that leaf and retain the router reference |
| `all` | All four rows above, with the rule stated at the weakest common abstraction that is actually valid |

Before writing, read each selected router and resolve its real path. A
compatibility wrapper is not permission to edit an unrelated implementation:
follow its delegation and amend the canonical file that owns the default.

## Local policy format

When the requested scope is local, use this repository-root format:

```markdown
# Powers Policy

This file applies only to this repository. Global powers defaults remain in
force unless this file explicitly tightens them.

## latexpowers

- <local default or convention>

## mathpowers

- <local default or convention>
```

Include only the sections named by the user. Each powers router reads
`POWERS.md` before planning when it exists and applies the matching section.
The file is a repository contract, not a global skill source.

## Amendment procedure

1. Identify the named power(s), the explicit scope, and the smallest owning
   skill or local section.
2. Read the existing text and preserve unrelated worktree changes. State the
   proposed rule in operational terms: what is required, where it applies,
   and what counts as a pass or failure.
3. For global changes, patch only mapped canonical owners. For a local
   change, patch only the repository's `POWERS.md` unless the user separately
   requests a manuscript or source edit.
4. If `all` is selected, check every router for a matching instruction and
   avoid copying a LaTeX-only rule into math, teaching, or Lean text where it
   would be false. Add a domain-specific adaptation or record the rule as
   latexpowers-only.
5. Verify the scope boundary: global changes are visible through the global
   skill entry; local changes are visible only from the selected repository.
   Check that no duplicate skill or policy source was created.
6. Run the relevant skill and repository checks. Report changed paths,
   validation, scope, and commit status. Do not commit or push unless the
   user explicitly asks.

## Definition-format example

When the requested amendment concerns definitions in a LaTeX manuscript, a
global latexpowers rule should say this plainly: when several words are being
defined together, put the definitions in a dedicated `enumerate` environment
with one `\item` per word, rather than hiding them in running prose. If an
immediate consequence follows, close the `definition` environment first and
state that consequence in prose, a remark, or a theorem-class environment
outside the definition. The definition environment contains definitions only.

## Quality floors

- Never change the meaning of a definition merely to satisfy its layout;
  revise the definition and its dependents together when its semantics change.
- Never silently turn a local request into a global amendment or vice versa.
- Never overwrite an existing local policy or canonical router without
  preserving and inspecting its current content.
- A compatibility alias must continue to preserve the user's scope,
  destinations, and active workflow.
