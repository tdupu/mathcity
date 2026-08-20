"""The brief body — the decision evidence — must be reachable through mctl.

`mctl briefs show --json` reported eleven metadata fields and no content, so a
consumer rendering a `present-it` brief detail (§1 What is being decided …
§7 Plan membership) had nothing to render. The data was never missing: 62 of
64 open hecke decision beads carry a `description`. The field was.

Two shapes, both required (issue #66 item 11, bead `mc-vdl.3`):

* the **raw body**, verbatim, so a parser can never lose content, and
* **parsed sections**, so a consumer need not re-parse markdown itself.

The invariant that makes both safe together: parsing NEVER silently drops
content. An unparseable body still returns its raw text, and the parse
failure is reported as a diagnostic on the record rather than as an empty
`sections` array that reads like "this brief has no sections".

`decision_options()` is the same bug one layer over, so it is fixed and
tested here too: it parsed §4 out of `<brief_root>/.pile/<brief_id>.md`, a
path that does not resolve on the live rig (0 of 25 sampled hecke briefs
returned an option), and it failed open by design. The bead description is
canonical and present, so it is now the primary source.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

MCTL = SCRIPTS_ROOT / "mctl.py"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"

BRIEF = "mc-body"
SOURCE = "source-body"

# A well-formed present-it brief: the seven grill-ordered sections, with the
# explicit `§N` markers the skill's template emits.
PRESENT_IT_BODY = """# Brief — expose the brief body

## §1 — What is being decided (INVARIANT)

Whether `briefs show` should return the brief body.

## §2 — Recommended answer

APPROVE. The body is the brief.

## §3 — Assumptions surfaced

- Assumes every decision bead carries a description.

## §4 — Options

- **(A) Return body and sections.** *(recommended)* Both shapes.
- **(B) Return the body only.** Consumers re-parse markdown.

## §5 — Risks foregrounded

A parser that silently drops content is worse than no parser.

## §6 — Supporting evidence

62 of 64 open hecke decision beads carry a description.

## §7 — Plan membership, blocking, and required gates

Issue #66 item 11; bead mc-vdl.3.
"""

# What live hecke briefs actually look like: no `§N` markers, prose headings,
# a nested subsection, and a fenced block whose `#` lines are not headings.
LIVE_SHAPED_BODY = """## Decision

Phase A encodes the b_k(X) convention using the Borel-Serre complex.

### Encoding

Add generators from C_*(M_c) to C_*(X_BS).

```bash
# this is a shell comment, not a section heading
echo "## Not a heading either"
```

## Rationale

The Borel-Casselman theorem is the rigorous justification.

## Alternatives Considered

