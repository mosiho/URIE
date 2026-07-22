"""Live interception / challenge loop — contradiction detection (§3.2)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from urie.domain.facts import Fact, values_contradict


@dataclass(frozen=True)
class CandidateMutation:
    entity: str
    subject_node_id: Optional[str]  # may be unresolved yet
    subject_spoken: str
    value: Any
    is_hypothesis: bool = False
    edge_type: Optional[str] = None  # HAS_TRAIT, RELATES_TO, etc.
    trait_name: Optional[str] = None
    rel_label: Optional[str] = None


@dataclass(frozen=True)
class Challenge:
    entity: str
    subject_node_id: str
    subject_spoken: str
    existing_fact_id: str
    existing_value: Any
    candidate_value: Any
    vui_prompt: str

    def to_dict(self) -> dict:
        return {
            "entity": self.entity,
            "subject_node_id": self.subject_node_id,
            "subject_spoken": self.subject_spoken,
            "existing_fact_id": self.existing_fact_id,
            "existing_value": self.existing_value,
            "candidate_value": self.candidate_value,
            "vui_prompt": self.vui_prompt,
        }


def detect_contradiction(
    candidate: CandidateMutation,
    existing: Optional[Fact],
) -> Optional[Challenge]:
    """
    When new input contradicts a stored active fact, freeze ingestion and challenge.
    Never silently overwrite.
    """
    if existing is None or not existing.is_active:
        return None
    if existing.entity != candidate.entity:
        return None
    if candidate.subject_node_id and existing.subject_node_id != candidate.subject_node_id:
        return None
    if not values_contradict(existing.value, candidate.value):
        return None

    prompt = (
        f"Ask why {candidate.entity} changed from {existing.value!r} "
        f"to {candidate.value!r} for {candidate.subject_spoken}."
    )
    return Challenge(
        entity=candidate.entity,
        subject_node_id=existing.subject_node_id,
        subject_spoken=candidate.subject_spoken,
        existing_fact_id=existing.fact_id,
        existing_value=existing.value,
        candidate_value=candidate.value,
        vui_prompt=prompt,
    )
