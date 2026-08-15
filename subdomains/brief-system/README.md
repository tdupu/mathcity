# The Brief System — a walkthrough for mathematicians

Parent: [../../README-subdomains.md](../../README-subdomains.md)

This document explains, in plain language, the decision pipeline a human operator uses
to review work produced by AI agents. It assumes zero prior knowledge of Gas
City, beads, or any of the local tooling. The formal rulebook is
[POLICY.md](./POLICY.md) in this directory; this README is the guided tour.
(A glossary of jargon is at the bottom — consult it freely.)

---

## What this system is

Agents (automated workers) constantly produce artifacts: code branches,
computations, LaTeX edits, cleanup proposals. Every artifact eventually needs
a human decision — merge it? reject it? redo it? The human adjudicator has
limited attention; the brief system is the queue that rations it.

The central object is a **brief**: a structured presentation of exactly one
decision ("What is being decided" always comes first), with the evidence,
alternatives, and risks assembled in advance so the decision takes seconds,
not a research session.

**Decisions-as-beads, the one-bead model.** Everything here is tracked in an
issue database whose records are called *beads* (think: numbered index cards
with links between them, like `he-x8dk`). A brief **is** a bead of type
`decision`. It is in exactly one of two states — *adjudicated* (a verdict is
recorded on it and it is closed) or *not adjudicated* (still open, waiting).
The markdown file you actually read is only a **presentation artifact** — a
printout. The bead is the mathematical object; the file is a rendering of it.

Why this design?

- **Minimal bead bloat.** There is no separate "decision record" bead
  attached to each brief; the verdict is written onto the brief bead itself
  and the bead is closed. One object per decision, not two.
- **Decisions are queryable forever.** Every human verdict
  is a closed `decision` bead with verdict, rationale, authorizer, and date —
  searchable with one command, years later.
- **The bead store is canonical; files are cache** (rule B2.8). Any
  directory of brief files can be regenerated from the beads. If they
  disagree, the beads win.

---

## How work is launched

A brief always decides the fate of some **source** — another bead or set of
beads describing actual work. Sources come into existence several ways:

- **By hand:** `bd create --type=task --title "Merge branch feat/he-wzn"`
  creates a bead directly.
- **The handoff-bead skill:** an interactive session packages its findings
  into a structured bead for later dispatch.
- **`gc sling`:** the command that throws a unit of work at an agent — this
  can create and assign the bead in one step.
- **Order triggers:** standing automation. For example, when an agent closes
  a bead labeled `needs-decision`, the `on-merge-brief-record` order
  automatically starts a brief for it.

Once a source exists, the **brief-prep** formula (a scripted multi-step
recipe an agent follows) turns it into a brief:

1. stage a draft under `.beads/briefs/.staging/<slug>/`,
2. write the brief with the decision at the top (seven sections: decision →
   recommendation → assumptions → alternatives → risks → evidence → gates),
3. attach evidence for every **gate** — the 17 named checkpoints G1–G16 +
   G5b (test evidence, external critical review, LaTeX correctness, etc.,
   defined in POLICY.md and machine-wired in
   `mathcity/assets/brief-pipeline/gates.toml`),
4. pass an external critical review, and
5. deposit the finished brief into the **pile**.

Concretely:

```bash
gc sling hecke/gc.run-operator brief-prep --formula \
  --var source=he-x8dk --var brief_slug=he-x8dk-merge
```

---

## Mechanism status (settled as of 2026-07-16)

The brief system can publish work via several mechanisms. As of 2026-07-16
the architecture is settled:

| ID | Status | Description |
|---|---|---|
| **D2** | PRIMARY (proven) | Build-basic-briefed convoy: the terminal slot runs brief-prep SKILL, depositing the brief in the pile. The briefed publish slot **never pushes, never opens a PR, never merges**; an APPROVE verdict edge gates shipping via brief-decision-dispatch → gc.publisher. |
| **B** | MANUAL COMPLEMENT | Human-initiated publish: an operator runs a formula manually or uses `gc sling` directly. Remains valid; used for off-cycle or emergency publishes. |
| **A** | DEAD | Structural race (bead `gsp-510c`): the original auto-publish-on-close path had a race between the work-close event and the merge gate check. Abandoned in favour of the briefed path. |
| **D1** | DEFERRED | P1.2 city.toml tension: the direct-to-merge-queue mechanism conflicts with the pack portability constraint in P1.2. Deferred pending a policy ruling. |

**Proven E2E chain (D2, confirmed 2026-07-16):**

