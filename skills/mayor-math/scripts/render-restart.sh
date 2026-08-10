#!/usr/bin/env bash
# Renders the Mayor restart document from session-catalog.json + PROMPT-mayor-restart.j2.
# Falls back to PROMPT-mayor-restart.txt if jinja2 is unavailable or catalog is empty.

CATALOG="$HOME/gt/mathcity-mayor/session-catalog.json"
TEMPLATE="$HOME/gt/mathcity-mayor/PROMPT-mayor-restart.j2"
FALLBACK="$HOME/gt/mathcity-mayor/PROMPT-mayor-restart.txt"

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
)
legacy_prefix = legacy_session_key
context[legacy_prefix + "_number"] = session_number
context[legacy_prefix + "_number_word"] = session_word
context[legacy_prefix + "_number_ordinal"] = ordinal(session_number)
context["next_" + legacy_prefix + "_word"] = next_word
print(tmpl.render(**context))
PYEOF

cat "$FALLBACK"
