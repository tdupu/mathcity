# Machine-readability audit of the brief system — 2026-08-19

**Scope.** Every piece of state the brief system needs to read, classified by what
it would take to make a program able to read it.

**Epistemic rule.** Every number below is **MEASURED** against the live city on
2026-08-19 unless the line says **INFERENCE**. Measurements were taken by direct
read-only SQL against the managed Dolt server and by running the production
parsers in `assets/scripts/mctl_core/briefs.py` over the real corpus — not by
re-quoting earlier session figures. Where a figure handed to me did not
reproduce, the reconciliation is in §2 and my number is the one used.

---

## 1. Verdict

**Roughly a fifth of the brief system is machine-readable today, and the readable
fifth is mostly the wrong fifth.** Identity, status, priority and the dependency
graph are typed and reliable. Everything that carries the *decision* is prose:
of 139 closed decision beads, `mctl` classifies **10 as adjudicated and 129 as
malformed**, because `_verdict()` reads only `metadata.verdict` / `decision` /
`recorded_verdict` and never looks at `close_reason` — which **138 of those 139
beads actually carry**. Of 280 decision beads the production parser extracts a
§4 section from 59 and a labeled decision option from **exactly one**. Of 89
stack files, **85 fail the very gate check the policy tells authors to satisfy**.
The data is in far better shape than the readers are: the corpus is not empty,
it is unaddressed.

**The three changes with the highest leverage**, in the order I would do them:

1. **Teach the verdict reader the two sources that already hold verdicts.**
   `close_reason` (138 of 139 closed beads) and
   `.beads/decisions-track/manifest.jsonl`, which carries a typed `verdict` key
   on **126 of 204 rows** and is currently classified by `policy_refs.py` as
   "migration input, not an active presentation lane" — i.e. deliberately not
   read. Wiring an adapter over these two moves the Adjudicated view from 10
   rows to roughly 130 without a single bead being edited. This is the largest
   single unlock in the audit and it is mostly TOOLING.

2. **Fix the gate-token regex.** `require_gate` in
   `assets/scripts/checks/brief-check.sh:220` matches `(PASS|N/A)\b`, so the
   policy-mandated `PASSED` and `NOT APPLICABLE` are both mechanically rejected,
   as is any bolded `**PASS**`. Measured: **4 of 89 stack files pass G14; 85
   fail.** It is a one-line change with no migration, and it is the only item
   here where the corpus is already correct and only the enforcer is wrong.

3. **Put typed options on the bead.** `parse_decision_options` returns at least
   one option for **1 of 280** decision beads. The design's §4 "decide" screen
   therefore has no data source at all — not a sparse one, an empty one. This is
   the most expensive item (MIGRATION over ~59 beads that have a §4 and ~183
   that have no headings at all), and it is the one that cannot be shortcut.

A fourth, cheaper than #3: **backfill source dependencies.** `MBRF004` fires on
**120 of 141 open decision beads**, and it is a hard refusal, so the pending
queue — the screen a user sees first — is blocked for 85% of its rows.

---

## 2. Reconciliation of the 264 / 137 discrepancy

The figure handed to me was "200 decision beads across 5 rigs" versus "264/137
across 8 stores". Neither reproduces. Measured today by SQL:

| store (Dolt db) | decision beads | closed |
|---|---|---|
| `hq` (city root) | 80 | 53 |
| `hecke` | 114 | 50 |
| `gascity_packs` | 69 | 33 |
| `gs` | 11 | 0 |
| `agent_skills` | 5 | 2 |
| `differential_valuations` | 1 | 1 |
| **total** | **280** | **139** |

Two separate causes, both now identified:

- **"5 rigs / 200" omitted the city-root HQ store.** 200 is the five rig stores;
  the HQ store holds another 80 decision beads (53 closed), and HQ is where most
  of the process-policy briefs live. Any dashboard that reports "city-wide" and
  counts 200 is under-reporting by 29%.
- **"8 stores" over-counted by aliasing.** `find` reports 23 `.beads`
  directories under the city root, but seven of them are not distinct stores:
  `mathcity.brief-operator{,-1,-3,-5,-8}` have **no `config.yaml`** and
  `gascity-packs-briefpath` has a `gsp` prefix but returns `gt-` ids — all six
  resolve to the HQ database and each reports HQ's 80/53. `diff_alg_examples`
  errors out with a project-identity mismatch. Counting those as stores
  double-counts HQ. There are **6** real stores holding decision beads.