Algebraic quotient without explicit cusp cells.
"""

# No headings at all. The body is still real content that must survive.
UNPARSEABLE_BODY = (
    "Taylor wants the omnibus bead split. No headings, no structure, "
    "just the decision in a paragraph."
)


def bead_rows(description: str | None) -> list[dict[str, object]]:
    brief: dict[str, object] = {
        "id": BRIEF,
        "title": "Expose the brief body",
        "status": "open",
        "issue_type": "decision",
        "labels": ["brief-open"],
        "dependencies": [{"issue_id": BRIEF, "depends_on_id": SOURCE, "type": "related"}],
        "created_at": "2026-08-10T12:00:00Z",
        "updated_at": "2026-08-11T12:00:00Z",
    }
    if description is not None:
        brief["description"] = description
    return [
        brief,
        {
            "id": SOURCE,
            "title": "Source work",
            "status": "open",
            "issue_type": "task",
            "labels": [],
            "created_at": "2026-08-10T12:00:00Z",
            "updated_at": "2026-08-11T12:00:00Z",
        },
    ]


def runtime(tmp_path: Path, description: str | None, *, pile_body: str | None = None):
    """A one-brief rig whose description is the only source of body text.

    `pile_body` writes the legacy markdown cache instead, which is how the
    fallback path is exercised without a description present.
    """
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    beads = rig_root / ".beads"
    (beads / "briefs" / "decisions").mkdir(parents=True)
    (beads / "briefs" / "stack").mkdir(parents=True)
    (beads / "briefs" / "stack" / ".index.jsonl").write_text("", encoding="utf-8")
    (beads / "briefs" / ".pile").mkdir(parents=True)
    (beads / "decisions-track").mkdir(parents=True)
    (beads / "decisions-track" / "manifest.jsonl").write_text("", encoding="utf-8")
    if pile_body is not None:
        (beads / "briefs" / ".pile" / f"{BRIEF}.md").write_text(pile_body, encoding="utf-8")
    fixture = beads / "issues.jsonl"
    fixture.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in bead_rows(description)),
        encoding="utf-8",
    )
    return city_root, fixture


def run_mctl(city_root: Path, fixture: Path, *args: str):
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["MCTL_BEADS_FIXTURE"] = str(fixture)
    return subprocess.run(
        [sys.executable, str(MCTL), *args, "--city", str(city_root), "--rig", "mathcity"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
        env=env,
    )


def show(city_root: Path, fixture: Path) -> dict:
    result = run_mctl(city_root, fixture, "briefs", "show", BRIEF, "--json")
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)["brief"]


def context_for(city_root: Path, fixture: Path):
    from mctl_core.context import resolve_context

    return resolve_context(
        REPO_ROOT,
        city=city_root,
        rig="mathcity",
        require_runtime_city=True,
        require_explicit_runtime=True,
        env={"MCTL_BEADS_FIXTURE": str(fixture)},
    )


# --- the raw body ------------------------------------------------------------


def test_briefs_show_returns_the_raw_body_verbatim(tmp_path: Path):
    """Verbatim: nothing the parser cannot handle may be lost on the way out."""
    city_root, fixture = runtime(tmp_path, LIVE_SHAPED_BODY)

    brief = show(city_root, fixture)

    assert brief["body"] == LIVE_SHAPED_BODY


def test_a_bead_with_no_description_returns_an_explicit_empty_body(tmp_path: Path):
    """Absent content is reported as empty, never as a crash or a missing key."""
    city_root, fixture = runtime(tmp_path, None)

    brief = show(city_root, fixture)

    assert brief["body"] == ""
    assert brief["sections"] == []
    assert "MBRF040" in {item["code"] for item in brief["body_diagnostics"]}


def test_briefs_list_carries_no_bead_body(tmp_path: Path):
    """A city-wide list read must not fetch 200 bead descriptions.

    Still true, and still the reason `briefs show` exists. A manifest record
    is the documented exception -- it reaches no other surface -- but a
    bead-backed brief has `show`, so the roster keeps carrying only its
    metadata plus `fields`, which is a frontmatter head-read, not a body.
    """
    city_root, fixture = runtime(tmp_path, PRESENT_IT_BODY)

    result = run_mctl(city_root, fixture, "briefs", "list", "--json")

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    listed = next(item for item in payload["briefs"] if item["brief_id"] == BRIEF)
    assert "body" not in listed
    assert "sections" not in listed
    assert set(listed) == {
        "bead_id",
        "body_path",
        "brief_id",
        "canonical_source",
        "created_at",
        "decision_state",
        "fields",
        "labels",
        "policy_references",
        "redundant_artifacts",
        "source",
        "status",
        "timestamp",
        "timestamp_field",
        "title",
        "track",
        "updated_at",
        "verdict",
    }


# --- parsed sections ---------------------------------------------------------


def test_sections_parse_for_a_well_formed_present_it_brief(tmp_path: Path):
    city_root, fixture = runtime(tmp_path, PRESENT_IT_BODY)

    sections = show(city_root, fixture)["sections"]

    indexed = {section["section_index"]: section for section in sections}
    assert sorted(index for index in indexed if index) == [1, 2, 3, 4, 5, 6, 7]
    assert indexed[1]["section_key"] == "what_is_being_decided"
    assert indexed[1]["match"] == "explicit"
    assert "Whether `briefs show` should return the brief body." in indexed[1]["body"]
    assert indexed[7]["section_key"] == "plan_membership"
    assert indexed[1]["start_line"] < indexed[7]["start_line"]


def test_sections_parse_a_live_shaped_brief_without_section_markers(tmp_path: Path):
    """Real bead bodies use prose headings, so name matching has to carry them."""
    city_root, fixture = runtime(tmp_path, LIVE_SHAPED_BODY)

    sections = show(city_root, fixture)["sections"]

    by_heading = {section["heading"]: section for section in sections}
    assert by_heading["Decision"]["section_index"] == 1
    assert by_heading["Decision"]["match"] == "heading"
    assert by_heading["Alternatives Considered"]["section_index"] == 4
    # A parent section keeps its nested subsection, so §-level rendering is whole.
    assert "Add generators" in by_heading["Decision"]["body"]
    assert by_heading["Encoding"]["level"] == 3


def test_headings_inside_fenced_code_are_not_sections(tmp_path: Path):
    """A `#` comment in a shell block is not a §; fabricating one is data loss."""
    city_root, fixture = runtime(tmp_path, LIVE_SHAPED_BODY)

    headings = [section["heading"] for section in show(city_root, fixture)["sections"]]

    assert "this is a shell comment, not a section heading" not in headings
    assert "Not a heading either" not in headings


def test_an_unparseable_body_still_returns_its_raw_text_with_a_diagnostic(tmp_path: Path):
    """The bug being fixed one layer over: never return `{}` and stay silent."""
    city_root, fixture = runtime(tmp_path, UNPARSEABLE_BODY)

    brief = show(city_root, fixture)

    assert brief["body"] == UNPARSEABLE_BODY
    assert brief["sections"] == []
    codes = {item["code"] for item in brief["body_diagnostics"]}
    assert "MBRF041" in codes, brief["body_diagnostics"]


def test_a_body_whose_sections_map_to_no_present_it_section_says_so(tmp_path: Path):
    city_root, fixture = runtime(tmp_path, "## Bookkeeping\n\nRouting notes only.\n")

    brief = show(city_root, fixture)

    sections = brief["sections"]
    assert [section["heading"] for section in sections] == ["Bookkeeping"]
    assert sections[0]["section_index"] is None
    assert sections[0]["match"] == "unmapped"
    assert "MBRF042" in {item["code"] for item in brief["body_diagnostics"]}


# --- decision_options resolves from the canonical bead -----------------------


def test_decision_options_resolve_from_the_bead_description(tmp_path: Path):
    from mctl_core.briefs import decision_options

    city_root, fixture = runtime(tmp_path, PRESENT_IT_BODY)

    options = decision_options(context_for(city_root, fixture), BRIEF)

    assert [option.label for option in options] == ["A", "B"]
    assert options[0].heading == "Return body and sections."


def test_decision_options_prefer_the_bead_over_a_disagreeing_markdown_cache(tmp_path: Path):
    """B2.4/B2.8: the bead is canonical, the file is a cache."""
    from mctl_core.briefs import decision_options

    stale = "## §4 — Options\n\n- **(Z) A stale cached option.** Superseded.\n"
    city_root, fixture = runtime(tmp_path, PRESENT_IT_BODY, pile_body=stale)

    options = decision_options(context_for(city_root, fixture), BRIEF)

    assert [option.label for option in options] == ["A", "B"]


def test_decision_options_fall_back_to_the_markdown_cache_without_a_description(tmp_path: Path):
    from mctl_core.briefs import decision_options

    cached = "## §4 — Options\n\n- **(A) Cached only.** No bead description exists.\n"
    city_root, fixture = runtime(tmp_path, None, pile_body=cached)

    options = decision_options(context_for(city_root, fixture), BRIEF)

    assert [option.label for option in options] == ["A"]


def test_adjudicating_a_multi_option_bead_body_requires_naming_the_option(tmp_path: Path):
    """MOPT001 now fires on real briefs, whose options live only on the bead."""
    city_root, fixture = runtime(tmp_path, PRESENT_IT_BODY)

    result = run_mctl(
        city_root,
        fixture,
        "briefs",
        "adjudicate",
        BRIEF,
        "--verdict",
        "approve",
        "--reason",
        "body-sourced options",
        "--json",
    )

    assert result.returncode != 0
    assert "MOPT001" in result.stderr, result.stderr


# --- the MCP surface ---------------------------------------------------------


def test_mcp_briefs_show_validates_against_its_own_declared_schema(tmp_path: Path):
    from mctl_core import mcp_server
    from mctl_core.schemas import schema_errors

    city_root, fixture = runtime(tmp_path, PRESENT_IT_BODY)
    tool = next(item for item in mcp_server.TOOLS if item.name == "briefs_show")
    instance = mcp_server.MctlMcpServer(
        default_city=city_root,
        default_rig="mathcity",
        client_class="internal",
        env={"MCTL_BEADS_FIXTURE": str(fixture)},
        cwd=REPO_ROOT,
    )
    response = instance.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": "briefs_show", "arguments": {"brief_id": BRIEF}},
        }
    )
    payload = response["result"]["structuredContent"]

    assert response["result"].get("isError") is not True, payload
    assert schema_errors(payload, tool.output_schema) == []
    assert payload["brief"]["body"] == PRESENT_IT_BODY
    assert payload["brief"]["sections"]


def test_the_briefs_show_output_schema_declares_body_and_sections():
    from mctl_core import mcp_server

    tool = next(item for item in mcp_server.TOOLS if item.name == "briefs_show")
    brief = tool.output_schema["properties"]["brief"]

    # Nullable since Slice 7: a manifest record whose body file does not exist
    # reports null, which is the `unreadable` lane and not an empty brief.
    assert brief["properties"]["body"]["type"] == ["string", "null"]
    assert brief["properties"]["sections"]["type"] == "array"
    assert {"body", "sections", "body_diagnostics"} <= set(brief["required"])


def test_the_briefs_list_output_schema_makes_body_optional_not_required():
    """A list item may carry a body; a bead-backed one does not.

    `briefs show` is where a bead's body belongs, so `body` is absent from
    `required` and a client must not assume it. It is declared, because a
    manifest record does carry one -- that record reaches no other surface, so
    withholding it there withholds it everywhere.
    """
    from mctl_core import mcp_server

    tool = next(item for item in mcp_server.TOOLS if item.name == "briefs_list")
    item_schema = tool.output_schema["properties"]["briefs"]["items"]
    detail = next(
        item for item in mcp_server.TOOLS if item.name == "briefs_show"
    ).output_schema["properties"]["brief"]

    assert "body" in item_schema["properties"]
    assert "sections" in item_schema["properties"]
    assert "body" not in item_schema["required"]
    assert "sections" not in item_schema["required"]
    assert {"body", "sections", "body_diagnostics"} <= set(detail["required"])


# --- the human renderer ------------------------------------------------------


def test_human_show_summarizes_the_body_instead_of_dumping_it(tmp_path: Path):
    """A 2,400-character body in a terminal table is not human output."""
    city_root, fixture = runtime(tmp_path, PRESENT_IT_BODY)

    result = run_mctl(city_root, fixture, "briefs", "show", BRIEF)

    assert result.returncode == 0, result.stderr
    assert "sections: 7" in result.stdout
    assert "§1 What is being decided" in result.stdout
    # The section bodies themselves stay out of the summary.
    assert "62 of 64 open hecke decision beads" not in result.stdout


def test_human_show_reports_an_empty_body_rather_than_omitting_it(tmp_path: Path):
    city_root, fixture = runtime(tmp_path, None)

    result = run_mctl(city_root, fixture, "briefs", "show", BRIEF)

    assert result.returncode == 0, result.stderr
    assert "body: (empty)" in result.stdout


# --- the parser in isolation -------------------------------------------------


def test_parse_brief_sections_spans_cover_the_body_without_gaps():
    from mctl_core.briefs import parse_brief_sections

    sections = parse_brief_sections(PRESENT_IT_BODY)
    top = [section for section in sections if section.level == 2]

    assert len(top) == 7
    for earlier, later in zip(top, top[1:]):
        assert earlier.end_line + 1 == later.start_line


def test_parse_brief_sections_on_empty_input_returns_nothing():
    from mctl_core.briefs import parse_brief_sections

    assert parse_brief_sections("") == ()
