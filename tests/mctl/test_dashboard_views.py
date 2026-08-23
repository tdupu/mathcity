"""Slice 8 dashboard: read views, diagnostics, and the no-passthrough rule.

The dashboard is a *client of the Slice 6 MCP surface*. Nothing here reaches
into `mctl_core` for domain state: every assertion below is about what a
browser receives after the dashboard has asked the typed tool surface, which
is exactly the property the plan's Slice 8 step 2 makes binding.

Two of these tests exist because a plausible-looking dashboard would do real
damage without them:

* `MBRF021` is a mass false positive (Q5). The server already moves it into
  `untrusted_diagnostics`; a UI that rendered it as a finding would tell an
  operator to repair 66 briefs that are fine.
* `MBRF004`/`MBRF005` are instrumentation under review
  (`subdomains/dev/docs/MALFORMED-BRIEF-TRIAGE-2026-08-19.md`): `malformed`
  means "closed with no verdict *field*", and the verdicts are mostly present
  in `close_reason`/`notes`. A bare "74 malformed" badge is a defect.
"""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import mcp_server
from mctl_dashboard.app import Dashboard, Request
from mctl_dashboard.client import ALLOWED_TOOLS, InProcessMcpClient, UnknownToolError
from mctl_dashboard.review import UNDER_REVIEW_CODES

FIXTURES = Path(__file__).resolve().parent / "fixtures"
CITY_ROOT = FIXTURES / "city_root"
SOURCE_CHECKOUT = FIXTURES / "source_checkout"
BRIEF_STATE = FIXTURES / "brief_state"

DASHBOARD_PACKAGE = SCRIPTS_ROOT / "mctl_dashboard"

READ_ONLY_TOOLS = frozenset(tool.name for tool in mcp_server.TOOLS if not tool.mutating)


def runtime_fixture(tmp_path: Path) -> tuple[Path, Path]:
    city_root = tmp_path / "city_root"
    rig_root = city_root / "mathcity"
    shutil.copytree(CITY_ROOT, city_root)
    shutil.copytree(SOURCE_CHECKOUT, tmp_path / "source_checkout")
    shutil.copytree(BRIEF_STATE / "briefs", rig_root / ".beads" / "briefs")
    shutil.copytree(BRIEF_STATE / "decisions-track", rig_root / ".beads" / "decisions-track")
    shutil.copy2(BRIEF_STATE / "beads.jsonl", rig_root / ".beads" / "issues.jsonl")
    return city_root, rig_root


def untrusted_fixture(tmp_path: Path) -> tuple[Path, Path]:
    """The live pile convention Q5 describes: bead id in frontmatter, not stem.

    Reproducing it here is what makes `artifact_trust.trusted` false and
    pushes `MBRF021` into `untrusted_diagnostics`, so the dashboard's handling
    of untrusted state is tested against the shape that actually occurs.
    """
    city_root, rig_root = runtime_fixture(tmp_path)
    pile = rig_root / ".beads" / "briefs" / ".pile"
    (pile / "07-inspect-open-brief.md").write_text(
        "---\nartifact: mc-open\n---\n\n# Inspect open brief\n", encoding="utf-8"
    )
    return city_root, rig_root


class RecordingClient:
    """Wraps a client and records every tool call the dashboard makes."""

    def __init__(self, inner):
        self.inner = inner
        self.calls: list[tuple[str, dict]] = []

    def list_tools(self):
        return self.inner.list_tools()

    def call(self, name, arguments=None):
        self.calls.append((name, dict(arguments or {})))
        return self.inner.call(name, arguments)

    @property
    def names(self) -> list[str]:
        return [name for name, _ in self.calls]


def client_for(city_root: Path, rig_root: Path) -> InProcessMcpClient:
    return InProcessMcpClient(
        city=city_root,
        rig="mathcity",
        env={"MCTL_BEADS_FIXTURE": str(rig_root / ".beads" / "issues.jsonl")},
    )


def dashboard_for(tmp_path: Path, *, untrusted: bool = False):
    city_root, rig_root = (untrusted_fixture if untrusted else runtime_fixture)(tmp_path)
    client = RecordingClient(client_for(city_root, rig_root))
    return Dashboard(client), client, city_root, rig_root


def body(dashboard, path: str, **query) -> str:
    response = dashboard.handle(Request.get(path, **query))
    assert response.status == 200, response.body
    return response.body


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html)


# --- the dashboard loads and resolves context through MCP --------------------


def test_the_dashboard_loads_and_resolves_context_through_mcp(tmp_path: Path):
    dashboard, client, city_root, _ = dashboard_for(tmp_path)

    html = body(dashboard, "/")

    assert "context_resolve" in client.names, "context must come from the MCP surface"
    assert str(city_root) in html
    assert "mathcity" in html


