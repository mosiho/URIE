"""
Vertical-slice integration tests against in-memory adapters.

These exercise the full engine loop without requiring Docker/Postgres.
Postgres-backed tests live in test_vertical_slice.py and skip when DB is down.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from urie.adapters.memory import (
    InMemoryEmbeddingRepository,
    InMemoryEventBus,
    InMemoryFactRepository,
    InMemoryGraphRepository,
)
from urie.services.pipeline import VerticalSliceEngine


@pytest.fixture
def engine() -> VerticalSliceEngine:
    return VerticalSliceEngine(
        facts=InMemoryFactRepository(),
        graph=InMemoryGraphRepository(),
        embeddings=InMemoryEmbeddingRepository(),
        bus=InMemoryEventBus(),
    )


AGENT = "agt_mem_01"


@pytest.mark.asyncio
async def test_new_fact_flow_produces_feed_item(engine: VerticalSliceEngine):
    result = await engine.start_debrief(
        AGENT,
        transcript="Met with John today. John's budget is 3 million USD.",
    )
    assert result["status"] == "completed"
    assert len(result["staged_mutations"]) >= 1
    mut = result["staged_mutations"][0]
    assert mut["entity"] == "Budget"
    assert mut["value"]["amount"] == 3_000_000

    nodes = await engine.graph.list_nodes(AGENT, kind="Person")
    assert any(n["name"] == "John" for n in nodes)

    facts = await engine.facts.list_for_subject(AGENT, mut["subject_node_id"])
    active = [f for f in facts if f.entity == "Budget" and f.is_active]
    assert len(active) == 1

    n = await engine.process_reasoning()
    assert n >= 1
    items = await engine.list_feed(AGENT, include_held=True)
    assert len(items) >= 1
    assert items[0]["status"] == "active"
    assert "John" in items[0]["script"]


@pytest.mark.asyncio
async def test_contradiction_challenge_supersede_and_held_feed(engine: VerticalSliceEngine):
    r1 = await engine.start_debrief(
        AGENT,
        transcript="Spoke with John. John's budget is 3 million USD.",
    )
    assert r1["status"] == "completed"
    await engine.process_reasoning()

    r2 = await engine.start_debrief(
        AGENT,
        transcript="Update on John — John's budget is 5 million USD now.",
    )
    assert r2["status"] == "awaiting_resolution"
    assert r2["pending_challenge"]["entity"] == "Budget"
    old_fact_id = r2["pending_challenge"]["existing_fact_id"]

    r3 = await engine.resolve_challenge(
        AGENT,
        r2["session_id"],
        resolution_note="His bonus came through and spouse agreed to stretch.",
        accepted_value={"amount": 5_000_000, "currency": "USD"},
    )
    assert r3["status"] == "completed"
    new_mut = [m for m in r3["staged_mutations"] if m.get("is_conflict_resolution")]
    assert new_mut
    new_fact_id = new_mut[0]["fact_id"]

    subject_id = new_mut[0]["subject_node_id"]
    all_facts = await engine.facts.list_for_subject(AGENT, subject_id)
    budget_facts = [f for f in all_facts if f.entity == "Budget"]
    active = [f for f in budget_facts if f.is_active]
    superseded = [f for f in budget_facts if not f.is_active]
    assert len(active) == 1
    assert active[0].fact_id == new_fact_id
    assert active[0].is_conflict_resolution is True
    assert active[0].confidence_score == 0.95
    assert any(f.fact_id == old_fact_id and f.superseded_by == new_fact_id for f in superseded)

    r4 = await engine.start_debrief(
        AGENT,
        transcript="Don't contact John until 2026-07-28 — high workload this week.",
    )
    assert r4["status"] == "completed"

    r5 = await engine.start_debrief(
        AGENT,
        transcript="Great news — John's wife is expecting a baby.",
    )
    assert r5["status"] == "completed"

    await engine.process_reasoning()
    items = await engine.list_feed(AGENT, include_held=True)
    held = [i for i in items if i["status"] == "held"]
    assert len(held) >= 1
    held_item = held[0]
    assert held_item["held_until"] is not None

    # Force release
    held_item["held_until"] = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    await engine.feed.update(held_item)
    released = await engine.release_held()
    assert released >= 1

    items2 = await engine.list_feed(AGENT, include_held=False)
    assert any(i["feed_id"] == held_item["feed_id"] and i["status"] == "active" for i in items2)
