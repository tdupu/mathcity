"""#116: the ticker had a vocabulary, no reader, and no tool.

`mctl_core/ticker.py` has held the tiers, the default-hidden chatter band and
the cause/response pairing since it was written, and it is tested. It had no
way IN, so the dashboard's Events panel rendered `city_screen.unwired()`,
saying in as many words: *"Built, and not reachable from any page ... So there
is nothing for this screen to call."*

`ticker_read.py` is the way in.

NAMED `ticker_read`, NOT `events`. `mctl_core/events.py` already exists and is
the trace/event WRITE helper (`append_jsonl`) that `trace.py` imports. I took
that name first and broke every import in the package -- 102 collection errors
in one run. The suite caught it immediately, which is the system working; the
test at the bottom pins the distinction so nobody repeats it.

THE DENOMINATOR IS THE POINT. The live log measured 218 MB, so this reads a
bounded TAIL. Every count is therefore within the window scanned, and the field
is called `available_in_scan` rather than `available` for exactly that reason:
#124 records that quoting a partial figure as a population is how "every figure
is a FLOOR" gets forgotten. The truncation is reported, not inferred.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_ROOT = REPO_ROOT / "assets" / "scripts"
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core import ticker
from mctl_core.ticker_read import city_reader, events_list


def _write_log(root: Path, rows: list[dict]) -> Path:
    log = root / ".gc" / "events.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    return log


def _rows() -> list[dict]:
    return [
        {"ts": "2026-08-29T01:00:00", "type": "order.fired", "subject": "answered"},
        {"ts": "2026-08-29T01:00:01", "type": "order.completed", "subject": "answered"},
        {"ts": "2026-08-29T02:00:00", "type": "order.fired", "subject": "silent"},
        {"ts": "2026-08-29T03:00:00", "type": "bead.updated", "subject": "chatty"},
        {"ts": "2026-08-29T04:00:00", "type": "bead.closed", "subject": "done"},
        {"ts": "2026-08-29T05:00:00", "type": "brand.new.type", "subject": "novel"},
    ]


# --- the read itself --------------------------------------------------------


def test_a_missing_log_is_unreachable_not_empty(tmp_path: Path) -> None:
    """The distinction the whole module exists to protect."""
    result = events_list(city_reader(tmp_path))
    assert result["state"] == "unreachable"
    assert result["events"] is None, "None, never [] -- an empty list asserts a quiet city"
    assert result["available_in_scan"] is None
    assert any(d["code"] == "MEVT_EVENTS_UNREACHABLE" for d in result["diagnostics"])


def test_events_come_back_newest_first(tmp_path: Path) -> None:
    _write_log(tmp_path, _rows())
    result = events_list(city_reader(tmp_path))
    stamps = [row["ts"] for row in result["events"]]
    assert stamps == sorted(stamps, reverse=True)
    assert result["state"] == "healthy"


def test_chatter_is_hidden_by_default_and_returns_on_request(tmp_path: Path) -> None:
    _write_log(tmp_path, _rows())
    default = events_list(city_reader(tmp_path))
    assert not any(r["type"] == "bead.updated" for r in default["events"])
    assert default["chatter_included"] is False

    loud = events_list(city_reader(tmp_path), include_chatter=True)
    assert any(r["type"] == "bead.updated" for r in loud["events"])
    assert loud["chatter_included"] is True


def test_an_unclassified_type_always_survives_the_filter(tmp_path: Path) -> None:
    """ticker.py's rule, carried to the payload: defaulting a new type to
    chatter is how a newly-introduced event vanishes for a week."""
    _write_log(tmp_path, _rows())
    result = events_list(city_reader(tmp_path))
    novel = [r for r in result["events"] if r["type"] == "brand.new.type"]
    assert novel, "an unknown type must not be filtered away"
    assert novel[0]["tier"] == ticker.UNKNOWN_TIER


def test_unanswered_causes_are_named_and_answered_ones_are_not(tmp_path: Path) -> None:
    _write_log(tmp_path, _rows())
    result = events_list(city_reader(tmp_path))
    subjects = {p["cause"]["subject"] for p in result["unanswered_causes"]}
    assert "silent" in subjects
    assert "answered" not in subjects


def test_unanswered_causes_are_paired_across_the_window_not_the_page(tmp_path: Path) -> None:
    """Pairing inside one page would invent a break at every page boundary."""
    _write_log(tmp_path, _rows())
    result = events_list(city_reader(tmp_path), limit=1)
    assert result["returned"] == 1
    # `answered` is still not reported unanswered even though its response is
    # far outside the single returned row.
    assert {p["cause"]["subject"] for p in result["unanswered_causes"]} == {"silent"}


# --- the denominator --------------------------------------------------------


def test_an_untruncated_scan_says_so(tmp_path: Path) -> None:
    _write_log(tmp_path, _rows())
    result = events_list(city_reader(tmp_path))
    assert result["scan"]["truncated"] is False
    assert not any(d["code"] == "MEVT_SCAN_TRUNCATED" for d in result["diagnostics"])


def test_a_truncated_scan_warns_and_reports_the_window(tmp_path: Path) -> None:
    """The count must be presentable as a floor, not as the population."""
    log = _write_log(tmp_path, _rows())
    result = events_list(city_reader(tmp_path, tail_bytes=120))
    assert result["scan"]["truncated"] is True
    assert result["scan"]["log_bytes"] == log.stat().st_size
    assert result["scan"]["scanned_bytes"] == 120
    assert result["state"] == "degraded"
    assert any(d["code"] == "MEVT_SCAN_TRUNCATED" for d in result["diagnostics"])


def test_the_scan_count_is_not_called_available(tmp_path: Path) -> None:
    """#124: a tail quoted as a population is how a floor becomes a total."""
    _write_log(tmp_path, _rows())
    result = events_list(city_reader(tmp_path))
    assert "available_in_scan" in result
    assert "available" not in result


def test_a_partial_first_line_is_discarded_not_parsed(tmp_path: Path) -> None:
    """Seeking into the middle of the file lands mid-object."""
    _write_log(tmp_path, _rows())
    result = events_list(city_reader(tmp_path, tail_bytes=150))
    assert result["scan"]["malformed_lines"] == 0
    for row in result["events"]:
        assert "type" in row


def test_one_malformed_line_is_not_a_dead_log(tmp_path: Path) -> None:
    log = tmp_path / ".gc" / "events.jsonl"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(
        json.dumps({"ts": "2026-08-29T01:00:00", "type": "bead.closed", "subject": "a"}) + "\n"
        + "{not json at all\n"
        + json.dumps({"ts": "2026-08-29T02:00:00", "type": "bead.closed", "subject": "b"}) + "\n",
        encoding="utf-8",
    )
    result = events_list(city_reader(tmp_path))
    assert result["state"] == "healthy"
    assert {r["subject"] for r in result["events"]} == {"a", "b"}
    assert result["scan"]["malformed_lines"] == 1


# --- the name collision that cost 102 collection errors ---------------------


def test_the_write_helper_module_is_untouched() -> None:
    """`mctl_core/events.py` is the trace WRITE helper `trace.py` imports.

    Taking that name for this reader shadowed it and broke every import in the
    package. Pinned so the next author does not rediscover it.
    """
    from mctl_core import events as write_helper

    assert hasattr(write_helper, "append_jsonl")
    assert not hasattr(write_helper, "events_list")
