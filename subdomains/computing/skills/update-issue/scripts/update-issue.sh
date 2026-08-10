#!/bin/bash
# update-issue.sh — Replace a GitHub issue's body and consolidate the prior
# body into a single archive comment (folded via HTML <details>).
#
# Fixes #25: invocations no longer post a new comment each time. Instead,
# all prior body versions live in one comment, distinguished by a hidden
# HTML marker.
#
# Usage:
#   update-issue.sh <issue_number> --body-file <path>  [options]
#   update-issue.sh <issue_number> --body-stdin       [options]
#
# Required (exactly one):
#   --body-file <path>     New body content from a file
#   --body-stdin           New body content from stdin
#
# Options:
#   --reason "<line>"      Short reason annotation (embedded in fold summary)
#   --discard-old-body     Don't archive the old body (default: archive)
#   --repo <owner/repo>    Defaults to gh's current repo context
#   --from <agent_uuid>    Caller's session UUID (annotation only)
#   --delete-comments <id1,id2>  Comma-separated comment IDs to delete first
#   --no-ai-attribution    Suppress BOTH the AI-assisted footer and label
#   --ai-model <name>      Model name in footer (default: claude-opus-4-7)
#   --ai-label <label>     Label to add (default: ai-assisted; "" skips label)
#   --on-behalf-of <user>  @handle named in footer (default: example-owner)
#
# Exit codes:
#   0  — success (body replaced, archive consolidated)
#   1  — usage error
#   2  — gh not authenticated / repo not resolvable
#   3  — archive comment would exceed 65k chars even after consolidation
#        (degraded mode: oldest folds truncated; printed warning)
#   4  — gh API error during execution
#
# Env overrides:
#   UPDATE_ISSUE_MARKER    HTML marker used to identify the archive comment
#                          (default: <!-- update-issue-consolidated-archive -->)
#   UPDATE_ISSUE_AI_FOOTER_MARKER  HTML marker used to identify the AI footer
#                          (default: <!-- ai-assisted-footer -->)
#   GH                     Path to gh binary (default: gh; testable via PATH mock)
#   MAX_ARCHIVE_CHARS      Soft cap before truncation (default: 60000)

set -e

# ---------- defaults ----------
GH_BIN="${GH:-gh}"
MARKER="${UPDATE_ISSUE_MARKER:-<!-- update-issue-consolidated-archive -->}"
AI_FOOTER_MARKER="${UPDATE_ISSUE_AI_FOOTER_MARKER:-<!-- ai-assisted-footer -->}"
MAX_ARCHIVE_CHARS="${MAX_ARCHIVE_CHARS:-60000}"

# ---------- arg parsing ----------
ISSUE=""
BODY_FILE=""
USE_STDIN=""
REASON=""
DISCARD_OLD=""
REPO=""
FROM_UUID=""
DELETE_IDS=""
NO_AI_ATTRIBUTION=""
AI_MODEL="claude-opus-4-7"
AI_LABEL="ai-assisted"
ON_BEHALF_OF="example-owner"

usage() {
  sed -n '2,35p' "$0" >&2
  exit 1
}

while [ $# -gt 0 ]; do
  case "$1" in
    --body-file) BODY_FILE="$2"; shift 2 ;;
    --body-stdin) USE_STDIN=1; shift ;;
    --reason) REASON="$2"; shift 2 ;;
    --discard-old-body) DISCARD_OLD=1; shift ;;
    --repo) REPO="$2"; shift 2 ;;
    --from) FROM_UUID="$2"; shift 2 ;;
    --delete-comments) DELETE_IDS="$2"; shift 2 ;;
    --no-ai-attribution) NO_AI_ATTRIBUTION=1; shift ;;
    --ai-model) AI_MODEL="$2"; shift 2 ;;
    --ai-label) AI_LABEL="$2"; shift 2 ;;
    --on-behalf-of) ON_BEHALF_OF="$2"; shift 2 ;;
    -h|--help) usage ;;
    -*) echo "unknown option: $1" >&2; usage ;;
    *)
      if [ -z "$ISSUE" ]; then
        ISSUE="$1"
      else
        echo "unexpected positional: $1" >&2; usage
      fi
      shift
      ;;
  esac
done

# ---------- validate ----------
if [ -z "$ISSUE" ]; then echo "error: issue number required" >&2; exit 1; fi
if [ -z "$BODY_FILE" ] && [ -z "$USE_STDIN" ]; then
  echo "error: must specify --body-file <path> or --body-stdin" >&2; exit 1
