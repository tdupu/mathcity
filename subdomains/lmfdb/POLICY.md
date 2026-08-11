# LMFDB Subdomain Policy

Parent: [README.md](./README.md)

| Field | Value |
| --- | --- |
| Status | Draft — pending human adjudication |
| Date | 2026-07-12 |
| Drafted | Outside agent (Claude), from is-good-experiment, create-lmfdb-type, update-schema, server skills, hecke `magma/schema.md`, and the brief-system E/S-rules |
| Applies to | `mathcity-lmfdb` subdomain — LMFDB labels, experiments that produce or consume LMFDB data, remote compute-server usage, and new LMFDB type creation |
| Consumers | `check-lmfdb-hygiene`, `new-lmfdb-type-policy`, `create-lmfdb-type`, `update-schema`, `is-good-experiment`, `push-data-to-server`, `pull-data-from-server`, `push-to-server`, `plan-an-lmfdb-webpage`, any polecat working an LMFDB-type bead |

Governs what makes a good LMFDB label, what makes a good LMFDB experiment,
how the remote compute server is used, and when a new LMFDB type is
justified. Every rule has an ID and a pass/fail criterion a skill can
mechanically check.

Rule-ID prefix: **LM**, reserved in
`mathcity/docs/rule-prefix-registry.md` (PP5.2) — avoids collision with
the brief-system's L/S-rules, the latex subdomain's LX-rules, the magma
subdomain's M-rules, and dev's P-rules. Families: **LM1.x** labels,
**LM2.x** experiments, **LM3.x** server usage, **LM4.x** type creation.

**Governance (POLICY-POLICY.md).** This document follows the mathcity
policy-governance rules: Draft status governs nothing until the human adjudicator
adopts it (PP2.1–PP2.2); rule IDs are permanent once committed (PP1.5);
amendments require a human-approved proposal (PP1.4 — until a dedicated
`new-lmfdb-policy` amendment skill exists, use the `new-hygiene-policy`
proposal format against this file). The audit half of the trinity is
`check-lmfdb-hygiene`. Note: `new-lmfdb-type-policy` creates LMFDB
*types* under this policy, not policy rules (same naming caveat as
`new-math-bead-policy`).

**Relationship to sibling policies.** This policy *specializes*; it never
*duplicates*. Experiment design authority is the brief-system E-rules
(`mathcity/subdomains/brief-system/POLICY.md`) enforced by
`is-good-experiment`; server-touching brief/close discipline is the
brief-system S-rules and B3.2; pack privacy and portability is dev
P1.10/P1.14. Where this document restates a sibling rule it cites it; on
any conflict the sibling policy wins for its own domain and this policy
wins for LMFDB-specific mechanics.

---

## Core definitions

- **LMFDB label.** The stable text key of a serialized mathematical
  object. It is simultaneously: the primary key in flat files and the
  PostgreSQL `lmfdb` schema, a `DATA/` path component, the equality
  criterion (`'eq'` intrinsics compare by label), and — for types headed
  to the public LMFDB site — a URL slug.
- **LMFDB experiment.** A computation run to answer a question about
  LMFDB-pipeline data or code (scaling probes, invariant checks,
  cross-checks against lmfdb.org). Distinct from a **data-production
  run** (a make/crunch script populating canonical `DATA/`).
- **Server-touching.** Per brief-system S1: any operation that modifies
  remote server state or the canonical `DATA/` tree — dispatching
  compute, pushing data, non-dry-run repair/recompute queues, remote DB
  writes. Reading (queries, pulls into snapshots, dry-runs) is not
  server-touching.
- **LMFDB type.** A `declare type LMFDBXxx` in `package-LMFDB.mag` with
  the full serialization contract: ATTRS list, `Print`, `load`/`read`/
  `write`/`create` intrinsics, path functions, `'eq'`, column
  registration in `package-IO.mag`, and a `schema.md` section.

---

## Pillar 1 — Labels (LM1.x)

*A label outlives every session, file layout, and schema version that
touched it. Design it like a permanent address, because it is one.*

- **LM1.1 Every type has a label; every label scheme is documented.**
  Every LMFDB type declares a `label` attribute (registered in
  `TextCols`), unique within the type's table, and `schema.md` documents
  the scheme with an explicit construction rule (component list + how
  each is computed) and an example. A type whose label scheme exists
  only in code → **fail**.
