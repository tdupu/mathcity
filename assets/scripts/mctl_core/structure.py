"""Structural requirements for a brief body (#169).

One rule, one place. See `assets/brief-pipeline/required-sections.toml` for why
this is data rather than code.
"""
from __future__ import annotations

import re
import tomllib
from collections.abc import Iterable
from pathlib import Path
from typing import Any, NamedTuple

RULES_PATH = Path(__file__).resolve().parents[2] / "brief-pipeline" / "required-sections.toml"


def required_sections(path: Path | None = None) -> list[dict[str, Any]]:
    """The sections a brief body must carry. Absent file -> no requirements.

    An absent rules file yields an EMPTY list, which is permissive -- and that is
    deliberate rather than an oversight. This gate runs at creation, where
    refusing every brief because a data file is missing would take the tool down
    entirely. The drain-time checker still holds the line, so a missing file
    degrades to today's behaviour rather than to a hole.
    """
    target = path or RULES_PATH
    if not target.is_file():
        return []
    with target.open("rb") as handle:
        return list(tomllib.load(handle).get("section") or [])


def missing_sections(body: str, path: Path | None = None) -> list[dict[str, Any]]:
    """Required sections absent from `body`.

    Matched with the shell checker's own regex, translated only where POSIX and
    Python classes differ (`[[:space:]]` -> `\\s`). Anchored per line, because
    the shell patterns are `^`-anchored and a substring search would accept a
    body that merely mentions the section name in prose.
    """
    absent: list[dict[str, Any]] = []
    for section in required_sections(path):
        pattern = str(section.get("match") or "").replace("[[:space:]]", r"\s")
        if not pattern:
            continue
        if not re.search(pattern, body, re.MULTILINE):
            absent.append(section)
    return absent


# --- G17 section discipline (mc-qbs6j) ---------------------------------------
#
# `mc-67snh` carried every mandated heading and still hid its findings, so
# `required_sections` above — which only asks whether a heading EXISTS — passed
# it. This asks the next question: is the content under the heading the kind of
# content that heading promises?
#
# Takes ALREADY-PARSED sections rather than a body, so this module keeps no
# import of `briefs.py` (which imports this one). The caller owns the parser;
# `parse_brief_sections` is the only one in the codebase and is not duplicated
# here.

DISCIPLINE_PATH = (
    Path(__file__).resolve().parents[2] / "brief-pipeline" / "section-discipline.toml"
)


class SectionViolation(NamedTuple):
    """One G17 finding: which condition, where, and what to do about it."""

    condition: str          # "C1" | "C2" | "C3"
    code: str               # the MBRF diagnostic code the caller raises
    summary: str            # one line, names the offending thing
    detail: str             # the matched text or the duplicated headings
    remedy: str             # what the author does next
    line: int | None        # 1-based line of the offending heading, when known
    blocking: bool          # True -> refuses the write; False -> WARN advisory


def discipline_rules(path: Path | None = None) -> dict[str, Any]:
    """The G17 vocabulary. Absent file -> `{}`, which disables the gate.

    Permissive-on-absent for the same reason `required_sections` is: this runs
    at creation, and refusing every brief because a data file is missing would
    take the tool down entirely. A missing file degrades to the behaviour that
    existed before the gate, never to a silent pass that claims to have checked.
    """
    target = path or DISCIPLINE_PATH
    if not target.is_file():
        return {}
    with target.open("rb") as handle:
        return dict(tomllib.load(handle))


def _explicit(sections: Iterable[Any]) -> list[Any]:
    """Sections whose heading literally carries `§N` / `Section N`.

    Heading-vocabulary matches are deliberately excluded from the duplicate
    test: `_classify_heading` maps both "Alternatives named" and "Options" to
    §4 by vocabulary, so counting inferred matches would report a duplicate
    number on a brief that wrote only one.
    """
    return [s for s in sections if getattr(s, "match", None) == "explicit"]


