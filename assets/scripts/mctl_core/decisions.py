"""`decisions-to-briefs` as a typed operation: a brief that can be acted on.

#85 records the damage this exists to stop. `decisions-to-briefs/SKILL.md` writes
the pile manifest and the decisions track **directly, behind mctl's back**, and
it does that because no typed tool exists to do it properly -- the CT13.2 shape,
capability present, surface absent.

The bar is therefore not "a brief was created". It is that `work_status` on the
result returns `readiness: "ready"` with `blockers: []`. A tool that emits briefs
which cannot then be dispatched does not fix #85, it relocates it: the skill keeps
writing directly, because the sanctioned path still does not work.

`readiness == "ready"` requires ALL of, from `work.py`:

    MWRK011  a source dependency exists
    MWRK012  the source bead resolves
             the source bead is NOT closed
    MWRK010  the brief carries an approving verdict
    MWRK001  the source has no active assignee
    MWRK002  no open child workflow on the source
             no prior dispatch provenance

which is the pair requirement:

    ADJUDICATED BRIEF --(source dependency)--> OPEN SOURCE BEAD
      closed + approving verdict                  status NOT closed

Everything this module refuses is one of those conditions checked BEFORE the write,
so a caller is told at creation rather than discovering it at dispatch.

**This module does NOT create its own source bead.** #173 is the shape that
forbids it: a brief made its own source, then bricked the moment its own approval
closed that source. The source must already exist and be open, and the caller names
it.
"""

from __future__ import annotations

from dataclasses import dataclass

from .beads import Bead
from .diagnostics import Diagnostic, Severity


#: Refusals that mean "this brief would be born undispatchable". Each maps to the
#: `work.py` blocker it prevents, so the two surfaces cannot drift on what
#: "dispatchable" means.
MDTB_NO_SOURCE = "MDTB001"        # -> MWRK011
MDTB_SOURCE_NOT_FOUND = "MDTB002"  # -> MWRK012
MDTB_SOURCE_CLOSED = "MDTB003"     # -> the closed-source blocker
MDTB_SOURCE_ASSIGNED = "MDTB004"   # -> MWRK001
MDTB_SOURCE_HAS_WORKFLOW = "MDTB005"  # -> MWRK002


@dataclass(frozen=True)
class DecisionBriefInput:
    """One decision TO BE MADE, and the open bead it decides about."""

    decision: str
    source_bead_id: str
    title: str | None = None
    labels: tuple[str, ...] = ()
    requested_by: str | None = None


def dispatchability_refusals(
    make_diagnostic,
    *,
    source_bead_id: str,
    beads: tuple[Bead, ...],
    open_child_workflow_of,
) -> tuple[Diagnostic, ...]:
    """Every reason this brief would be undispatchable, checked before the write.

    `make_diagnostic` is injected rather than imported so this stays testable
    without a context, and `open_child_workflow_of` is passed in because the
    canonical implementation lives in `work.py` and duplicating it here is how the
    two definitions of "dispatchable" would drift apart.

    Returned as a tuple rather than raising on the first: a caller fixing one
    condition should not have to re-run to discover the next.
    """
    refusals: list[Diagnostic] = []
    if not (source_bead_id or "").strip():
        refusals.append(
            make_diagnostic(
                Severity.ERROR,
                MDTB_NO_SOURCE,
                "A dispatchable brief must name the open bead it decides about.",
                suggested_next_command="mctl work ready --json   # pick an open source bead",
            )
        )
        return tuple(refusals)

    source = next((b for b in beads if b.id == source_bead_id), None)
    if source is None:
        refusals.append(
            make_diagnostic(
                Severity.ERROR,
                MDTB_SOURCE_NOT_FOUND,
                f"Source bead {source_bead_id!r} was not found in this rig.",
                suggested_next_command=f"bd show {source_bead_id}",
            )
        )
        return tuple(refusals)

    if source.status.strip().lower() in {"closed", "done"}:
        # The #173 shape. A closed source cannot be worked, so the brief is born
        # bricked -- and it would report success at creation and fail only later
        # at dispatch.
        refusals.append(
            make_diagnostic(
                Severity.ERROR,
                MDTB_SOURCE_CLOSED,
                f"Source bead {source_bead_id!r} is {source.status}, so the brief "
                "would be undispatchable the moment it is created.",
                suggested_next_command="mctl work ready --json   # pick an open source bead",
            )
        )
    if source.has_active_assignee:
        refusals.append(
            make_diagnostic(
                Severity.ERROR,
                MDTB_SOURCE_ASSIGNED,
                f"Source bead {source_bead_id!r} already has an active assignee.",
                suggested_next_command=f"bd show {source_bead_id}",
            )
        )
    existing = open_child_workflow_of(source_bead_id)
    if existing is not None:
        refusals.append(
            make_diagnostic(
                Severity.ERROR,
                MDTB_SOURCE_HAS_WORKFLOW,
                f"An open child workflow already exists for {source_bead_id!r}.",
                suggested_next_command=f"mctl work status {existing} --json",
            )
        )
    return tuple(refusals)


