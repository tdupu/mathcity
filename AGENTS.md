# AGENTS.md — orientation for agents working in `mathcity`

This is the standalone `mathcity` pack (the Gas City pack family). Start here, then
defer to the authoritative documents below — this file is a signpost, not a
restatement.

- **Repo layout:** [`LAYOUT.md`](./LAYOUT.md) — what each top-level directory holds
  and the `subdomains/` sub-pack pattern.
- **Pack/plan hygiene:** [`subdomains/dev/POLICY.md`](./subdomains/dev/POLICY.md) —
  how work is planned, executed, and audited (the P-rules; `check-plan-hygiene` /
  `check-build-hygiene` enforce them). Run `check-plan-hygiene` before dispatching a
  plan.
- **Rule-prefix registry:** [`docs/rule-prefix-registry.md`](./docs/rule-prefix-registry.md).
- **ADRs:** [`docs/adr/`](./docs/adr/).

## Dashboards — there are TWO; never conflate them

The single most common confusion in this repo. Both are rendered by **one
codebase** (`assets/scripts/mctl_dashboard/`), which is why they blur together.

| Dashboard | Purpose | Design + status |
|---|---|---|
| **City dashboard** (a.k.a. mathcity/mctl dashboard — one name, "city dashboard") | Operator **observability**: rigs, orders, molecules, pools, health | [`docs/superpowers/plans/dashboards/city/`](./docs/superpowers/plans/dashboards/city/) |
| **Briefs dashboard** (a.k.a. "Brief Manager") | **Adjudication** of present-it briefs awaiting a human verdict | [`docs/superpowers/plans/dashboards/briefs/`](./docs/superpowers/plans/dashboards/briefs/) |

Before writing about "the dashboard," say **which one**. The signpost + the
built-vs-designed status for each is
[`docs/superpowers/plans/dashboards/README.md`](./docs/superpowers/plans/dashboards/README.md) —
read it before touching dashboard code or filing a dashboard issue.

## Where dashboard design docs and plans go

Dashboard **design handoffs, prototypes, and implementation plans** live under:

```
docs/superpowers/plans/dashboards/city/     # city dashboard
docs/superpowers/plans/dashboards/briefs/   # briefs dashboard
```

Do **not** scatter them into `docs/` (reserved for reference/ADRs/filters per
`LAYOUT.md`), `subdomains/dev/docs/`, or the `plans/` root. One dashboard's material
never lands in the other's folder. Superpowers design specs (non-dashboard) follow
the brainstorming default: `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`;
implementation plans: `docs/superpowers/plans/`.

## Running & tearing down a dashboard (the #154 contract)

A `mctl dashboard serve` process has no natural exit condition, so a debugging
session that starts one leaves it running forever unless the agent stops it.
Eight were once live at once; the danger is not the leak but the ambiguity —
a browser pointed at a stale server on a stray port shows a fix "working" while
the canonical dashboard never got it. **If you start a dashboard, you tear it
down.**

- Every `mctl dashboard serve` now stamps itself under `<city>/.mctl/dashboards/`
  (pid, port, and the commit it imported); dead stamps self-prune.
- **All four lifecycle verbs are typed** (mc-lj0sh): an MCP-only Mayor can now
  drive the whole lifecycle without dropping to the CLI.
- **See what is running:** the `dashboard_status` MCP tool (or read the stamp
  dir) — pid, port, serving commit, and staleness per instance.
- **Start one:** the `dashboard_serve` MCP tool (or `mctl dashboard serve`) —
  dry-run by default; refuses `MDSH_PORT_IN_USE` rather than double-binding a
  port that already has a stamped dashboard, and confirms the child bound its
  port before reporting success (a child that dies first is `MDSH_SERVE_FAILED`;
  one still coming up at the deadline is `still_starting`, never a failure).
- **Tear it down at session end / when parking a branch:** the
  `dashboard_teardown` MCP tool (or `mctl dashboard teardown --city <root>`)
  stops every dashboard for that city and clears its stamp; `--port N` stops
  just one. A stop that did not take is reported (`MDSH_TEARDOWN_FAILED` / a
  non-zero CLI exit) with the stamp left in place, so it is safe in a
  session-end hook.
- Restarting the canonical instance onto current code is a **deliberate**
  `dashboard_restart` (#207) — never an automatic reload (#164/#210).

## Git / lane (outside agents)

Repo work happens in `~/repos/mathcity`; commits reach the running city and the
`~/gt` twin through `origin` (`tdupu/mathcity`). Irreversible git operations (push,
merge, PR) gate through the human via `authorize-git-operation` — commit locally,
present the gate, never push unprompted.
