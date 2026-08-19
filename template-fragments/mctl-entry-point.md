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

`--all-rigs` was specified in Slice 2 and is **not implemented yet**. Do not
build a per-skill loop over rigs to fake it — that is the duplicate control
surface this whole slice exists to remove. Make the single-rig call, and record
the cross-rig need as a dependency on `--all-rigs`.

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
