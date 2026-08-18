#!/usr/bin/env python3
"""Entry point for the MathCity command-line tool."""
from __future__ import annotations

import sys
from pathlib import Path


SCRIPTS_ROOT = Path(__file__).resolve().parent
if str(SCRIPTS_ROOT) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_ROOT))

from mctl_core.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
