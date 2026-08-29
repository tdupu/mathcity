# Typed bead-write verbs on the mctl MCP surface (mc-p0wps)

| Field | Value |
| --- | --- |
| Status | Approved (design), 2026-08-28 |
| Bead | mc-p0wps (P1) — executes brief mc-i9bwz option A |
| Provenance | mc-i9bwz **approve, option A**, Taylor Dupuy 2026-08-28, MCTL-TRACE ad503a55-8cec-42f6-ae39-b5f2ed916e03. Second verdict on the gap (mc-qcnaz approved hold/release earlier, nothing built). |
| Lane | `~/repos/mathcity` (outside-agent; conservative git, gate before push) |

## What is being decided / built

The mctl MCP surface can dispatch work in but has **no verb to close, hold, or
release a bead**. Today it exposes exactly three bead-touching mutations —
`bead_comment` (append-only), `create_defect_bead`, `create_issue_bead`. Add
three typed verbs behind the interface (P7.3 — fill the gap, do not route
around it):

- `bead_close`
- `bead_hold`
- `bead_release`

The MCP-only rule is intentional handicapping for debugging (Taylor 2026-08-22):
the value is that hitting a wall produces evidence. These verbs fill the gap the
right way — through mctl — rather than by carving a shell-out exception.

## Architecture

Follow the established four-part pattern (precedent: `bead_comment`,
`molecule_cancel`):

1. **Input dataclass** — per verb, in a new module `assets/scripts/mctl_core/bead_writes.py` (parallel to `bead_comments.py`).
2. **Pure `plan_*` builder** — reads beads, runs refusal checks (as blocking `Diagnostic` preconditions or raised `MutationError`), returns an `EffectPlan`. No I/O side effects; refusals are visible in dry-run because `dry_run_payload` and `apply_effect_plan` share `_raise_if_blocked`.
3. **Thin `_handle_*`** in `mcp_server.py` — builds the plan, returns `_effect_payload(ctx, plan, _dry_run(arguments))`.
4. **`ToolSpec`** in the `TOOLS` tuple — `mutating=True`, `external_ready=False`, input schema carries `"dry_run": DRY_RUN_PROPERTY`, output `response_schema(_EFFECT_RESPONSE, ...)`.

