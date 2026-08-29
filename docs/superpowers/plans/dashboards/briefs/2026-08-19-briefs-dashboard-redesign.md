# Briefs Dashboard Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the mctl operator dashboard to the adopted Claude Design briefs-dashboard, delivered as vertical slices — each slice is one screen working end-to-end against real `mctl` data, not a layer.

**Architecture:** `render.py` and the `screens/` modules are pure functions returning HTML strings built with f-strings and `_e()`; `app.py` dispatches routes over `client.py`'s 16-tool allowlist. Navigation and data state live in the query string, so every screen, sort, filter and verdict works with JavaScript disabled; inline vanilla JS is layered on for four affordances that cannot be a link or a form. No build step, no npm, no external bundle.

**Tech Stack:** Python 3.11+ stdlib only (`http.server`, `html.escape`, `urllib.parse`, `json`). HTML5 + CSS custom properties. `<details>`/`<summary>` for disclosure. pytest.

**Spec:** `docs/superpowers/plans/dashboards/briefs/design_handoff_brief_manager/` — `Brief Manager Dashboard.dc.html`, `README.md`, `CHANGELOG.md` (the canonical "Brief Manager" design). Read all three. Where the HTML and README disagree, **the HTML is authoritative** (§GC9). NOTE: this plan first targeted the older `claude-design-briefs-dashboard-2026-08-19/` design, which was retired and removed 2026-08-24; reconcile any slice detail against the Brief Manager HTML before building.

**Spec is frozen.** Taylor finished iterating 2026-08-19. `CHANGELOG.md` §G is the designer's own prioritised list of backend work and is the authoritative ordering for issue #66.

**Branch:** `feat/dashboard-redesign`, worktree `.claude/worktrees/dashboard-redesign`, off local `main`.

---

## Why vertical slices

An earlier draft of this plan was layered — tokens, then state, then shell, then table, then detail. That ordering produces nothing usable until the last task lands, and it defers every integration risk to the end. The risk here is *integration*, not rendering: whether `briefs_list` gives the columns the table needs, whether `sections` maps cleanly onto §1–§7, whether the panel's POST survives the staleness guard.

So each slice below is **one screen, end-to-end, against the live city**. Slice 1 ships a working stack table reading real briefs. Slice 2 ships a working brief detail. Slice 3 ships a real verdict written to a real bead. Shared infrastructure is built *inside the first slice that needs it* and extended by later ones — the theme exists because Slice 1 needs colours, not as a prerequisite in its own right.

Every slice ends with the dashboard running and that screen usable. If work stops after any slice, what shipped works.

| Slice | Ships | Depends on backend? |
| --- | --- | --- |
| 1 | Stack table with real briefs, sortable, columns toggleable | No — `briefs_list` is enough |
| 2 | Brief detail §1–§7 with knowls | No — `36f55c3` shipped `body` + `sections` |
| 3 | Adjudication: verdict → DRY RUN plan → written bead | No — reuses `/preview` + `/apply` |
| 4 | Diagnostics and trust chrome on the new shell | No |
| 5 | Pile, Deferred, Adjudicated | **Partly** — renders the gap where data is absent |
| 6 | Priority list, ranking, drafts | No — client-side |

---

## Global Constraints

Every slice's requirements implicitly include this section.

- **GC1 — stdlib only.** No `pip install`, no npm, no build step, no external CSS/JS/font URL, no CDN.
- **GC2 — loopback only.** `--host` default `127.0.0.1`. Never bind all interfaces.
- **GC3 — no JS required for navigation or data.** Every screen reachable, sortable, filterable and adjudicable with JavaScript disabled. JS may enhance, never gate.
- **GC4 — the four honesty properties.**
  1. `MBRF021` / `MBRF004` / `MBRF005` render **with codes visible**, in a separate "under review" region, **excluded from actionable counts**, with **no repair affordance anywhere**.
  2. The malformed count carries its caveat **inline, adjacent to the number** — never behind a tooltip or a disclosure.
  3. `artifact_trust` renders **both ways**, per rig.
  4. A degraded rig is **a named row with its reason**, never a silently smaller total.
