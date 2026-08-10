---
name: remember-this
description: Route an important mid-session insight to the right DURABLE store so it survives session death and is retrievable by ANY agent (Claude, Codex, future LLMs). Routes formal adjudicated verdicts to `bd create -t decision` (via [[record-decision]]), persistent cross-session facts/insights to `bd remember --key`, and (Claude sessions only) adds a one-line MEMORY.md pointer that LINKS to the bead — never duplicates content. Trigger phrases: "remember this", "don't lose this", "save this insight", "this needs to survive the session", "make this durable", "write this down somewhere permanent". Beads philosophy: beads are durable, sessions are ephemeral — the bead IS the memory.
---

# remember-this

Sessions die; beads don't. When an insight matters beyond this session, put it
in the bd store, then verify you can get it back out. Works for any agent that
can run `bd` — no Claude-specific tooling required.

## Decision tree

1. **Adjudicated verdict?** (closes deliberation: the human adjudicator ruling, architecture
   choice with rejected alternatives, policy lock)
   → `bd create -t decision` — follow **[[record-decision]]** (canonical; do
   NOT put decision content in `bd remember` alone).
2. **Persistent fact or design insight?** (knowledge future sessions need,
   mechanism description, hard-won debugging fact — no verdict to adjudicate)
   → `bd remember --key <slug> "<full insight>"`.
3. **Both shapes?** (a verdict that also needs keyword recall)
   → do 1, then add a `bd remember` entry that carries the insight AND cites
   the decision bead ID. This pairing is usually REQUIRED, not optional:
   `bd search` does not surface decision-type beads (verified 2026-07-08),
   so the memory entry is the only keyword path to the decision.
4. **Ephemeral observation / TODO?** → not this skill. Comment, chat, or
   `bd create -t task`.

## Store it

```bash
# Persistent fact/insight (key = short slug; re-running same key updates in place)
bd remember --key refinery-tree-contraction \
  "Refinery hook: find complete leaf, merge to parent, contract upward. [[bead: gsp-XXX]]"

# Formal decision (see record-decision for the full Rationale/Alternatives template)
bd create "Refinery merges complete leaves only" -t decision \
  --description "<Decision / Rationale / Alternatives / Affects>" \
  --notes "Session: ${GC_SESSION:-unknown}; context: <where this came from>"
```

### Combo (decision + keyword recall) — one invocation, two writes

The bead is canonical; the memory entry is the INDEX into it. Order matters:
create the decision first so the memory can cite its ID.

```bash
ID=$(bd create "Refinery merges complete leaves only" -t decision \
      --description "<Decision/Rationale/Alternatives/Affects>" --json | jq -r .id)
bd remember --key refinery-tree-contraction \
  "Refinery hook: bottom-up tree contraction — merge only complete leaves. Full record: [[bead: $ID]]"
```

Worked example: gsp-udi (decision) + `bd recall refinery-tree-contraction`
(index), banked 2026-07-08.

Notes go in the store of the repo you're standing in (`bd -C <dir>` to target
another rig). Never commit `.beads/` data to a code repo.

## Verify retrieval (mandatory — a memory you can't find doesn't exist)

```bash
bd memories <keyword>      # must surface the remember entry
bd recall <key>            # full text of one memory
bd show <decision-id>      # must show the decision bead
bd list -t decision        # decisions live here, NOT in bd search
bd search "<query>"        # title search over non-decision beads only
```

Caveat (verified 2026-07-08): `bd search` misses decision-type beads even by
exact ID — retrieve decisions via `bd show` / `bd list -t decision`, and rely
on the paired memory entry for keyword recall. If retrieval fails, fix the
key/title until it succeeds — that IS the skill.

## MEMORY.md pointer (Claude sessions only, optional)

Claude agents may add **one line** to their MEMORY.md that points to the bead:

```
- [Short title] — one-line gist; [[bead: <id>]] / bd recall <key>
```

Never duplicate the full content into MEMORY.md — the bead is canonical;
MEMORY.md fragments across accounts and is invisible to non-Claude agents.

## Cross-agent retrieval contract

- **Any agent** (Codex, Claude, future): `bd memories <keyword>`,
  `bd recall <key>`, `bd show <id>`, `bd search <query>`. Memories are also
  injected at `bd prime` time.
- **Claude agents additionally**: scan MEMORY.md pointers, then follow the
  `[[bead: <id>]]` link with `bd show` / `bd recall` for the real content.
