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
#   check-latex.sh <tex-file> [--base <git-ref>] [--out <dir>] [--bead <id>]
#
set -euo pipefail

usage() {
  echo "usage: check-latex.sh <tex-file> [--base <git-ref>] [--out <dir>] [--bead <id>]" >&2
  exit 2
}

TEX=""
BASE=""
OUT=""
BEAD=""

while [ $# -gt 0 ]; do
  case "$1" in
    --base) BASE="${2:-}"; shift 2 ;;
    --out)  OUT="${2:-}";  shift 2 ;;
    --bead) BEAD="${2:-}"; shift 2 ;;
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

BEAD="${BEAD:-unbeaded}"
OUT="${OUT:-$HOME/gt/tmp-for-review/$BEAD}"
mkdir -p "$OUT"

TEX_ABS="$(cd "$(dirname "$TEX")" && pwd)/$(basename "$TEX")"
REPO_DIR="$(dirname "$TEX_ABS")"

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
    latexmk)  BUILD_CMD="latexmk -pdf -interaction=nonstopmode -halt-on-error -outdir=$OUT $TEX_ABS" ;;
    tectonic) BUILD_CMD="tectonic --outdir $OUT $TEX_ABS" ;;
    *)        BUILD_CMD="$COMPILE_TOOL -interaction=nonstopmode -halt-on-error -output-directory=$OUT $TEX_ABS" ;;
  esac
  if ( cd "$REPO_DIR" && eval "$BUILD_CMD" ) >"$COMPILE_LOG" 2>&1; then
    if grep -Eq 'LaTeX Warning: .*undefined|Reference .* undefined' "$COMPILE_LOG"; then
      COMPILE_STATUS="pass-with-undefined-refs"
      COMPILE_DETAIL="Compiled but log has undefined references (cross-refs may need a second pass). tool=$COMPILE_TOOL log=$COMPILE_LOG"
    else
      COMPILE_STATUS="pass"
      COMPILE_DETAIL="Compiled clean. tool=$COMPILE_TOOL log=$COMPILE_LOG"
    fi
  else
    COMPILE_STATUS="fail"
    COMPILE_DETAIL="Compile FAILED. tool=$COMPILE_TOOL log=$COMPILE_LOG (see log tail for the first error)."
  fi
fi

# ---------------------------------------------------------------------------
# 2. Diff acquisition + semantic diff (sections / theorems / equations).
# ---------------------------------------------------------------------------
DIFF_FILE="$OUT/tex.diff"
DIFF_STATUS=""
FILES_TOUCHED=""

in_git() { ( cd "$REPO_DIR" && git rev-parse --git-dir >/dev/null 2>&1 ); }

if in_git; then
  # Resolve the repo TOPLEVEL and run every git op from there, using a
  # toplevel-relative pathspec — running from a subdir with a --full-name
  # pathspec silently produces an empty (false-clean) diff.
  GIT_TOP="$( cd "$REPO_DIR" && git rev-parse --show-toplevel 2>/dev/null )"
  GIT_TOP="${GIT_TOP:-$REPO_DIR}"
  REL="$( cd "$GIT_TOP" && git ls-files --full-name "$TEX_ABS" 2>/dev/null | head -n1 )"
  REL="${REL:-$(basename "$TEX_ABS")}"
  if [ -n "$BASE" ]; then
    if ( cd "$GIT_TOP" && git rev-parse --verify "$BASE" >/dev/null 2>&1 ); then
      ( cd "$GIT_TOP" && git diff "$BASE" -- "$REL" ) >"$DIFF_FILE" 2>/dev/null || true
      DIFF_STATUS="git-diff vs $BASE"
      FILES_TOUCHED="$( cd "$GIT_TOP" && git diff --name-only "$BASE" 2>/dev/null | grep -E '\.tex$' || true )"
    else
      DIFF_STATUS="base-ref-not-found: $BASE (fell back to working-tree diff)"
      ( cd "$GIT_TOP" && git diff -- "$REL" ) >"$DIFF_FILE" 2>/dev/null || true
      FILES_TOUCHED="$( cd "$GIT_TOP" && git diff --name-only 2>/dev/null | grep -E '\.tex$' || true )"
    fi
  else
    ( cd "$GIT_TOP" && git diff -- "$REL" ) >"$DIFF_FILE" 2>/dev/null || true
    DIFF_STATUS="git-diff working-tree vs HEAD"
    FILES_TOUCHED="$( cd "$GIT_TOP" && git diff --name-only 2>/dev/null | grep -E '\.tex$' || true )"
  fi
else
  DIFF_STATUS="not-a-git-repo (no diff available; whole-file treated as content)"
  : >"$DIFF_FILE"
fi

[ -n "$FILES_TOUCHED" ] || FILES_TOUCHED="$(basename "$TEX_ABS")"

# Semantic summary: scan the ADDED/REMOVED lines of the diff (fallback: whole file).
if [ -s "$DIFF_FILE" ]; then
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
  echo "  \"tex_sha\": $(json_escape "$TEX_SHA"),"
  echo "  \"compile\": {"
  echo "    \"status\": $(json_escape "$COMPILE_STATUS"),"
  echo "    \"tool\": $(json_escape "$COMPILE_TOOL"),"
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
  echo "- **tex sha:** \`${TEX_SHA:-n/a}\`"
  echo ""
  echo "## 1. Compile status"
  echo ""
  echo "- **status:** \`$COMPILE_STATUS\`"
  echo "- **tool:** \`${COMPILE_TOOL:-none}\`"
  echo "- **detail:** $COMPILE_DETAIL"
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
