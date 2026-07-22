"""Ingestion orchestrator — debrief → parse → ER → challenge → write saga."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from urie.adapters.db import models as m
from urie.adapters.db.repositories import (
    PostgresEmbeddingRepository,
    PostgresFactRepository,
    PostgresGraphRepository,
)
from urie.adapters.outbox.bus import OutboxEventBus
from urie.adapters.providers.mock import MockEmbedder, MockLLM, MockSTT
from urie.domain.challenge import CandidateMutation, detect_contradiction
from urie.domain.entity_resolution import ResolutionAction, resolve_entity, vui_prompt_for_ambiguity
from urie.domain.facts import Fact, conflict_resolution_fact


class AmbiguityPending(Exception):
    def __init__(self, payload: dict[str, Any]) -> None:
        super().__init__("entity ambiguity")
        self.payload = payload


class IngestionService:
    def __init__(
        self,
        session: AsyncSession,
        stt: MockSTT | None = None,
        llm: Any = None,
        embedder: MockEmbedder | None = None,
    ) -> None:
        self.session = session
        self.stt = stt or MockSTT()
        self.llm = llm or MockLLM()
        self.embedder = embedder or MockEmbedder()
        self.facts = PostgresFactRepository(session)
        self.graph = PostgresGraphRepository(session)
        self.embeddings = PostgresEmbeddingRepository(session)
        self.bus = OutboxEventBus(session)

    async def ensure_agent(self, agent_id: str, name: str = "Agent") -> None:
        existing = await self.session.get(m.Agent, agent_id)
        if not existing:
            self.session.add(m.Agent(agent_id=agent_id, name=name))
            await self.session.flush()
            # Default ER config
            self.session.add(
                m.ERConfig(agent_id=agent_id, version=1, w1=0.5, w2=0.3, w3=0.2, lambda_decay=0.01)
            )
            await self.session.flush()

    async def start_debrief(
        self,
        agent_id: str,
        transcript: str | None = None,
        audio: bytes | None = None,
    ) -> dict[str, Any]:
        await self.ensure_agent(agent_id)
        text = await self.stt.transcribe(audio, transcript_hint=transcript)
        session = m.DebriefSession(
            session_id=f"deb_{uuid4()}",
            agent_id=agent_id,
            status=m.DebriefStatus.ACTIVE,
            transcript=text,
            staged_mutations=[],
            pending_challenge=None,
            turns=[],
            covered_gaps=[],
            next_question=None,
            mode="oneshot",
        )
        self.session.add(session)
        await self.session.flush()

        mutations = await self.llm.parse_debrief(text, agent_id)
        return await self._process_mutations(session, mutations)

    async def resolve_challenge(
        self,
        agent_id: str,
        session_id: str,
        resolution_note: str,
        accepted_value: Any | None = None,
        resolved_node_id: str | None = None,
    ) -> dict[str, Any]:
        session = await self._get_session(agent_id, session_id)
        if not session.pending_challenge:
            raise ValueError("No pending challenge on this session")

        challenge = session.pending_challenge
        subject_node_id = resolved_node_id or challenge["subject_node_id"]
        entity = challenge["entity"]
        value = accepted_value if accepted_value is not None else challenge["candidate_value"]

        # Attach narrative into value if dict
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

        emb = await self.embedder.embed(f"{entity}:{value}")
        # Ensure subject has embedding
        node = await self.graph.get_node(agent_id, subject_node_id)
        if node:
            node_emb = await self.embedder.embed(node["name"])
            await self.embeddings.upsert(agent_id, subject_node_id, node_emb)

        event_id = await self.bus.publish(
            agent_id,
            "graph.mutation",
            {
                "kind": "fact_superseded",
                "subject_node_id": subject_node_id,
                "entity": entity,
                "fact_id": new_fact.fact_id,
                "old_fact_id": old_fact_id,
                "value": value,
                "resolution_note": resolution_note,
            },
        )

        staged = list(session.staged_mutations or [])
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
        session.staged_mutations = staged
        session.pending_challenge = None
        session.status = m.DebriefStatus.COMPLETED
        await self.session.flush()
        await self.session.commit()

        return await self.get_debrief(agent_id, session_id)

    async def get_debrief(self, agent_id: str, session_id: str) -> dict[str, Any]:
        session = await self._get_session(agent_id, session_id)
        return {
            "session_id": session.session_id,
            "agent_id": session.agent_id,
            "status": session.status.value if hasattr(session.status, "value") else session.status,
            "transcript": session.transcript,
            "staged_mutations": session.staged_mutations or [],
            "pending_challenge": session.pending_challenge,
            "turns": getattr(session, "turns", None) or [],
            "covered_gaps": getattr(session, "covered_gaps", None) or [],
            "next_question": getattr(session, "next_question", None),
            "mode": getattr(session, "mode", None) or "oneshot",
            "created_at": session.created_at.isoformat() if session.created_at else None,
        }

    async def _get_session(self, agent_id: str, session_id: str) -> m.DebriefSession:
        q = select(m.DebriefSession).where(
            m.DebriefSession.session_id == session_id,
            m.DebriefSession.agent_id == agent_id,
        )
        session = (await self.session.execute(q)).scalar_one_or_none()
        if not session:
            raise LookupError(f"Debrief session {session_id} not found")
        return session

    async def _process_mutations(
        self,
        session: m.DebriefSession,
        mutations: list[CandidateMutation],
    ) -> dict[str, Any]:
        agent_id = session.agent_id
        staged: list[dict[str, Any]] = list(session.staged_mutations or [])
        weights = await self.graph.get_er_weights(agent_id)

        for mut in mutations:
            # --- Entity resolution ---
            subject_id = mut.subject_node_id
            if not subject_id:
                candidates = await self.graph.find_person_candidates(agent_id, mut.subject_spoken)
                # Context neighbors empty on first mention
                result = resolve_entity(mut.subject_spoken, candidates, set(), weights)
                if result.action == ResolutionAction.CLARIFY:
                    ambiguity = {
                        "type": "ambiguity",
                        "field": "person_reference",
                        "spoken_token": mut.subject_spoken,
                        "candidates": [
                            {"node_id": c[0], "score": c[1], "hint": c[2]} for c in result.candidates
                        ],
                        "vui_prompt": vui_prompt_for_ambiguity(mut.subject_spoken, result.candidates),
                        "pending_mutation": {
                            "entity": mut.entity,
                            "value": mut.value,
                            "is_hypothesis": mut.is_hypothesis,
                            "edge_type": mut.edge_type,
                            "trait_name": mut.trait_name,
                        },
                    }
                    session.pending_challenge = ambiguity
                    session.status = m.DebriefStatus.AWAITING_RESOLUTION
                    session.staged_mutations = staged
                    await self.session.flush()
                    await self.session.commit()
                    return await self.get_debrief(agent_id, session.session_id)

                if result.action == ResolutionAction.UPSERT and result.node_id:
                    subject_id = result.node_id
                    await self.graph.touch_node(agent_id, subject_id)
                else:
                    subject_id = await self.graph.create_node(
                        agent_id,
                        kind="Person",
                        name=mut.subject_spoken,
                        aliases=[mut.subject_spoken],
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

            # --- Constraint / trait edges without contradiction semantics ---
            if mut.edge_type == "CONSTRAINED_BY":
                await self._apply_constraint(agent_id, mut, staged)
                continue

            if mut.edge_type == "HAS_TRAIT":
                await self._apply_trait(agent_id, mut, staged)
                continue

            # --- Fact + contradiction check ---
            existing = await self.facts.get_active(agent_id, subject_id, mut.entity)
            challenge = detect_contradiction(mut, existing)
            if challenge:
                session.pending_challenge = challenge.to_dict()
                session.status = m.DebriefStatus.AWAITING_RESOLUTION
                session.staged_mutations = staged
                await self.session.flush()
                await self.session.commit()
                return await self.get_debrief(agent_id, session.session_id)

            # Write saga: fact → graph touch → embedding → outbox (one tx)
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
            emb = await self.embedder.embed(f"{mut.subject_spoken}:{mut.entity}:{mut.value}")
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

        session.staged_mutations = staged
        session.status = m.DebriefStatus.COMPLETED
        session.pending_challenge = None
        await self.session.flush()
        await self.session.commit()
        return await self.get_debrief(agent_id, session.session_id)

    async def _apply_trait(
        self,
        agent_id: str,
        mut: CandidateMutation,
        staged: list[dict[str, Any]],
    ) -> None:
        assert mut.subject_node_id
        trait_name = mut.trait_name or str(mut.value)
        trait_id = await self.graph.create_node(
            agent_id,
            kind="Trait",
            name=trait_name,
            attrs={"value": mut.value},
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
            agent_id,
            "HAS_TRAIT",
            mut.subject_node_id,
            trait_id,
            fact_id=fact.fact_id,
            confidence=0.9,
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
        self,
        agent_id: str,
        mut: CandidateMutation,
        staged: list[dict[str, Any]],
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
            agent_id,
            kind="Constraint",
            name=label,
            attrs={"value": mut.value},
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

    async def resolve_ambiguity(
        self,
        agent_id: str,
        session_id: str,
        chosen_node_id: str | None,
        create_new: bool = False,
    ) -> dict[str, Any]:
        """Resolve a pending person-reference ambiguity, then continue mutation."""
        session = await self._get_session(agent_id, session_id)
        pending = session.pending_challenge
        if not pending or pending.get("type") != "ambiguity":
            raise ValueError("No pending ambiguity on this session")

        spoken = pending["spoken_token"]
        mut_data = pending["pending_mutation"]
        if create_new or not chosen_node_id:
            subject_id = await self.graph.create_node(
                agent_id, kind="Person", name=spoken, aliases=[spoken]
            )
            emb = await self.embedder.embed(spoken)
            await self.embeddings.upsert(agent_id, subject_id, emb)
        else:
            subject_id = chosen_node_id
            await self.graph.touch_node(agent_id, subject_id)

        session.pending_challenge = None
        session.status = m.DebriefStatus.ACTIVE
        await self.session.flush()

        mut = CandidateMutation(
            entity=mut_data["entity"],
            subject_node_id=subject_id,
            subject_spoken=spoken,
            value=mut_data["value"],
            is_hypothesis=mut_data.get("is_hypothesis", False),
            edge_type=mut_data.get("edge_type"),
            trait_name=mut_data.get("trait_name"),
        )
        return await self._process_mutations(session, [mut])
