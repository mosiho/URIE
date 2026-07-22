"""
Port-injected vertical slice engine.

Runs the full debrief → ER → challenge → write saga → ghost-mode feed loop
against any Fact/Graph/Embedding/EventBus implementations (Postgres or in-memory).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional, Protocol
from uuid import uuid4

from urie.adapters.providers.mock import MockEmbedder, MockLLM, MockSTT
from urie.domain.challenge import CandidateMutation, detect_contradiction
from urie.domain.entity_resolution import ResolutionAction, resolve_entity, vui_prompt_for_ambiguity
from urie.domain.facts import Fact, conflict_resolution_fact
from urie.domain.reasoning import Opportunity, decide_ghost_mode
from urie.ports import EmbeddingRepository, EventBus, FactRepository, GraphRepository


class SessionStore(Protocol):
    async def create(
        self, agent_id: str, transcript: str
    ) -> dict[str, Any]: ...

    async def get(self, agent_id: str, session_id: str) -> dict[str, Any]: ...

    async def save(self, session: dict[str, Any]) -> None: ...


class FeedStore(Protocol):
    async def add(self, item: dict[str, Any]) -> None: ...

    async def list(
        self, agent_id: str, include_held: bool = False
    ) -> list[dict[str, Any]]: ...

    async def get(self, agent_id: str, feed_id: str) -> Optional[dict[str, Any]]: ...

    async def update(self, item: dict[str, Any]) -> None: ...


class InMemorySessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict[str, Any]] = {}

    async def create(self, agent_id: str, transcript: str) -> dict[str, Any]:
        sid = f"deb_{uuid4()}"
        row = {
            "session_id": sid,
            "agent_id": agent_id,
            "status": "active",
            "transcript": transcript,
            "staged_mutations": [],
            "pending_challenge": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self._sessions[sid] = row
        return row

    async def get(self, agent_id: str, session_id: str) -> dict[str, Any]:
        row = self._sessions.get(session_id)
        if not row or row["agent_id"] != agent_id:
            raise LookupError(f"Debrief session {session_id} not found")
        return row

    async def save(self, session: dict[str, Any]) -> None:
        self._sessions[session["session_id"]] = session


class InMemoryFeedStore:
    def __init__(self) -> None:
        self._items: dict[str, dict[str, Any]] = {}

    async def add(self, item: dict[str, Any]) -> None:
        self._items[item["feed_id"]] = item

    async def list(self, agent_id: str, include_held: bool = False) -> list[dict[str, Any]]:
        statuses = {"active"}
        if include_held:
            statuses.add("held")
        return [
            i
            for i in self._items.values()
            if i["agent_id"] == agent_id and i["status"] in statuses
        ]

    async def get(self, agent_id: str, feed_id: str) -> Optional[dict[str, Any]]:
        i = self._items.get(feed_id)
        if i and i["agent_id"] == agent_id:
            return i
        return None

    async def update(self, item: dict[str, Any]) -> None:
        self._items[item["feed_id"]] = item


class VerticalSliceEngine:
    def __init__(
        self,
        facts: FactRepository,
        graph: GraphRepository,
        embeddings: EmbeddingRepository,
        bus: EventBus,
        sessions: SessionStore | None = None,
        feed: FeedStore | None = None,
        stt: MockSTT | None = None,
        llm: MockLLM | None = None,
        embedder: MockEmbedder | None = None,
        agents: set[str] | None = None,
    ) -> None:
        self.facts = facts
        self.graph = graph
        self.embeddings = embeddings
        self.bus = bus
        self.sessions = sessions or InMemorySessionStore()
        self.feed = feed or InMemoryFeedStore()
        self.stt = stt or MockSTT()
        self.llm = llm or MockLLM()
        self.embedder = embedder or MockEmbedder()
        self.agents = agents if agents is not None else set()

    async def ensure_agent(self, agent_id: str, name: str = "Agent") -> None:
        _ = name
        self.agents.add(agent_id)

    async def start_debrief(
        self,
        agent_id: str,
        transcript: str | None = None,
        audio: bytes | None = None,
    ) -> dict[str, Any]:
        await self.ensure_agent(agent_id)
        text = await self.stt.transcribe(audio, transcript_hint=transcript)
        session = await self.sessions.create(agent_id, text)
        mutations = await self.llm.parse_debrief(text, agent_id)
        return await self._process_mutations(session, mutations)

    async def get_debrief(self, agent_id: str, session_id: str) -> dict[str, Any]:
        return await self.sessions.get(agent_id, session_id)

    async def resolve_challenge(
        self,
        agent_id: str,
        session_id: str,
        resolution_note: str,
        accepted_value: Any | None = None,
    ) -> dict[str, Any]:
        session = await self.sessions.get(agent_id, session_id)
        challenge = session.get("pending_challenge")
        if not challenge:
            raise ValueError("No pending challenge")

        subject_node_id = challenge["subject_node_id"]
        entity = challenge["entity"]
        value = accepted_value if accepted_value is not None else challenge["candidate_value"]
        if isinstance(value, dict):
            value = {**value, "resolution_note": resolution_note}
        else:
            value = {"value": value, "resolution_note": resolution_note}

        new_fact = conflict_resolution_fact(
            agent_id=agent_id,
            entity=entity,
            subject_node_id=subject_node_id,
            value=value,
        )
        old_fact_id = challenge["existing_fact_id"]
        await self.facts.save(new_fact)
        await self.facts.mark_superseded(old_fact_id, new_fact.fact_id)
        await self.graph.touch_node(agent_id, subject_node_id)

        event_id = await self.bus.publish(
            agent_id,
            "graph.mutation",
            {
                "kind": "fact_superseded",
                "subject_node_id": subject_node_id,
                "subject_name": challenge.get("subject_spoken", "client"),
                "entity": entity,
                "fact_id": new_fact.fact_id,
                "old_fact_id": old_fact_id,
                "value": value,
                "trait_summary": f"{entity} updated after conflict resolution",
            },
        )
        staged = list(session.get("staged_mutations") or [])
        staged.append(
            {
                "fact_id": new_fact.fact_id,
                "entity": entity,
                "subject_node_id": subject_node_id,
                "value": value,
                "is_conflict_resolution": True,
                "event_id": event_id,
            }
        )
        session["staged_mutations"] = staged
        session["pending_challenge"] = None
        session["status"] = "completed"
        await self.sessions.save(session)
        return session

    async def process_reasoning(self, limit: int = 50) -> int:
        events = await self.bus.poll_unprocessed(limit=limit)
        count = 0
        for event in events:
            if event["event_type"] == "graph.mutation":
                await self._handle_mutation(event)
            await self.bus.mark_processed(event["event_id"])
            count += 1
        return count

    async def release_held(self, now: datetime | None = None) -> int:
        now = now or datetime.now(timezone.utc)
        released = 0
        # Peek all held via include_held
        items = await self.feed.list("__all__", include_held=True)  # type: ignore[arg-type]
        # InMemoryFeedStore filters by agent — iterate internal if needed
        if hasattr(self.feed, "_items"):
            items = list(self.feed._items.values())  # noqa: SLF001
        for item in items:
            if item["status"] != "held" or not item.get("held_until"):
                continue
            held_until = item["held_until"]
            if isinstance(held_until, str):
                held_until = datetime.fromisoformat(held_until)
            if held_until.tzinfo is None:
                held_until = held_until.replace(tzinfo=timezone.utc)
            if held_until > now:
                continue
            script, rationale, gift = await self.llm.synthesize_ghost_script(
                "client", item.get("rationale", ""), {}
            )
            node = await self.graph.get_node(item["agent_id"], item["subject_node_id"])
            name = node["name"] if node else "client"
            script, rationale, gift = await self.llm.synthesize_ghost_script(
                name, item.get("rationale", "update"), {}
            )
            item["script"] = script
            item["rationale"] = rationale
            item["gifting_suggestion"] = gift
            item["status"] = "active"
            item["held_until"] = None
            await self.feed.update(item)
            released += 1
        return released

    async def list_feed(self, agent_id: str, include_held: bool = False) -> list[dict[str, Any]]:
        await self.release_held()
        return await self.feed.list(agent_id, include_held=include_held)

    async def _process_mutations(
        self,
        session: dict[str, Any],
        mutations: list[CandidateMutation],
    ) -> dict[str, Any]:
        agent_id = session["agent_id"]
        staged: list[dict[str, Any]] = list(session.get("staged_mutations") or [])
        weights = await self.graph.get_er_weights(agent_id)

        for mut in mutations:
            subject_id = mut.subject_node_id
            if not subject_id:
                candidates = await self.graph.find_person_candidates(agent_id, mut.subject_spoken)
                result = resolve_entity(mut.subject_spoken, candidates, set(), weights)
                if result.action == ResolutionAction.CLARIFY:
                    session["pending_challenge"] = {
                        "type": "ambiguity",
                        "field": "person_reference",
                        "spoken_token": mut.subject_spoken,
                        "candidates": [
                            {"node_id": c[0], "score": c[1], "hint": c[2]} for c in result.candidates
                        ],
                        "vui_prompt": vui_prompt_for_ambiguity(mut.subject_spoken, result.candidates),
                    }
                    session["status"] = "awaiting_resolution"
                    session["staged_mutations"] = staged
                    await self.sessions.save(session)
                    return session
                if result.action == ResolutionAction.UPSERT and result.node_id:
                    subject_id = result.node_id
                    await self.graph.touch_node(agent_id, subject_id)
                else:
                    subject_id = await self.graph.create_node(
                        agent_id, "Person", mut.subject_spoken, aliases=[mut.subject_spoken]
                    )
                    emb = await self.embedder.embed(mut.subject_spoken)
                    await self.embeddings.upsert(agent_id, subject_id, emb)

            mut = CandidateMutation(
                entity=mut.entity,
                subject_node_id=subject_id,
                subject_spoken=mut.subject_spoken,
                value=mut.value,
                is_hypothesis=mut.is_hypothesis,
                edge_type=mut.edge_type,
                trait_name=mut.trait_name,
                rel_label=mut.rel_label,
            )

            if mut.edge_type == "CONSTRAINED_BY":
                await self._apply_constraint(agent_id, mut, staged)
                continue
            if mut.edge_type == "HAS_TRAIT":
                await self._apply_trait(agent_id, mut, staged)
                continue

            existing = await self.facts.get_active(agent_id, subject_id, mut.entity)
            challenge = detect_contradiction(mut, existing)
            if challenge:
                session["pending_challenge"] = challenge.to_dict()
                session["status"] = "awaiting_resolution"
                session["staged_mutations"] = staged
                await self.sessions.save(session)
                return session

            fact = Fact(
                agent_id=agent_id,
                entity=mut.entity,
                subject_node_id=subject_id,
                value=mut.value,
                confidence_score=0.7 if mut.is_hypothesis else 0.85,
                is_hypothesis=mut.is_hypothesis,
            )
            await self.facts.save(fact)
            await self.graph.touch_node(agent_id, subject_id)
            emb = await self.embedder.embed(f"{mut.subject_spoken}:{mut.entity}")
            await self.embeddings.upsert(agent_id, subject_id, emb)
            event_id = await self.bus.publish(
                agent_id,
                "graph.mutation",
                {
                    "kind": "fact_written",
                    "subject_node_id": subject_id,
                    "subject_name": mut.subject_spoken,
                    "entity": mut.entity,
                    "fact_id": fact.fact_id,
                    "value": mut.value,
                    "trait_summary": f"{mut.entity}={mut.value}",
                },
            )
            staged.append(
                {
                    "fact_id": fact.fact_id,
                    "entity": mut.entity,
                    "subject_node_id": subject_id,
                    "value": mut.value,
                    "event_id": event_id,
                }
            )

        session["staged_mutations"] = staged
        session["status"] = "completed"
        session["pending_challenge"] = None
        await self.sessions.save(session)
        return session

    async def _apply_trait(
        self, agent_id: str, mut: CandidateMutation, staged: list[dict[str, Any]]
    ) -> None:
        assert mut.subject_node_id
        trait_name = mut.trait_name or str(mut.value)
        trait_id = await self.graph.create_node(
            agent_id, "Trait", trait_name, attrs={"value": mut.value}
        )
        fact = Fact(
            agent_id=agent_id,
            entity=mut.entity,
            subject_node_id=mut.subject_node_id,
            value=mut.value,
            confidence_score=0.9,
        )
        await self.facts.save(fact)
        await self.graph.upsert_edge(
            agent_id, "HAS_TRAIT", mut.subject_node_id, trait_id, fact_id=fact.fact_id, confidence=0.9
        )
        emb = await self.embedder.embed(trait_name)
        await self.embeddings.upsert(agent_id, trait_id, emb)
        event_id = await self.bus.publish(
            agent_id,
            "graph.mutation",
            {
                "kind": "trait_added",
                "subject_node_id": mut.subject_node_id,
                "subject_name": mut.subject_spoken,
                "trait_node_id": trait_id,
                "trait_summary": trait_name,
                "fact_id": fact.fact_id,
            },
        )
        staged.append(
            {
                "fact_id": fact.fact_id,
                "entity": mut.entity,
                "subject_node_id": mut.subject_node_id,
                "trait_node_id": trait_id,
                "value": mut.value,
                "event_id": event_id,
            }
        )

    async def _apply_constraint(
        self, agent_id: str, mut: CandidateMutation, staged: list[dict[str, Any]]
    ) -> None:
        assert mut.subject_node_id
        label = mut.trait_name or "Do-Not-Disturb"
        window_end: Optional[datetime] = None
        if isinstance(mut.value, dict) and mut.value.get("window_end"):
            raw = mut.value["window_end"]
            if isinstance(raw, str):
                window_end = datetime.fromisoformat(raw).replace(tzinfo=timezone.utc)
            label = mut.value.get("label", label)
        constraint_id = await self.graph.create_node(
            agent_id, "Constraint", label, attrs={"value": mut.value}
        )
        fact = Fact(
            agent_id=agent_id,
            entity="Constraint",
            subject_node_id=mut.subject_node_id,
            value=mut.value,
            confidence_score=0.95,
        )
        await self.facts.save(fact)
        await self.graph.upsert_edge(
            agent_id,
            "CONSTRAINED_BY",
            mut.subject_node_id,
            constraint_id,
            fact_id=fact.fact_id,
            confidence=0.95,
            window_start=datetime.now(timezone.utc),
            window_end=window_end,
        )
        event_id = await self.bus.publish(
            agent_id,
            "graph.mutation",
            {
                "kind": "constraint_added",
                "subject_node_id": mut.subject_node_id,
                "subject_name": mut.subject_spoken,
                "constraint_node_id": constraint_id,
                "trait_summary": label,
                "window_end": window_end.isoformat() if window_end else None,
                "fact_id": fact.fact_id,
            },
        )
        staged.append(
            {
                "fact_id": fact.fact_id,
                "entity": "Constraint",
                "subject_node_id": mut.subject_node_id,
                "constraint_node_id": constraint_id,
                "value": mut.value,
                "event_id": event_id,
            }
        )

    async def _handle_mutation(self, event: dict[str, Any]) -> None:
        payload = event["payload"]
        if payload.get("kind") == "constraint_added":
            return
        subject_node_id = payload.get("subject_node_id")
        if not subject_node_id:
            return
        agent_id = event["agent_id"]
        subject_name = payload.get("subject_name")
        if not subject_name:
            node = await self.graph.get_node(agent_id, subject_node_id)
            subject_name = node["name"] if node else "client"
        trait_summary = payload.get("trait_summary") or payload.get("entity", "update")
        constraints = await self.graph.active_constraints(agent_id, subject_node_id)
        script, rationale, gift = await self.llm.synthesize_ghost_script(
            subject_name, trait_summary, payload
        )
        decision = decide_ghost_mode(
            Opportunity(subject_node_id, subject_name, trait_summary, event["event_id"]),
            constraints,
            synthesized_script=script,
            synthesized_rationale=rationale,
            gifting_suggestion=gift,
        )
        await self.feed.add(
            {
                "feed_id": f"feed_{uuid4()}",
                "agent_id": agent_id,
                "subject_node_id": subject_node_id,
                "script": decision.script,
                "rationale": decision.rationale,
                "gifting_suggestion": decision.gifting_suggestion,
                "status": "held" if decision.held else "active",
                "held_until": decision.held_until.isoformat() if decision.held_until else None,
                "source_event_id": event["event_id"],
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
