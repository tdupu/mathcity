# Dolt pre-flight fragment (P1.14)

**Canonical source for the Dolt dependency pre-flight.** Every mathcity skill
that needs the live bead store copies the block below verbatim (adjusting only
the abort-message wording to name what *that* skill needs). Do not invent a
variant — `tests/dolt-preflight-exit-codes/smoke_test.sh` greps every call site
and fails if one drifts back to a boolean test.

## Why this is not a boolean test

`gc dolt health` has a **three-valued** exit contract, defined upstream in
gascity `examples/bd/dolt/commands/health/run.sh` (the `Exit status` comment
block just above the final `exit`):

| exit | meaning |
|---|---|
| `0` | healthy — server running and answering SQL |
| `1` | **server unreachable** — this is the only value that means "Dolt is down" |
| `2` | server reachable, but a **compaction quarantine** is standing. Upstream calls this "a real (if non-fatal) data-plane degradation" and assigns it a *distinct* code explicitly so callers do not conflate it with an unreachable server. |

Other non-zero values occur in practice and must be treated as "unusable", not
as "quarantine": **78** (`gc dolt: cannot resolve runtime port` — observed live
2026-08-13 during a supervisor bounce, while `dolt-state.json` was momentarily
absent) and **127** (`gc` not on PATH). This is why the block below tests `0`
and `2` explicitly and routes *everything else* to the abort branch, rather than
testing for `1`.

`gc dolt health --json` is **unconditionally exit 0**; programmatic consumers
read `server.reachable` and the `quarantine[]` array from the payload instead
of the exit code.

The historical bug (issues #7, #8): every gate used
`gc dolt health >/dev/null 2>&1 || { "unreachable"; exit 1; }`. `||` fires on
*any* non-zero, so a standing quarantine — which held on `hq` and `hecke` for
30 and 27 days — was reported as a connectivity failure, with remediation
advice (`gc dolt start`) that is a no-op on a running server. Meanwhile `bd`
resolved beads fine the whole time.

## The block

```bash
# --- P1.14 Dolt pre-flight (three-valued; see template-fragments/dolt-preflight.md)
_dolt_out=$(gc dolt health 2>&1); _dolt_rc=$?
case "$_dolt_rc" in
  0) ;;   # healthy — proceed silently
  2) # reachable, but auto-GC is blocked by a standing compaction quarantine.
     # NON-FATAL: bd resolves beads normally. Warn loudly, then proceed.
     echo "WARNING: Dolt is up, but auto-GC is blocked by a standing compaction quarantine:"
     printf '%s\n' "$_dolt_out" | sed -n '/^Compaction quarantine:/,$p' | sed 's/^/  /'
     echo "  Not fatal: bd works. Reclaim with 'gc dolt compact' once an operator clears the marker."
     ;;
  *) # 1 (server unreachable) or anything else (gc missing, no city) — genuinely unusable
     echo "I'm sorry, I can't do that — Dolt is unreachable (bd cannot resolve beads)."
     echo "Run 'gc dolt status' / 'gc dolt start' and retry."
     exit 1 ;;
esac
```

## Rules

1. **Never** collapse this to `gc dolt health >/dev/null 2>&1 || …`.
2. Run `gc dolt health` **once** and reuse `$_dolt_out` — it pings the SQL
   server and can take seconds under load (see `check-work/SKILL.md`).
3. The `2` branch must **not** `exit`. Aborting on a quarantine is the bug.
4. The `*` branch keeps the P1.14 message shape — `I'm sorry, I can't do
   that — …` / fix action / one-line "what this enables". Per-skill wording of
   the *what is missing* and *what this enables* lines is expected to differ;
   the **predicate** must not.
5. Reporting skills (`city-status`, `hourly-check`, `wake-city`) do not abort,
   but must still distinguish `2` from `1` and surface the quarantine block —
   never `head -n` the health output, since the quarantine block is printed
   **last**.

## Known limitation

`gc dolt health` is cwd-dependent: outside a Gas City root the `dolt` subcommand
is not registered at all (`gc: unknown command "dolt"`, exit 1), so the `*`
branch fires and reports "unreachable" when the real cause is "not in a city".
Run these skills from the city root. Distinguishing the two is tracked
separately; it is not what issues #7/#8 fix.