The residual 280−264 = 16 is ordinary drift (three `gascity_packs` decision
beads were created today alone). The 4-rig figure of **86 closed** does
reproduce exactly (50+33+2+1), and the "1 of 189" acceptance-criteria figure was
that same 4-rig scope; city-wide it is **1 of 280**.

---

## 3. Classification table

`R?` = machine-readable today. Counts are city-wide over all 6 stores unless a
narrower scope is named.

| field / artifact | where it lives | machine-readable today? | what it takes | est. scope |
|---|---|---|---|---|
| **Bead identity** (`id`) | `issues.id` | **Yes** — typed, primary key | — | done |
| **Status** (open/closed) | `issues.status` | **Yes** | — | done |
| **Adjudication state** (D5 binary) | derived, `briefs.py::_decision_state` | **No** — computed from a verdict reader that misses 129 of 139 | **BOTH** | 129 beads |
| **Verdict** | `metadata.verdict` (12), `close_reason` (138), `manifest.jsonl:verdict` (126), stack front-matter `verdict:` (22) | **Barely** — 12 of 280 in the one place the reader looks; four uncoordinated channels that disagree | **BOTH** — adapter first, then a single canonical write path | 129 beads |
| **`close_reason` semantics** | `issues.close_reason` | **No** — one field, five meanings (measured: 79 narrative, 25 legacy-backfill, 21 supersession, 7 leading-verdict-token, 4 SCREAMING-KEBAB, 2 withdrawal, 1 empty) | **BOTH** | 139 closed |
| **Disposition / option chosen** | inside the verdict string | **No** — e.g. `A-DISPATCH-NOW-WITH-Q-DEFAULTS`; parseable by eye only | **BOTH** | ~130 |
| **Compound / per-item verdicts** | inside the verdict string | **No** — e.g. `PER-ITEM-VERBATIM-PASSED-TO-MAYOR-FOR-DECOMPOSITION-PLUS-DEPENDENCY-GRAPH-REJECTED` | **MIGRATION**, and it needs a schema decision first (§2 of the state doc) | 12 |
| **§4 decision options** | bead `description` prose | **No** — `parse_decision_options` returns ≥1 option on **1 of 280 beads**. `_OPTION_ITEM` matches only `- **(A) Heading**` inside a §4 section, and fails open with no diagnostic reserved for "options present but unparseable", so `MOPT001` can never fire. **Important:** 17 of 89 stack `.md` files already use that exact grammar — the format is established, it just never reached the beads | **BOTH** — the grammar exists, so the migration is transcription rather than invention | 280 |
| **Brief body** | `issues.description` | **Yes** — `briefs_show` returns `body` | — | done (was TOOLING, fixed) |
| **Brief body sections** | headings in `description` | **Partly** — production parser: **97 of 280** yield ≥1 section, **59** yield a §4, **183 yield none** (`MBRF041`); **272 headings map to no section index** (`MBRF042`) | **MIGRATION** | 183 |
| **Acceptance criteria** | `issues.acceptance_criteria` | **Column exists and `bd --acceptance` writes it; 1 of 280 uses it. `mctl_core` never reads it — `Bead` has no field for it and `_bead_from_mapping` never extracts it** | **ACCEPT** (see §5) — D11 says never force these. If a screen ever needs it, the accessor is a two-line **TOOLING** add | 1 |
| **Gate evidence** | stack `.md` prose + tables | **No** — 43 of 89 have a Gate Evidence section; **only 4 of 89 satisfy `require_gate` for G14**; written in ≥3 incompatible formats (pipe table, `Key: PASS`, bolded) | **TOOLING** — the corpus is right, the regex is wrong | 89 files, 1 line of code |
| **Gate disposition** | stack `.md` `Disposition:` line | **Yes where present, and a fixed enum** (`promote\|reject\|blocked`) — but present on **2 of 89** | **MIGRATION** | 87 files |
| **`brief_bead:` identity** | stack `.md` front matter | **No** — **1 of 89**; `present-briefs`' canonical-bead filter is a no-op for 88 | **MIGRATION** (D2/D3 make this the docket number) | 88 files |
| **`metadata.brief_path`** | bead metadata | **Structurally yes, semantically dead** — 44 beads carry it, **0 of 44 resolve on disk**, and all 44 are absolute home paths baked into bead data | **MIGRATION** (delete or repoint) | 44 |
| **Form / shape marker** | stack front matter `form:` | **Written but read by nobody** — 50 of 89 (`full` 28, `compact` 19, `full-present-it` 3), values a clean enum. No reader for `form:` exists anywhere in `assets/`. The adjacent live signal, `compact_eligible:true`, is emitted to stdout JSON by `catch-no-brainer` and never read back | **BOTH** — a reader first (cheap), then 39 files of backfill | 39 files |
| **Stack front matter generally** | stack `.md` YAML | **Better than assumed** — **89 of 89** have parseable YAML front matter; `status` 89, `artifact` 85, `unlock_count` 60, `track` 49 | **TOOLING** — nothing in `mctl_core` reads it | 0 migration |
| **Stack `status` values** | front matter `status:` | **No** — 15 distinct values, several embedding the whole verdict inline | **MIGRATION** | 89 |
| **Stack index row** | `manifest.jsonl` slug ↔ filename | **Partly** — 46 of 89 stack files match a manifest row; **5 have neither a manifest row nor gate evidence** (not 41 — see §6) | **BOTH** | 43 files |
| **Decisions-track manifest** | `.beads/decisions-track/manifest.jsonl` | **Yes, and it is the single richest structured source in the system** — 204 rows, 43 distinct keys, `verdict` on 126, `unlock_count` on 149, `form` on 201, `adjudicated_at` on 101 | **TOOLING** — `policy_refs.py` classifies it as migration-only input, so nothing presents it | 0 migration |
| **…its `status` field** | same | **No** — 48 distinct values; 39 rows embed the verdict inside the status string, e.g. `adjudicated:approve-b(push=false)` | **MIGRATION** (mechanical, see §4) | 39 rows |
| **…its `source_bead` link** | same | **No** — 133 of 204 null/`"none"`; only 55 distinct beads referenced; **0 rows carry `brief_bead`** | **MIGRATION** | 133 rows |
| **Per-brief decision cache** | `.beads/briefs/decisions/*.toml` | **Yes — fully typed** (`decision`, `decision_maker`, `timestamp`, `source_bead`, `stack_path`) | **MIGRATION** — only **10 files exist** for 280 beads | 270 |
| **Pile membership** | `.pile/` filesystem | **No** — membership is "is there a file", and there are **5 `.md` vs 56 `.md.bak`**; `classification.log` is unparsed | **BOTH** | 61 files |
| **No-brainer classification** | a structured line inside Gate Evidence: `G9 No-brainer-filter: PASS classifier_state=… category=… confidence=…`; plus `.pile/.no-brainer/` (6 files), `manifest.jsonl:no_brainer_leak` (16), one `no-brainer` label, 4 beads' metadata | **A real grammar and a real parser exist** — `brief-shuffle-fast-drain.py:80-116` validates `classifier_state` against a 5-value enum, `category` against `no-brainer-categories.toml`, and a 0.85 confidence floor. But it is written on **6 of 89** stack files (3 with `category`, 4 with `confidence`), lives on no bead, and the `.pile/.no-brainer/` files are inert — `artifact_layout()` never reads the `no_brainer` key from `paths.toml` | **BOTH** — the grammar is settled, so this is mostly backfill plus moving it onto the bead | ~83 files |
| **Defer window** | `issues.defer_until` (real typed `datetime` column) | **The plumbing works; the corpus is empty.** `bd update --defer` writes it, `mctl`'s `plan_deferral` calls it, `_defer_until()` reads it. Populated on **10 issues city-wide and 0 decision beads**. Two real defects: the dead sibling key `deferred_until` (not a column), and mctl writing a date (`YYYY-MM-DD`) into a column bd returns as an ISO timestamp, compared **lexically** — which happens to work except at the same-day boundary | **MIGRATION** (backfill), plus a small **TOOLING** fix for the lexical compare and the dead key | ~5 |
| **Dependency edges — type** | `dependencies.type` | **Yes** — typed enum, `bd dep add -t` writes it. Decision-bead-scoped: 542 edges, **519 `related`**, 15 `relates-to`, 4 `parent-child`, 2 `discovered-from`, **1 `blocks`**, 1 `supersedes` | **MIGRATION** — the column is fine, the values are uniformly `related` | 519 edges |
| **Dependency edges — reason** | `dependencies.metadata` | **No** — column exists, **all 44,648 edges across all 6 stores are `{}`**, and `bd dep add` has **no metadata flag** (`--file` documents only `from`/`to`/`type`) | **UPSTREAM** — unwritable without a `bd` change | bd |
| **Source dependency (B2.1)** | edge existence | **No for most** — `MBRF004` fires on **120 of 141 open** decision beads (hecke: 82 of 114 total) | **MIGRATION** | 120 |
| **Provenance / producer** | stack front matter `deposited_by` (43), `deposited_at` (43), `producer_contract` (5), `source_formula` (5); bead `created_by`, `owner` | **Partly** — `created_by`/`owner` are typed and populated; `deposited_by` is a free-form string mixing session UUIDs, agent handles and formula names | **BOTH** — the bead columns already answer "who"; the front-matter field answers "which formula step" and needs a grammar | 43 |
| **Policy references** | `policy_refs.py::PolicyReference` | **Partly** — 3 hard-coded references with `reference` + `description` only; no file, line or text. Stack files cite G1–G16 as bare tokens (G4 in 91 places, G8 in 77, G14 in 65) with no registry mapping token → rule | **TOOLING** — build a PolicyIndex; the citations already exist and are consistent | 0 migration |
| **Diagnostics registry** | `assets/mctl/diagnostics.toml` | **Yes — 75 codes, 24 of them `MBRF*`**, each with `severity`, `meaning`, `policy_ref`, `module` | — | done |
| **Labels** | `labels` table | **Yes, but sparse and ad-hoc** — 130 label rows on **51 of 280** beads; `brief-record` (9) and `policy` (8) are the only ones used more than 5 times | **ACCEPT** — labels are a folksonomy; do not promote to schema | — |
| **Priority** | `issues.priority` | **Yes** — 0:1, 1:104, 2:75, 3:100 | — | done |
| **Unlock count** (ranking) | `metadata.unlock_count` (31 beads), manifest (149), stack front matter (60) | **Partly** — three channels, no reconciliation, and it is derivable from the edge graph anyway | **TOOLING** — compute it, stop storing it | 0 migration |
| **Comments / rationale thread** | `comments` table | **Yes as a container** — 56 of 280 beads have ≥1 | **ACCEPT** — see §5 | — |
| **`design` / `notes` columns** | `issues.design`, `issues.notes` | **Available, barely used for briefs** — design 3, notes 128 | **ACCEPT** — prose fields doing prose work | — |
| **Decisions-track `decisions.jsonl`** | same directory | **Yes — fully typed and the best-shaped record in the corpus** (`ts`, `n`, `verdict`, `taylor_verbatim`, `scope_granted`, `scope_NOT_granted`, `supersedes`, `channels`) | **MIGRATION** — **only 2 rows exist** | — |
| **`no-brainer-leaks.jsonl`** | same directory | **Yes** — typed, 10 rows, includes `structural_reason` and `rule_proposed` | **TOOLING** — nothing reads it | 0 migration |

