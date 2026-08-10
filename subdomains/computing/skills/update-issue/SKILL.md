---
name: update-issue
description: Replace a GitHub issue's body with a single up-to-date canonical statement, consolidating all prior body versions into ONE archive comment per issue (folded via HTML <details> blocks). Use whenever the user says "update issue N", "rewrite issue N", "consolidate the issue body", "clean up issue N", or when an issue's body has gotten stale, bloated, or contradicted by newer evidence. NEVER posts a new comment per invocation — see #25.
---

# update-issue Skill

## What "clean" looks like

A clean GitHub issue surface has:

- **One body** — the canonical current state. Self-contained. Human-readable by any collaborator (not just the team working on it). NO references to agent UUIDs, inbox protocols, coordinator dispatches, or other multi-agent-internal noise. Hyperlinks for files tracked in the repo.
- **At most ONE archive comment** — the consolidated history of prior body versions, folded as `<details>` blocks, ordered newest-first. Identified by a hidden HTML marker (`<!-- update-issue-consolidated-archive -->`) so subsequent invocations find and update it in place instead of creating a new one.
- **Active-discussion comments** — anything the team is currently working in. Untouched by this skill.

**Bug history**: prior versions of this skill created a new archive comment per invocation. After several invocations the comment list became cluttered with prior body archives — exactly the bloat the skill was supposed to prevent. See [#25](https://github.com/<github-owner>/agent-skills/issues/25). This version uses an HTML marker + comment-edit-in-place to guarantee at-most-one archive comment per issue.

## What the skill does

When invoked with `update-issue.sh <N> --body-file <path>` (or `--body-stdin`):

1. **Fetches the current body**.
2. **(Optional) Archive-then-delete listed comments** via `--delete-comments id1,id2,...`:
   - For each comment ID, fetches its body, author, and timestamp BEFORE deletion.
   - Each fetched body is added as its own `<details>` fold in the consolidated archive (so nothing is lost — same pattern as the old-body archive).
   - Then issues the `DELETE`.
   - Skip the fetch step when `--discard-old-body` is set; deletes proceed but bodies are not preserved.
3. **Consolidates the old body into the archive comment** (unless `--discard-old-body`):
   - Searches issue comments for the marker `<!-- update-issue-consolidated-archive -->`.
   - **If found**: fetches the existing archive comment, prepends a new section (deleted-comment folds, if any, followed by the old-body fold) under the marker, edits the comment in place via `gh api -X PATCH`. **One comment, edited.**
   - **If not found**: creates the consolidated archive comment for the first time, starting with the marker + header + the new section. **One new comment.**
4. **Replaces the issue body** with the new content.
5. **Reports**: new body length, action taken (created vs edited archive), total comments on the issue.

If the consolidated archive would exceed 60k chars (configurable via `MAX_ARCHIVE_CHARS`), the oldest folds are dropped to fit, with a "⚠ Older versions truncated" note added. GitHub's hard cap is 65k per comment.

**End-state guarantee**: regardless of how many invocations, the issue has at most ONE archive comment. With `--delete-comments`, the count of "other" comments goes down by the count of IDs deleted, but the archive count stays at one.

## Usage

```bash
bash ~/.claude/skills/update-issue/scripts/update-issue.sh <issue_number> \
  --body-file <path>  [options]
```

Required (exactly one):
- `--body-file <path>` — new body content from a file
- `--body-stdin` — new body content from stdin

Options:
- `--reason "<line>"` — short reason; embedded in the fold's summary line
- `--discard-old-body` — skip archiving (default is to archive)
- `--repo <owner/repo>` — defaults to `gh repo view`'s current context
- `--from <agent_uuid>` — caller's session UUID (annotation only, first 8 chars shown)
- `--delete-comments <id1,id2>` — comma-separated comment IDs to delete first
- `--no-ai-attribution` — suppress both the footer and the `ai-assisted` label
- `--ai-model <name>` — model name embedded in the footer (default: `claude-opus-4-7`)
- `--ai-label <label>` — label to add (default: `ai-assisted`; pass `""` to skip just the label)
- `--on-behalf-of <handle>` — `@handle` named in the footer as the principal (default: `<github-owner>`)

Exit codes:
- `0` success
- `1` usage error
- `2` `gh` not authenticated / repo not resolvable
- `3` archive would exceed 65k char cap even after truncation
- `4` GitHub API error

Env overrides:
- `UPDATE_ISSUE_MARKER` — HTML marker for archive comment (default: `<!-- update-issue-consolidated-archive -->`)
- `UPDATE_ISSUE_AI_FOOTER_MARKER` — HTML marker for the AI-assisted footer (default: `<!-- ai-assisted-footer -->`)
- `GH` — path to `gh` binary (default: `gh`; testable via PATH mock)
- `MAX_ARCHIVE_CHARS` — soft cap before truncation (default: 60000)

## Body conventions

The new body you pass to the skill should be:

- **Self-contained** — a collaborator opening the issue cold can understand the current state from the body alone. A fresh agent or person should be able to pick up the issue and know what to do without reading the comment history.
- **Pickup-ready** — for bug issues, include: Summary, Scope, Behavior, MRE (minimal reproducer with concrete commands and file paths), Code locations (specific files + line numbers), What needs to be done (priority-ordered checklist), Priority + reasoning, Cross-references. Anyone glancing at the issue should see the path forward.
- **Human-readable** — written for the people who will use the work product, not for the agents who built it. No agent UUIDs in the body. No inbox protocol mentions.
- **Hyperlinked to tracked artifacts** — for any in-repo file the body references, prefer `https://github.com/<owner>/<repo>/blob/main/<path>` over a raw filesystem path.
- **Concise** — body is a problem statement / status report, not a transcript.
- **Honest about state** — say plainly what's done, pending, deferred. If an earlier diagnosis was wrong, say so plainly. The archive preserves the prior versions.
- **Include a provenance footer if autogenerated** — see next section.

## AI-assisted attribution (auto-applied)

Issues posted or rewritten via this skill appear under the authenticated user's GitHub account, which makes it impossible for collaborators to tell whether a human or an LLM authored the change. The skill therefore applies two attribution signals on every invocation:

1. **A provenance footer**, appended to the issue body. Mirrors the diff-val commit convention (`AI-assisted: Content autogenerated by Claude ...`). Carries a hidden HTML marker (`<!-- ai-assisted-footer -->`) so re-runs detect and refresh the existing footer instead of stacking copies.
2. **An `ai-assisted` GitHub label** added to the issue. Surfaces in the issue list, search filters, and notification routing without the reader needing to open the issue. The label is created on the repo if missing (color `ededed`).

Footer shape (markdown subscript so it doesn't dominate the page):

```markdown
---

<sub><!-- ai-assisted-footer -->**AI-assisted.** Content autogenerated by Claude (model: `claude-opus-4-7`) on behalf of @&lt;owner&gt; via the [`update-issue`](https://github.com/<github-owner>/agent-skills/tree/main/skills/update-issue) skill. Please verify before relying on this. The consolidated archive comment preserves prior body versions.</sub>
```

The footer is injected after the body the caller supplied — the user-facing content always comes first. Where `@<owner>` is filled in from `--on-behalf-of` (defaults to `<github-owner>`).

**Opt-out:** pass `--no-ai-attribution` for human-authored rewrites you're shepherding through the skill (drops both footer and label). Pass `--ai-label ""` to skip just the label. Use `--ai-model claude-...` to record a different model name.

**Idempotency:** the skill greps the new body for the marker before injecting; an existing `<!-- ai-assisted-footer -->` block is left as-is. The label call is also idempotent — `gh issue edit --add-label` is a no-op when the label is already on the issue.

## Anatomy of the consolidated archive comment

After three invocations, the single archive comment looks like:

```markdown
<!-- update-issue-consolidated-archive -->
# Archive — superseded body versions

This comment consolidates all prior versions of the issue body, ordered newest-first. Each version is folded; click to expand.

<details>
<summary>Version as of 2026-06-10 14:30 — H2 confirmed (by 0b1e9d61)</summary>

[contents of body just before the latest update]

</details>

<details>
<summary>Version as of 2026-06-10 11:00 — H1 walked back (by 0b1e9d61)</summary>

[contents of body two updates ago]

</details>

<details>
<summary>Version as of 2026-06-09 08:30 — initial diagnosis (by 0b1e9d61)</summary>

[original body]

</details>
```

GitHub renders `<details>`/`<summary>` as collapsible disclosure triangles. The issue page stays clean; history is one click away.

## What the skill does NOT do

- **Close issues** — use `gh issue close`.
- **Add follow-up comments** — use `gh issue comment`. Use this skill only when REPLACING the body.
- **Expunge sensitive content** — the archive lives in a public comment. If sensitive content ever hits the body, fix it BEFORE running the skill (or pass `--discard-old-body`).
- **Touch issues the user hasn't asked you to** — body replacement is destructive (only recoverable via the archive comment).

## Failure modes and degraded behavior

- **Archive grows past 60k chars** → oldest fold(s) dropped, "⚠ Older versions truncated" note added. The body still gets updated.
- **Archive cannot shrink below cap** → exit 3 with error; body NOT updated. Manual intervention required (e.g. move oldest folds to a gist).
- **`gh` not authenticated** → exit 2 at startup; nothing modified.
- **API call fails mid-flow** → exit 4. If the failure is after the archive comment was posted/edited but before body replacement, the archive is consistent but the body still shows the old content. Idempotent re-run will succeed without duplicating the archive (the marker prevents a second consolidation comment).

## Setup checklist before first run

1. `gh auth status` returns OK.
2. Confirm the repo (`--repo` or default).
3. Stage the new body as a tempfile (`/tmp/issue-N-rewrite.md`) or pipe it in. The skill does NOT edit the new body content — pass it in final form.
4. Compose the `--reason` line — short imperative phrase.
5. (Optional) Identify any stale existing comments to delete; collect their IDs for `--delete-comments`.

## Example invocations

**Standard rewrite, archive old body, default reason:**
```bash
bash ~/.claude/skills/update-issue/scripts/update-issue.sh 191 \
  --body-file /tmp/191-rewrite.md \
  --reason "correct root-cause diagnosis"
```

**Full cleanup — new canonical body + delete (and archive) all status comments:**
```bash
# 1. Collect the comment IDs to delete via the REST API (gives numeric IDs
#    suitable for the DELETE endpoint).
gh api repos/<owner>/<repo>/issues/<N>/comments \
  --jq '.[] | "\(.id)\t\(.user.login)\t\(.body | split("\n")[0])"'

# 2. Pass them to update-issue along with the new canonical body. Each
#    deleted comment's body is folded into the consolidated archive
#    before the DELETE fires.
bash ~/.claude/skills/update-issue/scripts/update-issue.sh 98 \
  --body-file /tmp/98-final.md \
  --reason "end-of-workstream canonical rewrite" \
  --from "$CLAUDE_CODE_SESSION_ID" \
  --delete-comments 4667067929,4667646330,4668017565,4672436283
```

End state: 1 canonical body (the rewrite, with the auto-injected AI-assisted footer), 1 consolidated archive comment (with N+1 folds: one per deleted comment plus the old body), 0 follow-up comments, `ai-assisted` label set on the issue.

**Trivial body replacement, no archive:**
```bash
bash ~/.claude/skills/update-issue/scripts/update-issue.sh 215 \
  --body-stdin --discard-old-body --reason "fix typo" <<'EOF'
## Summary
...
EOF
```

## Testing

- `tests/run-all.sh` — L1 mocked tests. Mocks the `gh` binary via PATH redirect. Runs anywhere safely, no real GitHub API calls. Default for iteration.
- `tests/manual/` — L2 tests that exercise real `gh` against a throwaway test issue. Documented as opt-in via explicit invocation; require `gh auth status` OK.

## See also

- `~/.claude/skills/skill-creator-plus/SKILL.md` — publish-side companion (this skill is an update-side tool for issues, not for skills).
- `~/.claude/skills/communicate-with-other-agent/SKILL.md` — inter-agent channel; useful for routing "issue updated, please re-read" notifications.
