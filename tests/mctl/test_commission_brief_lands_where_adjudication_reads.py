"""mc-4ovmy (P0): a commission brief must land where adjudication reads.

THE DEFECT, MEASURED 2026-08-28. Eighteen complete, gate-passing briefs sit in
`<rig-root>/.gc-builds/<bead>/.pile/<slug>.md`, a directory no adjudication
surface reads. A brief no adjudicator can reach has no route to a human, which
is the entire purpose of a brief. Twelve of the eighteen carry
`source_formula: commission-work-briefed`; six carry `simple-work-briefed`.
Both are reached from `skills/work/SKILL.md` Path B.

THE MECHANISM IS ONE VARIABLE SERVING TWO PURPOSES.
`work-briefed.toml` types `artifact_root` as *"Build or brief artifact root"*,
and the two purposes want opposite things:

  * a BUILD root must be per-bead, or two concurrent dispatches in one rig
    collide (the gsp-1bmxuz hazard the skill warns about);
  * a BRIEF deposit root must be the rig's one shared pile, or nothing reads it.

Path B bead-scopes the single var to `.gc-builds/$SOURCE_BEAD` -- correct for
builds -- and `commission-work-briefed`'s terminal `file-brief` step deposits to
`{{artifact_root}}/.pile/`, so the brief inherits the build scoping and strands.
`commission-work-briefed` has no deposit step after `file-brief`, so it is
terminal: nothing later moves the file back.

WHY THIS TEST IS SHAPED THIS WAY -- P6.2, "a check that could not have failed
must not render as a check that passed". `tests/artifact-root-scoping` greps
six skills for the literal string `artifact_root=<rig-root>/.gc-builds/<bead>`
and passes; `tests/commission-work-briefed` greps the formula for section
headings and passes. Both passed throughout the entire period the eighteen
briefs were stranding, because neither asks the only question that mattered:
IS THE DEPOSITED BRIEF REACHABLE?

So this test asserts the CONSEQUENCE. It renders the deposit path the way the
live dispatch chain renders it -- reading the bindings out of the skill and the
formulas rather than restating them -- writes a brief there, and then asks
mctl's own reader whether it can see it. A path-string equality assertion is
deliberately avoided: it is the shape of check that already failed here.

THE READER IS NOT ASSUMED EITHER. `artifact_layout()` is mctl's single resolver
and every adjudication surface derives from it. Measured against the live city
2026-08-28 it reports, per rig:

    mathcity -> <city-root>/mathcity/.beads/briefs/.pile
    hecke    -> <city-root>/hecke/.beads/briefs/.pile
    hq       -> <city-root>/.beads/briefs/.pile

The root is RIG-relative, per `assets/brief-pipeline/paths.toml`. The city-root
tree is not a competing convention -- it is `hq`'s own rig-relative tree, `hq`
being the reserved id for the store whose rig root IS the city root. A "fix"
that re-points a `mc-*` brief at the city root would therefore strand it just as
thoroughly, in the other direction.
"""
from __future__ import annotations

import os
import re
import shutil
import sys
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

sys.path.insert(0, str(Path(__file__).resolve().parent))

from test_briefs_create_validate_cli import runtime_fixture  # noqa: E402

WORK_SKILL = REPO_ROOT / "skills" / "work" / "SKILL.md"
ROUTER = REPO_ROOT / "formulas" / "work-briefed.toml"
COMMISSION = REPO_ROOT / "formulas" / "commission-work-briefed.toml"

#: A bead id whose rig is the fixture rig. The value is arbitrary; what matters
#: is that the same id flows through skill -> router -> producer unchanged, so a
#: root that is bead-scoped anywhere in the chain shows up in the rendered path.
BEAD = "mc-4ovmy"

BRIEF_BODY = (
    "---\n"
    f"brief_bead: {BEAD}\n"
    "source_formula: commission-work-briefed\n"
    "source_step: file-brief\n"
    "---\n\n"
    "# commission brief\n\n"
    "## What is being decided\n\nWhether the proposed dispatch graph is right.\n\n"
    "## Gate Evidence\n\nDeposited by the commission path under test.\n"
)


# --- reading the dispatch chain, rather than restating it --------------------


