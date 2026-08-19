# Dolt pre-flight fragment (P1.14)

**Canonical source for the Dolt dependency pre-flight.** Every mathcity skill
that needs the live bead store copies one of the two blocks below verbatim
(adjusting only the abort-message wording to name what *that* skill needs). Do
not invent a third variant — `tests/dolt-preflight-exit-codes/smoke_test.sh`
greps every call site, fails if one drifts back to a boolean test, and fails if
a call site is not listed in exactly one of the two variant classes.

## Which variant do I copy?

> **If the skill's purpose is to report on city health, use Variant B;
> otherwise use Variant A.**

That is the whole rule. A skill whose output a human reads *in order to learn
what state the city is in* — `city-status`, `hourly-check`, `wake-city` — is a
reporting skill. Everything else is a working skill: it is doing a job, and a
standing city-health condition is not its business.

The two variants differ in **exactly one branch**, the `2` (quarantine) branch.
The `0` branch and the `*` (abort) branch are byte-identical in both.

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
absent) and **127** (`gc` not on PATH). This is why the blocks below test `0`
and `2` explicitly and route *everything else* to the abort branch, rather than
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

## Variant A — working skills (proceed SILENTLY on exit 2)

Copy this into any skill that is *doing a job*. Exit 2 produces **no output at
all**: the quarantine is real, but it is a standing city-health condition that
this skill neither caused nor can fix, and printing it on every invocation
trains the reader to skip this skill's output.

```bash
# --- P1.14 Dolt pre-flight (three-valued; see template-fragments/dolt-preflight.md)
_dolt_out=$(gc dolt health 2>&1); _dolt_rc=$?
case "$_dolt_rc" in
  0) ;;   # healthy — proceed silently
  2) ;;   # reachable; auto-GC blocked by a standing compaction quarantine.
          # NON-FATAL and NOT this skill's business: bd resolves beads normally.
          # Proceed SILENTLY — the reporting skills surface it (Variant B).
  *) # 1 (server unreachable) or anything else (gc missing, no city) — genuinely unusable
     echo "I'm sorry, I can't do that — Dolt is unreachable (bd cannot resolve beads)."
     echo "Run 'gc dolt status' / 'gc dolt start' and retry."
     exit 1 ;;
esac
```

Note that `_dolt_out` is still captured even though Variant A never prints it.
That is deliberate: the capture is what keeps the probe quiet on **every** exit
code, and the abort branch stays byte-identical to Variant B.

## Variant B — reporting skills (surface the quarantine in full)

Copy this into a skill whose job *is* to tell a human what state the city is
in. Exit 2 prints the whole quarantine block — every quarantined database and
how long each has been held — plus the reclaim path.

```bash
# --- P1.14 Dolt pre-flight — REPORTING (see template-fragments/dolt-preflight.md)
_dolt_out=$(gc dolt health 2>&1); _dolt_rc=$?
case "$_dolt_rc" in
  0) ;;   # healthy — proceed silently
  2) # reachable, but auto-GC is blocked by a standing compaction quarantine.
     # NON-FATAL: bd resolves beads normally. Surfacing this IS this skill's job.
     echo "DOLT QUARANTINED — reachable, but auto-GC is blocked:"
     printf '%s\n' "$_dolt_out" | sed -n '/^Compaction quarantine:/,$p' | sed 's/^/  /'
     echo "  Not fatal: bd works. Reclaim with 'gc dolt compact' once an operator clears the marker."
     ;;
  *) # 1 (server unreachable) or anything else (gc missing, no city) — genuinely unusable
     echo "I'm sorry, I can't do that — Dolt is unreachable (bd cannot resolve beads)."
     echo "Run 'gc dolt status' / 'gc dolt start' and retry."
     exit 1 ;;
esac
```

**Never `head -n` the health output.** The quarantine block is printed **last**;
truncating from the top discards exactly the thing Variant B exists to show.

## Rules

1. **Never** collapse this to `gc dolt health >/dev/null 2>&1 || …`.
2. Run `gc dolt health` **once** and reuse `$_dolt_out` — it pings the SQL
   server and can take seconds under load (see `check-work/SKILL.md`).
3. The `2` branch must **not** `exit`, in either variant. Aborting on a
   quarantine is the bug (issue #8). Variant A is *silent*, not *absent*: the
   `2` case must still be written out explicitly so that exit 2 can never fall
   through to `*`.
4. The `*` branch keeps the P1.14 message shape — `I'm sorry, I can't do
   that — …` / fix action / one-line "what this enables". Per-skill wording of
   the *what is missing* and *what this enables* lines is expected to differ;
   the **predicate** must not.
5. **Reporting-vs-working is a behavioural split, not a caveat.** Every call
   site belongs to exactly one class, and the class decides what exit 2 does:
   working skills (Variant A) print nothing, reporting skills (Variant B)
   print the full quarantine block. `city-status`, `hourly-check` and
   `wake-city` are the reporting skills; every other call site is a working
   skill. The class lists are enforced in
   `tests/dolt-preflight-exit-codes/smoke_test.sh` — a new call site that
   appears in neither list fails the suite, so a skill cannot drift in
   unclassified.
6. **Silence on exit 2 is not permission to discard the signal.** Variant A is
   allowed to say nothing *only because* Variant B exists and runs on a
   cadence — `hourly-check` is a watchdog, `city-status` is run before every
   dispatch decision. Auto-GC being blocked on the city's largest bead stores
   is a real degradation; the store grows unbounded until an operator clears
   the marker. If a future edit "simplifies" Variant B into Variant A, or
   deletes the quarantine surfacing from the reporting skills, the signal
   stops reaching a human anywhere and issue #8 returns in a new form — the
   quarantine invisible instead of misreported. **Do not narrow Variant B.**
   If you want less noise, the answer is to clear the quarantine, not to stop
   printing it.
7. **Reporting skills may replace the `*` branch with report-and-continue.**
   `wake-city`, `city-status` and `hourly-check` exist *to diagnose a dead
   city*; aborting on exit 1 would make `wake-city` unable to perform its own
   Step 2 remedy (`gc dolt start`). Those three therefore report
   `DOLT DOWN` / `dolt: DOWN` and continue with the checks that do not need
   Dolt. This deviation is sanctioned **only** for the three files named in the
   Variant B class list and is orthogonal to the A/B split; a working skill
   must still abort. Everything above about the `2` branch applies unchanged.

## Known limitation

`gc dolt health` is cwd-dependent: outside a Gas City root the `dolt` subcommand
is not registered at all (`gc: unknown command "dolt"`, exit 1), so the `*`
branch fires and reports "unreachable" when the real cause is "not in a city".
Run these skills from the city root. Distinguishing the two is tracked
separately; it is not what issues #7/#8 fix.
