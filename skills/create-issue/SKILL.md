---
name: create-issue
description: File a high-quality GitHub issue against the canonical mathcity repo `tdupu/mathcity` (the default), with `tdupu/gascity-packs` and `gastownhall/gascity` as declared alternatives. Runs the full investigation a maintainer would otherwise redo (duplicate search, verify-the-problem-exists-on-current-main, design/policy alignment, blast radius, file:line root-cause refs, >=2 fix candidates, required MRE for bugs), fills the target repo's LIVE `.github/ISSUE_TEMPLATE/` form, and stops at a human approval gate before anything is filed. Trigger phrases "create an issue", "file an issue", "write an issue for X", "open an issue about X", "report this bug", "file this against mathcity", "file this against gascity". Use this whenever the target is a tdupu-owned repo or whenever the target is passed explicitly; the upstream `contributing.write-issue` skill covers external-contributor filing to `gastownhall/gascity` with no targeting parameter. For the dispatchable, brief-pipeline version of the same standard, sling the `mathcity-issue-briefed` formula instead.
---

# create-issue

The interactive surface of the MathCity issue workflow. A human is in the loop; you
investigate with them, draft against the target repo's live template, and stop for a
verdict before filing.

**The investigation standard is not in this file.** It lives in one place:

> **[`template-fragments/issue-investigation-standard.md`](../../template-fragments/issue-investigation-standard.md)**

Read it now, in full, before touching anything. This skill contributes the
interactive scaffolding around it — target resolution, the human checkpoints, and
the approval gate. The dispatchable sibling `mathcity-issue-briefed` reads the same
fragment. When the standard changes, it changes there, once.

## Why this exists rather than upstream `write-issue`

