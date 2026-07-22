"""Unit tests for constraint gating / ghost-mode decisions."""

from datetime import datetime, timedelta, timezone

from urie.domain.reasoning import (
    ActiveConstraint,
    Opportunity,
    decide_ghost_mode,
)


def test_held_when_dnd_active():
    now = datetime(2026, 7, 15, tzinfo=timezone.utc)
    opp = Opportunity(
        subject_node_id="node_john",
        subject_name="John",
        trait_summary="Expecting a baby",
        mutation_event_id="evt_1",
    )
    constraints = [
        ActiveConstraint(
            edge_id="e1",
            constraint_node_id="c1",
            label="Do-Not-Disturb: high workload",
            window_start=now - timedelta(days=1),
            window_end=datetime(2026, 7, 28, tzinfo=timezone.utc),
        )
    ]
    decision = decide_ghost_mode(opp, constraints, when=now)
    assert decision.held is True
    assert decision.held_until == datetime(2026, 7, 28, tzinfo=timezone.utc)
    assert "Blocked" in decision.rationale


def test_released_when_dnd_expired():
    now = datetime(2026, 7, 29, tzinfo=timezone.utc)
    opp = Opportunity(
        subject_node_id="node_john",
        subject_name="John",
        trait_summary="Expecting a baby",
        mutation_event_id="evt_1",
    )
    constraints = [
        ActiveConstraint(
            edge_id="e1",
            constraint_node_id="c1",
            label="Do-Not-Disturb: high workload",
            window_start=datetime(2026, 7, 10, tzinfo=timezone.utc),
            window_end=datetime(2026, 7, 28, tzinfo=timezone.utc),
        )
    ]
    decision = decide_ghost_mode(
        opp,
        constraints,
        when=now,
        synthesized_script="Call John about the baby.",
        synthesized_rationale="Life event.",
        gifting_suggestion="Nursery gift",
    )
    assert decision.held is False
    assert decision.held_until is None
    assert "Call John" in decision.script
    assert decision.gifting_suggestion == "Nursery gift"


def test_no_constraints_releases():
    opp = Opportunity("n", "Jane", "Loves sailing", "evt")
    decision = decide_ghost_mode(opp, [])
    assert decision.held is False
    assert "Jane" in decision.script
