"""One read that knows both shapes the core returns."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "assets" / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "assets" / "scripts"))


def _fielded(**pairs):
    return {"fields": {k: {"name": k, "value": v, "readings": []}
                       for k, v in pairs.items()}}


def test_reads_a_top_level_value():
    from mctl_dashboard.reading import attr

    assert attr({"unlock_count": 3}, "unlock_count") == 3


def test_reads_a_value_under_fields():
    from mctl_dashboard.reading import attr

    assert attr(_fielded(unlock_count=3), "unlock_count") == 3


def test_top_level_wins_over_fields():
    from mctl_dashboard.reading import attr

    row = _fielded(unlock_count=3)
    row["unlock_count"] = 9
    assert attr(row, "unlock_count") == 9


def test_zero_and_false_are_values_not_absences():
    from mctl_dashboard.reading import attr

    assert attr(_fielded(unlock_count=0), "unlock_count") == 0
    assert attr(_fielded(server_touching=False), "server_touching") is False


def test_a_genuinely_absent_key_returns_the_default():
    from mctl_dashboard.reading import attr

    assert attr(_fielded(track="x"), "unlock_count") is None
    assert attr({}, "unlock_count", "fallback") == "fallback"


def test_a_malformed_fields_entry_does_not_raise():
    from mctl_dashboard.reading import attr

    assert attr({"fields": {"unlock_count": "not-a-mapping"}}, "unlock_count") is None
    assert attr({"fields": None}, "unlock_count") is None