fi
if [ -n "$BODY_FILE" ] && [ -n "$USE_STDIN" ]; then
  echo "error: --body-file and --body-stdin are mutually exclusive" >&2; exit 1
fi
if [ -n "$BODY_FILE" ] && [ ! -f "$BODY_FILE" ]; then
  echo "error: --body-file not found: $BODY_FILE" >&2; exit 1
fi

if [ -z "$REPO" ]; then
  REPO=$("$GH_BIN" repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null) || {
    echo "error: gh repo view failed (auth? in a repo dir?)" >&2; exit 2
  }
fi

# ---------- read new body ----------
NEW_BODY=$(mktemp)
DELETED_COMMENTS_PAYLOAD=$(mktemp)
trap 'rm -f "$NEW_BODY" "$OLD_BODY" "$ARCHIVE_PAYLOAD" "$DELETED_COMMENTS_PAYLOAD" "$EXISTING_ARCHIVE" "$NEW_ARCHIVE" 2>/dev/null' EXIT
if [ -n "$USE_STDIN" ]; then
  cat > "$NEW_BODY"
else
  cp "$BODY_FILE" "$NEW_BODY"
fi
: > "$DELETED_COMMENTS_PAYLOAD"

# ---------- archive-then-delete listed comments ----------
# Unlike v1, --delete-comments now FOLDS each deleted body into the archive
# before deleting (so nothing is lost). Skipped when --discard-old-body.
if [ -n "$DELETE_IDS" ]; then
  IFS=',' read -ra IDS <<< "$DELETE_IDS"
  for cid in "${IDS[@]}"; do
    if [ -z "$DISCARD_OLD" ]; then
      # Fetch the comment body + createdAt BEFORE deleting
      DC_BODY=$("$GH_BIN" api "repos/$REPO/issues/comments/$cid" --jq .body 2>/dev/null || true)
      DC_TS=$("$GH_BIN" api "repos/$REPO/issues/comments/$cid" --jq .created_at 2>/dev/null || true)
      DC_AUTHOR=$("$GH_BIN" api "repos/$REPO/issues/comments/$cid" --jq .user.login 2>/dev/null || true)
      if [ -n "$DC_BODY" ]; then
        DC_FIRST_LINE=$(printf '%s' "$DC_BODY" | head -1 | head -c 100)
        DC_SUMMARY="Deleted comment ${cid}"
        [ -n "$DC_AUTHOR" ] && DC_SUMMARY="$DC_SUMMARY by @${DC_AUTHOR}"
        [ -n "$DC_TS" ] && DC_SUMMARY="$DC_SUMMARY at ${DC_TS}"
        [ -n "$DC_FIRST_LINE" ] && DC_SUMMARY="$DC_SUMMARY — ${DC_FIRST_LINE}"
        {
          printf '<details>\n<summary>%s</summary>\n\n' "$DC_SUMMARY"
          printf '%s' "$DC_BODY"
          printf '\n\n</details>\n\n'
        } >> "$DELETED_COMMENTS_PAYLOAD"
      fi
    fi
    "$GH_BIN" api -X DELETE "repos/$REPO/issues/comments/$cid" \
      && echo "deleted comment $cid" \
      || { echo "warning: delete failed for $cid" >&2; }
  done
fi

# ---------- fetch current body ----------
OLD_BODY=$(mktemp)
"$GH_BIN" issue view "$ISSUE" --repo "$REPO" --json body --jq .body > "$OLD_BODY" || {
  echo "error: gh issue view failed" >&2; exit 4
}

