#!/usr/bin/env bash
# latex-gate-approval-required.sh — poka-yoke enforcement for the LaTeX HARD GATE.
#
# Fails CLOSED. Exit 0 = gate satisfied (push/merge may proceed). Exit 1 = gate
# blocks. Exit 2 = usage / misconfiguration (also blocks).
#
# The gate: any edit to notes.tex or any notes-tier .tex file in the
# differential-valuations, hecke, homog, or jacobi rigs requires the human adjudicator's
# explicit approval of the SPECIFIC diff before push/merge.
#
# This script is MECHANICAL. It answers exactly one question: does the diff
# under evaluation touch a covered .tex file, and if so, is there (a) a
# check-latex evidence report AND (b) a recorded human approval pinned to the
# SPECIFIC diff sha? If the diff touches no covered file, the gate is N/A and
# passes. If it touches a covered file without both artifacts, it BLOCKS.
#
# Inputs (env, all optional except at least one diff source):
#   LATEX_GATE_DIFF        path to a unified .tex diff to evaluate, OR
#   LATEX_GATE_BASE        git ref to diff the working tree / HEAD against
#   LATEX_GATE_REPO        repo dir (default: cwd)
#   LATEX_GATE_EVIDENCE    dir holding check-latex-report.{json,md}
#                          (default: $HOME/gt/tmp-for-review/$GC_BEAD_ID)
#   LATEX_GATE_APPROVAL    path to the approval record (toml/json/txt) that must
#                          name the human adjudicator + pin the approved diff sha
#   GC_BEAD_ID             bead id (used to locate default evidence dir)
#
set -eu

block() { echo "latex-gate: BLOCK — $*" >&2; exit 1; }
misuse() { echo "latex-gate: MISCONFIG — $*" >&2; exit 2; }
ok() { echo "latex-gate: PASS — $*"; exit 0; }

REPO="${LATEX_GATE_REPO:-$PWD}"
BEAD="${GC_BEAD_ID:-}"

# Rigs whose notes-tier .tex files are covered by the HARD GATE.
COVERED_RIGS='differential-valuations|hecke|homog|jacobi'

# ---------------------------------------------------------------------------
# 1. Acquire the list of .tex files the diff touches.
# ---------------------------------------------------------------------------
touched=""
if [ -n "${LATEX_GATE_DIFF:-}" ]; then
  [ -f "$LATEX_GATE_DIFF" ] || misuse "LATEX_GATE_DIFF not a file: $LATEX_GATE_DIFF"
  # +++ b/path lines name the post-image files in a unified diff.
  touched="$(grep -E '^\+\+\+ b/' "$LATEX_GATE_DIFF" | sed 's|^\+\+\+ b/||' | grep -E '\.tex$' || true)"
elif [ -n "${LATEX_GATE_BASE:-}" ]; then
  ( cd "$REPO" && git rev-parse --git-dir >/dev/null 2>&1 ) || misuse "not a git repo: $REPO"
  ( cd "$REPO" && git rev-parse --verify "$LATEX_GATE_BASE" >/dev/null 2>&1 ) ||
    misuse "base ref not found: $LATEX_GATE_BASE"
  touched="$( cd "$REPO" && git diff --name-only "$LATEX_GATE_BASE" 2>/dev/null | grep -E '\.tex$' || true )"
else
  ( cd "$REPO" && git rev-parse --git-dir >/dev/null 2>&1 ) ||
    misuse "no LATEX_GATE_DIFF and no LATEX_GATE_BASE and cwd is not a git repo"
  touched="$( cd "$REPO" && git diff --name-only 2>/dev/null | grep -E '\.tex$' || true )"
fi

# ---------------------------------------------------------------------------
# 2. Is any touched .tex file COVERED?
#    Covered = named notes.tex, OR under a latex/notes/ tree, OR the repo path
#    is one of the four rigs and the file is notes-tier.
# ---------------------------------------------------------------------------
repo_real="$(cd "$REPO" 2>/dev/null && pwd -P || echo "$REPO")"
covered=""
for f in $touched; do
  base="$(basename "$f")"
  if [ "$base" = "notes.tex" ] || printf '%s' "$f" | grep -Eq '(^|/)latex/notes/'; then
    # In-rig gating: only enforce for the four covered rigs.
    if printf '%s' "$repo_real" | grep -Eq "($COVERED_RIGS)(/|$)" ||
       printf '%s' "$f" | grep -Eq "($COVERED_RIGS)(/|$)"; then
      covered="$covered $f"
    fi
  fi
