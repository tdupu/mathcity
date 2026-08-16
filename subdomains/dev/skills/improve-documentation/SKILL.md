---
name: improve-documentation
description: >-
  Update mathcity documentation hygienically after feature, formula, skill,
  policy, setup, or workflow changes. Use after any user-facing change, after
  adding planned work, or when check-documentation-policy reports drift. Keeps
  README.md, feature docs, examples, tests, formula/skill/subdomain indexes,
  parent links, and setup guides aligned with source.
---

# improve-documentation

Operational updater for [POLICY-documentation.md](../../POLICY-documentation.md).
Use this to make docs match source and to keep the documentation graph clean.

## Step 0 — Read The Policy And Scope The Change

```bash
cat <mathcity-pack-root>/subdomains/dev/POLICY-documentation.md
```

Identify what changed:

| Change type | Required documentation pass |
| --- | --- |
| Feature or workflow | User-facing docs, examples, tests, Example Coverage table |
| Formula | `README-formulas.md`, formula docs, tests, examples if user-facing |
| Skill | `README-skills.md`, skill docs, any workflow docs that mention it |
| Subdomain | `README-subdomains.md`, subdomain README, root Documentation Map |
| Policy | Policy index/map, development docs, checker/amender skill references |
| Setup/ops | `SETUP.md`, `README-dolt.md`, `README-mayor.md`, `README-clerk.md`, relevant operation docs |

## Step 1 — Find The Canonical Home

Before writing, decide where the information belongs. Avoid duplicate
competing explanations.

- Root `README.md`: concise overview and Documentation Map.
- `GLOSSARY.md`: terms only.
- `docs/TECHNICAL-SPEC.md`: system mechanics.
- `SETUP.md`: operator setup from first principles.
- `README-formulas.md`, `README-skills.md`, `README-subdomains.md`: canonical indexes.
- Feature/subdomain README: user-facing usage and examples.
- Policy files: checkable rules only.

If a section is too detailed for the root README, move the detail to a linked
doc and leave a concise summary.

## Step 2 — Update Examples And Tests

For each user-facing feature touched:

1. Add or update a working usage example.
2. Add or update an `Example Coverage` table:
   `Example | Runner | Prerequisites | Command | Test path | Status | Issue`.
3. Ensure at least one reasonable test certifies the new behavior.
4. Route high-cost, risky, or agent-heavy tests through `test-execution-request`
   or a briefed test plan rather than running them silently.

Existing features without full coverage can be marked backlog, but new features
must not be marked complete without examples and tests.

## Step 3 — Keep The Navigation Graph Clean

- Root `README.md` must link every important doc.
- Every important doc below root must have a `Parent:` link near the top.
- Use sibling/child links where they help; the hyperlink graph does not need to
  be a tree.
- Remove stale duplicate explanations instead of adding another explanation.

## Step 4 — Update Indexes

Run the same source-alignment checks as `check-documentation-policy`:

- formulas on disk vs `README-formulas.md`
- skills on disk vs `README-skills.md`
- subdomain `pack.toml` roots vs `README-subdomains.md`

Fix missing rows, ghost rows, wrong aliases, wrong counts, and stale text.

## Step 5 — Planned Work Gets Issues

Any planned feature mentioned in public docs needs an issue link. If creating
the issue is blocked by auth or network, write an issue-needed finding in the
doc update report and leave the feature clearly marked planned.

## Step 6 — Verify

Run:

```bash
/check-documentation-policy
```

Then run targeted cheap checks appropriate to the change, for example:

```bash
bash scripts/run-local-tests.sh
```

For documentation-only changes, do not spend model tokens or run integration
tests unless the docs changed those paths.

## Output

Report:

```text
improve-documentation — <date>

Updated:
  - <doc>: <what changed>

Examples/tests:
  - <feature>: <example/test status>

Indexes:
  - formulas: <in sync | fixed>
  - skills: <in sync | fixed>
  - subdomains: <in sync | fixed>

Follow-up issues:
  - <issue link or issue-needed>

check-documentation-policy:
  - <PASS | PASS-WITH-NOTES | FAIL summary>
```

## Hard Rules

- Do not add local/private values to public docs.
- Do not document planned behavior as current behavior.
- Do not leave examples without runner/prerequisite/test status.
- Do not create a competing index.
- Do not hide slop by moving stale text to another file; fix it or track it.
