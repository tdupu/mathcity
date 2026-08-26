# Open Threads — the coordinator's checklist

> **Running document, lumby (coordinator).** Companion to
> [SURFACE-STATUS.md](./SURFACE-STATUS.md), which is the Mayor's per-tool census.
> **This file is per-THREAD: what is open, who holds it, what was decided, and what
> it changes.** Started 2026-08-23 after the thread count passed twenty and a single
> conversation stopped being able to hold it.
>
> **Ownership:** this file is lumby's. `SURFACE-STATUS.md` §1/§2 are QUIMBY's, §3 is
> lumby's. Same split, one reason: so two writers cannot collide.
>
> **Rule:** a thread leaves this file only by being CLOSED with a stated outcome, or by
> being explicitly STOPPED. A thread that goes quiet stays here.

---

## A. DECIDED — kept for the reason, not the status

| # | Thread | Decision | Where it lives |
|---|---|---|---|
| A1 | `decisions_to_briefs` auto-approves | **Decisions TO BE MADE become a hygienic brief deposited UNDECIDED to the pile; the no-brainer cycle answers it or promotes it to the stack.** The tool should not approve at all. **The name was the bug** — "decisions to briefs" was built as *decisions already made*. **FIX LANDED `99a1c24`** — but see **B2**: it closed the hole and did not open a drain. | **#194** comment · `99a1c24` |
| A2 | "`mathcity/gc.run-operator` does not exist" | **Malformed.** A pool always exists; it can be empty. The account is **#99** — `poolDesired` keys on IN-FLIGHT work plus a static floor, so a ready backlog exerts zero upward pressure. mathcity: ready work, zero in-flight, no floor → computes zero. | **#180** comment (correction), **#99** |
| A3 | The finalize deadlock | **Fix the formulas.** Not the retry classifier (that is `gc`-layer, upstream). | **#189** |
| A4 | Pool fixes of the workaround class | **Struck.** Repo owner: *"We don't want to do workarounds."* Disposes of the class, not two instances. | stripes' handoff, amended |

**Retracted causes — do not re-derive:**
- **"pinned import 26 days older than the fix"** — refuted by bob 15:06; the `named_session` fix is present in both gascity-packs trees. **Not a cause at all.**
- **"the deadlock is starving the control plane"** — refuted by cozy; see B1. **Arrow was backwards.**

---

## B. THE LIVE FINDING — measured today, changes what the decisions cover

### B1. The control plane has been dead since 2026-08-07, and #189 is a SECOND failure on top of it

```
LAST dispatcher bead CREATED   2026-08-07
LAST dispatcher bead CLOSED    2026-08-07
#189 retries BEGAN             2026-08-15
```

**`[measured]` by cozy** (`created_by == 'hecke--core__control-dispatcher'`), **date
independently corroborated by lumby** with a capped instrument — counts from cozy's,
which is uncapped.

**432–494 open dispatcher beads, every one created on or before 08-07.**

**The ordering argument, in the form that survives without its author:** *the retries
cannot have caused a silence that preceded them by eight days.*

**What it does to A3:** fixing the formulas prevents NEW deadlocks and leaves 494 open
beads, 76,961 retries, and a dead control plane untouched. **The ruling is still sound on
its own merits; it just does not address the outage.**

**Explains thread D3** (`he-8d6gsg` never claimed): it is routed to
`hecke/core.control-dispatcher`, which has done nothing for sixteen days.

**`[inferred]`, NOT investigated, deliberately:** why it stopped on 08-07. cozy is holding;
**this is a decision, not a hunch — it needs an owner or an explicit stop.**

### B2. The no-brainer cycle CANNOT FIRE ON ITS OWN — #194 is half a fix

**`[measured]` by stripes, 2026-08-23, from the order DEFINITIONS in
`gascity-packs/mathcity/orders/` (18 files) — NOT from `orders_status`, which could not answer.**

```
trigger census, all 18 mathcity orders
  7  event
  6  cooldown
  3  condition
  2  manual        <- BOTH are the no-brainer orders, and NOTHING ELSE is manual

no-brainer-process            formula = no-brainer-classify           trigger = MANUAL
no-brainer-candidate-curate   formula = no-brainer-candidate-curate   trigger = MANUAL
```

