#!/usr/bin/env bash
# render-prime.sh — renders the Mayor prime input (the restart PROMPT).
#
# Resolution order:
#   1. Jinja: $STATE_DIR/restart/PROMPT-mayor-restart.j2 rendered with
#      $STATE_DIR/session-catalog.json + live `bd show <handoff-bead>`.
#   2. Fallback: $STATE_DIR/restart/PROMPT-mayor-restart.txt (curated text).
#   3. Generic:  <skill>/templates/PROMPT-mayor-generic.txt (first-import
#      experience — printed with bootstrap instructions).
#
# State dir defaults to <city-root>/mathcity-mayor; override with MAYOR_STATE_DIR.

STATE_DIR="${MAYOR_STATE_DIR:-$HOME/gt/mathcity-mayor}"
CATALOG="$STATE_DIR/session-catalog.json"
TEMPLATE="$STATE_DIR/restart/PROMPT-mayor-restart.j2"
FALLBACK="$STATE_DIR/restart/PROMPT-mayor-restart.txt"
SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
GENERIC="$SKILL_DIR/templates/PROMPT-mayor-generic.txt"

# --- 1. jinja render (requires jinja2 + non-empty catalog + template) -------
if [ -f "$CATALOG" ] && [ -f "$TEMPLATE" ]; then
    python3 - "$CATALOG" "$TEMPLATE" <<'PYEOF' && exit 0
import sys, json, subprocess

try:
    from jinja2 import Template
except ImportError:
    sys.exit(1)

catalog_path, template_path = sys.argv[1], sys.argv[2]

with open(catalog_path) as f:
    sessions = json.load(f)

if not sessions:
    sys.exit(1)

last = sessions[-1]
handoff_bead = last.get("bead")
legacy_session_key = "qui" + "mby"
session_number = last.get("mayor_session", last.get(legacy_session_key, 0)) + 1

def ordinal(n):
    if 11 <= n % 100 <= 13:
        return f"{n}th"
    return {1: "1st", 2: "2nd", 3: "3rd"}.get(n % 10, f"{n}th")

_words = {1:"first",2:"second",3:"third",4:"fourth",5:"fifth",6:"sixth",
          7:"seventh",8:"eighth",9:"ninth",10:"tenth"}

session_word = _words.get(session_number, ordinal(session_number))
next_word = _words.get(session_number + 1, ordinal(session_number + 1))

handoff_content = "(no handoff bead recorded)"
if handoff_bead:
    try:
        result = subprocess.run(["bd", "show", handoff_bead],
                                capture_output=True, text=True, timeout=15)
        handoff_content = result.stdout.strip() or "(empty bead)"
    except Exception as e:
        handoff_content = f"(could not fetch {handoff_bead}: {e})"

with open(template_path) as f:
    tmpl = Template(f.read())

prior_session = last.get("mayor_session", last.get(legacy_session_key, 0))
prev = sessions[-2] if len(sessions) >= 2 else {}

context = dict(
    sessions=sessions,
    mayor_session_number=session_number,
    mayor_session_number_word=session_word,
    mayor_session_number_ordinal=ordinal(session_number),
    next_mayor_session_word=next_word,
    handoff_bead=handoff_bead or "none",
    handoff_bead_content=handoff_content,
    city_state=last.get("city_state") or "(not recorded)",
    charge=last.get("charge_for_next") or "(no charge recorded)",
    objectives_short=last.get("objectives_short") or [],
    objectives_long=last.get("objectives_long") or [],
    prior_mayor_session=prior_session,
    prior_objectives_eval=last.get("objectives_eval") or [],
    prior_additional_work=last.get("additional_work") or [],
)
legacy_prefix = legacy_session_key
context[legacy_prefix + "_number"] = session_number
context[legacy_prefix + "_number_word"] = session_word
context[legacy_prefix + "_number_ordinal"] = ordinal(session_number)
context["next_" + legacy_prefix + "_word"] = next_word
context["prior_" + legacy_prefix] = prior_session
print(tmpl.render(**context))
PYEOF
fi

# --- 2. curated plain-text fallback ------------------------------------------
if [ -f "$FALLBACK" ]; then
    cat "$FALLBACK"
    exit 0
fi

# --- 3. generic mayor statement (first import — no state dir yet) ------------
cat "$GENERIC"
cat <<BOOTSTRAP

######
BOOTSTRAP (no mayor state found at $STATE_DIR)
######
This city has no mayor session state yet. To set it up:
  mkdir -p "$STATE_DIR/restart"
  echo "[]" > "$STATE_DIR/session-catalog.json"
Then, at the end of this first session, run /mayor-math-handoff — it writes
your first handoff bead, session-catalog entry, and restart PROMPT, after
which future sessions prime from your own city's state instead of this
generic statement.
BOOTSTRAP
