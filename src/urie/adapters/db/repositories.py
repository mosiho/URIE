"""Agent-scoped Postgres repositories."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Sequence
from uuid import uuid4

from sqlalchemy import select, update, text
from sqlalchemy.ext.asyncio import AsyncSession

from urie.adapters.db import models as m
from urie.domain.entity_resolution import CandidateNode, ERWeights
from urie.domain.facts import Fact
from urie.domain.reasoning import ActiveConstraint


def _fact_from_row(row: m.Fact) -> Fact:
    return Fact(
        fact_id=row.fact_id,
        agent_id=row.agent_id,
        entity=row.entity,
        subject_node_id=row.subject_node_id,
        value=row.value,
        confidence_score=row.confidence_score,
        source=row.source,
        is_hypothesis=row.is_hypothesis,
        is_conflict_resolution=row.is_conflict_resolution,
        created_at=row.created_at,
        superseded_by=row.superseded_by,
    )


class PostgresFactRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active(self, agent_id: str, subject_node_id: str, entity: str) -> Optional[Fact]:
        q = (
            select(m.Fact)
            .where(
                m.Fact.agent_id == agent_id,
                m.Fact.subject_node_id == subject_node_id,
                m.Fact.entity == entity,
                m.Fact.superseded_by.is_(None),
            )
            .order_by(m.Fact.created_at.desc())
            .limit(1)
        )
        row = (await self.session.execute(q)).scalar_one_or_none()
        return _fact_from_row(row) if row else None

    async def save(self, fact: Fact) -> Fact:
        row = m.Fact(
            fact_id=fact.fact_id,
            agent_id=fact.agent_id,
            entity=fact.entity,
            subject_node_id=fact.subject_node_id,
            value=fact.value,
            confidence_score=fact.confidence_score,
            source=fact.source,
            is_hypothesis=fact.is_hypothesis,
            is_conflict_resolution=fact.is_conflict_resolution,
            created_at=fact.created_at,
            superseded_by=fact.superseded_by,
        )
        self.session.add(row)
        await self.session.flush()
        return fact

    async def mark_superseded(self, old_fact_id: str, new_fact_id: str) -> None:
        await self.session.execute(
            update(m.Fact).where(m.Fact.fact_id == old_fact_id).values(superseded_by=new_fact_id)
        )

    async def list_for_subject(self, agent_id: str, subject_node_id: str) -> list[Fact]:
        q = select(m.Fact).where(
            m.Fact.agent_id == agent_id,
            m.Fact.subject_node_id == subject_node_id,
        )
        rows = (await self.session.execute(q)).scalars().all()
        return [_fact_from_row(r) for r in rows]


class PostgresGraphRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_node(self, agent_id: str, node_id: str) -> Optional[dict[str, Any]]:
        q = select(m.Node).where(m.Node.agent_id == agent_id, m.Node.node_id == node_id)
        row = (await self.session.execute(q)).scalar_one_or_none()
        if not row:
            return None
        return {
            "node_id": row.node_id,
            "kind": row.kind.value if hasattr(row.kind, "value") else row.kind,
            "name": row.name,
            "aliases": row.aliases or [],
            "attrs": row.attrs or {},
            "last_touched_at": row.last_touched_at,
        }

    async def find_person_candidates(self, agent_id: str, spoken: str) -> list[CandidateNode]:
        q = select(m.Node).where(
            m.Node.agent_id == agent_id,
            m.Node.kind == m.NodeKind.PERSON,
        )
        rows = (await self.session.execute(q)).scalars().all()
        # Soft filter: keep nodes whose name/alias shares a token with spoken
        spoken_l = spoken.strip().lower()
        candidates: list[CandidateNode] = []
        for row in rows:
            names = [row.name] + list(row.aliases or [])
            # Include all persons for scoring; ER will threshold
            if not spoken_l or any(spoken_l in n.lower() or n.lower() in spoken_l for n in names) or True:
                neighbors = await self.neighbor_ids(agent_id, row.node_id)
                candidates.append(
                    CandidateNode(
                        node_id=row.node_id,
                        name=row.name,
                        aliases=list(row.aliases or []),
                        neighbor_ids=neighbors,
                        last_touched_at=row.last_touched_at,
                    )
                )
        return candidates

    async def create_node(
        self,
        agent_id: str,
        kind: str,
        name: str,
        aliases: list[str] | None = None,
        attrs: dict | None = None,
        node_id: str | None = None,
    ) -> str:
        nid = node_id or f"node_{uuid4()}"
        kind_enum = m.NodeKind(kind) if not isinstance(kind, m.NodeKind) else kind
        row = m.Node(
            node_id=nid,
            agent_id=agent_id,
            kind=kind_enum,
            name=name,
            aliases=aliases or [],
            attrs=attrs or {},
            last_touched_at=datetime.now(timezone.utc),
        )
        self.session.add(row)
        await self.session.flush()
        return nid

    async def touch_node(self, agent_id: str, node_id: str) -> None:
        await self.session.execute(
            update(m.Node)
            .where(m.Node.agent_id == agent_id, m.Node.node_id == node_id)
            .values(last_touched_at=datetime.now(timezone.utc))
        )

    async def upsert_edge(
        self,
        agent_id: str,
        edge_type: str,
        src_node_id: str,
        dst_node_id: str,
        fact_id: str | None = None,
        confidence: float = 0.8,
        rel_label: str | None = None,
        window_start: datetime | None = None,
        window_end: datetime | None = None,
        attrs: dict | None = None,
    ) -> str:
        et = m.EdgeType(edge_type) if not isinstance(edge_type, m.EdgeType) else edge_type
        # Find existing same type/src/dst
        q = select(m.Edge).where(
            m.Edge.agent_id == agent_id,
            m.Edge.edge_type == et,
            m.Edge.src_node_id == src_node_id,
            m.Edge.dst_node_id == dst_node_id,
        )
        existing = (await self.session.execute(q)).scalar_one_or_none()
        if existing:
            existing.fact_id = fact_id or existing.fact_id
            existing.confidence = confidence
            existing.rel_label = rel_label or existing.rel_label
            existing.window_start = window_start if window_start is not None else existing.window_start
            existing.window_end = window_end if window_end is not None else existing.window_end
            if attrs:
                existing.attrs = {**(existing.attrs or {}), **attrs}
            await self.session.flush()
            return existing.edge_id

        eid = f"edge_{uuid4()}"
        row = m.Edge(
            edge_id=eid,
            agent_id=agent_id,
            edge_type=et,
            src_node_id=src_node_id,
            dst_node_id=dst_node_id,
            fact_id=fact_id,
            confidence=confidence,
            rel_label=rel_label,
            window_start=window_start,
            window_end=window_end,
            attrs=attrs or {},
        )
        self.session.add(row)
        await self.session.flush()
        return eid

    async def neighbor_ids(self, agent_id: str, node_id: str) -> set[str]:
        q = select(m.Edge).where(
            m.Edge.agent_id == agent_id,
            (m.Edge.src_node_id == node_id) | (m.Edge.dst_node_id == node_id),
        )
        rows = (await self.session.execute(q)).scalars().all()
        result: set[str] = set()
        for e in rows:
            result.add(e.src_node_id if e.src_node_id != node_id else e.dst_node_id)
        return result

    async def active_constraints(self, agent_id: str, person_node_id: str) -> list[ActiveConstraint]:
        q = (
            select(m.Edge, m.Node)
            .join(m.Node, m.Node.node_id == m.Edge.dst_node_id)
            .where(
                m.Edge.agent_id == agent_id,
                m.Edge.src_node_id == person_node_id,
                m.Edge.edge_type == m.EdgeType.CONSTRAINED_BY,
            )
        )
        rows = (await self.session.execute(q)).all()
        out: list[ActiveConstraint] = []
        for edge, node in rows:
            out.append(
                ActiveConstraint(
                    edge_id=edge.edge_id,
                    constraint_node_id=node.node_id,
                    label=node.name,
                    window_start=edge.window_start,
                    window_end=edge.window_end,
                )
            )
        return out

    async def depth2_context(self, agent_id: str, node_id: str) -> dict[str, Any]:
        center = await self.get_node(agent_id, node_id)
        if not center:
            return {"node": None, "neighbors": [], "edges": []}
        q = select(m.Edge).where(
            m.Edge.agent_id == agent_id,
            (m.Edge.src_node_id == node_id) | (m.Edge.dst_node_id == node_id),
        )
        edges = (await self.session.execute(q)).scalars().all()
        neighbor_ids: set[str] = set()
        edge_dicts = []
        for e in edges:
            other = e.dst_node_id if e.src_node_id == node_id else e.src_node_id
            neighbor_ids.add(other)
            edge_dicts.append(
                {
                    "edge_id": e.edge_id,
                    "edge_type": e.edge_type.value if hasattr(e.edge_type, "value") else e.edge_type,
                    "src_node_id": e.src_node_id,
                    "dst_node_id": e.dst_node_id,
                    "rel_label": e.rel_label,
                    "confidence": e.confidence,
                    "window_start": e.window_start.isoformat() if e.window_start else None,
                    "window_end": e.window_end.isoformat() if e.window_end else None,
                }
            )
        # Depth-2: neighbors of neighbors
        depth2: set[str] = set()
        for nid in list(neighbor_ids):
            depth2 |= await self.neighbor_ids(agent_id, nid)
        depth2 -= {node_id}
        depth2 -= neighbor_ids

        all_ids = neighbor_ids | depth2
        neighbors = []
        for nid in all_ids:
            n = await self.get_node(agent_id, nid)
            if n:
                neighbors.append(n)
        return {"node": center, "neighbors": neighbors, "edges": edge_dicts}

    async def list_nodes(self, agent_id: str, kind: str | None = None) -> list[dict[str, Any]]:
        q = select(m.Node).where(m.Node.agent_id == agent_id)
        if kind:
            q = q.where(m.Node.kind == m.NodeKind(kind))
        rows = (await self.session.execute(q)).scalars().all()
        return [
            {
                "node_id": r.node_id,
                "kind": r.kind.value if hasattr(r.kind, "value") else r.kind,
                "name": r.name,
                "aliases": r.aliases or [],
                "attrs": r.attrs or {},
                "last_touched_at": r.last_touched_at,
            }
            for r in rows
        ]

    async def get_er_weights(self, agent_id: str) -> ERWeights:
        q = (
            select(m.ERConfig)
            .where(m.ERConfig.agent_id == agent_id, m.ERConfig.is_active.is_(True))
            .order_by(m.ERConfig.version.desc())
            .limit(1)
        )
        row = (await self.session.execute(q)).scalar_one_or_none()
        if not row:
            return ERWeights()
        return ERWeights(w1=row.w1, w2=row.w2, w3=row.w3, lambda_decay=row.lambda_decay)


class PostgresEmbeddingRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert(self, agent_id: str, node_id: str, embedding: Sequence[float]) -> None:
        existing = (
            await self.session.execute(
                select(m.NodeEmbedding).where(m.NodeEmbedding.node_id == node_id)
            )
        ).scalar_one_or_none()
        vec = list(embedding)
        if existing:
            existing.embedding = vec
            existing.agent_id = agent_id
            existing.updated_at = datetime.now(timezone.utc)
        else:
            self.session.add(
                m.NodeEmbedding(node_id=node_id, agent_id=agent_id, embedding=vec)
            )
        await self.session.flush()

    async def search(
        self, agent_id: str, embedding: Sequence[float], limit: int = 10
    ) -> list[tuple[str, float]]:
        # Cosine distance via pgvector <=> operator
        vec = list(embedding)
        result = await self.session.execute(
            text(
                """
                SELECT node_id, embedding <=> :vec AS distance
                FROM node_embeddings
                WHERE agent_id = :agent_id
                ORDER BY embedding <=> :vec
                LIMIT :limit
                """
            ),
            {"vec": str(vec), "agent_id": agent_id, "limit": limit},
        )
        return [(row.node_id, float(row.distance)) for row in result]