done

covered="$(printf '%s\n' $covered | sed '/^$/d' | sort -u | tr '\n' ' ')"

if [ -z "$(printf '%s' "$covered" | tr -d '[:space:]')" ]; then
  ok "diff touches no covered notes-tier .tex in {${COVERED_RIGS}} — gate N/A"
fi

echo "latex-gate: covered files:$covered" >&2

# ---------------------------------------------------------------------------
# 3. Require a check-latex evidence report.
# ---------------------------------------------------------------------------
EVID="${LATEX_GATE_EVIDENCE:-}"
if [ -z "$EVID" ] && [ -n "$BEAD" ]; then
  EVID="$HOME/gt/tmp-for-review/$BEAD"
fi
[ -n "$EVID" ] || block "covered .tex touched but no check-latex evidence dir (set LATEX_GATE_EVIDENCE or GC_BEAD_ID)"
[ -f "$EVID/check-latex-report.json" ] ||
  block "missing check-latex evidence: $EVID/check-latex-report.json — run the check-latex skill first"
[ -f "$EVID/check-latex-report.md" ] ||
  block "missing check-latex evidence: $EVID/check-latex-report.md — run the check-latex skill first"

# ---------------------------------------------------------------------------
# 4. Require an explicit human approval PINNED to the specific diff.
#    Poka-yoke: the approval record must (a) name the human adjudicator as approver, (b) carry
#    an approved-diff sha, and (c) that sha must match the sha of the diff under
#    evaluation. A stale approval for a different diff does NOT satisfy the gate.
# ---------------------------------------------------------------------------
APPROVAL="${LATEX_GATE_APPROVAL:-}"
if [ -z "$APPROVAL" ] && [ -n "$EVID" ] && [ -f "$EVID/latex-approval.toml" ]; then
  APPROVAL="$EVID/latex-approval.toml"
fi
[ -n "$APPROVAL" ] && [ -f "$APPROVAL" ] ||
  block "covered .tex touched but no human approval record (set LATEX_GATE_APPROVAL or place $EVID/latex-approval.toml)"

grep -Eiq '(^|[^a-z])(approver|authorized_by)[[:space:]]*=[[:space:]]*"?the human adjudicator"?' "$APPROVAL" ||
  block "approval record does not name the human adjudicator as approver: $APPROVAL"

approved_sha="$(grep -Ei '^[[:space:]]*(approved_diff_sha|diff_sha)[[:space:]]*=' "$APPROVAL" |
  head -n1 | sed -E 's/.*=[[:space:]]*"?([0-9a-fA-F]+)"?.*/\1/' || true)"
[ -n "$approved_sha" ] ||
  block "approval record has no approved_diff_sha — the gate requires per-diff approval, not blanket sign-off: $APPROVAL"

# Compute the sha of the diff under evaluation.
diff_sha=""
if [ -n "${LATEX_GATE_DIFF:-}" ]; then
  diff_sha="$(git hash-object "$LATEX_GATE_DIFF" 2>/dev/null || shasum "$LATEX_GATE_DIFF" 2>/dev/null | awk '{print $1}')"
elif [ -f "$EVID/tex.diff" ]; then
  diff_sha="$(git hash-object "$EVID/tex.diff" 2>/dev/null || shasum "$EVID/tex.diff" 2>/dev/null | awk '{print $1}')"
fi
[ -n "$diff_sha" ] ||
  block "cannot compute sha of the diff under evaluation (no LATEX_GATE_DIFF and no $EVID/tex.diff) — cannot verify per-diff approval"

# Prefix match tolerates short shas in the approval record.
case "$diff_sha" in
  "$approved_sha"*|*"$approved_sha"*) : ;;
  *) block "approval sha ($approved_sha) does not match diff under evaluation ($diff_sha) — stale/blanket approval rejected; the human adjudicator must approve THIS diff" ;;
esac

ok "covered .tex diff has check-latex evidence + human approval pinned to diff sha $diff_sha"
