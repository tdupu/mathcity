"""A dead MCP child must name itself, not surface a raw OS error.

`#166`. Taylor's dashboard served 500 on every route for about an hour while he
slept. Its MCP subprocess had died and become a zombie; the dashboard was alive
and had no data source, so every fetch wrote to a closed pipe:

    BrokenPipeError: [Errno 32] Broken pipe

The maddening part is that the right diagnostic already existed **in the same
function** -- `MCTL_DASH_SERVER_GONE`, *"Restart the dashboard; the server
subprocess is no longer running"* -- and was unreachable. It sits on the
`readline()` branch, which handles the *graceful* death: the child closed stdout
and exited. When the child is already gone, the **write** fails first, and the
branch that would have explained it is never evaluated.

So the operator got a raw OS error instead of the sentence someone had already
written for exactly this situation.

Both orders must produce the same, actionable diagnostic. The exit code is
carried where it can be: it is the only evidence of *why* the child died, and
in the live incident it was lost.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.client import StdioMcpClient, ToolFailure


class _DeadPipe:
    """stdin on a child that has already exited."""

    def write(self, _data):
        raise BrokenPipeError(32, "Broken pipe")

    def flush(self):
        raise BrokenPipeError(32, "Broken pipe")


class _DeadChild:
    """A child that exited. `poll()` returns its status, as Popen does."""

    returncode = 9

    def __init__(self):
        self.stdin = _DeadPipe()
        self.stdout = None
        self.stderr = None

    def poll(self):
        return self.returncode


def _client_with_dead_child():
    client = StdioMcpClient.__new__(StdioMcpClient)
    client.process = _DeadChild()
    return client


def test_a_dead_child_raises_the_named_diagnostic_not_a_raw_oserror():
    client = _client_with_dead_child()
    with pytest.raises(ToolFailure) as caught:
        client._exchange({"method": "tools/call"})
    codes = [d.get("code") for d in caught.value.diagnostics]
    assert "MCTL_DASH_SERVER_GONE" in codes


def test_the_diagnostic_carries_the_child_exit_code():
    """The live incident lost this, and it is the only evidence of WHY the
    child died. `BrokenPipeError` alone cannot carry it."""
    client = _client_with_dead_child()
    with pytest.raises(ToolFailure) as caught:
        client._exchange({"method": "tools/call"})
    facts = caught.value.diagnostics[0].get("facts") or {}
    assert facts.get("exit_code") == 9


def test_the_hint_tells_the_operator_what_to_do():
    client = _client_with_dead_child()
    with pytest.raises(ToolFailure) as caught:
        client._exchange({"method": "tools/call"})
    hint = str(caught.value.diagnostics[0].get("hint") or "").lower()
    assert "restart" in hint


def test_a_broken_pipe_with_no_exit_status_still_names_the_cause():
    """Belt and braces: if the write fails while `poll()` still reports the
    child as running, the pipe is authoritative -- something is wrong with the
    channel and a raw OSError is still the wrong thing to show."""

    class _RunningButBroken(_DeadChild):
        def poll(self):
            return None

    client = StdioMcpClient.__new__(StdioMcpClient)
    client.process = _RunningButBroken()
    with pytest.raises(ToolFailure) as caught:
        client._exchange({"method": "tools/call"})
    assert "MCTL_DASH_SERVER_GONE" in [d.get("code") for d in caught.value.diagnostics]


# ---------------------------------------------------------------------------
# and the operator has to SEE it
# ---------------------------------------------------------------------------


def test_the_page_shows_the_hint_not_a_generic_defect_message():
    """The diagnostic is worthless if the page swallows it.

    The generic unhandled-exception guard renders "this is a defect in the
    dashboard" -- true, and it tells the operator nothing to do. A
    `ToolFailure` carries a hint written for exactly this moment; the page
    must show it.
    """
    from mctl_dashboard.app import Dashboard, Request

    class _DeadClient:
        def call(self, name, *a, **k):
            raise ToolFailure(
                name,
                [
                    {
                        "severity": "FATAL",
                        "code": "MCTL_DASH_SERVER_GONE",
                        "message": "The mctl MCP server closed the connection.",
                        "hint": "Restart the dashboard; the server subprocess is no longer running.",
                        "facts": {"exit_code": 9},
                    }
                ],
                {},
            )

        def list_tools(self):
            return []

        def clone(self):
            return self

    body = Dashboard(_DeadClient(), city_wide=True, rig=None).handle(Request.get("/queue")).body
    assert "MCTL_DASH_SERVER_GONE" in body
    assert "Restart the dashboard" in body, "the actionable hint was swallowed"


# ---------------------------------------------------------------------------
# the second exception, which was caught and never exercised
# ---------------------------------------------------------------------------


def test_a_closed_pipe_object_also_names_the_cause():
    """sally's review of `#166`: the `ValueError` arm had 0 test mentions.

    Writing to a *closed* file object raises `ValueError: I/O operation on
    closed file`, not `BrokenPipeError` — a genuinely different second case,
    and the one that occurs when the pipe was closed on this side rather than
    dying on the other.

    The handler is shared, so the code worked; what was untested is that the
    second exception actually reaches it. An `except` arm nothing exercises is
    a claim, not a behaviour — which is the shape this file exists to remove.
    """

    class _ClosedPipe:
        def write(self, _data):
            raise ValueError("I/O operation on closed file")

        def flush(self):  # pragma: no cover - write raises first
            raise ValueError("I/O operation on closed file")

    class _ChildWithClosedStdin(_DeadChild):
        def __init__(self):
            super().__init__()
            self.stdin = _ClosedPipe()

    client = StdioMcpClient.__new__(StdioMcpClient)
    client.process = _ChildWithClosedStdin()

    with pytest.raises(ToolFailure) as caught:
        client._exchange({"method": "tools/call"})

    diagnostic = caught.value.diagnostics[0]
    assert diagnostic.get("code") == "MCTL_DASH_SERVER_GONE"
    # The write_error fact must name what actually happened, so a reader can
    # tell the two arms apart in a trace rather than seeing one blurred cause.
    assert "ValueError" in str((diagnostic.get("facts") or {}).get("write_error"))
