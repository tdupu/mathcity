# MathCity Dashboard — Fixture Data

**What this is.** Concrete data for laying out
[dashboard-screens.md](./dashboard-screens.md). A dashboard designed against toy
data breaks on contact — these are the real proportions.

**Two kinds of content, marked on every item:**

- **[OBS]** — observed from the live city on 2026-08-20. Real ids, real counts.
- **[SYN]** — synthesized. The ideal-city fields (evidence chains, dispatch
  cause, worktree ownership) **do not exist yet**, so any value shown for them is
  invented to be realistic. Do not cite a `[SYN]` number as a measurement.

---

## City-wide scale

**[OBS]** Bead stores, with commit counts and open beads:

```
gascity_packs     29,750 commits    3,923 open beads   ← dominant
agent_skills       1,547               139
gs (gascity)       1,884               103
differential_val…    295                19
cp2                  128                 9
he (hecke)           109                 8
da_prob / da_pub / dc   33 each           0 each       ← registered, EMPTY
```

**Design consequences.** One store holds **93% of all open beads**. Equal visual
weight per rig wastes most of the screen. Three rigs are registered and
completely empty and **must still render** — empty is the common case, not an
edge case to sketch last.

**[OBS]** Data plane: healthy, `127.0.0.1:58506`, **223 ms** latency. Health
probe returns **exit code 2** — reachable, quarantine standing. This is the
three-valued case, and it is the *live* state, so the "degraded but fine"
rendering is exercised from day one.

**[OBS]** 16 registered rigs. 98 registered diagnostic codes.

---

## Molecules

**[OBS]** **45 open `build-basic-briefed` roots** in `gascity_packs` alone. All
titled identically — *"build-basic-briefed"* — all P0, all open.

That is the single most important layout fact in this document. **Forty-five rows
with the same title and the same priority**, of which perhaps a handful are
actually doing anything. If the census cannot distinguish them, it is a wall of
identical text.

**[OBS]** A real one: `gsp-q31ot8` · build-basic-briefed · created 2026-08-05 ·
updated 2026-08-05 · P0 · OPEN. Fifteen days without an update.

Its description is long — 25+ lines of formula rationale, mentioning
`parser.go:411-436`, mechanism IDs, invariant names. **Molecule descriptions are
prose, not labels.** Truncate deliberately.

### Scenario set — one of each state

| Id | State | Shape |
|---|---|---|
| `gsp-q31ot8` **[OBS]** | `dormant` | Open 15 days, no worker, no motion. Open *by design*, terminal step never reached |
| `gsp-8eqb3o` **[OBS]** | `stranded` **[SYN]** | Same title, same priority — indistinguishable without evidence |
| `he-8kd2` **[SYN]** | `advancing` | Worker attached, commit 6m ago, step 3 of 8 |
| `gsp-w4t354` **[OBS]** | `stalled` **[SYN]** | Worker holds slot, `limit_state=weekly` — a nudge cannot fix it |
| `as-g6f2` **[SYN]** | `advancing` | The defect signature: artifact written, step bead still open |

**The layout problem these pose:** four of five share a title. The census must
carry state, evidence age, and worker in the row itself, because the title
distinguishes nothing.

### Evidence chains **[SYN]**

```
advancing        D 16:02  E 16:38  C 16:36  B 16:36  A —      broken_at: none
stalled          D 09:14  E 11:02  C —      B —      A —      broken_at: commit
stranded         D 08:00  E —      C —      B —      A —      broken_at: agent_active
defect signature D 14:10  E 15:55  C 15:51  B 15:51  A —      broken_at: step_closed
dormant          D —      E —      C —      B —      A —      broken_at: claimed
```

Note that `stalled` and `defect signature` differ only in whether C/B fired —
the whole diagnostic value is in those two cells.

---

## Convoys — the noise problem

**[OBS]** Member-count distribution in one rig:

```
0 members     27 convoys      ← convoys with nothing in them
1 member     546 convoys      ← 80%
2 members     40
3–8 members  ~66
```

**[OBS]** Real examples, one per kind:

