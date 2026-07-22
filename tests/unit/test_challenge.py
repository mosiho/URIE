"""Unit tests for challenge / contradiction detection."""

from urie.domain.challenge import CandidateMutation, detect_contradiction
from urie.domain.facts import Fact


def test_detects_budget_contradiction():
    existing = Fact(
        agent_id="agt",
        entity="Budget",
        subject_node_id="node_john",
        value={"amount": 3_000_000, "currency": "USD"},
        fact_id="fct_old",
    )
    candidate = CandidateMutation(
        entity="Budget",
        subject_node_id="node_john",
        subject_spoken="John",
        value={"amount": 5_000_000, "currency": "USD"},
    )
    challenge = detect_contradiction(candidate, existing)
    assert challenge is not None
    assert challenge.existing_fact_id == "fct_old"
    assert "budget" in challenge.vui_prompt.lower() or "Budget" in challenge.vui_prompt


def test_no_challenge_when_same_value():
    existing = Fact(
        agent_id="agt",
        entity="Budget",
        subject_node_id="node_john",
        value={"amount": 3_000_000, "currency": "USD"},
    )
    candidate = CandidateMutation(
        entity="Budget",
        subject_node_id="node_john",
        subject_spoken="John",
        value={"amount": 3_000_000, "currency": "USD"},
    )
    assert detect_contradiction(candidate, existing) is None


def test_no_challenge_without_existing():
    candidate = CandidateMutation(
        entity="Budget",
        subject_node_id="node_john",
        subject_spoken="John",
        value={"amount": 5_000_000, "currency": "USD"},
    )
    assert detect_contradiction(candidate, None) is None
