"""In-memory adapters for tests — same ports as Postgres, no I/O."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional, Sequence
from uuid import uuid4

from urie.domain.entity_resolution import CandidateNode, ERWeights
from urie.domain.facts import Fact
from urie.domain.reasoning import ActiveConstraint


class InMemoryFactRepository:
    def __init__(self) -> None:
        self._facts: dict[str, Fact] = {}

    async def get_active(self, agent_id: str, subject_node_id: str, entity: str) -> Optional[Fact]:
        matches = [
            f
            for f in self._facts.values()
            if f.agent_id == agent_id
            and f.subject_node_id == subject_node_id
            and f.entity == entity
            and f.superseded_by is None
        ]
        matches.sort(key=lambda f: f.created_at, reverse=True)
        return matches[0] if matches else None

    async def save(self, fact: Fact) -> Fact:
        self._facts[fact.fact_id] = fact
        return fact

    async def mark_superseded(self, old_fact_id: str, new_fact_id: str) -> None:
        old = self._facts[old_fact_id]
        self._facts[old_fact_id] = Fact(
            fact_id=old.fact_id,
            agent_id=old.agent_id,
            entity=old.entity,
            subject_node_id=old.subject_node_id,
            value=old.value,
            confidence_score=old.confidence_score,
            source=old.source,
            is_hypothesis=old.is_hypothesis,
            is_conflict_resolution=old.is_conflict_resolution,
            created_at=old.created_at,
            superseded_by=new_fact_id,
        )

    async def list_for_subject(self, agent_id: str, subject_node_id: str) -> list[Fact]:
        return [
            f
            for f in self._facts.values()
            if f.agent_id == agent_id and f.subject_node_id == subject_node_id
        ]


class InMemoryGraphRepository:
    def __init__(self) -> None:
        self._nodes: dict[str, dict[str, Any]] = {}
        self._edges: list[dict[str, Any]] = []
        self._er: dict[str, ERWeights] = {}

    async def get_node(self, agent_id: str, node_id: str) -> Optional[dict[str, Any]]:
        n = self._nodes.get(node_id)
        if n and n["agent_id"] == agent_id:
            return deepcopy(n)
        return None

    async def find_person_candidates(self, agent_id: str, spoken: str) -> list[CandidateNode]:
        out = []
        for n in self._nodes.values():
            if n["agent_id"] != agent_id or n["kind"] != "Person":
                continue
            neighbors = await self.neighbor_ids(agent_id, n["node_id"])
            out.append(
                CandidateNode(
                    node_id=n["node_id"],
                    name=n["name"],
                    aliases=list(n.get("aliases") or []),
                    neighbor_ids=neighbors,
                    last_touched_at=n.get("last_touched_at"),
                )
            )
        return out

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
        self._nodes[nid] = {
            "node_id": nid,
            "agent_id": agent_id,
            "kind": kind,
            "name": name,
            "aliases": aliases or [],
            "attrs": attrs or {},
            "last_touched_at": datetime.now(timezone.utc),
        }
        return nid

    async def touch_node(self, agent_id: str, node_id: str) -> None:
        n = self._nodes.get(node_id)
        if n and n["agent_id"] == agent_id:
            n["last_touched_at"] = datetime.now(timezone.utc)

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
        for e in self._edges:
            if (
                e["agent_id"] == agent_id
                and e["edge_type"] == edge_type
                and e["src_node_id"] == src_node_id
                and e["dst_node_id"] == dst_node_id
            ):
                e.update(
                    {
                        "fact_id": fact_id or e["fact_id"],
                        "confidence": confidence,
                        "rel_label": rel_label or e.get("rel_label"),
                        "window_start": window_start if window_start is not None else e.get("window_start"),
                        "window_end": window_end if window_end is not None else e.get("window_end"),
                    }
                )
                return e["edge_id"]
        eid = f"edge_{uuid4()}"
        self._edges.append(
            {
                "edge_id": eid,
                "agent_id": agent_id,
                "edge_type": edge_type,
                "src_node_id": src_node_id,
                "dst_node_id": dst_node_id,
                "fact_id": fact_id,
                "confidence": confidence,
                "rel_label": rel_label,
                "window_start": window_start,
                "window_end": window_end,
                "attrs": attrs or {},
            }
        )
        return eid

    async def neighbor_ids(self, agent_id: str, node_id: str) -> set[str]:
        result: set[str] = set()
        for e in self._edges:
            if e["agent_id"] != agent_id:
                continue
            if e["src_node_id"] == node_id:
                result.add(e["dst_node_id"])
            elif e["dst_node_id"] == node_id:
                result.add(e["src_node_id"])
        return result

    async def active_constraints(self, agent_id: str, person_node_id: str) -> list[ActiveConstraint]:
        out = []
        for e in self._edges:
            if (
                e["agent_id"] == agent_id
                and e["src_node_id"] == person_node_id
                and e["edge_type"] == "CONSTRAINED_BY"
            ):
                node = self._nodes.get(e["dst_node_id"], {})
                out.append(
                    ActiveConstraint(
                        edge_id=e["edge_id"],
                        constraint_node_id=e["dst_node_id"],
                        label=node.get("name", "Constraint"),
                        window_start=e.get("window_start"),
                        window_end=e.get("window_end"),
                    )
                )
        return out

    async def depth2_context(self, agent_id: str, node_id: str) -> dict[str, Any]:
        center = await self.get_node(agent_id, node_id)
        if not center:
            return {"node": None, "neighbors": [], "edges": []}
        neighbors = []
        edges = []
        for e in self._edges:
            if e["agent_id"] != agent_id:
                continue
            if e["src_node_id"] == node_id or e["dst_node_id"] == node_id:
                edges.append(e)
                other = e["dst_node_id"] if e["src_node_id"] == node_id else e["src_node_id"]
                n = await self.get_node(agent_id, other)
                if n:
                    neighbors.append(n)
        return {"node": center, "neighbors": neighbors, "edges": edges}

    async def list_nodes(self, agent_id: str, kind: str | None = None) -> list[dict[str, Any]]:
        return [
            deepcopy(n)
            for n in self._nodes.values()
            if n["agent_id"] == agent_id and (kind is None or n["kind"] == kind)
        ]

    async def get_er_weights(self, agent_id: str) -> ERWeights:
        return self._er.get(agent_id, ERWeights())


class InMemoryEmbeddingRepository:
    def __init__(self) -> None:
        self._vecs: dict[str, tuple[str, list[float]]] = {}

    async def upsert(self, agent_id: str, node_id: str, embedding: Sequence[float]) -> None:
        self._vecs[node_id] = (agent_id, list(embedding))

    async def search(
        self, agent_id: str, embedding: Sequence[float], limit: int = 10
    ) -> list[tuple[str, float]]:
        scored = []
        for nid, (aid, vec) in self._vecs.items():
            if aid != agent_id:
                continue
            # cosine distance approx
            dot = sum(a * b for a, b in zip(vec, embedding))
            scored.append((nid, 1.0 - dot))
        scored.sort(key=lambda x: x[1])
        return scored[:limit]


class InMemoryEventBus:
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []

    async def publish(self, agent_id: str, event_type: str, payload: dict[str, Any]) -> str:
        event_id = f"evt_{uuid4()}"
        self._events.append(
            {
                "event_id": event_id,
                "agent_id": agent_id,
                "event_type": event_type,
                "payload": payload,
                "created_at": datetime.now(timezone.utc),
                "processed_at": None,
            }
        )
        return event_id

    async def poll_unprocessed(self, limit: int = 50) -> list[dict[str, Any]]:
        out = [e for e in self._events if e["processed_at"] is None][:limit]
        return deepcopy(out)

    async def mark_processed(self, event_id: str) -> None:
        for e in self._events:
            if e["event_id"] == event_id:
                e["processed_at"] = datetime.now(timezone.utc)

