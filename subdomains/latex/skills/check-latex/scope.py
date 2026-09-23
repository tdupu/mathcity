#!/usr/bin/env python3
"""Select a LaTeX section/subsection and filter a unified diff to it."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path


LEVELS = {
    "part": 0,
    "chapter": 1,
    "section": 2,
    "subsection": 3,
    "subsubsection": 4,
    "paragraph": 5,
    "subparagraph": 6,
}
HEADING_START = re.compile(
    r"^\s*\\(part|chapter|section|subsection|subsubsection|paragraph|subparagraph)"
    r"(\*)?(?:\s*\[[^]]*\])?\s*\{"
)
INCLUDE = re.compile(r"\\(?:input|include)\s*\{([^}]+)\}")
LABEL = re.compile(r"\\label\s*\{([^{}]+)\}")
HUNK = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def read_lines(path: Path):
    return path.read_text(encoding="utf-8").splitlines()


def brace_text(lines, line_index, brace_index):
    """Return the balanced brace contents and the last line used."""
    depth = 0
    chars = []
    for current in range(line_index, len(lines)):
        line = lines[current]
        start = brace_index if current == line_index else 0
        escaped = False
        for pos in range(start, len(line)):
            char = line[pos]
            if char == "\\" and not escaped:
                escaped = True
                if depth:
                    chars.append(char)
                continue
            if char == "{" and not escaped:
                depth += 1
                if depth > 1:
                    chars.append(char)
            elif char == "}" and not escaped:
                depth -= 1
                if depth == 0:
                    return "".join(chars), current
                chars.append(char)
            else:
                chars.append(char)
            escaped = False
        if current + 1 < len(lines):
            chars.append("\n")
    return "".join(chars), line_index


def heading_at(lines, line_index):
    match = HEADING_START.match(lines[line_index])
    if not match:
        return None
    brace_index = match.end() - 1
    title, last_line = brace_text(lines, line_index, brace_index)
    return {
        "command": match.group(1),
        "starred": bool(match.group(2)),
        "title": title.replace("\n", " ").strip(),
        "line": line_index,
        "last_line": last_line,
        "token": lines[line_index].strip(),
    }


def resolve_include(include_root, name):
    raw = name.strip()
    candidates = [include_root / raw]
    if not raw.endswith(".tex"):
        candidates.append(include_root / (raw + ".tex"))
    for candidate in candidates:
        if candidate.is_file():
            return candidate.resolve()
    return None


def walk(path, target, events, counters, stack, include_root=None):
    path = path.resolve()
    include_root = include_root or path.parent
    if path in stack or not path.is_file():
        return
    stack.add(path)
    lines = read_lines(path)
    for index, line in enumerate(lines):
        heading = heading_at(lines, index)
        if heading:
            level = LEVELS[heading["command"]]
            if not heading["starred"]:
                counters[level] += 1
                if level == 0:
                    # Standard parts neither prefix nor reset chapter/section
                    # numbers. Select a part by title or label, not an inferred
                    # class-dependent Roman numeral.
                    heading["number"] = ""
                else:
                    for lower in range(level + 1, len(counters)):
                        counters[lower] = 0
                    nonzero = [value for value in counters[1 : level + 1] if value]
                    heading["number"] = ".".join(str(value) for value in nonzero)
            else:
                heading["number"] = ""
            heading["level"] = level
            heading["path"] = str(path)
            if path == target:
                events.append(heading)

        for include in INCLUDE.finditer(line):
            included = resolve_include(include_root, include.group(1))
            if included:
                walk(included, target, events, counters, stack, include_root)
    stack.remove(path)


def local_events(target):
    events = []
    walk(target, target, events, [0] * len(LEVELS), set())
    return events


def labels_for_event(events, lines, event_index):
    event = events[event_index]
    start = event["line"]
    stop = events[event_index + 1]["line"] if event_index + 1 < len(events) else len(lines)
    labels = []
    saw_label = False
    heading_end = event.get("last_line", start)
    for index in range(heading_end, min(stop, heading_end + 8)):
        line = lines[index]
        stripped = line.strip()
        if index == heading_end:
            found = LABEL.findall(line)
            if found:
                labels.extend(found)
                saw_label = True
            continue
        if not stripped:
            if saw_label:
                break
            continue
        found = LABEL.findall(line)
        if found:
            labels.extend(found)
            saw_label = True
            continue
        break
    return labels


def select_event(events, lines, selector):
    numeric = re.fullmatch(r"\d+(?:\.\d+)*", selector)
    label_selector = selector[6:] if selector.startswith("label:") else None
    text_selector = selector[5:] if selector.startswith("text:") else None
    matches = []
    for index, event in enumerate(events):
        labels = labels_for_event(events, lines, index)
        event["labels"] = labels
        if numeric and event["number"] == selector:
            matches.append(event)
        elif label_selector is not None and label_selector in labels:
            matches.append(event)
        elif text_selector is not None and event["title"].casefold() == text_selector.casefold():
            matches.append(event)
        elif label_selector is None and text_selector is None and (
            selector in labels or event["title"].casefold() == selector.casefold()
        ):
            matches.append(event)
    if len(matches) != 1:
        if not matches:
            raise ValueError(
                "scope selector %r did not match a numbered heading, label, or title" % selector
            )
        rendered = ", ".join(
            "%s %s" % (event["number"] or "(unnumbered)", event["title"])
            for event in matches
        )
        raise ValueError("scope selector %r matched multiple headings: %s" % (selector, rendered))
    return matches[0]


def changed_lines(diff_text, start_line, end_line, old_range=None):
    """Return added/removed diff lines whose source line is in the scope."""
    if not diff_text:
        return []
    old_line = new_line = 0
    selected = []
    for line in diff_text.splitlines():
        hunk = HUNK.match(line)
        if hunk:
            old_line = int(hunk.group(1))
            new_line = int(hunk.group(3))
            continue
        if not old_line and not new_line:
            continue
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            if start_line <= new_line <= end_line:
                selected.append(line)
            new_line += 1
        elif line.startswith("-"):
            if old_range and old_range[0] <= old_line <= old_range[1]:
                selected.append(line)
            old_line += 1
        elif line.startswith(" "):
            old_line += 1
            new_line += 1
    return selected


if __name__ == "__main__":
    # Keep argument handling explicit so paths containing spaces remain intact.
    if len(sys.argv) != 9:
        print(
            "usage: scope.py <target.tex> <root.tex> <selector> <diff> <meta> <scope> <scope-diff> <old-target.tex>",
            file=sys.stderr,
        )
        raise SystemExit(2)
    target = Path(sys.argv[1]).resolve()
    root = Path(sys.argv[2]).resolve()
    selector = sys.argv[3].strip()
    diff_path = Path(sys.argv[4])
    meta_path = Path(sys.argv[5])
    scope_path = Path(sys.argv[6])
    diff_scope_path = Path(sys.argv[7])
    old_target = Path(sys.argv[8])
    events = []
    walk(root, target, events, [0] * len(LEVELS), set())
    if not events:
        events = local_events(target)
    lines = read_lines(target)
    if not events:
        raise SystemExit("check-latex: no section headings found in %s" % target)
    event = select_event(events, lines, selector)
    event_index = events.index(event)
    end_line = len(lines) - 1
    for following in events[event_index + 1 :]:
        if following["level"] <= event["level"]:
            end_line = following["line"] - 1
            break
    start_line = event["line"]
    scope_lines = lines[start_line : end_line + 1]
    diff_text = diff_path.read_text(encoding="utf-8")
    old_lines = read_lines(old_target)
    old_events = []
    for index in range(len(old_lines)):
        heading = heading_at(old_lines, index)
        if heading:
            heading['level'] = LEVELS[heading['command']]
            old_events.append(heading)
    for index, heading in enumerate(old_events):
        heading['labels'] = labels_for_event(old_events, old_lines, index)
    matches = [h for h in old_events if set(h['labels']) & set(event['labels'])]
    if not matches:
        matches = [h for h in old_events if h['command'] == event['command']
                   and h['title'].casefold() == event['title'].casefold()]
    old_range = None
    if len(matches) == 1:
        old_event = matches[0]
        old_end = len(old_lines)
        for following in old_events[old_events.index(old_event) + 1:]:
            if following['level'] <= old_event['level']:
                old_end = following['line']
                break
        old_range = (old_event['line'] + 1, old_end)
    elif old_lines and diff_text:
        raise SystemExit('check-latex: cannot pair this scope with a unique baseline '
                         'heading; run without --section to review the full diff')
    diff_scope = changed_lines(diff_text, start_line + 1, end_line + 1, old_range)
    meta = {
        "selector": selector,
        "matched": True,
        "number": event["number"],
        "heading": event["title"],
        "command": event["command"],
        "level": event["level"],
        "labels": event["labels"],
        "target_file": str(target),
        "root_file": str(root),
        "start_line": start_line + 1,
        "end_line": end_line + 1,
        "baseline_range": old_range,
        "changed_lines_in_scope": len(diff_scope),
    }
    meta_path.write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    scope_path.write_text(
        "".join("+%s\n" % line for line in scope_lines), encoding="utf-8"
    )
    diff_scope_path.write_text(
        "+%s\n%s\n" % (event["token"], "\n".join(diff_scope)) if diff_scope else "",
        encoding="utf-8",
    )
