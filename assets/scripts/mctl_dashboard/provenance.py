"""Where the data on this page came from, derived rather than asserted.

The dashboard reads a real city by default and a JSONL fixture when
`MCTL_BEADS_FIXTURE` -- or its per-rig form `MCTL_BEADS_FIXTURE_<rig>` -- is
set. A fixture-backed render and a live render were pixel-identical, so nothing
distinguished invented numbers from measured ones. That is §5's rule applied to
the page's own provenance: **a page that cannot tell you where its data came
from is a page that can lie about it.**

Two properties this module exists to hold:

**Derived, not declared.** The answer comes from the same environment the read
resolves against (`context.py:485`), not from a caller passing `live=True`. A
caller that can assert its own provenance can assert it wrongly, and the whole
point is that the page cannot be wrong about this.

**Not rounded.** One fixture-backed rig in a seventeen-rig read makes the page
not-live. Reporting "live" because most of it was is the majority-path lie this
is here to prevent.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping, Sequence

#: Must match `context.BEADS_FIXTURE_ENV`. Duplicated rather than imported so
#: the dashboard package does not depend on the core to render its own shell --
#: the shell must render even when a core read is what failed.
BEADS_FIXTURE_ENV = "MCTL_BEADS_FIXTURE"


@dataclass(frozen=True)
class DataProvenance:
    """Which rigs on this page are fixture-backed. Empty means live."""

    fixtures: tuple[tuple[str, str], ...] = ()

    @property
    def is_live(self) -> bool:
        return not self.fixtures


def fixture_sources(
    env: Mapping[str, str] | None = None, rig_ids: Sequence[str] = ()
) -> tuple[tuple[str, str], ...]:
    """`(rig_id, fixture_path)` for every rig reading a fixture, in rig order.

    Per-rig beats global, matching how `context.py` resolves it -- a city-wide
    read touches several rigs in one process, and a single global path would
    make every rig report the same beads.
    """
    environ = os.environ if env is None else env
    found: list[tuple[str, str]] = []
    for rig_id in rig_ids:
        path = environ.get(f"{BEADS_FIXTURE_ENV}_{rig_id}") or environ.get(BEADS_FIXTURE_ENV)
        if path:
            found.append((rig_id, str(path)))
    if found:
        return tuple(found)
    # No rig list, but a global fixture is set: report it against a placeholder
    # rather than returning "live". An unknown rig list must not resolve to the
    # reassuring answer -- the no-rig-list path is exactly the one a caller who
    # forgot to pass provenance takes, so it is the one that must not lie.
    global_path = environ.get(BEADS_FIXTURE_ENV)
    if global_path and not rig_ids:
        return (("(all rigs)", str(global_path)),)
    return ()


def resolve(
    env: Mapping[str, str] | None = None, rig_ids: Sequence[str] = ()
) -> DataProvenance:
    return DataProvenance(fixtures=fixture_sources(env, rig_ids))