def test_context_is_the_first_visible_state_and_names_runtime_versus_checkout(tmp_path: Path):
    """Plan Slice 8 step 3: source checkout versus city runtime must be obvious."""
    dashboard, _, city_root, rig_root = dashboard_for(tmp_path)

    html = body(dashboard, "/")

    context_index = html.index("data-region=\"context\"")
    for later in ("data-region=\"queue\"",):
        assert context_index < html.index(later), "context must render before the queue"
    text = strip_tags(html)
    assert "City runtime" in text
    assert "Source checkout" in text
    assert str(rig_root) in html


def test_every_view_resolves_context_so_no_page_renders_an_unlabelled_rig(tmp_path: Path):
    dashboard, client, _, _ = dashboard_for(tmp_path)

    for path in ("/", "/briefs", "/briefs/mc-open", "/work", "/diagnostics"):
        client.calls.clear()
        body(dashboard, path)
        assert "context_resolve" in client.names, f"{path} rendered without resolving context"


# --- brief list and detail render canonical bead fields ---------------------


def test_the_brief_list_renders_canonical_bead_fields(tmp_path: Path):
    dashboard, client, _, _ = dashboard_for(tmp_path)

    html = body(dashboard, "/briefs")

    assert "briefs_list" in client.names
    text = strip_tags(html)
    for bead_id in ("mc-open", "mc-broken", "mc-closed", "mc-adjudicated"):
        assert bead_id in text
    assert "pending" in text
    assert "adjudicated" in text
    assert "bead_store" in text, "the canonical source must be stated, not implied"


def test_the_brief_list_filters_through_the_typed_tool_rather_than_in_the_page(tmp_path: Path):
    dashboard, client, _, _ = dashboard_for(tmp_path)

    body(dashboard, "/briefs", status="open")

    listing = next(args for name, args in client.calls if name == "briefs_list")
    assert listing["status"] == "open"


def test_the_brief_detail_view_renders_canonical_bead_fields_and_options(tmp_path: Path):
    dashboard, client, _, _ = dashboard_for(tmp_path)

    html = body(dashboard, "/briefs/mc-open")

    assert "briefs_show" in client.names
    assert "briefs_options" in client.names
    assert "briefs_doctor" in client.names, "the per-brief invariant view uses doctor"
    text = strip_tags(html)
    assert "mc-open" in text
    assert "Inspect open brief" in text
    assert "pending" in text
    assert "bead_store" in text
    assert "Adjudicate" in text
    assert "Dispatch work" in text


def test_a_disabled_option_shows_the_diagnostic_code_that_disabled_it(tmp_path: Path):
    dashboard, _, _, _ = dashboard_for(tmp_path)

    html = body(dashboard, "/briefs/mc-open")

    # dispatch-work is blocked on this fixture by MBRF011, and the operator
    # must be able to read the code, not just "unavailable".
    assert "MBRF011" in strip_tags(html)


def test_an_unknown_brief_renders_the_typed_diagnostic_not_a_traceback(tmp_path: Path):
    dashboard, _, _, _ = dashboard_for(tmp_path)

    response = dashboard.handle(Request.get("/briefs/mc-does-not-exist"))

    assert response.status == 404
    assert "Traceback" not in response.body
    assert "MBRF" in strip_tags(response.body)


# --- diagnostic code and severity are visible -------------------------------


def test_diagnostic_code_and_severity_are_both_visible(tmp_path: Path):
    dashboard, client, _, _ = dashboard_for(tmp_path)

    html = body(dashboard, "/diagnostics")

    # The rig-wide view reads `briefs_validate`, the strict superset of
    # `briefs_doctor`: MBRF021 is a strict invariant and only appears there.
    # `briefs_doctor` backs the per-brief view instead.
    assert "briefs_validate" in client.names
    text = strip_tags(html)
    assert "MBRF004" in text, "the diagnostic code itself must never be hidden"
    assert "MBRF005" in text
    assert "ERROR" in text
    assert 'data-severity="ERROR"' in html, "severity needs visual treatment too"


def test_severity_gets_visual_treatment_without_replacing_the_code(tmp_path: Path):
    dashboard, _, _, _ = dashboard_for(tmp_path)

    html = body(dashboard, "/diagnostics")

    for severity in ("INFO", "WARN", "ERROR", "FATAL"):
        assert f".severity-{severity}" in html, f"no visual treatment declared for {severity}"
    # Every rendered severity badge sits beside a code element.
    codes = re.findall(r'<code class="diagnostic-code">([A-Z0-9_]+)</code>', html)
    assert codes, "diagnostics must render their code in a dedicated element"
    assert any(code.startswith("MBRF") for code in codes)


