"""Pure domain: Fact objects, money, conditional fields, temporal supersede."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4


def new_fact_id() -> str:
    return f"fct_{uuid4()}"


@dataclass(frozen=True)
class Money:
    amount: float
    currency: str = "USD"

    def to_dict(self) -> dict[str, Any]:
        return {"amount": self.amount, "currency": self.currency}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Money:
        return cls(amount=float(data["amount"]), currency=str(data.get("currency", "USD")))


@dataclass
class ConditionalVariable:
    trigger_condition: str
    impact: str  # e.g. increases_ceiling
    associated_node_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "trigger_condition": self.trigger_condition,
            "impact": self.impact,
            "associated_node_id": self.associated_node_id,
        }


@dataclass
class ConditionalField:
    """Fuzzy numeric field from messy speech (§4.2)."""

    field_name: str
    base_metric: Money
    ceiling_metric: Optional[Money] = None
    variables: list[ConditionalVariable] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "field_name": self.field_name,
            "base_metric": self.base_metric.to_dict(),
            "ceiling_metric": self.ceiling_metric.to_dict() if self.ceiling_metric else None,
            "variables": [v.to_dict() for v in self.variables],
        }

    @property
    def baseline_value(self) -> dict[str, Any]:
        """Safe queryable baseline for Postgres."""
        return self.base_metric.to_dict()


@dataclass
class Fact:
    """Canonical Fact — never a bare value (§4.1)."""

    agent_id: str
    entity: str
    subject_node_id: str
    value: Any
    fact_id: str = field(default_factory=new_fact_id)
    confidence_score: float = 0.8
    source: str = "voice_debrief"
    is_hypothesis: bool = False
    is_conflict_resolution: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    superseded_by: Optional[str] = None

    @property
    def is_active(self) -> bool:
        return self.superseded_by is None

    def with_confidence(self, score: float) -> Fact:
        return Fact(
            fact_id=self.fact_id,
            agent_id=self.agent_id,
            entity=self.entity,
            subject_node_id=self.subject_node_id,
            value=self.value,
            confidence_score=max(0.0, min(1.0, score)),
            source=self.source,
            is_hypothesis=self.is_hypothesis,
            is_conflict_resolution=self.is_conflict_resolution,
            created_at=self.created_at,
            superseded_by=self.superseded_by,
        )


CONFLICT_RESOLUTION_CONFIDENCE = 0.95


def supersede(old: Fact, new: Fact) -> tuple[Fact, Fact]:
    """
    Point old.superseded_by at new.fact_id. Old facts are never deleted (temporal moat).
    Returns (updated_old, new).
    """
    if old.agent_id != new.agent_id:
        raise ValueError("Cannot supersede facts across agents")
    if old.entity != new.entity or old.subject_node_id != new.subject_node_id:
        raise ValueError("Supersede requires same subject + entity")

    updated_old = Fact(
        fact_id=old.fact_id,
        agent_id=old.agent_id,
        entity=old.entity,
        subject_node_id=old.subject_node_id,
        value=old.value,
        confidence_score=old.confidence_score,
        source=old.source,
        is_hypothesis=old.is_hypothesis,
        is_conflict_resolution=old.is_conflict_resolution,
        created_at=old.created_at,
        superseded_by=new.fact_id,
    )
    return updated_old, new


def conflict_resolution_fact(
    agent_id: str,
    entity: str,
    subject_node_id: str,
    value: Any,
    source: str = "voice_debrief",
) -> Fact:
    """Human-verified resolution: baseline confidence 0.95 (§3.2)."""
    return Fact(
        agent_id=agent_id,
        entity=entity,
        subject_node_id=subject_node_id,
        value=value,
        confidence_score=CONFLICT_RESOLUTION_CONFIDENCE,
        source=source,
        is_hypothesis=False,
        is_conflict_resolution=True,
    )


def values_contradict(existing: Any, candidate: Any) -> bool:
    """
    Heuristic contradiction check for comparable values.
    Money/dicts compared on amount+currency; scalars on equality.
    """
    if existing is None or candidate is None:
        return False

    def _normalize(v: Any) -> Any:
        if isinstance(v, Money):
            return ("money", v.amount, v.currency)
        if isinstance(v, dict) and "amount" in v:
            return ("money", float(v["amount"]), v.get("currency", "USD"))
        if isinstance(v, ConditionalField):
            return _normalize(v.baseline_value)
        if isinstance(v, (int, float)):
            return ("num", float(v))
        return ("str", str(v).strip().lower())

    a, b = _normalize(existing), _normalize(candidate)
    if a[0] != b[0]:
        # Different shapes — treat as potential contradiction if both are money-like or both scalar
        return True
    return a != b