def section_discipline_violations(
    sections: Iterable[Any], path: Path | None = None
) -> list[SectionViolation]:
    """Check the three conditions `mc-67snh` failed. Empty list == clean."""
    rules = discipline_rules(path)
    if not rules:
        return []
    # Which conditions REFUSE and which only warn is declared in the data file,
    # with the reason. Absent key -> everything blocks, so a truncated data file
    # cannot quietly turn the gate into a reporter.
    blocking = set(
        (rules.get("registry") or {}).get("blocking_conditions", ["C1", "C2", "C3"])
    )
    explicit = _explicit(sections)
    numbered = [s for s in explicit if s.section_index == 1]
    if not numbered:
        # No explicit §1 -> not a present-it full-form body. Compact-form briefs
        # have no numbered sections and this gate has nothing to say about them.
        return []

    violations: list[SectionViolation] = []

    # C1 -- §1 states the question, and carries no evidence.
    body_one = numbered[0].body or ""
    for klass in rules.get("evidence_class") or []:
        pattern = str(klass.get("pattern") or "")
        if not pattern:
            continue
        found = re.findall(pattern, body_one)
        if not found:
            continue
        shown = ", ".join(dict.fromkeys(str(f) for f in found if str(f)))[:160]
        violations.append(
            SectionViolation(
                condition="C1",
                code="MBRF037",
                summary=(
                    f"§1 carries {klass.get('description') or klass.get('id')}; "
                    "§1 states the question, and nothing else."
                ),
                detail=shown or pattern,
                remedy=str(klass.get("remedy") or "move it to §6 — Supporting evidence"),
                line=getattr(numbered[0], "start_line", None),
                blocking="C1" in blocking,
            )
        )

    # C2 -- section numbers are unique.
    by_number: dict[int, list[Any]] = {}
    for section in explicit:
        by_number.setdefault(section.section_index, []).append(section)
    for index in sorted(by_number):
        repeated = by_number[index]
        if len(repeated) < 2:
            continue
        violations.append(
            SectionViolation(
                condition="C2",
                code="MBRF038",
                summary=f"§{index} appears {len(repeated)} times; section numbers are unique.",
                detail=" | ".join(str(s.heading) for s in repeated),
                remedy=(
                    f"renumber or merge the repeated §{index} headings so each number "
                    "appears once"
                ),
                line=getattr(repeated[1], "start_line", None),
                blocking="C2" in blocking,
            )
        )

    # C3 -- §2 is a recommendation, not a restatement.
    two = rules.get("section_two") or {}
    seconds = [s for s in explicit if s.section_index == 2]
    if not seconds:
        violations.append(
            SectionViolation(
                condition="C3",
                code="MBRF039",
                summary="No §2 — Recommended answer. A brief without one hands the work back.",
                detail="the body carries an explicit §1 but no explicit §2",
                remedy="add '## §2 — Recommended answer' naming the action you recommend",
                line=None,
                blocking="C3" in blocking,
            )
        )
    else:
        text = (seconds[0].body or "").strip()
        null_pattern = str(two.get("null_answer_pattern") or "")
        verbs = [str(v) for v in (two.get("verbs") or []) if str(v)]
        verb_pattern = (
            r"\b(?:%s)(?:s|es|ed|ing|d)?\b" % "|".join(re.escape(v) for v in verbs)
            if verbs
            else ""
        )
        if not text:
            problem = ("§2 is empty.", "no text under the heading")
        elif null_pattern and re.match(null_pattern, text, re.IGNORECASE):
            problem = ("§2 opens with a null answer.", text.splitlines()[0][:160])
        elif verb_pattern and not re.search(verb_pattern, text, re.IGNORECASE):
            problem = (
                "§2 names no decision verb, so it restates the question rather than "
                "answering it.",
                text.splitlines()[0][:160],
            )
        else:
            problem = None
        if problem is not None:
            violations.append(
                SectionViolation(
                    condition="C3",
                    code="MBRF039",
                    summary=problem[0],
                    detail=problem[1],
                    remedy=(
                        "write the recommended action in §2 — one sentence naming what "
                        "to do (adopt / ship / defer / reject / …)"
                    ),
                    line=getattr(seconds[0], "start_line", None),
                    blocking="C3" in blocking,
                )
            )

    return violations
