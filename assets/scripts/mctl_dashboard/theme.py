"""Design tokens for the briefs dashboard, in one place.

Every colour, font and radius the dashboard renders comes from here. Nothing
else in `mctl_dashboard` contains a hex literal, because a colour that appears
in two files is a colour that will disagree with itself after the first
revision.

Provenance is recorded per token, because two sources are not equally
authoritative and whoever tunes this later needs to know which is which
without re-deriving it:

  [design]  quoted from the adopted design's README --
            `subdomains/dev/docs/plans/mcp/claude-design-briefs-dashboard-2026-08-19/`.
            These are the values Taylor approved by looking at the rendered
            page, so they win wherever they exist.

  [lmfdb]   taken from `lmfdb/utils/color.py` and `lmfdb/templates/style.css`.
            Used only where the design states no value: its stylesheet
            (`_ds/classical-.../styles.css`) did not ship with the handoff, so
            thirteen of its twenty-one colour variables arrived unvalued.

Why LMFDB is the right filler rather than an interpolation: the design already
borrows LMFDB's conventions (the fixed sidebar, the `.ntdata` table, the knowl
pattern, the properties box), and LMFDB's palette is organised as a *semantic
ramp* -- `col_main_d` (header ground) through `col_main` (links) to
`col_main_ll` (lightest fill) -- which is the same shape as the design's
100-900 scale. Its warm schemes are recognisably the family the Classical
palette descends from: `Tans.col_main_l` is #cca661, sitting beside the
design's accent #b68235, and `Tans.col_main_ll` is #ffd893 beside the design's
--color-accent-100 #fff3e4. `RuddyBrowns` supplies the dark end.

Note that LMFDB's palette is *not* in `lmfdb/templates/style.css`; that file is
a Jinja template full of `{{color.*}}` references. `lmfdb/utils/color.py` is
the source.

If `_ds/classical-.../styles.css` ever surfaces, replace TOKENS wholesale.
Nothing else needs to change.
"""

from __future__ import annotations

from pathlib import Path

#: [design] ink at 16%, as the design README specifies for --color-divider.
_DIVIDER = "rgba(32, 31, 29, 0.16)"

TOKENS: dict[str, str] = {
    # --- ground and ink ---------------------------------------------------
    "--color-bg": "#f3f2f2",           # [design]
    "--color-surface": "#eae9e9",      # [design]
    "--color-text": "#201f1d",         # [design]
    "--color-divider": _DIVIDER,       # [design]
    # --- accent ramp ------------------------------------------------------
    "--color-accent": "#b68235",       # [design]
    "--color-accent-100": "#fff3e4",   # [design]
    "--color-accent-200": "#fbe6c8",   # [lmfdb] Tans col_main_ll #ffd893, lightened
    "--color-accent-300": "#f0d0a0",   # [lmfdb] between Tans col_main_ll and col_main_l
    "--color-accent-400": "#dcb478",   # [lmfdb] Tans col_main_l #cca661, lightened
    "--color-accent-500": "#c69a52",   # [lmfdb] Tans col_main_l #cca661
    "--color-accent-600": "#b68235",   # [design] same value as --color-accent
    "--color-accent-700": "#7d5411",   # [design]
    "--color-accent-800": "#5c3d0e",   # [lmfdb] RuddyBrowns col_main_2 #443227, warmed
    "--color-accent-900": "#3a270d",   # [design]
    # --- neutral ramp -----------------------------------------------------
    "--color-neutral-100": "#f8f4f4",  # [design]
    "--color-neutral-200": "#ece8e8",  # [lmfdb] light_grey_9 #e9e9e9, warmed
    "--color-neutral-300": "#d8d3d3",  # [lmfdb] light_grey_3 #ddd, warmed
    "--color-neutral-400": "#bbbaba",  # [lmfdb] literal #bbbaba in style.css
    "--color-neutral-500": "#918b8b",  # [lmfdb] grey #999, warmed
    "--color-neutral-600": "#6f6a6a",  # [lmfdb] dark_grey_1 #666, warmed
    "--color-neutral-700": "#565151",  # [lmfdb] between dark_grey_1 and dark_grey
    "--color-neutral-800": "#3f3b3b",  # [lmfdb] dark_grey #333, warmed
    "--color-neutral-900": "#2d2b2b",  # [design]
    # --- type -------------------------------------------------------------
    # Self-hosted; see assets/mctl/fonts/ and the @font-face rules below.
    # Georgia leads the fallback so the page is correct before the fonts load
    # and correct if they are absent entirely.
    "--font-heading": "'Cormorant Garamond', Georgia, 'Times New Roman', serif",
    "--font-body": "'Lora', Georgia, 'Times New Roman', serif",
    "--font-mono": "ui-monospace, Menlo, Monaco, 'Cascadia Mono', monospace",
    # --- spacing (design README's scale) -----------------------------------
    "--space-1": "4.6px",
    "--space-2": "9.2px",
    "--space-3": "13.8px",
    "--space-4": "18.4px",
    "--space-5": "23px",
    "--space-6": "27.6px",
    "--space-7": "32.2px",
    "--space-8": "36.8px",
    # --- radius ------------------------------------------------------------
    "--radius-sm": "2px",   # [design]
    "--radius-md": "4px",   # [design]
    "--radius-lg": "7px",   # [design]
}

