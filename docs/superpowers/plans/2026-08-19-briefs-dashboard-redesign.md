# Briefs Dashboard Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the mctl operator dashboard's presentation layer to the adopted Claude Design briefs-dashboard, preserving every honesty property and the stdlib-only constraint.

**Architecture:** `render.py` stays a pure function library returning HTML strings built with f-strings and `_e()`; `app.py` stays a route dispatcher over `client.py`'s 16-tool allowlist. All *navigation and data* state (view, scope, sort, visible columns, `--all-rigs`, open brief) moves into URL query parameters so every screen is reachable and operable with JavaScript off. Inline vanilla JS is added only for affordances that cannot be expressed as a link or form — keyboard cursor, drag-to-reorder, live score sliders, draft persistence, and scroll-on-adopt — each layered on top of a working no-JS baseline. No build step, no npm, no external bundle, no framework.

**Tech Stack:** Python 3.11+ stdlib only (`http.server`, `html.escape`, `urllib.parse`, `json`). HTML5 + CSS custom properties. `<details>`/`<summary>` for disclosure. Inline `<script>` for enhancement only. pytest for tests.

**Spec:** `subdomains/dev/docs/plans/mcp/claude-design-briefs-dashboard-2026-08-19/` — `Briefs-Dashboard.dc.html` (the prototype, 2192 lines), `README.md` (the prose spec) and `CHANGELOG.md` (what was decided and why). Read all three. Where the HTML and README disagree, **the HTML is authoritative** (see Global Constraints §GC9).

**Spec is frozen.** Taylor finished iterating in Claude Design on 2026-08-19 and the snapshot in the repo is final. `CHANGELOG.md` §G is a *prioritised* list of the backend work the design implies, written by the designer — it is the authoritative ordering for issue #66, ahead of any ordering this plan invents.

**Branch:** `feat/dashboard-redesign`, worktree at `.claude/worktrees/dashboard-redesign`, branched off local `main`.

---

## Global Constraints

Every task's requirements implicitly include this section.

- **GC1 — stdlib only.** No `pip install`, no `npm`, no build step, no external CSS or JS file, no CDN. `mctl_dashboard/` imports only the standard library and `mctl_core`.
- **GC2 — loopback only.** `--host` default `127.0.0.1` (`server.py`). Never bind all interfaces.
- **GC3 — no JS required for navigation or data.** Every screen must be reachable, sortable, filterable, and adjudicable with JavaScript disabled. JS may *enhance* (keyboard, drag, sliders, drafts, smooth scroll) but may never be the only path to a screen or a verdict. See ADR note in §GC10.
- **GC4 — the four honesty properties.** Verbatim, non-negotiable:
  1. `MBRF021` / `MBRF004` / `MBRF005` render **with their codes visible**, in a separate "under review" region, **excluded from actionable counts**, with **no repair affordance anywhere**.
  2. The malformed count carries its caveat **inline and adjacent to the number**, never behind a tooltip or a disclosure.
  3. `artifact_trust` renders **both ways**, per rig — "trusted" must be visually distinct from a page that forgot to say.
  4. A degraded rig is **a named row with its reason**, never a silently smaller total.
- **GC5 — the seam.** `client.py::ALLOWED_TOOLS` is the boundary. This plan adds **no** tools. `tests/mctl/test_dashboard_views.py:332` asserts `len(ALLOWED_TOOLS) == 16`; if that number ever changes, `client.py:40` and that assertion change together, in the same commit.
- **GC6 — no shell-shaped escape hatch.** `test_dashboard_views.py:360` scans `mctl_dashboard/*.py` for `os.system`, `shell=True`, `os.popen`, `subprocess.call(`, and `eval(` — **`eval(` is banned as a bare substring**, so do not write `eval(`, and do not name a variable `eval(`-adjacent in a way that produces that substring. Only `client.py` may contain `Popen`.
- **GC7 — banned strings.** `test_dashboard_views.py:285` asserts none of these appear in rendered output: `action="/repair"`, `>Repair<`, `>Fix<`, `Fix these`, `auto-repair`. Do not use the words "Repair" or "Fix" as a bare button/link label anywhere. (The error-brief *verdict* chip is labelled `repair` in lowercase inside a `<button>`, which does not match `>Repair<`; keep it lowercase.)
- **GC8 — machine-readable hooks are load-bearing.** Tests assert on `data-region`, `data-actionable-count`, `data-under-review-count`, `data-artifact-trust`, `data-rig`, `data-degraded`, `data-severity`, `data-code`, `data-under-review`, and `<code class="diagnostic-code">`. **Document order is asserted**: the actionable diagnostics region must render *before* the under-review region. Preserve all of it.
- **GC9 — spec conflicts: the HTML wins.** The README says "twelve available columns, eight on by default"; the prototype defines **13 columns, 9 default**. Use 13/9. The README says headings need ~14px padding so the sort arrow does not clip; the prototype emits `padding: 6px 5px`, which *does* clip under `white-space: nowrap; overflow: hidden`. Here the README states the *intent* and the HTML has the *bug* — use `padding: 6px 12px`. Each such case is called out in the task that touches it.
- **GC10 — a written constraint is changing.** `render.py`'s module docstring and `README-development.md:527` both currently assert the dashboard "works in any browser with JavaScript off". After this plan that remains true for navigation, sorting, filtering, and adjudication, but **false for keyboard nav, drag-reorder, live sliders, and drafts**. Task 1 updates both statements to say exactly that. Do not silently leave them wrong.
- **GC11 — commit messages.** `subdomains/dev/POLICY.md` **P5.5** forbids `Co-Authored-By: Claude` trailers. Use the footer form: `[autogenerated by Claude <model> v<version> on <date>]`.
- **GC12 — schema snapshots.** If any task changes an MCP schema (none should), regenerate with `MCTL_UPDATE_MCP_SNAPSHOT=1 python3 -m pytest tests/mctl/test_mcp_schema_snapshots.py`.
- **GC13 — mutations stay dry-run-first.** `Dashboard.MUTATION_ROUTES` remains exactly `("/preview", "/apply")`. Every write goes preview → confirm with the existing single-use token and three-fingerprint staleness guard in `preview.py`. Adding a third mutation route breaks `test_dashboard_views.py:285`.
- **GC14 — do NOT carry over the `FIXTURES · NOT LIVE DATA` badge.** It appears six times in the prototype and is correct *there* — nothing on that page is read from the city. The real dashboard reads live data, so shipping the badge would state something false. It is the one design element deliberately not implemented. (`CHANGELOG.md` §F31.)
- **GC15 — health colours are never used for verdicts.** A closed decision has no pipeline health, so the Adjudicated screen's verdict column must not reuse the stoplight scale. (`CHANGELOG.md` §F29.) The prototype already respects this: its verdict colours are `#8f2c22` for reject, neutral-800 for approve/repair, accent-800 otherwise.
- **GC16 — reads may span rigs; mutations are always single-rig.** The rig picker is multi-select and defaults to all rigs, but every write pins to one rig at preview time and `preview.arguments` carries that pin through to `/apply`. Never let a rig change between preview and confirm retarget a write. (`CHANGELOG.md` §F34; already enforced at `app.py:900-904`.)

### Test command

```bash
cd /Users/tdupuy/repos/mathcity/.claude/worktrees/dashboard-redesign
python3 -m pytest tests/mctl -q
```

Dashboard-only, faster loop:

```bash
python3 -m pytest tests/mctl/test_dashboard_views.py tests/mctl/test_dashboard_mutation_safety.py tests/mctl/test_dashboard_transport.py -q
```

### Run it

```bash
bin/mctl dashboard serve --city ~/gt --rig mathcity
```

Default `http://127.0.0.1:8471`. Omit `--rig` for city-wide scope.

---

## File Structure

`render.py` is 915 lines today and this plan roughly triples the presentation surface. Keeping it as one file would produce a ~2500-line module — beyond what can be held in context or reviewed. It splits by **screen responsibility**, which is also how it changes.

