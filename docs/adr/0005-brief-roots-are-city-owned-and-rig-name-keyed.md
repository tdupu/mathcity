# ADR 0005 — Brief roots are city-owned and keyed by rig NAME, not rig path

Date: 2026-09-10 · Status: accepted (convention delegated by Taylor; agreed
between kolchin-monitor and QUIMBY 69 as ~/gt's agent) · Companion: ADR 0001

## Context

`assets/brief-pipeline/paths.toml` declares brief paths RIG-RELATIVE, resolving
against `<rig_root>`, and states the assumption plainly:

> "matching the live pilot layout at `<rig_root>/.beads/briefs/`
> (hecke pilot: `<city-root>/hecke`)"

That is sound only if rig roots are city-owned directories. They are not, on
either machine:

- **ritt (`~/gt`)** — rigs live under the city root, but they are the gascity
  twins, i.e. git working trees that exchange commits through GitHub.
- **kolchin (`~/HQ`)** — rigs resolve to external source checkouts entirely
  outside the city: `gascity` → `~/repos/gascity`, `mathcity` → `~/repos/mathcity`.

Either way the brief pile lands **inside a git working tree**.

### Gitignoring does not solve it

The obvious mitigation was tested against `~/gt/mathcity`, whose `.beads` IS
gitignored:

```
$ git -C ~/gt/mathcity clean -ndx -- .beads/briefs
Would remove .beads/briefs/
```

All 525 files. `git clean -x` includes ignored files; `git stash -a` sweeps
them; a re-clone loses them outright. **Gitignoring prevents accidental
commits and nothing else.** It remains worth doing for that reason — see
Consequences — but it is not the fix and must not be recorded as one.

### Measured exposure at time of writing (ritt)

```
                          on-disk  tracked  .beads gitignored
mathcity                      525        0  yes
hecke                          87        0  NO
gascity-packs                  67        0  NO
gascity                        51        0  NO
tdupu_github_io                26        0  NO
homog / lmfdb                  38        0  NO
jacobi                         16        0  NO
magma_clifford_algebras         1        0  NO
```

812 files, **zero tracked** — no violation has occurred. But 10 of 11 repos
leave brief state visible to git, one `git add -A` away from committing bead
data into a code repo, which `~/repos/CLAUDE.md` forbids. That risk is
demonstrated, not theoretical: a fork agent ran `git add -A` in a shared
checkout on 2026-09-10 and swept unrelated files into its commit.

kolchin has ~0 rig-side brief files — its rigs never had piles, which is the
defect that started this investigation (see ADR context in
`orders/brief-shuffle-on-submit.toml`).

## Decisions

1. **Brief roots are city-owned and keyed by rig NAME:**

   ```
   <city-root>/.beads/briefs/rigs/<rig>/
   ```

   Rig identity comes from the rig's declared name, never from its filesystem
   path. This is the substance of the fix: kolchin's external checkouts and
   ritt's in-city twins then resolve identically, and a root survives its
   checkout being moved, re-cloned, or cleaned.

2. **The city-root pile stays exactly where it is** — `<city-root>/.beads/briefs/`
   (on ritt: 1062 files, 99 stack briefs). It is not migrated and not nested
   under `rigs/`.

3. **`rigs/hq/` MUST NOT exist.** The `hq` rig is *synthesized*, not declared:
   `city_rig_entries` (`assets/scripts/mctl_core/context.py:191`) returns
   "`city.toml`'s rig entries, plus the reserved city-root store entry", under
   `HQ_RIG_ID = "hq"` (`context.py:42`) — the name the store already answers to
   as `dolt_database: "hq"`. Also documented in
   `orders/brief-shuffle-fast-drain-city.toml`. Verified directly, 2026-09-10. Its
   pile IS the city pile of decision 2. Any resolver asked for the `hq` rig root
   returns `<city-root>/.beads/briefs/`, never a `rigs/hq/` subtree. Without
   this rule two writers address the same pile by different paths and diverge.

4. **`~/.gc/<city>/briefs/<rig>/` is rejected**, despite the `gsp-1pv`
   precedent (`orders/brief-shuffle-pile.toml` line 1 records an earlier
   migration to `~/.gc/mathcity/briefs`). `~/.gc/` also holds import caches
   — kolchin carries `~/.gc/cache/repos/<sha>/orders/…` — and durable brief
   state must not share a tree with something whose contract is "safe to
   clear."

   *Trade-off, stated because it is real:* `~/.gc/` would be immune to a city
   root ever becoming a git repo, and `.beads/` is not. This was accepted on
   the grounds that the cache-clearing risk is measured while the
   city-root-becomes-a-repo risk is hypothetical — and, per QUIMBY, actively
   guarded on ritt: `~/gt` was deliberately de-gitted in S34 (bead `gt-08ddnd`),
   so that reversal has already happened once and left a paper trail.

5. **B2.4/B2.8 "regenerable from bead state" is treated as FALSE for migration
   purposes.** `paths.toml` frames the brief tree as an implementation-detail
   cache. Per QUIMBY, that is *provably* false for a measured subset: bead
   `mc-3fayz` records 122 hq brief rows (90 `stack_file` + 32 manifest) carrying
   `bead_id` null — no bead exists to regenerate them from, so for those rows
   the file is the only record. Bulk regeneration has never been exercised
   end-to-end by either agent.

   **Migration MOVES files. Regeneration is not the recovery path**, and must
   not be relied on as one until someone demonstrates it.

## Consequences

**Blast radius** (measured in `~/repos/mathcity`): 436 references to
`.beads/briefs`, of which 227 are docs (accuracy only). The runtime lever is
~50 declaration sites — 31 formula `vars.artifact_root` defaults, 17
`paths.toml` entries, 2 order overrides. The indirection already exists
(`paths.toml`: "Scripts and formulas may override the root via BRIEF_ROOT /
artifact_root"), so this changes defaults rather than rearchitecting. Any
script hardcoding the literal instead of reading the variable is a latent bug
the migration will surface.

**Data to move:** 812 files across 10 rig trees on ritt; ~0 on kolchin.

**Stopgap, explicitly not the fix.** Adding `.beads/` to `.gitignore` in the 9
unprotected ritt rigs is accident-prevention against `git add -A` only. Per the
`clean -ndx` measurement above it does not protect against cleaning or
re-cloning. It should be labeled as such wherever it is scheduled.

**Division of work.** QUIMBY beads the ~/gt migration (812 files, 10 rigs) as
scheduled work rather than performing it hot, folding the stopgap into the same
bead. kolchin-side changes are this ADR and the declaration-site defaults.

## Cross-references — resolve these together, not separately

- **`he-cc1vqe`** — pending brief, "rig-scoped brief-shuffle root resolution:
  109 briefs stranded in rig piles the shuffler reports as empty." This is the
  same defect from the shuffler's side. **The shuffler fix must target the
  convention above, not repair the old rig-relative paths**, or the two land
  contradictory resolutions.
- **`gt-8p6011`** — mathcity existing in three divergent copies; name-keyed
  roots address the brief-root half of this.
- **`gt-08ddnd`** — the S34 de-gitting of `~/gt` that guards decision 4.
- **`gsp-1pv`** — the earlier `~/.gc/mathcity/briefs` migration this ADR
  supersedes as the convention.
- `orders/brief-shuffle-on-submit.toml` — the rig-scoped-event fan-out fix
  (commit `1f21a6c`) that surfaced this. **That fix set `scope = "city"` to
  stop the fan-out and is in tension with rig-scoped briefs**; it should be
  revisited once rig roots are stable, so the shuffle can be rig-scoped again
  against a root that resolves correctly.

## Provenance

Measurements attributed to kolchin-monitor were taken directly on ritt and
kolchin on 2026-09-10 and are reproducible from the commands shown. Facts
attributed to QUIMBY (`mc-3fayz` row counts, `he-cc1vqe`, `gt-8p6011`,
`gt-08ddnd`) come from ~/gt's agent and have NOT been independently verified
here; they are recorded as reported, with their bead IDs so a reader can check
them.