def _shell_assignments(block: str, seed: dict[str, str]) -> dict[str, str]:
    """Evaluate `NAME="value"` lines in order, expanding `$NAME` as it goes.

    In order, deliberately: `BRIEF_SLUG="$SOURCE_BEAD-work"` is only meaningful
    after `SOURCE_BEAD` is bound, and a single-pass dict comprehension would
    silently leave the `$SOURCE_BEAD` literal in the slug.

    A seeded name is never overwritten. Two kinds of right-hand side cannot be
    evaluated here and the seed stands in for both:

      * a documentation placeholder (`SOURCE_BEAD=<bead-id>`) -- the skill is
        prose for a human and `<bead-id>` is where the reader substitutes;
      * a command substitution (`RIG_PATH="$(gc rig list --json | jq ...)"`) --
        the seed supplies what the city registry would answer for this bead.

    Substituting the registry's answer is the point, not a shortcut: it is what
    makes the rendered path testable as REGISTRY-derived. A skill that dropped
    the registry lookup and used `$PWD`, a hardcoded root, or a bead-scoped root
    would render a different path and still fail.
    """
    env = dict(seed)
    for name, value in re.findall(r'^([A-Z][A-Z0-9_]*)="?([^"\n]*)"?$', block, re.M):
        if name in seed:
            continue
        env[name] = _expand_shell(value, env)
    return env


def _expand_shell(value: str, env: dict[str, str]) -> str:
    return re.sub(
        r"\$\{?([A-Z][A-Z0-9_]*)\}?", lambda m: env.get(m.group(1), m.group(0)), value
    )


def _path_b_block() -> str:
    text = WORK_SKILL.read_text(encoding="utf-8")
    marker = "## Path B — commission fresh work"
    assert marker in text, "skills/work/SKILL.md no longer documents Path B"
    return text.split(marker, 1)[1].split("\n## ", 1)[0]


def _sling_vars(block: str, formula: str) -> dict[str, str]:
    """The `--var name=value` bindings of the `gc sling ... --on <formula>` call."""
    start = block.find(f"--on {formula}")
    assert start != -1, f"no `gc sling ... --on {formula}` in this block"
    call = block[start:].split("```", 1)[0]
    matches = re.findall(r'--var\s+([a-z_]+)=(?:"([^"]*)"|(\S+))', call)
    return {name: quoted or bare for name, quoted, bare in matches}


def _step(formula_path: Path, step_id: str) -> dict:
    data = tomllib.loads(formula_path.read_text(encoding="utf-8"))
    for step in data.get("steps", []):
        if step.get("id") == step_id:
            return step
    raise AssertionError(f"{formula_path.name} has no step {step_id!r}")


def _defaults(formula_path: Path) -> dict[str, str]:
    data = tomllib.loads(formula_path.read_text(encoding="utf-8"))
    return {
        name: str(spec.get("default", ""))
        for name, spec in (data.get("vars") or {}).items()
        if isinstance(spec, dict) and "default" in spec
    }


def _render(template: str, bindings: dict[str, str]) -> str:
    return re.sub(
        r"\{\{\s*([a-z_]+)\s*\}\}",
        lambda m: bindings.get(m.group(1), m.group(0)),
        template,
    )


def commission_deposit_template(rig_path: Path | None = None) -> tuple[str, dict[str, str]]:
    """The brief path the live chain renders, and the bindings it renders with.

    Follows the three hops the dispatch actually takes:
      1. `skills/work/SKILL.md` Path B binds the vars and slings `work-briefed`
      2. `work-briefed`'s COMMISSION branch forwards vars to `commission-work-briefed`
      3. `commission-work-briefed`'s `file-brief` step declares the deposit path

    `rig_path` is what `gc rig list --json` would answer for `BEAD`'s prefix.
    """
    block = _path_b_block()
    seed = {"SOURCE_BEAD": BEAD}
    if rig_path is not None:
        seed["RIG_PATH"] = str(rig_path)
    env = _shell_assignments(block, seed)
    skill_vars = {
        name: _expand_shell(value, env)
        for name, value in _sling_vars(block, "work-briefed").items()
    }

    router_step = _step(ROUTER, "route")
    forwarded = _sling_vars(router_step["description"], "commission-work-briefed")
    bindings = dict(_defaults(COMMISSION))
    bindings.update(
        {name: _render(value, skill_vars) for name, value in forwarded.items()}
    )

    template = _step(COMMISSION, "file-brief")["metadata"]["gc.brief.path"]
    return template, bindings