| File | Status | Responsibility |
| --- | --- | --- |
| `mctl_dashboard/theme.py` | **create** | The design tokens as one `TOKENS` dict + the `STYLESHEET` string. Single source of truth for every colour, font, radius. Nothing else imports colours. |
| `mctl_dashboard/render.py` | **modify** | Page shell, nav, context bar, diagnostics, trust panels, degraded rigs. The honesty-property renderers stay here, unmoved, so their tests keep passing against one file. |
| `mctl_dashboard/screens/__init__.py` | **create** | Re-exports, so `app.py` imports one name per screen. |
| `mctl_dashboard/screens/stack.py` | **create** | The stack/errors/no-brainer queue table: 13 columns, sort, column picker, key legend, score note. |
| `mctl_dashboard/screens/brief.py` | **create** | Brief detail: breadcrumb, provenance, HELD banner, error diagnostic block, compact form, §1–§7, properties box. |
| `mctl_dashboard/screens/panel.py` | **create** | The adjudication panel: entry / review / done, verdict chips, disposition, locked state, effect plan. |
| `mctl_dashboard/screens/pipeline.py` | **create** | Pile, Deferred, Adjudicated, Priority list — the four screens whose data is partly unavailable. |
| `mctl_dashboard/knowl.py` | **create** | The tokenizer + disclosure renderer for rule ids, bead ids, diagnostic codes. Used by brief.py and pipeline.py. |
| `mctl_dashboard/state.py` | **create** | Parse/serialize view state to and from query strings. One place that knows the URL vocabulary. |
| `mctl_dashboard/app.py` | **modify** | Routes. Adds `/pile`, `/deferred`, `/adjudicated`, `/queue`. Keeps `/preview` + `/apply` as the only mutations. |
| `mctl_dashboard/assets.py` | **create** | The one inline `<script>` string, and nothing else. Isolated so GC6's source scan has one obvious place to look and so a reviewer can read all the JS at once. |
| `tests/mctl/test_dashboard_redesign.py` | **create** | New-surface tests. The existing `test_dashboard_views.py` is **not** rewritten — it is the honesty-property contract and must keep passing untouched. |

---

## Task 0: Confirm the baseline is green before changing anything

**Files:** none (verification only)

- [ ] **Step 1: Run the full suite on the untouched worktree**

```bash
cd /Users/tdupuy/repos/mathcity/.claude/worktrees/dashboard-redesign
python3 -m pytest tests/mctl -q 2>&1 | tail -20
```

Expected: all pass. If anything fails **stop and report** — a redesign starting from a red suite cannot tell its own breakage from inherited breakage.

- [ ] **Step 2: Record the baseline count**

Write the pass count into the commit message of Task 1 so later regressions are attributable.

---

## Task 1: Design tokens and the stylesheet

**Files:**
- Create: `assets/scripts/mctl_dashboard/theme.py`
- Modify: `assets/scripts/mctl_dashboard/render.py:35-136` (replace `STYLESHEET`), `:3-8` (docstring, per GC10)
- Modify: `README-development.md:527` (per GC10)
- Test: `tests/mctl/test_dashboard_redesign.py`

**Interfaces:**
- Produces: `theme.TOKENS: dict[str, str]`, `theme.STYLESHEET: str`, `theme.STOP: dict[str, dict[str, str]]`. Every later task reads colours from `TOKENS`/`STOP` and never writes a hex literal.

**Context — the 13 missing ramp values.** The handoff defines only 8 of the 21 colour variables the prototype uses. The rest (`--color-accent-200/300/400/500/600/800`, `--color-neutral-200/300/400/500/600/700/800`) are used heavily — `--color-neutral-600` appears 57 times — and have no value anywhere in the handoff, because `_ds/classical-…/styles.css` did not ship. The values below are **interpolated** between the anchors that *are* defined, in OKLCH-ish perceptual steps, then rounded to hex. They are a faithful reconstruction, not the original. **If the real design-system CSS becomes available, replace this dict wholesale — that is the only change needed.**

Anchors given by the spec: `--color-accent-100 #fff3e4`, `--color-accent-700 #7d5411`, `--color-accent-900 #3a270d`, `--color-neutral-100 #f8f4f4`, `--color-neutral-900 #2d2b2b`, `--color-bg #f3f2f2`, `--color-surface #eae9e9`, `--color-text #201f1d`, `--color-accent #b68235`.

- [ ] **Step 1: Write the failing test**

```python
# tests/mctl/test_dashboard_redesign.py
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard import theme


def test_every_token_the_design_uses_has_a_value():
    """The prototype references 21 colour variables; all must resolve.

    Thirteen of them were never shipped with the handoff. Rendering a page
    with an undefined custom property fails silently -- the browser drops the
    declaration and the element inherits, so the page looks *nearly* right.
    This test is the thing that notices.
    """
    required = {
        "--color-bg", "--color-surface", "--color-text", "--color-divider",
        "--color-accent",
        "--color-accent-100", "--color-accent-200", "--color-accent-300",
        "--color-accent-400", "--color-accent-500", "--color-accent-600",
        "--color-accent-700", "--color-accent-800", "--color-accent-900",
        "--color-neutral-100", "--color-neutral-200", "--color-neutral-300",
        "--color-neutral-400", "--color-neutral-500", "--color-neutral-600",
        "--color-neutral-700", "--color-neutral-800", "--color-neutral-900",
        "--font-heading", "--font-body", "--font-mono",
        "--radius-sm", "--radius-md", "--radius-lg",
    }
    assert required <= set(theme.TOKENS), (
        f"missing tokens: {sorted(required - set(theme.TOKENS))}"
    )


def test_the_stylesheet_declares_every_token_it_uses():
    """No `var(--x)` in the sheet may reference a name `:root` never defines."""
    declared = set(re.findall(r"(--[a-z0-9-]+):", theme.STYLESHEET))
    used = set(re.findall(r"var\((--[a-z0-9-]+)", theme.STYLESHEET))
    assert used <= declared, f"undeclared: {sorted(used - declared)}"


def test_the_stoplight_scale_is_defined_once():
    """Five states, each with fg/bg/edge. Re-inlining hex is how they drift."""
    assert set(theme.STOP) == {"error", "held", "warn", "go", "ok"}
    for name, entry in theme.STOP.items():
        assert set(entry) == {"fg", "bg", "edge"}, name
```

- [ ] **Step 2: Run it to verify it fails**

```bash
python3 -m pytest tests/mctl/test_dashboard_redesign.py -q
```

Expected: `ModuleNotFoundError: No module named 'mctl_dashboard.theme'`.

- [ ] **Step 3: Write `theme.py`**

