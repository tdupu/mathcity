"""Shared core for the MathCity command-line tool."""

from .context import ContextError, MctlContext, resolve_context
from .diagnostics import Diagnostic, Severity

__all__ = [
    "ContextError",
    "Diagnostic",
    "MctlContext",
    "Severity",
    "resolve_context",
]
