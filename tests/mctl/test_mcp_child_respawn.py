"""A dead MCP child is health-checked and respawned before the next request.

`#165`. Taylor's dashboard (:8491) went from serving `/queue` to bare 500s with
no restart and no code change under it: its MCP subprocess had died and become a
`Z <defunct>` zombie, the parent had zero live children, and NOTHING ever polled
that child or spawned a replacement. Every subsequent request needing a tool
call failed -- some as a 500, some as a page rendering every count as an em-dash,
which is indistinguishable from a city that genuinely has no data.

`#166` (its sibling) made the death *loud*: a child that dies mid-exchange now
raises the named `MCTL_DASH_SERVER_GONE` diagnostic instead of a raw
`BrokenPipeError`, and the page shows the operator what to do. That is the
detect-and-fail-loudly half.

This file is the other half the issue's title names: **health-check + respawn**.
A child that is ALREADY dead when a request arrives is detected by `poll()`
before the write, and a fresh subprocess is spawned to serve the request -- so a
transient child death becomes an invisible hiccup, not a dashboard an operator
has to notice is broken and restart by hand.

The respawn is BOUNDED, per the issue's own trade-off note ("what if respawn
itself fails? needs its own named diagnostic, not a silent retry-forever loop").
After a small number of consecutive respawns that never yield a working child,
the client stops spawning and raises the same named diagnostic, carrying the
fact that respawn was tried and exhausted. A single successful exchange resets
that budget, so a long-lived client that recovers now and then is never capped.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))

from mctl_dashboard.client import StdioMcpClient, ToolFailure


class _Pipe:
    """A child's stdin. Broken (child already gone) or accepting."""

    def __init__(self, *, broken: bool):
        self.broken = broken
        self.written: list[str] = []

    def write(self, data):
        if self.broken:
            raise BrokenPipeError(32, "Broken pipe")
        self.written.append(data)

    def flush(self):
        if self.broken:
            raise BrokenPipeError(32, "Broken pipe")


class _Stdout:
    def __init__(self, line: str):
        self._line = line

    def readline(self):
        return self._line


class _Stderr:
    def read(self):
        return ""


class _FakeChild:
    """A stand-in for the Popen subprocess.

    `exit_code=None` is a live, healthy child that answers `response`; any int is
    a child that has already exited (`poll()` returns it, the pipe is broken).
    """

    def __init__(self, *, exit_code: int | None = None, response: dict | None = None):
        self._exit = exit_code
        self.stdin = _Pipe(broken=exit_code is not None)
        line = (json.dumps(response) + "\n") if response is not None else ""
        self.stdout = _Stdout(line)
        self.stderr = _Stderr()

    def poll(self):
        return self._exit


def _client_with(first_child: _FakeChild) -> tuple[StdioMcpClient, list]:
    """A client whose subprocess is `first_child`, with `_spawn` faked.

    `_spawn` pops the next child from `queue` and installs it, recording each
    call. That is exactly the seam the real `_spawn` provides: build a fresh
    Popen and bind it to `self.process`.
    """
    client = StdioMcpClient.__new__(StdioMcpClient)
    _JsonRpcInit(client)
    client.process = first_child
    queue: list[_FakeChild] = []
    spawns: list[_FakeChild] = []

    def fake_spawn():
        child = queue.pop(0)
        client.process = child
        spawns.append(child)

    client._spawn = fake_spawn  # type: ignore[assignment]
    client._spawn_queue = queue  # type: ignore[attr-defined]
    client._spawns = spawns  # type: ignore[attr-defined]
    return client, spawns


def _JsonRpcInit(client: StdioMcpClient) -> None:
    """Run the `_JsonRpcClient.__init__` bookkeeping `__new__` skipped."""
    from mctl_dashboard.client import _JsonRpcClient

    _JsonRpcClient.__init__(client)


_OK = {"jsonrpc": "2.0", "id": 1, "result": {"ok": True}}


def test_a_dead_child_is_respawned_and_the_request_then_succeeds():
    """The #165 core: a child already dead when the request arrives is replaced,
    and the request is served against the fresh child rather than erroring."""
    client, spawns = _client_with(_FakeChild(exit_code=9))
    client._spawn_queue.append(_FakeChild(response=_OK))  # the healthy replacement

    result = client._exchange({"jsonrpc": "2.0", "id": 1, "method": "tools/call"})

    assert result == _OK
    assert len(spawns) == 1, "exactly one respawn, of the dead child"


def test_a_healthy_child_is_not_respawned():
    """poll() is None -> no death -> no new process. The health check must not
    fire on a working child (that would be the fork-bomb failure mode)."""
    client, spawns = _client_with(_FakeChild(response=_OK))

    result = client._exchange({"jsonrpc": "2.0", "id": 1, "method": "tools/call"})

    assert result == _OK
    assert spawns == [], "a live child must never be replaced"


def test_respawn_resets_initialization_so_the_fresh_child_is_handshaked():
    """A new process has not seen `initialize`. The client must re-run the
    handshake against it, so the caller cannot end up talking to an
    un-initialized server thinking it is initialized."""
    client, _ = _client_with(_FakeChild(exit_code=9))
    client._initialized = True
    client._spawn_queue.append(_FakeChild(response=_OK))

    client._exchange({"jsonrpc": "2.0", "id": 1, "method": "tools/call"})

    assert client._initialized is False


def test_respawn_is_bounded_and_names_the_exhaustion():
    """The issue's explicit guard against a retry-forever loop: if every fresh
    child is also dead, stop spawning after a small budget and raise the named
    diagnostic, carrying that respawn was tried and exhausted."""
    client, spawns = _client_with(_FakeChild(exit_code=9))
    # An unbounded supply of already-dead replacements.
    for _ in range(50):
        client._spawn_queue.append(_FakeChild(exit_code=9))

    # Drive the client until it refuses to keep spawning.
    last: ToolFailure | None = None
    for _ in range(20):
        with pytest.raises(ToolFailure) as caught:
            client._exchange({"jsonrpc": "2.0", "id": 1, "method": "tools/call"})
        last = caught.value

    assert last is not None
    codes = [d.get("code") for d in last.diagnostics]
    assert "MCTL_DASH_SERVER_GONE" in codes
    facts = last.diagnostics[0].get("facts") or {}
    assert "respawns_exhausted" in facts, "the diagnostic must say respawn gave up"
    assert len(spawns) <= StdioMcpClient._MAX_RESPAWNS, (
        f"respawn must be bounded, spawned {len(spawns)} times"
    )


def test_a_successful_exchange_resets_the_respawn_budget():
    """A client that recovers, works, then loses its child again much later must
    get a fresh budget -- the cap is on *consecutive* failed respawns, not on
    the lifetime of the client."""
    client, spawns = _client_with(_FakeChild(exit_code=9))
    client._spawn_queue.append(_FakeChild(response=_OK))  # recovers
    client._exchange({"jsonrpc": "2.0", "id": 1, "method": "tools/call"})
    assert client._respawns == 0, "a working exchange clears the budget"

    # Much later, its child dies again; it must be willing to respawn afresh.
    client.process = _FakeChild(exit_code=9)
    client._spawn_queue.append(_FakeChild(response=_OK))
    result = client._exchange({"jsonrpc": "2.0", "id": 1, "method": "tools/call"})
    assert result == _OK
    assert len(spawns) == 2
