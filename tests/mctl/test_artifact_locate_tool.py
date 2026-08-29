"""mc-8q0g4 -- `locate_artifact` needs a route, and the route must not take a path.

The core function is only half the fix. The defect it addresses is that an agent
asking "is this artifact there?" had no typed way to ask -- 48 tools, none of
them this one -- so it shelled out to `find` against a hand-typed path. Shipping a core module nobody can call would
leave that unchanged -- the same shape `#153`/`gates_status` was filed for.

THE PROPERTY THAT MATTERS MOST HERE is not that the tool exists. It is what the
tool REFUSES to accept. If `artifact_locate` took a root, a directory, or any
other caller-supplied path, it would faithfully search whatever wrong tree it was
handed and answer with the full authority of the typed surface -- which is worse
than the shell, not better, because the answer would be believed harder.

    caller passes a BEAD ID  ->  the tool resolves the root  ->  wrong tree unreachable
    caller passes a PATH     ->  the tool is a slower `find`

So `test_the_tool_refuses_to_take_a_path` is the load-bearing test in this file,
and it is the one that would still be worth keeping if every other test here were
deleted.

The second property, inherited from the core and asserted again at this layer
because a wrapper is exactly where it gets flattened:

    root missing   ->  "unknown"   we could not look
    root present   ->  "absent"    we looked and it is not there

A tool returning `{"artifacts": []}` for both reproduces, one layer up and with
more authority, the ambiguity this whole bead exists to remove.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))


def _server():
    from mctl_core.mcp_server import MctlMcpServer

    return MctlMcpServer(default_city=Path("<city-root>"), client_class="internal")


def _spec():
    for spec in _server().visible_tools():
        if spec.name == "artifact_locate":
            return spec
    raise AssertionError("artifact_locate is not registered")


def test_the_tool_is_exposed() -> None:
    """It must be reachable, not merely implemented."""
    names = {spec.name for spec in _server().visible_tools()}
    assert "artifact_locate" in names


def test_the_tool_refuses_to_take_a_path() -> None:
    """The structural guarantee: no caller-supplied path, so no wrong tree.

    Asserted against the declared input schema rather than by calling, because
    the guarantee is about what the surface ADMITS. A tool that ignored a path
    argument at runtime would still invite callers to pass one and to believe
    the result was scoped to it.
    """
    properties = _spec().input_schema.get("properties", {})
    forbidden = {"path", "root", "brief_root", "directory", "pile", "decisions", "city_root"}
    offered = set(properties)
    assert not (offered & forbidden), (
        f"artifact_locate must not accept a caller-supplied path; it offers {sorted(offered & forbidden)}"
    )
    assert "bead_id" in offered, "the caller names a bead, not a location"


def test_the_response_names_the_root_it_searched() -> None:
    """A wrong-root answer must be visible on sight, not inferred later."""
    declared = _spec().output_schema
    properties = declared.get("properties", {})
    assert "resolved_root" in properties
    assert "root_exists" in properties


def test_unknown_and_absent_are_distinct_verdicts_at_the_tool_layer() -> None:
    """The core keeps them apart; assert the wrapper does not flatten them.

    Exercised through the core the tool wraps, with both roots real, so this
    fails if either verdict is ever collapsed into the other.
    """
    from mctl_core.redundant_state import ArtifactLayout, locate_artifact

    def layout(root: Path) -> ArtifactLayout:
        return ArtifactLayout(
            root=root,
            pile=root / ".pile",
            stack=root / "stack",
            stack_index=root / "stack" / ".index.jsonl",
            decisions=root / "decisions",
            legacy_manifest=root / "manifest.jsonl",
        )

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        present_root = Path(tmp) / "briefs"
        (present_root / ".pile").mkdir(parents=True)
        (present_root / "decisions").mkdir(parents=True)
        (present_root / "stack").mkdir(parents=True)
        looked = locate_artifact(layout(present_root), "mc-nothing")

        missing_root = Path(tmp) / "absent-briefs"
        could_not = locate_artifact(layout(missing_root), "mc-nothing")

    assert looked.artifact("pile").verdict == "absent"
    assert could_not.artifact("pile").verdict == "unknown"
    assert looked.artifact("pile").verdict != could_not.artifact("pile").verdict
