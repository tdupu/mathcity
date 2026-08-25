"""Design tokens for the briefs dashboard, in one place.

Every colour, font and radius the dashboard renders comes from here. Nothing
else in `mctl_dashboard` contains a hex literal, because a colour that appears
in two files is a colour that will disagree with itself after the first
revision.

Provenance is recorded per token, because two sources are not equally
authoritative and whoever tunes this later needs to know which is which
without re-deriving it:

  [template]  verbatim from the design system itself. An offline, fully
              self-contained render of the prototype turned up on 2026-08-19
              carrying the Classical stylesheet inlined, which is where these
              come from. They are the real values, not an approximation.

  [design]    quoted from the adopted design's README, where the template and
              the README agree.

Thirteen of these were previously reconstructed from LMFDB's semantic ramp,
because the design's own stylesheet had not shipped with the handoff. That
reconstruction is now replaced and the difference was not cosmetic in every
case: the ramps here are generated in OKLCH on one shared lightness scale, so
the same step of any role matches the others in visual value, which an
eyeballed interpolation does not give you. The clearest error it fixes is
`--color-accent-600`, which the reconstruction had set to #b68235 -- that is
`--color-accent`, a different thing; the real ramp step is #a06f24.

The LMFDB lineage in the docstring history was not wrong about the family, and
LMFDB remains the source for the *conventions* this dashboard borrows: the
fixed sidebar, the `.ntdata` table metrics, the knowl, the properties box. It
is simply no longer the source for any colour.
"""

from __future__ import annotations

import base64
from pathlib import Path

#: [template] verbatim from the design system: ink at 16%, expressed as a
#: color-mix rather than a baked rgba so it tracks --color-text.
_DIVIDER = "color-mix(in srgb, #201f1d 16%, transparent)"

TOKENS: dict[str, str] = {
    # --- ground and ink ---------------------------------------------------
    "--color-bg": "#f3f2f2",           # [design]
    "--color-surface": "#eae9e9",      # [design]
    "--color-text": "#201f1d",         # [design]
    "--color-divider": _DIVIDER,       # [design]
    # --- accent ramp ------------------------------------------------------
    "--color-accent": "#b68235",       # [design]
    "--color-accent-100": "#fff3e4",  # [template]
    "--color-accent-200": "#ffe3bf",  # [template]
    "--color-accent-300": "#facb8d",  # [template]
    "--color-accent-400": "#e1ad66",  # [template]
    "--color-accent-500": "#c28d41",  # [template]
    "--color-accent-600": "#a06f24",  # [template]
    "--color-accent-700": "#7d5411",  # [template]
    "--color-accent-800": "#5a3b0a",  # [template]
    "--color-accent-900": "#3a270d",  # [template]
    # --- neutral ramp -----------------------------------------------------
    "--color-neutral-100": "#f8f4f4",  # [template]
    "--color-neutral-200": "#eae7e7",  # [template]
    "--color-neutral-300": "#d7d3d3",  # [template]
    "--color-neutral-400": "#bab6b6",  # [template]
    "--color-neutral-500": "#9b9797",  # [template]
    "--color-neutral-600": "#7d7979",  # [template]
    "--color-neutral-700": "#605d5d",  # [template]
    "--color-neutral-800": "#444141",  # [template]
    "--color-neutral-900": "#2d2b2b",  # [template]
    # --- type -------------------------------------------------------------
    # Self-hosted; see assets/mctl/fonts/ and the @font-face rules below.
    # Georgia leads the fallback so the page is correct before the fonts load
    # and correct if they are absent entirely.
    # [template] verbatim, except that Georgia is inserted ahead of the
    # generic fallback: the two families are not vendored here (see
    # assets/mctl/fonts/README.md), and system-ui on a serif design is a
    # worse approximation than a serif.
    "--font-heading": "'Cormorant Garamond', Georgia, system-ui, sans-serif",
    "--font-body": "'Lora', Georgia, system-ui, sans-serif",
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
  src: url('%(src)s') format('woff2');
  font-weight: %(weight)s;
  font-style: %(style)s;
  font-display: swap;
}
"""


def _data_uri(path: Path) -> str:
    """A `woff2` file as a self-contained `data:` URI.

    Embedded rather than served from `/fonts/`: the design handoff calls for
    the typeface to travel *inside* the page, so the stylesheet is complete on
    its own with no second request. That also closes the two failure modes a
    served font has here -- a loopback tool must never phone out, and a font
    request would leak which rig is being read to whoever answers it -- and it
    means the page renders in Cormorant/Lora even where `server.py`'s `/fonts/`
    route is not reachable. The bytes are the OFL families vendored in
    `assets/mctl/fonts/`; base64 adds about a third to their size, paid once
    per page in the inlined stylesheet.
    """
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:font/woff2;base64,{encoded}"

_FACES = (
    ("'Cormorant Garamond'", "CormorantGaramond-SemiBold.woff2", "600", "normal"),
    ("'Lora'", "Lora-Regular.woff2", "400", "normal"),
    ("'Lora'", "Lora-Italic.woff2", "400", "italic"),
)


def font_faces() -> str:
    """@font-face rules embedding each present font file as a `data:` URI.

    The rules are emitted only for files on disk, and each carries the font's
    own bytes inline (see `_data_uri`) rather than a `/fonts/` URL. So there is
    no cold-load request to 404 and nothing to phone out for: the typeface is
    part of the stylesheet. Drop the two OFL families into `assets/mctl/fonts/`
    (see the README there) and the typography appears with no code change;
    leave them out and the dashboard renders in Georgia, which is why Georgia
    leads the fallback list.
    """
    present = []
    for family, filename, weight, style in _FACES:
        path = FONT_DIR / filename
        if path.is_file():
            present.append(
                _FACE_TEMPLATE
                % {
                    "family": family,
                    "src": _data_uri(path),
                    "weight": weight,
                    "style": style,
                }
            )
    return "\n" + "".join(present) if present else "\n"

_RULES = """
*, *::before, *::after { box-sizing: border-box; }
html, body { margin: 0; background: var(--color-bg); }
/* The design is explicit: wide content scrolls inside its own container and
   the page body never scrolls horizontally. Enforced here rather than trusted
   to every future caller remembering it -- a control row that does not wrap
   pushed the body to 547px at a 390px viewport, and no unit test noticed
   because none of them lay the page out. */
