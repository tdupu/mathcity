---
name: new-latex-bead
description: Create a new LaTeX work bead that is well-formed under the LaTeX Subdomain Policy (mathcity/subdomains/latex/POLICY.md, LX-rules) and POLICY-beads.md BP7 from birth - real bd type (never an invented type, P5.3), [LATEX] label plus exactly one latex-* stage label, named root compilation target, declared gate coverage (he-jwmy scope test), section-scoped atomization with the LX4.6 cap, computation and claim dependency edges (bd dep), and gate-evidence acceptance criteria pre-filled. Refuses monolith shapes and routes document-scale work to an epic decomposition. Trigger on "new latex bead", "create a latex bead", "file a bead for this .tex work", "track this section rewrite", "new-latex-bead <root-file>", or when check-latex-hygiene reports work that should have been beaded (LX1.1). NOTE - this skill creates BEADS, not policy rules; amendments to the LX policy go through the future new-latex-policy trinity skill.
---

# new-latex-bead

Create a LaTeX bead with the LX-required fields pre-filled, so it passes
[[check-latex-hygiene]] from birth. Companion of [[check-math-bead-hygiene]] /
`new-math-bead-policy` (which own the BP5–BP9 math-item lifecycle); this skill
owns the LaTeX-workflow shape.

Read [POLICY.md](../../POLICY.md) (LX-rules) and `mathcity/POLICY-beads.md`
Pillar 7 before creating anything.

## Pre-flight (P1.14)

1. `bd list --help` succeeds (beads DB reachable in the current rig). If not:
   ```
   I'm sorry, I can't do that — no beads database is reachable here.
   Run bd init (or cd into the rig that owns this .tex work) first.
   (The bead IS the tracked work item; without bd there is nothing to create.)
   ```
2. The root `.tex` file must exist on disk (or the user must confirm it is
   about to be created by this bead). A bead with no compilation target is
   LX9.2 — refuse to create it without one.

## Step 1 — Gather the six required fields

Ask only for what can't be inferred from context:

1. **Root compilation target** — the file `check-latex` will run against
   (e.g. `latex/notes/notes.tex`). If the work touches an `\input` fragment,
   the ROOT document is still required (LX9.2).
2. **Section scope** — one section or contiguous range (LX4.1). "The whole
   document" → go to Step 2 (epic path).
3. **Work kind** — content / restyle / restructure-merge / typo-batch /
   promotion / MRE-fix. One kind per bead (LX9.5); merges get the LX6 shape.
4. **Stage** — default `latex-draft` (LX2.1). A bead is born at draft unless
   the work item is purely gate-screening of existing compiled content.
5. **Computation & claim provenance** — any Magma computation beads whose
   results the prose will quote (LX8.3), any `[MATH_CLAIM]` beads being
   written up (BP7.4), any LMFDB knowl/record coupling (LX5.1).
6. **Owner** — assignee, required before the bead can pass
   `latex-compilation-ready` (LX9.3).

## Step 2 — Shape checks (refuse bad shapes BEFORE creating)

- **Coverage test (BP7.1 / he-jwmy).** Mechanically determine whether each
  touched file is covered: named `notes.tex` at any depth, under a
  `latex/notes/` tree, or in the depth-2 closure
  (`grep -E '\\\\(input|include)\{' <notes-tier roots>`). Record the result —
  it goes in the description verbatim. Never mix covered and uncovered files
  in one bead (LX4.7): split instead.
- **Monolith check (LX4.2/LX4.6).** If the scope is document-scale or the
  projected diff exceeds ~200 changed lines / ~3 sections: do NOT create a
  task. Create an `epic` and per-section child tasks (pattern: he-ce4.3),
  each child re-entering this skill. Tell the user which cut you propose.
- **Atomization floor (LX4.7).** Confirm each proposed bead's midpoint state
  can compile on its own (no dangling refs across bead boundaries) — if not,
  re-cut the seams.
- **Type selection (BP1/P5.3).** `task` (default, section-scale) | `feature`
  (new paper/deliverable) | `epic` (decomposition parent) | `chore`
  (typo-batch, LX4.5). Never an invented type; never `spike` for
  mathematical writing (BP1.4).
- **Merge shape (LX6).** For restructure-merge work: note that
  `merge-latex-sections` is HOLD (gsp-fby) — the bead plans a MANUAL
  pure-move merge with pre/post `check-labels-and-refs` reports in its
  acceptance criteria (LX6.2–LX6.3).

