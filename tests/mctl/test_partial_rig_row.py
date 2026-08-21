"""A partial rig's rows are counted in the city total, so its row must show them.

`hq` on the live city answers from its documents while its bead store times out.
The API reports that faithfully -- `counts.briefs: 220`, `ok: false`,
`partial: true` -- and those 220 briefs are inside the city total. The table
rendered them as "could not be read" with no numbers, so the visible rows summed
to 135 against a city row of 355, under a caption promising the total *is* the
sum of the rows.

The existing multi-rig fixture models a rig with no store at all, which is the
`unreadable` case. Nothing exercised a rig that contributed rows and still failed,
which is why this survived.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "assets" / "scripts"))

from mctl_dashboard import render


class _Rig:
    def __init__(self, rig_id, ok, partial, reason=""):
        self.rig_id = rig_id
        self.ok = ok
        self.partial = partial
        self.reason = reason


class _View:
    """The live shape: one partial rig holding most of the city's briefs."""

    def __init__(self):
        self.rigs = (
            _Rig("hecke", ok=True, partial=False),
            _Rig("hq", ok=False, partial=True, reason="the bead store could not be read"),
            _Rig("gone", ok=False, partial=False, reason="no store"),
        )
        self._counts = {
            "hecke": {"pending": 45, "adjudicated": 31},
            "hq": {"pending": 100, "adjudicated": 120},
            "gone": {},
        }

    @property
    def rows(self):
        """One entry per brief actually in the payload -- hq's included."""
        return tuple(range(sum(self.state_counts().values())))

    @property
    def healthy(self):
        return tuple(r for r in self.rigs if r.ok)

    def state_counts(self, rig_id=None):
        if rig_id is None:
            total: dict[str, int] = {}
            for counts in self._counts.values():
                for state, n in counts.items():
                    total[state] = total.get(state, 0) + n
            return total
        return dict(self._counts.get(rig_id, {}))


def _row_numbers(html: str, rig: str) -> list[int]:
    """The per-state cells of a rig's row, without its trailing total cell."""
    match = re.search(rf'<tr data-rig="{rig}"[^>]*>(.*?)</tr>', html, re.S)
    assert match, f"no row rendered for {rig}"
    cells = [int(n) for n in re.findall(r'<td class="mono">(\d+)</td>', match.group(1))]
    if not cells:
        return cells
    states, total = cells[:-1], cells[-1]
    assert sum(states) == total, (
        f"{rig}'s row total ({total}) disagrees with its own cells ({states})"
    )
    return states


def test_a_partial_rig_shows_the_counts_it_contributed():
    """The numbers exist and are already in the total; the row must print them."""
    html = render.city_queue_panel(_View())

    assert sorted(_row_numbers(html, "hq")) == [100, 120], (
        "hq contributed 220 briefs that are inside the city total; its row "
        "showed no numbers at all"
    )


def test_the_visible_rows_sum_to_the_city_total():
    """The caption promises this. It was 135 against 355 on the live page."""
    html = render.city_queue_panel(_View())

    per_rig = sum(sum(_row_numbers(html, rig)) for rig in ("hecke", "hq"))
    city = sum(_View().state_counts().values())

    assert per_rig == city, f"rows summed to {per_rig}, city total is {city}"


def test_a_genuinely_unreadable_rig_still_renders_no_numbers():
    """The distinction must survive the fix: `gone` contributed nothing."""
    html = render.city_queue_panel(_View())

    match = re.search(r'<tr data-rig="gone"[^>]*>(.*?)</tr>', html, re.S)
    assert match, "the unreadable rig must still appear"
    assert not re.findall(r'<td class="mono">\d+</td>', match.group(1)), (
        "a rig that contributed nothing must not display fabricated zeros"
    )
    assert "could not be read" in match.group(1)
