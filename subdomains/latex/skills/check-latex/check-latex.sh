#!/usr/bin/env bash
# check-latex.sh — mechanical evidence engine for the check-latex skill (F1a).
#
# Given a .tex file (and optionally a base git ref), this script produces the
# evidence block the human adjudicator needs to approve or reject a notes.tex change:
#   (a) compile status  — degrades GRACEFULLY to "toolchain unavailable" when
#                          no TeX build tool is present; NEVER fakes a compile.
#   (b) semantic diff    — which sections / theorems / equations were touched.
#   (c) files touched + exact diff pointer.
#
# Contract:
#   - READ-ONLY. Writes only under the output dir (default <city-root>/tmp-for-review/).
#   - Emits check-latex-report.json AND check-latex-report.md.
#   - Exit codes are ADVISORY on its own (report is the product); the gate's
#     poka-yoke check script (latex-gate-approval-required.sh) is what fails
#     closed. Exit 0 = report produced, 2 = usage error, 3 = target missing.
#
# Usage:
#   check-latex.sh <tex-file> [--root <root.tex>] [--section|--scope <selector>]
#       [--base <git-ref>] [--out <dir>] [--bead <id>]
#
set -euo pipefail

usage() {
  echo "usage: check-latex.sh <tex-file> [--root <root.tex>] [--section|--scope <selector>] [--base <git-ref>] [--out <dir>] [--bead <id>]" >&2
  exit 2
}

TEX=""
BASE=""
OUT=""
BEAD=""
ROOT=""
SCOPE=""

while [ $# -gt 0 ]; do
  case "$1" in
    --base) BASE="${2:-}"; shift 2 ;;
    --out)  OUT="${2:-}";  shift 2 ;;
    --bead) BEAD="${2:-}"; shift 2 ;;
    --root) ROOT="${2:-}"; shift 2 ;;
    --section|--scope) SCOPE="${2:-}"; shift 2 ;;
    -h|--help) usage ;;
    -*) echo "unknown flag: $1" >&2; usage ;;
    *)  if [ -z "$TEX" ]; then TEX="$1"; shift; else echo "unexpected arg: $1" >&2; usage; fi ;;
  esac
done

[ -n "$TEX" ] || usage

if [ ! -f "$TEX" ]; then
  echo "check-latex: target .tex not found: $TEX" >&2
  exit 3
fi

ROOT="${ROOT:-$TEX}"
if [ ! -f "$ROOT" ]; then
  echo "check-latex: compile root .tex not found: $ROOT" >&2
  exit 3
fi

BEAD="${BEAD:-unbeaded}"
OUT="${OUT:-$HOME/gt/tmp-for-review/$BEAD}"
mkdir -p "$OUT"

TEX_ABS="$(cd "$(dirname "$TEX")" && pwd)/$(basename "$TEX")"
TARGET_DIR="$(dirname "$TEX_ABS")"
ROOT_ABS="$(cd "$(dirname "$ROOT")" && pwd)/$(basename "$ROOT")"
ROOT_DIR="$(dirname "$ROOT_ABS")"
REPO_DIR="$TARGET_DIR"

# ---------------------------------------------------------------------------
# 1. Compile status — degrade gracefully; never fake.
# ---------------------------------------------------------------------------
COMPILE_TOOL=""
for t in latexmk pdflatex xelatex lualatex tectonic; do
  if command -v "$t" >/dev/null 2>&1; then COMPILE_TOOL="$t"; break; fi
done

COMPILE_STATUS=""
COMPILE_DETAIL=""
COMPILE_LOG="$OUT/compile.log"

if [ -z "$COMPILE_TOOL" ]; then
  COMPILE_STATUS="toolchain-unavailable"
  COMPILE_DETAIL="No TeX build tool (latexmk/pdflatex/xelatex/lualatex/tectonic) found on PATH. Compile not attempted; NOT faked."
else
  case "$COMPILE_TOOL" in
    latexmk)  BUILD_CMD="latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=$OUT $ROOT_ABS" ;;
    tectonic) BUILD_CMD="tectonic --outdir $OUT $ROOT_ABS" ;;
    *)        BUILD_CMD="$COMPILE_TOOL -interaction=nonstopmode -halt-on-error -output-directory=$OUT $ROOT_ABS" ;;
  esac
  if ( cd "$ROOT_DIR" && eval "$BUILD_CMD" ) >"$COMPILE_LOG" 2>&1; then
    if grep -Eq 'LaTeX Warning: .*undefined|Reference .* undefined' "$COMPILE_LOG"; then
      COMPILE_STATUS="pass-with-undefined-refs"
      COMPILE_DETAIL="Compiled but log has undefined references (cross-refs may need a second pass). tool=$COMPILE_TOOL root=$ROOT_ABS log=$COMPILE_LOG"
    else
      COMPILE_STATUS="pass"
      COMPILE_DETAIL="Compiled clean. tool=$COMPILE_TOOL root=$ROOT_ABS log=$COMPILE_LOG"
    fi
  else
    COMPILE_STATUS="fail"
    COMPILE_DETAIL="Compile FAILED. tool=$COMPILE_TOOL root=$ROOT_ABS log=$COMPILE_LOG (see log tail for the first error)."
  fi
