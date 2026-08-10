# Repair No-Brainer And Gates

This filter decides whether a brief is a known mechanical no-brainer or must
go through the full brief presentation path. It is the G9 gate inside the
16-gate brief registry, not a standalone merge or close mechanism.

## Purpose

The brief stack can contain work that is already mechanically settled: stale
scratch cleanup, already-merged close-done cases, or execution confirmations
with concrete proof. The no-brainer filter recognizes those shapes so the
presentation layer can collapse them into compact form and reduce human review
load.

## Inputs

- A brief markdown file produced by `brief-prep` or `create-brief`.
- Frontmatter and body evidence for the proposed disposition.
- The category registry at
  `assets/brief-pipeline/no-brainer-categories.toml`.
- Gate evidence, especially G5, G5b, G9, G12, G13, G14, and G16.

## Outputs

The classifier emits one JSON object per brief with:

- `no_brainer`: `true`, `false`, or `"candidate"`;
- `category`: a known registry category, `capability-blocker`, or `null`;
- `compact_eligible`: whether `present-it` may use compact form;
- `confidence`;
- `reason` or `proposed_registry_extension`.

For known no-brainers, the classifier may copy the brief into
`.pile/.no-brainer/`. For novel candidate shapes, it may write a candidate
record under `.gates-candidate-pile/`. It never closes beads, updates verdicts,
or dispatches work.

## How To Invoke

Most users should invoke this through the brief pipeline:

```sh
/brief-prep <artifact>
```

For a direct classifier check:

```sh
/catch-no-brainer <brief-path>
```

The formula/order layer includes `no-brainer-classify`,
`no-brainer-candidate-curate`, and `no-brainer-process`, but those are system
plumbing. Use them directly only when debugging the pack.

## Safety Rules

- Stop gates run before G9. Server-touching and user-skill-touching work cannot
  pass the shortcut path without explicit human authorization.
- `auto_merge_enabled=false` at the city or rig level halts auto-execution.
- Capability blockers are not compact-form approvals; they route to blocker
  resolution and then reclassification.
- Unknown or low-confidence shapes become candidates for review, not shortcuts.

## Test Status

The current fixture harness is:

```sh
bash mathcity/skills/catch-no-brainer/fixtures/run.sh
```

The G9 evidence check is:

```sh
GC_BRIEF_PATH=<brief.md> sh mathcity/assets/scripts/checks/brief-no-brainer-classification-evidence.sh
```

In the July 2026 E2E pass, the repair no-brainer/gate path passed against the
fixture suite and a live repaired brief carrying explicit G9 evidence.