```python
"""Design tokens for the briefs dashboard, in one place.

Every colour, font and radius the dashboard renders comes from here. Nothing
else in `mctl_dashboard` may contain a hex literal -- a colour that appears in
two files is a colour that will disagree with itself after the first revision.

Provenance: the adopted design is
`subdomains/dev/docs/plans/mcp/claude-design-briefs-dashboard-2026-08-19/`.
Its stylesheet (`_ds/classical-.../styles.css`) did NOT ship with the handoff,
so eight tokens are quoted from the design's README and the remaining thirteen
ramp steps are interpolated between those anchors. They are a reconstruction.
If the real design-system CSS arrives, replace `TOKENS` wholesale; nothing else
needs to change.
"""

from __future__ import annotations

#: Ink at 16%, as the design README specifies `--color-divider`.
_DIVIDER = "rgba(32, 31, 29, 0.16)"

TOKENS: dict[str, str] = {
    # --- ground and ink: quoted from the design README ---
    "--color-bg": "#f3f2f2",
    "--color-surface": "#eae9e9",
    "--color-text": "#201f1d",
    "--color-divider": _DIVIDER,
    # --- accent ramp: 100/700/900 quoted, the rest interpolated ---
    "--color-accent": "#b68235",
    "--color-accent-100": "#fff3e4",
    "--color-accent-200": "#f9e3c6",
    "--color-accent-300": "#eccfa4",
    "--color-accent-400": "#d9b177",
    "--color-accent-500": "#c69a52",
    "--color-accent-600": "#b68235",
    "--color-accent-700": "#7d5411",
    "--color-accent-800": "#5c3d0e",
    "--color-accent-900": "#3a270d",
    # --- neutral ramp: 100/900 quoted, the rest interpolated ---
    "--color-neutral-100": "#f8f4f4",
    "--color-neutral-200": "#ece8e8",
    "--color-neutral-300": "#d8d3d3",
    "--color-neutral-400": "#b9b3b3",
    "--color-neutral-500": "#918b8b",
    "--color-neutral-600": "#6f6a6a",
    "--color-neutral-700": "#565151",
    "--color-neutral-800": "#3f3b3b",
    "--color-neutral-900": "#2d2b2b",
    # --- type ---
    "--font-heading": "'Cormorant Garamond', 'Cormorant', Georgia, 'Times New Roman', serif",
    "--font-body": "'Lora', Georgia, 'Times New Roman', serif",
    "--font-mono": "ui-monospace, Menlo, Monaco, 'Cascadia Mono', monospace",
    # --- spacing (design README's scale; the prototype uses literals, we do not) ---
    "--space-1": "4.6px",
    "--space-2": "9.2px",
    "--space-3": "13.8px",
    "--space-4": "18.4px",
    "--space-5": "23px",
    "--space-6": "27.6px",
    "--space-7": "32.2px",
    "--space-8": "36.8px",
    # --- radius ---
    "--radius-sm": "2px",
    "--radius-md": "4px",
    "--radius-lg": "7px",
}

#: The stoplight scale. Semantic, defined once, reused everywhere.
#: These are literal hex on purpose: they are not part of the accent/neutral
#: ramps and must not drift with them.
STOP: dict[str, dict[str, str]] = {
    "error": {"fg": "#8f2c22", "bg": "#fbeceb", "edge": "#8f2c22"},
    "held": {"fg": "#b0570f", "bg": "#fdeedd", "edge": "#d98322"},
    "warn": {"fg": "#856512", "bg": "#fbf4d5", "edge": "#d4b02c"},
    "go": {"fg": "#3f6b3a", "bg": "#edf3ea", "edge": "#5d8a52"},
    "ok": {"fg": "var(--color-neutral-500)", "bg": "transparent", "edge": "transparent"},
}

#: Three literals the prototype uses that belong to no ramp.
DOTTED_DIAGNOSTIC = "#c2867f"   # dotted underline under a diagnostic knowl
LOCKED_RULE = "#e9cfcc"         # divider inside the locked adjudication panel
LOCKED_BODY = "#fdf5f4"         # locked panel body ground


def _root_block() -> str:
    lines = "\n".join(f"  {name}: {value};" for name, value in TOKENS.items())
    return ":root {\n" + lines + "\n}"


STYLESHEET = _root_block() + """
*, *::before, *::after { box-sizing: border-box; }
html, body { margin: 0; background: var(--color-bg); }
body {
  font-family: var(--font-body);
  color: var(--color-text);
  background: var(--color-bg);
  font-size: 14px;
  line-height: 1.45;
  min-height: 100vh;
}
a { color: var(--color-accent-700); text-decoration: none; }
a:hover { color: var(--color-accent-800); background: var(--color-accent-100); }
*:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
::selection { background: var(--color-accent-200); }
.mono { font-family: var(--font-mono); font-feature-settings: 'tnum'; }
.scroll-x { overflow-x: auto; }

/* --- knowl: a <details> styled as the design's dotted-underline term --- */
.knowl > summary {
  display: inline; cursor: pointer; list-style: none;
  font-family: var(--font-mono); font-size: 0.94em;
  color: var(--color-accent-700);
  border-bottom: 1px dotted var(--color-accent-600);
}
.knowl > summary::-webkit-details-marker { display: none; }
.knowl > summary:hover { background: var(--color-accent-100); }
.knowl.diag > summary { color: #8f2c22; border-bottom-color: """ + DOTTED_DIAGNOSTIC + """; }

/* --- buttons: the design system's .btn family, authored here --- */
.btn {
  font-family: var(--font-body); font-size: 12px; line-height: 1.2;
  padding: 5px 12px; border-radius: var(--radius-md);
  border: 1px solid var(--color-divider); background: transparent;
  color: var(--color-neutral-800); cursor: pointer;
}
.btn:hover { background: var(--color-accent-100); border-color: var(--color-accent-500); }
.btn-primary {
  background: var(--color-accent-600); border-color: var(--color-accent-700);
  color: #fff;
}
.btn-primary:hover { background: var(--color-accent-700); color: #fff; }
.btn-secondary { background: var(--color-neutral-200); border-color: var(--color-neutral-400); }
.btn-ghost { background: transparent; }
.btn[disabled], .btn[aria-disabled="true"] { opacity: 0.45; pointer-events: none; }

/* --- rows and headers --- */
.mc-row:hover { background: var(--color-accent-100); }
.mc-th:hover { color: var(--color-accent-700); }
.mc-adopt { cursor: pointer; }
.mc-adopt:hover { background: var(--color-accent-100); border-color: var(--color-accent-500); }
.mc-navlink:hover { background: var(--color-accent-100); }

/* --- responsive: the existing test asserts a max-width media query --- */
@media (max-width: 720px) {
  .mc-shell { flex-direction: column; }
  .mc-sidebar { width: 100%; border-right: 0; border-bottom: 1px solid var(--color-divider); }
}
"""
```

- [ ] **Step 4: Run the tests to verify they pass**

```bash
python3 -m pytest tests/mctl/test_dashboard_redesign.py -q
```

Expected: 3 passed.

- [ ] **Step 5: Wire `render.py` to the new sheet and correct the two JS-off statements**

In `render.py`, replace the `STYLESHEET` constant (`:35-136`) with an import:

```python
from mctl_dashboard.theme import STYLESHEET  # noqa: F401  (re-exported for page())
```

Then update the module docstring (`render.py:3-8`), replacing the sentence that claims JavaScript-off operation, with:

```python
"""HTML rendering for the mctl operator dashboard.

There is no build step and no client-side framework: this is `str.join` and a
stylesheet. Every screen, every sort, every filter and every verdict works with
JavaScript disabled -- navigation and data state live in the query string, and
mutations are ordinary form posts. JavaScript is layered on top for four
affordances that cannot be expressed as a link or a form: the j/k row cursor,
drag-to-reorder on the priority list, live score-weight sliders, and locally
saved verdict drafts. Each degrades to a working no-JS path.
"""
```

Apply the same correction to `README-development.md:527`.

- [ ] **Step 6: Run the full suite — nothing may regress**

```bash
python3 -m pytest tests/mctl -q
```

Expected: the Task 0 baseline count, plus 3.

- [ ] **Step 7: Commit**

```bash
git add assets/scripts/mctl_dashboard/theme.py assets/scripts/mctl_dashboard/render.py \
        tests/mctl/test_dashboard_redesign.py README-development.md
git commit -m "$(cat <<'EOF'
dashboard: add the design-token theme module

Introduces mctl_dashboard/theme.py as the single source for every colour,
font and radius, replacing the inline STYLESHEET constant. Eight tokens are
quoted from the adopted design's README; the thirteen ramp steps it never
shipped are interpolated between those anchors and marked as a
reconstruction, so replacing them later is one dict.

Also corrects two statements that would otherwise become false: the dashboard
still works with JavaScript off for navigation, sorting, filtering and
verdicts, but the incoming keyboard cursor, drag-reorder, live sliders and
drafts are enhancement-only. Saying "works with JavaScript off" without that
qualification would be wrong once those land.

[autogenerated by Claude claude-opus-5 v2.1.220 on 2026-08-19]
EOF
)"
```

---

## Task 2: View state in the query string