- **GC5 — the seam.** `client.py::ALLOWED_TOOLS` is the boundary. This plan adds **no** tools. `test_dashboard_views.py:332` asserts `len(ALLOWED_TOOLS) == 16`; if that changes, `client.py:40` and the assertion change in the same commit.
- **GC6 — no shell-shaped escape hatch.** `test_dashboard_views.py:360` scans for `os.system`, `shell=True`, `os.popen`, `subprocess.call(`, and `eval(` as a bare substring. Only `client.py` may contain `Popen`.
- **GC7 — banned strings** (`test_dashboard_views.py:285`): `action="/repair"`, `>Repair<`, `>Fix<`, `Fix these`, `auto-repair`. Never use "Repair"/"Fix" as a capitalised button label. The error-brief verdict chip stays lowercase `repair`.
- **GC8 — machine-readable hooks are load-bearing.** Preserve `data-region`, `data-actionable-count`, `data-under-review-count`, `data-artifact-trust`, `data-rig`, `data-degraded`, `data-severity`, `data-code`, `data-under-review`, `<code class="diagnostic-code">`. **Document order is asserted**: actionable region before under-review region.
- **GC9 — spec conflicts: the HTML wins.** README says 12 columns / 8 default; the prototype has **13 / 9**. Use 13/9. README says headings need ~14px padding so the sort arrow does not clip; the prototype emits `6px 5px`, which *does* clip under `nowrap; overflow:hidden` — here the README states the intent and the HTML has the bug, so use `6px 12px`.
- **GC10 — a written constraint is being made precise.** `render.py`'s docstring and `README-development.md:527` claim the dashboard "works with JavaScript off". After this plan that stays true for navigation, sorting, filtering and verdicts, and is false for the j/k cursor, drag-reorder, live sliders and drafts. Slice 1 updates both to say exactly that.
- **GC11 — commit messages.** `subdomains/dev/POLICY.md` **P5.5** forbids `Co-Authored-By: Claude`. Use `[autogenerated by Claude <model> v<version> on <date>]`.
- **GC12 — schema snapshots.** If any MCP schema changes (none should), regenerate with `MCTL_UPDATE_MCP_SNAPSHOT=1 python3 -m pytest tests/mctl/test_mcp_schema_snapshots.py`.
- **GC13 — mutations stay dry-run-first.** `MUTATION_ROUTES` stays exactly `("/preview", "/apply")`, with the existing single-use token and three-fingerprint staleness guard.
- **GC14 — do NOT carry over the `FIXTURES · NOT LIVE DATA` badge.** Correct in the prototype, false on a dashboard reading the live city. The one design element deliberately not implemented.
- **GC15 — health colours are never used for verdicts.** A closed decision has no pipeline health (`CHANGELOG.md` §F29).
- **GC16 — reads may span rigs; mutations are always single-rig.** The rig picker is multi-select defaulting to all rigs; every write pins one rig at preview time and `preview.arguments` carries the pin to `/apply` (already enforced, `app.py:900-904`).

### Test command

```bash
cd <repos-root>/mathcity/.claude/worktrees/dashboard-redesign
python3 -m pytest tests/mctl -q
```

### Run it

```bash
bin/mctl dashboard serve --city ~/gt --rig mathcity
```

`http://127.0.0.1:8471`. Omit `--rig` for city-wide.

---

## The palette, and where it comes from

The design's stylesheet (`_ds/classical-…/styles.css`) never shipped, so 13 of its 21 colour variables have no stated value. Taylor's direction: **bottom out on LMFDB**, whose conventions the design already borrows.

LMFDB's palette is not in `lmfdb/templates/style.css` — that file is a Jinja template full of `{{color.*}}` references. The real source is `lmfdb/utils/color.py`, which defines a **semantic ramp** per scheme:

| LMFDB slot | Role |
| --- | --- |
| `col_main_d` | header and footer ground |
| `col_main_dl` | header and footer text |
| `col_main` | links, body text |
| `col_main_2` | link hover |
| `col_main_l` | tabs |
| `col_main_lg` | shadow, bottom border |
| `col_main_ld` | box background |
| `col_main_ll` | lightest fill |

That is the same shape as the design's 100–900 ramp, which is why the two compose. The warm schemes are the family the Classical palette descends from — `Tans.col_main_l = #cca661` sits beside the design's accent `#b68235`, and `Tans.col_main_ll = #ffd893` beside `--color-accent-100 #fff3e4`; `RuddyBrowns` supplies the dark end (`#33261d`, `#443227`, `#83614c`).

**Rule for the implementer:** where the design states a value, the design wins — those are the anchors Taylor approved by looking at the page. Where it does not, take the LMFDB value from the corresponding slot, hue-corrected into the design's gold. Every entry in `theme.TOKENS` carries a comment saying which of the two it came from, so the provenance survives.

**Fonts.** LMFDB uses generic `sans-serif`/`monospace`; the design specifies Cormorant Garamond and Lora. These do not conflict, because what the design borrows from LMFDB is *conventions* — the sidebar, the `.ntdata` table, the knowl, the properties box — not the typeface. Cormorant Garamond and Lora are both OFL-licensed; Slice 1 vendors the `.woff2` files under `assets/mctl/fonts/` and serves them from the loopback server with a Georgia fallback, so the page is correct before the fonts load and correct if they fail.