- **LM1.2 Labels are deterministic functions of mathematical data.** The
  label is computed from the object's mathematical invariants (dimension,
  form label, discriminant, index, cycle structure, sort position among
  canonical representatives) — never from session state, wall-clock,
  RAM addresses, or file arrival order. Re-running label assignment on
  the same object MUST reproduce the same label. Nondeterministic input
  → **fail**.
- **LM1.3 Machine-safe character set.** Labels use only characters safe
  as filenames, URL path segments, and pipe-delimited fields:
  alphanumerics plus `.` (component separator) and `-` (sub-object
  suffix separator, e.g. eigenform `<subgroup_label>-a`). Negative
  integers encode with the `m` prefix (`m4` = −4); hashes use base-62
  (`0–9a–zA–Z`). Never `|` (the serialization delimiter), never spaces,
  slashes, or shell metacharacters. Violating character → **fail**.
- **LM1.4 Structure beats hashes.** Prefer mathematically meaningful,
  sortable components (invariants, canonical indices, cycle-structure
  prelabels) over opaque hashes. A hash component is a last-resort
  disambiguator, and any hash must be computed from a *canonical* form of
  the data (e.g. minimized coset table), never from a representation that
  varies by conjugation or basis choice. Precedent: legacy hash-form
  order labels were removed in hecke #252; the subgroup scheme moved to
  `<order_label>.<index>.<prelabel>.<ordinal>`. New scheme leading with
  an avoidable hash → **revise**.
- **LM1.5 Namespaces compose downward.** A child object's label extends
  its parent's label as a prefix: order → subgroup
  (`<order_label>.<index>.<prelabel>.<ordinal>`) → eigenform
  (`<subgroup_label>-<suffix>`). This makes cross-type collisions
  structurally impossible and the parent recoverable by parsing. A new
  type whose objects belong to a parent object MUST prefix the parent
  label; a freestanding scheme for a child type → **revise**.
- **LM1.6 Human-readability is a byproduct, not a goal.** Labels are
  machine keys first. Readability comes from ordering components most-
  significant-first (a human can bucket by prefix), not from embedding
  names or descriptions. Descriptive text lives in columns and knowls,
  never in the label.
- **LM1.7 Labels are stable — migration is an event, not an edit.** Once
  a label has been written to canonical `DATA/` or the database, it
  never changes silently. A label migration requires ALL of: (a) its own
  bead stating old scheme, new scheme, and why; (b) a one-off migration
  script under `magma/make/one-offs/` (precedent:
  `relabel-subgroups-01.mag`); (c) archival of pre-migration files
  (snapshot or `data-*` archive) before rewriting; (d) `schema.md`
  documenting both schemes until migration completes; (e) if migrated
  records exist on the server, the migration is server-touching (LM3.3).
  Any silent relabel → **fail**.
- **LM1.8 Validation is mechanical.** A label checker can verify, with no
  mathematical computation: component count, character set (LM1.3),
  parent-prefix containment (LM1.5), and uniqueness within the loaded
  table (`SELECT label, COUNT(*) ... HAVING COUNT(*) > 1`, or duplicate
  scan over flat files). `check-lmfdb-hygiene` performs these checks.
  *Namespace note:* the similarly-named `check-labels-and-refs` skill
  (latex subdomain) validates LaTeX `\label`/`\ref` pairs, NOT LMFDB
  labels — do not cite it as an LMFDB label gate.

---

## Pillar 2 — Experiments (LM2.x)

*An experiment without a falsifiable question wastes compute; an
experiment whose result can't be reloaded wastes the compute twice.*

- **LM2.1 is-good-experiment gates every LMFDB experiment.** Before
  compute is spent, the proposal passes `is-good-experiment` (the six
  checkpoints; brief-system E1–E6): exactly one falsifiable question,
  both outcomes interpreted, coverage supporting an inferential leap,
  cost classified, pitfalls planned for, runnability assessed. REJECT or
  NEEDS-REVISION → do not run. An LMFDB experiment run without a
  verdict on record → **fail**.
- **LM2.2 The experiment bead is the record.** A good LMFDB experiment
  bead carries, before the run: the question; the YES/NO
  interpretations; the coverage set stated in LMFDB terms (which orders/
  dims/levels — by label where possible); the cost class (short < ~30
  min wall, else long + resource estimate); the data dependencies and
  how they load (`AttachSpec`, `SetLMFDBRootFolder`, `load_*`/`read_*`
  calls); the intrinsics called and why they are the fast route; and the
  output path. Missing question or interpretations → **fail**; other
  missing fields → **revise**.