---

## 4. Migration planning — mechanical vs judgement

The owner's framing is a per-bead agent loop. The split below is what a script
can settle alone versus what needs a model or a person. Counts are the buckets.

### 4a. Verdict (129 beads read as malformed)

| bucket | n | mechanical? |
|---|---|---|
| `close_reason` begins with a `VALID_VERDICTS` token (`approve:` …) | 7 | **Fully mechanical.** Split on the first `:`, map through `VALID_VERDICTS`, write `metadata.verdict`. |
| `legacy verdict backfill: <TOKEN> per decisions.jsonl <ts>` | 25 | **Fully mechanical.** Fixed grammar; the token and the timestamp both lift out with one regex. The token itself stays opaque — that is the *disposition* problem, not the verdict problem. |
| `APPROVED -- see comment …` (SCREAMING-KEBAB lead) | 4 | **Mechanical** for the verdict (`approve`); the rationale is in a comment and should stay there. |
| Supersession / duplicate (`Superseded by X`, `Duplicate of Y`) | 21 | **Mechanical to *detect*, judgement to *classify*.** A script can lift the target id with a regex; whether the row is an adjudication at all is a policy call — the state doc already flags 3 of these as "never adjudications". Recommend a script that proposes `superseded_by=<id>` and refuses to write a verdict. |
| Withdrawal / moot | 2 | **Mechanical** to detect; needs the schema decision on whether "moot" is a verdict. |
| Prose narrative | 79 | **Judgement.** Leading tokens are `Taylor` (16), `push` (16), `Decision` (11), `push/sync` (9) — the `push`/`push/sync` group (**25**) is not adjudication at all, it is `authorize-git-operation` execution records and should be excluded from the brief corpus rather than migrated. That leaves **~54 genuinely needing a model read** of the close reason plus the bead body. |
| Empty | 1 | Judgement (one bead). |

