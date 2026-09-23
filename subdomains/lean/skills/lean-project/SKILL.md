---
name: lean-project
description: Use when adding Lean formalization to a repository or locating the workspace for a Lean task.
---

# Select or establish the Lean workspace

Input: repository, authorized deliverable, local instructions and layout.
Output: workspace path, library/module roots, pinned dependencies, scratch path,
the registry-manifest path, and the command that verifies setup.

1. Read the nearest instructions and `LAYOUT.md` when present. Locate existing
   lakefiles and toolchains before creating anything. Reuse the relevant project;
   do not upgrade it, overwrite its manifests or move it to satisfy a default.
2. For a new workspace, default to repository-root `lean/` beside `latex/`.
   Honor a declared alternative. If a binding layout must change, route that
   amendment through installed `new-repo-layout-policy`, carrying existing user
   authorization; otherwise report the exact unresolved layout choice.
3. Read [tool recipes](../lean-workflow/references/tools.md). Select a concrete
   Lean/Mathlib-compatible pin. Create the smallest library workspace needed;
   record its toolchain, lakefile and dependency lockfile. Add source modules to
   actual build targets. Core-only mathematics need not acquire Mathlib.
4. Ignore `.lake/` and generated build output in the workspace. Put experiments,
   logs and source maps under the declared scratch root, default dated `ai/` at
   repository root. Keep reusable formalization sources in the Lean workspace.
5. Declare the workspace's documentation paths, all inside it beside the library
   root: an assumption census, a statement-to-declaration map, and — when the
   project may be registered — a **Palomar manifest at `<workspace>/PALOMAR.md`**.
   A registry entry describes a Lean workspace at an exact commit, so its manifest
   belongs with that workspace, never in a separate repository-root directory.
   Report the path at setup even when the file does not yet exist, so later work
   does not invent a location. Preparing a manifest and submitting it are separate
   acts, and submission needs its own explicit authorization; a manifest states
   which has occurred. Per entry it records the declaration name, its elaborated
   type quoted verbatim from Lean, an informal claim rendered from that type rather
   than from memory, the axioms, and an explicit *does not claim* block — registries
   check informal-against-formal agreement, and an absent claim is not visible to a
   reviewer unless it is written down.
6. Invoke `lean-doctor`; return its evidence and any setup blocker. An unavailable
   compiler still permits source analysis but cannot produce a checked result.

Example: a repo already using `formal/Algebra/` keeps that project; a manuscript
repo with only `latex/` normally gains `lean/`, with run evidence under `ai/`.