- **LM2.3 Reproducibility is three artifacts.** Every completed
  experiment leaves: (a) **parameters** — the exact script (versioned
  `test-*.mag` or `make/one-offs/` file) with inputs in its header, plus
  the base ref of the repo at run time (brief-system T2/G16); (b)
  **serialized results** — machine-readable output (TSV, flat file, or
  LMFDB objects) written to a stable declared path, never
  eyeball-the-terminal output; (c) **interpretation** — the answer to
  the question, attached to a research bead or the source bead
  (brief-system E7; research beads are never destructively closed,
  B3.7). Missing any of the three → **revise**.
- **LM2.4 Results enter the pipeline through the lattice, never around
  it.** Experimental data that graduates to canonical data flows through
  the conversion lattice — `create_lmfdb_*` → `write_lmfdb_*` →
  `textfile-to-database`, or `lmfdb-object-to-database` for direct
  insert — so that `label` uniqueness, column types, and the
  `staging → promote` ledger are enforced. Hand-written SQL inserts into
  `lmfdb.*` tables → **fail**.
- **LM2.5 No orphan data in DATA/.** Canonical `DATA/` holds only types
  with a complete `schema.md` section and pipeline wiring (LM4.3).
  Experiment scratch output lives outside canonical `DATA/` dirs (or in
  clearly non-canonical scratch paths) until its type is wired. An
  experiment that deposits unwired flat files into a canonical `DATA/`
  subdir → **revise**.
- **LM2.6 Unrunnable is declared, not silent.** If the experiment cannot
  run (no Magma, missing `DATA/`, server unreachable), report
  UNRUNNABLE with the reason and obtain a `critical-review` verdict
  supporting any conclusion drawn from static evidence (brief-system
  E6). Silent abandonment → **fail**.

---

## Pillar 3 — Server usage (LM3.x)

*The server runs hardware the human adjudicator doesn't sit in front of. Mistakes are
slow to reverse and can clobber days of computation. Authorization must
outlive the session that obtained it.*

- **LM3.1 Conf-driven, private, pre-flighted.** Every server operation
  reads `lmfdb-server.conf` at the project root (fallback:
  `magma/scripts/data-generation.conf`, the hecke convention). No
  hostname, user, key path, or schema name ever appears in pack content,
  scripts, or beads (dev P1.10). Every server/database skill probes for
  its conf before acting and stops gracefully, naming
  `/configure-server` or `/configure-database` (dev P1.14). Hardcoded
  connection value → **fail**.
- **LM3.2 Authorized without a separate gate** (read-only or
  local-additive; no per-run the human adjudicator OK needed):
  - `search-lmfdb` / `mcp__lmfdb__*` queries against lmfdb.org;
  - `pull-data-from-server` — it snapshots into
    `DATA/snapshots/data-server-MM-DD-YY-NN/` before touching canonical
    local dirs, and re-running is idempotent;
  - read-only SSH inspection (`ls`, reading logs, `nproc`, disk checks);
  - dry-run previews (`rsync -n`, `--dry-run` queue passes).
  These still report what they did; they just don't queue for
  authorization.
- **LM3.3 Server-touching operations are gated.** `push-data-to-server`,
  `push-to-server` (mutates remote checkout state), non-dry-run
  dispatch/repair/recompute queues, and any remote DB write classify the
  bead **server-touching**: tag it `server-touching` (and
  `HUMAN_OK_REQUIRED` when brief-system S-rules apply), route its brief
  full-form (S7 — never compact, never auto-execute), and follow
  dry-run → smoke test → per-item OK (S2–S4). Untagged server-touching
  work → **fail**.
- **LM3.4 Authorization does not evaporate.** The reason these beads are
  tagged: a human "go ahead" that lives only in a conversation dies
  with the session, and the next polecat — or the same polecat after
  compaction — cannot distinguish "was authorized" from "assumed
  authorized". Therefore: authorization is recorded as a **decision
  bead** (plus the redundant `decisions.jsonl` / inline-annotation
  channels) BEFORE the operation executes; it is per-item and per-run,
  never transitive (S4 — authorizing the dry-run does not authorize the
  batch; authorizing bead A does not authorize bead B in the same
  convoy); and a server-touching bead without a recorded authorization
  can neither execute nor close (B3.2). Execution or close on a
  conversational-only OK → **fail**.