# ---------- archive flow ----------
if [ -z "$DISCARD_OLD" ]; then
  TS=$(date '+%Y-%m-%d %H:%M')
  SUMMARY="Version as of $TS"
  [ -n "$REASON" ] && SUMMARY="$SUMMARY — $REASON"
  [ -n "$FROM_UUID" ] && SUMMARY="$SUMMARY (by ${FROM_UUID:0:8})"

  # Build the new <details> blocks for this archive entry.
  # If any comments were just deleted, their folds come FIRST (most recent
  # context), followed by the old-body fold.
  ARCHIVE_PAYLOAD=$(mktemp)
  {
    # Deleted-comments folds (one per --delete-comments id)
    if [ -s "$DELETED_COMMENTS_PAYLOAD" ]; then
      cat "$DELETED_COMMENTS_PAYLOAD"
    fi
    # Old-body fold
    printf '<details>\n<summary>%s</summary>\n\n' "$SUMMARY"
    cat "$OLD_BODY"
    printf '\n\n</details>\n'
  } > "$ARCHIVE_PAYLOAD"

  # Find the existing consolidated-archive comment, if any.
  # Use REST API for direct numeric comment IDs (gh issue view's .comments[].id is a graphql node id).
  COMMENT_ID=$("$GH_BIN" api "repos/$REPO/issues/$ISSUE/comments" \
    --jq ".[] | select(.body | contains(\"$MARKER\")) | .id" 2>/dev/null | head -1)

  if [ -n "$COMMENT_ID" ]; then
    # Existing archive present: fetch its body, prepend new fold, PATCH in place
    EXISTING_ARCHIVE=$(mktemp)
    "$GH_BIN" api "repos/$REPO/issues/comments/$COMMENT_ID" --jq .body > "$EXISTING_ARCHIVE" || {
      echo "error: gh api comment fetch failed" >&2; exit 4
    }

    # Build new archive body:
    #   marker line
    #   header
    #   new <details>
    #   ...existing <details> blocks...
    NEW_ARCHIVE=$(mktemp)
    {
      printf '%s\n' "$MARKER"
      printf '# Archive — superseded body versions\n\n'
      printf 'This comment consolidates all prior versions of the issue body, '
      printf 'ordered newest-first. Each version is folded; click to expand.\n\n'
      cat "$ARCHIVE_PAYLOAD"
      printf '\n'
      # Strip the existing marker + header from existing archive; keep the folds.
      # Folds start with the first `<details>` line.
      awk '/^<details>/{flag=1} flag{print}' "$EXISTING_ARCHIVE"
    } > "$NEW_ARCHIVE"

    # Truncation if too big — drop oldest fold(s).
    while [ "$(wc -c < "$NEW_ARCHIVE")" -gt "$MAX_ARCHIVE_CHARS" ]; do
      # Remove the last </details> ... <details> block (oldest)
      TRUNCATED=$(mktemp)
      awk '
        BEGIN { count = 0 }
        /^<details>/ { count++ }
        { lines[NR] = $0 }
        END {
          # Print all but the last details block
          last_details_start = 0
          for (i = NR; i >= 1; i--) {
            if (lines[i] ~ /^<details>/) { last_details_start = i; break }
          }
          if (last_details_start == 0) { for (i=1;i<=NR;i++) print lines[i]; exit }
          for (i = 1; i < last_details_start; i++) print lines[i]
          # Add truncation notice
          print ""
          print "<details>"
          print "<summary>⚠ Older versions truncated to fit comment cap</summary>"
          print ""
          print "GitHub caps a single comment at 65k chars. The oldest fold was dropped to fit."
          print "</details>"
        }
      ' "$NEW_ARCHIVE" > "$TRUNCATED"
      mv "$TRUNCATED" "$NEW_ARCHIVE"
      # Safety: bail if we cannot get below cap (no <details> left)
      if ! grep -q '^<details>' "$NEW_ARCHIVE"; then
        echo "error: cannot shrink archive below $MAX_ARCHIVE_CHARS chars" >&2
        exit 3
      fi
    done

    # Update the existing comment in place. gh's `-f body=@file` does NOT
    # read the file; -F is required for @file syntax in gh api.
    # Workaround that's portable across gh versions: pass body as a string.
    "$GH_BIN" api -X PATCH "repos/$REPO/issues/comments/$COMMENT_ID" \
      -f body="$(cat "$NEW_ARCHIVE")" >/dev/null || {
      echo "error: gh api PATCH failed" >&2; exit 4
    }
    COMMENT_URL=$("$GH_BIN" api "repos/$REPO/issues/comments/$COMMENT_ID" --jq .html_url 2>/dev/null)
    ACTION_TAKEN="edited existing archive comment ($COMMENT_URL)"
  else
    # No existing archive: create the consolidated comment for the first time
    NEW_ARCHIVE=$(mktemp)
    {
      printf '%s\n' "$MARKER"
      printf '# Archive — superseded body versions\n\n'
      printf 'This comment consolidates all prior versions of the issue body, '
      printf 'ordered newest-first. Each version is folded; click to expand.\n\n'
      cat "$ARCHIVE_PAYLOAD"
    } > "$NEW_ARCHIVE"

    POSTED_URL=$("$GH_BIN" issue comment "$ISSUE" --repo "$REPO" \
      --body-file "$NEW_ARCHIVE") || {
      echo "error: gh issue comment failed" >&2; exit 4
    }
    ACTION_TAKEN="created consolidated archive comment ($POSTED_URL)"
  fi
