# Premise-testing pass over the pending brief pile — 2026-09-26

Produced by `derive-verdict` (QUIMBY 75, fanned out to six read-only workers,
shard records in [`2026-09-26/`](./2026-09-26/)). **This is a derivation record,
not a set of recorded verdicts.** ADR 0006 is `Status: Proposed`, so nothing here
was written to a bead as a verdict. Follows the 2026-09-25 pass
([`2026-09-25-brief-pile-derivation-pass.md`](./2026-09-25-brief-pile-derivation-pass.md)),
which derived 5 of 218 by policy-keyword reading.

## Method

The 2026-09-25 pass found that keyword matching reaches the *location* half of a
question and not its substance. This pass instead **measured each brief's
load-bearing premise against current state** (bead status, refs, source at HEAD,
running processes) and classified on the result. Only Adopted, non-PROPOSED,
non-JUDGEMENT rules were cited; every quote was re-verified by `grep -n -F`.

## Coverage

213 briefs = 212 pending canonical brief beads not handled on 09-25, plus
`mc-viw9l` (QUIMBY 75 directly). Verified: every id in the input list has exactly
one section across the six shards, no id twice.

| Outcome | Count | Leaves Taylor's queue? |
|---|---|---|
| MOOT — premise measurably dead / action already done | 40 | yes |
| DERIVED — an Adopted rule leaves one option | 1 | yes |
| DERIVED-OUT — pure routing/sequencing (standing instruction, not policy) | 6 | yes |
| DUPLICATE — another pending brief asks the same decision | 17 | yes (survivor stays) |
| REFUSED (contested 3 · judgement 1 · stop-gate 2) | 6 | goes to Taylor **as a refusal** |
| UNDETERMINED — genuine human decision | 143 | yes, it is his |

**64 of 213 need no human decision.** One (`gt-o6e12s`) is counted MOOT in its
options but is re-routed as an escalation (below).

## The one policy derivation

**`mc-snxym` — DERIVED from B2.16** (`subdomains/brief-system/POLICY.md:606`,
Adopted, re-verified by QUIMBY 75): *"a mechanical failure MUST NOT remove the
brief from any pile, index, queue, view, or presentation surface"* and the fail
clause *"…or strands it where nothing reads it"*. Kills the `.rejected/`
status quo and leave-in-place. Survivor: flag-in-place (A) + the restore half of D.
B2.16 predates the brief by ten days — a PP1.10 surfacing.

B2.16 also settles **half** of `gt-024lxi`, `gt-xd161g` (rejected-on-form briefs
must come back) and `mc-zp1fs` (kills D); CT3.1 kills option C of `mc-lw18s`;
P6.2 kills B and D of `gt-myrjav`. Those stay UNDETERMINED on their other half.

## Escalations surfaced by the pass (not decisions)

1. **`gt-o6e12s` — possible data loss.** The salvage bundle
   `gascity-hq-strays-2026-09-06.bundle` (only copy of 7 refs deleted from
   `tdupu/gascity-dolt`) is not found anywhere under `~` or `/private/tmp`
   (re-verified by QUIMBY 75: `mdfind` + `find` → nothing). Box uptime 35 min;
   the Sep-6 scratchpad it lived in is presumed wiped. Needs an off-box recovery
   check, not a destination choice.
2. **`mol-dog-stale-db.formula.toml:111` still runs `rm -rf` inside
   `~/gt/.dolt-data`** (test-prefix globs). Present in `~/gt/.beads/formulas/`
   **and 17 rig formula dirs** (re-verified). The three briefs about it
   (`gt-25ep8l` + dups) name only `~/gt`.

## Non-UNDETERMINED results

| id | outcome |
|---|---|
| mc-snxym | DERIVED (B2.16) |
| he-9g84vd, mc-31b8c, mc-sw2a7, mc-vynt6, gsp-3h3uit, mc-aoasm | DERIVED-OUT |
| mc-uwyhb→mc-7fwku · mc-897zw→mc-9cr72 · mc-xlcqm→mc-p21l9 · he-xucfdq→he-8oku2r · gsp-pqtyvl→gs-b9ja · lm-0ggn→gs-b9ja · gsp-ga5gbh→gsp-e8dlmf · gt-k888o0→gt-25ep8l · gt-w126z9→gt-25ep8l · gt-1mgmgq→gt-624ew1 · gt-d8ljdq→gt-fbucam · gt-ftq6wn→gt-pnq9im · lm-m9oo→lm-ckhb · mc-027dz→mc-jq637 · mc-19zky→mc-nq1cn · mc-b02eq→mc-v7rhw · mc-tj7sy→mc-y9reo | DUPLICATE (→ survivor) |
| mc-viw9l, gsp-2m3auw, gsp-5daxgf, gsp-izal2t, gsp-qtzu92, gt-n9271k, gt-0sm9im, gt-5cls5j, gt-kzca38, gt-nbh1qv, gt-y650td, gt-1tytnk, gt-8tdj5a, gt-hgwu3m, he-8yn93f, he-bphri0, he-brzl49, he-equ713, he-inh88z, he-iqh4a9, he-ltvno1, he-sojlhr, he-x9xi5p, mc-2ju8s, mc-370v3, mc-55dlr, mc-7xn6p, mc-anjnx, mc-dbhgm, mc-f6a2e, mc-izq9q, mc-pmrjc, mc-t6phs, mc-t8zeo, mc-vtru8, mc-yskk8, mc-up5vd (residual), mc-kevm0 (partial), mc-aj15r | MOOT |
| gt-9c29t5, gt-ycps03, mc-nhz1n | REFUSED_CONTESTED |
| mc-kqmj1 | REFUSED_JUDGEMENT |
| mc-1h6r4, mc-vmcc5 | REFUSED_STOP_GATE |

`gt-ycps03` is the keystone refusal: CT2.5 read literally leaves one option, but
its session-ID premise is disputed on `gt-m50xwa`. One ruling on worker-identity
spelling would unblock it and the claim-identity cluster
(`mc-7fwku`, `mc-cns3c`, `mc-p21l9`, `gs-b9ja`).

## Stale premises inside UNDETERMINED briefs

Roughly 30 UNDETERMINED briefs carry at least one premise measured false today
(e.g. `gsp-27atpf` — source says `gc mail send` exits 1, not 0; `mc-o11rc` —
"option A shipped" is false for main; `mc-3fzhb` — `GC_HOOK_CLAIM_WINDOW` exists;
`gt-pnq9im` — the archiver exists). Each is listed in its shard record. **Refresh
the premise before presenting** — a brief whose premise is false is not ready.

## Corrections to this pass's own workers (QUIMBY 75)

- mc0 worker: "gate commits 680dfdb and cc900bc are on no ref" — **false**; held by
  `refs/salvage/mc-2juir` and `refs/salvage/mc-4eqs0`.
- Two workers ran `git fetch -q` in `~/repos/mathcity` (remote-tracking refs only;
  inside LP1's fence). Recorded, not repeated.
- Four hecke branches (he-brzl49, he-equ713, he-sojlhr, he-x9xi5p) were deleted
  after the 2026-09-19 anchoring; tips survive on salvage refs; deleting
  authority not traced.

## Honest scope

Policy settled **1** brief outright. Measurement settled 63 more. The policy set
still does not reach the substance of the pile — the 09-25 conclusion stands, now
with a sharper number: of 213, one is policy-derivable, 143 are genuine decisions.

[autogenerated by Claude Opus 5.5 (Claude Code) on 2026-09-26]
