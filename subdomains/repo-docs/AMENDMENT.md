# Amendment procedure — shared by all new-repo-*-policy skills

Parent: [README.md](./README.md). The five amendment skills
(`new-repo-layout-policy`, `new-repo-latex-policy`,
`new-repo-style-policy`, `new-repo-adr-policy`,
`new-repo-agents-policy`) each own exactly one repo doc and all follow
this procedure. Written once here; the skills cite it (pointer-not-copy).
Model: the LX trinity's `new-latex-policy`.

RED baseline for this whole class: `baselines-phase1.md` scenario D —
unguided agents amend the convention doc in place with no proposal, no
approval, no change log (D3: acceptance is a human act).

## Step 0 — Resolve the target doc

Repo-local-first per [RESOLUTION.md](./RESOLUTION.md). On miss, this IS
the instantiation path: copy the template, fill the header, and treat
the instantiation itself as the proposal (Step 2).

## Step 1 — Draft the proposal

```
## Proposed amendment — <doc> (<repo>)
**Change:** <add rule <ID> | amend <ID> | deprecate <ID> | ADR entry | header/status change>
**Text:** <exact new text; rules need a mechanical pass/fail criterion
           or they are guidance and belong in prose, not as a rule>
**Rationale:** <incident, check finding, or human request that exposed the gap>
**Floor check:** <does this weaken any LX rule or template-floor rule? then STOP — floors cannot be lowered repo-side>
**Downstream:** <existing files now in violation; remediation lines>
```

Rule IDs are permanent: next integer in the prefix, never renumber,
deprecate with a tombstone (the LX discipline).

## Step 2 — Human gate (mandatory)

Present via AskUserQuestion (or present-it compact form):
`DECISION / CONTEXT / RECOMMEND / CONFIRM: approve | revise | defer`.
No edit before explicit approval in THIS conversation. Silence is not
approval; approval of a different proposal does not transfer. Defer →
record the proposal (bead if a store exists, else
`scratch/<date>-proposals/`) and STOP.

## Step 3 — Apply

Edit ONLY the owned doc: insert the text, bump the header `Date`,
append a Change Log row (`| date | change | approver |`). Adoption
(Status: Draft → Adopted) is itself an amendment, decided by the human.

## Step 4 — Verify

Run the paired check skill on the repo. A surprise (something now
fails) goes back to the human — never quietly weaken the new text to
make an existing violation pass.

## Step 5 — Commit (conservative)

Show `git status` and the diff; commit only with explicit authority,
pathspec-scoped to the owned doc; repo commit conventions (ST8) apply.

## Hard rules

- One skill, one doc: never edit another repo doc, any `.tex`, or the
  pack templates (template changes are a pack-side amendment, decided
  with Taylor).
- Never amend to excuse an existing violation.
- Never lower a floor.
- Never commit or push beyond Step 5's explicit authority.