- **LM3.5 Idempotency preconditions for any push.** Before
  `push-data-to-server` (or any data-mutating dispatch) runs for real,
  ALL of the following hold:
  - (a) a dry-run (`rsync -avzn`) has been run and its output reviewed —
    no `data-*/` snapshot directories in the transfer list, no
    unexpected deletions;
  - (b) the operation is re-run-safe: rsync semantics for transfers;
    make/crunch scripts use the `OpenTest`-skip pattern; DB promotion
    uses `SELECT DISTINCT ON (label)` — running twice must equal
    running once;
  - (c) anything being overwritten remotely is recoverable — a local
    snapshot or remote backup exists (`I_HAVE_A_BACKUP=1` discipline);
  - (d) only canonical working dirs are pushed — snapshots (`data-*/`)
    never leave the local machine.
  Missing precondition → **fail**; the push does not run.
- **LM3.6 Pull before push on overlapping dirs.** If remote computation
  may have written to a `DATA/` subdir since your last pull, run
  `pull-data-from-server` (snapshot) before pushing that subdir.
  Pushing over unpulled remote results destroys server compute →
  **fail**.
- **LM3.7 Know the direction map.**
  | Skill | Direction | Payload |
  | --- | --- | --- |
  | `pull-data-from-server` | remote → local snapshot → canonical local | computed `DATA/` results |
  | `push-data-to-server` | canonical local → remote (excludes `data-*/`) | locally-computed `DATA/` files |
  | `push-to-server` | GitHub → remote (`git pull` over SSH) | code, never data |
  Data never moves through the code repo; code never moves through
  rsync. Mixing the channels → **revise**.

---

## Pillar 4 — Type creation (LM4.x)

*A new type is a permanent contract: a label scheme, a storage layout,
seven synchronized files, and (eventually) a public webpage. Create one
deliberately or not at all.*

- **LM4.1 A new type must be justified.** Create a new LMFDB type only
  when ALL hold: (a) it is a distinct class of mathematical object with
  its own label scheme and storage path — not a variant of an existing
  type expressible as new columns (that is `update-schema` on the
  existing type); (b) the data is reused across sessions/pipelines — a
  one-off experiment output is not a type (LM2.5); (c) the populating
  intrinsics exist or are specified. Failing (a) → **reject** (extend
  the existing type); failing (b) or (c) → **defer** until they hold.
- **LM4.2 Naming conventions.** Magma type `LMFDBXxx` (CamelCase, `LMFDB`
  prefix); intrinsics `load_lmfdb_<name>`, `read_lmfdb_<name>`,
  `write_lmfdb_<name>`, `create_lmfdb_<name>`, `get_lmfdb_<name>_path`;
  staging table `staging.<type>_src`; production table
  `lmfdb.clifford_<type>`; DATA dir `DATA/<type_dir>/`. The ATTRS list
  is `Sort([...])` with the `//ALWAYS ALPHABETICAL!` comment —
  serialization order depends on it. Avoid Magma reserved words in
  attribute names (`adj` → `adjacent`); the Magma attribute `order`
  maps to `order_label_old` in staging and `order_label` in the lmfdb
  schema (SQL reserved word). Deviation → **revise**.
