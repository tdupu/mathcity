---
name: github-issues-to-briefs
description: Drain the GitHub issue tracker into per-issue decision briefs on an hourly cadence — standardize each issue against the repo's templates, mint its bead, deposit ONE brief per issue titled "github-issue N — …", comment the bead id back onto the issue, and close the issue when its brief resolves. Use when the owner asks to "drain the issue tracker", "make briefs for the github issues", or to restart the hourly issue drain.
---

# github-issues-to-briefs

Turn the open GitHub issue backlog into adjudicable decision briefs, one brief
per issue, on a self-terminating hourly cadence. This skill codifies the
owner-directed drain of 2026-08-24 (per-issue pattern ruling: cohort briefs are
rejected; every brief corresponds to exactly one issue, title starting
`github-issue N`).

## Task boundary

- **In scope:** reading the tracker; standardizing issue bodies (additive);
  minting issue beads; depositing per-issue briefs into the pile; recording
  evidence-backed adjudications for the already-resolved class; commenting bead
  ids onto issues; closing issues whose briefs resolve; ledgering each firing.
- **Out of scope:** implementing the work the briefs commission (that flows
  through `work_dispatch` after the owner's verdict); editing issue bodies
  destructively (the standardize tool is additive-only by design); any push,
  deploy, or repo landing (route to the outside agent's authorization gate).

## Pre-flight (every firing)

1. **Typed surface present?** The `mcp__mctl__*` tools must be in the tool
   list. If absent:

   ```text
   I'm sorry, I can't do that — the mctl MCP surface is not connected.
   Run /mcp reconnect mctl (or start the session with the mctl server) to enable it.
   The typed tools are the sole authorized writers of brief artifacts (POLICY B2.11).
   ```

2. **Tracker reachable?** `gh issue list --repo <owner>/<repo> --limit 1`
   exits 0. If not, report the error and skip the firing — never guess issue
   state.
3. **Owner authorization on record** for `gh` closes/comments. Issue closes and
   comments are public-tracker writes; they run only under a standing
   owner directive naming this drain (recorded in the session or the ledger).
   Absent that, deposit briefs but leave closes/comments for the owner.

## The hourly loop (cron, ~10 issues per firing)

Schedule one firing per hour (offset minute, e.g. `:23`). Each firing:

1. **Fetch the 10 oldest unprocessed open issues**
   (`gh issue list --state open --json number,title,createdAt --limit 250`,
   sort ascending, skip issues already processed per the run ledger).
2. **Classify each with evidence verified against current `origin/main`**
   (fetch first — stale-at-filing is the modal error):
   - **ALREADY-RESOLVED / MOOT** → close via `gh issue close` with a hygienic
     comment citing the fixing commit or measurement, AND record the hygienic
     adjudication: if a brief/bead exists for it, `mcp__mctl__briefs_relay_adjudication`
     with the evidence as reason; if none exists, the close comment is the
     record. Never close what could not be verified — report `unknown` instead.
   - **WRONG LAYER** (e.g. platform-core defects on the pack tracker) →
     re-home: file on the correct tracker via `mcp__mctl__create_github_issue`,
     close the original with a pointer comment.
   - **IN-FLIGHT elsewhere** → note in the ledger, skip.
   - **WORKABLE** → the per-issue pipeline (step 3).
3. **Per-issue pipeline** (the core of this skill):
   a. `mcp__mctl__standardize_github_issue` (dry_run=false) — the issue is made
      hygienic against the repo's issue templates; additive restatement only,
      the original body is preserved.
   b. `mcp__mctl__create_issue_bead` — mint the bead (idempotent when it
      exists).
   c. `mcp__mctl__briefs_create` — deposit ONE brief with exactly one source
      (the bead), **title starting `github-issue N — <short title>`**, full-form
      §1–§7 with options and a recommendation in §2. The brief lands in the
      pile and rides the normal pipeline.
   d. **Comment the bead id onto the issue**:
      `gh issue comment N --body "Tracked as bead <bead-id>; decision brief <brief-id> (github-issue N)."`
      This is the issue↔bead back-pointer the lost-bead filters need.
   e. **Adjudication**: evidence-backed no-brainer classes (already-resolved
      closes, mechanical re-homes) are adjudicated automatically with the
      evidence as reason; judgment calls wait for the owner's verdict on the
      brief. Never auto-approve work commissioning — that is the owner's call
      by the two-catch model.
4. **Close-on-resolution sweep**: for every brief previously deposited by this
   drain whose verdict is now terminal (approve with work completed, reject,
   or close-as-resolved), close the corresponding GitHub issue with a comment
   citing the brief id, verdict, and evidence. An approved brief whose work is
   still in flight leaves the issue open.
5. **Ledger** one row per firing in the operations run log (issues processed,
   verdicts, closes, briefs, comments, errors). Any non-cosmetic process error
   also gets a bug_report-template filing on the tracker.
6. **Stop condition**: when every open issue has a brief (or a terminal
   disposition), delete the cron job and report the drain complete. The drain
   is self-terminating — it must not idle-fire against an empty backlog.

## Hard rules carried from policy

- One brief per issue, always — cohort briefs are a rejected pattern
  (owner ruling 2026-08-24).
- The typed tools are the only writers of brief artifacts (B2.11/P7.1); `gh`
  is used only for the tracker-side reads, closes, and comments this skill
  authorizes.
- Public-tracker hygiene: no private rig references, hostnames, or absolute
  local paths in issue comments or bodies.
- A close needs verifiable evidence; `unknown` is reported, never closed.
- Known-cosmetic dispatch diagnostics (documented on the tracker) are
  ledgered, not re-filed.