```
source bead → build-basic-briefed convoy → terminal slot: brief-prep SKILL
  → catch-no-brainer → .pile → brief-shuffle promotes → stack
  → present-briefs + adjudicate-brief → APPROVE verdict
  → brief-decision-dispatch → gc.publisher → real publish
```

Decision-only briefs use the same intake. `decisions-to-briefs` writes new
decision briefs into `.beads/briefs/.pile` with `brief_kind=decision`,
`gate_profile=decision`, no-brainer classifier evidence, and
`feedback_sink=brief_quality_failure`. The old `.beads/decisions-track`
directory is preserved as legacy/migration input and as an audit trail; it is
not the normal presentation queue.

---

## Where it goes: pile → shuffle → stack

- **The pile** (`.beads/briefs/.pile/`) is the single accumulation point for
  briefs that are written but not yet vetted. Canonically the pile is a bead
  query — "all open `decision` beads not under an active defer" — and the
  directory is its cache. Artifact briefs, decision-only briefs,
  lost-bead-filter briefs, and producer-repair briefs all enter here.
- **The shuffle** is the gatekeeper. A background order
  (`brief-shuffle-pile`) notices a non-empty pile and runs the
  `brief-shuffle` formula: take one brief, check every required gate against
  the registry, and either **promote** it or **reject** it (rejects go to
  `.pile/.rejected/` with a reason; nothing is silently dropped). The shuffle
  is the *single writer* to the stack — producers may never skip it. Source
  differences are expressed with `brief_kind` and `gate_profile`, not with
  separate presentation lanes.
- **The stack** (`.beads/briefs/stack/`) holds gate-clean briefs awaiting
  human adjudication, indexed in `stack/.index.jsonl`. Ordering is by **unlock count**:
  the number of downstream beads that adjudicating this brief would unblock,
  computed from the dependency graph — largest first. The idea: human
  attention is the scarce resource, so spend it where one verdict releases
  the most stalled work. Ties break by priority, then age.

Every source uses the same source contract before promotion: a typed
`gate_profile`, no-brainer classifier evidence, and a declared
`feedback_sink`. Rejects from any source record `brief_quality_failure.v1`;
producer-origin rejects also retain the legacy producer-failure cache for
compatibility.

Presentation then drains the stack (next section).

---

## How one adjudicates

**Reading the stack.** Two routes:

- The **present-briefs** skill, run by the outside clerk (or Mayor), drains
  pending briefs from the unified stack: trivial "no-brainer" items are
  collapsed into one-line `DECISION / CONTEXT / RECOMMEND / CONFIRM: y/n`
  entries, and full briefs are presented one at a time in their seven-section
  form. During the migration window, `present-briefs` may scan
  `.beads/decisions-track` only as an explicit legacy fallback and suppresses
  duplicates that already have a `legacy_source` mapping in the stack index.
  Presentation is human-facing and cannot be staffed by a gc order — there is
  no `brief-present-next` order; the outside clerk runs the skill.

- The **present-it** skill, interactively: say "present he-x8dk-merge" in a
  session and get the same decision-first dump in conversation.

**Recording a verdict.** Under the one-bead model, adjudication means writing
the verdict fields **onto the brief bead itself** — verdict, one-line
rationale, authorizer, date — and then **closing the bead**. That is the
whole canonical act. The `adjudicate-brief` skill (formerly `record-decision`)
does it, writes a redundant `.toml` record, and rings the `brief.decided`
event bell — which fires the machine cascade on the `mathcity.brief-operator`
pool. Invoke it as a skill in a session:

```
adjudicate-brief he-x8dk-merge --decision approve --reason "clean merge, tests green"
```

**The verdict vocabulary** (four words, three of which are final):

| Verdict | Meaning | Effect |
|---|---|---|
| **approve** | Do it. | Verdict recorded on the bead; bead closed; work proceeds. |
| **revise** | Fixable problems; here's what to fix. | Bead closed with the named defects; the fixed artifact returns later as a *new* brief. |
| **reject** | The approach itself is wrong. | Bead closed; a different approach needs a new brief. |
| **defer** | Ask me again in X days. | *Not* an adjudication — the bead stays open but hidden until the window expires. |

---

## What happens after

Recording a verdict rings the `brief.decided` bell, and two automatic
consumers act on it:

- **brief-decision-dispatch** executes the verdict:
  - *approve* → the source bead is pushed into the owning repository's merge
    queue (branch published, merge target set, reassigned to the merge
    agent);
  - *reject* / *revise* → a follow-up bead titled `[rejected] <slug>` or
    `[revise] <slug>` is created carrying the adjudicator's reason, so the feedback
    is actionable work, not a lost comment;
  - *defer* → no action beyond bookkeeping.

  Every action is logged to an append-only ledger
  (`decisions-dispatched.jsonl`), with bounded retries and escalation to a
  human if a dispatch can never succeed.
