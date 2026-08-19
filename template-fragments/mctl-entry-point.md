# mctl entry-point fragment (Slice 7)

**Canonical source for the MathCity control-CLI call site.** Every mathcity
skill that reads or mutates brief / work state copies the block below verbatim.
`tests/mctl-shim-callsite/smoke_test.sh` greps every wired skill for it and
fails if a skill invents a second discovery rule or bypasses `bin/mctl`.

## Why a fragment rather than "just call mctl"

Skills are prompt text executed as shell, from whatever cwd the session happens
to be in. `bin/mctl` is a shim that resolves *its own* checkout root and hands
off to `assets/scripts/mctl.py`; `mctl_core/context.py` then owns city and rig
discovery and fails loudly rather than guessing. A skill that re-derives either
of those is the second resolution rule the shim exists to prevent — it will work
in one checkout and silently address the wrong city in another.

`bin/mctl` is the ONLY supported entry point. Never invoke
`assets/scripts/mctl.py` directly.

## The block

```bash
CITY_ROOT="${CITY_ROOT:-$HOME/gt}"

# `bin/mctl` is the ONLY supported entry point for the MathCity control CLI.
# Never invoke assets/scripts/mctl.py directly — the shim owns repo-root
# resolution, and mctl_core/context.py owns city/rig discovery.
PACK_ROOT="${MATHCITY_PACK_ROOT:-$(
  sed -n '/^\[defaults.rig.imports.mathcity\]/,/^\[/p' "$CITY_ROOT/city.toml" \
    | sed -n 's/^source *= *"\(.*\)"/\1/p' | head -1
)}"
MCTL="$PACK_ROOT/bin/mctl"
[ -x "$MCTL" ] || { echo "mctl entry point not found at $MCTL"; exit 1; }
```

## Rig scoping

Plain commands operate on exactly one resolved rig, so pass `--rig` explicitly
whenever the bead prefix tells you which rig owns the bead:

```bash
rig_for_prefix() {   # bead prefix -> rig NAME registered in city.toml
  case "$1" in
    he-*)  echo hecke ;;
    gsp-*) echo gascity-packs ;;
    gs-*)  echo gascity ;;
    as-*)  echo agent_skills ;;
    mc-*)  echo mathcity ;;
    tgi-*) echo tdupu_github_io ;;
    lm-*)  echo lmfdb ;;
    ho-*)  echo homog ;;
    ja-*)  echo jacobi ;;
    dv-*)  echo differential_valuations ;;
    mca-*) echo magma_clifford_algebras ;;
    mda-*) echo magma_diff_alg ;;
    *)     echo "" ;;   # unmapped — see "the gt-* gap" below
  esac
}
```

### The `gt-*` gap — a real limitation, not a choice

`gt-*` beads live in the city-root HQ store, which is **not a registered rig**
in `city.toml`. `mctl --rig gt` therefore fails with
`MCTL_CONTEXT_UNKNOWN_RIG`, and every `gt-*` bead is unreachable through the
rig-scoped path. Skills that must handle `gt-*` keep a direct `bd` fallback for
those ids and say so. Do not pretend the rig resolves.

### Cross-rig reads

`--all-rigs` **is implemented** (`mctl_core/city.py`) and is the only sanctioned
way to read the whole city. It resolves every registered rig concurrently and
tags each row with the `rig_id` of the store it came from. Do not build a
per-skill loop over rigs — that is the duplicate control surface this whole
slice exists to remove, and it is slower besides (~3.9s serial vs ~1.3s across
the live 16 rigs).

Its exit code is **not** a simple pass/fail: `mctl` exits 1 when any rig was
unreadable, and still prints the full payload, precisely so a caller cannot
mistake a partial answer for a complete one. Branch on the payload, never on
the exit code alone, and name every degraded rig in your output.
`skills/check-briefs/SKILL.md` step 3 is the reference implementation.

## The MCP surface — the target, with `bin/mctl` as the bridge

Issue #60 D1 resolved the surface question: **MCP is the target; `bin/mctl` is
the bridge.** The organizing goal is that agents "act like python and less like
chat bots" — the same operation, spelled the same way, every run. A typed tool
call beats a prose command for mechanical reasons:

- arguments are schema-validated **before** anything executes, so a bad call
  fails at the boundary instead of halfway through a mutation
- there is no shell — no quoting bugs, no `$VAR` expansion, no PATH
  resolution, and **no cwd sensitivity**
- the tool list *is* the discovery surface: an agent cannot invoke a tool that
  does not exist, and cannot paraphrase a signature the way it can paraphrase
  prose

The server is `assets/scripts/mctl_core/mcp_server.py` (`mctl`, stdio). When it
is connected to a session its tools appear as **`mcp__mctl__<tool>`**.

### The 16 tools, and the CLI command each mirrors

Same core, same diagnostics, same trace ids — two front doors. The mapping is
mechanical, so anything this fragment says about a CLI command is equally true
of its tool:

| MCP tool | CLI equivalent | mutating |
| --- | --- | --- |
| `mcp__mctl__context_resolve` | `mctl context resolve` | no |
| `mcp__mctl__context_rigs` | `mctl context rigs` | no |
| `mcp__mctl__briefs_list` | `mctl briefs list` | no |
| `mcp__mctl__briefs_show` | `mctl briefs show` | no |
| `mcp__mctl__briefs_options` | `mctl briefs options` | no |
| `mcp__mctl__briefs_doctor` | `mctl briefs doctor` | no |
| `mcp__mctl__briefs_validate` | `mctl briefs validate` | no |
| `mcp__mctl__briefs_adjudicate` | `mctl briefs adjudicate` | **yes** |
| `mcp__mctl__briefs_defer` | `mctl briefs defer` | **yes** |
| `mcp__mctl__briefs_create` | `mctl briefs create` | **yes** |
| `mcp__mctl__work_ready` | `mctl work ready` | no |
| `mcp__mctl__work_status` | `mctl work status` | no |
| `mcp__mctl__work_provenance` | `mctl work provenance` | no |
| `mcp__mctl__work_dispatch` | `mctl work dispatch` | **yes** |
| `mcp__mctl__trace_show` | `mctl trace show` | no |
| `mcp__mctl__trace_replay_preview` | `mctl trace replay-preview` | no |

### The rollout gate — why the tools are usually absent

`mcp_server.py` gates the tool list by client class:

- **`external`** (the default) sees **zero** tools until an operator sets
  `MCTL_MCP_ENABLE_EXTERNAL_TOOLS=1`; even armed, the four mutating tools stay
  hidden, because `external_ready=False` on each.
- **`internal`** (`MCTL_MCP_CLIENT_CLASS=internal`) sees all 16.

So the surface being absent is the **designed default**, not a fault. Registering
the server is an operator action, it only takes effect at session start, and its
disposition is still undecided. **Never write a skill that assumes the tools are
there.**

### Detecting the surface — look, do not probe

**Read your own tool list.** The tools are either registered in this session or
they are not, and you can see which without running anything:

- `mcp__mctl__*` tools present → the MCP is live. Prefer typed tool calls.
- no `mcp__mctl__*` tools → the MCP is not connected in this session. Use
  `bin/mctl`. This is the common case today and is completely fine.

**Do not probe by calling a tool to see whether it answers.** Invoking an
unregistered tool is an error, and a step whose failure mode is an error is not
a detection method. There is likewise no shell command that reports the
session's tool list — checking for a `.mcp.json` on disk proves nothing, since
the file is inert until the session that reads it starts.

### The degradation rule

**`bin/mctl` is never wrong.** It is the same core, it needs no gate, and it is
always present in a checkout. The MCP is a better front door when it exists.

Therefore, in this order:

1. `mcp__mctl__*` in your tool list → call the tool.
2. Otherwise → run the `bin/mctl` block above. Say once, in one line, which
   surface you used. Do not narrate the absence further.
3. Never block, stall, or abort because the MCP is missing.

This matters most in a **prime**, where the surface is how a fresh session
orients. A prime that hard-fails on a missing MCP is strictly worse than one
that never mentioned it: the session starts blind. Degrade to the CLI, name the
surface you fell back to, and carry on priming.

## Trace ids (mutations only)

Every mctl command stamps a `trace_id` into its payload. A skill that performs
a **mutation or dispatch** must surface it, so the invocation can be replayed
afterwards with `mctl trace show <id>`:

```bash
out=$("$MCTL" briefs adjudicate "$BRIEF" --verdict "$V" --reason "$R" \
        --city "$CITY_ROOT" --rig "$RIG" --json) || rc=$?
TRACE_ID=$(printf '%s' "$out" | python3 -c 'import json,sys; print(json.load(sys.stdin).get("trace_id",""))')
echo "MCTL-TRACE: $TRACE_ID"
```

Report the `MCTL-TRACE:` line in the skill's own summary output. Read-only
commands emit a trace id too, but nothing is being audited, so they need not
report it.

## Three diagnostic codes that must NOT drive behavior

mctl's diagnostics are generally actionable. These three are not, and a skill
that branches on them acts on false signal:

| code | why it is untrustworthy today |
| --- | --- |
| `MBRF021` | mass false positive — 66 of 70 briefs in one rig report "no redundant cache artifact" because the artifact root and the lookup disagree (issue #58, `OPEN-DESIGN-QUESTIONS.md` Q5). `mctl_core/mcp_server.py` already moves it to `untrusted_diagnostics`. |
| `MBRF004` | "no source dependency" — instrumentation under review. It fires on 146 of 185 briefs across both healthy and malformed ones. |
| `MBRF005` | "closed brief bead has no recorded verdict" — `malformed` means *closed with no verdict field*, not damaged. The verdicts are in `close_reason`/`notes`, which the reader does not consult, and ~39 of the 74 "malformed" beads were never briefs. |

See `subdomains/dev/docs/MALFORMED-BRIEF-TRIAGE-2026-08-19.md`.

**`MBRF004` genuinely does gate `adjudicate` / `defer` / `dispatch`** — it is an
`ERROR`, and `effects.py::_blocking_preconditions` refuses any mutation whose
doctor report carries one. So a refactored skill *will* be refused on most of
the live pending queue. **That is real current behavior.** Report the refusal
with its diagnostic verbatim; do not bypass the gate, and do not treat the
refusal as the skill's own bug.
