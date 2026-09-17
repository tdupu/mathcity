# WRITERS.md — shared mechanics for every tex-writing skill

Parent: [README.md](./README.md). Every writing leaf (write-proposition,
write-definition, write-remark, rapid-prototype, explain-experiment,
revise, write-materials-and-methods, write-introduction) runs this
preamble and postamble; leaves state only their own middle. Binding:
design ADRs 0003 (in place or nowhere), 0004 (tex purity, agent-side
ledger).

## Preamble (before writing a word)

1. **Resolve** the repo's docs per
   `subdomains/repo-docs/RESOLUTION.md`; read STYLE.md's style
   variables and repo-specific conventions. No docs → `init-repo-docs`
   first.
2. **Target**: the canonical file LATEX.md names for the tier being
   written (or a declared aspirational file being opened). Any other
   `.tex` target is a refusal: "in place or nowhere." Markdown output
   goes to `scratch/`, never a second `.tex`.
3. **Contradiction gate**: run `contradiction-check` targeted at the
   claims about to be written/changed. A hit = the write is refused
   (that skill's Step 3 owns the report).
4. **Doubt gate** (claim promotions into notes.tex only): the ledger
   row must carry a recorded doubt run
   (`subdomains/repo-docs/LEDGER.md`); absent → refuse and name the
   gap.

## Writing rules

- Every edit sits inside ST5 machine tags
  (`% >>> [agent-<harness> <date> <slug>]` … `% <<< […]`), superseded
  text commented out, never deleted.
- Never create, delete, or edit a human marker (`\taylor{}`, `\todo{}`)
  or any human comment or tag; answer queries only via `\agentreply{}`
  adjacent to the marker (ST4).
- Statement discipline per the repo's STYLE.md (ST1 proposition-only,
  ST2 explicit hypotheses, ST3 line length); LX floor applies (LX4:
  proof, pinpoint citation, or textbook note — nothing else ships).
- Citations only through `track-down-reference` output (opened-source
  verified); notes tier defaults to self-contained proofs (ST6).
- No status metadata in the tex (ST7); ledger rows carry status.

## Postamble

1. Update the agent-side ledger row(s) (LEDGER.md format): where,
   status, evidence, depends-on.
2. Run `check-latex` (compile + evidence block) and `check-style` on
   the touched file; findings are reported, not silently fixed beyond
   the tagged edit.
3. Report the tagged region(s) to the human for acceptance — acceptance,
   acknowledgement, and marker/tag cleanup are human acts. No commit
   without explicit authority; ST8 applies when one is authorized.

## Loud refusal

A writer that cannot satisfy its preconditions (missing docs, failed
contradiction gate, missing doubt record, undeclared target, unresolved
markers where its leaf forbids them) states the reason and stops. It
never substitutes an adjacent task (design D5).
