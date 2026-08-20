#!/usr/bin/env python3
"""Repair ungated compact briefs into full form, and record that it happened.

POLICY B1.3 makes compact form **gated, not default**: it is allowed only for a
brief the no-brainer classifier cleared. `create-brief` SKILL.md states the same
three conditions. The corpus does not comply -- measured 2026-08-19 and
re-measured 2026-08-20 against `~/gt/.beads/briefs/stack/`, 19 of 89 briefs are
`form: compact` and 18 of those carry no `no_brainer_classification` at all.

**Why this may be automated at all.** Two owner rulings interlock:

    "I would rather enforce this with the no-brainer contract rather than a
    hard fail."          ... and, on brief shape generally ...
    "But let ME reject the brief so we pick up the signal."

Rejection is a verdict on a brief's *content*; it belongs to the owner and is
never automated. Repair is a change to a brief's *shape* that leaves the
decision intact; it belongs to the contract. A repaired brief still reaches the
stack and still needs the owner's verdict -- it is merely legible when it gets
there. So this tool never writes a verdict, never sets a disposition status,
never closes anything, and never removes a file.

**Why the recording is not bookkeeping.** A *silent* repair would destroy the
producer signal exactly as an auto-reject would: afterwards nothing would say
that a producer keeps filing ungated compact briefs. The record is therefore
the reason the automation is permissible, not a nicety attached to it. Each
repaired brief keeps `arrived_form`, a token `repair_reason`, and the producing
lane, so the population stays countable by `grep` alone.

**Nothing is synthesized.** The compact shape has no slot for §3 assumptions,
§4 alternatives, §5 risks, §6 evidence or the gate table, so the producer
supplied none. Those sections are appended marked `NOT SUPPLIED` -- absent, and
visibly so. Filling them in would fabricate evidence, which is the one failure
mode worse than the shape defect this closes.

Dry-run is the default, as it is for `brief-stack-index.py`: these are files a
human is queued to read.
"""

from __future__ import annotations

import argparse
import collections
import datetime as dt
import json
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


sys.path.insert(0, str(Path(__file__).resolve().parent))

from mctl_core.materialize_plan import is_disposed, parse_stack_file  # noqa: E402


#: Bumped when the emitted record's shape changes, so a later reader can tell
#: which contract produced a given repair rather than assuming the current one.
TOOL_ID = "brief-compact-repair.v1"

#: One token, not a sentence. The same argument as verdict-source provenance:
#: a reason that varies per file cannot be counted, and counting is the whole
#: point of recording it.
REPAIR_REASON = "B1.3-compact-without-no-brainer-classification"

#: The 7 grill-ordered sections, per `present-it` §"Full-form template" and
#: `create-brief`. `Gate Evidence` is required in BOTH shapes (B1.4) and so is
#: appended too when the arriving brief has none.
FULL_FORM_SECTIONS = (
    (1, "What is being decided"),
    (2, "Recommended answer"),
    (3, "Assumptions"),
    (4, "Alternatives"),
    (5, "Risks"),
    (6, "Evidence"),
    (7, "Plan membership and required gates"),
)

#: A heading that opens a numbered section: `## §1 ...`, `### 1. ...`, `## 1 ...`.
#: Anchored to a line start. An unanchored search would match the `§1` inside a
#: cross-reference in prose and conclude a section exists that does not --
#: which is the defect class (`.replace('-brief','')`, a body substring) that
#: this whole queue exists to close, and it has shipped twice.
_SECTION_HEADING = re.compile(r"^#{1,4}[ \t]*(?:§[ \t]*)?(\d)[.:)\s]", re.MULTILINE)

#: The compact form's own opening key. Used only to place the §1 heading above
#: a body that has no heading at all; anchored to a line start for the same
#: reason as above.
_DECISION_LINE = re.compile(r"^[ \t]*DECISION[ \t]*:", re.MULTILINE)

_GATE_EVIDENCE_HEADING = re.compile(r"^#{1,4}[ \t]*Gate Evidence\b", re.MULTILINE | re.IGNORECASE)

#: Keys whose presence proves this file already went through a repair. Checked
#: independently of `form`, so a hand-edit that put `compact` back cannot stack
#: a second scaffold on top of the first.
_REPAIR_MARKER_KEYS = ("arrived_form", "repaired_by", "repair_reason")

