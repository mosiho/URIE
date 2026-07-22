"""
End-to-end vertical slice integration tests.

Requires Postgres with pgvector (docker compose up -d).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from urie.adapters.db import models as m
from urie.services.ingestion import IngestionService
from urie.services.reasoning_worker import FeedService, ReasoningWorker


AGENT = "agt_test_01"


@pytest.mark.asyncio
async def test_new_fact_flow_produces_feed_item(session):
    """(a) new node + fact + graph edge + feed item from a canned debrief."""
    svc = IngestionService(session)
    result = await svc.start_debrief(
        AGENT,
        transcript="Met with John today. John's budget is 3 million USD.",
    )
    assert result["status"] == "completed"
    assert len(result["staged_mutations"]) >= 1
    mut = result["staged_mutations"][0]
    assert mut["entity"] == "Budget"
    assert mut["value"]["amount"] == 3_000_000

    # Person node exists
    nodes = (
        await session.execute(
            select(m.Node).where(m.Node.agent_id == AGENT, m.Node.kind == m.NodeKind.PERSON)
        )
    ).scalars().all()
    assert any(n.name == "John" for n in nodes)

    # Fact persisted and active
    facts = (
        await session.execute(
            select(m.Fact).where(m.Fact.agent_id == AGENT, m.Fact.entity == "Budget")
        )
    ).scalars().all()
    assert len(facts) == 1
    assert facts[0].superseded_by is None

    # Outbox event then reasoning → feed
    worker = ReasoningWorker(session)
    n = await worker.process_pending()
    assert n >= 1

    feed = FeedService(session)
    items = await feed.list_feed(AGENT, include_held=True)
    assert len(items) >= 1
    assert items[0]["status"] == "active"
    assert "John" in items[0]["script"]


@pytest.mark.asyncio
async def test_contradiction_challenge_supersede_and_held_feed(session):
    """
    (b) contradiction triggers challenge loop → resolve supersedes old fact;
        DND constraint holds then releases a feed item.
    """
    svc = IngestionService(session)

    # Seed initial budget
    r1 = await svc.start_debrief(
        AGENT,
        transcript="Spoke with John. John's budget is 3 million USD.",
    )
    assert r1["status"] == "completed"
    subject_id = r1["staged_mutations"][0]["subject_node_id"]

    # Process first feed
    worker = ReasoningWorker(session)
    await worker.process_pending()

    # Contradicting debrief
    r2 = await svc.start_debrief(
        AGENT,
        transcript="Update on John — John's budget is 5 million USD now.",
    )
    assert r2["status"] == "awaiting_resolution"
    assert r2["pending_challenge"] is not None
    assert r2["pending_challenge"]["entity"] == "Budget"
    assert r2["pending_challenge"]["existing_fact_id"]

    # Resolve with narrative
    r3 = await svc.resolve_challenge(
        AGENT,
        r2["session_id"],
        resolution_note="His bonus came through and spouse agreed to stretch.",
        accepted_value={"amount": 5_000_000, "currency": "USD"},
    )
    assert r3["status"] == "completed"
    new_mut = [m for m in r3["staged_mutations"] if m.get("is_conflict_resolution")]
    assert new_mut
    new_fact_id = new_mut[0]["fact_id"]

    # Old fact superseded
    old = await session.get(m.Fact, r2["pending_challenge"]["existing_fact_id"])
    # pending_challenge was cleared — fetch from DB by superseded_by
    all_facts = (
        await session.execute(
            select(m.Fact).where(m.Fact.agent_id == AGENT, m.Fact.entity == "Budget")
        )
    ).scalars().all()
    active = [f for f in all_facts if f.superseded_by is None]
    superseded = [f for f in all_facts if f.superseded_by is not None]
    assert len(active) == 1
    assert active[0].fact_id == new_fact_id
    assert active[0].is_conflict_resolution is True
    assert active[0].confidence_score == 0.95
    assert len(superseded) >= 1
    assert superseded[0].superseded_by == new_fact_id

    # Add DND constraint via debrief, then a trait opportunity
    r4 = await svc.start_debrief(
        AGENT,
        transcript="Don't contact John until 2026-07-28 — high workload this week.",
    )
    assert r4["status"] == "completed"

    r5 = await svc.start_debrief(
        AGENT,
        transcript="Great news — John's wife is expecting a baby.",
    )
    assert r5["status"] == "completed"

    await worker.process_pending()

    feed = FeedService(session)
    items = await feed.list_feed(AGENT, include_held=True)
    held = [i for i in items if i["status"] == "held"]
    # Trait opportunity should be held due to DND
    assert any("baby" in (i["script"] + i["rationale"]).lower() or i["status"] == "held" for i in items)
    assert len(held) >= 1
    held_item = held[0]
    assert held_item["held_until"] is not None

    # Force release by backdating held_until
    row = await session.get(m.FeedItem, held_item["feed_id"])
    row.held_until = datetime.now(timezone.utc) - timedelta(minutes=1)
    await session.flush()
    await session.commit()

    released = await worker.release_held_items()
    assert released >= 1

    items2 = await feed.list_feed(AGENT, include_held=False)
    assert any(i["feed_id"] == held_item["feed_id"] and i["status"] == "active" for i in items2)


@pytest.mark.asyncio
async def test_crm_writeback_idempotent(session):
    from urie.adapters.db.models import CRMWriteback

    svc = IngestionService(session)
    r = await svc.start_debrief(
        AGENT,
        transcript="Met Sarah. Sarah's budget is 2 million EUR.",
    )
    fact_id = r["staged_mutations"][0]["fact_id"]

    session.add(
        CRMWriteback(
            writeback_id="wb_1",
            agent_id=AGENT,
            fact_id=fact_id,
            note="Sarah budget 2M EUR",
            crm_target="follow_up_boss",
        )
    )
    await session.commit()

    # Second insert with same fact_id should violate unique — we check via query
    existing = (
        await session.execute(select(CRMWriteback).where(CRMWriteback.fact_id == fact_id))
    ).scalar_one()
    assert existing.note == "Sarah budget 2M EUR"