**Shortcut that removes most of the work:** `manifest.jsonl` already holds a
typed `verdict` for 126 rows, and 43 of the 89 stack files carry a slug that
matches a manifest row. Join manifest → stack file → bead first; every bead the
join covers needs no interpretation at all. I did not measure the join yield
onto beads because `source_bead` is null on 133 of 204 manifest rows — **that
join yield is the single most useful next measurement**, and it decides whether
the prose bucket is 79 beads or closer to 20.

### 4b. Disposition / option code (~130)

Almost entirely **judgement**. A script can mechanically detect the shape
(`^[A-Z]-` prefix, ~30 cases) and extract the letter, but the letter is
meaningless without the option list it indexes into — and the option lists are
in §4 prose that itself does not parse (see 4d). Do 4d first or this bucket
cannot be validated. **1 case is already machine-readable** (`he-skli`:
`3A-5C-1NORELITIGATE`) and should be the target grammar.

### 4c. Source dependency, `MBRF004` (120 open beads)

**Mixed, and better than it looks.** Mechanical for any bead whose title or
description names a bead id in the same store — a `\b(he|gsp|gt|gs|as|dv)-\w+\b`
scan against the store's id set will propose an edge with high precision.
Judgement for the rest, and for deciding edge *type* (`related` vs
`discovered-from` vs `parent-child`). I did not measure the id-mention yield; it
is a five-minute script and should be run before scoping this bucket.

