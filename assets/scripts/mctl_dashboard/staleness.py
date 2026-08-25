"""What commit is this process actually serving, and is it behind the checkout?

`#164`. The dashboard is a long-running process that loaded its Python once.
Nothing about that is wrong; what was wrong is that the page could not say so.
Taylor's server ran seven hours stale across four merges, rendering
merged-and-absent features identically to never-built ones — and three times in
one day a human had to notice and bounce it.

This does not restart anything. Restarting is a decision with an owner and a
blast radius. **Saying what you are serving is not**, and an operator who can
see "14 commits behind" can act, where one who cannot is being quietly
misinformed by a page that looks current.

P6.2 governs the check itself: when the comparison cannot be made, the banner
says the age is **unknown**. A staleness check that renders "up to date" from a
check that did not run would be this module's own defect, one level up.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import subprocess

from .render import esc as _e

#: Kept short: this runs per page render, and a slow answer would be paid on
#: every view. A checkout that cannot answer in this budget reports unknown,
#: which is a true statement, rather than delaying the page.
HEAD_READ_TIMEOUT_SECONDS = 2.0


@dataclass(frozen=True)
class Staleness:
    served: str | None
    current: str | None

    @property
    def is_known(self) -> bool:
        """Whether the comparison could be made at all."""
        return bool(self.served) and bool(self.current)

    @property
    def is_stale(self) -> bool:
        """True only when we KNOW the process is behind.

        False here is not a claim of freshness -- read `is_known` first. That
        separation is the whole point: an unknown answer must not be able to
        masquerade as a good one.
        """
        return self.is_known and self.served != self.current


def compare(*, served: str | None, current: str | None) -> Staleness:
    return Staleness(served=served, current=current)


def read_head(repo: Path, *, timeout: float = HEAD_READ_TIMEOUT_SECONDS) -> str | None:
    """The checkout's current HEAD, or None if it cannot be read.

    None rather than an exception or a placeholder: a caller that cannot tell
    must render `unknown`, and any sentinel string here would eventually be
    displayed as if it were a commit.
    """
    try:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def banner(state: Staleness) -> str:
    """One line, always emitted, saying what code this page came from.

    A full-width shell banner (theme's `.mc-banner`), matching the provenance
    banner one row above it in the shell -- both are a fact about the whole
    page, so both get banner treatment rather than the inset `.review-note`
    paragraph style, which is for notes inside a panel. `.mc-banner-alert` is
    the loud accent variant, used when the news must stop the reader: an
    unknown age or older code. A clean match is quiet, like the provenance
    banner's "live data" line.
    """
    if not state.is_known:
        return (
            '<div class="mc-banner mc-banner-alert" data-region="served-code" '
            'data-stale="unknown" role="alert">'
            "<strong>The age of this code is unknown.</strong> The checkout's "
            "current commit could not be read, so this page cannot tell you "
            "whether the process is behind it — that is a statement about the "
            "check, not a clean bill of health.</div>"
        )
    if state.is_stale:
        return (
            '<div class="mc-banner mc-banner-alert" data-region="served-code" '
            'data-stale="yes" role="alert">'
            f"<strong>This process is serving older code.</strong> Started from "
            f'<span class="mono">{_e(state.served or "")}</span>; the checkout is '
            f'now at <span class="mono">{_e(state.current or "")}</span>. '
            "Anything merged since is <em>not on this page</em> — it will render "
            "exactly as if it had never been built. <strong>Restart the dashboard "
            "to pick it up.</strong></div>"
        )
    return (
        '<div class="mc-banner" data-region="served-code" data-stale="no">'
        f'Serving <span class="mono">{_e(state.served or "")}</span>, which matches '
        "the checkout. Nothing merged is missing from this page.</div>"
    )