# --- the three codes that must not be presented as actionable ---------------


def test_untrusted_diagnostics_are_not_rendered_as_actionable_findings(tmp_path: Path):
    dashboard, _, _, _ = dashboard_for(tmp_path, untrusted=True)

    html = body(dashboard, "/diagnostics")

    assert "MBRF021" in strip_tags(html), "withholding it silently would hide real state"
    withheld = html.index('data-region="untrusted-diagnostics"')
    actionable = html.index('data-region="actionable-diagnostics"')
    assert actionable < withheld
    # MBRF021 must appear only inside the withheld region.
    assert "MBRF021" not in html[actionable:withheld]
    assert "MBRF021" in html[withheld:]


def test_artifact_trust_false_is_surfaced_where_artifact_state_is_shown(tmp_path: Path):
    dashboard, _, _, _ = dashboard_for(tmp_path, untrusted=True)

    html = body(dashboard, "/briefs/mc-open")

    text = strip_tags(html)
    assert 'data-artifact-trust="false"' in html
    assert "Q5" in text
    assert "OPEN-DESIGN-QUESTIONS" in text
    assert "unverified" in text, "an unverifiable reading must not be shown as `missing`"


def test_artifact_trust_true_is_also_stated_rather_than_left_blank(tmp_path: Path):
    dashboard, _, _, _ = dashboard_for(tmp_path)

    html = body(dashboard, "/briefs/mc-open")

    assert 'data-artifact-trust="true"' in html


def test_the_three_under_review_codes_are_labelled_and_never_offered_a_fix(tmp_path: Path):
    dashboard, _, _, _ = dashboard_for(tmp_path, untrusted=True)

    pages = [body(dashboard, "/diagnostics"), body(dashboard, "/briefs/mc-closed")]

    assert UNDER_REVIEW_CODES == frozenset({"MBRF004", "MBRF005", "MBRF021"})
    joined = "\n".join(pages)
    assert "MALFORMED-BRIEF-TRIAGE-2026-08-19" in joined
    assert "OPEN-DESIGN-QUESTIONS" in joined
    assert "under review" in strip_tags(joined).lower()
    # No repair affordance anywhere: the dashboard offers adjudicate/defer,
    # never "fix this diagnostic". Asserted against the controls, not against
    # prose -- a core diagnostic is free to use the word "repair" in its text.
    for banned in ('action="/repair"', ">Repair<", ">Fix<", "Fix these", "auto-repair"):
        assert banned not in joined
    assert Dashboard.MUTATION_ROUTES == ("/preview", "/apply")


def test_the_malformed_count_carries_its_caveat(tmp_path: Path):
    dashboard, _, _, _ = dashboard_for(tmp_path)

    text = strip_tags(body(dashboard, "/"))

    assert "malformed" in text
    normalized = " ".join(text.split())
    assert "closed with no verdict field" in normalized.lower()
    assert "close_reason" in normalized


def test_under_review_diagnostics_are_excluded_from_the_actionable_count(tmp_path: Path):
    dashboard, _, _, _ = dashboard_for(tmp_path)

    html = body(dashboard, "/diagnostics")

    actionable = int(re.search(r'data-actionable-count="(\d+)"', html).group(1))
    under_review = int(re.search(r'data-under-review-count="(\d+)"', html).group(1))
    assert under_review >= 2, "MBRF004 and MBRF005 both fire on this fixture"
    codes = re.findall(r'<code class="diagnostic-code">([A-Z0-9_]+)</code>', html)
    assert actionable == len([code for code in codes if code not in UNDER_REVIEW_CODES])


# --- no generic command execution -------------------------------------------


def test_the_dashboard_allowlist_contains_no_command_execution_tool():
    """The boundary, and a tripwire on its size.

    The count is pinned so that widening the dashboard's reach is a deliberate,
    reviewable act rather than something that happens by accident. It did its
    job: adding `gates_status` tripped it.

    19 since `gates_status` was added. `mctl_core/gates.py` shipped with #119
    and had no MCP tool, so no page could call it -- #153's deeper shape, where
    a merged and tested surface is unreachable rather than merely unrendered.
    A read-only city surface, on the same footing as `fleet_sessions` and
    `city_health`.

    22 since `blast_radius_registry` was added: #110 shipped
    `mctl_core/blast_radius.py` with no MCP tool and no consumer, so no page
    could reach it. A read-only city surface, same footing as `gates_status`.

    Raise this number only alongside the tool that justifies it, and say which
    tool in the docstring.
    """
    assert ALLOWED_TOOLS & mcp_server.FORBIDDEN_TOOL_NAMES == frozenset()
    assert ALLOWED_TOOLS <= frozenset(mcp_server.TOOLS_BY_NAME)
    # A drift alarm on a security-relevant list: the allowlist must stay
    # NARROWER than the server surface, so this stays a literal deliberately.
    # Registry-relative would assert allowlist == tools, which is the opposite
    # of what this guards. Bumped for molecules_list/_show (#111).
    assert len(ALLOWED_TOOLS) == 25