- **LM4.3 Full wiring or it isn't a type.** The `create-lmfdb-type`
  checklist completes in full: type declaration + ATTRS, `Print`,
  `load`, `'eq'`, path function(s), `read`, `write`, `create`, column
  registration in `package-IO.mag`, and an `update-schema` pass over all
  seven files (`schema.md`, `package-LMFDB.mag`, `package-IO.mag`,
  `db_schema_staging.sql`, `db_schema_lmfdb.sql`, `db_load.py`,
  `db_migrate.py`), plus caching attribute and make script (or a filed
  issue for each deferral). A partially-wired type is a proto-type; its
  implementing bead cannot close (brief-system B4.1 analog). Explicitly
  staged wiring (e.g. DB files deferred to a promotion PR, as in hecke
  #301) is allowed only when the deferral is tracked in the bead/issue.
- **LM4.4 Label scheme before serialization code.** The label scheme
  (LM1.1–LM1.5) is designed, documented in the bead, and confirmed
  against the parent-prefix rule BEFORE any `create_lmfdb_*` code is
  written. Changing a label scheme after data exists is a migration
  (LM1.7), so get it right first. Columns and types are final before
  the `update-schema` pass (changing them after → data migration).
- **LM4.5 Storage layout is a deliberate choice.** One-file-per-order
  (all entries appended) vs one-file-per-entry is chosen by the loading
  pattern — per-entry loading → one file per entry — and recorded in
  `schema.md`. Precedent: gamma0 moved from appended-per-order (old,
  deprecated) to one-file-per-entry (v2).
- **LM4.6 Webpage decision is explicit.** Every new type records, in its
  bead, whether it is headed for the public LMFDB website. If yes: its
  label becomes a URL and `plan-an-lmfdb-webpage` is run to produce the
  web-layer task breakdown (Blueprint, web data class, routes,
  templates, beta migration) once the data pipeline is done. If no
  (internal cache type, e.g. `LMFDBOrderSnfs`): record "internal-only"
  and skip the web plan. A silent no-decision → **revise**.
- **LM4.7 Serialization footguns are law.** Never assign
  `SaveJsonb(...)` to an LMFDB attribute (double-encoding corrupts
  every jsonb field — hecke #174); assign raw jsonified values and let
  `SaveAttr` encode. Never edit `.sig` files (auto-generated). Flat
  files use the psycodict convention: `|`-delimited, `\N` for NULL,
  `t`/`f` for booleans, columns in ATTRS alphabetical order. Violation
  → **fail**.

---

## Non-negotiables (quick checklist)

- Every type has a documented, deterministic, machine-safe label; child
  labels extend parent labels (LM1.1–LM1.5).
- Labels never change silently; migration = bead + one-off script +
  archive + dual-scheme docs (LM1.7).
- No experiment runs without an `is-good-experiment` verdict; question +
  both outcomes + coverage + cost + data-loading + fast-route intrinsics
  live in the bead (LM2.1–LM2.2).
- Every experiment leaves parameters, serialized results, and an
  interpretation; results enter the DB only through the conversion
  lattice (LM2.3–LM2.4).
- No connection values in pack content; conf pre-flight on every
  server/database skill (LM3.1).
- Reads and dry-runs are free; writes are gated, tagged, and authorized
  by decision bead BEFORE execution — authorization is per-item,
  per-run, and never conversational-only (LM3.2–LM3.4).
- Dry-run reviewed + re-run-safe + backup exists + snapshots excluded,
  before every push; pull before push on overlapping dirs (LM3.5–LM3.6).
- New types: justified, conventionally named, fully wired, label-first,
  layout deliberate, webpage decision recorded (LM4.1–LM4.6).
- Never `SaveJsonb` on assignment; never edit `.sig` files (LM4.7).

---

## Verdict vocabulary

Reuses the brief-cycle vocabulary (same as dev and brief-system
policies): **approve** (no violations), **revise** (fixable violations —
list all, with rule IDs), **reject** (the approach itself violates a
pillar — e.g. unauthorized server write, hashed label where structure
exists, new type for one-off data), **defer** (human call — escalate to
the human adjudicator, don't guess).

---

## References

- `mathcity/subdomains/lmfdb/skills/check-lmfdb-hygiene/SKILL.md` — enforcement procedure for this policy
- `mathcity/subdomains/lmfdb/skills/new-lmfdb-type-policy/SKILL.md` — policy-gated type creation wrapper
- `mathcity/subdomains/lmfdb/skills/create-lmfdb-type/SKILL.md` — the 11-step type scaffold (LM4.3 checklist source)
- `mathcity/subdomains/lmfdb/skills/update-schema/SKILL.md` — the seven-file schema sync
- `mathcity/subdomains/lmfdb/skills/{push-data-to-server,pull-data-from-server,push-to-server,configure-server,configure-database}/SKILL.md` — server mechanics (LM3)
- `mathcity/subdomains/lmfdb/skills/plan-an-lmfdb-webpage/SKILL.md` — web-layer planning (LM4.6)
- `mathcity/skills/is-good-experiment/SKILL.md` — six-checkpoint experiment gate (LM2.1)
- `mathcity/subdomains/brief-system/POLICY.md` — E-rules (experiments), S-rules (server-touching briefs), B3.2/B4.1 (close discipline), B3.7 (research beads)
- `mathcity/subdomains/dev/POLICY.md` — P1.10 (privacy scrub), P1.12 (setup-skill companion), P1.14 (dependency pre-flight)
- `<repos-root>/hecke/magma/schema.md` — live label schemes, storage layouts, and the database pipeline workflow this policy generalizes from