#: The stoplight scale -- semantic, defined once, reused everywhere.
#:
#: Literal hex on purpose: these are not steps of the accent or neutral ramps
#: and must not drift with them. A WARN that shifted because someone retuned
#: the neutral scale would be a bug in the meaning, not in the styling.
#: [design] -- all five are stated in the design README's stoplight table.
STOP: dict[str, dict[str, str]] = {
    "error": {"fg": "#8f2c22", "bg": "#fbeceb", "edge": "#8f2c22"},
    "held": {"fg": "#b0570f", "bg": "#fdeedd", "edge": "#d98322"},
    "warn": {"fg": "#856512", "bg": "#fbf4d5", "edge": "#d4b02c"},
    "go": {"fg": "#3f6b3a", "bg": "#edf3ea", "edge": "#5d8a52"},
    "ok": {"fg": "var(--color-neutral-500)", "bg": "transparent", "edge": "transparent"},
}

#: Three literals the design uses that belong to no ramp. [design]
DOTTED_DIAGNOSTIC = "#c2867f"  # dotted underline under a diagnostic-code knowl
LOCKED_RULE = "#e9cfcc"        # divider inside the locked adjudication panel
LOCKED_BODY = "#fdf5f4"        # locked adjudication panel body ground

#: Served from `assets/mctl/fonts/` by server.py. Both families are OFL.
#: Vendored rather than fetched: a loopback tool must not phone out for a
#: typeface, and a remote font would also leak which rig is being read to
#: whoever serves it.
FONT_FILES: tuple[str, ...] = (
    "CormorantGaramond-SemiBold.woff2",
    "Lora-Regular.woff2",
    "Lora-Italic.woff2",
)


def _root_block() -> str:
    declarations = "\n".join(f"  {name}: {value};" for name, value in TOKENS.items())
    return ":root {\n" + declarations + "\n}"


#: Where vendored font files live, if they are present at all.
FONT_DIR = Path(__file__).resolve().parents[2] / "mctl" / "fonts"

_FACE_TEMPLATE = """@font-face {
  font-family: %(family)s;
  src: url('/fonts/%(file)s') format('woff2');
  font-weight: %(weight)s;
  font-style: %(style)s;
  font-display: swap;
}
"""

_FACES = (
    ("'Cormorant Garamond'", "CormorantGaramond-SemiBold.woff2", "600", "normal"),
    ("'Lora'", "Lora-Regular.woff2", "400", "normal"),
    ("'Lora'", "Lora-Italic.woff2", "400", "italic"),
)


