#!/usr/bin/env python3
"""Evidence gate for report-fix-briefed intake (design D5 / P6.1, decision mc-3q4v).

The single code-owner of the "is this bug report evidence-backed enough to draft a
fix-brief?" rule. The report-fix-briefed formula's `intake` step shells out to this
instead of hand-rolling the condition in bash, so the rule is one tested unit
rather than untested prose — and its refusal branch has an OBSERVED failing case
(tests/mctl/test_report_fix_evidence_gate.py), satisfying P6.2.

The rule (D5): an evidence-backed fix-brief needs, at minimum,
  (a repro OR a locatable code site)  AND  (at least one related/source bead).
A field carrying the literal placeholder `<unknown — needs input>` is ABSENT, not
present — fabricated-looking evidence must not satisfy the gate.

CLI (used by the formula intake):
    report_fix_evidence_gate.py --repro "$REPRO" --code-site "$SITE" --sources "$SRC"
Exit 0 + `PASS` on stdout when the gate passes; exit 3 + `BLOCKED: <missing>` on
stdout when it refuses (fail-closed, P6.1). `--json` emits the structured verdict.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field

UNKNOWN_MARKER = "<unknown — needs input>"
BLOCK_EXIT = 3


def _present(value: str | None) -> bool:
    """A field is present iff it is non-empty and not the unknown-placeholder."""
    if value is None:
        return False
    v = value.strip()
    if not v:
        return False
    if v == UNKNOWN_MARKER:
        return False
    return True


@dataclass
class Verdict:
    ok: bool
    missing: list[str] = field(default_factory=list)

    def as_line(self) -> str:
        return "PASS" if self.ok else "BLOCKED: " + ", ".join(self.missing)


def evidence_verdict(repro: str | None, code_site: str | None,
                     sources: str | None) -> Verdict:
    """Decide the evidence gate. Pure — no I/O — so it is directly unit-testable."""
    has_repro = _present(repro)
    has_code_site = _present(code_site)
    has_source = _present(sources)

    missing: list[str] = []
    if not (has_repro or has_code_site):
        missing.append("repro-or-code-site")
    if not has_source:
        missing.append("related-bead-or-source")
    return Verdict(ok=not missing, missing=missing)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="report-fix-briefed evidence gate")
    ap.add_argument("--repro", default="",
                    help="concrete repro: steps / observed failing output / a failing command")
    ap.add_argument("--code-site", default="",
                    help="locatable code site where the bug lives (file:line or symbol)")
    ap.add_argument("--sources", default="",
                    help="related/source bead ids (comma or space separated)")
    ap.add_argument("--json", action="store_true", help="emit the structured verdict")
    args = ap.parse_args(argv)

    v = evidence_verdict(args.repro, args.code_site, args.sources)
    if args.json:
        print(json.dumps({"ok": v.ok, "missing": v.missing}))
    else:
        print(v.as_line())
    return 0 if v.ok else BLOCK_EXIT


if __name__ == "__main__":
    sys.exit(main())
