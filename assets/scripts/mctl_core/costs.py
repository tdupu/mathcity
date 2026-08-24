"""Costs as a typed read: token bucketing + the meta-work ratio (#118).

WHAT THIS ANSWERS. Not "what did this city spend in dollars" -- `gc costs`
already prints that as a list-price estimate, and a list price is not an
authoritative charge (see its own `--help`). This answers "is the city
spending its own tokens on itself" -- the meta-work ratio, city/meta effort
vs mathematics effort -- because that ratio climbing over months means the
machine is consuming its own output, and that trend is invisible in a
per-run cost table.

UNIT IS TOKENS, NEVER BEAD COUNT. A one-line fix and a month of research both
count as "1" if the unit is beads. `total_tokens` sums
input+output+cache_read+cache_creation across model facts; `worker_hours`
(compute wall-seconds / 3600) rides beside it as the companion measure.

DATA SOURCE IS THE LOCAL USAGE LOG, NOT A `gc costs` SUBPROCESS. `gc costs`
(cmd/gc/cmd_costs.go) does exactly one thing this module needs: it reads
`<city-root>/.gc/usage.jsonl` and aggregates by run. But it declares no JSON
output (`gc costs --json-schema result` reports
`json_schema_unavailable: command "costs" does not declare JSON support`),
so a subprocess reader would mean parsing a tabwriter table -- strictly
worse than reading the same file this module already needs to read for
per-window bucketing and rig classification, which `gc costs`'s per-run
grouping does not do at all. So `city_reader` reads `.gc/usage.jsonl`
directly, exactly as `mctl_core.orders.city_reader` reads
`.gc/events.jsonl` directly rather than shelling to a slow `gc` subcommand.

RIG CLASSIFICATION HAS A REAL, DOCUMENTED GAP. A usage fact
(`internal/usage.Fact` in gascity) carries no `rig` field -- only `worker`,
the tmux-safe session name. A rig-qualified session name is sanitized as
`<rig>/<agent>` -> `<rig>--<agent>` (`/` -> `--`, `.` -> `__`;
`internal/agent/session_name.go`), so `_rig_from_worker` reverses that
encoding and takes the leading segment. A singleton session (no `/` in its
qualified name -- a manual chat, or an agent that is not rig-scoped) cannot
be attributed this way. Rather than guess, such a fact -- and any fact whose
recovered rig matches neither the meta list nor the math list -- lands in
`unclassified_tokens`, its own bucket, WITH an informational diagnostic
naming the gap (`MCOS_RIG_UNRESOLVED`). Folding it into either side would
fabricate the ratio; hiding it would understate how much spend this module
cannot yet attribute. This is the honestly-unknown dimension of #118: real
production usage.jsonl data may put a meaningful fraction of tokens in
`unclassified` until a `rig` field is added at the emitter (`internal/worker`
and `cmd/gc/usage_compute.go` in gascity) -- a fact for a future issue, not
this module's job to paper over.

THREE-VALUED, NOT BOOLEAN. A usage-log read that fails reports
`state="unreachable"` with `total_tokens=None` (never `0`) -- "we could not
look" and "there was no usage" are different facts. `windows` is `None`
on that path too, never `[]`.

`unpriced_count` IS THE EXPLICIT CHANNEL for "ran but price unknown" -- a run
with no pricing entry is counted here, never valued at `$0` and never
silently dropped from `total_tokens` (tokens were still spent; only the
dollar estimate is unknown).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from .diagnostics import Diagnostic, Severity

MCOS_USAGE_UNREACHABLE = "MCOS_USAGE_UNREACHABLE"
MCOS_RIG_UNRESOLVED = "MCOS_RIG_UNRESOLVED"

#: Rig-name prefixes that count as "the city working on itself". Matched with
#: `str.startswith`, per #118's brief ("RIG PREFIX already decides the
#: side") -- `gascity-packs` and `gascity` share a side, so prefix overlap
#: between them is harmless.
META_RIG_PREFIXES: tuple[str, ...] = ("gascity-packs", "gascity", "mathcity")

#: Rig-name prefixes that count as "the city working on mathematics".
#: `magma_` is deliberately a prefix (`magma_general`, `magma_hecke_...`),
#: matching the brief's own `magma_*` notation.
MATH_RIG_PREFIXES: tuple[str, ...] = (
    "hecke",
    "differential_valuations",
    "magma_",
    "lmfdb",
    "jacobi",
    "homog",
)

#: The bucket for a rig matching neither list above, and for a worker whose
#: rig cannot be recovered at all. A third, explicit bucket -- never silently
#: folded into either side, which would fabricate the ratio.
UNCLASSIFIED = "unclassified"

_WINDOW_UNKNOWN = "unknown"


def classify_rig(rig: str | None) -> str:
    """`"meta"`, `"math"`, or `UNCLASSIFIED` -- never guessed past what the
    prefix lists actually say."""
    if not rig:
        return UNCLASSIFIED
    for prefix in META_RIG_PREFIXES:
        if rig.startswith(prefix):
            return "meta"
    for prefix in MATH_RIG_PREFIXES:
        if rig.startswith(prefix):
            return "math"
    return UNCLASSIFIED


def _rig_from_worker(worker: Any) -> str | None:
    """Best-effort recovery of the originating rig from a sanitized session
    name. `None` when the worker is blank or carries no `rig/agent`
    structure -- a fact this module must not guess past (see module
    docstring's "RIG CLASSIFICATION HAS A REAL, DOCUMENTED GAP")."""
    text = str(worker or "").strip()
    if not text:
        return None
    unsanitized = text.replace("--", "/").replace("__", ".")
    if "/" not in unsanitized:
        return None
    rig = unsanitized.split("/", 1)[0].strip()
    return rig or None


def _window_key(at_millis: Any) -> str:
    """A UTC calendar-day bucket. `_WINDOW_UNKNOWN` when the fact carries no
    usable timestamp -- the fact is still counted in the totals, just not
    placeable on the trend."""
    if not at_millis:
        return _WINDOW_UNKNOWN
    try:
        moment = datetime.fromtimestamp(float(at_millis) / 1000.0, tz=timezone.utc)
    except (OverflowError, OSError, TypeError, ValueError):
        return _WINDOW_UNKNOWN
    return moment.strftime("%Y-%m-%d")


def _ratio(numerator: int, denominator: int) -> float | None:
    """`None` when the denominator is zero -- never a division by zero, and
    never a fabricated ratio when there is no math-side spend to compare
    against."""
    if not denominator:
        return None
    return numerator / denominator


def _empty_window(window: str) -> dict[str, Any]:
    return {
        "window": window,
        "total_tokens": 0,
        "meta_tokens": 0,
        "math_tokens": 0,
        "unclassified_tokens": 0,
        "worker_hours": 0.0,
        "unpriced_count": 0,
        "meta_work_ratio": None,
    }


def _unreachable(err: Exception) -> dict[str, Any]:
    """The usage-log read could not run. Every total is `None`, never `0`."""
    return {
        "state": "unreachable",
        "total_tokens": None,
        "worker_hours": None,
        "unpriced_count": None,
        "unclassified_tokens": None,
        "meta_work_ratio": {"numerator": None, "denominator": None, "ratio": None},
        "windows": None,
        "diagnostics": [
            Diagnostic(
                Severity.WARN,
                MCOS_USAGE_UNREACHABLE,
                f"usage facts unavailable: {err}",
            ).to_dict()
        ],
    }


def _token_count(fact: Mapping[str, Any]) -> int:
    return (
        int(fact.get("input_tokens") or 0)
        + int(fact.get("output_tokens") or 0)
        + int(fact.get("cache_read_tokens") or 0)
        + int(fact.get("cache_creation_tokens") or 0)
    )


def costs_summary(read: Callable[[str], Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Token totals + worker-hours + the meta-work ratio, bucketed by window.

    `now` is accepted for parity with `queue_status`'s injection style and
    future use (e.g. bounding the window range); it is not consulted today --
    every fact read is bucketed, not just a recent slice.
    """
    del now  # reserved; see docstring

    try:
        facts = list(read("usage_facts") or [])
    except Exception as err:  # noqa: BLE001 -- any read failure is "we could not look"
        return _unreachable(err)

    windows: dict[str, dict[str, Any]] = {}
    total_tokens = 0
    unpriced_count = 0
    worker_hours = 0.0
    meta_tokens = 0
    math_tokens = 0
    unclassified_tokens = 0

    for fact in facts:
        if not isinstance(fact, Mapping):
            continue
        window_key = _window_key(fact.get("at"))
        bucket = windows.setdefault(window_key, _empty_window(window_key))
        kind = fact.get("kind")

        if kind == "model":
            tokens = _token_count(fact)
            total_tokens += tokens
            bucket["total_tokens"] += tokens

            side = classify_rig(_rig_from_worker(fact.get("worker")))
            if side == "meta":
                meta_tokens += tokens
                bucket["meta_tokens"] += tokens
            elif side == "math":
                math_tokens += tokens
                bucket["math_tokens"] += tokens
            else:
                unclassified_tokens += tokens
                bucket["unclassified_tokens"] += tokens

            if fact.get("unpriced"):
                unpriced_count += 1
                bucket["unpriced_count"] += 1
        elif kind == "compute":
            hours = float(fact.get("wall_seconds") or 0.0) / 3600.0
            worker_hours += hours
            bucket["worker_hours"] += hours

    ordered_windows = [windows[key] for key in sorted(windows)]
    for bucket in ordered_windows:
        bucket["meta_work_ratio"] = _ratio(bucket["meta_tokens"], bucket["math_tokens"])

    diagnostics: list[dict[str, Any]] = []
    if unclassified_tokens:
        diagnostics.append(
            Diagnostic(
                Severity.INFO,
                MCOS_RIG_UNRESOLVED,
                f"{unclassified_tokens} token(s) could not be attributed to a rig on either "
                "side of the meta-work ratio -- the rig matched neither the meta nor the math "
                "prefix list, or the recording worker's session name carried no `rig/agent` "
                "structure to recover a rig from at all.",
            ).to_dict()
        )

    return {
        "state": "healthy",
        "total_tokens": total_tokens,
        "worker_hours": worker_hours,
        "unpriced_count": unpriced_count,
        "unclassified_tokens": unclassified_tokens,
        "meta_work_ratio": {
            "numerator": meta_tokens,
            "denominator": math_tokens,
            "ratio": _ratio(meta_tokens, math_tokens),
        },
        "windows": ordered_windows,
        "diagnostics": diagnostics,
    }


def city_reader(city_root) -> Callable[[str], Any]:
    """A reader over the live city's local usage log, for the typed tool.

    `.gc/usage.jsonl` is a local file, milliseconds to read -- exactly the
    same asymmetry `mctl_core.orders.city_reader` documents for
    `.gc/events.jsonl` vs `gc order list`. `gc costs` reads the identical
    file and declares no JSON output, so shelling to it would mean parsing a
    tabwriter table for data this reader already has typed.

    Raises rather than returning a default, so `costs_summary` turns a
    missing or unreadable log into `state="unreachable"` -- never into a
    silent zero.
    """
    import json
    from pathlib import Path as _Path

    def read(what: str) -> Any:
        if what == "usage_facts":
            path = _Path(city_root) / ".gc" / "usage.jsonl"
            if not path.is_file():
                raise FileNotFoundError(f"no usage log at {path}")
            out: list[dict[str, Any]] = []
            with path.open(errors="replace") as handle:
                for line in handle:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                    except ValueError:
                        continue  # one malformed line is not a dead log
                    if isinstance(record, dict):
                        out.append(record)
            return out
        raise KeyError(what)

    return read
