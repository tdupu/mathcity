# Label plan

The issue forms in `ISSUE_TEMPLATE/` apply `kind/*` and `status/needs-triage`
automatically. This file records the labels they expect and the exact commands
that create them.

> **None of the commands below have been run.** Label changes mutate the public
> repo, so they are the repo owner's call. Until they are run, the templates
> still work — GitHub silently drops label names it doesn't recognize rather than
> erroring, so issues will be filed correctly but arrive unlabeled.

## Target scheme

Borrowed from `gastownhall/gascity`: three orthogonal axes, nothing more.

| Label | Meaning |
| --- | --- |
| `kind/bug` | Reproducible defect or regression |
| `kind/feature` | New capability |
| `kind/docs` | Documentation wrong, missing, or misleading |
| `priority/p1` | Breaks many users, data loss, or unrecoverable |
| `priority/p2` | Significant friction, workaround exists |
| `priority/p3` | Polish, ergonomics, nice-to-have |
| `status/needs-triage` | Filed, not yet assessed by a maintainer |

## Path A — rename the three defaults, then create the rest (recommended)

`bug`, `documentation`, and `enhancement` are already applied to live issues
(#7–#11). Renaming preserves those associations; deleting and recreating would
strip the labels off existing issues.

```bash
gh label edit bug           --repo tdupu/mathcity --name "kind/bug"     --color d73a4a --description "Reproducible defect or regression"
gh label edit enhancement   --repo tdupu/mathcity --name "kind/feature" --color a2eeef --description "New capability"
gh label edit documentation --repo tdupu/mathcity --name "kind/docs"    --color 0075ca --description "Docs wrong, missing, or misleading"

gh label create "priority/p1"        --repo tdupu/mathcity --color b60205 --description "Breaks many users, data loss, or unrecoverable"
gh label create "priority/p2"        --repo tdupu/mathcity --color d93f0b --description "Significant friction, workaround exists"
gh label create "priority/p3"        --repo tdupu/mathcity --color fbca04 --description "Polish, ergonomics, nice-to-have"
gh label create "status/needs-triage" --repo tdupu/mathcity --color fef2c0 --description "Filed, not yet assessed by a maintainer"
```

## Path B — create all seven, leave the defaults alone

Use this only if you want `bug`/`enhancement`/`documentation` to keep existing
alongside the new scheme. It leaves two labels meaning the same thing, which is
why Path A is preferred.

```bash
gh label create "kind/bug"           --repo tdupu/mathcity --color d73a4a --description "Reproducible defect or regression"
gh label create "kind/feature"       --repo tdupu/mathcity --color a2eeef --description "New capability"
gh label create "kind/docs"          --repo tdupu/mathcity --color 0075ca --description "Docs wrong, missing, or misleading"
gh label create "priority/p1"        --repo tdupu/mathcity --color b60205 --description "Breaks many users, data loss, or unrecoverable"
gh label create "priority/p2"        --repo tdupu/mathcity --color d93f0b --description "Significant friction, workaround exists"
gh label create "priority/p3"        --repo tdupu/mathcity --color fbca04 --description "Polish, ergonomics, nice-to-have"
gh label create "status/needs-triage" --repo tdupu/mathcity --color fef2c0 --description "Filed, not yet assessed by a maintainer"
```

**Paths A and B are alternatives — never run both.** After Path A, the
`gh label create "kind/*"` lines in Path B would fail as already-existing.

## Verify

```bash
gh label list --repo tdupu/mathcity
```

## Notes

- **Priority is applied by the triager, not by the form.** Each template has a
  "Suggested priority" dropdown, but GitHub issue forms cannot map a dropdown
  answer to a label. The dropdown is triage input; a maintainer adds the
  `priority/*` label. Filers who don't know may answer "Unsure — please triage".
- **`status/needs-triage` is removed on triage**, not on close. It marks
  "nobody has looked at this yet", which is a different state from open.
- **No `area/*` labels are proposed.** mathcity's surfaces (skills, formulas,
  orders, gates, agents) are already carried by the `bug: <surface>: …` title
  convention the templates require, and gascity's scheme is deliberately
  kind + priority + status only. Adding a fourth axis duplicates the title for no
  routing gain.
- The remaining GitHub defaults (`duplicate`, `good first issue`, `help wanted`,
  `invalid`, `question`, `wontfix`) are untouched by both paths. They are
  orthogonal to the three axes above and cost nothing to keep.