# --- the reader --------------------------------------------------------------


def _reader_layout(city_root: Path):
    from mctl_core.context import resolve_context
    from mctl_core.redundant_state import artifact_layout

    ctx = resolve_context(
        city_root,
        city=city_root,
        rig="mathcity",
        require_runtime_city=False,
        env=os.environ,
    )
    return ctx, artifact_layout(ctx)


def _reader_sees(layout, deposited: Path) -> bool:
    """Ask mctl's own pile reader whether the deposited file is visible.

    `orphan_markdown_cache_ids` is the surface that enumerates brief markdown
    independent of any bead -- which is the population these eighteen briefs
    belong to: they have deposit files and no brief bead.
    """
    from mctl_core.redundant_state import orphan_markdown_cache_ids

    return deposited.resolve() in {
        path.resolve() for _, path in orphan_markdown_cache_ids(layout)
    }


@pytest.fixture()
def city(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    return city_root, rig_root


class TestTheCommissionBriefIsReachable:
    def test_a_brief_filed_by_the_commission_path_is_found_by_the_pile_reader(
        self, city
    ):
        """THE defect. RED before the fix, and it is the only assertion that
        could have caught the eighteen."""
        city_root, rig_root = city
        template, bindings = commission_deposit_template(rig_root)
        rendered = _render(template, bindings)
        assert "{{" not in rendered, (
            f"the deposit path still has unbound vars: {rendered}. A var the "
            "chain never binds resolves to nothing at runtime."
        )
        assert "$" not in rendered, (
            f"the deposit path still has an unresolved shell reference: {rendered}"
        )

        # The skill says "Run from the source bead's rig directory", so a
        # relative root resolves against the rig root.
        deposited = Path(rendered)
        if not deposited.is_absolute():
            deposited = rig_root / rendered
        deposited.parent.mkdir(parents=True, exist_ok=True)
        deposited.write_text(BRIEF_BODY, encoding="utf-8")

        _ctx, layout = _reader_layout(city_root)
        assert _reader_sees(layout, deposited), (
            "STRANDED: the commission path deposited a brief at\n"
            f"    {deposited}\n"
            "but the adjudication reader resolves its pile to\n"
            f"    {layout.pile}\n"
            "so the brief has no route to a human. This is mc-4ovmy."
        )

    def test_the_brief_resolves_from_its_source_bead_id(self, city):
        """Reachable-as-a-file is not enough: adjudication addresses a brief by
        bead id, and `_pile_artifact` is where that lookup happens."""
        from mctl_core.redundant_state import _pile_artifact

        city_root, rig_root = city
        template, bindings = commission_deposit_template(rig_root)
        rendered = _render(template, bindings)
        deposited = Path(rendered)
        if not deposited.is_absolute():
            deposited = rig_root / rendered
        deposited.parent.mkdir(parents=True, exist_ok=True)
        deposited.write_text(BRIEF_BODY, encoding="utf-8")

        _ctx, layout = _reader_layout(city_root)
        artifact = _pile_artifact(layout, BEAD)
        assert artifact.state == "present", (
            f"lookup by bead id reports {artifact.state!r} at {artifact.path}; "
            f"the brief is at {deposited}"
        )

    def test_the_reader_is_discriminating(self, city):
        """Positive/negative control. Without it, a reader that answered `True`
        for everything -- or a `_reader_sees` that never looks -- would satisfy
        the tests above without the brief being reachable at all."""
        city_root, rig_root = city
        _ctx, layout = _reader_layout(city_root)

        in_pile = layout.pile / "mc-control-positive.md"
        in_pile.parent.mkdir(parents=True, exist_ok=True)
        in_pile.write_text(BRIEF_BODY, encoding="utf-8")
        assert _reader_sees(layout, in_pile), "the reader cannot see its own pile"

        elsewhere = rig_root / ".gc-builds" / "mc-control" / ".pile" / "mc-control.md"
        elsewhere.parent.mkdir(parents=True, exist_ok=True)
        elsewhere.write_text(BRIEF_BODY, encoding="utf-8")
        assert not _reader_sees(layout, elsewhere), (
            "the reader claims to see a file outside its pile, so a PASS above "
            "would prove nothing"
        )


class TestTheBuildRootStaysPerBead:
    """The fix must not re-create the hazard it is unwinding.

    `artifact_root` is bead-scoped because two concurrent dispatches in one rig
    otherwise share a stage-artifact root (gsp-1bmxuz). Making the brief
    reachable by un-scoping `artifact_root` would trade a visibility defect for
    a concurrency defect, so this pins the build root as still per-bead.
    """

    def test_path_b_still_scopes_the_build_root_per_bead(self):
        block = _path_b_block()
        env = _shell_assignments(block, {"SOURCE_BEAD": BEAD})
        artifact_root = _expand_shell(
            _sling_vars(block, "work-briefed")["artifact_root"], env
        )
        assert BEAD in artifact_root, (
            f"artifact_root is {artifact_root!r}: a build root shared across "
            "beads re-opens gsp-1bmxuz"
        )

    def test_the_brief_root_is_not_bead_scoped(self, tmp_path: Path):
        _template, bindings = commission_deposit_template(tmp_path / "rig")
        rendered = _render(
            _step(COMMISSION, "file-brief")["metadata"]["gc.brief.path"], bindings
        )
        root = rendered.split("/.pile/", 1)[0]
        assert BEAD not in root, (
            f"the brief deposit root is {root!r}, still scoped to the source "
            "bead -- one pile per bead is one pile nobody drains"
        )


class TestPathAAlsoSuppliesTheDepositRoot:
    """`mctl work dispatch` slings the same router, and it must satisfy it.

    Path B (the skill) is not the only caller of `work-briefed`.
    `mctl_core/work.py::_formula_invocation` builds the SAME `gc sling
    work-briefed` command for Path A, and it is the caller a human never sees,
    so a var it silently omits is a var nobody notices is missing.

    Splitting `artifact_root` into a build root and a brief root fixes Path B
    and, on its own, breaks Path A: the router now declares `brief_root`
    required and Path A never passed it. A fix that repairs the documented
    route while breaking the programmatic one has moved the defect, not
    removed it.

    The second assertion is the one that carries the mc-4ovmy claim: Path A's
    deposit root must be the root the READER resolves for that same rig, taken
    from `artifact_layout()` rather than restated here. Restating it would
    reintroduce exactly the second resolution rule `redundant_state` exists to
    prevent -- and a test that agrees with a hardcoded string agrees with
    itself.
    """

    def _invocation(self, city):
        from mctl_core.work import _formula_invocation

        city_root, rig_root = city
        _ctx, layout = _reader_layout(city_root)

        class _Item:
            brief_id = f"{BEAD}-work"
            bead_id = BEAD

        command = list(_formula_invocation(_ctx, _Item())["command"])
        bound = dict(
            pair.split("=", 1)
            for pair in command
            if "=" in pair and not pair.startswith("-")
        )
        return bound, layout

    def test_path_a_binds_every_var_the_router_declares_required(self, city):
        bound, _layout = self._invocation(city)
        data = tomllib.loads(ROUTER.read_text(encoding="utf-8"))
        required = {
            name
            for name, spec in (data.get("vars") or {}).items()
            if isinstance(spec, dict) and spec.get("required")
        }
        missing = sorted(required - set(bound))
        assert not missing, (
            f"`mctl work dispatch` slings {ROUTER.name} without {missing}. "
            "The router declares them required, so this dispatch cannot run."
        )

    def test_path_a_deposit_root_is_the_root_the_reader_resolves(self, city):
        bound, layout = self._invocation(city)
        assert bound.get("brief_root") == str(layout.root), (
            f"Path A deposits under {bound.get('brief_root')!r} but the "
            f"adjudication reader resolves {str(layout.root)!r}. That is "
            "mc-4ovmy on the programmatic route."
        )
