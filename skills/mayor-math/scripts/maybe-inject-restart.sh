#!/usr/bin/env bash
# PreToolUse hook: reads tool input JSON from stdin.
# If skill == "mayor-math-restart", renders and outputs the Mayor restart context.
# For all other skills, exits silently.

RENDER="$(dirname "$0")/render-restart.sh"

python3 - "$RENDER" <<'PYEOF'
import sys, json, subprocess

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("skill") == "mayor-math-restart":
    subprocess.run(["bash", sys.argv[1]])
PYEOF
