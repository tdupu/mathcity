#!/usr/bin/env sh
# Read-only fixture packaging checks; no models, network, or semantic claims.
set -eu

fixture_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
    printf '%s\n' 'Missing Python 3: required for fixture packaging checks.' >&2
    exit 1
fi
exec python3 -B "$fixture_dir/fixture.py" check
