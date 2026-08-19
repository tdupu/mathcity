"""The knowl: a term in prose that expands in place to explain itself.

Borrowed from LMFDB, where a dotted-underlined term opens an inline panel
rather than navigating away. Here the terms are policy rule ids, bead ids and
diagnostic codes, wherever they appear in a brief's prose or tables.

Implemented as `<details>`/`<summary>`, not a script. That is the single
largest no-JS win in the redesign -- the pattern appears in every section of
every brief -- and it brings keyboard operation and assistive-technology
semantics for free rather than needing them re-added.

**An unresolved token stays plain text.** A knowl that expands to nothing is
worse than no knowl: it promises an explanation the dashboard does not have.
This matters concretely, because the adopted design's fixtures cite `MC-E101`,
`MC-E113`, `MC-E207` and `MC-E4xx`, and none of the four exist -- the real
registry is `assets/mctl/diagnostics.toml`, whose codes are `MBRF*`, `MWRK*`
and `MOPT*`. Rendering the design's invented codes as live knowls would carry
fiction into a tool whose job is to be believed.
"""

from __future__ import annotations

import re
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Any, Mapping

from mctl_dashboard.render import esc as _e

#: Where the real diagnostic registry lives.
DIAGNOSTICS_TOML = Path(__file__).resolve().parents[2] / "mctl" / "diagnostics.toml"

#: Rule ids (`B2.4`, `BP9.1`, `PP1.7`, `N5`), diagnostic codes (`MBRF004`,
#: `MWRK_DISPATCH_BLOCKED`, `MOPT001`) and bead ids (`he-saeno4`, `mc-4kf2`).
_TOKEN = re.compile(
    r"\b("
    r"MBRF\d{3}"
    r"|MOPT\d{3}"
    r"|MWRK_[A-Z_]+"
    r"|MCTL_[A-Z_]+"
    r"|[A-Z]{1,2}\d+\.\d+"
    r"|N\d"
    r"|[a-z]{2,3}-[0-9a-z]{4,8}"
    r")\b"
)


@lru_cache(maxsize=1)
def diagnostic_registry() -> dict[str, dict[str, str]]:
    """The 72-code diagnostic registry, read from this repo's own asset.

    Note on the seam: `client.py::ALLOWED_TOOLS` is the boundary for *domain
    behaviour*, and nothing here asks the core a question about a brief. This
    is a static reference table shipped in the same repository -- code, meaning,
    severity -- of the same character as `review.py`'s hardcoded notes. When the
    core grows a registry read (issue #66, item 5) this becomes a tool call and
    the parsing here goes away.
    """
    try:
        with DIAGNOSTICS_TOML.open("rb") as handle:
            raw = tomllib.load(handle)
    except (OSError, tomllib.TOMLDecodeError):  # pragma: no cover - defensive
        return {}
    registry: dict[str, dict[str, str]] = {}
    for code, entry in raw.items():
        if isinstance(entry, Mapping):
            registry[code] = {
                "severity": str(entry.get("severity") or ""),
                "meaning": str(entry.get("meaning") or ""),
                "policy_ref": str(entry.get("policy_ref") or ""),
                "module": str(entry.get("module") or ""),
            }
    return registry


def _panel(title: str, subtitle: str, body: str, *, extra: str = "") -> str:
    return (
        '<div class="knowl-body">'
        '<div style="display: flex; gap: 9px; align-items: baseline;">'
        f'<span style="font-family: var(--font-heading); font-size: 13px; '
        f'font-weight: 600;">{title}</span>'
        f'<span class="mono" style="margin-left: auto; font-size: 10px; '
        f'color: var(--color-neutral-600);">{subtitle}</span>'
        "</div>"
        f'<div style="margin-top: 4px;">{body}</div>'
        f"{extra}"
        "</div>"
    )


def _resolve(
    token: str,
    *,
    rules: Mapping[str, Any],
    beads: Mapping[str, Any],
    diagnostics: Mapping[str, Any],
) -> tuple[str, str] | None:
    """(css class, panel html) for a token, or None to leave it as text."""
    rule = rules.get(token)
    if rule:
        name = str(rule.get("name") or rule.get("description") or token)
        text = str(rule.get("text") or rule.get("description") or "")
        where = str(rule.get("file") or rule.get("reference") or "")
        return "", _panel(f"{_e(token)} — {_e(name)}", _e(where), _e(text))

    bead = beads.get(token)
    if bead:
        title = str(bead.get("title") or "")
        kind = str(bead.get("kind") or bead.get("decision_state") or "")
        link = ""
        href = bead.get("href")
        if href:
            link = (
                f'<a class="mono" style="font-size: 10.5px;" href="{_e(href)}">'
                "open this brief →</a>"
            )
        return "", _panel(f"{_e(token)}", _e(kind), _e(title), extra=link)

    entry = diagnostics.get(token)
    if entry:
        severity = str(entry.get("severity") or "")
        meaning = str(entry.get("meaning") or entry.get("message") or "")
        policy = str(entry.get("policy_ref") or "")
        module = str(entry.get("module") or "")
        subtitle = " · ".join(part for part in (severity, module) if part)
        extra = (
            f'<div class="mono" style="font-size: 10px; margin-top: 6px; '
            f'color: var(--color-neutral-600);">enforces {_e(policy)}</div>'
            if policy
            else ""
        )
        return "diag", _panel(_e(token), _e(subtitle), _e(meaning), extra=extra)

    return None


def tokenize(
    text: str,
    *,
    key: str,
    rules: Mapping[str, Any] | None = None,
    beads: Mapping[str, Any] | None = None,
    diagnostics: Mapping[str, Any] | None = None,
) -> str:
    """Escape `text` and turn every resolvable identifier into a knowl.

    `key` disambiguates two occurrences of the same token in one document so
    each expands independently.
    """
    rules = rules or {}
    beads = beads or {}
    diagnostics = diagnostics if diagnostics is not None else diagnostic_registry()

    out: list[str] = []
    cursor = 0
    for index, match in enumerate(_TOKEN.finditer(text)):
        token = match.group(1)
        resolved = _resolve(token, rules=rules, beads=beads, diagnostics=diagnostics)
        if resolved is None:
            continue
        css, panel = resolved
        out.append(_e(text[cursor : match.start()]))
        classes = "knowl" + (f" {css}" if css else "")
        out.append(
            f'<details class="{classes}" name="knowl-{_e(key)}-{index}">'
            f"<summary>{_e(token)}</summary>{panel}</details>"
        )
        cursor = match.end()
    out.append(_e(text[cursor:]))
    return "".join(out)