- **file-or-sendback routing** decides whether the decision spawns a
  follow-up brief (FILE) or simply archives (SEND-BACK).

The brief's markdown document is then archived under
`.beads/briefs/archive/`, and the **no-resurface guarantee** (rule B2.3)
applies: an adjudicated brief can *never* be presented again. If reality
changes later, the remedy is a new brief bead linking the old one — the old
verdict stands as history.

---

## When things circulate: the orders

An **order** is a standing rule of the form "when *trigger*, run *formula*."
The brief system's orders:

| Order | Trigger | What it does |
|---|---|---|
| `brief-shuffle-pile` | condition: pile non-empty | Vet and promote (or reject) one pile brief per run. |
| `brief-review-patrol` | every 30 min, per rig | Rescue briefs stuck at a pending external review; run the missing review or escalate. |
| `brief-watchdog-refill` | every 30 min | If the stack is below the low-water mark (2), commission up to 3 new brief-preps from ready source work; target depth 5. |
| `brief-watchdog-refill-on-stack-low` | event: `brief.stack-low` | Same refill, fired instantly when a decision empties the stack. |
| ~~`brief-present-next`~~ | ~~manual~~ | **RETIRED 2026-07-13 (P4.2 migration).** A gc order cannot staff a human presenter. Presentation is now the outside clerk's `present-briefs` skill. The `brief-present-next` FORMULA is kept. |
| `brief-decision-dispatch` | event: `brief.decided` | Execute the verdict (see previous section). |
| `post-decision-file-or-sendback` | event: `brief.decided` | Route follow-up briefing: FILE vs SEND-BACK. |
| `brief-archive-on-request` | event: `brief.archive_requested` | Archive a sent-back brief immediately. |
| `brief-archive-sweep` | every 24 h | Tidy decided/rejected artifacts into `archive/` (never deletes records). |
| `on-merge-brief-record` | event: bead closed, per rig | If the closed bead is labeled `needs-decision`, start a brief for it. |
| `no-brainer-process` | manual | Classify one candidate under the no-brainer shortcut policy. |

The design principle is "ring the bell": decisions emit events and consumers
wake immediately; the timed sweeps are backstops for lost events.

## Migration And Deployment Notes

Legacy `.beads/decisions-track` material is migrated copy-first. The inventory
tool records ready, deferred, terminal, malformed, missing-file, and
file-without-manifest cases before any behavior changes. Live unadjudicated
items get normalized printouts in `.beads/briefs/.pile`; terminal items remain
preserved and do not re-enter pile or stack.

BART deployment must verify the runtime source path before live migration. A
plain `git pull --ff-only` in `/Users/tdupuy/repos/mathcity` is sufficient only
when the live `gc` runtime resolves skills, formulas, assets, and tests
directly from that checkout. If the runtime resolves an installed pack under
`/Users/tdupuy/gt`, `~/.gc/cache`, or another materialized location, BART must
run the existing pack import/build/install step and verify the live-resolved
`present-briefs`, `decisions-to-briefs`, `gates.toml`, and policy-check files
match the merged source revision before running migration.

---

## How to check on work

```bash
bd show he-x8dk              # one bead in full (description, links, status)
bd list --type decision      # all brief/decision beads
bd search "merge feat"       # full-text search across beads
gc bd show he-x8dk           # same, via the city tooling
```

- **Dashboard:** <http://127.0.0.1:8372/city/gt/runs> shows live and recent
  formula runs.
- **Audit:** the `check-brief-policy` skill audits the live pipeline against
  every rule in POLICY.md and reports approve / revise / defer with specific
  violations.
- **Policy amendment:** to add or amend a brief-system rule, invoke the
  `new-brief-policy` skill. It is the sole write path for changes to POLICY.md
  (PP1.4) — editing POLICY.md directly without going through this skill is a
  policy violation.
- **Decision backlog:** the `decisions-to-briefs` skill converts pending
  decisions from conversation, a running list, or a durable decision inbox into
  adjudicable brief artifacts.
- **Remember:** the bead store is canonical. The directories under
  `.beads/briefs/` (pile, stack, archive — layout in
  `mathcity/assets/brief-pipeline/paths.toml`) are a regenerable cache; if a
  file and a bead disagree, trust the bead (B2.8).

---

## A worked example, end to end

