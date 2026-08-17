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
    PolicyReference(
        "subdomains/brief-system/POLICY.md B2.10",
        "Legacy decisions-track is migration input, not an active presentation lane.",
    ),
)
