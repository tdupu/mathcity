"""Per-brief pile state, including the rejections nothing could read (#226).

Panel v2 re-grounded the error-briefs and HELD views on real failure artifacts
(ADR 0004 D4). The artifacts exist -- `.pile/.rejected/<slug>/rejection.json`,
measured on disk -- and no typed tool served them, so the dashboard rendered an
honest "not readable" banner over data that was sitting there.

## WHY THIS IS NOT A COSMETIC GAP

`.pile/.rejected/` is read by `briefs_list`? No. Shown on `/queue`? No. Surfaced
by `check-briefs`? No. **A brief moved there leaves the adjudication queue with
no operator-visible trace**, and from the Mayor's chair it looks identical to a
brief that was never filed.

Measured 2026-08-29 (`mc-x338k`): the three briefs the S63 charge told four
consecutive Mayors to present FIRST -- `mc-s0a4j`, `mc-vmcc5`, `mc-7a98s` --
were all sitting in `.rejected/`. Four sessions recorded "not presented"; none
recorded "cannot be presented", because nothing could tell them apart. Eight
more in that directory carry a verdict (7 approve, 1 reject).

That is the wilt failure in structural form: not a bead without a brief, but a
brief with no route back. This module is the route back.

## WHAT IT REPORTS, AND WHAT IT REFUSES TO INVENT

`REJECTED` is a MEASUREMENT -- the artifact exists, and its `reason`,
`gate_profile`, `rejected_at` and `failures` are read verbatim.

`PENDING` means present in the pile and not rejected. It does **not** mean
promotable.

The issue asks for `PROMOTABLE` / `WAITING-on-gate-X`, and this deliberately
does not emit them. Gate evaluation lives in `brief-check.sh` and the shuffler
-- shell, outside the typed surface -- and `#66` records the pile's gate state
as unreadable. Deriving PROMOTABLE from "in the pile and not rejected" would be
a guess wearing a measurement's clothes, and the guess would read as an
assurance that a brief is ready to promote. `gate_state` is therefore `null`
with `gate_state_known: false`, which is the honest half of what was asked for.

`failures: []` is itself worth surfacing rather than smoothing: on the live
population every rejection carries an empty failures list beside a non-empty
`reason`, so the gate names a verdict without naming which check produced it.
Reported as-is; a reader that saw `[]` and inferred "no failures" would have it
exactly backwards.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .diagnostics import Diagnostic, Severity

STATE_PENDING = "PENDING"
STATE_REJECTED = "REJECTED"

MPIL_PILE_UNREACHABLE = "MPIL_PILE_UNREACHABLE"
MPIL_REJECTION_UNPARSEABLE = "MPIL_REJECTION_UNPARSEABLE"
MPIL_GATE_STATE_UNREADABLE = "MPIL_GATE_STATE_UNREADABLE"

#: Directory under the pile holding one folder per rejected brief.
REJECTED_DIRNAME = ".rejected"


def city_reader(pile_root: Any) -> Callable[[str], Any]:
    """A reader over one rig's pile directory.

    Raises rather than returning a default on every failure path: a pile that
    cannot be listed must be reported `unreachable`, never as an empty pile. An
    empty pile and an unreadable one are different answers about whether any
    brief is waiting, and conflating them is how a stalled queue reads as a
    drained one.
    """

    def read(what: str) -> Any:
        pile = Path(pile_root)
        if what == "pending":
            if not pile.is_dir():
                raise FileNotFoundError(f"no pile directory at {pile}")
            # Depth-1 files only, matching the shuffler's own invariant shape:
            # `.rejected/`, `.no-brainer/` and `.bak-archive/` are excluded
            # structurally rather than by name, and dotfiles are partials.
            return sorted(
                path.stem
                for path in pile.iterdir()
                if path.is_file() and path.suffix == ".md" and not path.name.startswith(".")
            )
        if what == "rejected":
            rejected = pile / REJECTED_DIRNAME
            if not rejected.is_dir():
                return []  # a pile with no rejections is a real, empty answer
            out = []
            for entry in sorted(rejected.iterdir()):
                if not entry.is_dir():
                    continue
                payload_path = entry / "rejection.json"
                if not payload_path.is_file():
                    out.append({"slug": entry.name, "payload": None, "unparseable": "absent"})
                    continue
                try:
                    out.append(
                        {
                            "slug": entry.name,
                            "payload": json.loads(payload_path.read_text(encoding="utf-8")),
                            "unparseable": None,
                        }
                    )
                except (OSError, ValueError) as error:
                    out.append({"slug": entry.name, "payload": None, "unparseable": str(error)})
            return out
        raise KeyError(what)

    return read


def _unreachable(err: Exception) -> dict[str, Any]:
    """The pile could not be listed. Populations are `None`, never `[]`."""
    return {
        "state": "unreachable",
        "briefs": None,
        "pending_count": None,
        "rejected_count": None,
        "gate_state_known": False,
        "diagnostics": [
            Diagnostic(
                Severity.WARN,
                MPIL_PILE_UNREACHABLE,
                f"pile directory unreadable: {err}",
            ).to_dict()
        ],
    }


def briefs_pile_state(read: Callable[[str], Any]) -> dict[str, Any]:
    """Every brief in the pile with its state, and every rejection's payload."""
    try:
        pending = list(read("pending"))
        rejected = list(read("rejected"))
    except Exception as err:  # noqa: BLE001 -- any read failure is "we could not look"
        return _unreachable(err)

    diagnostics: list[dict[str, Any]] = []
    briefs: list[dict[str, Any]] = []

    for entry in rejected:
        payload = entry.get("payload") or {}
        if entry.get("unparseable"):
            diagnostics.append(
                Diagnostic(
                    Severity.WARN,
                    MPIL_REJECTION_UNPARSEABLE,
                    (
                        f"{entry['slug']}: rejection artifact could not be read "
                        f"({entry['unparseable']}); it is reported REJECTED with no detail "
                        "rather than omitted."
                    ),
                ).to_dict()
            )
        briefs.append(
            {
                "slug": entry["slug"],
                "state": STATE_REJECTED,
                # Verbatim from the artifact. `failures` is commonly `[]` beside a
                # non-empty `reason` on the live population -- surfaced as-is,
                # because a reader inferring "no failures" from `[]` would have it
                # exactly backwards.
                "reason": payload.get("reason"),
                "gate_profile": payload.get("gate_profile"),
                "rejected_at": payload.get("rejected_at"),
                "failures": payload.get("failures"),
                "source_path": payload.get("source_path"),
                "artifact_readable": entry.get("unparseable") is None,
                "gate_state": None,
            }
        )

    rejected_slugs = {entry["slug"] for entry in rejected}
    for slug in pending:
        if slug in rejected_slugs:
            # Present in BOTH: the markdown was re-deposited after a rejection.
            # Already listed as REJECTED above; listing it twice would double the
            # count and imply two briefs.
            continue
        briefs.append(
            {
                "slug": slug,
                "state": STATE_PENDING,
                "reason": None,
                "gate_profile": None,
                "rejected_at": None,
                "failures": None,
                "source_path": None,
                "artifact_readable": True,
                "gate_state": None,
            }
        )

    diagnostics.append(
        Diagnostic(
            Severity.INFO,
            MPIL_GATE_STATE_UNREADABLE,
            (
                "PROMOTABLE / WAITING-on-gate is not reported: gate evaluation lives in "
                "brief-check.sh and the shuffler, outside the typed surface (#66). "
                "PENDING means present and not rejected -- it does NOT mean promotable."
            ),
        ).to_dict()
    )

    return {
        "state": "healthy",
        "briefs": briefs,
        "pending_count": sum(1 for b in briefs if b["state"] == STATE_PENDING),
        "rejected_count": sum(1 for b in briefs if b["state"] == STATE_REJECTED),
        # Always false today. Named rather than omitted so a consumer can tell
        # "not promotable" from "we cannot say whether it is promotable".
        "gate_state_known": False,
        "diagnostics": diagnostics,
    }
