#!/bin/bash
# mock-gh.sh — records every gh invocation and returns canned responses.
#
# Driven by env vars (set per-test):
#   MOCK_GH_LOG               — file to append every call to
#   MOCK_GH_OLD_BODY          — content for `gh issue view ... --json body --jq .body`
#   MOCK_GH_EXISTING_ARCHIVE  — comment ID returned for marker search ("" = no archive)
#   MOCK_GH_EXISTING_BODY     — content returned for `gh api repos/.../comments/<id>`
#   MOCK_GH_REPO              — value for `gh repo view --json nameWithOwner`
#                               (default: "example-owner/agent-skills")
#   MOCK_GH_COMMENTS_LEN      — value for `.comments | length` (default 1)
#   MOCK_GH_FAIL_PATCH        — non-empty → exit 1 from `gh api -X PATCH`
#   MOCK_GH_FAIL_EDIT         — non-empty → exit 1 from `gh issue edit`
#   MOCK_GH_LABEL_EXISTS      — non-empty → `gh label list` returns the label
#                               (default: empty, so the script creates it)

LOG="${MOCK_GH_LOG:-/tmp/mock-gh.log}"
ARGS_STR="$*"

# Append the full invocation to the log.
echo "gh $ARGS_STR" >> "$LOG"

# Capture --body-file content into a sidecar log so tests can inspect what
# was passed (since the script uses tempfiles that get cleaned by trap).
for ((i=1; i<=$#; i++)); do
  if [ "${!i}" = "--body-file" ]; then
    j=$((i+1))
    bf="${!j}"
    if [ -f "$bf" ]; then
      {
        echo "===BODY-FILE: $bf in call: gh $ARGS_STR ==="
        cat "$bf"
        echo "===END-BODY-FILE==="
      } >> "${LOG}.bodies"
    fi
  fi
done

# Read first non-option argument to identify subcommand.
SUBCMD=""
for a in "$@"; do
  case "$a" in
    -*) ;;
    *) SUBCMD="$a"; break ;;
  esac
done

case "$SUBCMD" in
  repo)
    # gh repo view --json nameWithOwner --jq .nameWithOwner
    echo "${MOCK_GH_REPO:-example-owner/agent-skills}"
    ;;
  issue)
    # gh issue <view|edit|comment> ...
    # Find the issue subcommand (second positional).
    SUB2=""
    seen_issue=0
    for a in "$@"; do
      if [ $seen_issue -eq 1 ] && [[ ! "$a" =~ ^- ]]; then
        SUB2="$a"; break
      fi
      [ "$a" = "issue" ] && seen_issue=1
    done
    case "$SUB2" in
      view)
        # Which JSON field? scan for --json X
        json_field=""
        prev=""
        for a in "$@"; do
          [ "$prev" = "--json" ] && json_field="$a" && break
          prev="$a"
        done
        case "$json_field" in
          body)
            printf '%s' "${MOCK_GH_OLD_BODY:-old body content}"
            ;;
          comments)
            # Length query path: --jq '.comments | length'
            if [[ " $* " == *" --jq "* ]]; then
              for ((i=1; i<=$#; i++)); do
                if [ "${!i}" = "--jq" ]; then
                  next=$((i+1))
                  q="${!next}"
                  if [[ "$q" == *"length"* ]]; then
                    echo "${MOCK_GH_COMMENTS_LEN:-1}"
                    exit 0
                  fi
                fi
              done
            fi
            echo "[]"
            ;;
          *)
            echo "{}"
            ;;
        esac
        ;;
      comment)
        # gh issue comment N --repo R --body-file F → returns posted URL
        echo "https://github.com/${MOCK_GH_REPO:-example-owner/agent-skills}/issues/99#issuecomment-fakeposted"
        ;;
      edit)
        # gh issue edit N --repo R --body-file F → silent on success
        # gh issue edit N --repo R --add-label LABEL → silent on success
        if [ -n "$MOCK_GH_FAIL_EDIT" ]; then
          echo "mock: forced edit failure" >&2; exit 1
        fi
        ;;
    esac
    ;;
  label)
    # gh label list --repo R --search NAME --json name --jq ...
    # gh label create NAME --repo R --color C --description D
    SUB2=""
    seen_label=0
    for a in "$@"; do
      if [ $seen_label -eq 1 ] && [[ ! "$a" =~ ^- ]]; then
        SUB2="$a"; break
      fi
      [ "$a" = "label" ] && seen_label=1
    done
    case "$SUB2" in
      list)
        # Return JSON array of objects with name field if MOCK_GH_LABEL_EXISTS set.
        # The script uses --jq to extract the name; emit a body that the real
        # gh would produce after the --jq filter has been applied.
        if [ -n "$MOCK_GH_LABEL_EXISTS" ]; then
          # The script's --jq is: .[] | select(.name == "<LABEL>") | .name
          # Scan args for --search to know what label is being searched for.
          search=""
          prev=""
          for a in "$@"; do
            [ "$prev" = "--search" ] && search="$a" && break
            prev="$a"
          done
          [ -n "$search" ] && echo "$search"
        fi
        ;;
      create)
        # gh label create NAME --repo R ... → silent on success
        ;;
    esac
    ;;
  api)
    # gh api <path> [-X METHOD] [--jq Q] [-f body=...]
    method="GET"
    path=""
    jq_arg=""
    body_arg=""
    seen_api=0
    for a in "$@"; do
      if [ $seen_api -eq 1 ] && [ -z "$path" ] && [[ ! "$a" =~ ^- ]]; then
        path="$a"
        seen_api=2
      fi
      [ "$a" = "api" ] && seen_api=1
    done
    # Inspect for -X and --jq
    for ((i=1; i<=$#; i++)); do
      case "${!i}" in
        -X) j=$((i+1)); method="${!j}" ;;
        --jq) j=$((i+1)); jq_arg="${!j}" ;;
        -f) j=$((i+1)); body_arg="${!j}" ;;
      esac
    done

    case "$method:$path" in
      DELETE:*comments/*)
        # delete-comments path
        cid="${path##*/}"
        echo "deleted $cid"
        ;;
      PATCH:*comments/*)
        # update archive path
        if [ -n "$MOCK_GH_FAIL_PATCH" ]; then
          echo "mock: forced patch failure" >&2; exit 1
        fi
        ;;
      GET:*comments/*)
        # fetch existing archive body
        printf '%s' "${MOCK_GH_EXISTING_BODY:-}"
        ;;
      GET:*issues/*/comments)
        # search for marker
        # If MOCK_GH_EXISTING_ARCHIVE is set, return its ID. Otherwise empty.
        if [ -n "$MOCK_GH_EXISTING_ARCHIVE" ]; then
          echo "$MOCK_GH_EXISTING_ARCHIVE"
        fi
        ;;
      *)
        echo "{}"
        ;;
    esac
    ;;
esac

exit 0
