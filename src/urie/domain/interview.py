"""Knowledge-gap detection for dynamic interviews (pure domain)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional, Sequence


class GapType(str, Enum):
    STALE_FACT = "stale_fact"
    LOW_CONFIDENCE = "low_confidence"
    OPEN_HYPOTHESIS = "open_hypothesis"
    MISSING_ATTRIBUTE = "missing_attribute"
    EXPIRED_CONSTRAINT = "expired_constraint"


# Attributes we expect on high-value Person nodes (beachhead: real estate)
CORE_PERSON_ATTRIBUTES = ("Budget", "Timeline", "DecisionMaker")


@dataclass(frozen=True)
class GapConfig:
    stale_after_days: float = 30.0
    low_confidence_below: float = 0.75
    missing_attrs: tuple[str, ...] = CORE_PERSON_ATTRIBUTES


@dataclass
class KnowledgeGap:
    gap_type: GapType
    subject_node_id: str
    entity: str
    priority: float
    rationale: str
    subject_name: str = ""
    gap_id: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.gap_id:
            self.gap_id = f"{self.gap_type.value}:{self.subject_node_id}:{self.entity}"

    def to_dict(self) -> dict[str, Any]:
        return {
            "gap_id": self.gap_id,
            "gap_type": self.gap_type.value,
            "subject_node_id": self.subject_node_id,
            "subject_name": self.subject_name,
            "entity": self.entity,
            "priority": self.priority,
            "rationale": self.rationale,
            "meta": self.meta,
        }


def _days_ago(ts: Optional[datetime], now: datetime) -> float:
    if ts is None:
        return 9999.0
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return max(0.0, (now - ts).total_seconds() / 86400.0)


def detect_gaps(
    *,
    people: Sequence[dict[str, Any]],
    facts: Sequence[Any],  # Fact-like with entity, subject_node_id, confidence_score, ...
    constraints: Sequence[dict[str, Any]] | None = None,
    now: datetime | None = None,
    config: GapConfig | None = None,
) -> list[KnowledgeGap]:
    """
    Scan the agent's book for interview-worthy gaps.
    `facts` items should expose: entity, subject_node_id, confidence_score,
    is_hypothesis, is_active (or superseded_by), created_at.
    """
    cfg = config or GapConfig()
    now = now or datetime.now(timezone.utc)
    gaps: list[KnowledgeGap] = []
    people_by_id = {p["node_id"]: p for p in people if p.get("kind") == "Person" or "name" in p}

    # Index active facts by subject
    facts_by_subject: dict[str, list[Any]] = {}
    for f in facts:
        if getattr(f, "superseded_by", None):
            continue
        if hasattr(f, "is_active") and not f.is_active:
            continue
        sid = f.subject_node_id
        facts_by_subject.setdefault(sid, []).append(f)

    for node_id, person in people_by_id.items():
        name = person.get("name") or node_id
        subject_facts = facts_by_subject.get(node_id, [])
        entities_present = {f.entity for f in subject_facts}

        # Missing core attributes
        for attr in cfg.missing_attrs:
            if attr not in entities_present:
                gaps.append(
                    KnowledgeGap(
                        gap_type=GapType.MISSING_ATTRIBUTE,
                        subject_node_id=node_id,
                        subject_name=name,
                        entity=attr,
                        priority=0.7,
                        rationale=f"{name} has no {attr} on record",
                    )
                )

        for f in subject_facts:
            conf = float(getattr(f, "confidence_score", 0.8))
            created = getattr(f, "created_at", None)
            age = _days_ago(created, now)

            if getattr(f, "is_hypothesis", False):
                gaps.append(
                    KnowledgeGap(
                        gap_type=GapType.OPEN_HYPOTHESIS,
                        subject_node_id=node_id,
                        subject_name=name,
                        entity=f.entity,
                        priority=0.85,
                        rationale=f"{name}'s {f.entity} was marked as a hypothesis",
                        meta={"fact_id": getattr(f, "fact_id", None)},
                    )
                )

            if conf < cfg.low_confidence_below and not getattr(f, "is_hypothesis", False):
                gaps.append(
                    KnowledgeGap(
                        gap_type=GapType.LOW_CONFIDENCE,
                        subject_node_id=node_id,
                        subject_name=name,
                        entity=f.entity,
                        priority=0.8 + (cfg.low_confidence_below - conf) * 0.2,
                        rationale=f"{name}'s {f.entity} confidence is {conf:.2f}",
                        meta={"confidence": conf, "fact_id": getattr(f, "fact_id", None)},
                    )
                )

            if age >= cfg.stale_after_days:
                # Priority rises with age
                gaps.append(
                    KnowledgeGap(
                        gap_type=GapType.STALE_FACT,
                        subject_node_id=node_id,
                        subject_name=name,
                        entity=f.entity,
                        priority=min(0.95, 0.55 + age / 100.0),
                        rationale=f"{name}'s {f.entity} is {age:.0f} days old",
                        meta={"age_days": age, "fact_id": getattr(f, "fact_id", None)},
                    )
                )

    # Expired constraints (window_end in the past)
    for c in constraints or []:
        end = c.get("window_end")
        if end is None:
            continue
        if isinstance(end, str):
            try:
                end = datetime.fromisoformat(end.replace("Z", "+00:00"))
            except ValueError:
                continue
        if end.tzinfo is None:
            end = end.replace(tzinfo=timezone.utc)
        if end <= now:
            sid = c.get("subject_node_id") or ""
            name = people_by_id.get(sid, {}).get("name") or sid
            gaps.append(
                KnowledgeGap(
                    gap_type=GapType.EXPIRED_CONSTRAINT,
                    subject_node_id=sid,
                    subject_name=name,
                    entity="Constraint",
                    priority=0.9,
                    rationale=f"{name}'s DND/constraint window ended; follow-up opportunity",
                    meta={"label": c.get("label"), "window_end": end.isoformat()},
                )
            )

    return prioritize_gaps(gaps)


def prioritize_gaps(gaps: Sequence[KnowledgeGap]) -> list[KnowledgeGap]:
    """Sort by priority descending; stable for equal scores."""
    return sorted(gaps, key=lambda g: (-g.priority, g.gap_type.value, g.entity))
