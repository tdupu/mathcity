---
name: update-course-webpage
description: Use when asked to update an existing course webpage, fix a typo or date, set office hours, or add a course document or lecture-note link.
---

# Update a course webpage

Make the requested edit, validate it, then use `claude-commit` and immediately push the scoped website commit. This is the default for an actual update request, not for questions, previews or dry runs. A user's no-commit/no-push instruction wins.

1. Resolve the exact repository, branch, remote, canonical page and affected public assets. Read applicable instructions and inspect working-tree/index changes and outgoing commits. Inspect the existing page and linked authoritative course sources. Office hours requested on the main page belong there, not only in a syllabus. If a new page is needed, use `create-course-webpage` within the authorized scope.
2. Apply only the requested change. Preserve layout, unrelated text and user edits. Resolve ambiguous dates or topics from evidence; ask when evidence conflicts. Do not change course policy to make the page agree. Link lecture notes beside the matching topic/date, using existing path conventions; update an existing matching link instead of duplicating it. Do not expose unreleased assessments, keys, raw scans or student information without specific authorization.
3. Inspect the exact diff; check HTML/build output, links, asset existence and rendering relevant to the change. A linked file must be present in the published repository or have a verified public URL. Exclude temporary builds, private sources and unrelated changes. If nothing changed, report a no-op without an empty commit.
4. Use `claude-commit` for commit creation only; defer its pull/push to step 5. Stage only task-owned paths/hunks, overriding its broad staging. Preserve other work and staged content through safe isolation or stop. Follow repository attribution rules with truthful runtime/model identity; never claim Codex is Claude. Keep hooks enabled and verify the exact publication commit.
5. Before any pull/push, verify the complete outgoing history, resolved website branch/remote and safe worktree/index synchronization. Reject Dolt-data remotes, unrelated commits, private material, detached HEAD and uncertain destinations. Pull/rebase against that branch/remote; stop on conflicts. Recheck the commit and outgoing history, then push exactly once to that branch/remote. Never force-push or discard work; no extra confirmation is needed when authorized.
6. Verify the remote branch contains the commit. Check deployment/public URL when available and distinguish pushed, deployed and unverified states. Report the changed page, commit, push result and remaining deployment issue. A failed push is not publication; preserve the local commit and report the blocker.