### 4d. §4 options (279 of 280 beads)

**Judgement, unavoidably** — this is writing structure that was never written.
But it splits:

- **59 beads have a parsed §4** and need only the option lines reformatted into
  a labeled grammar. A model can do this per-bead with the existing text; a
  script cannot, because the options are sentences.
- **38 more have sections but no §4** — a model must decide whether the brief
  offers options at all.
- **183 have no headings whatsoever.** These are the prose trackers. Most should
  probably not become option-bearing briefs; triage them first (see §5) rather
  than migrating them.

Recommended order: reformat the 59, triage the 183, then decide about the 38.

### 4e. Manifest `status` field (39 rows with embedded payload)

**Fully mechanical.** Every one matches `^(?P<state>[a-z-]+):(?P<payload>.*)$`.
Split into `status` + a new `verdict_detail`, leave `verdict` alone. Zero
judgement; this is a 20-line script.

### 4f. `metadata.brief_path` (44 beads, 0 resolving)

**Fully mechanical.** All 44 point at absolute home paths under a rig brief tree
that holds 2 files total. Either delete the key or repoint it at the stack; both
are scriptable. Doing this also removes 44 absolute home paths from bead data —
a P1.10 exposure that lives inside the corpus, not in a document.

### 4g. `brief_bead:` on stack files (88 files)

**Mechanical for 43** — those match a manifest slug, and the manifest's
`source_bead` gives the id where non-null. **Judgement for the rest**, and a
fuzzy title match against the bead store is the obvious assist. This is the D2
"docket number" item, so it is worth doing carefully rather than fast.

### 4h. Per-brief `decisions/*.toml` cache (270 missing)

**Fully mechanical once 4a lands** — the TOML shape is already defined and
populated for 10 files; generating the other 270 is a projection of bead state,
not new information. Do this last; it is a derived artifact and regenerating it
is cheap.

