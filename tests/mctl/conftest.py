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