fi

# ---------------------------------------------------------------------------
# 2. Diff acquisition + semantic diff (sections / theorems / equations).
# ---------------------------------------------------------------------------
DIFF_FILE="$OUT/tex.diff"
DIFF_STATUS=""
FILES_TOUCHED=""
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

in_git() { ( cd "$REPO_DIR" && git rev-parse --git-dir >/dev/null 2>&1 ); }

if in_git; then
  # Resolve the repo TOPLEVEL and run every git op from there, using a
  # toplevel-relative pathspec — running from a subdir with a --full-name
  # pathspec silently produces an empty (false-clean) diff.
  GIT_TOP="$( cd "$REPO_DIR" && git rev-parse --show-toplevel 2>/dev/null )"
  GIT_TOP="${GIT_TOP:-$REPO_DIR}"
  REL="$( cd "$GIT_TOP" && git ls-files --full-name "$TEX_ABS" 2>/dev/null | head -n1 )"
  REL="${REL:-$( cd "$GIT_TOP" && git ls-files --others --exclude-standard --full-name -- "$TEX_ABS" 2>/dev/null | head -n1 )}"
  REL="${REL:-$(python3 - "$GIT_TOP" "$TEX_ABS" <<'PY'
import os
import sys
print(os.path.relpath(sys.argv[2], sys.argv[1]))
PY
)}"
  if ( cd "$GIT_TOP" && git ls-files --error-unmatch -- "$REL" >/dev/null 2>&1 ); then
    TARGET_TRACKED=true
  else
    TARGET_TRACKED=false
  fi
  diff_target() {
    if [ "$TARGET_TRACKED" = true ]; then
      if [ -n "$1" ]; then
        ( cd "$GIT_TOP" && git diff "$1" -- "$REL" )
      else
        ( cd "$GIT_TOP" && git diff -- "$REL" )
      fi
    else
      # Untracked files have no ordinary git diff; compare them with /dev/null
      # so a scoped check still has a concrete full-file diff to scan.
      ( cd "$GIT_TOP" && git diff --no-index -- /dev/null "$REL" ) || true
    fi
  }
  if [ -n "$BASE" ]; then
    if [ "$TARGET_TRACKED" = true ] && ( cd "$GIT_TOP" && git rev-parse --verify "$BASE" >/dev/null 2>&1 ); then
      diff_target "$BASE" >"$DIFF_FILE" 2>/dev/null || true
      DIFF_STATUS="git-diff vs $BASE"
      FILES_TOUCHED="$REL"
    else
      if [ "$TARGET_TRACKED" = true ]; then
        DIFF_STATUS="base-ref-not-found: $BASE (fell back to working-tree diff)"
      else
        DIFF_STATUS="untracked-file-vs-/dev/null (base $BASE ignored)"
      fi
      diff_target "" >"$DIFF_FILE" 2>/dev/null || true
      FILES_TOUCHED="$REL"
    fi
  else
    diff_target "" >"$DIFF_FILE" 2>/dev/null || true
    if [ "$TARGET_TRACKED" = true ]; then
      DIFF_STATUS="git-diff working-tree vs HEAD"
    else
      DIFF_STATUS="untracked-file-vs-/dev/null"
    fi
    FILES_TOUCHED="$REL"
  fi
else
  DIFF_STATUS="not-a-git-repo (no diff available; whole-file treated as content)"
  : >"$DIFF_FILE"
fi

[ -n "$FILES_TOUCHED" ] || FILES_TOUCHED="$(basename "$TEX_ABS")"

# Semantic summary: scan the ADDED/REMOVED lines of the diff (fallback: whole file).
SCOPE_MATCH=false
SCOPE_NUMBER=""
SCOPE_HEADING=""
SCOPE_COMMAND=""
SCOPE_LEVEL=0
SCOPE_LABELS=""
SCOPE_START_LINE=0
SCOPE_END_LINE=0
SCOPE_CHANGED_LINES=0
SCOPE_META="$OUT/scope.json"
SCOPE_SOURCE="$OUT/scope-source.txt"
SCOPE_DIFF="$OUT/scope-diff.txt"

