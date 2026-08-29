"""mc-8r01j: the issue-template gate could not fail.

`.github/ISSUE_TEMPLATE/` holds `config.yml` -- the chooser config, not an issue
form -- which declares ZERO required fields. Under #211's rule ("a body is
conformant if it satisfies ANY ONE template") its missing-list is always `[]`,
`all()` over a falsy member is False, and the refusal never fired.

So EVERY body passed. Measured live 2026-08-29 on origin/main f66b5d8:

    create_github_issue(body="nothing here\\n", dry_run=true)
      -> plan built, 13 bytes, NO MGHW_TEMPLATE_SECTION_MISSING,
         NO MGHW_TEMPLATE_UNREADABLE

The absent `UNREADABLE` advisory is what makes it conclusive rather than
ambiguous: the templates WERE read -- four of them, confirmed by calling
`required_template_sections` directly -- so this was not the documented
best-effort skip. The check ran and could not fail.

WHY EVERY PRE-EXISTING TEST PASSED EITHER WAY, and why this file exists.
A test that feeds a CONFORMANT body passes whether or not the gate works. The
only test that discriminates is one feeding a body the gate must REJECT, and
there was none. That is the whole lesson: a suite full of positive cases cannot
detect a vacuous gate.

#211's per-template logic is RIGHT and is preserved here -- a bug_report body
must not be refused for lacking feature_request headings. Only the degenerate
template is removed from the gating set, filtered on the PROPERTY (requires
nothing) rather than the filename, so another non-form file cannot reintroduce
it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import effects
from mctl_core.effects import MutationError


BUG_REQUIRED = (
    "Summary", "Symptom", "Minimal reproducible example (MRE)", "Root cause",
    "Fix candidates", "Versions", "Environment",
)
FEATURE_REQUIRED = (
    "Problem to solve", "Proposed design", "Alternatives considered", "Blast radius",
)

#: The live shape: three real forms plus the chooser config, which requires
#: nothing. `config.yml` is the member that voided the gate.
LIVE_SHAPE = {
    "bug_report.yml": BUG_REQUIRED,
    "feature_request.yml": FEATURE_REQUIRED,
    "docs_report.yml": ("Which document?", "What does it say now?"),
    "config.yml": (),
}


def _body(sections) -> str:
    return "\n".join(f"### {s}\n\ncontent\n" for s in sections)


@pytest.fixture
def plan(monkeypatch, tmp_path):
    """Build a create_github_issue plan with the template read stubbed."""

    def _run(templates, body):
        monkeypatch.setattr(effects, "required_template_sections", lambda repo: templates)
        return effects.plan_create_github_issue(
            _ctx(tmp_path),
            effects.GithubIssueCreateInput(repo="tdupu/mathcity", title="t", body=body),
        )

    return _run


def _ctx(tmp_path):
    """Same construction `test_bead_close.py` uses -- copied rather than
    guessed. My first draft invented `rig_name=`, which does not exist."""
    from mctl_core.context import MctlContext

    return MctlContext(
        city_root=tmp_path,
        rig_id="mathcity",
        rig_root=tmp_path / "rig",
        beads_fixture=tmp_path / "issues.jsonl",
        rig_db=".beads",
        source_checkout=tmp_path,
        paths_toml=tmp_path / "paths.toml",
        gates_toml=tmp_path / "gates.toml",
        invocation_cwd=tmp_path,
        trace_id="trace-template-gate-1",
        warnings=(),
        discovery_path="test",
        city_active=None,
        city_endpoint=None,
    )


# --- the defect: the gate must be able to refuse ---------------------------


def test_an_empty_body_is_refused(plan) -> None:
    """The exact live control that caught this. 13 bytes, no headings."""
    with pytest.raises(MutationError):
        plan(LIVE_SHAPE, "nothing here\n")


def test_a_body_missing_one_required_section_is_refused(plan) -> None:
    """Not only the empty case: one short of bug_report must still refuse."""
    with pytest.raises(MutationError):
        plan(LIVE_SHAPE, _body(BUG_REQUIRED[:-1]))


def test_the_refusal_names_the_closest_template(plan) -> None:
    """CT13.4: a refusal the author cannot act on is a wall."""
    with pytest.raises(MutationError) as caught:
        plan(LIVE_SHAPE, _body(BUG_REQUIRED[:-1]))
    message = str(caught.value)
    assert "bug_report.yml" in message, "must name which form was closest"
    assert BUG_REQUIRED[-1] in message, "must name what is missing"


# --- #211's logic must survive: satisfying ONE template is enough ----------


def test_a_bug_shaped_body_passes_without_feature_headings(plan) -> None:
    """#211's whole point. This must NOT regress to the union rule."""
    result = plan(LIVE_SHAPE, _body(BUG_REQUIRED))
    assert result is not None


def test_a_feature_shaped_body_passes_without_bug_headings(plan) -> None:
    result = plan(LIVE_SHAPE, _body(FEATURE_REQUIRED))
    assert result is not None


# --- the degenerate-set case -----------------------------------------------


def test_all_degenerate_templates_advise_rather_than_pass_silently(plan) -> None:
    """If nothing can gate, say so. Passing quietly is what the bug did."""
    result = plan({"config.yml": (), "other.yml": ()}, "nothing here\n")
    codes = [d.code for d in result.advisories]
    assert "MGHW_TEMPLATE_NO_REQUIRED_SECTIONS" in codes


def test_no_templates_at_all_still_does_not_block(plan) -> None:
    """Unreadable templates must not turn a hygiene aid into a wall."""
    result = plan({}, "nothing here\n")
    assert result is not None


def test_the_diagnostic_code_is_registered() -> None:
    """#199: a code emitted but absent from the registry is unexplainable."""
    registry = (REPO_ROOT / "assets" / "mctl" / "diagnostics.toml").read_text(encoding="utf-8")
    assert "[MGHW_TEMPLATE_NO_REQUIRED_SECTIONS]" in registry
