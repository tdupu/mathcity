---
name: new-lmfdb-type-policy
description: Create a new LMFDB type the policy-conformant way — gate the justification (LM4.1), design and freeze the label scheme first (LM1.x, LM4.4), then drive create-lmfdb-type + update-schema, record the webpage decision, and finish with a check-lmfdb-hygiene audit. Use when the user says "new lmfdb type", "add an LMFDB type for X the right way", "policy-gated type creation", "new-lmfdb-type-policy", or whenever create-lmfdb-type is about to run on a type that doesn't have an approved label scheme and justification yet. Companion to check-lmfdb-hygiene; wraps (does not replace) create-lmfdb-type. NOTE: despite the -policy suffix, this skill creates LMFDB TYPES following the policy, not policy rules — amendments to lmfdb/POLICY.md go through a human-gated proposal per POLICY-POLICY.md PP1.4 (new-hygiene-policy format), same caveat as new-math-bead-policy.
---

# new-lmfdb-type-policy

Policy-gated wrapper around [[create-lmfdb-type]]. That skill scaffolds
the code; THIS skill makes sure the type deserves to exist, its label
scheme is right before any code is written, and the result passes
[POLICY.md](../../POLICY.md) before the bead closes.

**Why the wrapper exists:** labels are permanent (LM1.7) and a type is a
seven-file contract (LM4.3). The expensive mistakes — wrong label
scheme, type-that-should-have-been-columns, unrecorded webpage decision
— all happen *before* `create-lmfdb-type`'s Step 1. This skill front-
loads those decisions and gates them on the human adjudicator.

## Step 0 — Read the policy and the dependency check

```bash
cat <mathcity-pack-root>/subdomains/lmfdb/POLICY.md
```

Then verify the pipeline conf exists before proceeding (P1.14):

```bash
# Discover conf: project root first, hecke fallback
CONF=""
for candidate in \
    "$(git rev-parse --show-toplevel 2>/dev/null)/lmfdb-pipeline.conf" \
    "magma/scripts/data-generation.conf"; do
  [ -f "$candidate" ] && { CONF="$candidate"; break; }
done
if [ -z "$CONF" ]; then
  echo "I'm sorry, I can't do that — no database pipeline conf found."
  echo "Run /configure-database (mathcity-lmfdb.configure-database) to create lmfdb-pipeline.conf at your project root."
  echo "(This conf holds your PostgreSQL and DATA_DIR settings for the LMFDB pipeline.)"
  exit 1
fi
```

Do not design a type for a project with no pipeline.

## Step 1 — Justification gate (LM4.1)

Answer, in writing, in the type's bead:

1. **Distinct object class?** Is this a new class of mathematical
   object, or a variant of an existing type? If the data fits as new
   columns on an existing type → STOP, verdict **reject-as-type**, and
   route to [[update-schema]] instead. (Test: would it share the
   existing type's label scheme and storage path? If yes, it's
   columns.)
2. **Reused across sessions?** One-off experiment output is not a type
   (LM2.5). If unsure → **defer**.
3. **Populating intrinsics exist or are specified?** Name them with
   signatures. If they don't exist yet → **defer** until specified.

## Step 2 — Label scheme design (LM1.x, LM4.4) — BEFORE any code

Draft the scheme against every LM1 rule:

```
LABEL SCHEME PROPOSAL — <type name>

Components:   <ordered list, most-significant first, with how each is computed>
Example:      <a concrete label>
Determinism:  <why re-running assignment reproduces the label — LM1.2>
Charset:      [0-9a-zA-Z.-] only; m-prefix negatives; base-62 hashes — LM1.3
Structure:    <which components are invariants; any hash component and its
               canonical-form justification — LM1.4>
Parent:       <parent type + prefix rule, or "freestanding (no parent)" — LM1.5>
Uniqueness:   <what disambiguates ties — ordinal, index, canonical sort — LM1.8>
```

Model on the existing schemes in `<repos-root>/hecke/magma/schema.md`
("Label Scheme" section): order labels
(`<dim>.<form_label>.<disc_prefix><abs_disc>...<N>`), subgroup labels
(`<order_label>.<index>.<prelabel>.<ordinal>`), eigenform labels
(`<subgroup_label>-<suffix>`).

## Step 3 — Present to the human adjudicator

Gate Steps 1–2 with [[present-it]] (compact form for a clean,
precedent-following scheme; full-form if the type opens a new label
namespace or a new storage layout):

```
DECISION:  Create LMFDB type <LMFDBXxx> with label scheme <scheme>?
CONTEXT:   <one sentence: what it stores, why not columns on an existing type>
RECOMMEND: APPROVE — <one-line rationale>
CONFIRM:   y / n / grill-me-further
```

**Do not write code before approval.** Record the approval per
decision-recording discipline. Also collect NOW (they gate later
steps):

- storage layout: per-order vs per-entry, with the loading-pattern
  rationale (LM4.5);
- **webpage decision**: public-LMFDB-bound or internal-only (LM4.6);
- final column list with types — changing them after the schema pass is
  a data migration (LM4.4).

## Step 4 — Scaffold

Invoke [[create-lmfdb-type]] with the approved inputs. It drives the
11-step scaffold (declaration + ATTRS through make scripts) and calls
[[update-schema]] for the seven-file sync at its Step 10. Enforce as it
goes:

- naming conventions LM4.2 (including `Sort([...])` +
  `//ALWAYS ALPHABETICAL!`);
- no `SaveJsonb()` on attribute assignment, no `.sig` edits (LM4.7);
- every deferred checklist item (caching, make script, staged DB
  wiring) gets a tracked issue/bead — untracked deferral blocks close
  (LM4.3).

## Step 5 — Webpage wiring (LM4.6)

- **Public-bound:** run [[plan-an-lmfdb-webpage]] to produce the
  web-layer task breakdown; link its output from the type's bead.
- **Internal-only:** write "internal-only, no webpage" in the bead with
  one sentence of rationale (precedent: `LMFDBOrderSnfs`).

## Step 6 — Final gate

Run [[check-lmfdb-hygiene]] on the type's bead/diff. The type is done
only on **approve**. On **revise**, fix and re-run; on **reject**,
escalate to the human adjudicator — do not close the bead. Then fire the documentation
rules: README/`schema.md` rows land with the change (update-README /
D-rules).

## Hard rules

- **Never skip Step 3.** No type is created without the human adjudicator's recorded
  approval of the justification and label scheme.
- **Label scheme freezes at approval.** Changing it after data exists is
  an LM1.7 migration, not an edit.
- **This skill does not push or commit.** Git operations follow the
  active context profile and repo policy (`authorize-git-operation`
  where required).
- **reject-as-type is a success outcome.** Routing to `update-schema`
  instead of creating a redundant type is the policy working.

## Cross-references

- [POLICY.md](../../POLICY.md) — LM-rules; this skill executes LM4.1/LM4.4/LM4.6 and inherits the rest
- [[create-lmfdb-type]] — the scaffold this skill wraps
- [[update-schema]] — seven-file schema sync (and the destination for reject-as-type)
- [[plan-an-lmfdb-webpage]] — Step 5 for public-bound types
- [[check-lmfdb-hygiene]] — Step 6 final gate
- [[new-hygiene-policy]] — the dev-subdomain sibling whose gate-on-the human adjudicator shape this follows
- `<repos-root>/hecke/magma/schema.md` — label-scheme precedents
