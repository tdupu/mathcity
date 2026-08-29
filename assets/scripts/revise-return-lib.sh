#!/usr/bin/env bash
# revise-return-lib.sh — sourceable helpers for the revise-return formula.
#
# Extracted from the formula body so the two decisions with real logic
# (gt-5yxup1) are executably tested rather than pinned by prose (POLICY P6.2):
#
#   revise_scan_pending <root>
#       Print the slug of every decision record under <root>/decisions/*.toml
#       whose `decision` is `revise` and that has NOT yet been successfully
#       re-deposited (no SUCCESS line — one carrying `redeposited_at` — names it
#       in <root>/revise-returned.jsonl). An empty/absent root prints nothing:
#       there are genuinely no pending revises. This is the single scan point the
#       three brief.decided consumer formulas share; before gt-5yxup1 it scanned a
#       dead/empty root and re-filed nothing.
#
#   revise_resolve_target_rig <reason> <source_bead> <rig_list_json>
#       Which rig the revised brief re-files into.
#         DEFAULT: the SOURCE rig — longest configured prefix of <source_bead>
#         (`<prefix>-...`) in <rig_list_json> (`gc rig list --json`).
#         OVERRIDE: when <reason> names a KNOWN target rig via a move directive
#         ("move to rig X", "move to X", "-> rig X", "→ rig X", "refile to rig X"),
#         that rig instead. A directive naming an UNKNOWN rig is ignored (it must
#         not misroute), so resolution falls back to the source rig.
#
# Pure string/file logic; the only external dependency is jq (already a hard
# dependency of the formula's rig resolver).

revise_scan_pending() {
  root="$1"
  ledger="$root/revise-returned.jsonl"
  [ -d "$root/decisions" ] || return 0
  for f in "$root/decisions/"*.toml; do
    [ -f "$f" ] || continue
    slug="$(basename "$f" .toml)"
    decision="$(grep '^decision[[:space:]]*=' "$f" | head -n1 | sed 's/.*=[[:space:]]*//' | tr -d '"')"
    [ "$decision" = "revise" ] || continue
    if [ -f "$ledger" ] && grep "\"brief_slug\":[[:space:]]*\"$slug\"" "$ledger" 2>/dev/null | grep -q '"redeposited_at"'; then
      continue
    fi
    printf '%s\n' "$slug"
  done
}

revise_resolve_target_rig() {
  reason="$1"
  source_bead="$2"
  rigs_json="$3"

  # Known rig names, longest-first so "mathcity" is tried before a shorter name
  # that is a prefix of it.
  names="$(printf '%s' "$rigs_json" | jq -r '(.rigs // [])[].name' 2>/dev/null \
    | awk '{ print length, $0 }' | sort -rn | cut -d' ' -f2-)"

  reason_lc="$(printf '%s' "$reason" | tr '[:upper:]' '[:lower:]')"
  for name in $names; do
    name_lc="$(printf '%s' "$name" | tr '[:upper:]' '[:lower:]')"
    # A move directive that names THIS known rig. `rig <name>` or `move to <name>`
    # / `refile to <name>` / `-> <name>` / `→ <name>`, each optionally via "rig".
    if printf '%s' "$reason_lc" | grep -qE "(move to|re-?file to|->|→)[[:space:]]+(rig[[:space:]]+)?${name_lc}([^a-z0-9_-]|$)" \
       || printf '%s' "$reason_lc" | grep -qE "(^|[^a-z0-9_-])rig[[:space:]]+${name_lc}([^a-z0-9_-]|$)"; then
      printf '%s\n' "$name"
      return 0
    fi
  done

  # DEFAULT: source rig by longest matching prefix of the source bead.
  [ -n "$source_bead" ] || return 0
  printf '%s' "$rigs_json" | jq -r --arg id "$source_bead" '
    [(.rigs // [])[] | select(.prefix as $p | $id | startswith($p + "-"))]
    | sort_by(.prefix | length) | last // empty
    | select(. != null) | .name' 2>/dev/null
}
