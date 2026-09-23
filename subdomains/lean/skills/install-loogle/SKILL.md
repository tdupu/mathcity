---
name: install-loogle
description: Use when asked to install or configure Mathlib, LeanSearch or Loogle MCP search, or to diagnose unavailable Lean MCP tools.
---

# Set up Mathlib search and Lean MCP

Input: active host, requested search/LSP capabilities and selected workspace.
Output: tested tool availability and versions, or exact blockers and fallbacks.

Discover the current session's tools first. Registration in another host and a
CLI “Connected” label do not establish callability here. Do not require Claude
Code for a Codex or other MCP host. Ordinary search does not authorize global
installation; use `search-mathlib`'s fallback unless setup is requested.

## Configure the selected host

For search plus local Lean, use [lean-lsp-mcp](https://github.com/oOo0oOo/lean-lsp-mcp).
Its host-neutral stdio entry uses command `uvx`, args `["lean-lsp-mcp"]`, env
`LEAN_PROJECT_PATH=/absolute/selected/workspace`. Check `uvx`, `lake` and `rg`;
if uv is unavailable, use a project-local virtual environment and its absolute
`lean-lsp-mcp` executable. Record the resolved package version. Register through
the active host's supported MCP settings at the requested scope. For Claude
Code specifically, consult `claude mcp add --help`; other hosts use their own
configuration, not the Claude CLI.

Read the project's contracts, `lean-toolchain`, Lake configuration and baseline.
The tested server 0.30.0 with leanclient 0.13.2 requires Lean >=4.24 for LSP.
Check the installed version's requirements; never upgrade a project's pin merely
to enable optional tooling. Older projects keep CLI verification. A separate
compatible search workspace cannot validate their code.

For search only, existing [mathlas](https://github.com/Archerkattri/mathlas) is an
alternative stdio entry: command `uvx`, args `["mathlas-mcp"]`; discover its
actual `search_formal_math` schema. No Lean toolchain is needed for this lookup.

## Verify capability, not just connection

Initialize the server, discover schemas, and make a real call. Current Lean MCP
names include `lean_leansearch(query,num_results)` for informal language and
`lean_loogle(query,num_results)` for names/types. Smoke-test Loogle `add_comm`
and a semantic query; inspect returned declarations, not just transport success.
For local LSP, test `lean_goal` or `lean_diagnostic_messages` against the chosen
compatible project. Check payload errors, partial results and diagnostic severity.
Restart/reconnect only as required by the host and report capabilities still
unavailable in this session.

Return server/version, workspace/pin, discovered tool names, actual response and
remaining gaps. Search hits require local `#check` and compiled applications
through installed `lean-search` before formal reuse. LSP diagnostics do not
replace `lean-verify` or source fidelity review.

When setup fails, report the specific startup/network/version/schema error and
continue broader work through `search-mathlib`'s direct HTTP or local-source/CLI
path. Unavailability is not an empty search. Stacks setup and tagged-source
retrieval belong to `search-stacks`.