if [ -n "$SCOPE" ]; then
  if ! python3 "$SCRIPT_DIR/scope.py" "$TEX_ABS" "$ROOT_ABS" "$SCOPE" "$DIFF_FILE" "$SCOPE_META" "$SCOPE_SOURCE" "$SCOPE_DIFF"; then
    echo "check-latex: scope selector did not match exactly one heading: $SCOPE" >&2
    exit 2
  fi
  scope_get() {
    python3 -c 'import json,sys; value=json.load(open(sys.argv[1])).get(sys.argv[2], ""); print(value if value is not None else "")' "$SCOPE_META" "$1"
  }
  SCOPE_MATCH=true
  SCOPE_NUMBER="$(scope_get number)"
  SCOPE_HEADING="$(scope_get heading)"
  SCOPE_COMMAND="$(scope_get command)"
  SCOPE_LEVEL="$(scope_get level)"
  SCOPE_LABELS="$(scope_get labels)"
  SCOPE_START_LINE="$(scope_get start_line)"
  SCOPE_END_LINE="$(scope_get end_line)"
  SCOPE_CHANGED_LINES="$(scope_get changed_lines_in_scope)"
  if [ -s "$SCOPE_DIFF" ]; then
    SCAN_SRC="$(cat "$SCOPE_DIFF")"
  elif [ -s "$DIFF_FILE" ]; then
    # A real diff exists, but it did not touch the selected heading. Keep the
    # semantic counts empty rather than treating the unchanged scope as a diff.
    SCAN_SRC=""
  else
    SCAN_SRC="$(cat "$SCOPE_SOURCE")"
  fi
elif [ -s "$DIFF_FILE" ]; then
  SCAN_SRC="$( grep -E '^[+-]' "$DIFF_FILE" | grep -vE '^(\+\+\+|---)' || true )"
else
  SCAN_SRC="$( sed 's/^/+/' "$TEX_ABS" )"
fi

count_pat() { printf '%s\n' "$SCAN_SRC" | grep -cE "$1" || true; }

SECTIONS="$(   printf '%s\n' "$SCAN_SRC" | grep -oE '\\(sub)*section\*?\{[^}]*\}' | sort -u || true )"
THEOREMS="$(   printf '%s\n' "$SCAN_SRC" | grep -oE '\\begin\{(theorem|proposition|lemma|corollary|definition|remark|example|conjecture|question|claim)\}' | sort | uniq -c || true )"
N_EQUATIONS="$(count_pat '\\begin\{(equation|align|gather|multline|eqnarray)\*?\}')"
N_LABELS="$(   count_pat '\\label\{')"
N_CITES="$(    count_pat '\\cite[a-z]*\{')"
N_HUMAN_TAGS="$(count_pat '\\(taylor|david|claude|note|todo)\{')"

json_escape() { printf '%s' "$1" | python3 -c 'import json,sys; print(json.dumps(sys.stdin.read()))' 2>/dev/null || printf '""'; }

TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
TEX_SHA=""
if in_git; then TEX_SHA="$( cd "$REPO_DIR" && git hash-object "$TEX_ABS" 2>/dev/null || true )"; fi

# ---------------------------------------------------------------------------
# 3. Emit JSON + Markdown evidence block.
# ---------------------------------------------------------------------------
JSON="$OUT/check-latex-report.json"
MD="$OUT/check-latex-report.md"