**Files:**
- Create: `assets/scripts/mctl_dashboard/state.py`
- Test: `tests/mctl/test_dashboard_redesign.py` (append)

**Interfaces:**
- Produces: `state.ViewState` (frozen dataclass) with fields `view, scope, rig, all_rigs, sort_key, sort_dir, columns, brief_id, cursor`; `state.parse(query: Mapping[str, str]) -> ViewState`; `state.ViewState.url(self, **overrides) -> str`.
- Consumed by: every screen task. `url()` is how a sortable heading, a column checkbox and a nav link are all rendered as plain `<a href>`, which is what makes GC3 achievable.

**Why this exists.** The prototype holds 30 keys of React state. Thirteen of them are *navigation* (which screen, which scope, which sort, which columns, which brief) and must survive a page load with JS off. This module is the whole URL vocabulary, in one place, so no screen invents its own parameter name.

- [ ] **Step 1: Write the failing test**

```python
def test_view_state_round_trips_through_a_query_string():
    from mctl_dashboard import state

    original = state.ViewState(
        view="queue", scope="errors", rig="mathcity", all_rigs=True,
        sort_key="unlock", sort_dir=1, columns=("slug", "rig", "unlock"),
        brief_id=None, cursor=0,
    )
    url = original.url()
    assert url.startswith("/queue?")
    from urllib.parse import parse_qs, urlparse
    reparsed = state.parse({k: v[0] for k, v in parse_qs(urlparse(url).query).items()})
    assert reparsed.scope == "errors"
    assert reparsed.all_rigs is True
    assert reparsed.sort_key == "unlock"
    assert reparsed.sort_dir == 1
    assert reparsed.columns == ("slug", "rig", "unlock")


def test_sorting_the_current_column_flips_direction():
    from mctl_dashboard import state

    view = state.ViewState(sort_key="score", sort_dir=-1)
    assert view.sort_link("score").endswith("sort_dir=1") or "sort_dir=1" in view.sort_link("score")


def test_a_new_numeric_column_starts_descending():
    """Clicking Unlock first should show the biggest unlock_count, not the smallest."""
    from mctl_dashboard import state

    view = state.ViewState(sort_key="score", sort_dir=-1)
    assert "sort_dir=-1" in view.sort_link("unlock")
    assert "sort_dir=1" in view.sort_link("rig")  # text columns start ascending


def test_unknown_query_values_fall_back_rather_than_raising():
    """A hand-edited URL must not 500 the dashboard."""
    from mctl_dashboard import state

    view = state.parse({"view": "../etc/passwd", "sort_dir": "banana", "cursor": "-3"})
    assert view.view == "queue"
    assert view.sort_dir in (-1, 1)
    assert view.cursor == 0
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest tests/mctl/test_dashboard_redesign.py -q -k view_state
```

Expected: `ModuleNotFoundError: No module named 'mctl_dashboard.state'`.

- [ ] **Step 3: Write `state.py`**

```python
"""The dashboard's URL vocabulary, in one module.

Navigation state lives in the query string rather than in JavaScript, which is
what lets every screen, sort and filter work with scripting disabled. A screen
renders a sortable heading as an ordinary `<a href>` produced by `sort_link`,
and a column toggle as a checkbox inside a GET form -- no handler required.

Every parser here is total: a hand-edited or truncated URL falls back to the
default rather than raising, because a 500 on a malformed query string would
make the address bar a denial-of-service surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Mapping
from urllib.parse import urlencode

VIEWS = ("queue", "brief", "pile", "deferred", "adjudicated", "priority")
SCOPES = ("stack", "errors", "nobrainer")

#: key, label, width px, numeric, on-by-default.
#: Thirteen columns, nine default -- the prototype is authoritative over the
#: design README, which says twelve and eight (GC9).
COLUMNS: tuple[tuple[str, str, int, bool, bool], ...] = (
    ("slug", "Brief", 300, False, True),
    ("rig", "Rig", 86, False, True),
    ("artifact", "Artifact", 124, False, False),
    ("unlock", "Unlock", 78, True, True),
    ("score", "Score", 74, True, True),
    ("age", "Age", 64, True, True),
    ("prio", "Priority", 82, False, True),
    ("kind", "Type", 96, False, False),
    ("formula", "Producer", 156, False, False),
    ("nopts", "Opts", 62, True, True),
    ("sev", "Health", 78, False, True),
    ("source", "Source", 82, False, False),
    ("rec", "Rec.", 88, False, True),
)

COLUMN_KEYS = tuple(key for key, _, _, _, _ in COLUMNS)
NUMERIC_KEYS = frozenset(key for key, _, _, num, _ in COLUMNS if num)
DEFAULT_COLUMNS = tuple(key for key, _, _, _, on in COLUMNS if on)
COLUMN_WIDTH = {key: width for key, _, width, _, _ in COLUMNS}
COLUMN_LABEL = {key: label for key, label, _, _, _ in COLUMNS}

#: Leading tick cell + trailing queue cell + the floor the title column needs.
_LEADING_WIDTH = 46
_TRAILING_WIDTH = 104
_TITLE_FLOOR = 290


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
    sort_key: str = "score"
    sort_dir: int = -1
    columns: tuple[str, ...] = DEFAULT_COLUMNS
    brief_id: str | None = None
    cursor: int = 0

    # -- serialisation ----------------------------------------------------

    def query(self, **overrides: object) -> dict[str, str]:
        merged = replace(self, **overrides)  # type: ignore[arg-type]
        out: dict[str, str] = {}
        if merged.scope != "stack":
            out["scope"] = merged.scope
        if merged.rig:
            out["rig"] = merged.rig
        if merged.all_rigs:
            out["all_rigs"] = "1"
        if merged.sort_key != "score":
            out["sort_key"] = merged.sort_key
        out["sort_dir"] = str(merged.sort_dir)
        if tuple(merged.columns) != DEFAULT_COLUMNS:
            out["columns"] = ",".join(merged.columns)
        if merged.cursor:
            out["cursor"] = str(merged.cursor)
        return out

    def url(self, **overrides: object) -> str:
        merged = replace(self, **overrides)  # type: ignore[arg-type]
        path = f"/briefs/{merged.brief_id}" if merged.view == "brief" and merged.brief_id else {
            "queue": "/queue",
            "pile": "/pile",
            "deferred": "/deferred",
            "adjudicated": "/adjudicated",
            "priority": "/priority",
        }.get(merged.view, "/queue")
        query = urlencode(merged.query(**overrides))
        return f"{path}?{query}" if query else path

    # -- sorting ----------------------------------------------------------

    def sort_link(self, key: str) -> str:
        """Where a click on this heading goes.

        Same column flips direction. A new column starts descending when it is
        numeric -- clicking `Unlock` should show the largest unlock_count
        first, because that is the question the column exists to answer.
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

    # -- columns ----------------------------------------------------------

    def toggle_column(self, key: str) -> tuple[str, ...]:
        """Toggle one column, preserving canonical order on re-add."""
        if key in self.columns:
            return tuple(k for k in self.columns if k != key)
        wanted = set(self.columns) | {key}
        return tuple(k for k in COLUMN_KEYS if k in wanted)

    @property
    def table_min_width(self) -> int:
        """Derived, never static.

        A fixed min-width starves the title column as columns are toggled on:
        the title has no declared width and absorbs the remainder, so the
        remainder has to be computed from what is actually visible.
        """
        body = sum(
            COLUMN_WIDTH[key] for key in self.columns if key != "slug"
        )
        return _LEADING_WIDTH + _TRAILING_WIDTH + _TITLE_FLOOR + body


def parse(query: Mapping[str, str]) -> ViewState:
    raw_columns = str(query.get("columns") or "").strip()
    if raw_columns:
        wanted = {part for part in raw_columns.split(",") if part in COLUMN_KEYS}
        columns = tuple(key for key in COLUMN_KEYS if key in wanted) or DEFAULT_COLUMNS
    else:
        columns = DEFAULT_COLUMNS

    try:
        cursor = max(0, int(str(query.get("cursor") or "0")))
    except ValueError:
        cursor = 0

    sort_dir = -1 if str(query.get("sort_dir") or "-1").strip() != "1" else 1

    return ViewState(
        view=_one(query.get("view"), VIEWS, "queue"),
        scope=_one(query.get("scope"), SCOPES, "stack"),
        rig=(str(query.get("rig")).strip() or None) if query.get("rig") else None,
        all_rigs=_flag(query.get("all_rigs")),
        sort_key=_one(query.get("sort_key"), COLUMN_KEYS, "score"),
        sort_dir=sort_dir,
        columns=columns,
        brief_id=(str(query.get("brief_id")).strip() or None) if query.get("brief_id") else None,
        cursor=cursor,
    )
```