fi

# ---------- AI-assisted footer injection ----------
# Skipped entirely with --no-ai-attribution. Otherwise we append a marker-
# tagged subscript footer ONLY if the caller's body doesn't already contain
# the marker (idempotent — re-running the skill on its own output is a no-op
# for the footer). The marker is HTML so GitHub renders it as nothing.
AI_FOOTER_INJECTED=""
if [ -z "$NO_AI_ATTRIBUTION" ]; then
  if ! grep -qF "$AI_FOOTER_MARKER" "$NEW_BODY"; then
    {
      # Separator: ensure exactly one blank line before the horizontal rule.
      # Use printf so we don't depend on whether the caller's body ends in \n.
      printf '\n\n---\n\n'
      printf '<sub>%s' "$AI_FOOTER_MARKER"
      printf '**AI-assisted.** Content autogenerated by Claude (model: `%s`) ' "$AI_MODEL"
      printf 'on behalf of @%s via the ' "$ON_BEHALF_OF"
      printf '[`update-issue`](https://github.com/example-owner/agent-skills/tree/main/skills/update-issue) skill. '
      printf 'Please verify before relying on this. '
      printf 'The consolidated archive comment preserves prior body versions.</sub>\n'
    } >> "$NEW_BODY"
    AI_FOOTER_INJECTED=1
  fi
fi

# ---------- replace body ----------
"$GH_BIN" issue edit "$ISSUE" --repo "$REPO" --body-file "$NEW_BODY" >/dev/null || {
  echo "error: gh issue edit failed" >&2; exit 4
}

# ---------- AI-assisted label ----------
# Idempotent: gh issue edit --add-label is a no-op if the label is already
# on the issue. If the label doesn't exist on the repo, create it first.
# Failures are non-fatal — body replacement is the load-bearing operation.
AI_LABEL_APPLIED=""
if [ -z "$NO_AI_ATTRIBUTION" ] && [ -n "$AI_LABEL" ]; then
  # Ensure the label exists on the repo (idempotent: --force updates if exists,
  # but we only create when missing to avoid clobbering custom color/description).
  LABEL_EXISTS=$("$GH_BIN" label list --repo "$REPO" --search "$AI_LABEL" \
    --json name --jq ".[] | select(.name == \"$AI_LABEL\") | .name" 2>/dev/null | head -1)
  if [ -z "$LABEL_EXISTS" ]; then
    "$GH_BIN" label create "$AI_LABEL" --repo "$REPO" \
      --color ededed \
      --description "Issue body autogenerated by an LLM (see update-issue skill)" \
      >/dev/null 2>&1 || echo "warning: could not create label $AI_LABEL" >&2
  fi
  if "$GH_BIN" issue edit "$ISSUE" --repo "$REPO" --add-label "$AI_LABEL" >/dev/null 2>&1; then
    AI_LABEL_APPLIED="$AI_LABEL"
  else
    echo "warning: could not add label $AI_LABEL to issue $ISSUE" >&2
  fi
fi

# ---------- report ----------
echo "Issue #$ISSUE on $REPO updated."
echo "New body length: $(wc -c < "$NEW_BODY") chars."
if [ -z "$DISCARD_OLD" ]; then
  echo "Archive: $ACTION_TAKEN"
fi
if [ -n "$AI_FOOTER_INJECTED" ]; then
  echo "AI-assisted footer: injected (model=$AI_MODEL, on behalf of @$ON_BEHALF_OF)"
elif [ -z "$NO_AI_ATTRIBUTION" ]; then
  echo "AI-assisted footer: already present (left as-is)"
fi
if [ -n "$AI_LABEL_APPLIED" ]; then
  echo "AI-assisted label: $AI_LABEL_APPLIED"
fi
TOTAL_COMMENTS=$("$GH_BIN" issue view "$ISSUE" --repo "$REPO" --json comments --jq '.comments | length')
echo "Total comments on issue: $TOTAL_COMMENTS"
