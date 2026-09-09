#!/usr/bin/env python3
"""Read operational limits from policy rather than baking them into scripts.

POLICY (owner, 2026-09-09): "no baked-in timeouts, that should be a policy. We
can give warnings or timeout options but it can't be baked in."

Four audit scripts written that day hardcoded their own subprocess deadlines --
300s in three, 120s in a fourth -- chosen by whoever wrote them and invisible to
whoever ran them. A store slower than one agent's guess fails as "unreadable" on
a machine where nothing is wrong.

Resolution order, most specific first:

    1. an explicit --timeout on the command line   (operator, this run)
    2. $MATHCITY_<KEY>                              (operator, this shell)
    3. assets/mctl/limits.toml                      (policy, this checkout)
    4. the FALLBACK below                           (last resort, and it says so)

The fallback is not a hidden default: `resolve()` returns the source alongside
the value so a caller can report which one it used, and `--timeout 0` means
UNLIMITED, for when the honest answer is "wait as long as it takes".
"""
from __future__ import annotations

import os
import tomllib
from pathlib import Path

#: Used only when limits.toml is absent or unreadable. Callers are expected to
#: SAY when they fall back to these, not to pretend they were configured.
FALLBACK = {
    "bead_store_read_seconds": 300,
    "remote_query_seconds": 120,
    "progress_notice_seconds": 30,
}

_SECTION = {
    "bead_store_read_seconds": "subprocess",
    "remote_query_seconds": "subprocess",
    "progress_notice_seconds": "warning",
}


def _limits_path() -> Path:
    return Path(__file__).resolve().parents[1] / "mctl" / "limits.toml"


def resolve(key: str, cli_value: int | None = None) -> tuple[int | None, str]:
    """Return (seconds, source). `None` seconds means NO deadline.

    `source` is one of "cli", "env", "policy", "fallback" so the caller can
    report which one it used -- a timeout that came from a fallback and one
    that came from policy are different facts about the run.
    """
    if cli_value is not None:
        return (None if cli_value == 0 else cli_value), "cli"

    env = os.environ.get("MATHCITY_" + key.upper())
    if env is not None:
        try:
            value = int(env)
            return (None if value == 0 else value), "env"
        except ValueError:
            pass  # fall through; a malformed env var must not silently win

    path = _limits_path()
    if path.is_file():
        try:
            data = tomllib.loads(path.read_text(encoding="utf-8"))
            section = data.get(_SECTION.get(key, "subprocess"), {})
            if key in section:
                value = int(section[key])
                return (None if value == 0 else value), "policy"
        except Exception:
            pass  # an unreadable policy file falls back, and the caller says so

    return FALLBACK[key], "fallback"
