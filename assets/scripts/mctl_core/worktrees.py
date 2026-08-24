"""Worktree inventory: enumeration, and an honest account of what is not yet
recorded (#120).

WHAT THIS ANSWERS. The dashboard has Orders, Formulas, Molecules, a Queue, and
Costs -- and no inventory of the git worktrees the city's own agents create and
(sometimes) abandon. This module is that inventory: one row per worktree, keyed
by PATH.

ROW KEY IS THE PATH, NEVER THE ID. Measured 2026-08-20 (#120 brief): two ids
appear twice with different parents across the registered rigs. An id-keyed
table would silently collapse two distinct worktrees into one row.

WHERE ROWS COME FROM. `git worktree list --porcelain`, run once per registered
rig (`CityScope.rigs`), because worktree metadata lives in the PRIMARY
worktree's `.git` directory and a single call from any worktree of that repo
already lists every worktree of it -- primary and linked. THREE-VALUED: if the
city's rig roster itself cannot be read, `state="unreachable"` and `worktrees`
is `null`, never `[]`. If every registered rig's `git worktree list` call
fails, that is the same fact for a different reason and reports the same way.
A rig whose read fails while others succeed degrades that ONE rig (a named
`MWKT_RIG_UNREACHABLE` diagnostic) without discarding the rows a working rig
already produced -- exactly `queue_status`'s per-population degradation
(`mctl_core/queue.py`), applied per rig instead of per population.

SAFETY FREEZE (#120 brief). The live orphans under `~/gt/hecke/` (14
directories, ~119.7 GB, measured 2026-08-20) have ZERO overlap with
`git worktree list` -- they are not entries in any repository's worktree
registry. Because this module's ONLY discovery mechanism is
`git worktree list --porcelain`, those directories are structurally
UNREACHABLE from this tool: it never enumerates them, never sizes them, never
touches them. That is not a mitigation this module applies -- it is a
consequence of what `git worktree list` does and does not know about, and it
is also why `is_registered` reads `True` for every row this version produces
(next paragraph).

HONESTY GAP #1 -- `is_registered` IS ALWAYS `True` TODAY, AND THAT IS A KNOWN
LIMIT, NOT A COMPUTED FACT. The brief distinguishes `is_registered` ("git
still knows it") from `is_orphan` ("no live session, no open bead") as two
SEPARATE flags. Because this module's only row source IS `git worktree list`,
every row it can produce is, by construction, one `git` still lists -- there is
no second, independent registry (a bead-linked "expected worktree" ledger, for
instance) to cross-check against. A worktree git has forgotten but whose
directory still exists (like the frozen orphans above) would be exactly the
interesting `is_registered=False` row, and this version cannot produce it. If
such a registry is ever built, `is_registered` becomes a real per-row
computation instead of a constant; until then it stays `True` and this
docstring says so rather than presenting a constant as a measurement.

HONESTY GAP #2 -- `is_orphan` IS ALWAYS `null` TODAY. The brief's definition is
"no live session, no open bead" -- both halves require a join this city does
not yet have. Measured against `mctl_core/fleet.py::build_fleet_sessions`:
`gc session list --json` sessions carry `agent_name`/`rig`/`template`/`state`/
`id`/`provider`/`last_active`, and NO working-directory or worktree-path field
-- there is no key to join a worktree path to a live session by. And no code
anywhere in this rig (measured: `git grep -n worktree` before this module
existed returns nothing) records which bead, if any, a worktree was created
for -- `created_by`/`step` are exactly this same absence (Gap #3). Guessing
either join from naming conventions (branch names such as `w156` do suggest a
bead) would be exactly the kind of fabricated fact #118's `costs.py` and
#113's `queue.py` both refused to produce for their own real gaps; this module
follows that precedent and reports `is_orphan=null` with the
`MWKT_ORPHAN_UNDERIVABLE` diagnostic naming the missing join, rather than
guess. `orphans` (the row-count summary) is `null` for the same reason -- a
count of an undeterminable flag is not zero.

HONESTY GAP #3 -- `created_by` / `step` / `molecule` ARE UNRECORDED, NOT
UNKNOWN, AND THE SCHEMA SAYS SO WITH A DISTINCT VALUE. Nothing records these
at worktree-creation time today, so EVERY row carries the literal string
`UNRECORDED` (never Python/JSON `null`, which this codebase reserves for "we
tried to read this and could not" -- see the module docstrings of
`orders.py`/`queue.py`/`costs.py`). `UNRECORDED` must never collide with a
genuine future value: a worktree created by nobody in particular would record
an EMPTY STRING (`""`), which is a real, distinct value from the sentinel.
This mirrors `orders.py`'s `UNKNOWN_OUTCOME = "unknown"` -- a typed sentinel
for "the log has never seen this", not a stand-in for read failure.

`harvestable` IS A REAL, COMPUTED SIGNAL. `git worktree list --porcelain`
itself reports `prunable <reason>` when the worktree's directory is gone but
the administrative entry remains -- a fact git computes, not a guess this
module makes. `harvestable` is exactly that flag, `True` only when git itself
says so.

`merged` / `commits` ARE REAL, COMPUTED SIGNALS. Both are read relative to the
RIG'S PRIMARY WORKTREE'S branch (the first entry `git worktree list` reports
for that rig -- there is no other "default branch" this module can name
without guessing at a remote's HEAD, which may not exist offline). `merged`
is `git merge-base --is-ancestor <branch> <primary-branch>`; `commits` is
`git rev-list --count <primary-branch>..<branch>`. Both are `null` for a
detached/bare worktree (no branch to compare) and `null` if the git call
itself fails.

`size` IS BEST-EFFORT AND NEVER BLOCKS THE READ. `du -sk` on a worktree's own
path -- always a `git`-registered, non-frozen path per the Safety Freeze
section above. A `du` failure or timeout reports `size_bytes=null` for that
row alone (with one aggregate `MWKT_SIZE_UNKNOWN` diagnostic, not one per
row), never a fabricated size and never a read failure for the whole tool.

THREE-VALUED, NOT BOOLEAN. A rig-roster read that fails reports
`state="unreachable"` with `total=None` and `worktrees=None`. If every
registered rig's own worktree-list call fails, the same three values are
reported for the same reason -- "we could not look at any rig" is not "there
are no worktrees".
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from .diagnostics import Diagnostic, Severity

MWKT_WORKTREES_UNREACHABLE = "MWKT_WORKTREES_UNREACHABLE"
MWKT_RIG_UNREACHABLE = "MWKT_RIG_UNREACHABLE"
MWKT_SIZE_UNKNOWN = "MWKT_SIZE_UNKNOWN"
MWKT_ORPHAN_UNDERIVABLE = "MWKT_ORPHAN_UNDERIVABLE"
MWKT_CREATED_BY_UNRECORDED = "MWKT_CREATED_BY_UNRECORDED"

#: Reserved sentinel for "nothing records this field today" -- distinct from a
#: genuinely empty recorded value (`""`) and distinct from `null` (three-valued
#: "we could not read this"). See module docstring, Honesty Gap #3.
UNRECORDED = "unrecorded"


def _unreachable(err: Exception) -> dict[str, Any]:
    """The rig roster itself could not be read. Every count is `None`, the
    row list is `None` -- never `[]`, and never a report about zero rigs."""
    return {
        "state": "unreachable",
        "total": None,
        "worktrees": None,
        "orphans": None,
        "harvestable_count": None,
        "diagnostics": [
            Diagnostic(
                Severity.WARN,
                MWKT_WORKTREES_UNREACHABLE,
                f"rig roster unavailable: {err}",
                facts={"suggested_next_command": "gc rig list --json"},
            ).to_dict()
        ],
    }


def _rig_name(rig: Any) -> str | None:
    if isinstance(rig, Mapping):
        return rig.get("name")
    return getattr(rig, "name", None)


def _rig_root(rig: Any) -> Any:
    if isinstance(rig, Mapping):
        return rig.get("root")
    return getattr(rig, "root", None)


def _age_seconds(committed_at: Any, now: datetime) -> float | None:
    if not committed_at:
        return None
    try:
        stamp = datetime.fromisoformat(str(committed_at).replace("Z", "+00:00"))
    except ValueError:
        return None
    return (now - stamp).total_seconds()


def _shape_row(rig_name: str | None, raw: Mapping[str, Any], now: datetime) -> dict[str, Any]:
    path = raw.get("path")
    return {
        "path": path,
        "rig": rig_name,
        "branch": raw.get("branch"),
        # Honesty Gap #3 -- nothing records these today; UNRECORDED is a typed
        # sentinel, never Python/JSON null and never a guess.
        "molecule": UNRECORDED,
        "created_by": UNRECORDED,
        "step": UNRECORDED,
        "merged": raw.get("merged"),
        "age_seconds": _age_seconds(raw.get("committed_at"), now),
        "size_bytes": raw.get("size_bytes"),
        # Honesty Gap #2 -- undeterminable with today's data; see module
        # docstring and MWKT_ORPHAN_UNDERIVABLE.
        "is_orphan": None,
        # Honesty Gap #1 -- always True by construction; see module
        # docstring. Not a computed per-row fact yet.
        "is_registered": True,
        "harvestable": bool(raw.get("prunable_reason")),
        "commits": raw.get("commits_ahead"),
        "url": f"file://{path}" if path else None,
    }


def worktrees_status(read: Callable[..., Any], *, now: datetime | None = None) -> dict[str, Any]:
    """Every worktree across every registered rig, keyed by path (#120)."""
    now = now or datetime.now(timezone.utc)

    try:
        rigs = list(read("rigs"))
    except Exception as err:  # noqa: BLE001 -- any read failure is "we could not look"
        return _unreachable(err)

    diagnostics: list[dict[str, Any]] = []
    rows: list[dict[str, Any]] = []
    attempted = 0
    failed = 0
    any_size_unknown = False

    for rig in rigs:
        attempted += 1
        name = _rig_name(rig)
        root = _rig_root(rig)
        try:
            raw_rows = list(read("worktree_rows", name, root))
        except Exception as err:  # noqa: BLE001
            failed += 1
            diagnostics.append(
                Diagnostic(
                    Severity.WARN,
                    MWKT_RIG_UNREACHABLE,
                    f"git worktree list unavailable for rig {name}: {err}",
                    facts={
                        "rig_name": str(name) if name else "",
                        "suggested_next_command": "git -C <rig_root> worktree list --porcelain",
                    },
                ).to_dict()
            )
            continue
        for raw in raw_rows:
            if raw.get("size_bytes") is None:
                any_size_unknown = True
            rows.append(_shape_row(name, raw, now))

    if attempted and failed == attempted:
        # Every rig we tried to read failed -- we could not look at any
        # worktree, which is a different fact than "there are none".
        return {
            "state": "unreachable",
            "total": None,
            "worktrees": None,
            "orphans": None,
            "harvestable_count": None,
            "diagnostics": diagnostics,
        }

    if rows:
        if any_size_unknown:
            diagnostics.append(
                Diagnostic(
                    Severity.INFO,
                    MWKT_SIZE_UNKNOWN,
                    "One or more worktrees could not be sized (`du` failed or timed out); "
                    "those rows report size_bytes=null, never a fabricated size.",
                ).to_dict()
            )
        diagnostics.append(
            Diagnostic(
                Severity.INFO,
                MWKT_ORPHAN_UNDERIVABLE,
                "is_orphan is null for every row: `gc session list` carries no "
                "working-directory field to join a worktree path to a live session by, "
                "and no bead metadata records which worktree it owns. orphans is null for "
                "the same reason -- a count of an undeterminable flag is not zero.",
            ).to_dict()
        )
        diagnostics.append(
            Diagnostic(
                Severity.INFO,
                MWKT_CREATED_BY_UNRECORDED,
                "created_by/step/molecule are 'unrecorded' for every row: nothing records "
                "them at worktree-creation time today. The field exists so a future writer "
                "can populate it; 'unrecorded' is a typed sentinel, distinct from a real "
                "empty owner and from a read failure.",
            ).to_dict()
        )

    return {
        "state": "degraded" if failed else "healthy",
        "total": len(rows),
        "worktrees": rows,
        "orphans": None,
        "harvestable_count": sum(1 for r in rows if r["harvestable"]),
        "diagnostics": diagnostics,
    }


def city_reader(scope) -> Callable[..., Any]:
    """A reader over the live city's registered rigs, for the typed tool.

    Every branch raises rather than returning a default for the operation it
    covers -- `worktrees_status` turns a rig-roster failure into
    `state="unreachable"` and a single rig's failure into a named, per-rig
    diagnostic that does not discard the rows other rigs produced.
    """
    import subprocess
    from pathlib import Path as _Path

    def _git(root: Any, args: list[str], *, timeout: float = 15.0) -> str:
        proc = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"git {' '.join(args)} exited {proc.returncode}: {proc.stderr.strip()}")
        return proc.stdout

    def _parse_porcelain(text: str) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        current: dict[str, Any] = {}
        for line in text.splitlines():
            if not line.strip():
                if current:
                    entries.append(current)
                    current = {}
                continue
            if line.startswith("worktree "):
                current["path"] = line[len("worktree "):].strip()
            elif line.startswith("HEAD "):
                current["head"] = line[len("HEAD "):].strip()
            elif line.startswith("branch "):
                ref = line[len("branch "):].strip()
                current["branch"] = ref[len("refs/heads/"):] if ref.startswith("refs/heads/") else ref
            elif line == "bare":
                current["bare"] = True
            elif line == "detached":
                current["detached"] = True
            elif line.startswith("locked"):
                current["locked_reason"] = line[len("locked"):].strip() or "locked"
            elif line.startswith("prunable"):
                current["prunable_reason"] = line[len("prunable"):].strip() or "prunable"
        if current:
            entries.append(current)
        return entries

    def _size_bytes(path: str) -> int | None:
        try:
            proc = subprocess.run(
                ["du", "-sk", path], capture_output=True, text=True, timeout=20.0
            )
        except (OSError, subprocess.TimeoutExpired):
            return None
        if proc.returncode != 0:
            return None
        try:
            return int(proc.stdout.split()[0]) * 1024
        except (IndexError, ValueError):
            return None

    def read(op: str, *args: Any) -> Any:
        if op == "rigs":
            return [{"name": rig.name, "root": rig.root} for rig in scope.rigs]
        if op == "worktree_rows":
            _rig_name_arg, root = args
            text = _git(root, ["worktree", "list", "--porcelain"])
            entries = _parse_porcelain(text)
            primary_branch = entries[0].get("branch") if entries else None
            rows: list[dict[str, Any]] = []
            for entry in entries:
                branch = entry.get("branch")
                head = entry.get("head")
                committed_at = None
                if head:
                    try:
                        committed_at = _git(root, ["log", "-1", "--format=%cI", head]).strip() or None
                    except Exception:  # noqa: BLE001 -- age is best-effort, never fatal
                        committed_at = None
                merged: bool | None = None
                commits_ahead: int | None = None
                if branch and primary_branch:
                    if branch == primary_branch:
                        merged, commits_ahead = True, 0
                    else:
                        try:
                            rc = subprocess.run(
                                ["git", "-C", str(root), "merge-base", "--is-ancestor", branch, primary_branch],
                                capture_output=True,
                                timeout=15.0,
                            )
                            merged = rc.returncode == 0
                        except (OSError, subprocess.TimeoutExpired):
                            merged = None
                        try:
                            out = _git(root, ["rev-list", "--count", f"{primary_branch}..{branch}"])
                            commits_ahead = int(out.strip())
                        except Exception:  # noqa: BLE001 -- best-effort, never fatal
                            commits_ahead = None
                rows.append(
                    {
                        "path": entry.get("path"),
                        "branch": branch,
                        "head": head,
                        "bare": entry.get("bare", False),
                        "detached": entry.get("detached", False),
                        "locked_reason": entry.get("locked_reason"),
                        "prunable_reason": entry.get("prunable_reason"),
                        "committed_at": committed_at,
                        "merged": merged,
                        "commits_ahead": commits_ahead,
                        "size_bytes": _size_bytes(entry.get("path")) if entry.get("path") else None,
                    }
                )
            return rows
        raise KeyError(op)

    return read