**LMFDB table metrics to adopt** (`lmfdb/templates/style.css`): `table.ntdata td { white-space: nowrap; padding: 3px 7px; }`, `.properties-body table th, td { padding: 2px 10px; }` with `7px` top/bottom on first/last rows. These are what make an LMFDB table feel like one; the design's own densities are consistent with them.

---

## Slice 0: Confirm the baseline is green

- [ ] **Step 1: Run the suite untouched**

```bash
cd <repos-root>/mathcity/.claude/worktrees/dashboard-redesign
python3 -m pytest tests/mctl -q 2>&1 | tail -5
```

Expected: all pass. If anything fails, **stop and report** — a redesign starting from a red suite cannot distinguish its own breakage from inherited breakage.

- [ ] **Step 2: Record the count** in Slice 1's commit message.

---

## Slice 1 — The stack table, working end-to-end

**Ships:** `bin/mctl dashboard serve` renders the real brief stack in the new design: 13 columns, 9 default, sortable by clicking a heading, columns toggleable, stoplight rows, the Key legend. Reads live `briefs_list`. Works with JavaScript off.

**Files:**
- Create: `assets/scripts/mctl_dashboard/theme.py`, `state.py`, `assets.py`, `screens/__init__.py`, `screens/stack.py`
- Create: `assets/mctl/fonts/` (two `.woff2` files)
- Modify: `render.py` (`page()`, `NAV`, `STYLESHEET` → import; docstring per GC10), `app.py` (`/queue` route), `server.py` (font route), `README-development.md:527`
- Test: `tests/mctl/test_dashboard_redesign.py`

**Interfaces produced** (later slices consume these):
- `theme.TOKENS: dict[str, str]`, `theme.STYLESHEET: str`, `theme.STOP: dict[str, dict[str, str]]`
- `state.ViewState` (frozen) with `view, scope, rig, all_rigs, sort_key, sort_dir, columns, brief_id, cursor`; `state.parse(query)`; `ViewState.url(**overrides)`, `.sort_link(key)`, `.sort_marker(key)`, `.toggle_column(key)`, `.table_min_width`
- `render.page(title, view, sections, *, counts, context, context_bar="")`, `render.sidebar(view, counts)`, `render.masthead(counts, context)`
- `stack.table(briefs, view, *, queued)`, `stack.row_background(brief, *, index, cursor)`, `stack.key_legend()`, `stack.column_picker(view)`

- [ ] **Step 1: Write the failing tests**

```python
# tests/mctl/test_dashboard_redesign.py
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "assets" / "scripts"))


def test_every_token_the_design_uses_has_a_value():
    """The prototype references 21 colour variables; all must resolve.

    An undefined custom property fails silently -- the browser drops the
    declaration and the element inherits, so the page looks *nearly* right.
    This test is the thing that notices.
    """
    from mctl_dashboard import theme

    required = {
        "--color-bg", "--color-surface", "--color-text", "--color-divider",
        "--color-accent",
        *(f"--color-accent-{n}" for n in range(100, 1000, 100)),
        *(f"--color-neutral-{n}" for n in range(100, 1000, 100)),
        "--font-heading", "--font-body", "--font-mono",
        "--radius-sm", "--radius-md", "--radius-lg",
    }
    assert required <= set(theme.TOKENS), f"missing: {sorted(required - set(theme.TOKENS))}"


def test_the_stylesheet_declares_every_token_it_uses():
    from mctl_dashboard import theme

    declared = set(re.findall(r"(--[a-z0-9-]+):", theme.STYLESHEET))
    used = set(re.findall(r"var\((--[a-z0-9-]+)", theme.STYLESHEET))
    assert used <= declared, f"undeclared: {sorted(used - declared)}"


def test_fonts_are_self_hosted_not_fetched():
    """GC1/GC2. A CDN font URL would make a loopback tool phone home."""
    from mctl_dashboard import theme

    assert "https://" not in theme.STYLESHEET
    assert "fonts.googleapis" not in theme.STYLESHEET


def test_the_table_min_width_grows_with_visible_columns():
    """A static min-width starves the title column as columns are toggled on."""
    from mctl_dashboard import state

    lean = state.ViewState(columns=("slug", "rig"))
    fat = state.ViewState(columns=state.COLUMN_KEYS)
    assert fat.table_min_width > lean.table_min_width
    assert lean.table_min_width == 46 + 104 + 290 + 86


def test_a_new_numeric_column_starts_descending():
    """Clicking Unlock should answer 'which unlocks most', not 'least'."""
    from mctl_dashboard import state

    view = state.ViewState(sort_key="score", sort_dir=-1)
    assert "sort_dir=-1" in view.sort_link("unlock")
    assert "sort_dir=1" in view.sort_link("rig")


def test_unknown_query_values_fall_back_rather_than_raising():
    """A hand-edited URL must not 500 the dashboard."""
    from mctl_dashboard import state

    view = state.parse({"view": "../etc/passwd", "sort_dir": "banana", "cursor": "-3"})
    assert view.view == "queue"
    assert view.sort_dir in (-1, 1)
    assert view.cursor == 0


def test_health_outranks_the_cursor_in_row_colour():
    """An error row must not be recoloured by the cursor sitting on it."""
    from mctl_dashboard.screens import stack

    assert stack.row_background({"kind": "error", "sev": "error"}, index=3, cursor=3) == "#fbeceb"


def test_sorting_and_column_toggles_need_no_javascript():
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    html = stack.table([], state.ViewState(), queued=())
    assert '<a href="/queue?' in html
    for banned in ("onclick", "onchange", "javascript:"):
        assert banned not in html.lower()


def test_the_header_counts_link_to_the_screens_they_describe():
    """A chip must never disagree with its destination."""
    from mctl_dashboard import render

    html = render.page(
        "Brief stack", "queue", ["<p>x</p>"],
        counts={"pile": 6, "stack": 14, "deferred": 3, "errors": 2},
        context={"city_root": "~/gt", "rig_id": "mathcity"},
    )
    assert 'href="/pile"' in html and 'href="/deferred"' in html
```