def brief_body(
    decision: str,
    *,
    source_bead_id: str,
    checks_passed: tuple[str, ...],
    options_follow: bool = False,
    recommendation: str | None = None,
) -> str:
    """The `present-it` full-form body: §1 Decision-at-Top through §7 gates.

    #208 part 3. The old body was a hardcoded `## Decision` / `## Source` /
    `## Gate Evidence` triple. The Brief Manager detail screen renders the
    present-it full form -- §1 what-is-being-decided, §2 recommended answer,
    §3 assumptions, §4 alternatives, §5 risks, §6 evidence, §7 plan/gates --
    so a three-section body rendered as a stub with five empty sections. This
    composes all seven, in grill order, with the decision at the very top.

    The **Decision-at-Top INVARIANT** ([[present-it]] §1) is load-bearing:
    "what is being decided" is the FIRST content, before source, evidence or
    gates. `decisions_to_briefs` transports a QUESTION to be decided (#194),
    so this composer records no verdict and no recommendation -- §2 says so
    rather than inventing a recommended answer nobody gave. Authored decision
    options, when supplied, are appended as their own §4 Options block by the
    caller (mcp_server, #208 parts 1-2); this composer does not weave them in.

    Sections that have no material at composition say "None surfaced" with the
    reason, per present-it, rather than fabricating content -- the same
    could-not-have-failed shape this repo has spent the week removing. Only
    what was actually established is stated: the decision (§1), that no verdict
    exists yet (§2), the open source bead (§6), and the dispatch checks that
    passed (§7 Gate Evidence).

    The `### Gate Evidence` subsection under §7 keeps `briefs_create`'s
    structural rule satisfied (MBRF036, `required-sections.toml`), and its
    content is real evidence: each line is a `work.py` dispatch blocker that
    was tested before the write and did not fire.
    """
    decision_text = decision.strip()
    evidence_lines = "\n".join(f"- {check}" for check in checks_passed)
    # G17/C3 (mc-qbs6j). The old §2 opened "None recorded", which is the null
    # answer the gate refuses -- and Taylor's REVISE on `mc-67snh` was, in as
    # many words, "we need a recommendation". When the caller supplies one it
    # goes here, stated as the advisory it is (#194 keeps the marker prose, not
    # a verdict). When the caller supplies none there is nothing honest to put
    # here, and the creation gate refuses the brief rather than inventing one.
    advised = str(recommendation or "").strip()
    if advised:
        section_two = (
            f"Adopt option ({advised}) — advisory only. `decisions_to_briefs` "
            "records the author's recommendation and deposits the brief "
            "UNDECIDED (#194); the human adjudicator supplies the verdict."
        )
    else:
        section_two = (
            "None recorded. This brief transports a question to be decided; "
            "`decisions_to_briefs` deposits it UNDECIDED (#194) and the human "
            "adjudicator supplies the verdict."
        )
    # G17/C2. The composer used to emit this §4 placeholder unconditionally and
    # the caller then APPENDED its own `## §4 — Options`, so every brief that
    # carried options carried §4 twice -- 49 of the 178 live brief files, and
    # all 11 in-scope briefs this tool produced. `parse_decision_options` was
    # taught to de-duplicate around it (`seen_labels`) rather than the writer
    # being taught not to emit it. When options follow, the appended block IS
    # §4 and this placeholder is dropped.
    section_four = (
        ""
        if options_follow
        else (
            "## §4 — Alternatives named\n\n"
            "None enumerated at composition. The adjudicator may propose "
            "one.\n\n"
        )
    )
    return (
        "## §1 — What is being decided\n\n"
        f"{decision_text}\n\n"
        "## §2 — Recommended answer\n\n"
        f"{section_two}\n\n"
        "## §3 — Assumptions surfaced\n\n"
        "None surfaced at composition -- this brief was composed from a "
        "decision statement and its open source bead, not from a reviewed "
        "artifact.\n\n"
        f"{section_four}"
        "## §5 — Risks foregrounded\n\n"
        "None surfaced at composition. The decision has not yet been reviewed "
        "for breakage or downstream commitment; that is the adjudication.\n\n"
        "## §6 — Supporting evidence\n\n"
        f"This decision is about `{source_bead_id}`, an open bead in this rig. "
        "The source resolves, is not closed, and is unassigned -- the pair "
        "requirement an adjudicated brief needs to be dispatchable.\n\n"
        "## §7 — Plan membership, blocking, and required gates\n\n"
        f"Blocking: adjudicating this brief unblocks `{source_bead_id}`.\n\n"
        "### Gate Evidence\n\n"
        "Checked before this brief was written; each corresponds to a dispatch "
        "blocker in `work.py` that was tested and did not fire:\n\n"
        f"{evidence_lines}\n"
    )