- [ ] **Step 4: Run the tests**

```bash
python3 -m pytest tests/mctl/test_dashboard_redesign.py -q
```

Expected: 7 passed.

- [ ] **Step 5: Commit**

```bash
git add assets/scripts/mctl_dashboard/state.py tests/mctl/test_dashboard_redesign.py
git commit -m "$(cat <<'EOF'
dashboard: move view state into the query string

Adds mctl_dashboard/state.py as the dashboard's whole URL vocabulary: which
screen, which scope, which sort, which columns, which brief. Putting it here
rather than in client-side state is what lets a sortable heading be an <a
href> and a column toggle be a GET form, so every screen keeps working with
JavaScript disabled.

Two decisions worth naming. table_min_width is derived from the visible
columns rather than fixed, because a static value starves the title column as
columns are toggled on. And every parser is total -- a hand-edited query
string falls back to the default instead of raising, so the address bar is not
a way to 500 the page.

Thirteen columns, nine on by default, per the prototype. The design README
says twelve and eight; it also lists thirteen labels.

[autogenerated by Claude claude-opus-5 v2.1.220 on 2026-08-19]
EOF
)"
```

---

## Task 3: The page shell, sidebar and header

**Files:**
- Modify: `assets/scripts/mctl_dashboard/render.py` (`page()` at :159, `NAV` at :138)
- Create: `assets/scripts/mctl_dashboard/assets.py`
- Test: `tests/mctl/test_dashboard_redesign.py` (append)

**Interfaces:**
- Consumes: `theme.STYLESHEET`, `state.ViewState`.
- Produces: `render.page(title, view, sections, *, counts, context, context_bar="") -> str` — note the changed signature; `app.py` call sites update in Task 4. `render.sidebar(view, counts) -> str`. `assets.SCRIPT: str`.

**Spec references:** §A0 of the survey — header bar, key-map strip, sidebar (Pipeline / Priority list / Importance), footer with the DRY RUN legend.

- [ ] **Step 1: Write the failing test**

```python
def test_the_header_counts_link_to_the_screens_they_describe():
    """A chip must never disagree with its destination.

    The design README states this as a rule: every count derives from the same
    query as the view it opens. Rendering the chip as a link to that view is
    the cheap half; the expensive half is that both read one counts dict.
    """
    from mctl_dashboard import render

    html = render.page(
        "Brief stack", "queue", ["<p>body</p>"],
        counts={"pile": 6, "stack": 14, "deferred": 3, "errors": 2, "nobrainer": 3,
                "adjudicated": 8},
        context={"city_root": "~/gt", "rig_id": "mathcity"},
    )
    assert 'href="/pile"' in html
    assert 'href="/deferred"' in html
    assert ">6<" in html and ">3<" in html


def test_the_page_works_without_javascript():
    """Every nav affordance in the shell is a link or a form, never a handler."""
    from mctl_dashboard import render

    html = render.page(
        "Brief stack", "queue", [],
        counts={"pile": 0, "stack": 0, "deferred": 0, "errors": 0, "nobrainer": 0,
                "adjudicated": 0},
        context={},
    )
    for banned in ("onclick=", "onchange=", "onsubmit=", "javascript:"):
        assert banned not in html.lower(), banned


def test_the_footer_explains_the_dry_run_badge():
    from mctl_dashboard import render

    html = render.page("x", "queue", [], counts={}, context={})
    assert "DRY RUN" in html
    assert "no bead writes" in html.lower()
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest tests/mctl/test_dashboard_redesign.py -q -k "header or without_javascript or footer"
```

Expected: `TypeError: page() got an unexpected keyword argument 'counts'`.

- [ ] **Step 3: Implement the shell**

Replace `NAV` (`render.py:138-144`) and `page()` (`:159-192`). Match the existing idiom exactly — f-strings, `_e()` on every interpolation, `"\n".join([...])` for the document.

```python
#: (path, label, counts-key). The order is the pipeline's own order: produced
#: briefs land in the pile, gates promote them to the stack, verdicts close
#: them. A sidebar that listed these alphabetically would hide that.
NAV: tuple[tuple[str, str, str], ...] = (
    ("/queue", "Stack - ready for you", "stack"),
    ("/pile", "Pile - awaiting gates", "pile"),
    ("/queue?scope=errors", "Error briefs", "errors"),
    ("/adjudicated", "Adjudicated - closed", "adjudicated"),
    ("/queue?scope=nobrainer", "No-brainers - DRY RUN", "nobrainer"),
)


def _chip(href: str, label: str, count: object, *, accent: bool = False) -> str:
    colour = "var(--color-accent-800)" if accent else "var(--color-neutral-700)"
    return (
        f'<a href="{_e(href)}" style="font-size: 12px; color: {colour}; '
        'border-bottom: 1px dotted var(--color-accent-600);">'
        f'{_e(label)} <b class="mono" style="font-weight: 600; color: var(--color-text);">'
        f"{_e(count)}</b></a>"
    )


def masthead(counts: Mapping[str, Any], context: Mapping[str, Any]) -> str:
    """Brand, resolved runtime context, and the clickable counts.

    The context line is the *resolved* city/rig/store, not a guess: a
    source-checkout invocation hard-errors upstream rather than resolving a
    plausible-but-wrong rig, and this line is where an operator notices which
    city they are actually looking at.
    """
    city = context.get("city_root") or context.get("city_active") or "-"
    rig = context.get("rig_id") or "all rigs"
    store = context.get("rig_db") or ".beads"
    chips = "".join(
        (
            _chip("/pile", "pile", counts.get("pile", 0)),
            _chip("/queue", "stack", counts.get("stack", 0)),
            _chip("/deferred", "deferred", counts.get("deferred", 0)),
            _chip("/queue?scope=errors", "error briefs", counts.get("errors", 0), accent=True),
        )
    )
    return (
        '<header style="display: flex; align-items: baseline; gap: 18px; '
        "padding: 12px 20px 10px; border-bottom: 2px solid var(--color-neutral-900); "
        'background: var(--color-neutral-100);">'
        '<div style="font-family: var(--font-heading); font-size: 25px; font-weight: 600; '
        'letter-spacing: 0.01em;">MathCity '
        '<span style="color: var(--color-accent-700);">/</span> Briefs</div>'
        '<div class="mono" style="font-size: 11.5px; color: var(--color-neutral-700);">'
        f'<span style="color: var(--color-neutral-600);">city</span> {_e(city)} '
        '<span style="color: var(--color-neutral-400);">&middot;</span> '
        f'<span style="color: var(--color-neutral-600);">rig</span> {_e(rig)} '
        '<span style="color: var(--color-neutral-400);">&middot;</span> '
        f'<span style="color: var(--color-neutral-600);">store</span> {_e(store)}'
        "</div>"
        '<div style="margin-left: auto; display: flex; align-items: center; gap: 14px;">'
        f"{chips}</div>"
        "</header>"
    )
```

Then `sidebar()` — Pipeline rows with counts, the Priority list header, and the Importance sliders rendered inside a GET form so they work without JS:

```python
def sidebar(view: "ViewState", counts: Mapping[str, Any]) -> str:
    """Pipeline position, the operator's own ordering, and the score weights.

    The Importance sliders are wrapped in a GET form with a visible Apply
    button. With JavaScript they update live (see assets.SCRIPT); without it
    the button is the whole interaction, and the ordering still works.
    """
    header = (
        'style="font-family: var(--font-heading); font-size: 13px; font-weight: 600; '
        "letter-spacing: 0.06em; text-transform: uppercase; padding: 9px 12px; "
        'background: var(--color-neutral-900); color: var(--color-accent-200);"'
    )
    rows = "".join(
        f'<a class="mc-navlink" href="{_e(href)}" '
        'style="padding: 6px 12px; font-size: 13px; display: flex; '
        'justify-content: space-between; align-items: baseline; '
        'border-left: 3px solid transparent; color: var(--color-neutral-800);">'
        f"<span>{_e(label)}</span>"
        f'<span class="mono" style="font-size: 10.5px; color: var(--color-neutral-600);">'
        f"{_e(counts.get(key, 0))}</span></a>"
        for href, label, key in NAV
    )
    return (
        '<nav class="mc-sidebar" style="width: 186px; flex: none; '
        "background: var(--color-surface); border-right: 1px solid var(--color-divider); "
        'padding-bottom: 20px;">'
        f"<div {header}>Pipeline</div>"
        '<p style="padding: 7px 12px 4px; font-size: 11px; color: var(--color-neutral-600); '
        'font-style: italic; line-height: 1.35; margin: 0;">'
        "Where the pipeline says each brief is. Produced briefs land in the pile; "
        "gates promote them to the stack.</p>"
        f"{rows}"
        f'<a class="mc-navlink" href="/priority" {header}>Priority list</a>'
        "</nav>"
    )
```

Write `assets.py` with the enhancement script. Keep it small and readable — a reviewer must be able to read all the JavaScript in the dashboard in one sitting.

```python
"""The dashboard's only JavaScript, isolated so it can be read at once.

Nothing here is required. Every behaviour below has a working no-JS path:
the row cursor duplicates keyboard-less clicking, the sliders duplicate the
Apply button, drafts duplicate re-typing, and drag-to-reorder duplicates the
move-up/move-down links. If this file failed to load the dashboard would be
less pleasant and exactly as capable.
"""

SCRIPT = """
(function () {
  'use strict';
  var rows = document.querySelectorAll('[data-row-index]');
  var cursor = 0;

  function paint() {
    for (var i = 0; i < rows.length; i++) {
      rows[i].setAttribute('data-cursor', i === cursor ? 'true' : 'false');
    }
    if (rows[cursor]) {
      rows[cursor].scrollIntoView({ block: 'nearest' });
    }
  }

  document.addEventListener('keydown', function (event) {
    var tag = event.target && event.target.tagName;
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') { return; }
    var key = (event.key || '').toLowerCase();
    if (key === 'j' && rows.length) {
      cursor = Math.min(cursor + 1, rows.length - 1); paint(); event.preventDefault();
    } else if (key === 'k' && rows.length) {
      cursor = Math.max(cursor - 1, 0); paint(); event.preventDefault();
    } else if (key === 'enter' && rows[cursor]) {
      var href = rows[cursor].getAttribute('data-href');
      if (href) { window.location.href = href; event.preventDefault(); }
    } else if (key === '?') {
      var map = document.getElementById('mc-keys');
      if (map) { map.open = !map.open; }
    }
  });

  paint();
})();
"""
```

Inject it as the last element of `<body>` in `page()`:

```python
            f"<script>{SCRIPT}</script>",
            "</body>",
```

- [ ] **Step 4: Run the tests**

```bash
python3 -m pytest tests/mctl/test_dashboard_redesign.py -q
```

Expected: 10 passed.

- [ ] **Step 5: Run the full suite — `page()` changed signature, so call sites may break**

```bash
python3 -m pytest tests/mctl -q
```

If `test_dashboard_views.py` fails on the `page()` signature, that is expected at this point — Task 4 updates `app.py`. **Do not** edit `test_dashboard_views.py` to accommodate it; that file is the honesty contract. Instead give `page()` defaults for `counts` and `context` so existing call sites keep working, and re-run.

- [ ] **Step 6: Commit**

```bash
git add assets/scripts/mctl_dashboard/render.py assets/scripts/mctl_dashboard/assets.py \
        tests/mctl/test_dashboard_redesign.py
git commit -m "$(cat <<'EOF'
dashboard: rebuild the page shell, header and sidebar

Header carries the resolved city/rig/store and the four clickable counts;
each chip links to the screen it counts, so a chip cannot disagree with its
destination. Sidebar lists the pipeline in the pipeline's own order rather
than alphabetically, because the order is the information.

Adds mctl_dashboard/assets.py holding the dashboard's only JavaScript, kept
in one file so a reviewer can read all of it at once. Everything in it is
enhancement: the j/k cursor duplicates clicking, and the page is fully
operable if the script never loads.

[autogenerated by Claude claude-opus-5 v2.1.220 on 2026-08-19]
EOF
)"
```

---

## Task 4: The stack table

**Files:**
- Create: `assets/scripts/mctl_dashboard/screens/__init__.py`, `assets/scripts/mctl_dashboard/screens/stack.py`
- Modify: `assets/scripts/mctl_dashboard/app.py` (add `/queue`, update `_briefs`)
- Test: `tests/mctl/test_dashboard_redesign.py` (append)

**Interfaces:**
- Consumes: `state.ViewState`, `theme.STOP`, `render._e`.
- Produces: `stack.table(briefs, view, *, queued) -> str`, `stack.key_legend() -> str`, `stack.column_picker(view) -> str`, `stack.score(brief, weights) -> int`.

**Spec references:** survey §C in full — 13 columns with exact widths, the derived `min-width`, the ▾/▴ marker, the leading tick + row-number cell, the trailing add-to-queue cell, the stoplight precedence, and the Key legend copy.

**The stoplight precedence is load-bearing** (survey §C5): `kind == "error"` → `sev == "error"` (HELD) → `sev == "warn"` → cursor → zebra. Health outranks the cursor, so the cursor highlight is deliberately invisible on an error row. Preserve that; it is what stops a cursor from making a violation look ordinary.

- [ ] **Step 1: Write the failing test**

```python
def test_the_table_min_width_grows_with_visible_columns():
    """A static min-width starves the title column as columns are toggled on."""
    from mctl_dashboard import state

    lean = state.ViewState(columns=("slug", "rig"))
    fat = state.ViewState(columns=state.COLUMN_KEYS)
    assert fat.table_min_width > lean.table_min_width
    assert lean.table_min_width == 46 + 104 + 290 + 86


def test_health_outranks_the_cursor_in_row_colour():
    """An error row must not be recoloured by the cursor sitting on it."""
    from mctl_dashboard.screens import stack

    error_row = {"kind": "error", "sev": "error"}
    assert stack.row_background(error_row, index=3, cursor=3) == "#fbeceb"


def test_every_column_heading_is_a_link():
    """Sorting works with scripting disabled, so headings are anchors."""
    from mctl_dashboard import state
    from mctl_dashboard.screens import stack

    html = stack.table([], state.ViewState(), queued=())
    assert "<a href=\"/queue?" in html
    assert "onclick" not in html.lower()
```

- [ ] **Step 2: Run to verify it fails**

```bash
python3 -m pytest tests/mctl/test_dashboard_redesign.py -q -k "min_width or outranks or heading_is_a_link"
```

- [ ] **Step 3: Implement `screens/stack.py`**

Key functions, matching the survey's exact values:

```python
def row_background(brief: Mapping[str, Any], *, index: int, cursor: int) -> str:
    """Stoplight precedence, health first.

    Health outranks the cursor deliberately: if the cursor recoloured an error
    row, moving j/k down the table would make a violation look like an
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

The heading cell — note the padding correction from GC9 (12px, not the prototype's 5px, so the sort arrow does not clip under `nowrap; overflow: hidden`):

```python
        cells.append(
            f'<th class="mc-th" style="{width}text-align: {align}; padding: 6px 12px; '
            "border: 0; font-family: var(--font-heading); font-size: 12.5px; "
            f"font-weight: 600; letter-spacing: 0.02em; color: {colour}; "
            'white-space: nowrap; overflow: hidden;">'
            f'<a href="{_e(view.sort_link(key))}" style="color: inherit;">'
            f"{_e(label)}"
            f'<span class="mono" style="color: var(--color-accent-700);">'
            f"{_e(view.sort_marker(key))}</span></a></th>"
        )
```

The Key legend, copy verbatim from survey §C6 — five entries, `ERROR` / `HELD` / `WARN` / `OK` / cursor, each with its swatch.

- [ ] **Step 4: Run the tests**

```bash
python3 -m pytest tests/mctl/test_dashboard_redesign.py -q
```

- [ ] **Step 5: Wire the route in `app.py`**

Add `/queue` to `handle()` before the `/briefs` cases, keeping `/briefs` as an alias so existing links and tests do not break.

- [ ] **Step 6: Full suite**

```bash
python3 -m pytest tests/mctl -q
```

- [ ] **Step 7: Commit**

```bash
git add assets/scripts/mctl_dashboard/screens/ assets/scripts/mctl_dashboard/app.py \
        tests/mctl/test_dashboard_redesign.py
git commit -m "$(cat <<'EOF'
dashboard: rebuild the stack table

Thirteen columns with a picker, nine on by default, sortable by clicking a
heading -- each heading is an <a href>, so sorting survives JavaScript being
off. Table min-width is derived from the visible columns because the title
column has no declared width and absorbs the remainder.

Row colour follows the stoplight scale with health ranked above the cursor:
if the cursor recoloured an error row, running j/k down the table would make
a violation look like an ordinary selection for as long as the cursor sat on
it. Heading padding is 12px rather than the prototype's 5px, which clips the
sort arrow under nowrap+overflow:hidden.

[autogenerated by Claude claude-opus-5 v2.1.220 on 2026-08-19]
EOF
)"
```

---

## Task 5: Knowls

**Files:**
- Create: `assets/scripts/mctl_dashboard/knowl.py`
- Test: `tests/mctl/test_dashboard_redesign.py` (append)

**Interfaces:**
- Produces: `knowl.tokenize(text, *, rules, beads, diagnostics, key) -> str`.

**The important decision:** the knowl is a `<details>`/`<summary>` pair, not a JS toggle. That is the single largest no-JS win in the design — the knowl pattern appears in §1, §2, §3, §6, §7, the policy panel and the provenance panel, and `<details>` gives it expand/collapse, keyboard operation and screen-reader semantics for free.

**Token regex** (survey §F3), which must resolve against `RULES` → `BEADS` → `DIAG` in that order, leaving unresolved matches as plain text:

```python
_TOKEN = re.compile(
    r"(MC-E\d{3}|MBRF\d{3}|MWRK_[A-Z_]+|MOPT\d{3}"
    r"|[A-Z]{2}\d+\.\d+|[A-Z]\d+\.\d+|N\d"
    r"|[a-z]{2,3}-[0-9a-z]{4,6})"
)
```

**Note for the implementer:** the design's own fixtures cite `MC-E101`, `MC-E113`, `MC-E207` and `MC-E4xx`. **None of these exist** in `assets/mctl/diagnostics.toml`, which holds 72 real codes (`MBRF*`, `MWRK*`, `MOPT*`). Resolve every code against the real registry; an unresolved code renders as plain text rather than as a knowl that expands to nothing. Do **not** hard-code the design's fictional codes.

- [ ] **Step 1: Write the failing test**

```python
def test_a_knowl_needs_no_javascript():
    from mctl_dashboard import knowl

    html = knowl.tokenize(
        "This violates B2.4 and blocks mc-71p9.",
        rules={"B2.4": {"name": "Source dependency required", "text": "...", "file": "POLICY.md"}},
        beads={"mc-71p9": {"title": "A held brief"}},
        diagnostics={},
        key="s1",
    )
    assert "<details" in html and "<summary" in html
    assert "onclick" not in html.lower()


def test_an_unresolved_token_stays_plain_text():
    """A knowl that expands to nothing is worse than no knowl."""
    from mctl_dashboard import knowl

    html = knowl.tokenize("Raises MC-E101.", rules={}, beads={}, diagnostics={}, key="s1")
    assert "MC-E101" in html
    assert "<details" not in html
```

- [ ] **Step 2–5:** implement, verify, run the full suite, commit.

---

## Task 6: Brief detail, §1–§7

**Files:**
- Create: `assets/scripts/mctl_dashboard/screens/brief.py`
- Modify: `assets/scripts/mctl_dashboard/app.py::_brief` (`:309-365`)
- Test: `tests/mctl/test_dashboard_redesign.py` (append)

**Interfaces:**
- Consumes: `briefs_show` payload — which as of `36f55c3` carries `body` (raw markdown), `sections` (typed list, each with `section_index` 1–7, `section_key`, `heading`, `body`, `match`), and `body_diagnostics`. **No new tool is needed and `client.py` does not change.**
- Produces: `brief.detail(brief, view, *, knowls) -> str`, `brief.properties(brief) -> str`, `brief.provenance(brief) -> str`.

**Use the typed sections, do not re-parse.** `mctl_core.briefs.PRESENT_IT_SECTIONS` maps 1–7 to keys and `present_it_label(index, key)` returns `"§3 Assumptions surfaced"`. The dashboard renders what the core parsed. Parsing markdown in `render.py` would make it a second parser, which is exactly what `mctl_dashboard/__init__.py:6-9` forbids.

**Sections that did not parse must say so.** `body_diagnostics` carries `MBRF040` (no description → no body), `MBRF041` (no headings), `MBRF042` (no heading maps to §1–§7). Render the reason. An empty section list with no explanation reads as "this brief has no sections", which is a different and false claim.

**§4 is not available yet.** `parse_decision_options` exists in the core but no MCP tool returns it (survey §4d). Render §4 from `sections` where a §4 section exists, as prose, and show an honest note that per-option adopt controls arrive when the core exposes them. **Do not** re-implement the option parser here.

- [ ] **Step 1: Write the failing test**

```python
def test_sections_render_from_the_typed_payload_not_from_parsing():
    """render.py must never contain a markdown parser."""
    import inspect
    from mctl_dashboard.screens import brief

    source = inspect.getsource(brief)
    for banned in ("^#", "startswith('#')", 'startswith("#")', "splitlines()"):
        assert banned not in source, f"looks like markdown parsing: {banned}"


def test_a_brief_whose_body_did_not_parse_says_why():
    from mctl_dashboard.screens import brief
    from mctl_dashboard import state

    html = brief.detail(
        {"bead_id": "mc-1", "title": "t", "sections": [],
         "body_diagnostics": [{"code": "MBRF041", "message": "no markdown headings"}]},
        state.ViewState(), knowls={},
    )
    assert "MBRF041" in html
    assert "no markdown headings" in html
