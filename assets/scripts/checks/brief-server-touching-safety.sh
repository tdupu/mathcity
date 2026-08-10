#!/bin/sh
# brief-server-touching-safety.sh
#
# Gate: server-touching-safety-override
# Any brief frontmatter declaring server_touching: true MUST NOT be
# auto-dispatched or auto-approved.  This script enforces the machine
# form of the prose override in brief-prep §"Safety overrides" (Override 1)
# and present-it §"Compact form" NEVER rules.
#
# Exit 0  — gate passes (not server-touching, or the human adjudicator adjudication confirmed)
# Exit 1  — gate FAILS (server-touching brief reached automated dispatch path)
#
# Inputs (in priority order):
#   GC_BRIEF_PATH    — absolute path to the brief markdown file
#   gc.brief.path    — metadata key (read via gc bd show if GC_BEAD_ID set)
#
# The check is poka-yoke / binary: it reads the brief frontmatter for the
# literal key `server_touching: true` and rejects mechanically.  No judgment
# is applied here; judgment belongs to the human adjudicator.

set -eu

exec "$(dirname "$0")/brief-check.sh" server-touching-safety "$@"
