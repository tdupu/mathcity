# Spike — what does the brief manifest uniquely provide that beads cannot?

**Asked by:** Taylor, via lumby — *"the manifest operation is totally fucked and needs to be completely reworked."*
**Answered by:** mutt (`e7c10e75`), stack/index integrity owner. **Pair:** cozy (`mctl` boundary).
**Type:** spike. The output is an answer and a recommendation, not code. lumby's instruction was to answer before designing.

---

## Verdict in one line

**Taylor is right that it is broken and wrong that it is unnecessary — but only three fields justify its existence, and the recommendation is SHRINK, not delete and not rebuild.**

---

## The measurement

Every field carried by `stack/.index.jsonl` (57 rows, 12 distinct fields), tested against the bead store's 15 structured keys (`id · title · description · status · issue_type · owner · priority · labels · notes · created_at · updated_at · created_by · comment_count · dependency_count · dependent_count`).

| index field | derivable from beads? | evidence |
|---|---|---|
| `slug` | **yes** | bead id / title |
| `created_at` | **yes** | `bead.created_at` |
| `unlock_count` | **yes** | `bead.dependent_count` — beads already compute exactly this |
| `source` | **probably** | producer identity; no structured field, but reconstructible from provenance |
| `path` | **no** | filesystem location. Beads have no path concept |
| `gate_profile` | **no** | no field, no label |
| `brief_kind` | **no** | `issue_type` is a different taxonomy |
| `defer_until` | **no** | no bead field for a defer date |
| `legacy_n` | **no** | migration record |
| `legacy_source` | **no** | migration record |
| `manifest_status` | **no** | status *of the cache* — self-referential |
| `migration_action` | **no** | migration record |

**8 of 12 are not derivable.** That number alone would say "keep it" — and it would be the wrong read.

### The correction that changes the answer

**My first pass counted `gate_profile` in 57 bead payloads and nearly concluded it was derivable.** It is not. `grep` was matching **prose inside `description`** — in the sampled bead, a sentence *about* gate profiles ("no PRODUCER formula declares a `gate_profile`…"), not a brief's value. Structured-key check: `'gate_profile' in bead` → **False**. Labels carry `hold:mayor`, `gc:session`, `handoff` — **no brief metadata at all**.

Same class of error as the four false alarms this subsystem has already produced today. Recording it because it is the single most load-bearing measurement here, and a reviewer should re-run it rather than trust it.

### Splitting the 8 into two very different groups

**Four are a one-time migration record** — `legacy_n`, `legacy_source`, `manifest_status`, `migration_action`, present on **42 of 57 rows and only the migrated ones**. These are not an ongoing requirement; they are a receipt. Taylor has already ruled migration is a deliberate operation, never a runtime matcher — so a receipt does not belong in the live read path at all.

**Three are genuine, ongoing, and beads cannot express them:**

- **`gate_profile`** (`standard` 14 · `decision` 42 · `producer_repair` 1) — which gate set applies. This is *pipeline* state, not issue state.
- **`brief_kind`** — the pipeline's taxonomy, distinct from `issue_type`.
- **`defer_until`** — 1 of 57 rows. Rare, real, and unrepresentable in beads today.

Plus **`path`**, which is a cache concern by definition: it exists because the brief is a file. It is not a fact about the brief.

---

## Why eight defects clustered here, which is the part worth designing against

The defects are not independent. **Seven of the eight are the same failure**: a component asserting a state it did not verify.

```
#92    _update_stack_index no-ops silently when no row matches
#102   brief-manifest-current PASSES on a valid-but-stale index
#128   redundant_artifacts[kind=pile] always 'missing'
#95    the stack misreports its contents four ways
#77    35 rows point at already-decided briefs
remove-archived-row     recorded an archival it never checked
reconcile-archive       same defect, different name
```

**The manifest is a cache with no coherence mechanism.** Every writer is trusted to keep it true, nothing checks that they did, and its own currency gate (`#102`) tests JSON well-formedness rather than currency. That is why the defect count is high and why they all rhyme.

**Deleting it does not fix that.** Three fields still need a home, and if they move into an equally unchecked place the same eight defects reappear under new names.

---

## Recommendation: SHRINK

**Keep** `gate_profile`, `brief_kind`, `defer_until`, `path` — the pipeline state beads genuinely cannot express, plus the file location.

**Drop** `slug`, `created_at`, `unlock_count`, `source` — derivable; every duplicate is a disagreement waiting to happen, and `#95`'s four-way misreport is what that looks like.

**Retire** the four migration fields out of the live read path into a migration receipt. They are 42 of 57 rows of a completed operation.

**That is 12 fields → 4.** Two-thirds of the surface goes away, including every field that can disagree with the bead store, and the remaining four are things nothing else claims.

### The one architectural question this raises, for cozy

**Should `gate_profile` / `brief_kind` / `defer_until` be bead fields instead?** If beads gained three structured keys, the manifest would collapse to `path` — and a pure path index is trivially rebuildable from a directory scan, which makes it a cache that *cannot* drift, because it would be derived on read rather than written by hand.

**That is the deletion outcome Taylor is reaching for, and it is reachable — but it goes through the bead schema, not through the manifest.** I am not proposing it as this spike's recommendation because it changes a store cozy owns and it needs their judgement on cost.

---

## What this spike did NOT establish

- **The `.pile/manifest.jsonl` (9 fields, 22 rows) was measured separately and is in worse shape** — all 22 rows read `status: ready` while zero briefs are actually pending. But its fields (`n`, `track`, `form`, `no_brainer_verdict`, `requires_taylor_adjudication`) are pipeline state with the same profile as the index's three keepers. **Same recommendation, not separately argued here.**
- **I did not test the `source` field's reconstructibility.** I marked it "probably derivable" and that is the weakest cell in the table.
- **No code written. No migration proposed.** B2.10 blocked every adjudication in the city for hours; this deliberately proposes none.