def test_the_client_refuses_a_tool_outside_the_typed_surface(tmp_path: Path):
    city_root, rig_root = runtime_fixture(tmp_path)
    client = client_for(city_root, rig_root)

    for name in ("shell", "run_command", "exec", "briefs_teleport"):
        try:
            client.call(name, {})
        except UnknownToolError:
            continue
        raise AssertionError(f"{name} was not refused")


def test_no_view_calls_anything_outside_the_typed_surface(tmp_path: Path):
    dashboard, client, _, _ = dashboard_for(tmp_path)

    for path in ("/", "/briefs", "/briefs/mc-open", "/work", "/diagnostics", "/validate"):
        dashboard.handle(Request.get(path))

    assert client.names, "the dashboard must actually be talking to the server"
    assert set(client.names) <= ALLOWED_TOOLS
    for _, arguments in client.calls:
        assert "command" not in arguments
        assert "argv" not in arguments


def test_the_dashboard_source_contains_no_shell_shaped_escape_hatch():
    sources = {path: path.read_text(encoding="utf-8") for path in DASHBOARD_PACKAGE.glob("*.py")}
    assert sources, "the dashboard package must exist"
    for path, source in sources.items():
        for banned in ("os.system", "shell=True", "os.popen", "subprocess.call(", "eval("):
            assert banned not in source, f"{path.name} contains {banned}"
    # The one subprocess in the package is the MCP transport itself, and it
    # runs a fixed argv: `mctl mcp serve`, never operator-supplied text.
    spawning = [path.name for path, source in sources.items() if "Popen" in source]
    assert spawning == ["client.py"], spawning


# --- no repair on read -------------------------------------------------------


def test_rendering_a_view_never_calls_a_mutating_tool(tmp_path: Path):
    """No repair-on-read: a GET may not so much as plan a mutation."""
    dashboard, client, _, _ = dashboard_for(tmp_path)

    for path in ("/", "/briefs", "/briefs/mc-open", "/briefs/mc-closed", "/work", "/diagnostics"):
        dashboard.handle(Request.get(path))

    assert set(client.names) <= READ_ONLY_TOOLS, sorted(set(client.names) - READ_ONLY_TOOLS)


def test_rendering_a_view_writes_nothing_under_the_rig(tmp_path: Path):
    dashboard, _, _, rig_root = dashboard_for(tmp_path)
    before = {path: path.stat().st_mtime_ns for path in sorted(rig_root.rglob("*")) if path.is_file()}

    for path in ("/", "/briefs", "/briefs/mc-open", "/work", "/diagnostics", "/validate"):
        dashboard.handle(Request.get(path))

    after = {path: path.stat().st_mtime_ns for path in sorted(rig_root.rglob("*")) if path.is_file()}
    assert after == before


# --- work and trace views ----------------------------------------------------


def test_the_work_view_renders_readiness_through_the_work_tools(tmp_path: Path):
    dashboard, client, _, _ = dashboard_for(tmp_path)

    html = body(dashboard, "/work")

    assert "work_ready" in client.names
    assert "Ready work" in strip_tags(html)


def test_the_trace_view_previews_a_replay_without_applying_it(tmp_path: Path):
    dashboard, client, _, _ = dashboard_for(tmp_path)

    response = dashboard.handle(Request.get("/trace", trace_id="not-a-real-trace"))

    assert response.status == 200
    assert "trace_show" in client.names
    assert "MCTL_TRACE_NOT_FOUND" in strip_tags(response.body)
    assert 'action="/apply"' not in response.body, "a replay view must offer nothing to apply"


# --- responsive shell --------------------------------------------------------


def test_every_page_declares_a_mobile_viewport_and_a_breakpoint(tmp_path: Path):
    dashboard, _, _, _ = dashboard_for(tmp_path)

    for path in ("/", "/briefs", "/briefs/mc-open", "/work", "/diagnostics"):
        html = body(dashboard, path)
        assert 'name="viewport"' in html
        assert "width=device-width" in html
        assert "@media (max-width:" in html
