"""Structural requirements for a brief body (#169).

One rule, one place. See `assets/brief-pipeline/required-sections.toml` for why
this is data rather than code.
"""
from __future__ import annotations

import re
import tomllib
from pathlib import Path
from typing import Any

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