---

## 5. What should stay prose

- **Rationale, `verdict_note`, and `taylor_verbatim`.** The verbatim ruling is
  evidence; typing it would destroy it. `decisions.jsonl` already has the right
  shape: a typed `verdict` field *beside* an untouched `taylor_verbatim`. Copy
  that pattern everywhere rather than trying to structure the note.
- **Bead comments.** 56 beads use them for exactly what they are for. The
  container is already queryable; the contents should not be.
- **`design` and `notes` columns.** Prose fields doing prose work.
- **Acceptance criteria.** D11 rules these are never forced, and the measurement
  agrees with the ruling: 1 of 280 uses the column and the system has not
  suffered for it. Classify as **ACCEPT**, not as a 279-bead migration. Making
  the field *available* is already done; making it mandatory would manufacture
  ceremony.
- **Labels.** A folksonomy with 130 rows and a long tail. Promoting any of it to
  schema would freeze accidents.
- **The `structural_reason` / `rule_proposed` fields in `no-brainer-leaks.jsonl`.**
  These are arguments, and they are good ones. Type the surrounding record, not
  the argument.
- **The 25 `push` / `push/sync` close reasons.** These are git-authorization
  execution records that happen to live on decision beads. They should be
  *excluded* from the brief corpus, not migrated into it — a filter, not a
  rewrite.

---

## 6. What I could not determine

- **The "41 of 89 stack files have neither an index row nor gate evidence"
  figure does not reproduce, and I could not identify the definition that
  produces it.** With "index row" = a numeric filename prefix I get 5; with
  "index row" = a matching `manifest.jsonl` slug I get 5; with "index row" = an
  `n:` front-matter key I get 46 (no stack file has an `n:` key). The three
  underlying counts are solid — 47 of 89 numeric-prefixed, 46 of 89 with a
  manifest row, 43 of 89 with Gate Evidence — but the conjunction as stated is
  not one I can rebuild. **Treat 41 as unverified.**
- **The manifest→bead join yield.** The highest-value unmeasured number in this
  audit (see §4a). `source_bead` is null on 133 of 204 rows, so the join must go
  through the stack filename slug, and I did not build that mapping.
- **Whether `MBRF005` and `MBRF004` are the actual gate on the dashboard's
  pending screen**, or whether the dashboard filters earlier. I read the
  diagnostic emission in `briefs.py::_doctor_briefs` but did not trace the
  dashboard's consumption path.
- **Two registry/reader defects found while mapping the code, not chased to
  ground:** (i) `diagnostics.toml` defines `MBRF011` as "brief markdown cache
  exists with no matching decision bead", but `briefs.py:485,495` emit
  `MBRF011` for two entirely different conditions — the registered meaning is
  unreachable and the two live meanings are unregistered; (ii)
  `_approved_for_dispatch` (`briefs.py:976-981`) hard-codes its own four-string
  accept set instead of routing through `VALID_VERDICTS`, so the write-side
  normalisation table and the read-side acceptance set can silently drift.
- **`redundant_state.py` resolves artifact paths rig-root-relative while the
  live stack is city-root-level** (open question Q5, documented in
  `schemas.py:228-233`). The consequence is already encoded: every MCP response
  carrying artifact state is forced to also carry `trusted: false`. So the
  stack/pile artifact-state figures in this table are what the *filesystem*
  says, not what `mctl` currently trusts itself to report.
- **Whether `bd dep add --file` silently discards a `metadata` key.** I
  confirmed from `--help` that no metadata flag exists and that the documented
  `--file` schema is `from`/`to`/`type` only, and that all 44,648 edges are
  `{}`. I did **not** run the write test — this is a read-only audit — so
  "silently discards" remains **INFERENCE** from the help text and the corpus.
- **Whether the second pack checkout under the city root serves a different
  `mctl_core` to dispatched agents.** Flagged in the state doc, not re-verified
  here; if true, several parser figures above are checkout-dependent.
- **Rig-level brief trees.** The hecke rig brief tree holds 2 `.md` files
  total, which is why all 44 `metadata.brief_path` values dangle. I did not
  establish where those files went — archived, deleted, or never written.

---

*[autogenerated by Claude Opus 5 on 2026-08-19]*
