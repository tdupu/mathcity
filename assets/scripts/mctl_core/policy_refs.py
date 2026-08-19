"""Policy references rendered by the read-only brief surface."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PolicyReference:
    reference: str
    description: str

    def to_dict(self) -> dict[str, str]:
        return {"description": self.description, "reference": self.reference}


BRIEF_POLICY_REFERENCES = (
    PolicyReference(
        "subdomains/brief-system/POLICY.md B2.1",
        "A brief is a decision bead with at least one source dependency.",
    ),
    PolicyReference(
        "subdomains/brief-system/POLICY.md B2.8",
        "The bead store is canonical; filesystem artifacts are redundant cache.",
    ),
    # Slice 2 revisited this exclusion by measuring it rather than assuming it.
    # The manifest carries a typed `verdict` on 126 of its 204 rows, but 0 of
    # those rows join to a decision bead: 97 name no source bead at all, and the
    # 20 distinct beads the rest name are work items, none of type=decision. So
    # the exclusion stands on evidence now -- the lane is not merely
    # deprioritised, it is disjoint from the bead population.
    PolicyReference(
        "subdomains/brief-system/POLICY.md B2.10",
        "Legacy decisions-track is migration input, not an active presentation lane; "
        "measured 2026-08-19, 0 of its 126 typed verdicts join to a decision bead.",
    ),
)