def font_faces() -> str:
    """@font-face rules for the font files that are actually present.

    Declaring a face whose file is missing is not harmful -- the browser falls
    back to Georgia, which is why Georgia leads the fallback list -- but it does
    put a 404 in the server log on every cold load, which trains an operator to
    ignore 404s in the log of a tool whose whole job is to report failure
    honestly.

    So the rules are emitted only for files on disk. Drop the two OFL families
    into `assets/mctl/fonts/` (see the README there) and the typography appears
    with no code change; leave them out and the dashboard renders in Georgia.
    """
    present = []
    for family, filename, weight, style in _FACES:
        if (FONT_DIR / filename).is_file():
            present.append(
                _FACE_TEMPLATE
                % {"family": family, "file": filename, "weight": weight, "style": style}
            )
    return "\n" + "".join(present) if present else "\n"

_RULES = """
*, *::before, *::after { box-sizing: border-box; }
html, body { margin: 0; background: var(--color-bg); }
body {
  font-family: var(--font-body);
  color: var(--color-text);
  background: var(--color-bg);
  font-size: 14px;
  line-height: 1.45;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}
a { color: var(--color-accent-700); text-decoration: none; }
a:hover { color: var(--color-accent-800); background: var(--color-accent-100); }
*:focus-visible { outline: 2px solid var(--color-accent); outline-offset: 2px; }
::selection { background: var(--color-accent-200); }
h1, h2, h3 { font-family: var(--font-heading); font-weight: 600; }

.mono {
  font-family: var(--font-mono);
  font-feature-settings: 'tnum';
}
.scroll-x { overflow-x: auto; }
.lede { color: var(--color-neutral-700); font-size: 12.5px; }

/* --- shell ------------------------------------------------------------- */
.mc-shell { display: flex; flex: 1 0 auto; align-items: stretch; }
.mc-sidebar {
  width: 186px;
  flex: none;
  background: var(--color-surface);
  border-right: 1px solid var(--color-divider);
  padding-bottom: 20px;
}
.mc-main { flex: 1 1 auto; min-width: 0; padding: 14px 20px 40px; }
.mc-section-head {
  font-family: var(--font-heading);
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 9px 12px;
  background: var(--color-neutral-900);
  color: var(--color-accent-200);
  display: block;
}
.mc-navlink {
  padding: 6px 12px;
  font-size: 13px;
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  border-left: 3px solid transparent;
  color: var(--color-neutral-800);
}
.mc-navlink:hover { background: var(--color-accent-100); }
.mc-navlink[aria-current="page"] {
  color: var(--color-accent-800);
  font-weight: 600;
  border-left-color: var(--color-accent-600);
}

/* --- tables: LMFDB .ntdata metrics -------------------------------------- */
table.ntdata { border-collapse: collapse; width: 100%; }
table.ntdata td {
  white-space: nowrap;
  padding: 3px 7px;
}
table.ntdata thead tr {
  background: var(--color-neutral-200);
  border-bottom: 2px solid var(--color-neutral-900);
}
.mc-row { border-bottom: 1px solid var(--color-divider); }
.mc-row:hover { background: var(--color-accent-100); }
.mc-th a { color: inherit; display: block; }
.mc-th:hover { color: var(--color-accent-700); }

/* --- properties box: LMFDB .properties-body metrics --------------------- */
.properties-body table th, .properties-body table td { padding: 2px 10px; }
.properties-body table tr:first-child td { padding-top: 7px; }
.properties-body table tr:last-child td { padding-bottom: 7px; }
.properties-body .label { font-weight: 600; }

/* --- knowl: a <details> styled as LMFDB's dotted-underline term ---------- */
.knowl > summary {
  display: inline;
  cursor: pointer;
  list-style: none;
  font-family: var(--font-mono);
  font-size: 0.94em;
  color: var(--color-accent-700);
  border-bottom: 1px dotted var(--color-accent-600);
}
.knowl > summary::-webkit-details-marker { display: none; }
.knowl > summary::marker { content: ''; }
.knowl > summary:hover { background: var(--color-accent-100); }
.knowl-body {
  margin-top: 8px;
  border: 1px solid var(--color-divider);
  border-left: 3px solid var(--color-accent-600);
  border-radius: var(--radius-sm);
  background: var(--color-neutral-100);
  padding: 8px 10px;
  font-family: var(--font-body);
  font-size: 12.5px;
  line-height: 1.5;
  white-space: normal;
}

/* --- buttons: the design uses .btn but never defines it ----------------- */
.btn {
  font-family: var(--font-body);
  font-size: 12px;
  line-height: 1.2;
  padding: 5px 12px;
  border-radius: var(--radius-md);
  border: 1px solid var(--color-divider);
  background: transparent;
  color: var(--color-neutral-800);
  cursor: pointer;
}
.btn:hover { background: var(--color-accent-100); border-color: var(--color-accent-500); }
.btn-primary {
  background: var(--color-accent-600);
  border-color: var(--color-accent-700);
  color: var(--color-neutral-100);
}
.btn-primary:hover { background: var(--color-accent-700); color: var(--color-neutral-100); }
.btn-secondary { background: var(--color-neutral-200); border-color: var(--color-neutral-400); }
.btn-ghost { background: transparent; }
.btn[disabled], .btn[aria-disabled="true"] { opacity: 0.45; pointer-events: none; }

/* --- badges ------------------------------------------------------------- */
.mc-dry-run {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.08em;
  padding: 1px 5px;
  border: 1px solid #8f2c22;
  color: #8f2c22;
  border-radius: var(--radius-sm);
}

/* --- diagnostics (kept from the previous sheet; tests assert on these) --- */
.diagnostics { list-style: none; margin: 0; padding: 0; }
.diagnostic { padding: 7px 0; border-bottom: 1px solid var(--color-divider); }
.diagnostic-code { font-family: var(--font-mono); font-size: 11.5px; }
.diagnostic-message { margin: 4px 0 0; font-size: 12.5px; }
.diagnostic-meta { margin: 3px 0 0; font-size: 11px; color: var(--color-neutral-600); }
.severity { font-family: var(--font-mono); font-size: 10px; letter-spacing: 0.05em; }
.severity-FATAL { color: #6c1414; }
.severity-ERROR { color: #8f2c22; }
.severity-WARN { color: #856512; }
.severity-INFO { color: var(--color-neutral-600); }
.review-note {
  font-size: 12px;
  color: var(--color-neutral-800);
  background: var(--color-accent-100);
  border-left: 3px solid var(--color-accent-600);
  padding: 7px 9px;
  margin: 6px 0 0;
}
.panel {
  border: 1px solid var(--color-divider);
  border-radius: var(--radius-md);
  background: var(--color-neutral-100);
  padding: 11px 13px;
  margin-bottom: 14px;
}
.panel.untrusted { border-color: #8f2c22; background: #fbeceb; }
.badge {
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.04em;
  padding: 1px 6px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-divider);
}
dl.facts { display: grid; grid-template-columns: max-content 1fr; gap: 3px 12px; margin: 0; }
dl.facts dt { color: var(--color-neutral-600); font-size: 12px; }
dl.facts dd { margin: 0; font-size: 12.5px; }
pre.plan {
  background: var(--color-neutral-900);
  color: var(--color-neutral-200);
  padding: 10px;
  border-radius: var(--radius-sm);
  overflow-x: auto;
  font-family: var(--font-mono);
  font-size: 11.5px;
}

/* --- responsive --------------------------------------------------------- */
@media (max-width: 720px) {
  .mc-shell { flex-direction: column; }
  .mc-sidebar {
    width: 100%;
    border-right: 0;
    border-bottom: 1px solid var(--color-divider);
  }
  .mc-main { padding: 12px 14px 30px; }
}
"""

STYLESHEET = _root_block() + font_faces() + _RULES