- [ ] **Step 2: Run to verify they fail**

```bash
python3 -m pytest tests/mctl/test_dashboard_redesign.py -q
```

Expected: `ModuleNotFoundError: No module named 'mctl_dashboard.theme'`.

- [ ] **Step 3: Vendor the fonts**

Download the two OFL families and place **only** the woff2 subsets used:

```bash
mkdir -p assets/mctl/fonts
# CormorantGaramond-SemiBold.woff2  (600 -- the design's ceiling for UI)
# Lora-Regular.woff2, Lora-Italic.woff2
```

Add an `assets/mctl/fonts/LICENSE-OFL.txt` for both. Serve them from `server.py` by adding a `/fonts/<name>.woff2` branch that reads from that directory, guards the filename against traversal (`name` must match `^[A-Za-z0-9-]+\.woff2$`), and returns `font/woff2` with `Cache-Control: max-age=31536000, immutable`.

- [ ] **Step 4: Write `theme.py`**

Every entry carries its provenance. Design anchors are quoted; the rest are taken from LMFDB's `Tans` / `RuddyBrowns` slots, hue-corrected into the design's gold.

```python
"""Design tokens for the briefs dashboard, in one place.

Every colour, font and radius comes from here; nothing else in
`mctl_dashboard` contains a hex literal, because a colour that appears in two
files is a colour that will disagree with itself after the first revision.

Provenance, per token, in the comments below:

  [design]  quoted from the adopted design's README -- these are the values
            Taylor approved by looking at the rendered page, and they win.
  [lmfdb]   taken from `lmfdb/utils/color.py`'s semantic ramp (the warm
            `Tans` / `RuddyBrowns` schemes, whose family the Classical
            palette descends from), hue-corrected into the design's gold.
            Used only where the design states no value -- its stylesheet
            (`_ds/classical-.../styles.css`) did not ship with the handoff.

If that stylesheet ever arrives, replace TOKENS wholesale; nothing else
changes.
"""

from __future__ import annotations

_DIVIDER = "rgba(32, 31, 29, 0.16)"  # [design] ink at 16%

TOKENS: dict[str, str] = {
    # --- ground and ink -------------------------------------------------
    "--color-bg": "#f3f2f2",            # [design]
    "--color-surface": "#eae9e9",       # [design]
    "--color-text": "#201f1d",          # [design]
    "--color-divider": _DIVIDER,        # [design]
    # --- accent ramp ----------------------------------------------------
    "--color-accent": "#b68235",        # [design]
    "--color-accent-100": "#fff3e4",    # [design]
    "--color-accent-200": "#fbe6c8",    # [lmfdb] Tans col_main_ll #ffd893, lightened
    "--color-accent-300": "#f0d0a0",    # [lmfdb] between Tans _ll and _l
    "--color-accent-400": "#dcb478",    # [lmfdb] Tans col_main_l #cca661, lightened
    "--color-accent-500": "#c69a52",    # [lmfdb] Tans col_main_l #cca661
    "--color-accent-600": "#b68235",    # [design] = --color-accent
    "--color-accent-700": "#7d5411",    # [design]
    "--color-accent-800": "#5c3d0e",    # [lmfdb] RuddyBrowns col_main_2 #443227, warmed
    "--color-accent-900": "#3a270d",    # [design]
    # --- neutral ramp ---------------------------------------------------
    "--color-neutral-100": "#f8f4f4",   # [design]
    "--color-neutral-200": "#ece8e8",   # [lmfdb] light_grey_9 #e9e9e9, warmed
    "--color-neutral-300": "#d8d3d3",   # [lmfdb] light_grey_3 #ddd, warmed
    "--color-neutral-400": "#bbbaba",   # [lmfdb] literal #bbbaba from style.css
    "--color-neutral-500": "#918b8b",   # [lmfdb] grey #999, warmed
    "--color-neutral-600": "#6f6a6a",   # [lmfdb] dark_grey_1 #666, warmed
    "--color-neutral-700": "#565151",   # [lmfdb] between dark_grey_1 and dark_grey
    "--color-neutral-800": "#3f3b3b",   # [lmfdb] dark_grey #333, warmed
    "--color-neutral-900": "#2d2b2b",   # [design]
    # --- type -----------------------------------------------------------
    # Self-hosted (see assets/mctl/fonts/). Georgia is the fallback so the
    # page is correct before the fonts load and correct if they never do.
    "--font-heading": "'Cormorant Garamond', Georgia, 'Times New Roman', serif",
    "--font-body": "'Lora', Georgia, 'Times New Roman', serif",
    "--font-mono": "ui-monospace, Menlo, Monaco, monospace",
    # --- radius ---------------------------------------------------------
    "--radius-sm": "2px",   # [design]
    "--radius-md": "4px",   # [design]
    "--radius-lg": "7px",   # [design]
}

#: The stoplight scale -- semantic, defined once, reused everywhere.
#: Literal hex on purpose: these are not part of the ramps and must not
#: drift with them. [design]
STOP: dict[str, dict[str, str]] = {
    "error": {"fg": "#8f2c22", "bg": "#fbeceb", "edge": "#8f2c22"},
    "held": {"fg": "#b0570f", "bg": "#fdeedd", "edge": "#d98322"},
    "warn": {"fg": "#856512", "bg": "#fbf4d5", "edge": "#d4b02c"},
    "go": {"fg": "#3f6b3a", "bg": "#edf3ea", "edge": "#5d8a52"},
    "ok": {"fg": "var(--color-neutral-500)", "bg": "transparent", "edge": "transparent"},
}

DOTTED_DIAGNOSTIC = "#c2867f"  # [design] dotted underline under a diagnostic knowl
LOCKED_RULE = "#e9cfcc"        # [design] divider inside the locked panel
LOCKED_BODY = "#fdf5f4"        # [design] locked panel body ground
```