| Id | Title | Members |
|---|---|---|
| `as-g6864` | agent-skills-census-audit-3 | 2/5 closed |
| `as-2p7` | sling-as-pio | 0/1 |
| `as-790z` | input convoy for as-9oj9 | 0/1 |
| `as-fket` | drain unit 1 for as-zykg | 1/1 |

**~680 convoys, of which roughly 10% have more than one member.** An unfiltered
list is 600 rows of machine-generated single-member convoys.

**This is a population fact, not a semantic one.** All four rows are convoys in
exactly the same sense — gascity's sense. They differ in what someone created
them *for*, which is not an attribute the API should invent an enum for. The
dashboard filters on `member_count` and leaves the definition alone.

---

## Epics — the contrast case

**[OBS]** **8 open epics, city-wide. All eight read like goals:**

```
gsp-1nwt8  P1  manifest-triage-filter — KILL/DISPATCH/BRIEF classification layer
gsp-7pwq   P1  Reconcile ~/gt/gascity-packs -> ~/repos: land brief-path HQ fix
gsp-bct8k  P1  [synthesis] mathcity routing architecture: deterministic-first…
as-npcp    P2  Lean proof-assistant skill toolbox
gsp-6txvfg P2  Create vertical planning formula family
gsp-atev   P2  [proof-assist] Consolidate + rework automated-proofs work…
gsp-ez3x6  P2  formula-creator-math: skill + formula + 4 gap formulas
gsp-fby    P2  F2 — LaTeX merge (merge-latex-sections SKILL + mol-latex-merge)
```

**Epics are a browsable list of eight. Convoys are 680 rows of mostly noise.**
Same nominal "grouping object," completely different UI treatment. Epics get a
plain list; convoys need filtering to be usable at all.

Note the title conventions — bracketed prefixes (`[synthesis]`,
`[proof-assist]`), em-dashes, embedded paths. Real titles are long and
unglamorous.

---

## Worktrees

**[OBS]** 14 orphaned worktrees under `~/gt/hecke/`, **six at 13 GB each,
119.7 GB total**. `git worktree list` has **zero overlap** with them — git no
longer knows they exist.

```
he-kotqf    he-timtb (×2)   he-2led5k (×2)   he-0t4ndn   he-72i1se
he-7uewko   he-aup02z       he-f610ir        he-manv0r   he-mvcf14
he-ncpdl8   he-wdw0u        he-x315y
```

Two of these ids appear **twice with different parents** — the id alone is not
unique, so the row key must be the path.

**[SYN]** Ownership — `created_by` and `step` do not exist today:

```
PATH        BRANCH           BY       STEP        LAST     SIZE   FLAGS
he-kotqf    polecat/he-kot…  creek    implement   14d      13 GB  orphan, unregistered
he-timtb    polecat/he-tim…  brad-2   implement    9d      13 GB  orphan, unregistered
he-x315y    polecat/he-x31…  —        —           31d     240 MB  orphan, unregistered
```

**`—` in `BY` is a real and expected value**: ownership was never recorded. The
column must render "unknown" distinctly from "nobody," and this is exactly the
absence-is-data rule.

**Scale note:** a 13 GB row and a 240 MB row in the same table. Size formatting
has to span four orders of magnitude.

---

## Diagnostics — the skew

**[OBS]** On the brief corpus:

```
7 actionable      ·      634 under review
                         MBRF021 ×400   MBRF004 ×158   MBRF005 ×76
```

**Benign findings outnumber real ones ~90:1.** If the under-review region is
styled like a problem list, the operator tries to fix 634 things that are fine.
The split must be structural, not a filter you remember to apply.

**[OBS]** Real diagnostic shape:

```
code           MBRF004
severity       ERROR
message        Brief bead has no source dependency.
policy_ref     B2.1
module         briefs.py
actionable     false
```

**[OBS]** Escalations currently live — the **same** MEDIUM repeated five times:

