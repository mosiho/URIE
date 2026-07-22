"""Unit tests for Fact / Money / ConditionalField / supersede."""

from datetime import datetime, timezone

import pytest

from urie.domain.facts import (
    CONFLICT_RESOLUTION_CONFIDENCE,
    ConditionalField,
    ConditionalVariable,
    Fact,
    Money,
    conflict_resolution_fact,
    supersede,
    values_contradict,
)


def test_money_roundtrip():
    m = Money(amount=5_000_000, currency="EUR")
    assert Money.from_dict(m.to_dict()) == m


def test_conditional_field_baseline():
    cf = ConditionalField(
        field_name="purchasing_power",
        base_metric=Money(3_500_000_000, "IRT"),
        ceiling_metric=Money(5_000_000_000, "IRT"),
        variables=[
            ConditionalVariable("company_bonus_payout", "increases_ceiling", "node_trait_bonus")
        ],
    )
    assert cf.baseline_value == {"amount": 3_500_000_000, "currency": "IRT"}
    assert len(cf.to_dict()["variables"]) == 1


def test_supersede_preserves_old():
    old = Fact(
        agent_id="agt_1",
        entity="Budget",
        subject_node_id="node_john",
        value={"amount": 3e6, "currency": "USD"},
        confidence_score=0.8,
    )
    new = conflict_resolution_fact(
        agent_id="agt_1",
        entity="Budget",
        subject_node_id="node_john",
        value={"amount": 5e6, "currency": "USD"},
    )
    updated_old, new_f = supersede(old, new)
    assert updated_old.superseded_by == new_f.fact_id
    assert updated_old.is_active is False
    assert new_f.is_active is True
    assert new_f.confidence_score == CONFLICT_RESOLUTION_CONFIDENCE
    assert new_f.is_conflict_resolution is True


def test_supersede_rejects_cross_agent():
    old = Fact(agent_id="a", entity="Budget", subject_node_id="n", value=1)
    new = Fact(agent_id="b", entity="Budget", subject_node_id="n", value=2)
    with pytest.raises(ValueError):
        supersede(old, new)


def test_values_contradict_money():
    assert values_contradict({"amount": 3e6, "currency": "USD"}, {"amount": 5e6, "currency": "USD"})
    assert not values_contradict(
        {"amount": 3e6, "currency": "USD"}, {"amount": 3e6, "currency": "USD"}
    )


def test_fact_with_confidence_clamps():
    f = Fact(agent_id="a", entity="X", subject_node_id="n", value="v")
    assert f.with_confidence(1.5).confidence_score == 1.0
    assert f.with_confidence(-1).confidence_score == 0.0


def test_fact_created_at_timezone():
    f = Fact(agent_id="a", entity="X", subject_node_id="n", value="v")
    assert f.created_at.tzinfo is not None
    assert f.created_at <= datetime.now(timezone.utc)