The `STYLESHEET` follows, built from `TOKENS` plus `@font-face` rules pointing at `/fonts/…`, the `.knowl` `<details>` styling, the `.btn` family (which the design uses but never defines), and LMFDB's `.ntdata` metrics (`white-space: nowrap; padding: 3px 7px`) and `.properties-body` metrics (`padding: 2px 10px`, 7px on first/last rows).

- [ ] **Step 5: Write `state.py`, `assets.py`, `screens/stack.py`, and wire `/queue` in `app.py`**

`state.py` holds the whole URL vocabulary — 13 columns with widths, `sort_link`, `toggle_column`, derived `table_min_width`. Every parser is total: a hand-edited query string falls back rather than raising, so the address bar is not a way to 500 the page.

`stack.row_background` implements the stoplight precedence with **health above cursor**:

```python
def row_background(brief: Mapping[str, Any], *, index: int, cursor: int) -> str:
    """Stoplight precedence, health first.

    Health outranks the cursor deliberately: if the cursor recoloured an error
    row, running j/k down the table would make a violation look like an
    ordinary selected row for as long as the cursor sat on it.
    """
    if brief.get("kind") == "error":
        return STOP["error"]["bg"]
    severity = str(brief.get("sev") or "ok")
    if severity == "error":
        return STOP["held"]["bg"]
    if severity == "warn":
        return STOP["warn"]["bg"]
    if index == cursor:
        return "var(--color-accent-100)"
    return "var(--color-neutral-100)" if index % 2 else "transparent"
```