html, body { max-width: 100%; overflow-x: hidden; }
.scroll-x { overflow-x: auto; max-width: 100%; }
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

/* --- shell banners ------------------------------------------------------ */
/* Full-width strips that live in the document flow above the masthead --
   the provenance banner and the served-code (staleness) banner. Both are
   "a fact about this whole page", so both get the same banner treatment
   rather than the inset `.review-note` paragraph style, which is for notes
   inside a panel. The base is the quiet, neutral line the provenance banner
   uses for a clean live-source note; `.mc-banner-alert` is the loud accent
   variant it uses when the news must stop the reader (fixtures, stale code,
   an unknown age). Shared here so the two banners cannot drift apart. */
.mc-banner {
  padding: 7px 12px;
  font-family: var(--font-mono);
  font-size: 11px;
  letter-spacing: 0.04em;
  color: var(--color-neutral-700);
  border-bottom: 1px solid var(--color-divider);
}
.mc-banner-alert {
  background: var(--color-accent-200);
  color: var(--color-accent-900);
  border-bottom: 2px solid var(--color-accent-600);
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

/* --- one-click affordances --------------------------------------------- */
/* The option adopt link and the stack quick actions fill on hover, per the
   design's "outlined, fills on hover" note. Real CSS rather than an inline
   computed value, which the design's authoring note requires for hover. */
.mc-adopt:hover {
  background: var(--color-accent-600);
  color: var(--color-neutral-100);
}
.mc-quick {
  font-family: var(--font-mono);
  font-size: 10.5px;
  padding: 2px 8px;
  border: 1px solid #8f2c22;
  border-radius: var(--radius-md);
  color: #8f2c22;
  white-space: nowrap;
}
.mc-quick:hover { background: #8f2c22; color: #fdeedd; }

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

/* --- city-operations lists, notes and definition blocks ----------------- */
/* The city and molecules screens already emit these four classes; before the
   visual port the sheet defined none of them, so an honest per-rig reason list
   and a P6.2 caveat rendered as unstyled runs of text. Defined here, in the
   one shared sheet, rather than inline on each screen -- the same rule the rest
   of this file follows. */
ul.reason-list { list-style: none; margin: 6px 0 0; padding: 0; }
ul.reason-list li {
  padding: 3px 0;
  border-bottom: 1px solid var(--color-divider);
  font-size: 12.5px;
}
ul.reason-list li:last-child { border-bottom: 0; }
.muted { color: var(--color-neutral-600); }
/* The city screens' P6.2 caveat -- "both of these are true at once", "counted
   separately, never folded in". Same treatment as .review-note (it is the same
   kind of thing: a note the reader must not skip), kept a distinct class so the
   two can diverge. */
.note {
  font-size: 12px;
  color: var(--color-neutral-800);
  background: var(--color-accent-100);
  border-left: 3px solid var(--color-accent-600);
  padding: 7px 9px;
  margin: 6px 0 0;
}
dl.kv { display: grid; grid-template-columns: max-content 1fr; gap: 3px 14px; margin: 0 0 4px; }
dl.kv dt { color: var(--color-neutral-600); font-size: 12px; }
dl.kv dd { margin: 0; font-size: 12.5px; }

/* --- capacity strip: the prototype's colored per-slot cells -------------- */
/* One cell per configured slot. Drawn only when the fleet probe answered --
   an unknown fleet gets no strip at all, never a row of empty cells that would
   read as "all free". */
.mc-cap-strip { display: inline-flex; gap: 2px; align-items: stretch; margin: 4px 0 2px; }
.mc-cap { width: 13px; height: 18px; border-radius: 1px; display: inline-block; }
.mc-cap-occupied { background: var(--color-accent-600); }
.mc-cap-free { background: var(--color-neutral-300); }

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

def _stoplight_rules() -> str:
    """The stoplight pill family, one rule per `STOP` tone.

    Generated from `STOP` rather than typed out so a pill can never come to
    disagree with the scale: retune a tone in one place and its pill follows.
    This is the `.badge`-shaped treatment the design prototype paints on every
    STATE cell (its `TONE` map is exactly `STOP`), lifted into shared CSS so the
    city screens paint a status the same way the briefs screens do.

    `ok` is the neutral tone the honesty invariant needs: an `unknown` state is
    rendered with it, so a probe that could not run is dressed as neither a pass
    nor a failure.
    """
    base = (
        ".mc-stop { font-family: var(--font-mono); font-size: 10.5px; "
        "letter-spacing: 0.05em; padding: 1px 6px; border-radius: var(--radius-sm); "
        "border: 1px solid transparent; display: inline-block; }"
    )
    tones = "\n".join(
        f".mc-stop-{tone} {{ color: {c['fg']}; background: {c['bg']}; "
        f"border-color: {c['edge']}; }}"
        for tone, c in STOP.items()
    )
    return "\n" + base + "\n" + tones + "\n"


STYLESHEET = _root_block() + font_faces() + _RULES + _stoplight_rules()
