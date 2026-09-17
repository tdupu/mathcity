# Policy resolution — shared preamble for repo-doc check skills

Parent: [README.md](./README.md). Binding record: ADR 0001 of the
mathpowers/latexpowers design (repo-local-first resolution). Every
`check-*` skill in this subdomain runs this preamble before its first
finding. Written once here; skills cite it, never restate it
(pointer-not-copy).

## 1. Resolve repo-local-first

The documents a check skill enforces are the **repository's own**,
resolved in this order:

1. Paths declared in the repo's `AGENTS.md` (the canonical entry point).
2. Default root locations: `LAYOUT.md`, `LATEX.md` (or per-directory),
   `STYLE.md`, `ADR.md`, `AGENTS.md` at the repository root.

The pack defaults in [templates/](./templates/) are **seeds and floors**,
never the resolved target: a repo's instantiated copy is the contract.

## 2. On miss: import-and-interrupt

If the repo declares no instance of the needed document:

- Do NOT silently fall back to the pack default.
- Do NOT hard-fail.
- Instantiate the pack default template into the repo (fill the header:
  repo name, date, Status: Draft), then **interrupt the human** for
  approval before proceeding with the check. No approval → the check
  stops with verdict DEFER and the instantiated file left as Draft.

## 3. Floor semantics

Global subdomain policy is a floor. For `.tex` concerns the floor is
`subdomains/latex/POLICY.md` (LX-rules): a repo's docs may tighten LX
rules, never delete or weaken them. Divergence below a floor is a
finding (`FLOOR-BREACH`), reported against the repo doc, not the floor.

## 4. Status semantics

Read the resolved document's own `Status` field — never assume it.

| Status field | Check behavior |
| --- | --- |
| `Adopted` | Findings are binding (FAIL verdicts possible). |
| `Draft` | Full check runs; verdict is prefixed `ADVISORY` — Draft docs guide, they do not govern. |
| absent or unparseable | **Finding in itself** (`MALFORMED-POLICY`), and the check proceeds as if Adopted. Malformed must never collapse into permissive. |

## 5. The check must be able to fail

Every run self-verifies its own instruments before reporting:

- Every enumeration the verdict rests on (tex files found, docs found,
  markers matched) reports its **count**; a count of zero where the
  repo plausibly has such objects is an `EVIDENCE-ABSENT` finding,
  never a PASS on that clause.
- A glob or grep that matches nothing is distinguished from one that
  ran and found conformance: report "checked N objects, 0 violations",
  never bare "no violations".
- Before first use on a repo, the checker confirms it CAN fail: run the
  decisive clause against a state known to violate it (the fixture in
  the skill's tests, or a synthetic one-file violation in scratch) and
  confirm a finding is produced. A checker that cannot fail is worse
  than no checker.

## 6. Read-only

Check skills report; they never fix, never adjudicate, never edit the
docs they enforce (amendments go through the paired `new-repo-*-policy`
skill), and never create files except the Step-2 instantiation and their
own report under `scratch/`.