Headings are anchors with `padding: 6px 12px` (GC9 — the prototype's `5px` clips the sort arrow).

- [ ] **Step 6: Correct the two JavaScript-off statements (GC10)**

`render.py` docstring and `README-development.md:527`:

> Every screen, every sort, every filter and every verdict works with JavaScript disabled — navigation and data state live in the query string, and mutations are ordinary form posts. JavaScript is layered on for four affordances that cannot be expressed as a link or a form: the j/k row cursor, drag-to-reorder on the priority list, live score-weight sliders, and locally saved verdict drafts. Each degrades to a working no-JS path.

- [ ] **Step 7: Run the tests, then the full suite**

```bash
python3 -m pytest tests/mctl/test_dashboard_redesign.py -q
python3 -m pytest tests/mctl -q
```

Both green. `test_dashboard_views.py` must pass **untouched** — it is the honesty contract.

- [ ] **Step 8: Verify end-to-end against the live city**

```bash
bin/mctl dashboard serve --city ~/gt --rig mathcity &
curl -s -o /dev/null -w '/queue -> %{http_code}\n' 'http://127.0.0.1:8471/queue'
curl -s 'http://127.0.0.1:8471/queue?sort_key=unlock&sort_dir=-1' | grep -c 'mc-'
```

Then in a browser **with scripting disabled**: sort by a column, toggle a column off and on. Both must work.

- [ ] **Step 9: Commit**

```bash
git add assets/scripts/mctl_dashboard/ assets/mctl/fonts/ tests/mctl/test_dashboard_redesign.py \
        README-development.md
git commit -m "$(cat <<'EOF'
dashboard: the brief stack, rebuilt end-to-end

First vertical slice: `mctl dashboard serve` now renders the real brief stack
in the adopted design -- thirteen columns with a picker, nine on by default,
sortable, with the stoplight scale and its key. Reads live briefs_list; no
backend change.

Sorting is an <a href> and column toggles are a GET form, so both work with
scripting disabled. That is what the new state module buys: navigation and
data state live in the query string rather than in JavaScript.

Colours resolve the gap left by the design's stylesheet never shipping. Eight
tokens are quoted from the design; the thirteen it never specified are taken
from LMFDB's own semantic ramp in lmfdb/utils/color.py -- the warm Tans and
RuddyBrowns schemes whose family the Classical palette descends from -- and
hue-corrected. Each token says which source it came from. Cormorant Garamond
and Lora are vendored as woff2 rather than fetched, since a loopback tool
should not phone out for a typeface.

Row colour ranks health above the cursor: if the cursor recoloured an error
row, running j/k down the table would make a violation look like an ordinary
selection for as long as the cursor sat on it.

[autogenerated by Claude claude-opus-5 v2.1.220 on 2026-08-19]
EOF
)"
```

---

## Slice 2 — Brief detail, working end-to-end

**Ships:** clicking a row opens the brief in the new design — breadcrumb, title, provenance panel, §1–§7 from the typed `sections` payload, knowls on every rule id / bead id / diagnostic code, and the properties box. Reads live `briefs_show`.

**Files:** create `screens/brief.py`, `knowl.py`; modify `app.py::_brief` (`:309-365`).

**Consumes:** `briefs_show` — which since `36f55c3` carries `body`, `sections` (typed: `section_index` 1–7, `section_key`, `heading`, `body`, `match`) and `body_diagnostics`. **No new tool; `client.py` unchanged.**

**Three rules that decide whether this slice is right:**

1. **Render the typed sections; never parse markdown.** `mctl_core.briefs.PRESENT_IT_SECTIONS` maps 1–7 to keys and `present_it_label(index, key)` returns `"§3 Assumptions surfaced"`. A parser in `render.py` would make the dashboard a second parser, which `mctl_dashboard/__init__.py:6-9` forbids — and would re-implement the `(A)`-bold vs `A —` divergence in a second place.
2. **A body that did not parse says why.** `body_diagnostics` carries `MBRF040` (no description), `MBRF041` (no headings), `MBRF042` (no heading maps to §1–§7). Render the reason. An empty section list with no explanation reads as "this brief has no sections", which is a different and false claim.
3. **Resolve every identifier against the real registry.** The design's fixtures cite `MC-E101`, `MC-E113`, `MC-E207`, `MC-E4xx`; **none exist**. The real registry is `assets/mctl/diagnostics.toml` (72 codes: `MBRF*`, `MWRK*`, `MOPT*`). An unresolved token renders as plain text, never as a knowl that expands to nothing.

**Knowls are `<details>`/`<summary>`**, not a JS toggle — the single largest no-JS win in the design, and it brings keyboard and screen-reader behaviour for free.

**§4 is not fully available.** `parse_decision_options` exists in the core but no MCP tool returns it. Render §4 from `sections` as prose, with an honest note that per-option adopt controls arrive when the core exposes them (issue #66 item 2 / `CHANGELOG.md` §G2). Do not re-implement the option parser here.

- [ ] **Step 1: Write the failing tests** — including:

```python
def test_sections_render_from_the_typed_payload_not_from_parsing():
    """render.py must never contain a markdown parser."""
    import inspect
    from mctl_dashboard.screens import brief

    source = inspect.getsource(brief)
    for banned in ("startswith('#')", 'startswith("#")', "re.match(r'^#"):
        assert banned not in source


def test_a_brief_whose_body_did_not_parse_says_why():
    from mctl_dashboard.screens import brief
    from mctl_dashboard import state

    html = brief.detail(
        {"bead_id": "mc-1", "title": "t", "sections": [],
         "body_diagnostics": [{"code": "MBRF041", "message": "no markdown headings"}]},
        state.ViewState(), knowls={},
    )
    assert "MBRF041" in html and "no markdown headings" in html


def test_an_unresolved_identifier_stays_plain_text():
    """A knowl that expands to nothing is worse than no knowl."""
    from mctl_dashboard import knowl

    html = knowl.tokenize("Raises MC-E101.", rules={}, beads={}, diagnostics={}, key="s1")
    assert "MC-E101" in html and "<details" not in html


def test_a_knowl_needs_no_javascript():
    from mctl_dashboard import knowl

    html = knowl.tokenize(
        "This violates B2.4.",
        rules={"B2.4": {"name": "Source dependency required", "text": "...", "file": "POLICY.md"}},
        beads={}, diagnostics={}, key="s1",
    )
    assert "<details" in html and "<summary" in html
    assert "onclick" not in html.lower()
```

- [ ] **Steps 2–6:** implement per survey §D, run tests, run full suite, verify a real brief renders at `http://127.0.0.1:8471/briefs/<real-id>`, commit.

---

## Slice 3 — Adjudication, working end-to-end

**Ships:** choosing a verdict + disposition + reason, seeing the DRY RUN effect plan, and submitting a **real verdict written to a real bead**. The first slice that mutates.

**Files:** create `screens/panel.py`; modify `app.py::_preview` / `_apply` (reuse, do not replace).

**This is a form, not a widget.** Verdict chips are `<input type="radio">` styled as chips inside the existing POST to `/preview`; disposition is a second radio set; reason is `<textarea required minlength="3">`. `/preview` already renders the effect plan and the confirm token, so this reuses the whole staleness guard rather than building a parallel path — and that is *why* it works with JS off.

**The locked state is the one to get right.** While a brief is HELD, every verdict except reject is `disabled` on the input **and** struck through visually. Styling alone is not a lock: a disabled-looking radio that still submits would let an operator ratify a violation.

**Fix the prototype's lock defect.** It hardcodes `v !== "reject"`, but an error brief's verdict set is `repair` / `waive` / `reject source brief` / `defer` — so a blocked error brief would strike out all four. Compare against the *available* verdict set.

**Leave room for compound verdicts.** 12 of 86 closed briefs carry one, and at least one has two different verdicts in a single submission. Do not hard-code four verdicts as a closed set; keep the radio group extensible. The interaction is an open design question, not something to invent here.

- [ ] **Step 1: Write the failing tests**

```python
def test_a_held_brief_refuses_every_verdict_but_reject_in_the_markup():
    """Styling alone is not a lock -- the input must be disabled too."""
    import re
    from mctl_dashboard.screens import panel
    from mctl_dashboard import state

    html = panel.entry({"bead_id": "mc-71p9", "blocked_by": "mc-e207"},
                       options=[], view=state.ViewState())
    for verdict in ("approve", "revise", "defer"):
        found = re.search(rf'<input[^>]*value="{verdict}"[^>]*>', html)
        assert found and "disabled" in found.group(0), verdict
    allowed = re.search(r'<input[^>]*value="reject"[^>]*>', html)
    assert allowed and "disabled" not in allowed.group(0)


def test_the_panel_never_offers_a_repair_affordance():
    """GC4/GC7 -- the honesty contract, asserted at the panel too."""
    from mctl_dashboard.screens import panel
    from mctl_dashboard import state

    html = panel.entry({"bead_id": "mc-1"}, options=[], view=state.ViewState())
    for banned in ('action="/repair"', ">Repair<", ">Fix<", "Fix these", "auto-repair"):
        assert banned not in html


def test_a_verdict_submits_without_javascript():
    from mctl_dashboard.screens import panel
    from mctl_dashboard import state

    html = panel.entry({"bead_id": "mc-1"}, options=[], view=state.ViewState())
    assert 'action="/preview"' in html and 'method="post"' in html.lower()
```

- [ ] **Steps 2–6:** implement, run tests, run full suite, then **verify end-to-end on a real brief**: choose a verdict, confirm the DRY RUN plan lists the bead writes, submit, and check the verdict landed with `bin/mctl briefs show <id>`. Commit.

---

## Slice 4 — Diagnostics and trust chrome

**Ships:** the diagnostics, artifact-trust and degraded-rig panels restyled into the new design, with all four honesty properties intact on real data.

This slice is mostly *not* new rendering — `render.py`'s existing `diagnostics_sections`, `artifact_trust_panel` and `degraded_rigs_panel` already implement the honesty properties correctly and are test-locked. The work is restyling them into the new shell **without moving them**, so `test_dashboard_views.py` keeps passing against one file.

- [ ] Verify on live data that the actionable count still excludes every `MBRF004`/`MBRF005`/`MBRF021`:

```bash
curl -s http://127.0.0.1:8471/diagnostics | grep -o 'data-actionable-count="[0-9]*"'
curl -s http://127.0.0.1:8471/diagnostics | grep -c 'data-under-review="true"'
```

On the live city the under-review count is large and the actionable count small — `MBRF004` alone fires on 146 of 185 briefs.

---

## Slice 5 — Pile, Deferred, Adjudicated

**Ships:** the three pipeline screens, each rendering what the core can feed and **naming the gap** where it cannot.

| Screen | Data status | Render |
| --- | --- | --- |
| Pile | Gate evaluation **absent** (zero hits for PROMOTABLE/WAITING/GATE_REJECT) | Brief list + an honest panel naming issue #66 / `CHANGELOG.md` §G9 / `mc-xnx` |
| Deferred | `defer_until` computed then discarded (`_defer_until` returns a bool) | Deferred briefs; window shown as not-yet-exposed rather than blank |
| Adjudicated | verdict/option/reason never in the payload; **Outcome** column and **molecule step table** have no source at all | Closed briefs with `decision_state`; the row expansion states the trail is unreadable and names §G6 |

**Do not fake any of it.** A plausible-looking empty state where the real answer is "the core does not expose this yet" is precisely what the honesty properties exist to prevent.

`CHANGELOG.md` §E26 added the Outcome column and the expandable molecule step table; §G6 records the backend work. Render the expansion as `<details>` whose body names the gap. Still **no reopen affordance** (B3.8).

- [ ] **Step 1: Write the failing test**

```python
def test_an_unfed_field_names_the_gap_rather_than_rendering_blank():
    from mctl_dashboard.screens import pipeline

    html = pipeline.pile([{"bead_id": "mc-1", "title": "t"}], gate_states=None)
    assert "not yet exposed" in html.lower()
    assert "#66" in html
```

- [ ] **Steps 2–6:** implement, verify, commit.

---

## Slice 6 — Priority list, ranking and drafts

**Ships:** the operator's own ordering, drag-to-reorder, shuffle, rank-by-comparison, and per-brief verdict drafts. All client-side.

**Priority ordering and drafts live in `localStorage`, not the core.** For drafts this dissolves the standing objection that draft storage is "new domain state invented at the presentation layer" — a draft is browser state, not domain state, on a loopback single-operator tool. For the ordering the argument is stronger: it is explicitly the clerk's own hypothesis about importance, and no policy defines it; persisting it server-side would make one clerk's experiment look canonical.

**Stated cost:** neither survives a different browser or machine.

**No-JS baseline:** ordering has move-up / move-down links; drag is the enhancement. Rank-by-comparison is a page-per-comparison GET flow, which works without script and is arguably clearer than the prototype's in-place card.

**Fix two prototype defects:** the drag splice arithmetic shifts downward drops by one, and `shuffleQueue` uses `sort(() => Math.random() - 0.5)`, which is biased — use Fisher–Yates.

---

## Slice 7 — Final end-to-end verification

- [ ] Full suite green: `python3 -m pytest tests/mctl -q`
- [ ] Every route 200s:

```bash
for path in / /queue /pile /deferred /adjudicated /priority "/queue?scope=errors"; do
  printf '%s -> ' "$path"; curl -s -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:8471$path"
done
```

- [ ] **With JavaScript disabled**: load `/queue`, sort, toggle a column, open a brief, choose a verdict, reach the DRY RUN preview. If any fails, GC3 is violated and the work is not done.
- [ ] **Do not push.** Pushing goes through `authorize-git-operation` with Taylor; other agents' commits are already sitting unpushed on `main`.

---

## Open questions — resolve, do not silently assume

1. **Compound / per-item verdicts.** 12 of 86 closed briefs carry one; one has two different verdicts in a single submission. Slice 3 models one verdict + one disposition and leaves the group extensible. The interaction is a design question.
2. **`MBRF004` at 77%.** It refuses adjudication on 88 of 114 pending briefs and is documented as *instrumentation under review* firing on otherwise-healthy briefs. It must **not** share the HELD treatment, which means "a real gate failed and approving would ratify a violation". It needs a third state; the visual design is Taylor's.
3. **Error briefs are not filed at all** (`CHANGELOG.md` §G1). The whole error-brief class of screens renders empty until detection files them. Backend, and top of §G.
4. **Revise-closes-and-supersedes.** If revise now closes the brief and mints a successor, Slice 3's copy must not imply it comes back. Confirm before writing that copy.
5. **The reconstructed ramp.** Thirteen tokens are LMFDB-derived rather than quoted. If `_ds/classical-…/styles.css` ever surfaces, replacing `TOKENS` makes them exact.
