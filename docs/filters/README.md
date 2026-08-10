# Filter System User Manual

The mathcity filter system is the repeat-pattern layer around the brief and
bead workflows. A filter does not decide research questions and does not ship
code. It classifies repeated mechanical shapes, writes evidence, and routes the
next decision to the brief pipeline or repair workflow.

The system has four parts:

| Part | What it filters | Primary result |
| --- | --- | --- |
| [Repair no-brainer and gates](./repair-no-brainer-and-gates.md) | Briefs that look mechanically safe to shortcut | G9 classifier evidence and compact-form eligibility |
| [Formula repair feedback](./formula-repair-feedback.md) | Briefs rejected because their producer formula emitted bad or incomplete evidence | Producer-failure event records and repair-review work |
| [Bead repair no-brainer and gates](./bead-repair-no-brainer-and-gates.md) | Repeated lost-bead classifications that suggest a downstream filter rule | Decision briefs proposing a new downstream bead filter |
| [Bead repair feedback](./bead-repair-feedback.md) | Repeated lost-bead classifications that point at an upstream dispatch or formula failure | Decision briefs proposing an upstream repair |

## Safety Model

Filters are allowed to classify, cache derived evidence, create decision briefs,
or create repair-review work. They are not allowed to silently or unverified-ly
close beads, merge branches, defer work, patch formulas, or override
human-only gates.

The downstream and upstream rollup formulas' own worker steps (`file-brief` in
`lost-bead-classification-rollup.toml` and `lost-bead-upstream-repair-rollup.toml`)
are the one deliberate exception: they close themselves, but only after
verifying — with live commands, not assumption — that their output artifacts
and dependency links actually exist (`bd dep list "$BRIEF_ID" --readonly` plus a
markdown/manifest existence check). This is *evidence-verified* self-close, not
silent close. If verification fails, the step must stay open and report the
failing command, never close the workflow root or finalizer on its own.

These formulas are `graph.v2` workflows: a `workflow-finalize` step only closes
the workflow root after every `blocks`-type dependency step is already closed.
A worker step written to forbid its own close with no evidence-verified
escape hatch will never let the workflow terminate — the finalizer waits
forever with no timeout. Any new filter formula step that forbids self-close
must include an equivalent verified-completion path, or route through a
controller-side completion signal instead.

The main invariants are:

- stop gates run before shortcut decisions;
- repeated patterns must meet a threshold before a rule or repair is proposed;
- derived cache files are inspection state, not the canonical record;
- durable evidence lives in beads, decision briefs, or emitted events;
- unknown provenance stays unknown until evidence proves the source.

## User Entry Points

| Goal | Use | Notes |
| --- | --- | --- |
| Prepare a brief and let the filter system choose compact vs. full form | `/brief-prep <artifact>` | Calls the no-brainer classifier as part of brief production. |
| Classify one brief without executing anything | `/catch-no-brainer <brief-path>` | Dry-run classifier; writes only the documented candidate/no-brainer side-effect files. |
| Present filtered briefs for human decision | `/present-briefs` | Drains the approved stack; no-brainers appear in compact form only when gates allow it. |
| Record a human verdict on a brief | `/adjudicate-brief` | Records the verdict on the brief bead itself and emits `brief.decided`. |
| Diagnose one bead before acting on it | `/bead-check <bead-id>` | Read-only; may emit a `lost-bead-classification.v1` TOML block. |
| Record rejected-brief producer failures | `gc sling mathcity.brief-operator brief-producer-failure-record --formula` | Usually order-driven. Use manually only when investigating rejected pile items. |
| Roll up repeated producer failures | `gc sling mathcity.brief-operator brief-producer-failure-rollup --formula --var threshold=3` | Creates or finds repair-review work in the `gascity-packs` rig when a tight fingerprint reaches threshold. |
| Roll up downstream lost-bead filter candidates | `gc sling mathcity.brief-operator lost-bead-classification-rollup --formula --var classification_root=<dir>` | Reads exported classification event caches and files decision briefs for proposed downstream rules. |
| Roll up upstream lost-bead repair candidates | `gc sling mathcity.brief-operator lost-bead-upstream-repair-rollup --formula --var classification_root=<dir>` | Reads classification and provenance caches and files decision briefs for repair proposals. |

## What Not To Invoke Directly

Do not call internal gate scripts or orders as substitutes for the formulas
above unless you are writing or debugging the pack. In particular:

- `brief-gate-keep` is the promotion gate, not a user workflow;
- `brief-shuffle` is the single-writer pile mover, not a manual review tool;
- `lost-bead-filter.py` is the deterministic engine behind the rollup formulas;
- `brief-producer-failure-*` cache files are derived state, not inputs to edit.

When in doubt, run the skill first (`/brief-prep`, `/catch-no-brainer`,
`/present-briefs`, `/adjudicate-brief`, or `/bead-check`) and let the skill
route to the formula layer.