```
gt-wisp-kwirc   gt-wisp-073ht   gt-wisp-b9nns   gt-wisp-99be7   gt-wisp-ub9f9
[ESCALATION: Reaper anomalies detected [MEDIUM]]
gascity_packs: stale inactive workflow issue root query failed …
WITH RECURSIVE workflow_issue_root_candidates_base(id) AS (…
```

Design points: escalation bodies contain **raw SQL with newlines** and need a
code block, not a table cell. Five identical escalations must **collapse to one
row with a count** — and a repeated MEDIUM is a real signal, so the count is the
information, not the noise.

---

## Flood condition **[OBS]**

```
supervisor PID 20711
  file descriptors   138,234 held
  of which           96,183 pinned to worktrees deleted hours ago
  trend              still climbing
  effect             gc status latency 3s → 92s
  survives           gc stop (daemon stays up by design)
```

This is the case `Resources.flood_conditions` exists for: a leak that surfaced
only as mysterious latency, discovered by hand. It should have been a first-class
alarm the moment the descriptor count crossed a threshold.

Latency swinging **3s → 92s** is also the range the health probe must render —
a fixed-width latency column will not do.

---

## Briefs — background volume only

The dashboard excludes brief adjudication, but brief *stages* appear on the work
spine, so the volume matters.

**[OBS]** 200 briefs across 16 rigs; only 5 rigs have any.
`pending 114 · malformed 76 · adjudicated 10`. Per rig:
`hecke 114 · gascity-packs 69 · gascity 11 · agent_skills 5 · differential_valuations 1`.

**[OBS]** A real title, for width calibration:

> `[onboarding-decision] gamma0-aia-s27: authorize in-session live repair on aia-s27 (66 del, 172 rename, 7 recompute)`

**"Malformed" means closed with no verdict field — not damaged.** The caveat
belongs inline, adjacent to the number.

---

## Canaries **[SYN]**

Cadences are **[OBS]** from the order definitions; last-fired times are invented.

```
CANARY                EXPECTED   LAST      STATE
stuck-bead-watch      90s        47s ago   ok
orphan-sweep          5m         3m ago    ok
reclaim-stale-leases  5m         4m ago    ok
tail-end-detector     15m        4h ago    OVERDUE ×16
brief-review-patrol   30m        12m ago   ok
```

One overdue canary among five is the intended default look — enough green that
the red is legible.

**Order firing volume [OBS-derived]:** ~2,400/day city-wide before any real work
(stuck-bead-watch ~960, orphan-sweep and stale-lease ~288 each, tail-end ~96,
review patrol ~768 across 16 rigs). **This is why chatter defaults off.**

---

## Rig fixture set

Five rigs covering every state the layout must handle:

| Rig | State | Molecules | Worktrees | Beads | Why included |
|---|---|---|---|---|---|
| `gascity_packs` **[OBS]** | active | 45 open | ~30 | 3,923 open | The dominant rig — worst-case density |
| `hecke` **[OBS]** | active | ~11 | 19 (14 orphan, 119.7 GB) | 8 open | The disk problem |
| `agent_skills` **[OBS]** | active | few | few | 139 open | Middle case |
| `da_pub` **[OBS]** | registered | 0 | 0 | 0 | **Empty — must still render** |
| `lmfdb` **[SYN]** | degraded | unknown | unknown | unknown | **Named row with a reason, never omitted** |

The degraded row is the one most likely to be designed away, and it is the one
that matters most: *never collapse a degraded rig into a smaller total.*

---

## Values that must render

A checklist of the awkward cases, all drawn from above:

- **45 rows with identical titles** and identical priority
- **`—` for unknown ownership**, distinct from "nobody"
- **13 GB beside 240 MB** in one column
- **3,923 open beads** beside **0 open beads**
- **Latency 223 ms**, and the same field at **92 s**
- **Exit code 2** — healthy-but-quarantined, neither up nor down
- **Five identical escalations** collapsing to one row with a count
- **Raw SQL with newlines** inside an escalation body
- **A 120-character brief title**
- **Three empty rigs** that must still appear
- **One degraded rig** with unknown counts and a stated reason
- **634 benign findings** structurally separated from **7 real ones**
