---
policy_id: POLICY-BEAD-REVIVAL
policy_version: "0.1"
created: 2026-07-19
source: Taylor Q19 — "we have a lot of examples from no-brainers; Close if already solved / superseded / behavior gone"
feeds_into:
  - manifest-triage-filter KILL tier
  - catch-no-brainer classifier
  - manual triage sessions
---

# POLICY-BEAD-REVIVAL — When to Close vs Revive a Stale Bead

## Purpose

Stale beads (open, zero comments, old) clog the manifest and burn Taylor's brief-review time.
This policy provides the ordered close-tests so a filter or triage agent can kill them
confidently — without Taylor's eyes — or surface them for revival when the problem is real
and unsolved.

The policy has THREE mandatory close-checks. A bead survives all three iff it is eligible
for revival (i.e., dispatch to the machine or a brief to Taylor).

---

## Close-Check 1 — Problem Already Solved

**Rule:** Close if the underlying problem the bead addresses has already been resolved —
by a commit, a merged PR, another closed bead, or a configuration change.

**How to test:**

1. Extract the core problem phrase from the bead title/description (one clause, e.g.
   "Phase 5 patrol failures", "Dolt push backlog exceeds threshold").
2. `bd search "<problem phrase>"` — look for closed beads with overlapping title.
3. `git log --all --oneline --grep "<problem phrase>" | head -10` in the relevant repo.
4. `bd list --status closed | grep -i "<problem phrase>"` — check closed beads.
5. If any result directly names this fix as delivered: **KILL (already solved)**.

**False-positive guard:** A closed bead that *discusses* the same area but reached a
different conclusion (e.g. DEFER or WONT-FIX) is NOT evidence of resolution. The bead
must be closed with a reason that includes the fix ("Superseded by …", "Fixed in
commit …", "Resolved by …").

---

## Close-Check 2 — Problem Superseded by Another Bead

**Rule:** Close if a newer open or recently-closed bead covers the same ground with a
broader or more precise scope, making this bead redundant.

**How to test:**

1. `bd search "<title keywords>"` — find beads with similar title.
2. Compare: does the candidate bead's scope INCLUDE this bead's scope? If yes: close this
   one and add a `bd comments add <id> "Superseded by <newer-id>"` note.
3. Check the newer bead's status:
   - Newer bead OPEN: close this one with `--reason "Superseded by <newer-id>"`.
   - Newer bead CLOSED (resolved): this bead is also solved — apply Close-Check 1.
   - Newer bead CLOSED (deferred): keep this bead open (the problem was explicitly deferred,
     not resolved).

**Smell test for xkcd-927:** if closing this bead would require the replacement bead to
literally do everything this one describes PLUS more — close this one. If closing would
DROP scope from the replacement — do not close (file a note on the replacement instead).

---

## Close-Check 3 — Behavior No Longer Exists

**Rule:** Close if the bead references system behavior, a CLI, a formula, an order, or
a configuration that has since been removed, deprecated, or renamed — making the bead
unaddressable.

**How to test:**

1. Identify the system artifact the bead targets (e.g. `gt` CLI, `gastown.*` vocab,
   a specific formula like `dolt-remotes-sync`).
2. Check existence:
   ```bash
   which <cli-name> 2>/dev/null || echo "not found"
   gc list formulas 2>/dev/null | grep "<formula-name>" || echo "formula absent"
   ls ~/gt/gascity-packs/<rig>/formulas/<name>.toml 2>/dev/null || echo "formula absent"
   ```
3. Check deprecation notes: `grep -r "<artifact-name>" ~/gt/gascity-packs/*/docs/ | grep -i "deprecat\|removed\|retired"`.
4. If the artifact is confirmed gone and no replacement was designated for this bead's
   specific concern: **KILL (behavior no longer exists)**.

**Known deprecated surfaces (auto-KILL if the bead targets ONLY these):**
- `gt` CLI (`gastown.*` commands) — deprecated; `gc` is canonical
- `gastown.*` vocabulary in bead titles (formula step beads, patrol step beads)
- Phase N `brief-review-patrol` failure beads where the underlying brief has since been
  adjudicated or superseded
- `gc status` runtime probe results (known-buggy per gs-0cy2; beads depending on
  `gc status` output should be re-evaluated against `tmux -L gt ls`)

---

## Survivor Path — Revival

A bead that survives all three checks is a **candidate for revival**. Apply disposition:

| Bead age | Last comment | Disposition |
|----------|-------------|-------------|
| ≤ 14 days | any | DISPATCH (machine auto-picks up) |
| 15–60 days | ≥1 comment | DISPATCH with a refresh comment |
| 15–60 days | 0 comments | BRIEF to Taylor (lightweight decision) |
| > 60 days | any | BRIEF to Taylor (explicit revival decision required) |

A "refresh comment" is: `bd comments add <id> "Revived YYYY-MM-DD: problem confirmed unresolved; re-entering dispatcher queue."`.

---

## Policy Source — No-Brainer Exemplars

This policy is grounded in the catch-no-brainer fixture corpus. The following exemplar
shapes from that corpus map directly to close-checks above:

| Fixture | Maps to |
|---------|---------|
| `stale-branch-A.md` (stale branch, PR merged elsewhere) | Close-Check 1 |
| `stale-branch-B.md` (superseded by newer branch) | Close-Check 2 |
| `stale-branch-C.md` (target behavior removed) | Close-Check 3 |
| `close-done-cited-commit.md` (commit cited, work confirmed done) | Close-Check 1 |
| `execution-confirmation-proof.md` (confirmed executed) | Close-Check 1 |

New no-brainer exemplars that reach catch-no-brainer with a CLOSE disposition SHOULD be
reviewed against this policy's three checks to determine which check they satisfy. If a
new pattern emerges not covered by the three checks, file a bead to extend this policy.

---

## Integration Points

**manifest-triage-filter KILL tier**: Apply Close-Check 3 first (cheapest — substring
search), then Close-Check 1 (git log grep), then Close-Check 2 (bd search). Return KILL
if any check fires.

**catch-no-brainer**: Beads classified as STALE (gastown vocab, formula-step beads,
age > 21d + zero comments) implicitly satisfy Close-Check 3 or Close-Check 1. This policy
makes that classification explicit and testable.

**Manual triage (Mayor sessions)**: Present this policy in brief sessions when Taylor
asks "is this moot?" — the three checks are the answer structure.
