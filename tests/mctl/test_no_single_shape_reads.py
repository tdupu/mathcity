"""Fail when an attribute is read from one shape only.

Six times in this package an attribute was read with `.get("name")`,
found nothing because the core had put it under `fields`, and the result
was rendered as "there is nothing here". Careful review caught five and
missed the sixth. This catches the seventh mechanically.

The allowlist holds keys that genuinely live at the top level of a
payload and never inside a `fields` map -- envelope keys rather than
brief attributes. Adding to it is a deliberate act; adding an attribute
to it is how this test stops working.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "assets" / "scripts" / "mctl_dashboard"
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

#: Attributes that live on a brief and may appear under `fields`.
GUARDED = frozenset({
    "unlock_count", "priority", "track", "form", "gates", "verdict",
    "artifact", "bead_id", "brief_id", "rig_id", "canonical_source",
    "decision_state", "status", "kind", "sev", "title", "created_at",
    "recommendation", "decision_options", "defer_until", "deposited_by",
})

#: Reads that are legitimately single-shape.
ALLOWED_FILES = frozenset({
    "reading.py",       # the helper itself
    "aggregate.py",     # consumes the city envelope, not brief rows
    "preview.py",       # consumes tool arguments, not brief rows
    "client.py",        # consumes JSON-RPC envelopes
})

PATTERN = re.compile(r'\.get\(\s*["\']([a-z_]+)["\']')


def test_no_single_shape_reads():
    offenders: list[str] = []
    for path in sorted(PACKAGE.rglob("*.py")):
        if path.name in ALLOWED_FILES or "__pycache__" in path.parts:
            continue
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if "# single-shape-ok" in line:
                continue
            for key in PATTERN.findall(line):
                if key in GUARDED:
                    rel = path.relative_to(ROOT)
                    offenders.append(f"{rel}:{number}  .get({key!r})")
    assert not offenders, (
        "Attribute read from one shape only -- use reading.attr(brief, key).\n"
        "If the read is genuinely against an envelope rather than a brief "
        "row, append '# single-shape-ok' to the line with a reason.\n\n"
        + "\n".join(offenders)
    )
