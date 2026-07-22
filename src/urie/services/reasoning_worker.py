"""Reasoning worker — consumes outbox events, applies constraint gating, writes feed."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from urie.adapters.db import models as m
from urie.adapters.db.repositories import PostgresGraphRepository
from urie.adapters.outbox.bus import OutboxEventBus
from urie.adapters.providers.mock import MockLLM
from urie.domain.reasoning import Opportunity, decide_ghost_mode


class ReasoningWorker:
    def __init__(
        self,
        session: AsyncSession,
        llm: Any = None,
    ) -> None:
        self.session = session
        self.llm = llm or MockLLM()
        self.graph = PostgresGraphRepository(session)
        self.bus = OutboxEventBus(session)

    async def process_pending(self, limit: int = 50) -> int:
        """Poll outbox and process unhandled graph.mutation events. Returns count processed."""
        events = await self.bus.poll_unprocessed(limit=limit)
        processed = 0
        for event in events:
            if event["event_type"] == "graph.mutation":
                await self._handle_mutation(event)
            await self.bus.mark_processed(event["event_id"])
            processed += 1
        await self.session.commit()
        return processed

    async def release_held_items(self, now: datetime | None = None) -> int:
        """Promote held feed items whose held_until has passed."""
        now = now or datetime.now(timezone.utc)
        q = select(m.FeedItem).where(
            m.FeedItem.status == m.FeedStatus.HELD,
            m.FeedItem.held_until.is_not(None),
            m.FeedItem.held_until <= now,
        )
        rows = (await self.session.execute(q)).scalars().all()
        for item in rows:
            # Strip [HELD] prefix if present and re-synthesize if needed
            script = item.script
            if script.startswith("[HELD]"):
                node = await self.graph.get_node(item.agent_id, item.subject_node_id)
                name = node["name"] if node else "client"
                script, rationale, gift = await self.llm.synthesize_ghost_script(
                    name, item.rationale, {}
                )
                item.script = script
                item.rationale = rationale
                item.gifting_suggestion = gift
            item.status = m.FeedStatus.ACTIVE
            item.held_until = None
        await self.session.flush()
        if rows:
            await self.session.commit()
        return len(rows)

    async def _handle_mutation(self, event: dict[str, Any]) -> None:
        payload = event["payload"]
        agent_id = event["agent_id"]
        kind = payload.get("kind")
        # Constraints alone don't produce outreach scripts
        if kind == "constraint_added":
            return

        subject_node_id = payload.get("subject_node_id")
        if not subject_node_id:
            return

        subject_name = payload.get("subject_name")
        if not subject_name:
            node = await self.graph.get_node(agent_id, subject_node_id)
            subject_name = node["name"] if node else "client"

        trait_summary = payload.get("trait_summary") or payload.get("entity", "update")
        constraints = await self.graph.active_constraints(agent_id, subject_node_id)

        script, rationale, gift = await self.llm.synthesize_ghost_script(
            subject_name, trait_summary, payload
        )
        opportunity = Opportunity(
            subject_node_id=subject_node_id,
            subject_name=subject_name,
            trait_summary=trait_summary,
            mutation_event_id=event["event_id"],
        )
        decision = decide_ghost_mode(
            opportunity,
            constraints,
            synthesized_script=script,
            synthesized_rationale=rationale,
            gifting_suggestion=gift,
        )

        feed = m.FeedItem(
            feed_id=f"feed_{uuid4()}",
            agent_id=agent_id,
            subject_node_id=subject_node_id,
            script=decision.script,
            rationale=decision.rationale,
            gifting_suggestion=decision.gifting_suggestion,
            status=m.FeedStatus.HELD if decision.held else m.FeedStatus.ACTIVE,
            held_until=decision.held_until,
            source_event_id=event["event_id"],
        )
        self.session.add(feed)
        await self.session.flush()


class FeedService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.graph = PostgresGraphRepository(session)

    async def list_feed(
        self,
        agent_id: str,
        include_held: bool = False,
    ) -> list[dict[str, Any]]:
        # Release any due held items first
        worker = ReasoningWorker(self.session)
        await worker.release_held_items()

        statuses = [m.FeedStatus.ACTIVE]
        if include_held:
            statuses.append(m.FeedStatus.HELD)
        q = (
            select(m.FeedItem)
            .where(m.FeedItem.agent_id == agent_id, m.FeedItem.status.in_(statuses))
            .order_by(m.FeedItem.created_at.desc())
        )
        rows = (await self.session.execute(q)).scalars().all()
        return [self._to_dict(r) for r in rows]

    async def ack(
        self,
        agent_id: str,
        feed_id: str,
        action: str = "acked",
    ) -> dict[str, Any]:
        q = select(m.FeedItem).where(
            m.FeedItem.feed_id == feed_id, m.FeedItem.agent_id == agent_id
        )
        item = (await self.session.execute(q)).scalar_one_or_none()
        if not item:
            raise LookupError(f"Feed item {feed_id} not found")
        if action == "dismissed":
            item.status = m.FeedStatus.DISMISSED
        else:
            item.status = m.FeedStatus.ACKED
        await self.session.flush()
        await self.session.commit()
        return self._to_dict(item)

    def _to_dict(self, item: m.FeedItem) -> dict[str, Any]:
        return {
            "feed_id": item.feed_id,
            "agent_id": item.agent_id,
            "subject_node_id": item.subject_node_id,
            "script": item.script,
            "rationale": item.rationale,
            "gifting_suggestion": item.gifting_suggestion,
            "status": item.status.value if hasattr(item.status, "value") else item.status,
            "held_until": item.held_until.isoformat() if item.held_until else None,
            "source_event_id": item.source_event_id,
            "created_at": item.created_at.isoformat() if item.created_at else None,
        }


class ConstraintService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.graph = PostgresGraphRepository(session)

    async def list_constraints(self, agent_id: str, person_node_id: str | None = None) -> list[dict]:
        if person_node_id:
            constraints = await self.graph.active_constraints(agent_id, person_node_id)
            return [
                {
                    "edge_id": c.edge_id,
                    "constraint_node_id": c.constraint_node_id,
                    "label": c.label,
                    "window_start": c.window_start.isoformat() if c.window_start else None,
                    "window_end": c.window_end.isoformat() if c.window_end else None,
                    "subject_node_id": person_node_id,
                }
                for c in constraints
            ]
        # All CONSTRAINED_BY edges for agent
        q = (
            select(m.Edge, m.Node)
            .join(m.Node, m.Node.node_id == m.Edge.dst_node_id)
            .where(
                m.Edge.agent_id == agent_id,
                m.Edge.edge_type == m.EdgeType.CONSTRAINED_BY,
            )
        )
        rows = (await self.session.execute(q)).all()
        return [
            {
                "edge_id": e.edge_id,
                "constraint_node_id": n.node_id,
                "label": n.name,
                "window_start": e.window_start.isoformat() if e.window_start else None,
                "window_end": e.window_end.isoformat() if e.window_end else None,
                "subject_node_id": e.src_node_id,
            }
            for e, n in rows
        ]

    async def set_constraint(
        self,
        agent_id: str,
        person_node_id: str,
        label: str,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
    ) -> dict:
        from urie.adapters.db.repositories import PostgresFactRepository
        from urie.adapters.outbox.bus import OutboxEventBus
        from urie.domain.facts import Fact

        facts = PostgresFactRepository(self.session)
        bus = OutboxEventBus(self.session)

        # Ensure agent + person exist
        person = await self.graph.get_node(agent_id, person_node_id)
        if not person:
            raise LookupError("Person node not found")

        constraint_id = await self.graph.create_node(
            agent_id, kind="Constraint", name=label, attrs={}
        )
        fact = Fact(
            agent_id=agent_id,
            entity="Constraint",
            subject_node_id=person_node_id,
            value={"label": label, "window_end": window_end.isoformat() if window_end else None},
            confidence_score=0.95,
            source="api",
        )
        await facts.save(fact)
        edge_id = await self.graph.upsert_edge(
            agent_id,
            "CONSTRAINED_BY",
            person_node_id,
            constraint_id,
            fact_id=fact.fact_id,
            confidence=0.95,
            window_start=window_start or datetime.now(timezone.utc),
            window_end=window_end,
        )
        await bus.publish(
            agent_id,
            "graph.mutation",
            {
                "kind": "constraint_added",
                "subject_node_id": person_node_id,
                "constraint_node_id": constraint_id,
                "trait_summary": label,
                "fact_id": fact.fact_id,
            },
        )
        await self.session.commit()
        return {
            "edge_id": edge_id,
            "constraint_node_id": constraint_id,
            "label": label,
            "fact_id": fact.fact_id,
            "window_start": (window_start or datetime.now(timezone.utc)).isoformat(),
            "window_end": window_end.isoformat() if window_end else None,
            "subject_node_id": person_node_id,
        }
