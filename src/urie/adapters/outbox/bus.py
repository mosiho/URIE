"""Transactional outbox event bus (Kafka substitute)."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from urie.adapters.db.models import OutboxEvent


class OutboxEventBus:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def publish(self, agent_id: str, event_type: str, payload: dict[str, Any]) -> str:
        event_id = f"evt_{uuid4()}"
        self.session.add(
            OutboxEvent(
                event_id=event_id,
                agent_id=agent_id,
                event_type=event_type,
                payload=payload,
            )
        )
        await self.session.flush()
        return event_id

    async def poll_unprocessed(self, limit: int = 50) -> list[dict[str, Any]]:
        q = (
            select(OutboxEvent)
            .where(OutboxEvent.processed_at.is_(None))
            .order_by(OutboxEvent.created_at.asc())
            .limit(limit)
        )
        rows = (await self.session.execute(q)).scalars().all()
        return [
            {
                "event_id": r.event_id,
                "agent_id": r.agent_id,
                "event_type": r.event_type,
                "payload": r.payload or {},
                "created_at": r.created_at,
            }
            for r in rows
        ]

    async def mark_processed(self, event_id: str) -> None:
        await self.session.execute(
            update(OutboxEvent)
            .where(OutboxEvent.event_id == event_id)
            .values(processed_at=datetime.now(timezone.utc))
        )
        await self.session.flush()