> **"This is not 'the city does not schedule things.' It schedules 16 of 18. The two that
> classify briefs are precisely the two that do not."**

**This is the missing ARROW in the repo owner's #194 model.** The model has four nodes —
pile → no-brainer cycle → worthy → stack — and **the triage stage has no trigger.**

**The author of the #194 fix predicted this about their own work before it was measured:**

> *"Fixing #194 alone moves briefs from silently auto-approved to silently piling up."*

**Confirmed, not predicted:** `mc-60j` has sat in mathcity's `.pile` since 02:31 — fourteen
hours — with `brief-operator` workers alive and no order to wake them.

**THE POOL IS NOT THE GAP.** Both orders route to `mathcity.brief-operator`, which exists and is
staffed. **The trigger is the gap.**

**Instrument note, and it matters:** `orders_status` IS registered on the typed surface and was
NOT used — `gc order list` measured 89 s the night before and a partial or timed-out read would
have proved nothing. **The measurement was taken a different way and labelled as such, rather
than reported as `0` or worked around.**

**Consequence if unfixed:** every rig pile is a dead-letter queue. **The commission chain the
whole session has been building stops one step before the repo owner ever sees anything.**


### B3. The drain ALREADY EXISTS. What is missing is the EMISSION — and the deposit is in the place a prior decision rejected.

**Recorded 2026-08-23 16:55, after the repo owner said *"we went through this with the brief-shuffler
a couple QUIMBYs ago; there should be a record in the commits."* There is, and it overturns B2's
proposed fix and QUIMBY's Q3 conclusion.**

#### The event vocabulary is real and complete

```
brief.submitted                  ->  brief-shuffle-on-submit          rig
brief.decided                    ->  brief-decision-dispatch          city
brief.gate_rejected              ->  brief-producer-failure-record    city
brief.producer_failure_recorded  ->  brief-producer-failure-rollup    city
brief.archive_requested          ->  brief-archive-on-request         city
brief.stack-low                  ->  brief-watchdog-refill            city
```

**`brief.submitted` -> `brief-shuffle-on-submit` IS the trigger the owner described:** a brief
lands in the pile, an event fires, the shuffler runs it through the gates, and it is promoted or
rejected.

#### The gates are real and they REJECT

**`e6fe8a0` (2026-08-20):** when five long-stalled briefs finally drained, **all five were
REJECTED, not promoted** — brief 19 failed G9, briefs 20-22 were missing G5 Server-touching,
brief 23 had no Gate Evidence section. **Nothing deleted; each moved to `.pile/.rejected/<slug>/`
with a `rejection.json`.**

#### `[measured]` — what is actually missing

```
orders/brief-shuffle-on-submit.toml:3
  "`brief.submitted` is emitted by brief-prep's submit-to-pile step as soon as..."

mctl emits NO brief.* event.  Zero matches in mctl_core.
```

**The skill path emits. The typed path does not.** `decisions_to_briefs` deposits to the pile and
**rings no doorbell.**

#### AND THE DEPOSIT LOCATION WAS ALREADY DECIDED — against the rig pile

**`e6fe8a0`, verbatim:**

> *"Chose a city-scoped drain order over redirecting deposits into rig piles, on evidence: all 15
> rig stacks are EMPTY. The city root holds the only populated stack in the city — the same one
> `mctl briefs list`, `present-briefs` and the index repair all read... **Routing briefs into rig
> piles would have drained them into stacks no reader consumes, turning a stalled queue into a
> silently discarded one.**"*

**Same commit: *"every brief order is rig-scoped and none had ever fired on the city root — zero
`brief-*:rig:gt` events, ever."*** And `brief-shuffle-on-submit` is `scope = "rig"`.

**So `mc-60j` is not merely untriaged. It is in the location a prior decision rejected, waiting on
an event nothing emits, for an order that has never fired.**

#### What this RETRACTS