## Step 3 — Create the bead

```bash
bd create -t <type> \
  -l LATEX -l latex-draft \
  "[LATEX] <root-file> §<scope> — <one-line what>" \
  -d "$(cat <<'EOF'
## Compilation target
Root: <path/to/root.tex>          # LX9.2 — what check-latex runs against
Touched files: <list>
Coverage: <covered | not covered> per he-jwmy scope test: <one-line result>

## Scope (LX4.1)
Sections: <§X–§Y>
Work kind: <content|restyle|restructure-merge|typo-batch|promotion|mre-fix>

## Provenance & coupling
Computation deps: <bead-ids or none>      # LX8.3 — mirrored as bd dep edges
Claim beads written up: <ids or none>     # BP7.4
LMFDB coupling: <knowl/record + linked lmfdb bead id, or none>  # LX5.1
Direction of truth (if both prose+record): <prose→record | record→prose>  # LX5.3

## Acceptance criteria (BP7.2 — gate evidence, not vibes)
- [ ] check-latex report: compile pass (or pass-with-undefined-refs + reason);
      evidence at <city-root>/tmp-for-review/<this-bead>/
- [ ] check-labels-and-refs: PASS on touched labels/refs
- [ ] semantic diff summary within declared scope (LX4.1) and cap (LX4.6)
- [ ] quoted results trace to DATA/ path, committed .mag + sha, or verified
      LMFDB label (LX8.1/LX5.2)   <delete if no quoted results>
- [ ] [covered only] human approval of the SPECIFIC diff —
      latex-approval.toml with matching approved_diff_sha (LX3.4)
- [ ] [merge only] pre- AND post- check-labels-and-refs reports; post PASS
      with no new orphans; pure-move semantic diff (LX6.2–LX6.3)

## Stage log (LX2.2 — advance label only with entry evidence)
latex-draft: <today>
EOF
)"
```

Then wire the edges and owner:

```bash
bd dep add <new-id> <computation-bead>   # one per LX8.3 dep
bd dep add <new-id> <claim-bead>         # BP7.4
bd update <new-id> --assignee <owner>
```

For the epic path: create the epic first, then each child via this skill,
then `bd dep add` children → epic (or use [[create-convoy]] for the
decomposition).

## Step 4 — Verify

Run [[check-latex-hygiene]] on the new bead. It must come back **approve**
(with the Draft-policy advisory note while the LX policy is unadopted). If it
doesn't, fix the bead now — a bead that starts non-conformant stays
non-conformant.

## Stage transitions (later sessions)

This skill also performs the label advance when asked ("advance <id> to
compilation-ready"):

1. Verify the LX2.2 entry evidence for the requested stage exists in the
   bead / evidence dir. No evidence → refuse, list what's missing.
2. Replace the stage label (`bd label` remove old, add new — exactly one at a
   time, LX2.4). Never move backward (LX2.3): regressions get a NEW bead
   linked `discovered-from` the old one.
3. On `latex-published`: add `[RESEARCH_JOURNAL]` and the protective defer
   per BP2.2 — published mathematics is never destructively closed (B3.7).
4. Append to the Stage log section with date + evidence pointer.

## Hard rules

- Never create a bead without a root compilation target (LX9.2).
- Never use an invented bd type (P5.3/BP1.1) — stages are labels.
- Never mix coverage classes, work kinds, or documents in one bead
  (LX4.7/LX9.5).
- Never create a document-scale task — epic + decomposition only (LX4.2).
- Never encode a computation dependency as prose only — `bd dep` or it
  doesn't exist (LX8.3).
- This skill creates and advances beads; it never adjudicates diffs (LX3.4
  is the human adjudicator's) and never amends policy (PP1.4).

## Cross-references

- `mathcity/subdomains/latex/POLICY.md` — LX-rules (source of truth)
- `mathcity/POLICY-beads.md` — BP1 (types), BP7 (LaTeX bead well-formedness), BP8 (claims)
- [[check-latex-hygiene]] — the audit this bead must pass from birth
- [[check-latex]] — produces the acceptance-criteria evidence
- [[create-convoy]] — decomposition tooling for the epic path
- `new-math-bead-policy` (agent-skills) — math-item lifecycle sibling; use it for research/claim/lit-review beads, this skill for LaTeX work beads
