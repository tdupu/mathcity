"""Adjudications record WHO adjudicated (#152, the recording half).

THE HOLE. Three MCP calls compose into self-authorisation: `briefs_create`,
`briefs_adjudicate(verdict="approve")`, `work_dispatch(dry_run=false)`. Step 2
supplies the approving verdict that step 3 demands, so an agent can manufacture
its own authorisation for arbitrary work. The rule that a reviewer must not be
the author is enforced socially on branches and by nothing at all here.

THIS IS THE RECORDING HALF, NOT THE GATE. Refusing self-adjudication is a policy
decision with its own blast radius. Making self-adjudication *visible* is not,
and #152's own minimum is: "silent self-approval is the unacceptable case."

WHY `self_adjudicated` IS NOT COMPUTED AT WRITE TIME. It would need the brief
bead's `requested_by`, and `_beads()` is not cached -- every adjudication would
pay a second `bd` subprocess, 9-11s on the largest rig. Both `requested_by`
(written at create) and `adjudicated_by` (written here) land on the SAME bead,
so an auditor derives the comparison at read time for free. Recording both
facts is what makes the audit possible; computing the answer eagerly is not
required for it.

WHY AN OMITTED ADJUDICATOR IS LOUD. Absent is not false. An adjudication with
no recorded adjudicator is unattributable, and silence about it is the exact
failure #152 names -- so it emits a WARNING rather than passing quietly. It does
not block: that would be the gate half.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

import inspect  # noqa: E402

from mctl_core import effects  # noqa: E402

UNRECORDED_CODE = "MBRF_ADJUDICATOR_UNRECORDED"


class TestTheParameterExists:
    def test_plan_adjudication_accepts_an_adjudicator(self):
        params = inspect.signature(effects.plan_adjudication).parameters
        assert "adjudicated_by" in params

    def test_it_is_optional_because_this_is_the_recording_half_not_a_gate(self):
        """A required argument would refuse existing callers, which is the gate
        half wearing a signature change."""
        params = inspect.signature(effects.plan_adjudication).parameters
        assert params["adjudicated_by"].default is None

    def test_the_mcp_tool_exposes_it(self):
        from mctl_core.mcp_server import TOOLS_BY_NAME

        schema = TOOLS_BY_NAME["briefs_adjudicate"].input_schema
        assert "adjudicated_by" in schema["properties"], (
            "the tool that supplies the approving verdict must be able to say who supplied it"
        )

    def test_the_tool_does_NOT_require_it(self):
        from mctl_core.mcp_server import TOOLS_BY_NAME

        schema = TOOLS_BY_NAME["briefs_adjudicate"].input_schema
        assert "adjudicated_by" not in schema.get("required", [])


class TestTheDiagnosticIsRegistered:
    def test_the_unrecorded_code_exists_in_the_registry(self):
        import tomllib

        registry = tomllib.loads(
            (REPO_ROOT / "assets" / "mctl" / "diagnostics.toml").read_text(encoding="utf-8")
        )
        assert UNRECORDED_CODE in registry

    def test_it_is_a_warning_not_an_error(self):
        """ERROR would make it a precondition and block the write. The whole
        point of the recording half is that it does not block."""
        import tomllib

        registry = tomllib.loads(
            (REPO_ROOT / "assets" / "mctl" / "diagnostics.toml").read_text(encoding="utf-8")
        )
        assert registry[UNRECORDED_CODE]["severity"] == "WARN"


class TestTheMetadataContract:
    """What must land on the bead, asserted against the module's own constants
    rather than by running an adjudication (which needs a live brief)."""

    def test_the_adjudicator_key_is_named_consistently_with_requested_by(self):
        source = (SCRIPTS_ROOT / "mctl_core" / "effects.py").read_text(encoding="utf-8")
        assert '"adjudicated_by"' in source, "the metadata key must be written"

    def test_the_recording_is_paired_with_requested_by_in_the_code_comment(self):
        """The pairing IS the audit mechanism -- if a later edit drops one, the
        other becomes unusable for the purpose it was added for."""
        source = (SCRIPTS_ROOT / "mctl_core" / "effects.py").read_text(encoding="utf-8")
        assert "requested_by" in source and "adjudicated_by" in source


class TestTheCodeIsActuallyEmitted:
    """Closes a hole in this file's first version.

    The original tests asserted the code was REGISTERED and the parameter
    EXISTED, and passed unchanged when the emitted code string was renamed to
    something else entirely. They could not fail for the emission path -- the
    exact shape this file was written to guard against, in the file guarding
    against it.

    A true emission test would call `plan_adjudication` against a live brief.
    This is a source-level proxy: it asserts the string effects.py emits is the
    string the registry declares, so a rename on either side fails. Weaker than
    an emission test, stated so nobody reads it as one.
    """

    def test_the_emitted_code_matches_the_registered_code(self):
        source = (SCRIPTS_ROOT / "mctl_core" / "effects.py").read_text(encoding="utf-8")
        assert f'"{UNRECORDED_CODE}"' in source, (
            f"effects.py does not emit {UNRECORDED_CODE}; a rename here would make the "
            f"registry entry dead and the warning silent"
        )

    def test_the_warning_is_emitted_on_the_omitted_branch(self):
        """The `else` of the adjudicated_by check must be where it fires --
        emitting it unconditionally would warn on every adjudication."""
        source = (SCRIPTS_ROOT / "mctl_core" / "effects.py").read_text(encoding="utf-8")
        after_guard = source.split('metadata["adjudicated_by"]', 1)[-1]
        # Bounded by the next statement rather than a character count: the
        # first version used [:600] and broke when a comment grew, which is a
        # test asserting comment length rather than behaviour.
        region = after_guard.split("cache_fields", 1)[0]
        assert "else:" in region and UNRECORDED_CODE in region, (
            "the warning must fire on the omitted branch, not unconditionally"
        )

    def test_the_warning_is_an_advisory_not_a_precondition(self):
        """Preconditions BLOCK the mutation. A blocking warning would make the
        recording half silently become the gate half -- which is what happened
        on the first attempt, caught by 80 unrelated test failures."""
        source = (SCRIPTS_ROOT / "mctl_core" / "effects.py").read_text(encoding="utf-8")
        after_guard = source.split('metadata["adjudicated_by"]', 1)[-1]
        region = after_guard.split("cache_fields", 1)[0]
        assert "returned_advisories" in region, "the warning must go to advisories"
        assert "diagnostics.append" not in region, "advisories, never preconditions"
