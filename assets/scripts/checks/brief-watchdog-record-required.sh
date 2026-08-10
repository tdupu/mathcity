#!/bin/sh
exec "$(dirname "$0")/brief-check.sh" watchdog-record "$@"

