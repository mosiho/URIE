"""Unit tests for knowledge-gap detection."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from urie.domain.facts import Fact
from urie.domain.interview import GapType, detect_gaps, prioritize_gaps, KnowledgeGap


NOW = datetime(2026, 7, 21, tzinfo=timezone.utc)


def _person(nid: str, name: str) -> dict:
    return {"node_id": nid, "kind": "Person", "name": name}


def test_missing_attributes_for_new_person():
    people = [_person("n1", "John")]
    gaps = detect_gaps(people=people, facts=[], constraints=[], now=NOW)
    entities = {g.entity for g in gaps if g.gap_type == GapType.MISSING_ATTRIBUTE}
    assert "Budget" in entities
    assert "Timeline" in entities
    assert "DecisionMaker" in entities


def test_open_hypothesis_and_low_confidence():
    people = [_person("n1", "John")]
    facts = [
        Fact(
            agent_id="a",
            entity="Budget",
            subject_node_id="n1",
            value={"amount": 3_000_000, "currency": "USD"},
            is_hypothesis=True,
            confidence_score=0.6,
            created_at=NOW - timedelta(days=2),
        ),
        Fact(
            agent_id="a",
            entity="Timeline",
            subject_node_id="n1",
            value="Q4",
            confidence_score=0.5,
            created_at=NOW - timedelta(days=2),
        ),
    ]
    gaps = detect_gaps(people=people, facts=facts, now=NOW)
    types = {g.gap_type for g in gaps}
    assert GapType.OPEN_HYPOTHESIS in types
    assert GapType.LOW_CONFIDENCE in types


def test_stale_fact():
    people = [_person("n1", "John")]
    facts = [
        Fact(
            agent_id="a",
            entity="Budget",
            subject_node_id="n1",
            value={"amount": 1.0, "currency": "USD"},
            confidence_score=0.9,
            created_at=NOW - timedelta(days=60),
        )
    ]
    gaps = detect_gaps(people=people, facts=facts, now=NOW)
    assert any(g.gap_type == GapType.STALE_FACT and g.entity == "Budget" for g in gaps)


def test_expired_constraint():
    people = [_person("n1", "John")]
    constraints = [
        {
            "subject_node_id": "n1",
            "label": "Do-Not-Disturb",
            "window_end": NOW - timedelta(days=1),
        }
    ]
    gaps = detect_gaps(people=people, facts=[], constraints=constraints, now=NOW)
    assert any(g.gap_type == GapType.EXPIRED_CONSTRAINT for g in gaps)


def test_prioritize_sorts_descending():
    gaps = [
        KnowledgeGap(GapType.MISSING_ATTRIBUTE, "n1", "Budget", 0.5, "low", subject_name="A"),
        KnowledgeGap(GapType.EXPIRED_CONSTRAINT, "n1", "Constraint", 0.9, "high", subject_name="A"),
    ]
    ordered = prioritize_gaps(gaps)
    assert ordered[0].priority >= ordered[1].priority
