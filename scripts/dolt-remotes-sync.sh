#!/bin/sh
# dolt-remotes-sync.sh — standalone dolt remote sync for all city databases.
#
# Replaces the dolt-remotes-patrol exec-order (which had a hardcoded 300s
# gc exec-order timeout — less than the actual sync budget for 15+ databases).
#
# Designed to be launched by supervisor/launchd on a fixed interval.
# Recommended interval: T = num_dbs × avg_sync_time_per_db × safety_factor
#   Example: 15 dbs × 30s/db × 1.5 = 675s → 720s (12 min)
#
# No timeout constraint here — the script runs gc dolt sync to completion.
# If a run is still in progress when the next interval fires, launchd
# StartInterval semantics mean the next run is simply skipped until the
# current one exits (use ThrottleInterval in the plist to enforce this).
#
# Usage: called by launchd; no arguments expected.
# Logs to stdout/stderr (captured by launchd StandardOutPath/StandardErrorPath).

set -eu

# GC_HOME must be set (inherited from launchd EnvironmentVariables, same as
# the supervisor plist).
: "${GC_HOME:?GC_HOME must be set}"

CITY_PATH="${GC_CITY_PATH:-${HOME}/gt}"

START_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "[dolt-remotes-sync] START ${START_TS}"

if ! gc dolt sync --city "${CITY_PATH}"; then
    END_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    echo "[dolt-remotes-sync] FAILED at ${END_TS}"
    exit 1
fi

END_TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "[dolt-remotes-sync] DONE  ${END_TS} (started ${START_TS})"
