"""The dashboard's URL vocabulary, in one module.

Navigation and data state -- which screen, which scope, which sort, which
columns, which rig, which brief -- live in the query string rather than in
client-side state. That is what lets a sortable heading be an ordinary
`<a href>` and a column toggle be a GET form, so every screen keeps working
with JavaScript disabled.

Every parser here is total. A hand-edited, truncated or hostile query string
falls back to the default rather than raising, because a 500 reachable from
the address bar would make the URL bar a denial-of-service surface on a tool
whose whole job is to be readable under failure.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping
from urllib.parse import quote, urlencode

VIEWS = ("queue", "brief", "pile", "deferred", "adjudicated", "priority")
SCOPES = ("stack", "errors", "nobrainer")

#: key, label, width px, numeric, on-by-default.
#:
#: Twelve columns, nine on by default.
#:
#: The prototype defines thirteen. `Producer` -- which formula filed the brief
#: -- is not among them here: `provenance.py` is wired to work_provenance,
#: which is dispatch provenance, and nothing records brief production. There
#: is no source to render, and a column that can only ever be an em dash is
#: worse than an absent one, so it is dropped until a producer writes one.
COLUMNS: tuple[tuple[str, str, int, bool, bool], ...] = (
    ("slug", "Brief", 300, False, True),
    ("rig", "Rig", 86, False, True),
    ("artifact", "Artifact", 124, False, False),
    ("unlock", "Unlock", 78, True, True),
    ("score", "Score", 74, True, True),
    ("age", "Age", 64, True, True),
    ("prio", "Priority", 82, False, True),
    ("kind", "Type", 96, False, False),
    ("nopts", "Opts", 62, True, True),
    ("sev", "Health", 78, False, True),
    ("source", "Source", 82, False, False),
    ("rec", "Rec.", 88, False, True),
)

COLUMN_KEYS: tuple[str, ...] = tuple(key for key, _, _, _, _ in COLUMNS)
NUMERIC_KEYS = frozenset(key for key, _, _, num, _ in COLUMNS if num)
DEFAULT_COLUMNS: tuple[str, ...] = tuple(key for key, _, _, _, on in COLUMNS if on)
COLUMN_WIDTH: dict[str, int] = {key: width for key, _, width, _, _ in COLUMNS}
COLUMN_LABEL: dict[str, str] = {key: label for key, label, _, _, _ in COLUMNS}

#: The leading tick+row-number cell and the trailing add-to-queue cell have
#: fixed widths; the title column declares none and absorbs the remainder, so
#: it needs a floor of its own or it collapses.
#: The column the stack opens on.
#:
#: Not `score`, which is what the design shows: score folds unlock_count
#: and priority, and the core exposes neither, so it is empty on every real
#: brief. A default sort over an all-empty column is worse than no sort --
#: it looks like it worked. Age is derived from created_at, which is always
#: present, so it orders something real until issue #66 lands.
DEFAULT_SORT_KEY = "age"

LEADING_WIDTH = 46
TRAILING_WIDTH = 104
TITLE_FLOOR = 290

_PATHS = {
    "queue": "/queue",
    "pile": "/pile",
    "deferred": "/deferred",
    "adjudicated": "/adjudicated",
    "priority": "/priority",
}


def _one(value: object, allowed: tuple[str, ...], fallback: str) -> str:
    text = str(value or "").strip()
    return text if text in allowed else fallback


def _flag(value: object) -> bool:
    return str(value or "").strip().lower() in {"1", "true", "on", "yes"}


@dataclass(frozen=True)
class ViewState:
    view: str = "queue"
    scope: str = "stack"
    rig: str | None = None
    all_rigs: bool = False
    sort_key: str = DEFAULT_SORT_KEY
    sort_dir: int = -1
    columns: tuple[str, ...] = DEFAULT_COLUMNS
    brief_id: str | None = None
    cursor: int = 0

    # -- serialisation -----------------------------------------------------

    def _params(self) -> dict[str, str]:
        """Only what differs from the default, so URLs stay readable."""
        out: dict[str, str] = {}
        if self.scope != "stack":
            out["scope"] = self.scope
        if self.rig:
            out["rig"] = self.rig
        if self.all_rigs:
            out["all_rigs"] = "1"
        if self.sort_key != DEFAULT_SORT_KEY:
            out["sort_key"] = self.sort_key
        out["sort_dir"] = str(self.sort_dir)
        if tuple(self.columns) != DEFAULT_COLUMNS:
            out["columns"] = ",".join(self.columns)
        if self.cursor:
            out["cursor"] = str(self.cursor)
        return out

    def url(self, **overrides: Any) -> str:
        merged = replace(self, **overrides) if overrides else self
        if merged.view == "brief" and merged.brief_id:
            path = f"/briefs/{quote(str(merged.brief_id), safe='')}"
        else:
            path = _PATHS.get(merged.view, "/queue")
        query = urlencode(merged._params())
        return f"{path}?{query}" if query else path

    # -- sorting -----------------------------------------------------------

    def sort_link(self, key: str) -> str:
        """Where a click on this heading goes.

        Clicking the current column flips direction. Clicking a new column
        starts descending when it is numeric: the question `Unlock` exists to
        answer is "which brief unblocks the most", so opening it at the
        smallest value would be the wrong first screen.
        """
        if key == self.sort_key:
            direction = -self.sort_dir
        else:
            direction = -1 if key in NUMERIC_KEYS else 1
        return self.url(sort_key=key, sort_dir=direction)

    def sort_marker(self, key: str) -> str:
        if key != self.sort_key:
            return ""
        return " ▾" if self.sort_dir < 0 else " ▴"

    # -- columns -----------------------------------------------------------

    def toggle_column(self, key: str) -> tuple[str, ...]:
        """Toggle one column, restoring canonical order when re-added.

        Without the re-sort, a column removed and re-added would land at the
        end, so the table's column order would slowly become a history of what
        the operator happened to click.
        """
        if key in self.columns:
            return tuple(existing for existing in self.columns if existing != key)
        wanted = set(self.columns) | {key}
        return tuple(candidate for candidate in COLUMN_KEYS if candidate in wanted)

    @property
    def visible_columns(self) -> tuple[tuple[str, str, int, bool], ...]:
        """(key, label, width, numeric) for the visible columns, in order."""
        return tuple(
            (key, COLUMN_LABEL[key], COLUMN_WIDTH[key], key in NUMERIC_KEYS)
            for key in COLUMN_KEYS
            if key in self.columns
        )

    @property
    def table_min_width(self) -> int:
        """Derived from what is visible, never fixed.

        A static min-width starves the title column as columns are toggled on:
        the title has no declared width, so the space it gets is whatever the
        other columns leave, and the floor has to move with them.
        """
        body = sum(COLUMN_WIDTH[key] for key in self.columns if key != "slug")
        return LEADING_WIDTH + TRAILING_WIDTH + TITLE_FLOOR + body


def parse(query: Mapping[str, str]) -> ViewState:
    """Build a ViewState from a query mapping, tolerating anything."""
    raw_columns = str(query.get("columns") or "").strip()
    if raw_columns:
        wanted = {part for part in raw_columns.split(",") if part in COLUMN_KEYS}
        columns = tuple(key for key in COLUMN_KEYS if key in wanted) or DEFAULT_COLUMNS
    else:
        columns = DEFAULT_COLUMNS

    try:
        cursor = max(0, int(str(query.get("cursor") or "0")))
    except (TypeError, ValueError):
        cursor = 0

    sort_dir = 1 if str(query.get("sort_dir") or "-1").strip() == "1" else -1

    rig = str(query.get("rig") or "").strip() or None
    brief_id = str(query.get("brief_id") or "").strip() or None

    return ViewState(
        view=_one(query.get("view"), VIEWS, "queue"),
        scope=_one(query.get("scope"), SCOPES, "stack"),
        rig=rig,
        all_rigs=_flag(query.get("all_rigs")),
        sort_key=_one(query.get("sort_key"), COLUMN_KEYS, DEFAULT_SORT_KEY),
        sort_dir=sort_dir,
        columns=columns,
        brief_id=brief_id,
        cursor=cursor,
    )