Upstream [`contributing/skills/write-issue`](https://github.com/gastownhall/gascity-packs/tree/main/contributing/skills/write-issue)
has the right discipline and the wrong target: it names `gastownhall/gascity` in
nine places, so every MathCity use requires re-substituting the repo by hand. Issues
#7–#11 on `tdupu/mathcity` were filed correctly only because each subagent was told
in its prompt to make that substitution — a load-bearing instruction that lives in a
prompt is one that eventually gets forgotten, and the failure is silent (the issue
lands, on the wrong tracker).

Here the target is a **declared parameter with a default**, and the default is the
canonical `tdupu/mathcity`. Upstream's skill is not modified and not copied: it is
`gascity-packs`-owned and read-only to us (`subdomains/dev/POLICY.md` P2.1);
vendoring it would create a second real copy that P1.9 forbids and that P2.1 makes
impossible to deduplicate.

> **Naming.** This skill was `write-issue-targeted` through 2026-08-13. It was
> renamed to `create-issue` to match the verb its own formula already uses
> (`create-issue-briefed`) and the rest of the parent pack (`create-brief`,
> `create-convoy`, `create-artifact`). Same skill, same standard, one copy — the old
> name is gone, not deprecated-in-place, because two SKILL.md files competing for the
> same trigger phrases is the failure `xkcd-927` describes.

## Pre-flight (P1.14)

Probe before starting. If a dependency is missing, stop with the actionable form:

```bash
command -v gh >/dev/null 2>&1 || echo MISSING_GH
gh auth status >/dev/null 2>&1   || echo MISSING_GH_AUTH
```

- `gh` absent →
  `I'm sorry, I can't do that — the GitHub CLI (gh) is not installed. Install it (brew install gh), then re-run. (gh is how this skill searches for duplicates, reads the target repo's live issue templates, and files the approved issue.)`
- `gh auth status` non-zero →
  `I'm sorry, I can't do that — gh is installed but not authenticated. Run gh auth login, then re-run. (Without auth the duplicate search silently returns nothing, which reads exactly like "no duplicates" and is the worst possible failure mode here.)`

A checkout of the target repo is needed for stage 3 (verify-on-main) and stage 4
(design/policy corpus). If you do not have one, say so and offer the `gh api`
fallback in the fragment's stage 8 — but be explicit that a filing without stage 3 is
caveated, not complete.

## Step 1 — Resolve the target repo, out loud

**First action, before any investigation.** Do not begin work against an assumed
repo. Follow the fragment's stage 0 table and then state the resolution back:

> Target: `tdupu/mathcity` (default — this is a mathcity pack surface).
> Kind: `bug`. Templates read from `tdupu/mathcity@main:.github/ISSUE_TEMPLATE/`.

Resolution order:

1. **The human named a repo** → use it. Validate it is one of the three recognized
   targets; an unrecognized target is allowed but must be confirmed explicitly
   ("You asked for `owner/name`, which isn't a recognized target — confirm?").
2. **The human named a surface, not a repo** → map it with the stage 0 table. A `gc`
   or `bd` binary behavior maps to `gastownhall/gascity`; anything in this pack maps
   to `tdupu/mathcity`.
3. **Neither** → default to `tdupu/mathcity` and **say that you are defaulting**, so
   a wrong default is corrected in one sentence instead of after filing.

If the observation spans both a binary and a pack surface, the fragment's stage 0
routing rules require **two cross-linked filings**. Say so before starting; it
changes the shape of the work.

## Step 2 — Walk stages 1–7 of the standard

Work through the fragment's stages in order, with the human. Do not skip ahead; the
ordering is the point (a duplicate found at stage 2 saves the whole investigation).

Checkpoint with the human at three places rather than running to the end:

| After | Report | Because |
| --- | --- | --- |
| Stage 2 (duplicates) | the matches you found and your read of them | a match usually ends the task — comment instead of filing |
| Stage 3 (verify on main) | which finding-table row you landed on | "already fixed on main" ends the task too |
| Stage 7 (fix candidates) | the ≥2 candidates and your recommendation | this is the part a maintainer will actually argue with |

**Do not fabricate to fill a stage.** If stage 3 could not run because you have no
checkout, say "stage 3 not run — no checkout" rather than asserting the code is on
main. If stage 5 will not reduce, take one of the fragment's three explicit exits.

## Step 3 — Fill the live template (fragment stage 8)

Read the template off `$TARGET_REPO` **at draft time**. Do not reproduce a template
from memory or from this file — this skill deliberately contains no issue-body
template, because the repo's `.github/ISSUE_TEMPLATE/*.yml` is the enforcement point
and it changes without telling you.

```bash
# from a checkout of $TARGET_REPO
ls .github/ISSUE_TEMPLATE/
# or, without a checkout:
gh api "repos/$TARGET_REPO/contents/.github/ISSUE_TEMPLATE" --jq '.[].name'
```

Pick by the stage 1 kind — `bug` → `bug_report.yml`, `feature` →
`feature_request.yml`, `docs` → `docs_report.yml`. `config.yml` is the chooser
config, not a submission template; never fill it.

### Fallback when a template is absent

The listing above can come back empty or 404 — a fresh repo, a target that never
adopted forms, or an unpushed branch. Do not stall, and do not invent a template:

| What you find | What to do |
| --- | --- |
| The kind's template is present | Fill every field marked `validations: required: true`, in the template's order. Tick a required checkbox only if the assertion is **true** — on `tdupu/mathcity` those checkboxes assert that the stage 2 duplicate search and the stage 3 verify-on-main actually happened |
| `.github/ISSUE_TEMPLATE/` exists but has no template for this kind | Use the nearest sibling template (`bug_report.yml` is the most demanding) and say in the body which template you filled and why |
| `.github/ISSUE_TEMPLATE/` is absent entirely, or `gh api` 404s | Fall back to a plain body: `## Summary` / `## Symptom` / `## Reproduction` / `## Root cause` / `## Fix candidates` / `## Adjacent — out of scope`. Tell the human, in the approval gate, that you used the fallback and that the repo has no forms |
| `gh api` fails for a reason other than 404 (auth, rate limit, network) | Stop. An empty listing caused by a failed call reads exactly like "no templates" and would silently downgrade the filing. Report the error instead |

A `404` on `.github/ISSUE_TEMPLATE` means the templates are not on the target's
**default branch** yet. If you know they exist on an unmerged branch, say so — the
correct action is to land them, not to file against a template GitHub cannot see.

### Draft to a file

Write the draft to a file so the human sees exactly what would be filed:

```bash
DRAFT="${TMPDIR:-/tmp}/issue-draft-$$.md"
# ... write the filled body to "$DRAFT" ...
```

Clean the draft up when you are done with it (`rm -f "$DRAFT"`), or hand the path to
the human explicitly if they want to keep editing it.

## Step 4 — Approval gate (fragment stage 9) — REQUIRED

Present the paste-ready body and the exact filing command. Then **stop**. Nothing
here calls the issue-create verb before a verdict; that gate is the property
`create-issue-briefed` established and `subdomains/dev/POLICY.md` P3.2 requires, and
it survives into this skill unchanged.

Present:

- The target repo and the template being filled — or the fallback you used
- The **full** body, exactly as it would be filed
- Every field you had to mark `<unknown — needs input>`
- The label set, and which of those labels actually exist (see below)
- Your recommendation: file / revise / drop

Wait for APPROVE. On REVISE, return to step 3. On REJECT, stop — and say what you
would file instead, if anything.

### After APPROVE — and only after APPROVE

```bash
gh issue create --repo "$TARGET_REPO" \
  --title "<kind: surface: short imperative title>" \
  --body-file "$DRAFT" \
  --label "kind/<bug|feature|docs>,priority/p<1|2|3>,status/needs-triage"
```

**Labels: check before you pass them.** GitHub **silently drops** label names the
repo does not have — the issue files successfully and arrives unlabeled, so a
triage state you think you set may not be set. Check first and only pass what exists:

```bash
gh label list --repo "$TARGET_REPO" --limit 100
```

On `tdupu/mathcity` the `kind/*`, `priority/*`, and `status/*` scheme is **proposed,
not created**: [`.github/LABELS.md`](https://github.com/tdupu/mathcity/blob/main/.github/LABELS.md)
records the scheme and the exact `gh label` commands, and states plainly that none of
them have been run. Until an owner runs them the repo carries only GitHub's nine
defaults. So:

- If the `kind/*` labels do not exist, either drop `--label` entirely, or map to a
  default that does exist (`bug`, `enhancement`, `documentation`).
- Either way, **say which labels landed and which were dropped** rather than letting
  the human assume the triage state is set.

Report the issue URL back.

## When to use the formula instead

| You want | Use |
| --- | --- |
| To investigate interactively, with checkpoints | **this skill** |
| To dispatch issue-drafting to the fleet and get a decision brief back | `mathcity-issue-briefed` (`gc sling <rig>/<agent> mathcity-issue-briefed --formula --var source_bead=<id> --var brief_slug=<id>-issue`) |
| To file against `gastownhall/gascity` as an external contributor, with no MathCity context | upstream `contributing.write-issue` |

Both MathCity surfaces read the same fragment, so the investigation is identical;
they differ only in who drives and where the approval gate is presented.

## After filing

- Record the issue number on the originating bead (append a linked bead per P1.19 —
  do not rewrite the original's content).
- To pick the issue up yourself, upstream
  [`plan-implementation`](https://github.com/gastownhall/gascity-packs/tree/main/contributing/skills/plan-implementation)
  re-runs the competing-PR and architectural-refactor gates at code-time.
- For the PR that closes it, `pr-pipeline-briefed` is the required path (P3.2) — an
  upstream PR without a corresponding completed issue is a policy failure.
