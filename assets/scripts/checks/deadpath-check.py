#!/usr/bin/env python3
"""Detect agent-facing instructions that name a path no mechanism produces.

The error class (tdupu/mathcity#71): *an agent-facing instruction naming a
filesystem path that no mechanism produces.* It is silent by construction --
an agent told to run `X` that finds no `X` improvises, skips, or reports
something adjacent. There is no exception to catch, so it had to be found by
accident four separate times before this check existed.

Why the rules are citations rather than taste: each allowlist below is derived
from gascity source, named by file and line, so a future reader can re-derive
it instead of trusting it. Line numbers drift; the function and constant names
are the durable part of each citation.

Rules
-----
R1  blocking   `.gc/scripts/<x>` -- allowlist is `gc-beads-bd.sh`, nothing else.
R2  blocking   `$PACK_DIR/` in formula/skill/agent text -- never substituted.
R3  blocking   `<mathcity-pack-root>/X` -- X must ship in this pack.
R4  blocking   `path = "../assets/X"` in a check declaration -- X must ship.
R5  advisory   bare `assets/...` in a runnable position -- resolves only from
               the pack root, and production cwd is never the pack root.

R1/R2/R4 are blocking because each is provably dead: the allowlists come from
gascity source, not convention. R3 is blocking on the same footing as R4 --
both reduce to "does this file ship in the pack", which is decidable here. R5
is advisory until its scoping is proven, because its unscoped form produced 57
hits of which ~55 were prose.

Exemptions
----------
`<!-- deadpath-ok: <reason> -->` (markdown) or `# deadpath-ok: <reason>`
(TOML/shell), on the flagged line or the line directly above it. The reason is
mandatory -- a marker without one is itself an error. Every exemption is
printed in the summary, so they stay visible instead of accumulating silently.

This exists because R1 legitimately flags a sentence that names
`.gc/scripts/checks/` *in order to say it does not exist*. A blocking linter
with no exemption pushes authors to delete exactly the sentences that document
the hazard.

Usage
-----
    deadpath-check.py [--root PACK_ROOT] [--json] [--strict-advisory]

Exit 0 when no blocking hit is found, 1 otherwise. `--strict-advisory`
promotes advisory rules to blocking, for use on a known-bad corpus.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

BLOCKING = "blocking"
ADVISORY = "advisory"

# --- scan scopes ------------------------------------------------------------
# Each rule declares which slice of a file it reads. Keeping this a named scope
# rather than an inline condition is what lets the rule table below move to
# another pack unchanged.
SCOPE_TEXT = "text"  # every line of the file
SCOPE_RUNNABLE = "runnable"  # fenced code blocks, `exec =` values, whole .sh
SCOPE_NOT_EXEC = "not-exec"  # everywhere EXCEPT an order `exec =` value

# --- the rule table ---------------------------------------------------------
# Data-driven on purpose (#71 decision 3): the same rules apply to any pack
# whose formulas run under gascity, so nothing here hardcodes mathcity beyond
# the roots, which are a parameter.

RULES = (
    {
        "id": "R1",
        "severity": BLOCKING,
        "scope": SCOPE_TEXT,
        "summary": "path under .gc/scripts/ that gascity never generates",
        "citation": (
            "gascity cmd/gc/embed_builtin_packs.go ensureGcBeadsBdShim() is the only "
            "writer under <city>/.gc/scripts/, and it writes exactly gc-beads-bd.sh "
            "(path built by gcBeadsBdScriptPath() in cmd/gc/providers.go). "
            "cmd/gc/template_resolve.go only COPIES that directory into agent work "
            "dirs -- copying is why hand-placed files look installed."
        ),
        "pattern": re.compile(r"\.gc/scripts/(?P<ref>[A-Za-z0-9._/-]*)"),
        "allow": ("gc-beads-bd.sh",),
        "detail": "gascity generates only .gc/scripts/gc-beads-bd.sh",
    },
    {
        "id": "R2",
        "severity": BLOCKING,
        # Order `exec =` values are the ONE surface where PACK_DIR is real -- the
        # same citation that makes it dead everywhere else says so. Scoping the
        # rule around them is what keeps orders/*.toml legal.
        "scope": SCOPE_NOT_EXEC,
        "summary": "$PACK_DIR used as a path prefix where it is never substituted",
        "citation": (
            "gascity sets PACK_DIR/GC_PACK_DIR only in orderExecEnvWithError() "
            "(cmd/gc/order_store.go), consumed by the `sh -c` in "
            "cmd/gc/order_dispatch.go -- i.e. order `exec =` values only. Formula "
            "step text is substituted for {{name}} placeholders alone "
            "(internal/formula/parser.go varPattern/Substitute) and is never "
            "shell-expanded, so $PACK_DIR reaches the agent as literal text. "
            "gascity's own order_dispatch_test.go asserts PACK_DIR is absent "
            "without a formula layer."
        ),
        # Anchored on the trailing slash: path-expansion position only. Prose
        # that NAMES $PACK_DIR in order to forbid it (nine such sentences ship
        # today) has no slash and is correctly untouched.
        "pattern": re.compile(r"\$\{?(?:GC_)?PACK_DIR\}?/"),
        "detail": "$PACK_DIR is injected for order exec only, not for formula steps",
    },
    {
        "id": "R3",
        "severity": BLOCKING,
        "scope": SCOPE_TEXT,
        "summary": "<mathcity-pack-root>/X names a file that does not ship",
        "citation": (
            "The pack-root placeholder is resolved by the agent from `gc order show`; "
            "it is the sanctioned form, but only for paths that actually ship."
        ),
        "pattern": re.compile(r"<mathcity-pack-root>/(?P<ref>[A-Za-z0-9._/-]+)"),
        "must_exist": True,
        "detail": "no such file in this pack",
    },
    {
        "id": "R4",
        "severity": BLOCKING,
        "scope": SCOPE_TEXT,
        "summary": "check declaration points at an asset that does not ship",
        "citation": (
            "Check scripts are resolved FROM THE PACK at cook time via "
            'path = "../assets/...". Graph v2 makes a missing target a cook-time '
            "error; this catches it before cook."
        ),
        "pattern": re.compile(r'path\s*=\s*"\.\./(?P<ref>[A-Za-z0-9._/-]+)"'),
        "must_exist": True,
        "detail": "no such file in this pack",
    },
    {
        "id": "R5",
        "severity": ADVISORY,
        "scope": SCOPE_RUNNABLE,
        "summary": "bare assets/ path in a runnable position",
        "citation": (
            "A bare assets/... resolves only from the pack root. Check scripts and "
            "formula steps run with an agent work dir as cwd, which is never the "
            "pack root -- while the test suite runs from the pack root, so this "
            "class is structurally invisible to tests. Shell scripts should anchor "
            "on $0 (see pack_asset in brief-check.sh); agent-facing text should use "
            "<mathcity-pack-root>/."
        ),
        # Three anchored positions. Unanchored `assets/` matching is what produced
        # 57 hits for 2 defects, so every pattern here requires a syntactic
        # position that makes the token a path being USED, not a path being named.
        "patterns": (
            re.compile(r"\b(?:python3|python|bash|sh|source)\s+\"?assets/"),
            re.compile(r"\s--[a-z][a-z0-9-]*\s+\"?assets/"),
            re.compile(r"[A-Za-z_][A-Za-z0-9_]*=[\"']?assets/"),
        ),
        "detail": "resolves only from the pack root; production cwd is not the pack root",
    },
)

# Roots holding agent-facing content. A parameter, not a constant of the rules.
DEFAULT_ROOTS = (
    "formulas",
    "orders",
    "gates",
    "agents",
    "template-fragments",
    "skills",
    "assets/scripts/checks",
)

SCANNED_SUFFIXES = (".md", ".toml", ".sh")

EXEMPT_RE = re.compile(
    r"(?:<!--|#)\s*deadpath-ok:\s*(?P<reason>.*?)\s*(?:-->|$)"
)
FENCE_RE = re.compile(r"^\s*```")
EXEC_RE = re.compile(r"^\s*exec\s*=")


def runnable_lines(path: Path, lines: list[str]) -> set[int]:
    """1-based line numbers that an agent or a shell actually executes.

    Whole file for `.sh`. Otherwise: inside a fenced code block, or an
    `exec =` value. This is the scoping that separates R5's 2 real defects
    from its ~55 prose mentions.
    """
    if path.suffix == ".sh":
        return set(range(1, len(lines) + 1))
    inside = False
    runnable: set[int] = set()
    for number, line in enumerate(lines, start=1):
        if FENCE_RE.match(line):
            inside = not inside
            continue
        if inside or EXEC_RE.match(line):
            runnable.add(number)
    return runnable


def exemption_for(lines: list[str], number: int):
    """Return (reason, marker_line) for a hit, or None.

    Accepted on the flagged line or the line directly above it, so a marker can
    sit above a long command rather than trailing it.
    """
    for candidate in (number, number - 1):
        if 1 <= candidate <= len(lines):
            match = EXEMPT_RE.search(lines[candidate - 1])
            if match:
                return match.group("reason").strip(), candidate
    return None


def rule_patterns(rule) -> tuple:
    return rule.get("patterns") or (rule["pattern"],)


def check_file(path: Path, root: Path, rules) -> tuple[list[dict], list[dict]]:
    try:
        text = path.read_text(errors="replace")
    except OSError as exc:
        return ([{"kind": "unreadable", "path": str(path), "error": str(exc)}], [])
    lines = text.splitlines()
    runnable = runnable_lines(path, lines)

    hits: list[dict] = []
    exemptions: list[dict] = []
    for rule in rules:
        scope = rule["scope"]
        for number, line in enumerate(lines, start=1):
            if scope == SCOPE_RUNNABLE and number not in runnable:
                continue
            if scope == SCOPE_NOT_EXEC and EXEC_RE.match(line):
                continue
            # The marker text itself names the dead path (that is what it is
            # exempting), so strip it before matching. Otherwise every exemption
            # manufactures a second hit on its own marker line.
            scan_line = EXEMPT_RE.sub("", line)
            for pattern in rule_patterns(rule):
                match = pattern.search(scan_line)
                if not match:
                    continue
                groups = match.groupdict()
                ref = groups.get("ref")
                if ref is not None and ref in rule.get("allow", ()):
                    continue
                if rule.get("must_exist") and ref and (root / ref).exists():
                    continue
                record = {
                    "rule": rule["id"],
                    "severity": rule["severity"],
                    "path": str(path.relative_to(root)),
                    "line": number,
                    "text": line.strip(),
                    "match": match.group(0),
                    "detail": rule["detail"],
                }
                exempt = exemption_for(lines, number)
                if exempt is None:
                    hits.append(record)
                else:
                    reason, marker_line = exempt
                    if not reason:
                        record = dict(record)
                        record["detail"] = (
                            "deadpath-ok marker carries no reason; a reason is mandatory"
                        )
                        hits.append(record)
                    else:
                        record = dict(record)
                        record["reason"] = reason
                        record["marker_line"] = marker_line
                        exemptions.append(record)
                break
    return hits, exemptions


def collect_files(root: Path, roots) -> list[Path]:
    found: list[Path] = []
    for name in roots:
        base = root / name
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in SCANNED_SUFFIXES:
                found.append(path)
    return found


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", default=None, help="pack root (default: derived from this script)")
    parser.add_argument("--roots", nargs="*", default=None, help="content roots to scan")
    parser.add_argument("--json", action="store_true", help="emit JSON instead of a report")
    parser.add_argument(
        "--strict-advisory",
        action="store_true",
        help="treat advisory rules as blocking (for known-bad corpus runs)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parents[3]
    roots = tuple(args.roots) if args.roots else DEFAULT_ROOTS

    hits: list[dict] = []
    exemptions: list[dict] = []
    for path in collect_files(root, roots):
        file_hits, file_exemptions = check_file(path, root, RULES)
        hits.extend(file_hits)
        exemptions.extend(file_exemptions)

    blocking = [
        h
        for h in hits
        if h.get("severity") == BLOCKING or (args.strict_advisory and h.get("severity") == ADVISORY)
    ]

    if args.json:
        print(json.dumps({"hits": hits, "exemptions": exemptions, "blocking": len(blocking)}, indent=2))
        return 1 if blocking else 0

    for hit in hits:
        marker = "FAIL" if hit in blocking else "warn"
        print(f"{marker}: {hit.get('rule', '?')} {hit['path']}:{hit.get('line', '?')}: {hit['detail']}")
        print(f"      {hit.get('text', '')}")

    # Exemptions are always printed, never counted as clean. An exemption that
    # nobody sees is how a suppression list rots.
    print()
    print(f"deadpath exemptions in force: {len(exemptions)}")
    for exempt in exemptions:
        print(f"  {exempt['rule']} {exempt['path']}:{exempt['line']}: {exempt['reason']}")

    advisory = [h for h in hits if h not in blocking]
    print()
    print(
        f"deadpath summary: {len(blocking)} blocking, {len(advisory)} advisory, "
        f"{len(exemptions)} exempt"
    )
    return 1 if blocking else 0


if __name__ == "__main__":
    sys.exit(main())