The direct precedent for the close path is `plan_molecule_cancel` (effects.py):
it closes via `BeadUpdate(status="closed", if_status=step.status)`, carries a
`force` boolean, and computes open steps via `open_steps_of`. Our three verbs
are variations on it — `bead_close` closes **one** bead (cascade is
`molecule_cancel`'s explicit job).

### One genuinely new mechanism: label writes

`bead_hold`/`bead_release` set and clear a `hold:*` **label** (mc-qcnaz option A —
not a status change, not defer/undefer). mctl has no label-mutation apply path
today (it has update/create/relate/comment). Add:

- `BeadLabelChange` carried on `EffectPlan` (parallel to `bead_comments`).
- `apply_bead_label` in `beads.py` shelling `bd label add`/`bd label remove`
  (`_apply_bd_label`), with the same subprocess/timeout discipline as the other
  `_apply_bd_*` helpers.

## The three verbs

### `bead_close`

Input: `bead_id`, `reason` (nullable), `force` (bool, default false), `dry_run`
(default true).

Refusals (both dry-run-visible, emitted from `plan_bead_close`):

1. **Molecule root with open steps** — `is_molecule_root(bead)` (metadata
   `gc.kind == "workflow"`, EXACT match) AND `len(open_steps_of(bead_id, beads)) > 0`
   → `MBCL_ROOT_HAS_OPEN_STEPS` (FATAL). **`force` does NOT bypass this**
   (adjudicated 2026-08-28): it is the false-success guard mc-i9bwz §5.1 exists
   to create; deliberate cascade-close is `molecule_cancel`. The message names
   the count and the root, and points at `molecule_cancel`.
2. **Blocked by open dependencies** — reimplemented as a plan-time precondition
   (bd's own refusal only fires at apply time, so it would not show in dry-run):
   `MBCL_BLOCKED_BY_OPEN_DEPS` (ERROR). **`force` downgrades it** and the apply
   passes `bd update --status closed --force` (bd's own gate + force clause).

Apply: `BeadUpdate(bead_id, status="closed", reason=reason, if_status=observed.status)`
→ inherits `MCTL_BEAD_UPDATE_RACE_LOST` (exit 13) for free — a concurrent writer
loses the race loudly.

Non-existent bead → `MBCL_NO_SUCH_BEAD`.

### `bead_hold`

Input: `bead_id`, `label` (default bare `hold`; a `hold:*` value accepted),
`dry_run`.

Apply: `apply_bead_label` add. Refusals: non-existent bead
(`MBHD_NO_SUCH_BEAD`); a slash in the label (`MBHD_LABEL_HAS_SLASH`, honoring
MBRF033 — colon-form or bare only). Label add is idempotent; no `if_status`
(labels are not status).

### `bead_release`

Input: `bead_id`, `label` (which hold label to clear), `dry_run`.

Apply: `apply_bead_label` remove. Refusal: non-existent bead
(`MBRL_NO_SUCH_BEAD`).

## The six MCP declaration guards

Three new tools → keep all six consistent (checklist template:
`tests/mctl/test_commission_brief_tool.py`):

1. `DECLARED_TOOLS` (test_mcp_server.py) — add the three names.
2. `EXPECTED_TOOLS` (mctl_mcp_harness.py) — add the three names.
3. Hardcoded count assertions ×2 (test_mcp_client_harness.py) — 48 → 51.
4. Schema snapshot (tests/mctl/fixtures/mcp_tool_schemas.json) — regenerate:
   `MCTL_UPDATE_MCP_SNAPSHOT=1 python3 -m pytest tests/mctl/test_mcp_schema_snapshots.py`.
5. `ALLOWED_TOOLS` (dashboard client.py) — **NOT added**; these are agent-facing,
   not consumed by a dashboard screen → classify `DELIBERATELY_UNREACHABLE` in
   `test_dashboard_tool_reachability.py` (as `beads_list`/`beads_show` are). The
   `len(ALLOWED_TOOLS) == 31` assertion stays 31.

## Diagnostic codes (assets/mctl/diagnostics.toml)

Per-verb families paralleling `MBCM_` (bead_comment): `MBCL_*` (close), `MBHD_*`
(hold), `MBRL_*` (release). Each new code registered with `severity` / `meaning`
/ `module`.

## Testing (TDD, P6.2 — every refusal ships an observed failing case)

- `MBCL_ROOT_HAS_OPEN_STEPS`: close a root with an open step → refused; close the
  same root after its steps close → allowed. **Mutation-proven** — a vacuous
  guard (always-allow) must fail this test.
- `force` does NOT bypass the root refusal (negative control): `bead_close
  --force` on a root with open steps still refuses.
- `MBCL_BLOCKED_BY_OPEN_DEPS`: blocked bead refused; `--force` downgrades and
  applies `bd update --force`.
- `if_status` race: an update whose observed status changed loses loudly
  (`MCTL_BEAD_UPDATE_RACE_LOST`).
- Dry-run writes nothing and rings nothing (#188): each verb previews with no
  side effect.
- `bead_hold` adds the label; `bead_release` removes it; a slashed label is
  refused (`MB*_LABEL_HAS_SLASH`).
- Snapshot + declaration-guard agreement (the six guards) all pass.

## Known limitation (flagged, not silently assumed)

The `hold:*` label's **effectiveness** — actually excluding a held bead from the
claimable/ready set — depends on the ready/claim query passing `--exclude-label
hold:*`. No consumer of that convention is wired in bd / gc / mctl that I could
find (2026-08-28). Per mc-qcnaz the **verb** (set/clear the label) is the
deliverable and mc-1pale (making the hold bite) stays open. `bead_hold` therefore
sets a label that may not yet be respected by the claim path; this is filed as a
P7.3 interface follow-up rather than assumed working.

## Scope discipline / out of scope

- No `pool_pause`/`pool_resume` (mc-qcnaz option B explicitly not granted).
- No cascade-close (that is `molecule_cancel`).
- `bead_close` reads molecule state via `molecules.py` (read-only) — **no
  `work.py` edit**, so no collision with the mc-u9eun dispatch fix.

## Compliance (check-plan-hygiene: approve)

P7.3 (fills the gap behind the interface), P6.1 (loud refusals), P6.2 (observed
failing cases), P6.3 (bd deadlines report deadline_exceeded), P1.19 (close is the
allowed status-lifecycle carve-out), P5.5 (no Co-Authored-By; `[autogenerated by
Claude ...]` footer), P4.2 (six guards consistent), P3.6 (run
improve-documentation before completion).
