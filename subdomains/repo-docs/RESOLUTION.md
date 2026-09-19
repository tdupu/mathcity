# Policy resolution — shared preamble for repo-doc check skills

Parent: [README.md](./README.md). Binding record: design ADR 0001
(repo-local-first). Every `check-*` skill runs this preamble before its
first finding. Written once here; skills cite, never restate
(pointer-not-copy).

## 1. Resolve repo-local-first

A check skill enforces the **repository's own** documents, resolved in
this order:

1. Paths declared in the repo's `AGENTS.md` (the canonical entry point).
2. Default root locations: `LAYOUT.md`, `LATEX.md` (or per-directory),
   `STYLE.md`, `ADR.md`, `AGENTS.md`, `AI-POLICY.md`.

The pack defaults in [templates/](./templates/) are **seeds and floors**,
never the resolved target: a repo's instantiated copy is the contract.

## 2. On miss: import-and-interrupt

A miss = no declaration, or a declared path that does not exist —
treat both the same:

- Do NOT silently fall back to the pack default; do NOT hard-fail.
- Instantiate the template into the repo — at the AGENTS.md-declared
  path if any, else the default root location; fill the header (repo
  name, date, Status: Draft) — then **interrupt the human** for
  approval before checking. No approval → verdict DEFER, the
  instantiated file left as Draft.

## 3. Floor semantics

Global subdomain policy is a floor. For `.tex` concerns the floor is
`subdomains/latex/POLICY.md` (LX-rules): a repo's docs may tighten LX
rules, never delete or weaken them. Divergence below a floor is a
finding (`FLOOR-BREACH`), reported against the repo doc, not the floor.
A floor binds regardless of its own Status field — floors are the
non-negotiable minimum; FLOOR-BREACH findings are never downgraded to
advisory.

## 4. Status semantics

Read the resolved document's own `Status` field — never assume it.

| Status field | Check behavior |
| --- | --- |
| `Adopted` | Findings are binding (FAIL verdicts possible). |
| `Draft` | Full check; verdict prefixed `ADVISORY` — Draft guides, does not govern. |
| absent or unparseable | **Finding** (`MALFORMED-POLICY`); proceed as if Adopted — malformed never collapses into permissive. |

## 5. The check must be able to fail

Every run self-verifies its own instruments before reporting:

- Every enumeration the verdict rests on reports its **count**; a count
  of zero where the repo plausibly has such objects is
  `EVIDENCE-ABSENT`, never a PASS on that clause.
- A glob that matches nothing is distinguished from one that found
  conformance: report "checked N objects, 0 violations", never bare
  "no violations".
- On first use — the first run in a repo with no prior report from this
  checker — confirm it CAN fail: run the decisive clause against a
  known-violating state (a test fixture, or a synthetic one-file
  violation in `scratch/`) and confirm a finding. A checker that cannot
  fail is worse than no checker.

## 6. Read-only

Check skills report; they never fix, never adjudicate, never edit the
docs they enforce (amendments go through the paired `new-repo-*-policy`
skill), never creating files except the §2 instantiation and their own
report under `ai/<date>-<check>/` — dated, durable audit evidence, which is
also what lets a check report satisfy AI19's retained-with-the-submission
requirement. The §5 known-violating synthetic stays in `scratch/`: it is
throwaway, not evidence.