_ABSENT = "NOT SUPPLIED"


@dataclass(frozen=True)
class Skip:
    file: str
    reason: str

    def to_dict(self) -> dict[str, str]:
        return {"file": self.file, "reason": self.reason}


def atomic_write_text(path: Path, text: str) -> None:
    """Replace `path`'s contents in one rename.

    The stack is read concurrently by the clerk and by `mctl`; a half-written
    brief would be parsed as a brief with no frontmatter.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w") as handle:
            handle.write(text)
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def split_document(text: str) -> tuple[str, str] | None:
    """`(frontmatter block, body)`, or None when there is no frontmatter.

    The split is on the raw bytes rather than on a re-serialization of the
    parsed mapping, because the arriving frontmatter must survive byte-for-byte
    -- several live values (`needs-revision(a:b;c)`, `none (blocks gt-g2e +
    brief 04)`, `test-evidence N/A (decision-shaped, ...)`) do not round-trip
    through any writer that normalises them.
    """
    if not text.startswith("---"):
        return None
    end = text.find("\n---", 3)
    if end < 0:
        return None
    newline = text.find("\n", end + 1)
    if newline < 0:
        return None
    return text[4:end], text[newline + 1 :]


def sections_present(body: str) -> list[int]:
    return sorted({int(m.group(1)) for m in _SECTION_HEADING.finditer(body)})


def repair_frontmatter(block: str, now: str) -> str:
    """The arriving block with `form` retargeted and the repair record appended.

    Every other line is passed through untouched, in its arriving order and
    with its arriving spacing. Only the `form:` line is rewritten, and only its
    value: a brief whose author wrote `form:compact` keeps that spelling of the
    separator, because reformatting it would be a change nobody asked for and
    would show up in every future diff of the file.
    """
    lines = block.splitlines()
    for index, line in enumerate(lines):
        match = re.match(r"^([ \t]*form[ \t]*:[ \t]*)compact[ \t]*$", line)
        if match:
            lines[index] = match.group(1) + "full"
            break
    lines.extend(
        [
            "arrived_form: compact",
            f"repair_reason: {REPAIR_REASON}",
            f"repaired_by: {TOOL_ID}",
            f"repaired_at: {now}",
        ]
    )
    return "\n".join(lines)


def repair_body(body: str) -> tuple[str, list[int], bool]:
    """The arriving body, plus the sections it had no slot for.

    Returns `(body, appended section numbers, whether a gate table was added)`.

    The arriving prose is never rewritten. Two things happen around it: a §1
    heading is inserted *above* the arriving `DECISION:` block when the body
    carries no heading at all (B1.1 -- the decision must be the first content,
    and in these briefs it already is; only the heading is missing), and the
    remaining sections are appended below it marked absent.
    """
    present = sections_present(body)
    out = body

    if 1 not in present:
        decision = _DECISION_LINE.search(out)
        if decision is not None:
            out = out[: decision.start()] + "## §1 What is being decided\n\n" + out[decision.start() :]
            present = sections_present(out)

    missing = [number for number, _ in FULL_FORM_SECTIONS if number not in present]
    needs_gates = _GATE_EVIDENCE_HEADING.search(out) is None
    if not missing and not needs_gates:
        return out, [], False

    titles = dict(FULL_FORM_SECTIONS)
    parts = [
        out.rstrip("\n"),
        "",
        "---",
        "",
        "## Shape repair — POLICY B1.3",
        "",
        "**This brief arrived in compact form with no no-brainer classification, which",
        "B1.3 does not permit. Its shape was repaired to full form. Its content was not",
        "changed, no verdict was recorded, and it still needs an adjudication.**",
        "",
        "The sections below carry no producer material. The compact form has no slot for",
        f"them, so they are marked `{_ABSENT}` rather than filled in — the gap is the",
        "signal, and inventing evidence to close it would be worse than the shape defect.",
        "",
    ]
    for number in missing:
        parts += [f"## §{number} {titles[number]}", "", f"{_ABSENT} — arrived in compact form.", ""]
    if needs_gates:
        parts += [
            "## Gate Evidence",
            "",
            f"{_ABSENT} — arrived in compact form. B1.4 requires one entry per gate of",
            "the active `gates.toml` profile, each with evidence or an explicit N/A.",
            "",
        ]
    return "\n".join(parts), missing, needs_gates


def classify(path: Path) -> tuple[str | None, dict[str, str], str]:
    """`(skip reason or None, frontmatter, text)` for one stack file."""
    text = path.read_text(encoding="utf-8", errors="replace")
    frontmatter = dict(parse_stack_file(path.name, text).frontmatter)

    if (frontmatter.get("test_only") or "").strip().lower() == "true":
        return "test-only-canary", frontmatter, text
    if frontmatter.get("form") != "compact":
        # Includes the 39 briefs carrying no `form` key at all. 35 of them are
        # full-shaped, 3 are test canaries and 1 is compact-shaped but already
        # adjudicated -- none is a B1.3 case, and backfilling `form:` on a
        # brief that never declared one would assert a claim nobody made.
        return "not-compact", frontmatter, text
    if any(key in frontmatter for key in _REPAIR_MARKER_KEYS):
        return "already-repaired", frontmatter, text
    if frontmatter.get("no_brainer_classification"):
        # B1.3-compliant: the classifier cleared it. `gh-38` is the live case.
        return "classified", frontmatter, text
    if is_disposed(frontmatter.get("status") or ""):
        # The owner's instruction: "Repair unless they are already closed."
        return "already-disposed", frontmatter, text
    return None, frontmatter, text


def command_repair(args: argparse.Namespace) -> int:
    brief_root = Path(args.brief_root).expanduser()
    stack = brief_root / "stack"
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    repaired: list[dict[str, Any]] = []
    skipped: list[Skip] = []
    unparsed: list[str] = []
    writes: list[tuple[Path, str]] = []

    for path in sorted(stack.glob("*.md")):
        reason, frontmatter, text = classify(path)
        if reason is not None:
            # `not-compact` is the overwhelming majority and says nothing; the
            # reasons worth reporting are the ones that describe a brief the
            # tool deliberately declined to touch.
            if reason != "not-compact":
                skipped.append(Skip(path.name, reason))
            continue

        split = split_document(text)
        if split is None:
            unparsed.append(path.name)
            continue
        block, body = split

        before = sections_present(body)
        new_body, appended, gates_added = repair_body(body)
        new_text = "---\n" + repair_frontmatter(block, now) + "\n---\n" + new_body

        repaired.append(
            {
                "file": path.name,
                "form_before": "compact",
                "form_after": "full",
                "status": frontmatter.get("status"),
                "track": frontmatter.get("track"),
                "sections_present_before": before,
                "sections_appended": appended,
                "gate_evidence_appended": gates_added,
                "bytes_before": len(text.encode("utf-8")),
                "bytes_after": len(new_text.encode("utf-8")),
            }
        )
        writes.append((path, new_text))

    by_track = collections.Counter(entry["track"] or "UNDECLARED" for entry in repaired)
    report = {
        "apply": args.apply,
        "brief_root": str(brief_root),
        "command": "repair",
        "repair_reason": REPAIR_REASON,
        "repaired": repaired,
        "repaired_by_track": dict(sorted(by_track.items())),
        "repaired_count": len(repaired),
        "skipped": [skip.to_dict() for skip in skipped],
        "stack_file_count": len(list(stack.glob("*.md"))),
        "tool": TOOL_ID,
        "unparsed": unparsed,
    }
    print(json.dumps(report, indent=2, sort_keys=True))

    if args.apply:
        for path, new_text in writes:
            atomic_write_text(path, new_text)
    return 0


def main() -> int:
    # No subcommand: unlike `brief-stack-index.py`, which needs one to tell its
    # three operations apart, this tool has exactly one operation, and dry-run
    # versus `--apply` is the only axis a caller varies.
    parser = argparse.ArgumentParser(description="Repair ungated compact briefs into full form.")
    parser.add_argument("--brief-root", required=True)
    parser.add_argument("--apply", action="store_true")
    return command_repair(parser.parse_args())


if __name__ == "__main__":
    raise SystemExit(main())