- **B2's implied fix — "schedule the two no-brainer orders" — is wrong.** The owner's design is an
  event trigger, not a cadence. The coordinator recommended `cooldown, interval 15m`; **withdrawn.**
- **QUIMBY's Q3 conclusion — "the no-brainer cycle has to be dispatched PER RIG" — is wrong**, and
  was decided against three days earlier with evidence.
- **The no-brainer cycle is not the first stage.** The shuffler gates come first; classification is
  downstream of promotion, not a substitute for it.

#### OPEN, and needed before this is a plan rather than a guess

1. ~~**Should `decisions_to_briefs` deposit to `hq`, or was the rig-scoped deposit deliberate?**~~
   **PARTLY ANSWERED, and the coordinator's reading was too broad.** **#58** records a design
   decision: *"storage is per-rig, reporting is city-wide."* `e6fe8a0` chose a **city-scoped
   DRAIN** — which is not the same as a city-scoped **DEPOSIT**, and the two are compatible.
   **So the rig-scoped deposit is likely correct.** What remains is whether the drain reaches it,
   which is question 2 and #202. **The deposit-location question belongs on #58, not here.**
2. **CAN mctl emit an event at all?** It emits none today. This may be a capability it does not
   have, in which case the fix is larger than a call-site change.


---

## C. OPEN — WITH THE REPO OWNER

| # | Thread | What is needed | Blocks |
|---|---|---|---|
| C1 | **B1 — the 08-07 outage** | Does it become its own issue? **Recommended: yes, before the formula fix.** cozy wants it and has the store loaded. | The real recovery of 494 beads |
| C2 | **#99 then #197 sequencing** | `#99` (sizing responds to demand) must land before `#197` (typed surface reads/sets it). **A `set_pool_size` over a `poolDesired` that ignores its input is #153 again.** | `#180`, and QUIMBY's ability to diagnose its own capacity |
| C3 | **#191 fail-loudly patch** | bob built and tested it. **User-scope tooling — not the mathcity repo.** | Nothing; 23 messages already lost |
| C4 | ~~**B2 — schedule the no-brainer orders**~~ **SUPERSEDED BY B3** | **The owner ruled: event trigger, not cadence — and the machinery already exists.** The remaining questions are B3's two: **deposit to `hq` or the rig pile?** and **can mctl emit an event at all?** | **The drain.** #194's fix deposits a brief and rings no doorbell |
| C5 | **WHICH running MCP servers serve `99a1c24`? — it is NOT binary** | **QUIMBY measured: *"live in 2 of 11 servers."*** So the fleet is **split**: two agents get the fixed `decisions_to_briefs`, **nine get the auto-approving one — and nothing tells either which they have.** That is worse than uniformly stale: uniformly stale is predictable. **Method not yet shared; requested from QUIMBY.** | Every agent calling the tool right now |
| C5-old | ~~Does a RUNNING MCP server serve `99a1c24`?~~ **REPLACED — the binary framing was wrong** | Unmeasured. Every MCP process predates the commit by definition. **#164's shape one layer up** — the dashboard was restarted after every merge today and the MCP never was. | Whether the #194 fix is live at all |

---

## D. OPEN — ROUTED OR ROUTABLE

