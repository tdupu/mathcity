---
name: garbage-collect
description: HUMAN-GATED pre-submission strip of retained editorial machinery from a tex file: enumerate candidates (retained ST5 tags, agent replies, agent comments, superseded commented-out text), present the full list, execute ONLY the approved strip, verify the compile. Use when the user says "garbage collect", "strip the editorial comments", "prep this for arXiv/submission". Human markers and human comments are NEVER stripped unless the human explicitly includes them. NOT the acceptance step of the revision cycle (a human act).
---

# garbage-collect

Runs [../../WRITERS.md](../../WRITERS.md) preamble (resolution + target); the strip itself is
this leaf's gated middle:

## Enumerate → gate → strip

1. Enumerate candidates with counts and line numbers, by class:
   (a) ST5 tag lines (`% >>> [...]` / `% <<< [...]`); (b) superseded
   commented-out text between tags; (c) `\agentreply{...}` instances
   (visible in draft PDFs — their removal changes rendered output:
   say so); (d) agent metadata comments (ephemeral cache, D4);
   (e) the `\agentreply` macro definition once no uses remain.
2. Present the full list. The human approves per class or per item —
   and may add human-authored items (their own `\taylor{}` leftovers)
   EXPLICITLY; nothing human-made enters the strip by default.
3. Execute exactly the approval. GC output is the clean file itself —
   stripping the machinery is the point, and the git diff is the
   record (no ST5 tags on a strip). Compile before/after
   (check-latex); report the rendered-output changes (removed colored
   replies) and confirm zero statement-level changes.
4. Commit only with explicit authority (ST8), pathspec-scoped.

## Red flags

| Thought | Reality |
|---|---|
| "Old commented-out text is obviously junk" | It is the low-tech version control (ADR 0003). Gate it. |
| "I'll strip the \taylor{} leftovers too, it's going public" | Human markers are the human's. Explicit inclusion only. |