```

- [ ] **Step 2–6:** implement per survey §D, verify, full suite, commit.

---

## Task 7: The adjudication panel

**Files:**
- Create: `assets/scripts/mctl_dashboard/screens/panel.py`
- Modify: `assets/scripts/mctl_dashboard/app.py` (`_preview` :711, `_apply` :882 — reuse, do not replace)
- Test: `tests/mctl/test_dashboard_redesign.py` (append)

**Interfaces:**
- Consumes: `briefs_options` (the four action options with `enabled` + `disabled_reason`), the existing `/preview` + `/apply` token flow.
- Produces: `panel.entry(brief, options, view) -> str`, `panel.locked(brief, blocker) -> str`.

**This is a form, not a widget.** Verdict chips are `<input type="radio">` styled as chips inside the existing POST form to `/preview`; the disposition group is a second radio set; reason is a `<textarea required minlength="3">`. Submitting goes to `/preview`, which already renders the DRY RUN effect plan and the confirm token. That reuses the whole staleness guard rather than inventing a parallel path, and it is why the panel works with JS off.

**The locked state is the one to get right.** While a brief is HELD (`blocked = exists(errorBrief) && !resolved(errorBrief)`), every verdict except `reject` is `disabled` on the input *and* struck through visually. Do not rely on styling alone — a disabled-looking radio that still submits would let an operator ratify a violation. Assert both.

**Known prototype defect to fix** (survey §E3): the lock check hardcodes `v !== "reject"`, but an error brief's verdict set is `repair` / `waive` / `reject source brief` / `defer` — so a blocked error brief would strike out all four chips. Compare against the *available* verdict set, not the literal string.

- [ ] **Step 1: Write the failing test**

```python
def test_a_held_brief_refuses_every_verdict_but_reject_in_the_markup():
    """Styling alone is not a lock -- the input must be disabled too."""
    from mctl_dashboard.screens import panel
    from mctl_dashboard import state

    html = panel.entry(
        {"bead_id": "mc-71p9", "blocked_by": "mc-e207"},
        options=[], view=state.ViewState(),
    )
    import re
    for verdict in ("approve", "revise", "defer"):
        block = re.search(rf'<input[^>]*value="{verdict}"[^>]*>', html)
        assert block and "disabled" in block.group(0), verdict
    accept = re.search(r'<input[^>]*value="reject"[^>]*>', html)
    assert accept and "disabled" not in accept.group(0)


def test_the_panel_never_offers_a_repair_affordance():
    """GC4/GC7 -- the honesty contract, asserted at the panel too."""
    from mctl_dashboard.screens import panel
    from mctl_dashboard import state

    html = panel.entry({"bead_id": "mc-1"}, options=[], view=state.ViewState())
    for banned in ('action="/repair"', ">Repair<", ">Fix<", "Fix these", "auto-repair"):
        assert banned not in html
```

- [ ] **Step 2–6:** implement, verify, full suite, commit.

---

## Task 8: Pile, Deferred, Adjudicated, Priority

**Files:**
- Create: `assets/scripts/mctl_dashboard/screens/pipeline.py`
- Modify: `assets/scripts/mctl_dashboard/app.py` (routes `/pile`, `/deferred`, `/adjudicated`, `/priority`)
- Test: `tests/mctl/test_dashboard_redesign.py` (append)

**These four screens are wholly or partly unfed.** Per the survey and issue #66:

| Screen | Data status | What to render now |
| --- | --- | --- |
| Pile | Gate evaluation **absent** — zero hits for PROMOTABLE/WAITING/GATE_REJECT anywhere | The brief list with an honest panel: gate state is not yet exposed by the core, naming issue #66 and `mc-xnx` |
| Deferred | `defer_until` computed then **discarded** (`_defer_until` returns a bool) | The deferred briefs, with the window shown as "not exposed by the core yet" rather than blank |
| Adjudicated | verdict/option/reason computed internally, **never in the payload**; the new **Outcome** column and **molecule step table** have no source at all | Closed briefs with `decision_state`; Outcome and the expandable trail render their gap explicitly |
| Priority | No store — this plan puts it in `localStorage` | Fully working; ordering via move-up/move-down links (no-JS) plus drag (JS) |

**Adjudicated gained scope in the final design** (`CHANGELOG.md` §E26). Each row now carries an **Outcome** column, and expanding a row shows "what happened since" — a timestamped trail plus the **molecule step table** (steps done / running / pending, with times). Neither has a data source: `CHANGELOG.md` §G6 records "molecule step state and follow-up bead state must be readable per decided brief" as backend work. Render the row expansion as a `<details>` whose body states that the trail is not yet readable and names §G6 — do not synthesise a plausible timeline. Still **no reopen affordance** (B3.8).

**The store panel and rig picker** (`CHANGELOG.md` §E28) belong to Task 3's header, not here. The rig control is a **multi-select defaulting to all rigs** — not the prototype's earlier `--all-rigs` checkbox — and `store` opens a panel showing engine, branch, last commit, schema version, connection, legacy `decisions-track` rows and a doctor summary. That is one backend read (`CHANGELOG.md` §G7) which does not exist; render the panel with the fields it can fill and name the gap for the rest.

**Do not fake any of it.** A screen that renders a plausible-looking empty state where the real answer is "the core does not expose this yet" is precisely the failure the honesty properties exist to prevent. Each unfed field says which issue tracks it.

- [ ] **Step 1: Write the failing test**

```python
def test_an_unfed_field_names_the_gap_rather_than_rendering_blank():
    from mctl_dashboard.screens import pipeline

    html = pipeline.pile([{"bead_id": "mc-1", "title": "t"}], gate_states=None)
    assert "not yet exposed" in html.lower()
    assert "#66" in html
```

- [ ] **Step 2–6:** implement, verify, full suite, commit.

---

## Task 9: End-to-end verification against the live city

**Files:** none (verification)

- [ ] **Step 1: Full suite**

```bash
python3 -m pytest tests/mctl -q
```

- [ ] **Step 2: Start the dashboard**

```bash
bin/mctl dashboard serve --city ~/gt --rig mathcity
```

- [ ] **Step 3: Verify each screen returns 200**

```bash
for path in / /queue /pile /deferred /adjudicated /priority "/queue?scope=errors"; do
  printf '%s -> ' "$path"
  curl -s -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:8471$path"
done
```

Expected: `200` for every path.

- [ ] **Step 4: Verify the honesty properties survive on real data**

```bash
curl -s http://127.0.0.1:8471/diagnostics | grep -c 'data-under-review="true"'
curl -s http://127.0.0.1:8471/diagnostics | grep -o 'data-actionable-count="[0-9]*"'
```

The actionable count must exclude every `MBRF004`/`MBRF005`/`MBRF021`. On the live city that means a large under-review count and a small actionable one — `MBRF004` alone fires on 146 of 185 briefs.

- [ ] **Step 5: Verify it works with JavaScript disabled**

In a browser with scripting off: load `/queue`, sort by a column, toggle a column, open a brief, choose a verdict, submit to the DRY RUN preview. All must work. **If any of these fail, GC3 is violated and the task is not done.**

- [ ] **Step 6: Report, do not push**

Summarise: screens working, screens blocked on core data, test counts. **Do not push** — pushing goes through `authorize-git-operation` with Taylor, and three commits are already sitting unpushed on `main` from other agents.

---

## Open questions — resolve before or during, not silently

1. **The 13 reconstructed colour values.** Task 1 interpolates them. If the real `_ds/classical-…/styles.css` can be exported from Claude Design, replacing `theme.TOKENS` makes the reconstruction exact. **Ask before assuming the interpolation is good enough** — `--color-neutral-600` alone is used 57 times.
2. **Cormorant Garamond and Lora.** Neither ships nor is installed; `theme.py` falls back to Georgia. Vendoring the two `.woff2` files (both OFL) into `assets/` and serving them from the loopback server is a separate decision — it is the difference between the design's typography and a serif approximation.
3. **Compound / per-item verdicts.** 12 of 86 closed briefs carry one, and one has *two different verdicts in a single submission*. The panel in Task 7 models one verdict + one disposition. Do not hard-code four verdicts as a closed set; leave the radio group extensible. The interaction is a design question, not an implementation one.
4. **`MBRF004` at 77%.** It refuses adjudication on 88 of 114 pending briefs, and it is documented as *instrumentation under review* firing on otherwise-healthy briefs. It must **not** share the HELD treatment, which means "a real gate failed and approving would ratify a violation". It needs its own third state. Task 7 renders it distinctly and says so; the visual design is Taylor's.
5. **Revise-closes-and-supersedes.** If a revise now closes the brief and mints a successor, the panel's copy in Task 7 must not imply the brief comes back. Confirm the current semantics before writing that copy.
