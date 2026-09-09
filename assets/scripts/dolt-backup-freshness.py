#!/usr/bin/env python3
"""Fail loudly when a canonical dolt backup has gone stale (#79).

#79 measured canonical remotes 9-36 days behind stores that were being actively
written, with 5 of 6 reporting SUCCESS and writing nothing. A backup that lies
is worse than no backup: it is the one you do not check.

RE-MEASURED 2026-09-09 -- the condition has DEGRADED, not decayed:

    gascity-HQ-dolt       56 days   (36 when #79 was filed)
    gascity-packs-dolt    44 days
    gascity-dolt           2 days
    hecke-dolt             1 day
    mathcity-dolt          0 days

`hq` is the store #79 records as holding pre-compaction lineage that exists
nowhere else.

STALENESS IS RELATIVE TO LOCAL WRITES, not to the calendar. A store nobody has
written in three months does not need a push from yesterday, and failing on it
trains people to ignore the check. The condition that matters is ACTIVELY
WRITTEN BUT NOT BACKED UP, so --store compares the local store's newest write
against the remote's last push. Without --store the tool reports calendar age
and says so, rather than implying it measured something it did not.

Exit codes (P6.2):

    0  every remote checked is fresh (or nothing was checkable, said out loud)
    1  at least one backup is stale -- each named with both ages
    2  the remote could not be queried at all: NOT the same as "fresh"
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parent))
from mctl_limits import resolve as _resolve_limit  # noqa: E402

DEFAULT_MAX_LAG_DAYS = 3


def remote_pushed_at(repo: str, timeout: int) -> dt.datetime:
    proc = subprocess.run(
        ["gh", "api", f"repos/{repo}", "--jq", ".pushed_at"],
        capture_output=True, text=True, timeout=timeout,
    )
    if proc.returncode != 0 or not proc.stdout.strip():
        raise RuntimeError((proc.stderr or proc.stdout).strip()[:200] or "empty response")
    return dt.datetime.fromisoformat(proc.stdout.strip().replace("Z", "+00:00"))


def local_newest_write(path: str) -> dt.datetime | None:
    """Newest mtime under the store, as a proxy for 'was it written'.

    Deliberately NOT `dolt log`: that needs a running sql-server, and the whole
    point of this check is to work when the server is unhealthy -- which is
    exactly when backups are most likely to be silently failing. An mtime proxy
    can be fooled, so a stale finding names it as a proxy rather than asserting
    a commit time it did not read.
    """
    newest = None
    for root, dirs, files in os.walk(path):
        # `noms` holds the chunk store and dominates the walk; its mtime moves
        # with any write, which is all this needs.
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for name in files:
            try:
                stamp = os.stat(os.path.join(root, name)).st_mtime
            except OSError:
                continue
            if newest is None or stamp > newest:
                newest = stamp
    if newest is None:
        return None
    return dt.datetime.fromtimestamp(newest, dt.timezone.utc)


def main() -> int:
    ap = argparse.ArgumentParser(description="dolt backup freshness")
    ap.add_argument("--remote", action="append", required=True, metavar="OWNER/REPO",
                    help="backup remote to check; repeatable. Optionally "
                         "OWNER/REPO=/path/to/local/store to compare against "
                         "local writes rather than the calendar.")
    ap.add_argument("--max-lag-days", type=int, default=DEFAULT_MAX_LAG_DAYS)
    ap.add_argument("--timeout", type=int, default=None,
                    help="seconds; 0 = no deadline. Default comes from assets/mctl/limits.toml [remote_query_seconds], overridable with $MATHCITY_REMOTE_QUERY_SECONDS.")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    # POLICY, not a baked-in constant (owner, 2026-09-09). See
    # assets/mctl/limits.toml. `--timeout 0` means NO deadline.
    args.timeout, _timeout_source = _resolve_limit("remote_query_seconds", args.timeout)
    if _timeout_source == "fallback":
        print("NOTE: assets/mctl/limits.toml unreadable; using the built-in "
              f"fallback of {args.timeout}s for this run", file=sys.stderr)

    now = dt.datetime.now(dt.timezone.utc)
    rows, stale, unreachable = [], [], []

    for spec in args.remote:
        repo, _, store = spec.partition("=")
        row: dict[str, object] = {"remote": repo, "store": store or None}
        try:
            pushed = remote_pushed_at(repo, args.timeout)
        except Exception as exc:
            row["error"] = str(exc)
            unreachable.append(row)
            rows.append(row)
            continue

        remote_age = (now - pushed).days
        row["remote_pushed_at"] = pushed.isoformat()
        row["remote_age_days"] = remote_age

        if store and os.path.isdir(os.path.expanduser(store)):
            local = local_newest_write(os.path.expanduser(store))
            if local is not None:
                lag = (local - pushed).days
                row["local_newest_write"] = local.isoformat()
                row["local_ahead_of_backup_days"] = lag
                row["basis"] = "local-vs-remote (mtime proxy)"
                if lag > args.max_lag_days:
                    row["verdict"] = "STALE"
                    stale.append(row)
                else:
                    row["verdict"] = "fresh"
                rows.append(row)
                continue
            row["local_newest_write"] = None

        # No usable local side: report calendar age and SAY that is what it is.
        row["basis"] = "calendar age only (no --store given or store unreadable)"
        if remote_age > args.max_lag_days:
            row["verdict"] = "STALE"
            stale.append(row)
        else:
            row["verdict"] = "fresh"
        rows.append(row)

    if args.json:
        print(json.dumps({"max_lag_days": args.max_lag_days, "remotes": rows},
                         indent=2, sort_keys=True))
    else:
        for row in rows:
            if "error" in row:
                print(f"  {row['remote']:<28} UNREACHABLE -- {row['error']}")
                continue
            extra = ""
            if row.get("local_ahead_of_backup_days") is not None:
                extra = f", local {row['local_ahead_of_backup_days']}d ahead"
            print(f"  {row['remote']:<28} {str(row['verdict']):<6} "
                  f"remote {row['remote_age_days']}d old{extra}")
        if stale:
            print(f"\nBACKUP_FRESHNESS: {len(stale)} backup(s) STALE "
                  f"(> {args.max_lag_days}d). A dolt push that reports success "
                  f"and writes nothing leaves exactly this trace (#79).")
        elif not unreachable:
            print("\nBACKUP_FRESHNESS: OK -- every backup checked is current.")

    if unreachable:
        print(f"BACKUP_FRESHNESS: {len(unreachable)} remote(s) could not be "
              f"queried -- that is NOT 'fresh'.", file=sys.stderr)
        return 2
    return 1 if stale else 0


if __name__ == "__main__":
    raise SystemExit(main())
