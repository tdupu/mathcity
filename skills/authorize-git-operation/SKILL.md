---
name: authorize-git-operation
description: Explicit human-authorization gate for irreversible git operations — push, force-push, merge, PR creation, branch deletion, release tag. Reads the Mayor avatar PNG so the authorization icon appears before the approval prompt. Before presenting, runs a commit-hygiene "collaborator test" on what the operation would land (would a collaborator pulling this repo think it's AI slop?) and checks the target repo against its POLICY.md/LAYOUT.md via check-repository-policies and warns on violations, or — if the repo has no policy document — warns to create one and does a best-effort destructiveness check against the repo's current organization. Records the approval as a bd decision bead. Trigger phrases: "authorize git push", "authorize PR", "authorize merge", "need authorization to push", "authorize this git operation", "request git authorization", "get approval to merge", "authorize branch deletion", "authorize release". NEVER skip this gate for operations listed below — always ask, never auto-proceed.
---

# authorize-git-operation

Presents a visual authorization prompt to the human adjudicator for any irreversible git
operation and records the approval as a bd decision bead in the active rig.

## Covered operations (always gate)

| Operation | Examples |
|---|---|
| **push** | `git push`, `gh pr merge`, force-push |
| **merge** | branch merge to main/master, PR merge |
| **PR creation** | `gh pr create` to any upstream |
| **branch/tag delete** | `git branch -D`, `git push --delete` |
| **release tag** | `git tag -a`, `gh release create` |

Excluded: local commits, `git add`, `git stash`, read-only ops (`git log`,
`git diff`, `git fetch`). Those do not require this gate.

## Step 1 — Show the Mayor icon

**Read this file immediately when the skill is invoked:**

```
<repos-root>/agent-skills/assets/avatars/mayor-agent.png
```

In Claude Code (desktop / web app), the image renders inline — the human adjudicator sees
the blue "M" badge before the authorization question. In a terminal-only
session it is visible to the model only, but the text prompt below still
makes the role clear.

## Step 1b — Commit hygiene + repository policy check (before presenting the request)

Determine the repository the operation targets
(`git rev-parse --show-toplevel`) and vet **what the operation would land**
BEFORE building the authorization prompt — the outgoing commits/diff for a
push/merge/PR (`git log --stat <upstream>..HEAD`, `git diff --stat
<upstream>..HEAD`; for a merge, a `--no-commit --no-ff` trial merge to see the
true resulting tree), not just the committed state. Surface the result in the
"Policy & hygiene" field of Step 2 so the human adjudicator decides with it in view. This
step informs the decision; it never denies on its own.

**The collaborator test — the point of this step.** Before any mechanical
rule, ask the human question about the landing diff: *if a collaborator pulled
this repo right now, would they think someone posted AI slop into it?* This is
a public research repo; the tree should read as the artifact, not as agent
exhaust.

**Run this read at Opus tier.** The slop judgment is the one genuinely hard
call in this gate, so drive it with Opus regardless of the session model:
dispatch the hygiene read to an Opus subagent (`Agent` tool, `model: opus`) —
hand it the landing diff (`git diff <upstream>..HEAD`, `--stat`, and the trial-
merge file list) and have it return the concerns list. If the session is
already Opus, do it inline. Do not let a lighter session model make this call.

Look for the tells and name any you find in the prompt under
**"⚠️ Hygiene concerns"** (this is a judgment call — report, do not auto-deny):

- **Scaffolding / agent exhaust that isn't the artifact** — one-off, diag,
  probe, or scratch files landing in source dirs; `.beads/` workflow leakage
  (`briefs/`, `codex-consults/`, `hooks/`, `audits/`); stale symlinks; `~HEAD`
  merge sidecars; editor/OS cruft (`*~`, `.DS_Store`); backup bundles.
- **Wrong home / foreign entries** — a new top-level dir not in the layout (a
  research ledger dumped in `docs/`), a test at the repo root, a compute
  script in `test/`, data committed into a code path.
- **Volume without value** — dozens of near-identical generated files, or a
  diff far larger than the change it claims to make.
- **Conflict debris** — `<<<<<<<`/`>>>>>>>` markers, duplicated `-copy`/`.orig`
  files, half-finished renames.
- **Boilerplate a maintainer would be embarrassed to publish** — commit
  messages or file content that read as machine-generated filler.

Then the mechanical layer:

- **If the repo has a `POLICY.md` or `LAYOUT.md` at its root:** run the
  `check-repository-policies` skill against the repo. For a push / merge / PR,
  point it at what the operation would land (the outgoing commits / diff), not
  only the committed state, so about-to-land violations are caught too. If it
  reports violations, include them in the prompt under a **"⚠️ Policy
  violations"** heading, with the skill's work-preserving remediation, and let
  the human adjudicator weigh them — do not auto-deny.

- **If the repo has no `POLICY.md` and no `LAYOUT.md`:** warn in the prompt
  that the repository has no policy document and **recommend creating one**
  (via the `new-repository-policy` skill) so the repo does not drift over time.
  Then do a best-effort **destructiveness check**: read the actual change the
  operation would make (`git diff --stat`, `git show --stat`, `git ls-tree`,
  the affected refs) and reason about whether it deviates from the
  repository's current organization — e.g. deleting or renaming tracked
  top-level directories, introducing foreign top-level entries, or
  restructuring the tree away from how it is laid out today. Judge this against
  the observed layout, not a fixed file-count rule. Surface anything that looks
  structurally disruptive under a **"⚠️ No policy — structural check"**
  heading.

If `check-repository-policies` is unavailable, say so in the prompt and fall
back to the destructiveness check.

## Step 2 — Present the authorization request

After showing the icon, output a structured prompt in the following format
(adapt fields to the operation):

```
╔══════════════════════════════════════════════════╗
║  🅼  MAYOR AUTHORIZATION REQUIRED                 ║
╚══════════════════════════════════════════════════╝

Operation : <PUSH | MERGE | PR | DELETE | RELEASE>
Target    : <remote/branch, upstream, repo:tag — be specific>
Rig       : <rig name, e.g. hecke>
Bead      : <bead ID if the operation closes or relates to one; else "—">
Policy    : <POLICY.md | LAYOUT.md | none — see Policy check below>

What will happen
  <One paragraph. Include: what changes, which ref is affected, reversibility.
   Name the commit SHA or branch tip if known.>

Policy & hygiene check
  <From Step 1b. Report BOTH the collaborator/hygiene read and the policy read:
   • "clean — reads as the artifact; no policy violations" when the landing
     diff passes the collaborator test and the policy audit;
   • ⚠️ Hygiene concerns — <list each slop tell in the landing diff + its
     work-preserving fix>;
   • ⚠️ Policy violations — <list each with its remediation>;
   • ⚠️ No policy — recommend creating one (new-repository-policy); structural
     check: <what, if anything, deviates from the repo's current layout>.>

Risk
  <One sentence on worst-case if this goes wrong and how to undo it.>
```

Use `AskUserQuestion` for the approval — do NOT ask in plain text:

```
question: "Authorize this git operation?"
header: "Git auth"
options:
  - label: "Authorize"
    description: "Proceed with the operation as described."
  - label: "Deny"
    description: "Abort — no git action taken."
  - label: "Modify"
    description: "Abort, but I will tell you how to change the operation before re-asking."
```

## Step 3 — Record the decision

Whether approved or denied, create a bd decision bead immediately after
the human adjudicator responds:

```bash
# From inside the relevant repo (<repos-root>/<rig> or <city-root>/<rig>)
bd create -t decision \
  --title "the human adjudicator <authorized|denied> git <OPERATION>: <target>" \
  --description "Authorization gate invoked via authorize-git-operation skill." \
  --notes "Operation: <type>. Target: <ref>. Verdict: <AUTHORIZED|DENIED>. Reason: <the human adjudicator's stated reason if any>." \
  --priority 3
```

If the human adjudicator selects "Modify": record the denial, capture the modification in
the bead notes, then re-invoke this skill with the updated operation.

## Step 4 — Post-authorization (if approved)

### Current state (Phase 2 not yet done)

Run with the existing fallback identity (`claude-agent` App):

```bash
# Verify git credentials before the operation
cd <repos-root>/<rig>  # or <city-root>/<rig> if working from city
git config --local user.name
git config --local user.email
```

Commits/PRs will show the `claude-agent[bot]` avatar (no per-role
icon on GitHub yet — that is Phase 2+3).

### When Phase 2 is complete (`~/.config/gt/mayor/key.pem` exists)

Configure git identity for the Mayor role before the operation:

```bash
bash <repos-root>/agent-skills/scripts/setup-agent-github-identity.sh --role mayor
```

This sets `user.name = "🅼 mayor-agent[bot]"` and the matching
noreply email, so commits and PRs show the **blue M avatar** in the GitHub
UI.

Check with:
```bash
bash <repos-root>/agent-skills/scripts/setup-agent-github-identity.sh --check
```

### Phase 2 setup (the human adjudicator action — one time per App)

To create the Mayor GitHub App and complete Phase 2:

1. Browse to <https://github.com/settings/apps/new>
2. Name: `mayor-agent` | Homepage: `https://github.com/<github-owner>`
3. Permissions: Contents R/W, Issues R/W, Pull requests R/W, Metadata R
4. Webhooks: disabled | Install: only on this account
5. Upload `<repos-root>/agent-skills/assets/avatars/mayor-agent.png` as the avatar
6. Generate + download the private key (`.pem`), note the App ID + Installation ID
7. Install on all Gas Town repos
8. Save credentials:
   ```bash
   mkdir -p ~/.config/gt/mayor
   chmod 700 ~/.config/gt/mayor
   # Move the downloaded .pem:
   mv ~/Downloads/mayor-agent.*.pem ~/.config/gt/mayor/key.pem
   chmod 600 ~/.config/gt/mayor/key.pem
   echo <APP_ID> > ~/.config/gt/mayor/app-id
   echo <INSTALLATION_ID> > ~/.config/gt/mayor/installation-id
   ```

See `<repos-root>/agent-skills/docs/per-role-github-apps-plan.md` §3 for the full
flow and sequencing (Mayor first, then Refinery → Witness → Deacon → Polecat).

## Security rules

- NEVER skip this gate, even for "obviously safe" pushes.
- NEVER read or print the `.pem` file — use length-check only:
  `wc -c < ~/.config/gt/mayor/key.pem` (must be > 0).
- the human adjudicator's approval in one conversation does NOT carry over to the next.
  Each operation requires a fresh prompt.
- If the AskUserQuestion response is "Deny" or anything ambiguous: abort,
  record the denial bead, and report what was NOT done.

## What this skill does NOT do

- Does not execute the git operation itself — it only gates it.
- Does not configure per-rig Polecat/Refinery/Witness/Deacon identities
  (those use the same pattern; file separate authorizations under the
  relevant role).
- Does not push to `gastownhall/gascity-packs` upstream or open upstream PRs.

## See also

- `<repos-root>/agent-skills/docs/per-role-github-apps-plan.md` — full Phase 1/2/3 plan
- `<repos-root>/agent-skills/assets/avatars/mayor-agent.png` — the Mayor icon source
- `<repos-root>/agent-skills/scripts/setup-agent-github-identity.sh` — identity configuration script
- `check-repository-policies` skill — the POLICY.md/LAYOUT.md audit run in Step 1b
- `new-repository-policy` skill — recommended in Step 1b when a repo has no policy doc
- `record-decision` skill — for recording adjudications outside the git-op context
