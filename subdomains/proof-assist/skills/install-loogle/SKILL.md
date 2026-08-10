---
name: install-loogle
description: Install and configure a Loogle / Mathlib4 search MCP server so Lean 4 lemma lookup (and, for Lean work, live goal/build/run tooling) works through a connected MCP tool instead of only the raw web API. Recommended for Lean work is lean-lsp-mcp (`claude mcp add lean-lsp uvx lean-lsp-mcp`) — full LSP server with loogle/lean_search/lean_hammer plus lean_goal/lean_build/lean_run_code, needs a Lean project + uv; the lightweight search-only option is mathlas (`claude mcp add mathlas -- uvx mathlas-mcp`), no Lean install. Verifies with `claude mcp list` and falls back to the direct Loogle JSON API (see search-mathlib) if no MCP connects. Use when the user says "install loogle", "set up mathlib mcp", "add loogle mcp", "install lean-lsp", "install-loogle", "configure loogle search", or when search-mathlib reports no Loogle MCP is connected. Companion to search-mathlib (which USES the server this skill installs).
---

# install-loogle

Installs an MCP server that exposes **Loogle** (the Lean 4 / Mathlib4 search
engine) as a callable tool, mirroring how `stacks` and `scholar` are set up in
this subdomain. Loogle itself is a hosted web service; this skill wires a local
MCP server in front of it so lemma search is a first-class tool call.

## Pre-flight

- `claude` CLI must be on PATH (`command -v claude`). If missing, stop and tell
  the user to install/point at the Claude Code CLI first.
- `uvx` (from `uv`) is needed for the `uvx` install form. Check `command -v uvx`;
  if absent, either install `uv` (https://docs.astral.sh/uv/) or use a clone +
  `pip install -e .` form of whichever server is chosen.

## Choose a server

Two good options, by whether you are *searching* Mathlib or actually *working
in Lean*:

### Recommended for Lean work — lean-lsp-mcp

Full LSP-based server. Exposes search — `loogle`, `lean_search`, `lean_finder`,
`lean_hammer`, `lean_state_search` — **plus** live Lean-project interaction:
`lean_goal`, `lean_build`, `lean_run_code`, `lean_local_search` (goal states,
diagnostics, build, run). Best whenever you have a Lean project open.

```bash
claude mcp add lean-lsp uvx lean-lsp-mcp
# project-scoped:
claude mcp add lean-lsp -s project uvx lean-lsp-mcp
```

Requires: a valid Lean project (`lean-toolchain` + `lakefile.lean|toml`), `uv`
on PATH, and a one-time `lake build` first (recommended); `ripgrep` for local
search. Optional **Local Loogle** avoids Loogle rate limits (~2 GB, needs
git+lake, Unix only). Beta — grants filesystem access + external network calls;
may time out on the first `lake serve`.

### Lightweight, search-only — mathlas

No Lean toolchain needed. Wraps **Loogle + LeanSearch** behind one
`search_formal_math` tool with a 7-day cache. Use for quick Mathlib lookups
from a non-Lean repo (e.g. searching from the Magma / hecke side).

```bash
claude mcp add mathlas -- uvx mathlas-mcp
```

Verify either:

```bash
claude mcp list | grep -iE 'lean-lsp|mathlas'    # want: "✓ Connected"
```

Once a server is connected, `search-mathlib` uses its search tool instead of
the raw API.

## Fallback — no MCP required

If the MCP will not connect (network, `uvx` missing, package unavailable),
**do not block Mathlib search** — `search-mathlib` already queries the Loogle
JSON API directly and fails soft:

```bash
curl -s "https://loogle.lean-lang.org/json?q=add_comm"
```

Report the MCP failure, then point the user at `search-mathlib` for the
direct-API path. Installation is an enhancement (caching, one tool call), not a
prerequisite for search.

## Alternative server

| Server | What it adds | Install |
|--------|--------------|---------|
| `lean-mathlib-docs-mcp` | Local Mathlib docs search only | see repo (Sources) |

Cite whichever server you install in the `## Sources` section of any work that
uses it.

## Sources / Citations

Cite these wherever this server or its results are used (per repo policy: cite
all sources).

- **Loogle** — the Lean 4 / Mathlib4 search engine, hosted by the **Lean FRO**
  (Lean Focused Research Organization). https://loogle.lean-lang.org
  (JSON API: `https://loogle.lean-lang.org/json?q=<query>`).
- **mathlas MCP** — Loogle + LeanSearch proxy with cache.
  https://github.com/Archerkattri/mathlas
- **lean-lsp-mcp** — LSP-based Lean MCP server with Loogle integration.
  https://github.com/oOo0oOo/lean-lsp-mcp
- **lean-mathlib-docs-mcp** — local Mathlib docs search MCP.
  https://github.com/CriticalLine/lean-mathlib-docs-mcp
- **Mathlib4** — the Lean 4 mathematical library being searched.
  https://github.com/leanprover-community/mathlib4
- **Mathlib4 docs** — rendered declaration documentation.
  https://leanprover-community.github.io/mathlib4_docs/

## See also

- `search-mathlib` — the skill that USES this server (and works without it via
  the direct JSON API).
- `mcp/stacks/README.md`, `mcp/scholar/README.md` — the sibling MCP install
  patterns this skill mirrors.
