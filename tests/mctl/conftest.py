"""Test-wide guard: the suite must not ring the REAL city's doorbells.

MEASURED 2026-08-28. `gc` is on PATH on a developer box, and mctl's event
emitter shells straight to `gc event emit`. Every test that drove a LIVE apply
therefore published to the live bus: 329 `brief.decided` events carrying the
fixture subject `mc-open` and 60 carrying `gs-open` were on it within 24h, the
oldest timestamped 2026-08-27T18:38 -- so this predates, and is independent of,
the CLI doorbell landing alongside this file.

`brief.decided` has THREE consumers (brief-decision-dispatch,
post-decision-file-or-sendback, revise-return), so each stray event woke three
orders to look for a brief that does not exist. Wiring the CLI verdict path to
the same doorbell would have widened that, which is why the switch lands here.

A test that WANTS to observe an emission opts back in explicitly -- either by
injecting a runner (the switch is not honoured for an injected runner) or by
setting `MCTL_CITY_EVENTS=1` in the environment of a subprocess it aims at a
fake `gc`, which is what test_cli_adjudicate_emits_decided.py does.
"""
from __future__ import annotations

import pytest


@pytest.fixture(autouse=True, scope="session")
def _no_real_city_events() -> None:
    import os

    os.environ["MCTL_CITY_EVENTS"] = "0"


@pytest.fixture(autouse=True)
def _isolate_aggregated_brief_root(tmp_path_factory, monkeypatch) -> None:
    """Pin the aggregated brief root to a fresh per-test tmp dir.

    `effects._aggregated_brief_root()` (gt-5yxup1) defaults to the home-global
    `~/.gc/mathcity/aggregated-briefs` -- the SAME path the running city reads.
    Any in-process test that drives `plan_adjudication` without this override
    writes verdict records straight into that live path and accumulates them
    across the run: a data-integrity leak into live city data, and a source of
    order-dependent cross-test failures (the doorbell family that
    `_no_real_city_events` guards, one root over). A fresh root per test isolates
    the write completely; a test that wants to observe the real default injects
    its own value, exactly as `test_adjudication_writes_aggregated_decision.py`
    already does for its subprocess.
    """
    root = tmp_path_factory.mktemp("agg_brief_root")
    monkeypatch.setenv("MCTL_AGGREGATED_BRIEF_ROOT", str(root))