| # | Thread | Holder | State |
|---|---|---|---|
| D1 | **#180** — one issue → claimable molecule | **bob** | **BLOCKED, not failed.** Steps 1–4 proven (`gh#1 → mc-7d0 → mc-60j → ready`). Step 5 has an empty pool. Held rather than spending the one dispatch — `cook` has no `--dry-run`. |
| D2 | **#179** — the reusable adapter | **pink** | Waits on D1 by pink's own argument: building both separately is #160 again. Intake design proceeds meanwhile. |
| D3 | **`he-8d6gsg`** — a finalize step never claimed, 7h+ | QUIMBY 49 | **Explained by B1.** Distinct from #189: not-claimed vs claimed-but-cannot-close. |
| D4 | **#99** — ready depth exerts zero pool pressure | **UNASSIGNED** | Filed in response to the owner's own question: *"We have no control over this in mathcity?"* Recommended owner: mutt. |
| D5 | **#197** — no typed surface sees or sizes a pool | **UNASSIGNED** | **Holds the two tools the owner named on #182** (`adjust_worker_pool`, `get_worker_pool_size`) which were lost when #182 closed on partial scope. |
| D6 | **#189** — formulas deadlock their own finalize | **lumby** (owner's ruling) | Needs an implementer. Blocked on: which three formulas, and whether the fix is uniform. **Asked QUIMBY 49; unanswered.** |
| D7 | **#191** — silent misdelivery | filed | **Undercounts victims** — see E2. |
| D8 | **#185** — make an existing issue hygienic | filed, unbuilt | The chain works on rough issues; this improves the output. |
| D9 | **Nine claim-window P0s are ONE defect** | brad + stick-dog, settled | `mctl work ready` **11 ms** vs `gc hook --help` **9,584 ms**. Two refuted by measurement. **NOT YET WRITTEN ONTO THE P0s** — that is the deliverable. |
| D10 | ~~**Three uncommitted `ISSUE_TEMPLATE` files**~~ **RESOLVED `d089109`, pushed 17:50** | lumby | Dirty since 03:26, five asks, no owner, nearly lost to a reflexive stash. **Resolved rather than asked a sixth time.** **+70 lines, almost entirely NEW REQUIRED GATES** — search open *and closed* issues AND PRs; confirm the capability is genuinely absent on current `origin/main`; check the policy/design corpus. **`create-issue` reads the live template BY DESIGN, so the skill was right and its input was a day behind.** **Measured cost: #202 and the #185 rewrite were both filed today against the stale form.** |
| D14 | **`#202` — mctl emits no `brief.*` event** | **FILED 17:0x, the durable capture of B3.** The skill path emits `brief.submitted`; **mctl emits zero events of any kind.** A brief deposited by the typed surface rings no doorbell. **Absence VERIFIED on `origin/main`; consequence NOT** — the issue says so. **Two checks could refute it:** `brief-shuffle-pile` (condition trigger) may already be the drain; and `e6fe8a0` records *zero `brief-*:rig:gt` events, ever* — an emission nothing routes equals no emission. **Unassigned.** |
| D13 | **SWEEP: every place a thing describes itself, checked against its safeguard comment** | **HELD, not declined** — **SCOPE WIDENED 16:38 by the D12 findings.** The pairing is not only *docstring above safeguard comment*. Check **all four per site**: Python docstring · **MCP ToolSpec `title`+`description`** · **`input_schema` field descriptions** · **the schema snapshot fixture** (carries copies of the above). *"A safeguard comment can be contradicted by any of them, and the caller-facing ones matter most because they are read first and by more readers."* **ORIGINALLY** — one thing at a time, D12 lands first. **cozy's generalisation from its own finding:** *"any comment-based safeguard sitting under a stale docstring is defeated by it."* Not specific to one function. **cozy owns it when D12 merges.** **SCOPE, so it is not re-derived:** the shape is **NOT** "stale docstring" — that is unbounded and mostly noise. It is **a docstring that CONTRADICTS a safeguard comment positioned below it**. *"A stale docstring is noise; this one argues for the regression the comment exists to prevent."* **Method: grep for inline `do not restore` / `do not change this` comments FIRST, then read the docstring above each one.** |
| D12b | **SIX wrong self-descriptions, not four — and the worst two are caller-facing** | `fix/d12-… @ 5e6782f`, cozy, **with trans, unreviewed.** **5th (trans):** ToolSpec `title`/`description` — *"File an already-made decision as a dispatchable brief."* **6th (cozy, found by reading the whole entry rather than the two lines quoted):** the `decision` **parameter description** — *"The decision, as made."* **It told the caller to supply a verdict.** Each carries BOTH errors: the *already-made* misreading AND the *dispatchable* contract `99a1c24` deleted. **The docstring is read by someone already editing the function; the ToolSpec is read by every caller before any code.** |
| D12 | **`99a1c24`'s docstring now contradicts its own code** — **MERGED LOCALLY at `6e84bdc`, NOT PUSHED, superseded by `5e6782f`** `fix/d12-decisions-to-briefs-docstring @ 6e84bdc`, author cozy, reviewer trans, 1225 passed, docstring-only. **FOUR false claims, not three** — the fourth was the opening line, *"One already-made decision → … can actually be dispatched"*, **which was the #194 misreading stated as the function's purpose.** | **cozy, reviewing:** the `_handle_decisions_to_briefs` docstring is unchanged by the commit and now false — *"the bar is `work_status` returning readiness 'ready'"* (contract deleted), *"composes two already-gated operations... then adjudicate"* (second half deleted). **It sits ABOVE the inline note the commit added to stop a reader restoring the block — so a reader who trusts the docstring restores exactly what was removed.** Not a blocker; behaviour and tests are right. **cozy owns the fix (its prose).** |
| D11 | **#98** — FD leak | filed | Signature recorded: 96% of handles into the repo; the count tracks a directory walk. Supervisor restarted; **fresh baseline at 17 FDs** — first clean measurement point all session. |