Suppose an agent finished a branch `feat/he-wzn` and you want it reviewed.

```bash
# 1. Launch: a source bead exists (or create one).
bd create --type=task --title "Merge feat/he-wzn: FD side-pairing fix"
#    -> created he-q7r2

# 2. Brief-prep: produce the gated brief and deposit it in the pile.
gc sling hecke/gc.run-operator brief-prep --formula \
  --var source=he-q7r2 --var brief_slug=he-q7r2-merge

# 3. Shuffle: happens automatically (brief-shuffle-pile order fires on a
#    non-empty pile). Check the outcome:
ls <city-root>/.beads/briefs/stack/          # promoted
ls <city-root>/.beads/briefs/.pile/.rejected # or rejected, with reasons

# 4. Present: drain the stack. The outside clerk (or Mayor) runs the
#    present-briefs skill — presentation is human-facing, not a gc order.
present-briefs
#    ...the human adjudicator reads the seven sections and says: approve.

# 5. Record the verdict ON the brief bead and close it, via the
#    adjudicate-brief skill (formerly record-decision). It rings
#    brief.decided and fires the machine cascade on mathcity.brief-operator.
adjudicate-brief he-q7r2-merge --decision approve \
  --reason "side-pairing fix verified, tests green"

# 6. Dispatch: automatic (brief.decided event). The source bead he-q7r2 is
#    reassigned to the merge queue; the brief document is archived.
bd show he-q7r2      # watch it move through the merge lane
```

Steps 3 and 6 involve no human at all; steps 4–5 are the only places
human adjudication time is spent.

---

## Glossary

| Term | One-liner |
|---|---|
| **bead** | A record in the local issue database — a numbered index card (`he-x8dk`) with typed links to other cards. |
| **brief** | A bead of type `decision`: one question about one artifact, with pre-assembled evidence. The `.md` file is just its printout. |
| **gate** | A named checkpoint (G1–G16, G5b) a brief must satisfy with evidence or an explicit N/A — e.g. "tests actually ran," "an external reviewer looked." |
| **pile** | Where finished-but-unvetted briefs accumulate; canonically a bead query, cached as a directory. |
| **stack** | The vetted, presentation-ready queue, ordered by unlock count (biggest unblock first). |
| **adjudication** | A human adjudicator (or authorized automation) rendering a verdict: recorded on the brief bead, bead closed, never resurfaces. |
| **rig** | One managed repository inside the city (for example, a research project), with its own beads. |
| **sling** | To throw a unit of work at an agent: `gc sling <rig>/<agent> <formula> --formula --var k=v`. |
| **formula** | A scripted multi-step recipe (a TOML file) that an agent executes — the brief system's formulas live in `mathcity/formulas/brief-*.toml`. |
| **order** | A standing rule "when trigger, run formula" — the automation that keeps briefs circulating without anyone remembering to. |
| **convoy** | A group of related beads shipped and tracked together; it lands only when every member is closed. |

---

## Current status (honesty section, 2026-07-13)

This system is newly assembled from adopted policy plus formulas; parts have
not yet carried live traffic. Known state:

- **Shuffle empty-pile deadlock fix in flight** (bead `gsp-3al3`): when the
  pile is empty the shuffle formula's step graph deadlocks (a step closes
  "no-changes" but its successor blocks), stranding a lock and a worker per
  run. Priority-bumped; fix in progress. Related: a global-vs-rig-relative
  path split (`~/.gc/mathcity/briefs` vs `.beads/briefs`) awaits one ruling.
- **Presentation runs only through the interactive `present-briefs` skill** —
  the retired `brief-present-next` order never staffed a presenter, and all
  presentation to date has gone through the interactive skills.
- **`brief-decision-dispatch` has never run** — no verdict has yet flowed
  through the automatic approve/reject/revise executor.
- **T4 confirmed (2026-07-16, gsp-7x9f):** a live build-basic-briefed convoy fired an APPROVED decision brief at the terminal slot (gc.publish_mode=brief, no push/PR). The full chain source → convoy → pile → shuffle → stack → present → adjudicate → dispatch is now proven end-to-end.
- **Legacy backfill running** (bead `he-irjq9`): 46 pre-existing open brief
  beads, 10 stack documents, and a 318-line verdict ledger are being
  reconciled into the adopted system (verdict backfill onto beads, document
  repair, manifest resort).

For the scheduling-theory analysis behind the pile ordering (weighted age,
attention-cost denominators, starvation floors) and the no-brainer breakeven
mathematics, see this file's git history (versions prior to 2026-07-13).