{
  echo "{"
  echo "  \"skill\": \"check-latex\","
  echo "  \"status_banner\": \"PRELIMINARY (DRY-RUN ONLY)\","
  echo "  \"bead\": $(json_escape "$BEAD"),"
  echo "  \"timestamp\": $(json_escape "$TS"),"
  echo "  \"tex_file\": $(json_escape "$TEX_ABS"),"
  echo "  \"root_file\": $(json_escape "$ROOT_ABS"),"
  echo "  \"tex_sha\": $(json_escape "$TEX_SHA"),"
  echo "  \"compile\": {"
  echo "    \"status\": $(json_escape "$COMPILE_STATUS"),"
  echo "    \"tool\": $(json_escape "$COMPILE_TOOL"),"
  echo "    \"root_file\": $(json_escape "$ROOT_ABS"),"
  echo "    \"detail\": $(json_escape "$COMPILE_DETAIL"),"
  echo "    \"log\": $(json_escape "$COMPILE_LOG")"
  echo "  },"
  echo "  \"diff\": {"
  echo "    \"status\": $(json_escape "$DIFF_STATUS"),"
  echo "    \"pointer\": $(json_escape "$DIFF_FILE")"
  echo "  },"
  echo "  \"files_touched\": $(printf '%s\n' "$FILES_TOUCHED" | python3 -c 'import json,sys; print(json.dumps([l for l in sys.stdin.read().split() if l]))' 2>/dev/null || echo '[]'),"
  echo "  \"semantic\": {"
  echo "    \"equations_touched\": ${N_EQUATIONS:-0},"
  echo "    \"labels_touched\": ${N_LABELS:-0},"
  echo "    \"cites_touched\": ${N_CITES:-0},"
  echo "    \"unfinished_tags_touched\": ${N_HUMAN_TAGS:-0},"
  echo "    \"sections_touched\": $(printf '%s\n' "$SECTIONS" | python3 -c 'import json,sys; print(json.dumps([l for l in sys.stdin.read().split(chr(10)) if l.strip()]))' 2>/dev/null || echo '[]'),"
  echo "    \"theorem_envs_touched\": $(json_escape "$THEOREMS")"
  echo "  },"
  echo "  \"scope\": {"
  echo "    \"selector\": $(json_escape "$SCOPE"),"
  echo "    \"matched\": $SCOPE_MATCH,"
  echo "    \"number\": $(json_escape "$SCOPE_NUMBER"),"
  echo "    \"heading\": $(json_escape "$SCOPE_HEADING"),"
  echo "    \"command\": $(json_escape "$SCOPE_COMMAND"),"
  echo "    \"level\": $SCOPE_LEVEL,"
  echo "    \"labels\": $(printf '%s\n' "$SCOPE_LABELS" | python3 -c 'import ast,json,sys; value=sys.stdin.read().strip(); print(json.dumps(ast.literal_eval(value) if value else []))' 2>/dev/null || echo '[]'),"
  echo "    \"target_file\": $(json_escape "$TEX_ABS"),"
  echo "    \"root_file\": $(json_escape "$ROOT_ABS"),"
  echo "    \"start_line\": $SCOPE_START_LINE,"
  echo "    \"end_line\": $SCOPE_END_LINE,"
  echo "    \"changed_lines_in_scope\": $SCOPE_CHANGED_LINES"
  echo "  }"
  echo "}"
} >"$JSON"

{
  echo "# check-latex evidence block"
  echo ""
  echo "> **STATUS: PRELIMINARY (DRY-RUN ONLY)**"
  echo ""
  echo "- **bead:** $BEAD"
  echo "- **timestamp:** $TS"
  echo "- **tex file:** \`$TEX_ABS\`"
  echo "- **compile root:** \`$ROOT_ABS\`"
  echo "- **tex sha:** \`${TEX_SHA:-n/a}\`"
  echo ""
  echo "## 1. Compile status"
  echo ""
  echo "- **status:** \`$COMPILE_STATUS\`"
  echo "- **tool:** \`${COMPILE_TOOL:-none}\`"
  echo "- **detail:** $COMPILE_DETAIL"
  if [ -n "$SCOPE" ]; then
    echo ""
    echo "## Scope"
    echo ""
    echo "- selector: \`$SCOPE\`"
    echo "- matched: \`$SCOPE_MATCH\`"
    echo "- heading: \`${SCOPE_NUMBER:-$SCOPE_COMMAND} $SCOPE_HEADING\`"
    echo "- source range: lines $SCOPE_START_LINE-$SCOPE_END_LINE of \`$TEX_ABS\`"
    echo "- changed lines in scope: $SCOPE_CHANGED_LINES"
  fi
  echo ""
  echo "## 2. Files touched"
  echo ""
  printf '%s\n' "$FILES_TOUCHED" | sed 's/^/- `/;s/$/`/'
  echo ""
  echo "## 3. Semantic diff summary"
  echo ""
  echo "- equations touched: ${N_EQUATIONS:-0}"
  echo "- labels touched: ${N_LABELS:-0}"
  echo "- citations touched: ${N_CITES:-0}"
  echo "- unfinished tags (\\reviewer/\\david/\\claude/\\note/\\todo) touched: ${N_HUMAN_TAGS:-0}"
  echo ""
  echo "### Sections touched"
  echo ""
  if [ -n "$SECTIONS" ]; then printf '%s\n' "$SECTIONS" | sed 's/^/- `/;s/$/`/'; else echo "- (none detected)"; fi
  echo ""
  echo "### Theorem-class environments touched"
  echo ""
  if [ -n "$THEOREMS" ]; then printf '%s\n' "$THEOREMS" | sed 's/^/- /'; else echo "- (none detected)"; fi
  echo ""
  echo "## 4. Diff pointer"
  echo ""
  echo "- **diff status:** $DIFF_STATUS"
  echo "- **exact diff:** \`$DIFF_FILE\`"
  echo ""
  echo "---"
  echo ""
  echo "**Decision required from the human adjudicator:** approve or reject THIS specific diff before push/merge (LaTeX HARD GATE)."
} >"$MD"

echo "check-latex: wrote $JSON and $MD (compile=$COMPILE_STATUS)"
exit 0