---

## E. INFRASTRUCTURE — the channel we all depend on

| # | Thread | State |
|---|---|---|
| E1 | **Live peer channel** (`SendMessage`/`ListAgents`) | **Working.** Confirmed both directions with stripes and cozy. **2 of 10 identities mapped:** `gt-22`=stripes, `gt-20`=cozy. |
| E2 | **#191 undercounts DISTINCT VICTIMS** | stripes and cozy found it independently: a **prefix collision** puts a stranger's mail in a folder wearing a known agent's name. *"An unmapped uuid makes an odd-looking folder; a colliding one makes a folder wearing the right agent's name."* |
| E3 | **The live channel cannot reach non-Claude agents** | cozy's warning. **A silent failure of the same class as #191, introduced by the fix for #191.** `codex-worker` is a real mathcity agent. **RULE: a peer absent from `ListAgents` is UNKNOWN, not gone.** File inbox stays live. |
| E5 | **#191, third mechanism: the name lookup is CWD-DEPENDENT** | **Reproduced twice, 90 s apart, same sender/recipient/map.** From a scratch dir → `inbox/aee956dd/` (prefix fallback, unread). From the city root → `inbox/finalize-agent/` (correct). **The base resolves correctly while the name does not** — right tree, wrong leaf, send reports success. **A perfectly correct map still misroutes on the caller's CWD.** Filed on #191. **RULE: run `agent-send.sh` from `~/gt`.** |
| E4 | **creek** | 9h silent. **lumby holds the ledger** (`~/Documents/misc/DOGFOOD-LEDGER.md`, 174 KB). |

---

## F. RELATION TO SURFACE-STATUS.md

**THREE files, three questions, one owner each:**

```
SURFACE-STATUS.md      PER-TOOL      "What works right now."             QUIMBY §1/§2, lumby §3
OPEN-THREADS.md        PER-THREAD    "What is open and who holds it."    lumby
PENDING-DECISIONS.md   PER-DECISION  "What Taylor must rule on."         QUIMBY
```

**A tool's defect appears in both, differently:** `SURFACE-STATUS.md` records *the tool is
BROKEN and why*; this file records *who is fixing it, what was decided, and what it blocks*.

**Pending against SURFACE-STATUS.md** — plan committed at `6449477`
(`docs/superpowers/plans/2026-08-23-surface-status-update.md`), **not applied**:

- **Six §1 rows are stale** (QUIMBY's to change, offered not imposed): `city_health` (#176/#159 merged), `briefs_create` (two of four defects closed), `commission_brief` (#190 merged), `work_dispatch` (exercised: exit 0 at 162.7 s against a 120 s bound), and **`briefs_adjudicate` has no row at all** though #155 merged.
- **§3 is lumby's to fill:** eight in-flight surfaces — the four #197 pool tools, the two #182 assign verbs (PAUSED on measured grounds), #185, and the commission adapter.
- **The file's header says it is maintained in `tdupu/mathcity` (`docs/`); it exists only city-side.** A ledger built to catch surfaces that do not match their documentation, not matching its own.

---

## G. STOPPED — filed, correctly not worked

`#152` `#168` `#175` `#178` `#85` `#148` `#196` `#99-adjacent scope creep` `#50` `#52` `#201`

**Stopped is not resolved.** Closing these would convert *"we chose not to do this"* into
*"this is fixed"* — the exact failure this tracker keeps catching.

---

## Changelog

- **2026-08-23 (lumby), 18:15 — GAP SWEEP against SURFACE-STATUS.md.** Four fixed: **#202 was in
  SURFACE-STATUS §3 and missing from this file entirely** — the per-thread document, which exists to
  stop work being lost, had lost its own newest issue (now **D14**). **B3 question 1 corrected** —
  #58 records *"storage is per-rig, reporting is city-wide"*, so `e6fe8a0`'s city-scoped DRAIN does
  not override a per-rig DEPOSIT; the coordinator's reading was too broad and the question moves to
  #58. **C5 reframed** — QUIMBY measured *"live in 2 of 11 servers"*, so MCP staleness is **not
  binary**; the fleet is split and nothing tells an agent which version it has. **D10 RESOLVED** at
  `d089109`.
- **2026-08-23 (lumby), 16:55 — B3 ADDED, and it retracts two conclusions.** The repo owner
  pointed at the brief-shuffler history; `e6fe8a0` (2026-08-20) contains the decision. **The drain
  already exists** — `brief.submitted` -> `brief-shuffle-on-submit` -> the gates, which demonstrably
  REJECT. **What is missing is the emission: mctl emits no `brief.*` event at all.** And the
  rig-pile deposit was explicitly rejected three days ago as *"a stalled queue turned into a
  silently discarded one."* **Retracted: the coordinator's `cooldown, 15m` recommendation, and
  QUIMBY's "dispatch the cycle per rig" conclusion.**
- **2026-08-23 (lumby), 16:45 — COORDINATOR DRIFT, named by the repo owner.** Between 16:20 and
  16:40 every agent reply became the next action. **The inbox monitor turned each arrival into an
  interrupt and all of them were treated as urgent.** Merged D12 without pushing; cozy had already
  superseded it. **C4 and C5 untouched the whole time — and C4 decides whether #194 functions at
  all.** The grilling stopped at Q4 of 17 and was never resumed. **Recorded because the pattern
  repeats: work in front of you is not the same as the work.** cozy named the identical error one
  level down in the same hour — *"I searched for the phrases you quoted, found four, and stopped...
  I checked the thing in front of me thoroughly and never checked whether it was the whole thing."*
- **2026-08-23 (lumby), 16:35** — `99a1c24` **REVIEWED AND APPROVED** by cozy (reviewer != author;
  1225 passed at that SHA, red/green independently reproduced). One finding recorded as **D12**:
  the docstring survived the commit and now contradicts it. Also corrected: the coordinator
  attributed an `mc-iqk -> mc-0da` reproduction to cozy; **cozy has no record of running it and
  declined the credit.** That trace was QUIMBY 49's. **The reviewer choice was still sound for a
  different reason — cozy authored the test being corrected.**
- **2026-08-23 (lumby), 16:30** — **#194 FIXED AND PUSHED (`99a1c24`)**: the fix is a deletion
  of `plan_adjudication(verdict="approve")` at `mcp_server.py:855-866`; `plan_create_brief` was
  always correct. Red/green re-run at the merge point, 1350 passed. **Added B2** — the
  no-brainer cycle cannot fire on its own (2 of 18 orders manual, and they are precisely the
  two that triage briefs), so #194 closed the hole without opening a drain. **Added C4** (the
  trigger decision) and **C5** (whether a running MCP serves the new code). **Added E5** — a
  third #191 mechanism, reproduced twice: a send from outside the city root resolves the inbox
  BASE correctly and the NAME incorrectly.
- **2026-08-23 (lumby)** — created. Twenty-one threads at creation: 4 decided, 1 live
  finding, 3 with the repo owner, 11 routed or routable, 4 infrastructure. Two causes
  recorded as RETRACTED so they are not re-derived.
