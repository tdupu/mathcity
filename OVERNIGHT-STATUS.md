# Brief Manager — overnight run, 2026-08-20

Branch `feat/brief-manager-overnight`, 11 commits, **683 tests passing**.
The dashboard is running from this worktree on <http://127.0.0.1:8480>.

**Not merged.** Merging is gated by `authorize-git-operation` and approval does
not carry across conversations, so the branch is ready and waiting for you
rather than landed while you slept.

---

## The headline

You could not adjudicate. Now you can — and the reason you couldn't was not
what either of us thought.

The verdict controls were disabled on every refused brief. I had built that
gate, and I built it wrong: I treated "the core will not vouch for this brief"
as a reason to forbid *all* verdicts, when it is only a reason to forbid
**approving** one. An empty, unlinked brief is precisely the brief you send
back, and its emptiness is the reason for the verdict rather than an obstacle
to recording it.

Fixing the panel exposed that the veto was enforced **twice** — the core's
`plan_adjudication` turns every ERROR-severity diagnostic into a blocking
precondition for any verdict at all. So the freed control returned HTTP 409.
An enabled button that fails is worse than a disabled one, so I fixed that
layer too.

Now: `approve` stays gated exactly as before. `revise` and `reject` are always
available. Verified end to end against the live city — the POST that returned
409 returns 200, with `MBRF004` present as an advisory and the verdict in the
plan.

---

## What changed

| | Before | After |
|---|---|---|
| Verdicts on a refused brief | all 4 disabled | approve gated; revise/reject live |
| No-brainer control | did not exist | checkbox + reason, recorded on the bead |
| Brief page load | 13.5s | ~5s |
| Stack table | 5 columns of em dashes | only columns with data |
| Brief page navigation | none | `brief N of M`, prev/next, back to queue |
| After recording a verdict | terminal page | Next brief → with count remaining |
| Disposition | "type an option letter" | the brief's own options + propose your own |
| Adjudication forms on the page | two, both writing the verdict | one |
| Keyboard | j/k/enter on the queue only | + n/p/q/a on the brief page |
| Empty briefs | retype the same verdict each time | one-click standing return, still confirmed |

**Performance.** Per-call timing showed three independent reads of 4–6s each,
run one after another. They were serialized by the transport, not by any
dependency — one stdio pipe cannot carry two conversations. They now overlap,
so the page costs one core read instead of three. The remaining floor is
core-side and is cozy's (GH #76).

**The em-dash wall** was my own rule being violated: `fields.py` says absent
fields do not render, yet the table drew five columns of nothing. Columns are
now chosen from the rows in hand, so a column returns on its own the moment the
core feeds it — no release, no flag. What was hidden is named beneath the table.

---

## What I decided not to do, and why

**I did not bulk-mark the title-less briefs revise + no-brainer**, though you
authorised that earlier.

`briefs_list` returns no `title` and no `bead_id` at top level — both are
`None` on every row. I twice computed a population statistic against that field
and got a confident, wrong answer (first "245 title-less", then a different
number from a different wrong shape). Writing verdicts to ~90 real beads on an
identification I had already botched twice, unattended, was the wrong risk.

The machinery is built and proven; it needs a set I trust. My suggestion is you
point me at the filter you mean and I run it in one pass while you watch.

**I did not merge to main** — see above.

---

## Handed to cozy

**GH #76** — the seven attribute fields, ordered by value, with per-field
acceptance criteria. `unlock_count` is the big one: it is the queue's sort key
and it is not emitted, so the queue is ordered by whatever the store returns.

I also told them I changed `effects.py`, which is their module, and offered to
back it out if they disagree with the call.

---

## Verified on real data

- **22/22 routes** return 200 in both rig and city scope.
- **Brief pages across 6 rigs** — hq, hecke, agent_skills render the full
  verdict set and the no-brainer control; three rigs have no briefs.
- **Honesty properties intact city-wide**: "All 17 registered rigs answered",
  per-rig artifact trust reported both ways, hidden columns named.
- **Live preview round trip**: 200, single-use token, `if_status` guard,
  no-brainer marker present in the recorded reason.

The one thing not exercised live is a real `apply` — the write path is covered
by fixture tests, and I did not want to mutate a real bead unattended.

---

## The standing return

You asked for the empty briefs to be marked revise + no-brainer and sent back
asking for fields. There are ~90. I did not batch them (see above), so instead
a brief with no body now offers **"Fill in the standing return →"**: the form
arrives with revise selected, no-brainer ticked and the reason written, and you
confirm each one. With `n` to advance, that is roughly two keystrokes per brief
rather than a paragraph of retyping — and every verdict still passes a human.

## Still open

- The queue's remaining template interactions: shuffle, pairwise ranking, bulk
  action bar, save-draft.
- Page load is ~5s, floor is core-side.
- The 41-file `artifact:` hand-repair worklist (unstarted, delivered earlier).
- Superseding the 18 vintage stuck beads.

---

## 09:25 — hourly check

**Tests green: 702 passing.** Dashboard healthy, `/queue` 200 in 4.6s.
Branch rebased onto `main` at `e6fe8a0` (cozy's pile-drain + index-rebuild
work); zero file overlap, clean rebase. **13 commits.**

### Landed since the last section

**The data emptiness was my bug, not a missing field.** cozy replied that
`unlock_count` is a read that exists on most files — and they were right.
`briefs_list` returns most attributes inside a `fields` provenance map, and the
table read only the top level. So `unlock_count` read as `None` on all 308 hq
rows while **185 carried a value**, and `priority` read as `None` while every
row had one.

My hide-empty-columns rule then compounded it: it measured a populated column
as empty, hid it, and printed a note claiming no brief carried a value for
fields the core had been serving all along. A read that knows one of two shapes
does not fail — it under-reports, confidently.

Fixed: `attr()` looks in both. **Unlock and Priority now render on the live
city; hidden columns dropped from five to three**, and the three remaining are
genuinely absent. The sort key had the same defect, so ordering by Unlock had
been ordering 308 identical `None`s.

Also landed: one adjudication form per page (the legacy form was a second,
weaker verdict control writing the same field).

### In flight

Nothing blocking. Replied to cozy retracting my "columns are empty" report,
accepting their three corrections (DRY RUN badge stays, `unlock_count` is a
read, revised `track`/`gates` figures), and narrowing my asks to two.

### Blocked / needs you

- **`title` and `bead_id` are absent from `briefs_list` rows** — only
  `brief_id` is populated. Now my top ask of cozy, above `unlock_count`.
- **Merge is still gated** and unrequested.
- **cozy has an unlanded `render.py` edit** to the degraded-rig panel; my
  branch touches that file too, so one of us rebases when it lands.

### 09:55 — the table has data now

Finishing the two-shape read across the rest of the screen brought back a third
column. `score()` is computed from `unlock_count` and `priority`, so it had been
scoring all 308 rows off two `None`s — Score looked like a field the core could
not feed when it was a field the dashboard could not read.

Live queue now draws **Brief, Rig, Unlock, Score, Age, Priority, Health** with
real values. Hidden columns: **5 → 2**, and the two left (Opts, Rec.) are
genuinely absent.

**Full path re-verified end to end on real data**, queue → brief → preview:
nav reads `brief 1 of 115`, two verdicts enabled (revise/reject) with approve
correctly gated, no-brainer control present, preview returns 200 with a live
token, `verdict: revise`, the `[no-brainer]` marker inside the recorded reason,
and the `if_status: open` staleness guard intact.

**15 commits, 702 tests passing.**
