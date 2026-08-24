# mctl MCP: detecting a stale server and rebinding deliberately

Parent: [MCTL-MCP-IMPLEMENTATION-PLAN.md](./MCTL-MCP-IMPLEMENTATION-PLAN.md)
Issues: [#210](https://github.com/tdupu/mathcity/issues/210) (no rebind path),
[#172](https://github.com/tdupu/mathcity/issues/172) (server cannot report its
own staleness), [#164](https://github.com/tdupu/mathcity/issues/164) (the
serving-commit stamp this copies).

> This is the deliberate procedure a session follows when a freshly-landed MCP
> tool or fix is not reachable. It restarts a process; it does **not** end the
> session that requests it. Hot-reload is intentionally NOT implemented — see
> "Why not hot-reload" below.

---

## The problem in one paragraph

A running `mctl mcp serve` process imports `mctl_core` **once, at startup**, and
serves that code until it exits. A merge to `main` does not reach it. So a tool
can land on `main` with tests green and be callable by nobody: every session
that started before the merge is bound to a server running the older code, and
the client fixes its tool roster at session start with no refresh verb. This is
the `#210` symptom — `create_github_issue` landed at `b7d7a50` and was absent
from every running session's binding minutes later.

## Step 1 — Detect: ask the server what commit it is serving

Every `initialize` and `tools/list` response now carries the commit the process
imported at startup, under the MCP-reserved `_meta` envelope:

```jsonc
// tools/list result (and initialize result)
{
  "tools": [ /* ... */ ],
  "_meta": {
    "mctl": {
      "serving": {
        "commit": "b7d7a50",          // short SHA the PROCESS imported at start
        "known": true,                // P6.2: false => could not read; commit is null
        "started_at": "2026-08-23T21:17:04+00:00"
      }
    }
  }
}
```

This is captured **once, at import** (`mctl_core/serving.py`), not re-read per
request. That is deliberate: a stale process must report its OWN startup commit,
because that is the value you diff against current `origin/main` to see the
drift. A per-request `git rev-parse` would always look current and hide exactly
the staleness this exposes (the `#172` false-negative).

**Honesty rule (`P6.2`).** If `known` is `false`, the commit could not be read
(no git, detached tree, timeout). That is a statement about the check, not a
clean bill of health — treat it as "age unknown," never as "up to date."

## Step 2 — Compare against current main

```bash
cd <mathcity-pack-root>            # the checkout the server runs from
git fetch origin
git rev-parse --short origin/main  # the current landed code
```

If the server's `_meta.mctl.serving.commit` differs from current `origin/main`,
the server is serving older code and anything merged since is unreachable from
it. (This is the same comparison `mctl_dashboard.staleness.compare(served=...,
current=...)` performs for the dashboard banner — the MCP now exposes the same
`served` value the banner already had.)

## Step 3 — Rebind deliberately (without ending the session)

The MCP server is a **stdio child** of whatever launched it. Rebinding means
restarting that child so it re-imports `mctl_core` at the current commit. Pick
the case that matches how it was launched:

- **Session-owned stdio server** (the common case: the client spawned
  `mctl mcp serve` as a child). Reconnecting the MCP server respawns the child
  against current code. In Claude Code this is the MCP-server reconnect/restart
  control for the `mctl` server — it does **not** clear the session's
  conversation context. Prefer this over `/clear` or ending the session, which
  is what `#210` is trying to make unnecessary: a Mayor session carries hours of
  context that must survive the rebind.

- **Dashboard-spawned server** (`mctl dashboard serve` launches its own
  `mctl mcp serve` child — see the implementation plan §8). Restarting the
  dashboard process restarts its MCP child with it. This is the same deliberate
  bounce `#164` documents for the dashboard's own staleness banner.

- **Hand-launched server** (a bare `mctl mcp serve` in a terminal). Stop it
  (Ctrl-C / kill its PID) and re-run the identical command from the current
  checkout. Confirm with `git -C <mathcity-pack-root> rev-parse --short HEAD`
  before relaunching.

## Step 4 — Verify the rebind

Call `tools/list` again and confirm `_meta.mctl.serving.commit` now equals
current `origin/main`, and that the newly-landed tool appears in `tools`. Only
then is the fix actually deliverable to this session.

---

## Why not hot-reload

`#210` rejects hot-reload as the default answer, and this procedure implements
that decision:

1. **Silent auto-correction hides staleness.** `#164`'s whole design argument is
   that a process quietly swapping the code under a live caller is worse than a
   visible stale one. A stamp an operator can read lets them act; a silent
   reload removes the choice and the evidence.
2. **A tool schema is a contract.** Reloading modules under a live server could
   change a tool's input/output schema mid-session, out from under a caller that
   already bound to the old one — a contract swap with no handshake. Reloading
   Python modules under a running server is also its own failure class.

So staleness is made **visible** (Steps 1–2) and refresh is made a **deliberate
choice** (Step 3), rather than automatic. Detectability first; the rebind stays
an operator decision with a known blast radius.

## Where this is implemented

- `assets/scripts/mctl_core/serving.py` — captures the serving commit once at
  import; `serving_info()` builds the block (with the `P6.2` `known` flag).
- `assets/scripts/mctl_core/mcp_server.py` — `_serving_meta()` rides it on the
  `initialize` and `tools/list` responses under `_meta.mctl.serving`.
- `tests/mctl/test_mcp_serving_commit.py` — pins that the commit is captured at
  import (not per call), that it is honest when unreadable, and that both
  responses carry it additively.
