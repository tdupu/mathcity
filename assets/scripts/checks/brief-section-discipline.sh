#!/bin/sh
# G17 section discipline, over brief markdown files.
#
# ONE RULE, ONE PLACE. This does NOT reimplement the check in shell. It calls
# the same `mctl_core.structure.section_discipline_violations` that refuses at
# creation, reading the same `assets/brief-pipeline/section-discipline.toml`.
# A shell re-derivation is the drift #35 was filed about, and #169 records the
# repo already paying for it once.
#
# Usage:
#   brief-section-discipline.sh <brief.md> [<brief.md> ...]
#   brief-section-discipline.sh            # the brief this step is working on
#
# Exit 0 when every named brief is clean or out of scope; exit 1 on the first
# violation, having printed every violation on every file.
set -eu

script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
scripts_root=$(CDPATH= cd -- "$script_dir/.." && pwd)

if [ "$#" -eq 0 ]; then
    ROOT="${BRIEF_ROOT:-.beads/briefs}"
    if [ -n "${GC_BRIEF_PATH:-}" ]; then
        set -- "$GC_BRIEF_PATH"
    else
        found=$(find "$ROOT/.staging" -type f -name 'brief.md' 2>/dev/null | sort | head -n 1)
        [ -n "$found" ] || {
            echo "brief-section-discipline: no brief named and none found under $ROOT/.staging" >&2
            exit 2
        }
        set -- "$found"
    fi
fi

PYTHONPATH="$scripts_root${PYTHONPATH:+:$PYTHONPATH}" exec python3 - "$@" <<'PY'
import sys
from pathlib import Path

from mctl_core.briefs import parse_brief_sections
from mctl_core.structure import section_discipline_violations

failed = 0
checked = 0
for name in sys.argv[1:]:
    path = Path(name)
    if not path.is_file():
        print(f"brief-section-discipline: missing file: {path}", file=sys.stderr)
        failed += 1
        continue
    body = path.read_text(encoding="utf-8", errors="replace")
    violations = section_discipline_violations(parse_brief_sections(body))
    checked += 1
    for v in violations:
        where = f":{v.line}" if v.line else ""
        print(f"{path}{where}: {v.condition} {v.code} {v.summary} [{v.detail}] -> {v.remedy}")
    if violations:
        failed += 1

print(f"brief-section-discipline: {checked} file(s) checked, {failed} failing", file=sys.stderr)
sys.exit(1 if failed else 0)
PY
